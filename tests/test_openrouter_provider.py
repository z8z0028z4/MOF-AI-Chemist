import pytest
from backend.core.providers.openrouter_provider import OpenRouterCatalog, normalize_catalog
from backend.core.providers.openrouter_provider import OpenRouterProvider, CatalogItem
from backend.core.llm_provider import ProviderUnavailableError, StructuredOutputError, parse_and_validate_structured
from backend.core import generation
from backend.services import metadata_extractor
from backend.api.routes import settings as settings_route


def _text_architecture():
    return {"input_modalities": ["text"], "output_modalities": ["text"]}


def test_catalog_filters_and_prioritizes_vendors():
    models = [
        {"id": "other/x", "name": "Other", "supported_parameters": ["response_format", "structured_outputs"], "architecture": _text_architecture()},
        {"id": "anthropic/a", "name": "Anthropic", "supported_parameters": ["response_format", "structured_outputs"], "architecture": _text_architecture()},
        {"id": "google/g", "name": "Google", "supported_parameters": ["response_format", "structured_outputs"], "architecture": _text_architecture()},
        {"id": "bad/no-schema", "supported_parameters": ["response_format"], "architecture": _text_architecture()},
    ]
    endpoints = {
        model["id"]: [{"status": 0, "supported_parameters": ["response_format", "structured_outputs"], "input_modalities": ["text"], "output_modalities": ["text"]}]
        for model in models if "response_format" in model.get("supported_parameters", []) and "structured_outputs" in model.get("supported_parameters", [])
    }
    result = normalize_catalog(models, endpoints)
    assert [item.id for item in result] == ["anthropic/a", "google/g", "other/x"]
    assert result[0].name == "Anthropic"


def test_catalog_requires_eligible_text_endpoint():
    model = [{"id": "openai/x", "name": "X", "supported_parameters": ["response_format", "structured_outputs"], "architecture": _text_architecture()}]
    endpoints = {"openai/x": [{"status": 0, "supported_parameters": ["response_format"], "input_modalities": ["text"], "output_modalities": ["text"]}]}
    assert normalize_catalog(model, endpoints) == []
    endpoints["openai/x"][0]["supported_parameters"].append("structured_outputs")
    assert [item.id for item in normalize_catalog(model, endpoints)] == ["openai/x"]


def test_catalog_fails_closed_for_missing_endpoint_evidence_but_not_modalities():
    model = [{"id": "openai/x", "name": "X", "supported_parameters": ["response_format", "structured_outputs"], "architecture": _text_architecture()}]
    assert normalize_catalog(model, {}) == []
    assert [item.id for item in normalize_catalog(model, {"openai/x": [{"status": 0, "supported_parameters": ["response_format"]}]})] == []
    assert [item.id for item in normalize_catalog(model, {"openai/x": [{"status": 0, "supported_parameters": ["response_format", "structured_outputs"]}]})] == ["openai/x"]


def test_catalog_fails_closed_for_failed_endpoint_response():
    model = [{"id": "openai/x", "name": "X", "supported_parameters": ["response_format", "structured_outputs"], "architecture": _text_architecture()}]
    assert normalize_catalog(model, {"openai/x": []}) == []


def test_catalog_excludes_malformed_endpoint_records():
    model = [{"id": "openai/x", "name": "X", "supported_parameters": ["response_format", "structured_outputs"], "architecture": _text_architecture()}]

    assert normalize_catalog(model, {"openai/x": [{
        "status": "available",
        "supported_parameters": ["response_format", "structured_outputs"],
    }]}) == []
    assert normalize_catalog(model, {"openai/x": [{
        "status": 0,
        "supported_parameters": "response_format",
    }]}) == []
    assert normalize_catalog(model, {"openai/x": [{
        "status": 0,
        "supported_parameters": ["response_format", 123],
    }]}) == []
    assert normalize_catalog(model, {"openai/x": [{
        "status": 0,
        "supported_parameters": ["response_format", "structured_outputs"],
    }, "not-an-endpoint"]}) == []  # type: ignore[arg-type]


def test_catalog_scans_all_pages_and_persists_normalized_records(tmp_path):
    calls = []

    def model(identifier):
        return {"id": identifier, "name": identifier, "supported_parameters": ["response_format", "structured_outputs"], "architecture": _text_architecture()}

    class Response:
        is_success = True
        def __init__(self, models, pagination=None, endpoint=False):
            self.models, self.pagination, self.endpoint = models, pagination or {}, endpoint
        def raise_for_status(self): pass
        def json(self):
            if self.endpoint:
                return {"data": [{"status": 0, "supported_parameters": ["response_format", "structured_outputs"]}]}
            return {"data": self.models, "pagination": self.pagination}

    class Client:
        def get(self, url, headers):
            calls.append(url)
            assert "%2F" not in url
            if "/endpoints" in url:
                return Response([], endpoint=True)
            if "offset=100" in url:
                return Response([model("anthropic/next")], {"has_more": False})
            return Response([model(f"openai/{index}") for index in range(2)], {"has_more": True, "next_cursor": "100"})

    path = tmp_path / "eligible_catalog.json"
    catalog = OpenRouterCatalog(lambda: "key", Client(), path)
    first = catalog.load()
    assert [item.id for item in first["models"]] == ["openai/0", "openai/1", "anthropic/next"]
    assert first["has_more"] is False
    assert '"eligibility"' in path.read_text(encoding="utf-8")
    assert sum("/models?" in call for call in calls) == 2
    assert sum("/endpoints" in call for call in calls) == 3
    calls.clear()
    assert len(catalog.load()["models"]) == 3
    assert calls == []


def test_catalog_endpoint_request_preserves_model_namespace_separator(tmp_path):
    model_id = "vendor/model"
    calls = []

    class Response:
        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            pass

        def json(self):
            return self.payload

    class Client:
        def get(self, url, headers):
            calls.append(url)
            assert "%2F" not in url
            if url.endswith("/endpoints"):
                return Response({"data": [{"status": 0, "supported_parameters": ["response_format", "structured_outputs"]}]})
            return Response({"data": {"id": model_id, "name": "Model", "supported_parameters": ["response_format", "structured_outputs"], "architecture": _text_architecture()}})

    catalog = OpenRouterCatalog(lambda: "key", Client(), tmp_path / "catalog.json")
    assert catalog.contains(model_id) is True
    assert calls == [
        "https://openrouter.ai/api/v1/model/vendor/model",
        "https://openrouter.ai/api/v1/models/vendor/model/endpoints",
    ]


@pytest.mark.asyncio
async def test_openrouter_model_save_failure_does_not_mutate_settings(monkeypatch):
    existing = {"provider": "openrouter", "model": "openrouter/old"}

    class FailingCatalog:
        def contains(self, model_id, refresh=False):
            assert model_id == "vendor/model"
            assert refresh is True
            raise ProviderUnavailableError("targeted check failed")

    monkeypatch.setattr(settings_route, "_openrouter_catalog", FailingCatalog())
    monkeypatch.setattr(settings_route.settings_manager, "get_provider", lambda: existing["provider"])
    monkeypatch.setattr(settings_route.settings_manager, "set_provider", lambda provider: existing.__setitem__("provider", provider))
    monkeypatch.setattr(settings_route.settings_manager, "set_current_model", lambda model: existing.__setitem__("model", model))

    with pytest.raises(settings_route.HTTPException) as failure:
        await settings_route.update_model_settings(settings_route.ModelSettings(llm_provider="openrouter", llm_model="vendor/model"))

    assert failure.value.status_code == 400
    assert "refresh and reselect" in failure.value.detail
    assert existing == {"provider": "openrouter", "model": "openrouter/old"}


def test_catalog_refresh_failure_preserves_previous_bytes(tmp_path):
    path = tmp_path / "eligible_catalog.json"
    class Response:
        def __init__(self, fail=False): self.fail = fail
        def raise_for_status(self): pass
        def json(self): return {"data": []}
    class Client:
        fail = False
        def get(self, url, headers):
            if self.fail:
                raise RuntimeError("offline")
            if "/endpoints" in url:
                return Response()
            return Response()
    client = Client()
    catalog = OpenRouterCatalog(lambda: "key", client, path)
    # Seed a valid catalog through the same atomic writer, then fail refresh.
    catalog._write_catalog([CatalogItem("openai/x", "X", 0)])
    before = path.read_bytes()
    client.fail = True
    result = catalog.load(refresh=True)
    assert result["stale"] is True
    assert result["models"][0].id == "openai/x"
    assert path.read_bytes() == before


def test_catalog_rejects_persisted_records_without_eligibility_evidence(tmp_path):
    path = tmp_path / "eligible_catalog.json"
    path.write_text('{"schema_version": 1, "models": [{"id": "openai/x", "name": "X", "vendor": "openai", "vendor_rank": 0}]}', encoding="utf-8")
    catalog = OpenRouterCatalog(lambda: "key", object(), path)
    assert catalog._read_catalog() is None


def test_catalog_uses_model_architecture_when_endpoint_omits_modalities():
    models = [
        {
            "id": "openai/gpt-5.6-luna",
            "name": "GPT-5.6 Luna",
            "supported_parameters": ["response_format", "structured_outputs"],
            "architecture": {
                "modality": "text+image+file->text",
                "input_modalities": ["file", "image", "text"],
                "output_modalities": ["text"],
            },
        },
        {
            "id": "other/missing-architecture",
            "supported_parameters": ["response_format", "structured_outputs"],
        },
        {
            "id": "other/malformed-architecture",
            "supported_parameters": ["response_format", "structured_outputs"],
            "architecture": {"input_modalities": "text", "output_modalities": ["text"]},
        },
    ]
    endpoints = {
        "openai/gpt-5.6-luna": [{
            "status": 0,
            "supported_parameters": ["response_format", "structured_outputs"],
        }],
        "other/missing-architecture": [{
            "status": 0,
            "supported_parameters": ["response_format", "structured_outputs"],
        }],
        "other/malformed-architecture": [{
            "status": 0,
            "supported_parameters": ["response_format", "structured_outputs"],
        }],
    }

    assert [item.id for item in normalize_catalog(models, endpoints)] == ["openai/gpt-5.6-luna"]


def test_structured_output_is_not_repaired():
    with pytest.raises(StructuredOutputError):
        parse_and_validate_structured("prefix {\"x\": 1}", {"type": "object"})


def test_structured_request_uses_openai_schema_envelope_and_required_parameters():
    class Response:
        def raise_for_status(self): pass
        def json(self): return {"choices": [{"message": {"content": '{"answer":"ok"}'}, "finish_reason": "stop"}]}

    class Client:
        def __init__(self): self.body = None
        def post(self, url, headers, json): self.body = json; return Response()

    client = Client()
    class Catalog:
        def load(self, refresh=False): return {"models": [CatalogItem("openai/x", "X", 0)]}
    provider = OpenRouterProvider(lambda: "secret-not-printed", client=client, catalog=Catalog())
    result = provider.generate_structured("hello", "openai/x", {"type": "object", "required": ["answer"], "properties": {"answer": {"type": "string"}}}, schema_name="Answer")
    assert result.data == {"answer": "ok"}
    assert client.body["response_format"]["type"] == "json_schema"
    assert client.body["response_format"]["json_schema"]["name"] == "Answer"
    assert client.body["provider"] == {"require_parameters": True}


def test_text_request_rechecks_runtime_catalog_before_posting():
    class Response:
        def raise_for_status(self): pass
        def json(self): return {"choices": [{"message": {"content": "ok"}}]}

    class Client:
        posted = False
        def post(self, url, headers, json):
            self.posted = True
            return Response()

    class Catalog:
        def load(self, refresh=False):
            assert refresh is True
            return {"models": []}

    client = Client()
    provider = OpenRouterProvider(lambda: "key", client=client, catalog=Catalog())  # type: ignore[arg-type]
    with pytest.raises(ProviderUnavailableError, match="refresh and reselect"):
        provider.generate_text("hello", "openai/removed")
    assert client.posted is False


def test_catalog_requires_key_and_does_not_expose_cached_models_without_it():
    catalog = OpenRouterCatalog(lambda: None, client=object())
    with pytest.raises(ProviderUnavailableError, match="API key is required"):
        catalog.load()


def test_named_generation_wrappers_forward_openrouter_models_to_facade(monkeypatch):
    selected = "openrouter/vendor/model"
    calls = []

    def fake_structured(prompt, schema, model=None, **kwargs):
        calls.append(model)
        return {}

    monkeypatch.setattr(generation, "_selected_provider", lambda: "openrouter")
    monkeypatch.setattr(generation, "call_structured_llm", fake_structured)
    monkeypatch.setattr(generation, "get_current_model", lambda: selected)

    generation.call_llm_structured_proposal("system", "user", model=selected)
    generation.call_llm_structured_experimental_detail([], "proposal", model=selected)
    generation.call_llm_structured_revision_proposal("feedback", [], [], "proposal", model=selected)
    generation.call_llm_structured_revision_experimental_detail(
        "feedback", [], [], "proposal", "details", model=selected
    )

    assert calls == [selected, selected, selected, selected]


def test_upload_metadata_uses_structured_facade_and_local_schema(monkeypatch):
    calls = []

    def fake_structured(prompt, schema, model=None, **kwargs):
        calls.append((model, schema))
        return {"type": "SI", "title": "Supplement"}

    monkeypatch.setattr(metadata_extractor, "call_structured_llm", fake_structured)
    assert metadata_extractor.gpt_detect_type_and_title("text", "paper.pdf") == ("SI", "Supplement")
    assert calls and calls[0][1]["required"] == ["type", "title"]
    assert calls[0][1]["additionalProperties"] is False


def test_upload_metadata_fails_closed_on_schema_invalid_facade_result(monkeypatch):
    def invalid_structured(prompt, schema, model=None, **kwargs):
        return {"type": "not-a-valid-type", "title": "bad"}

    monkeypatch.setattr(metadata_extractor, "call_structured_llm", invalid_structured)
    with pytest.raises(StructuredOutputError):
        metadata_extractor.gpt_detect_type_and_title("text", "paper.pdf")


def test_structured_wrappers_propagate_provider_failures(monkeypatch):
    def failed_structured(*args, **kwargs):
        raise StructuredOutputError("invalid structured payload")

    monkeypatch.setattr(generation, "call_structured_llm", failed_structured)
    with pytest.raises(StructuredOutputError):
        generation.call_llm_structured_experimental_detail([], "proposal", model="openrouter/vendor/model")
    with pytest.raises(StructuredOutputError):
        generation.call_llm_structured_proposal("system", "user", model="openrouter/vendor/model")


def test_active_mof_extraction_forwards_selected_openrouter_model_and_propagates_failure(monkeypatch):
    selected = "openrouter/vendor/model"
    forwarded = []

    monkeypatch.setattr(generation, "get_current_model", lambda: selected)

    def failed_structured(prompt, schema, model=None, **kwargs):
        forwarded.append(model)
        raise ProviderUnavailableError("selected model unavailable")

    monkeypatch.setattr(generation, "call_structured_llm", failed_structured)
    with pytest.raises(ProviderUnavailableError, match="selected model unavailable"):
        generation.extract_mof_from_proposal("A proposal about a MOF")
    assert forwarded == [selected]


def test_provider_key_route_preserves_blank_save_and_returns_status_only(monkeypatch):
    values = {
        "OPENAI_API_KEY": "openai-secret",
        "GOOGLE_API_KEY": "google-secret",
    }
    updates = []

    monkeypatch.setattr(settings_route.env_manager, "get_env_variable", values.get)
    monkeypatch.setattr(settings_route.env_manager, "update_env_variable", lambda key, value: updates.append((key, value)) or values.__setitem__(key, value) or True)
    monkeypatch.setattr(settings_route, "reload_config", lambda: None)

    import asyncio
    result = asyncio.run(settings_route.set_provider_key(settings_route.ProviderKeySettings(provider="openai", api_key="   ")))

    assert updates == []
    assert result == {"provider": "openai", "configured": True, "status": "success"}
    assert "openai-secret" not in result
    assert "google-secret" not in result

    result = asyncio.run(settings_route.set_provider_key(settings_route.ProviderKeySettings(provider="google", api_key="new-google")))
    assert updates == [("GOOGLE_API_KEY", "new-google")]
    assert values["OPENAI_API_KEY"] == "openai-secret"
    assert result["configured"] is True


def test_provider_key_route_clear_is_scoped_and_switching_preserves_other_keys(monkeypatch):
    values = {"OPENAI_API_KEY": "openai-secret", "GOOGLE_API_KEY": "google-secret"}
    writes = []

    monkeypatch.setattr(settings_route.env_manager, "read_env_file", lambda: dict(values))
    def write_env_file(updated):
        values.clear()
        values.update(updated)
        writes.append(dict(updated))
        return True

    monkeypatch.setattr(settings_route.env_manager, "write_env_file", write_env_file)
    monkeypatch.setattr(settings_route.env_manager, "get_env_variable", values.get)
    monkeypatch.setattr(settings_route.env_manager, "update_env_variable", lambda key, value: values.__setitem__(key, value) or True)
    monkeypatch.setattr(settings_route, "reload_config", lambda: None)

    import asyncio
    result = asyncio.run(settings_route.set_provider_key(settings_route.ProviderKeySettings(provider="openai", clear=True)))
    assert writes == [{"GOOGLE_API_KEY": "google-secret"}]
    assert result == {"provider": "openai", "configured": False, "status": "success"}
    assert "openai-secret" not in result

    asyncio.run(settings_route.set_provider_key(settings_route.ProviderKeySettings(provider="google", api_key="new-google")))
    assert "OPENAI_API_KEY" not in values
    assert values["GOOGLE_API_KEY"] == "new-google"


def test_settings_has_one_provider_selector_and_renders_catalog_errors():
    source = open("frontend/src/pages/Settings.jsx", encoding="utf-8").read()
    assert source.count('<Option value="openrouter">') == 1
    assert 'label="Vendor 篩選"' not in source
    assert 'dropdownStyle={{ maxHeight: 320, overflowY: \'auto\' }}' in source
    assert "catalogState.error" in source
    assert "modelData.catalog_error" in source
    assert "handleResetToDefault" not in source
    assert "重置為預設" not in source
    assert "getProviderModels(llmProvider, isRefresh)" in source
    assert "Refresh {llmProvider} models" in source


@pytest.mark.asyncio
async def test_settings_model_route_preserves_initial_catalog_error(monkeypatch):
    monkeypatch.setattr(settings_route.settings_manager, "get_current_model", lambda: "openrouter/vendor/model")
    monkeypatch.setattr(settings_route.settings_manager, "get_fallback_model", lambda: "fallback")
    monkeypatch.setattr(settings_route.settings_manager, "get_provider", lambda: "openrouter")
    monkeypatch.setattr(settings_route.env_manager, "get_provider_key", lambda name: "key")

    class FailingCatalog:
        def load(self):
            raise RuntimeError("catalog unavailable")

    monkeypatch.setattr(settings_route, "_openrouter_catalog", FailingCatalog())
    response = await settings_route.get_model_settings()
    assert response.available_models == []
    assert response.catalog_stale is True
    assert "catalog unavailable" in (response.catalog_error or "")

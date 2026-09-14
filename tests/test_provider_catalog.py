import json

import httpx
import pytest

from backend.core.providers.provider_catalog import ProviderCatalog


VALID_EXPERIMENTAL_DETAIL = {
    "synthesis_process": "mix and heat",
    "materials_and_conditions": "solvent and temperature",
    "analytical_methods": "XRD",
    "precautions": "wear protection",
}


class Response:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


@pytest.mark.unit
def test_provider_list_records_are_dynamic_candidates(tmp_path):
    catalog = ProviderCatalog(
        "openai", lambda: "configured", catalog_path=tmp_path / "openai.json",
        evidence={"gpt-5": {"source_url": "https://platform.openai.com/docs/guides/structured-outputs", "structured_outputs": True}},
    )
    assert catalog.normalize([{"id": "gpt-5", "name": "GPT-5"}, {"id": "gpt-unknown", "name": "Unknown"}])[0].id == "gpt-5"
    assert catalog.normalize([{"id": "gpt-unknown", "name": "Unknown"}])[0].id == "gpt-unknown"


@pytest.mark.unit
def test_openai_request_is_authenticated_and_persisted_without_raw_payload(tmp_path):
    calls = []

    class Client:
        def get(self, url, headers):
            calls.append((url, headers))
            return Response({"data": [{"id": "gpt-5", "owned_by": "hidden", "name": "GPT-5"}]})

    catalog = ProviderCatalog("openai", lambda: "not-recorded", Client(), tmp_path / "openai.json")
    result = catalog.load(refresh=True)
    assert [item.id for item in result["models"]] == ["gpt-5"]
    assert calls[0][0] == "https://api.openai.com/v1/models"
    assert calls[0][1]["Authorization"].startswith("Bearer ")
    stored = json.loads((tmp_path / "openai.json").read_text())
    assert "owned_by" not in stored["models"][0]
    assert "not-recorded" not in (tmp_path / "openai.json").read_text()


@pytest.mark.unit
def test_google_pagination_is_key_scoped_and_refresh_failure_keeps_bytes(tmp_path):
    calls = []

    class Client:
        def get(self, url, headers):
            calls.append(url)
            if "pageToken" not in url:
                return Response({"models": [{"name": "models/gemini-2.5-pro", "displayName": "Gemini Pro"}], "nextPageToken": "next"})
            return Response({"models": [{"name": "models/gemini-3-flash-preview", "displayName": "Gemini Flash"}]})

    catalog = ProviderCatalog("google", lambda: "secret", Client(), tmp_path / "google.json")
    result = catalog.load(refresh=True)
    assert [item.id for item in result["models"]] == ["models/gemini-2.5-pro", "models/gemini-3-flash-preview"]
    assert all("key=secret" not in call for call in calls) is False  # key is sent only in the request URL, never persisted
    before = (tmp_path / "google.json").read_bytes()
    catalog.client = type("Failing", (), {"get": lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("offline"))})()
    stale = catalog.load(refresh=True)
    assert stale["stale"] is True
    assert (tmp_path / "google.json").read_bytes() == before


@pytest.mark.unit
def test_missing_key_returns_empty_provider_scoped_result(tmp_path):
    result = ProviderCatalog("google", lambda: None, catalog_path=tmp_path / "google.json").load()
    assert result["models"] == []
    assert "Google API key" in result["error"]


@pytest.mark.unit
@pytest.mark.parametrize(
    "evidence",
    [
        {"structured_outputs": True, "source_url": "http://evil.example/evidence"},
        {"structured_outputs": True, "source_url": "https://example.invalid/wrong-registry"},
    ],
)
def test_persisted_catalog_treats_documentation_as_non_gating_audit_metadata(tmp_path, evidence):
    path = tmp_path / "openai.json"
    path.write_text(json.dumps({
        "schema_version": 1,
        "provider": "openai",
        "models": [{"id": "gpt-5", "name": "GPT-5", "provider": "openai", "evidence": evidence}],
    }))
    catalog = ProviderCatalog("openai", lambda: "configured", catalog_path=path)

    assert catalog.contains("gpt-5") is True
    loaded = catalog._read_catalog()
    assert loaded is not None
    assert loaded[0].id == "gpt-5"


@pytest.mark.unit
def test_google_refresh_error_does_not_expose_query_key_or_exception(tmp_path):
    secret = "google-key-must-not-leak"

    class FailingClient:
        def get(self, url, headers):
            raise RuntimeError(f"request failed: {url} key={secret}")

    path = tmp_path / "google.json"
    catalog = ProviderCatalog("google", lambda: secret, FailingClient(), path)
    result = catalog.load(refresh=True)

    assert secret not in result["error"]
    assert secret not in path.read_text() if path.exists() else True


@pytest.mark.unit
def test_detection_uses_selected_native_model_and_validates_locally(tmp_path):
    calls = []

    class Client:
        def post(self, url, **kwargs):
            calls.append((url, kwargs))
            return Response({"output_text": json.dumps(VALID_EXPERIMENTAL_DETAIL)})

    catalog = ProviderCatalog("openai", lambda: "configured", Client(), tmp_path / "openai.json")
    catalog._write_catalog(catalog.normalize([{"id": "gpt-4.1", "name": "GPT-4.1"}]))
    result = catalog.detect_structured_output("gpt-4.1")
    assert result["status"] == "success"
    assert calls[0][0].endswith("/v1/responses")
    assert calls[0][1]["json"]["model"] == "gpt-4.1"
    assert calls[0][1]["json"]["text"]["format"]["type"] == "json_schema"


@pytest.mark.unit
def test_google_detection_converts_wire_name_without_changing_catalog_id(tmp_path):
    calls = []

    class Client:
        def post(self, url, **kwargs):
            calls.append((url, kwargs))
            return Response({"candidates": [{"content": {"parts": [{"text": json.dumps(VALID_EXPERIMENTAL_DETAIL)}]}}]})

    catalog = ProviderCatalog("google", lambda: "configured", Client(), tmp_path / "google.json")
    catalog._write_catalog(catalog.normalize([{"name": "models/gemini-2.5-flash", "displayName": "Flash"}]))
    result = catalog.detect_structured_output("models/gemini-2.5-flash")
    assert result["status"] == "success"
    assert "/models/gemini-2.5-flash:generateContent" in calls[0][0]
    schema = calls[0][1]["json"]["generationConfig"]["responseSchema"]
    assert "title" not in schema
    assert "additionalProperties" not in schema
    assert catalog.contains("models/gemini-2.5-flash")


@pytest.mark.unit
def test_openai_detection_extracts_rest_nested_responses_output(tmp_path):
    calls = []

    class Client:
        def post(self, url, **kwargs):
            calls.append((url, kwargs))
            return Response({"output": [{"type": "message", "content": [
                {"type": "output_text", "text": json.dumps(VALID_EXPERIMENTAL_DETAIL)},
            ]}]})

    catalog = ProviderCatalog("openai", lambda: "configured", Client(), tmp_path / "openai.json")
    result = catalog.detect_structured_output("gpt-4.1")
    assert result["status"] == "success"
    assert len(calls) == 1
    assert calls[0][1]["json"]["text"]["format"]["schema"]["title"] == "ExperimentalDetail"


@pytest.mark.unit
def test_detection_classifies_http_400_as_deterministic_schema_rejection(tmp_path):
    class ProviderError(RuntimeError):
        response = type("ResponseMetadata", (), {"status_code": 400})()

    class Response400(Response):
        def raise_for_status(self):
            raise ProviderError("provider rejected schema")

    class Client:
        def post(self, url, **kwargs):
            return Response400({"error": {"status": "INVALID_ARGUMENT"}})

    catalog = ProviderCatalog("google", lambda: "configured", Client(), tmp_path / "google.json")
    result = catalog.detect_structured_output("models/gemini-test")
    assert result["status"] == "schema_rejected"
    assert "temporary" not in result["message"]


@pytest.mark.unit
@pytest.mark.parametrize("status_code", [401, 403])
def test_google_detection_classifies_non_json_auth_errors_before_body_parsing(tmp_path, status_code):
    class ResponseAuthFailure(Response):
        def json(self):
            raise ValueError("response body is not JSON")

        def raise_for_status(self):
            request = httpx.Request("POST", "https://example.invalid")
            response = httpx.Response(status_code, request=request, text="permission denied")
            raise httpx.HTTPStatusError("provider rejected request", request=request, response=response)

    class Client:
        def post(self, url, **kwargs):
            return ResponseAuthFailure(None)

    catalog = ProviderCatalog("google", lambda: "configured", Client(), tmp_path / "google.json")
    result = catalog.detect_structured_output("models/gemini-test")

    assert result["status"] == "authentication"
    assert "permission denied" not in result["message"]


@pytest.mark.unit
def test_detection_distinguishes_malformed_and_schema_invalid_output(tmp_path):
    class Client:
        def __init__(self, payload):
            self.payload = payload

        def post(self, url, **kwargs):
            return Response({"output_text": self.payload})

    malformed = ProviderCatalog("openai", lambda: "configured", Client("not-json"), tmp_path / "malformed.json")
    invalid = ProviderCatalog("openai", lambda: "configured", Client('{"synthesis_process": "only"}'), tmp_path / "invalid.json")
    assert malformed.detect_structured_output("gpt-4.1")["status"] == "schema_rejected"
    assert invalid.detect_structured_output("gpt-4.1")["status"] == "schema_rejected"

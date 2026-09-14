import asyncio
from io import BytesIO


import pytest
from fastapi import BackgroundTasks, UploadFile
from fastapi import HTTPException
from langchain_core.documents import Document


def run_async(coro):
    return asyncio.run(coro)


@pytest.mark.fast
@pytest.mark.api
def test_settings_config_status_contract_without_real_keys(monkeypatch):
    from backend.api.routes import settings as settings_routes

    fake_validation = {
        "config_complete": False,
        "missing_keys": ["OPENAI_API_KEY", "GOOGLE_API_KEY"],
        "warnings": ["dummy key ignored"],
    }
    fake_env_status = {
        "exists": True,
        "path": "/tmp/test.env",
        "openai_key_configured": False,
        "google_key_configured": False,
    }

    monkeypatch.setattr(settings_routes, "validate_config", lambda: fake_validation)
    monkeypatch.setattr(
        settings_routes.env_manager,
        "get_env_file_status",
        lambda: fake_env_status,
    )

    data = run_async(settings_routes.get_config_status())

    assert data == {
        "config_validation": fake_validation,
        "env_status": fake_env_status,
        "system_ready": False,
    }


@pytest.mark.fast
@pytest.mark.api
def test_knowledge_query_contract_with_fake_retrieval(monkeypatch):
    import backend.core as core
    from backend.api.routes.knowledge import KnowledgeQueryRequest, query_knowledge

    chunks = [
        Document(
            page_content="MOF adsorption evidence",
            metadata={"source": "paper.pdf", "page": 7},
        )
    ]

    monkeypatch.setattr(core, "load_paper_vectorstore", lambda: object())
    monkeypatch.setattr(core, "search_documents", lambda **_: chunks)
    monkeypatch.setattr(
        core,
        "build_prompt",
        lambda docs, question: (
            "system prompt",
            [{"source": "paper.pdf", "page": "7", "text": docs[0].page_content}],
        ),
    )
    monkeypatch.setattr(core, "call_llm", lambda prompt: "fake answer")

    response = run_async(
        query_knowledge(
            KnowledgeQueryRequest(
                question="How does this MOF adsorb CO2?",
                retrieval_count=3,
                answer_mode="rigorous",
            )
        )
    )

    assert response.answer == "fake answer"
    assert response.citations[0]["source"] == "paper.pdf"
    assert response.chunks == [
        {
            "page_content": "MOF adsorption evidence",
            "metadata": {"source": "paper.pdf", "page": 7},
        }
    ]


@pytest.mark.fast
@pytest.mark.api
def test_knowledge_query_returns_404_when_fake_retrieval_is_empty(monkeypatch):
    import backend.core as core
    from backend.api.routes.knowledge import KnowledgeQueryRequest, query_knowledge

    monkeypatch.setattr(core, "load_paper_vectorstore", lambda: object())
    monkeypatch.setattr(core, "search_documents", lambda **_: [])

    with pytest.raises(HTTPException) as exc_info:
        run_async(
            query_knowledge(
                KnowledgeQueryRequest(
                    question="No matching evidence",
                    retrieval_count=3,
                    answer_mode="rigorous",
                )
            )
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "未找到相關文獻"


@pytest.mark.fast
@pytest.mark.api
def test_proposal_generate_contract_with_fake_agent(monkeypatch):
    from backend.api.routes import proposal as proposal_routes
    from backend.api.routes.proposal import ProposalRequest, generate_proposal
    from backend.services import knowledge_service

    fake_chunk = Document(
        page_content="citation evidence",
        metadata={"source": "paper.pdf", "page": 2},
    )

    monkeypatch.setattr(
        knowledge_service,
        "agent_answer",
        lambda question, mode, k, **kwargs: {
            "answer": "Use ethanol as a solvent.",
            "citations": [{"source": "paper.pdf", "page": 2}],
            "chunks": [fake_chunk],
            "used_model": "fake-model",
            "structured_proposal": None,
        },
    )
    monkeypatch.setattr(
        proposal_routes.chemical_service,
        "extract_chemicals_with_drawings",
        lambda answer: (
            [{"name": "ethanol", "formula": "C2H6O", "smiles": "CCO"}],
            [],
            answer,
        ),
    )
    monkeypatch.setattr(
        "backend.core.generation.extract_mof_from_proposal",
        lambda answer, **kwargs: {"metals": [], "linkers": [], "extracted_text": answer},
    )

    response = run_async(
        generate_proposal(
            ProposalRequest(
                research_goal="Make a CO2 adsorption material",
                retrieval_count=2,
            )
        )
    )

    assert response.proposal == "Use ethanol as a solvent."
    assert response.chemicals[0]["name"] == "ethanol"
    assert response.citations == [{"source": "paper.pdf", "page": "2"}]
    assert response.chunks == [
        {
            "page_content": "citation evidence",
            "metadata": {"source": "paper.pdf", "page": 2},
        }
    ]
    assert response.used_model == "fake-model"


@pytest.mark.fast
@pytest.mark.api
def test_upload_files_contract_schedules_background_task(monkeypatch):
    from backend.api.routes import upload as upload_routes
    from backend.api.routes.upload import upload_files

    scheduled_tasks = []

    class FakeBackgroundTasks(BackgroundTasks):
        def add_task(self, func, *args, **kwargs):
            scheduled_tasks.append((func, args, kwargs))

    monkeypatch.setattr(upload_routes.tempfile, "mkdtemp", lambda: "/tmp/fake-upload")
    monkeypatch.setattr(upload_routes.os.path, "getsize", lambda path: 12)
    monkeypatch.setattr(upload_routes.os.path, "join", lambda *parts: "/".join(parts))
    monkeypatch.setattr(upload_routes.shutil, "copyfileobj", lambda src, dst: dst.write(src.read()))
    monkeypatch.setattr(
        "builtins.open",
        lambda *args, **kwargs: BytesIO(),
    )

    upload_routes.processing_tasks.clear()

    response = run_async(
        upload_files(
            background_tasks=FakeBackgroundTasks(),
            files=[
                UploadFile(
                    filename="paper.pdf",
                    file=BytesIO(b"%PDF fake content"),
                )
            ],
        )
    )

    assert response.success is True
    assert response.processing_status == "pending"
    assert response.file_info == {
        "task_id": "task_1",
        "file_count": 1,
        "file_names": ["paper.pdf"],
    }
    assert upload_routes.processing_tasks["task_1"]["status"] == "pending"
    assert scheduled_tasks[0][0] is upload_routes.process_files_background


@pytest.mark.fast
@pytest.mark.api
def test_upload_status_contract_for_existing_and_missing_task():
    from backend.api.routes import upload as upload_routes
    from backend.api.routes.upload import get_processing_status

    upload_routes.processing_tasks.clear()
    upload_routes.processing_tasks["task_7"] = {
        "status": "completed",
        "progress": 100,
        "message": "done",
        "results": {"papers": 1},
    }

    response = run_async(get_processing_status("task_7"))

    assert response.task_id == "task_7"
    assert response.status == "completed"
    assert response.progress == 100
    assert response.message == "done"
    assert response.results == {"papers": 1}

    with pytest.raises(HTTPException) as exc_info:
        run_async(get_processing_status("missing"))

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "任務不存在"


@pytest.mark.fast
@pytest.mark.api
def test_upload_processing_summary_reports_skipped_papers():
    from backend.api.routes.upload import _build_processing_summary

    summary = _build_processing_summary(
        file_info={
            "type": "mixed",
            "papers": ["/tmp/duplicate.pdf"],
            "experiments": [],
            "others": [],
        },
        paper_results=[],
        experiment_results=[],
    )

    assert summary == {
        "paper_files": 1,
        "paper_files_processed": 0,
        "paper_files_skipped": 1,
        "experiment_files": 0,
        "experiment_files_embedded": 0,
        "experiment_files_failed": 0,
        "other_files": 0,
        "total_files": 1,
        "total_files_with_no_new_vectors": 1,
    }


@pytest.mark.fast
@pytest.mark.api
def test_upload_stats_contract_uses_cached_vector_stats(monkeypatch):
    from backend.api.routes.upload import get_vector_stats, refresh_vector_stats

    cached_stats = {
        "paper_vectors": 3,
        "experiment_vectors": 4,
        "total_vectors": 7,
    }
    refresh_calls = []

    import backend.main as main_module
    monkeypatch.setattr(main_module, "get_cached_vector_stats", lambda: cached_stats)
    monkeypatch.setattr(main_module, "update_vector_stats_cache", lambda: refresh_calls.append("called"))

    stats = run_async(get_vector_stats())
    refreshed_stats = run_async(refresh_vector_stats())

    assert stats.paper_vectors == 3
    assert stats.experiment_vectors == 4
    assert stats.total_vectors == 7
    assert refreshed_stats.paper_vectors == 3
    assert refresh_calls == ["called"]


@pytest.mark.fast
@pytest.mark.api
def test_settings_model_ignores_legacy_fallback_boundary(monkeypatch):
    from backend.api.routes import settings as settings_route
    from backend.api.routes.settings import get_model_settings, update_model_settings, ModelSettings
    from backend.core.settings_manager import settings_manager

    fake_settings = {"llm_model": "gemini-2.5-flash"}

    monkeypatch.setattr(settings_manager, "get_current_model", lambda: fake_settings["llm_model"])
    monkeypatch.setattr(settings_manager, "get_provider", lambda: "google")
    monkeypatch.setattr(settings_route.env_manager, "get_provider_key", lambda name: None)

    def mock_set_current_model(model):
        fake_settings["llm_model"] = model
    monkeypatch.setattr(settings_manager, "set_current_model", mock_set_current_model)

    # Test GET
    response = run_async(get_model_settings())
    assert response.current_model == "gemini-2.5-flash"
    assert not hasattr(response, "fallback_model")
    assert "llm_fallback_model" not in ModelSettings.__fields__
    assert response.available_models == []
    assert "Google API key" in response.catalog_error

    # Test POST
    post_data = ModelSettings(llm_model="gemini-2.5-pro")
    with pytest.raises(settings_route.HTTPException) as failure:
        run_async(update_model_settings(post_data))
    assert failure.value.status_code == 400
    assert "Google API key" in failure.value.detail
    assert fake_settings["llm_model"] == "gemini-2.5-flash"


@pytest.mark.fast
@pytest.mark.api
def test_google_documented_namespaced_model_saves_and_invalid_selection_is_atomic(monkeypatch):
    from backend.api.routes import settings as settings_route
    from backend.api.routes.settings import ModelSettings, update_model_settings
    from backend.core.settings_manager import settings_manager

    state = {"provider": "google", "model": "models/gemini-2.5-pro", "selection": None}

    class Catalog:
        def contains(self, model):
            return model == "models/gemini-2.5-pro"

    monkeypatch.setattr(settings_route, "_provider_catalogs", {"google": Catalog()})
    monkeypatch.setattr(settings_route.env_manager, "get_provider_key", lambda name: "configured")
    monkeypatch.setattr(settings_manager, "get_provider", lambda: state["provider"])
    monkeypatch.setattr(settings_manager, "set_provider", lambda provider: state.__setitem__("provider", provider))
    monkeypatch.setattr(settings_manager, "set_current_model", lambda model, **kwargs: state.__setitem__("model", model))
    monkeypatch.setattr(settings_manager, "set_provider_selection", lambda provider, model: state.__setitem__("selection", (provider, model)))

    original = dict(state)
    with pytest.raises(settings_route.HTTPException) as failure:
        run_async(update_model_settings(ModelSettings(llm_provider="google", llm_model="models/gemini-unknown")))
    assert failure.value.status_code == 400
    assert state == original

    response = run_async(update_model_settings(ModelSettings(llm_provider="google", llm_model="models/gemini-2.5-pro")))
    assert response["provider"] == "google"
    assert state == {"provider": "google", "model": "models/gemini-2.5-pro", "selection": ("google", "models/gemini-2.5-pro")}


@pytest.mark.fast
@pytest.mark.api
@pytest.mark.parametrize("provider", ["openai", "google"])
def test_provider_catalog_route_is_registered_and_refresh_is_provider_scoped(monkeypatch, provider):
    from backend.api.routes import settings as settings_route
    from backend.main import app

    calls = []

    class Catalog:
        def load(self, refresh=False):
            calls.append(refresh)
            return {"models": [], "stale": False, "error": None}

    assert "/api/v1/settings/models/{provider}" in {getattr(route, "path", None) for route in app.routes}
    monkeypatch.setattr(settings_route, "_provider_catalogs", {provider: Catalog()})

    response = run_async(settings_route.get_provider_models(provider, refresh=True))

    assert response == {"provider": provider, "models": [], "stale": False, "error": None}
    assert calls == [True]


@pytest.mark.fast
@pytest.mark.api
def test_model_detection_route_is_scoped_and_returns_safe_advisory(monkeypatch):
    from backend.api.routes import settings as settings_route
    from backend.main import app

    class Catalog:
        def contains(self, model):
            return model == "gpt-4.1"

        def detect_structured_output(self, model):
            assert model == "gpt-4.1"
            return {"status": "schema_rejected", "message": "Provider rejected the structured-output request or returned invalid JSON"}

    assert "/api/v1/settings/models/{provider}/detect" in {getattr(route, "path", None) for route in app.routes}
    monkeypatch.setattr(settings_route, "_provider_catalogs", {"openai": Catalog()})
    monkeypatch.setattr(settings_route.env_manager, "get_provider_key", lambda name: "configured")
    response = run_async(settings_route.detect_provider_model("openai", settings_route.ModelDetectionRequest(model="gpt-4.1")))
    assert response == {"provider": "openai", "model": "gpt-4.1", "status": "schema_rejected", "message": "Provider rejected the structured-output request or returned invalid JSON"}


@pytest.mark.fast
@pytest.mark.api
def test_openrouter_route_returns_complete_catalog_without_pagination(monkeypatch):
    from backend.api.routes import settings as settings_route
    from backend.api.routes.settings import get_openrouter_models

    class Catalog:
        def load(self, refresh=False):
            assert refresh is False
            return {
                "models": [
                    type("Item", (), {"id": "openai/first", "name": "First", "vendor": "openai"})(),
                    type("Item", (), {"id": "other/last", "name": "Last", "vendor": "other"})(),
                ],
                "stale": False,
                "error": None,
            }

    monkeypatch.setattr(settings_route, "_openrouter_catalog", Catalog())
    result = run_async(get_openrouter_models())
    assert [item["value"] for item in result["models"]] == ["openai/first", "other/last"]
    assert "has_more" not in result
    assert "next_cursor" not in result

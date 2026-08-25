import asyncio
from io import BytesIO
import sys
from types import SimpleNamespace

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

    monkeypatch.setitem(
        sys.modules,
        "main",
        SimpleNamespace(
            get_cached_vector_stats=lambda: cached_stats,
            update_vector_stats_cache=lambda: refresh_calls.append("called"),
        ),
    )

    stats = run_async(get_vector_stats())
    refreshed_stats = run_async(refresh_vector_stats())

    assert stats.paper_vectors == 3
    assert stats.experiment_vectors == 4
    assert stats.total_vectors == 7
    assert refreshed_stats.paper_vectors == 3
    assert refresh_calls == ["called"]


@pytest.mark.fast
@pytest.mark.api
def test_settings_model_fallback_contract(monkeypatch):
    from backend.api.routes.settings import get_model_settings, update_model_settings, ModelSettings
    from backend.core.settings_manager import settings_manager

    # Mock settings manager methods to isolate the test
    fake_settings = {
        "llm_model": "gemini-2.5-flash",
        "llm_fallback_model": "gemini-3-flash-preview"
    }

    monkeypatch.setattr(settings_manager, "get_current_model", lambda: fake_settings["llm_model"])
    monkeypatch.setattr(settings_manager, "get_fallback_model", lambda: fake_settings["llm_fallback_model"])

    def mock_set_current_model(model):
        fake_settings["llm_model"] = model
    def mock_set_fallback_model(model):
        fake_settings["llm_fallback_model"] = model

    monkeypatch.setattr(settings_manager, "set_current_model", mock_set_current_model)
    monkeypatch.setattr(settings_manager, "set_fallback_model", mock_set_fallback_model)

    # Test GET
    response = run_async(get_model_settings())
    assert response.current_model == "gemini-2.5-flash"
    assert response.fallback_model == "gemini-3-flash-preview"
    assert len(response.available_models) > 0

    # Test POST
    post_data = ModelSettings(llm_model="gemini-2.5-pro", llm_fallback_model="gemini-2.5-flash")
    post_response = run_async(update_model_settings(post_data))
    assert post_response["current_model"] == "gemini-2.5-pro"
    assert post_response["fallback_model"] == "gemini-2.5-flash"
    assert fake_settings["llm_model"] == "gemini-2.5-pro"
    assert fake_settings["llm_fallback_model"] == "gemini-2.5-flash"

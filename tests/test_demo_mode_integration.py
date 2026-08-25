"""
Demo-mode integration tests for backend/api/routes/proposal.py (TODO 13.0 card b)
and backend/api/routes/mof.py (TODO 13.0 card c).

Covers the 3 proposal.py route short-circuits:
- POST /proposal/generate      -> demo_config.is_stage_demo("proposal")
- POST /proposal/revise        -> demo_config.is_stage_demo("generate_new_idea")
- POST /proposal/experiment-detail -> demo_config.is_stage_demo("experiment_detail")

And the 3 mof.py route short-circuits (all gated on the single shared
"property_prediction" stage flag, per architect's approved scope decision):
- POST /mof/cif-generator/jobs               -> pormake_runner.start_job
- POST /mof/property-predictor/jobs          -> pmtransformer_runner.start_job
- POST /mof/property-predictor/upload-jobs   -> pmtransformer_runner.start_job

For each route:
- POSITIVE case: flag ON -> route returns demo fixture data without calling
  the real LLM entrypoint (backend.services.knowledge_service.agent_answer)
  or, for mof.py, without dispatching the runner's subprocess launch
  (pormake_runner.start_job / pmtransformer_runner.start_job).
- NEGATIVE case: flag OFF -> route calls agent_answer (mocked to a stub
  success response), or dispatches the runner's start_job as before.
  Protects the "OFF still hits real API/subprocess" contract.

respx is not in requirements.txt (checked before writing this test), so we
patch `backend.services.knowledge_service.agent_answer` directly with
unittest.mock instead of intercepting HTTP at the transport layer.

mof.py note: this is not an HTTP boundary — the relevant boundary is the
runner's `start_job(run_id)` call (which spawns a background thread that
eventually calls `subprocess.Popen`). `tests/test_mof_runner_demo_guards.py`
(card a) already covers the deeper `subprocess.Popen` guard inside
`_run_worker_thread` directly. These tests assert at the route level: does
the route even call `start_job` when demo mode is on? We reuse
`mof_test_setup` from test_mof_routes.py, which already replaces
`pormake_runner`/`pmtransformer_runner` in the route module with real
instances whose `.start_job` is a MagicMock — so we can assert on that mock
directly instead of re-patching subprocess.Popen.
"""

import asyncio
import json
from unittest.mock import patch

import pytest

from backend.api.routes.proposal import (
    ExperimentDetailRequest,
    ProposalRequest,
    ProposalRevisionRequest,
    generate_experiment_detail,
    generate_proposal,
    revise_proposal,
)
from tests.test_mof_routes import mof_test_setup  # noqa: F401 (re-exported fixture)


def run_async(coro):
    return asyncio.run(coro)


def _fake_agent_answer_success(*args, **kwargs):
    """Stub for the real agent_answer LLM entrypoint used by the negative-case
    (flag OFF) tests, so those tests don't hit a real provider."""
    return {
        "answer": "Stub real-path answer.",
        "structured_proposal": {},
        "structured_experiment": {},
        "citations": [],
        "chunks": [],
        "used_model": "stub-real-model",
        "materials_list": [],
    }


# ---------------------------------------------------------------------------
# /proposal/generate
# ---------------------------------------------------------------------------

@pytest.mark.api
def test_generate_proposal_demo_on_returns_fixture_without_calling_agent_answer(demo_stage):
    demo_stage("proposal")

    with patch(
        "backend.services.knowledge_service.agent_answer"
    ) as mock_agent_answer:
        response = run_async(
            generate_proposal(ProposalRequest(research_goal="Design a Cu-BTC MOF"))
        )

    mock_agent_answer.assert_not_called()
    assert response.used_model == "demo-mode"
    assert "Cu-BTC" in response.proposal
    assert response.chemicals


@pytest.mark.api
def test_generate_proposal_demo_off_still_calls_agent_answer(demo_stage):
    demo_stage()  # all stages off

    with patch(
        "backend.api.routes.proposal.chemical_service.extract_chemicals_with_drawings",
        return_value=([], [], "Stub real-path answer."),
    ), patch(
        "backend.services.knowledge_service.agent_answer",
        side_effect=_fake_agent_answer_success,
    ) as mock_agent_answer:
        response = run_async(
            generate_proposal(ProposalRequest(research_goal="Design a Cu-BTC MOF"))
        )

    mock_agent_answer.assert_called_once()
    assert response.proposal == "Stub real-path answer."
    assert response.used_model == "stub-real-model"


# ---------------------------------------------------------------------------
# /proposal/revise
# ---------------------------------------------------------------------------

@pytest.mark.api
def test_revise_proposal_demo_on_returns_fixture_without_calling_agent_answer(demo_stage):
    demo_stage("generate_new_idea")

    with patch(
        "backend.services.knowledge_service.agent_answer"
    ) as mock_agent_answer, patch(
        "backend.core.generation.call_structured_llm"
    ) as mock_structured_llm:
        response = run_async(
            revise_proposal(
                ProposalRevisionRequest(
                    original_proposal="original",
                    user_feedback="use ethanol instead",
                    chunks=[],
                )
            )
        )

    mock_agent_answer.assert_not_called()
    mock_structured_llm.assert_not_called()
    assert response.used_model == "demo-mode"
    assert "ethanol" in response.proposal.lower()


@pytest.mark.api
def test_revise_proposal_unchecked_modes_reach_agent_and_extraction_dependencies(
    demo_stage,
):
    """Only generate-new-idea Demo governs revision and its post-answer extraction."""
    from backend.core import demo_config

    for enabled_stages in ((), ("property_prediction",)):
        demo_stage(*enabled_stages)
        downstream_guard_values = []

        def structured_llm_with_downstream_guard(*_args, **_kwargs):
            downstream_guard_values.append(demo_config.is_active_stage_demo_or_any())
            return {"is_mof_related": False}

        with patch(
            "backend.api.routes.proposal.chemical_service.extract_chemicals_with_drawings",
            return_value=([], [], "Stub real-path answer."),
        ), patch(
            "backend.services.knowledge_service.agent_answer",
            side_effect=_fake_agent_answer_success,
        ) as mock_agent_answer, patch(
            "backend.core.generation.call_structured_llm",
            side_effect=structured_llm_with_downstream_guard,
        ) as mock_structured_llm:
            response = run_async(
                revise_proposal(
                    ProposalRevisionRequest(
                        original_proposal="original",
                        user_feedback="use ethanol instead",
                        chunks=[],
                    )
                )
            )

        mock_agent_answer.assert_called_once()
        mock_structured_llm.assert_called_once()
        assert downstream_guard_values == [False]
        assert response.proposal == "Stub real-path answer."


# ---------------------------------------------------------------------------
# /proposal/experiment-detail
# ---------------------------------------------------------------------------

@pytest.mark.api
def test_generate_experiment_detail_demo_on_returns_fixture_without_calling_agent_answer(demo_stage):
    demo_stage("experiment_detail")

    with patch(
        "backend.services.knowledge_service.agent_answer"
    ) as mock_agent_answer:
        response = run_async(
            generate_experiment_detail(
                ExperimentDetailRequest(proposal="some proposal text", chunks=[])
            )
        )

    mock_agent_answer.assert_not_called()
    assert "experiment_detail" in response
    assert "Synthesis Process" in response["experiment_detail"]


@pytest.mark.api
def test_generate_experiment_detail_demo_off_still_calls_agent_answer(demo_stage):
    demo_stage()

    with patch(
        "backend.services.knowledge_service.agent_answer",
        side_effect=_fake_agent_answer_success,
    ) as mock_agent_answer:
        response = run_async(
            generate_experiment_detail(
                ExperimentDetailRequest(proposal="some proposal text", chunks=[])
            )
        )

    mock_agent_answer.assert_called_once()
    assert response["experiment_detail"] == "Stub real-path answer."


# ---------------------------------------------------------------------------
# mof.py: /cif-generator/jobs, /property-predictor/jobs, /property-predictor/upload-jobs
# ---------------------------------------------------------------------------


def _mof_routes_module():
    import backend.api.routes.mof as routes_mof

    return routes_mof


@pytest.mark.api
def test_property_predictor_demo_status_is_ready_without_private_runtime(
    client, mof_test_setup, demo_stage
):
    demo_stage("property_prediction")

    tools = client.get("/api/v1/mof/tools/status")
    profiles = client.get("/api/v1/mof/property-predictor/profiles")

    assert tools.status_code == 200
    assert tools.json()["pormake"] == {
        "ready": True,
        "installed": True,
        "version": "demo-canned",
        "error": None,
    }
    assert tools.json()["pmtransformer"] == {
        "ready": True,
        "installed": True,
        "version": "demo-canned",
        "error": None,
    }
    assert profiles.status_code == 200
    assert profiles.json()["default_profile_id"] == "demo-canned-property-profile"
    assert profiles.json()["profiles"] == [
        {
            "id": "demo-canned-property-profile",
            "label": "Demo static/canned synthetic property prediction",
            "target_property": "CO2 uptake",
            "condition": "298 K, 0.15 bar",
            "unit": "mmol/g",
            "ready": True,
        }
    ]


@pytest.mark.api
def test_property_predictor_demo_off_keeps_real_tools_and_profile_sources(
    client, mof_test_setup, demo_stage
):
    demo_stage()
    routes_mof = _mof_routes_module()

    with patch.object(routes_mof.tool_env_service, "get_status", wraps=routes_mof.tool_env_service.get_status) as get_status:
        tools = client.get("/api/v1/mof/tools/status")

    profiles = client.get("/api/v1/mof/property-predictor/profiles")

    assert tools.status_code == 200
    assert get_status.call_count == 2
    assert tools.json()["pmtransformer"]["ready"] is False
    assert profiles.status_code == 200
    assert profiles.json()["default_profile_id"] == "co2-298k-015bar"


@pytest.mark.api
def test_create_cif_generator_job_demo_on_does_not_dispatch_pormake_start_job(
    client, mof_test_setup, demo_stage
):
    demo_stage("property_prediction")

    payload = {
        "node_id": "cu-paddlewheel",
        "linker_id": "btc",
        "topology": "tbo",
        "max_results": 10,
    }
    res = client.post("/api/v1/mof/cif-generator/jobs", json=payload)

    assert res.status_code == 200
    data = res.json()
    assert data["job_id"]
    assert data["tool"] == "pormake"
    assert data["status"] == "succeeded"

    _mof_routes_module().pormake_runner.start_job.assert_not_called()

    # Run's result.json should carry the demo fixture so /runs/{id} works.
    store = mof_test_setup["store"]
    run = store.get_run(data["job_id"])
    result = json.loads((run.run_dir / "result.json").read_text(encoding="utf-8"))
    assert result["results"]
    assert all(item.get("is_demo") for item in result["results"])


@pytest.mark.api
def test_create_cif_generator_job_demo_off_still_dispatches_pormake_start_job(
    client, mof_test_setup, demo_stage
):
    demo_stage()  # all stages off

    payload = {
        "node_id": "cu-paddlewheel",
        "linker_id": "btc",
        "topology": "tbo",
        "max_results": 10,
    }
    res = client.post("/api/v1/mof/cif-generator/jobs", json=payload)

    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "queued"

    _mof_routes_module().pormake_runner.start_job.assert_called_once()


@pytest.mark.api
def test_create_property_predictor_job_demo_on_does_not_dispatch_pmtransformer_start_job(
    client, mof_test_setup, demo_stage
):
    demo_stage("property_prediction")

    files = [
        ("files", ("test1.cif", b"data_test1", "application/octet-stream")),
    ]
    data = {"profile_id": "co2-298k-015bar"}
    res = client.post(
        "/api/v1/mof/property-predictor/jobs", data=data, files=files
    )

    assert res.status_code == 200
    job_info = res.json()
    assert job_info["tool"] == "pmtransformer"
    assert job_info["status"] == "succeeded"

    _mof_routes_module().pmtransformer_runner.start_job.assert_not_called()

    store = mof_test_setup["store"]
    run = store.get_run(job_info["job_id"])
    result = json.loads((run.run_dir / "result.json").read_text(encoding="utf-8"))
    assert result["results"]
    assert all(item.get("is_demo") for item in result["results"])


@pytest.mark.api
def test_create_property_predictor_job_demo_off_still_dispatches_pmtransformer_start_job(
    client, mof_test_setup, demo_stage
):
    demo_stage()

    files = [
        ("files", ("test1.cif", b"data_test1", "application/octet-stream")),
    ]
    data = {"profile_id": "co2-298k-015bar"}
    res = client.post(
        "/api/v1/mof/property-predictor/jobs", data=data, files=files
    )

    assert res.status_code == 200
    job_info = res.json()
    assert job_info["status"] == "queued"

    _mof_routes_module().pmtransformer_runner.start_job.assert_called_once()


@pytest.mark.api
def test_create_property_predictor_upload_job_demo_on_does_not_dispatch_pmtransformer_start_job(
    client, mof_test_setup, demo_stage
):
    demo_stage("property_prediction")

    payload = {
        "profile_id": "co2-298k-015bar",
        "files": [
            {"filename": "test1.cif", "content": "data_test1"},
        ],
    }
    res = client.post("/api/v1/mof/property-predictor/upload-jobs", json=payload)

    assert res.status_code == 200
    job_info = res.json()
    assert job_info["status"] == "succeeded"

    _mof_routes_module().pmtransformer_runner.start_job.assert_not_called()

    store = mof_test_setup["store"]
    run = store.get_run(job_info["job_id"])
    result = json.loads((run.run_dir / "result.json").read_text(encoding="utf-8"))
    assert result["results"]
    assert all(item.get("is_demo") for item in result["results"])


@pytest.mark.api
def test_create_property_predictor_upload_job_demo_off_still_dispatches_pmtransformer_start_job(
    client, mof_test_setup, demo_stage
):
    demo_stage()

    payload = {
        "profile_id": "co2-298k-015bar",
        "files": [
            {"filename": "test1.cif", "content": "data_test1"},
        ],
    }
    res = client.post("/api/v1/mof/property-predictor/upload-jobs", json=payload)

    assert res.status_code == 200
    job_info = res.json()
    assert job_info["status"] == "queued"

    _mof_routes_module().pmtransformer_runner.start_job.assert_called_once()


@pytest.mark.api
def test_create_property_predictor_job_demo_on_bypasses_invalid_profile_validation(
    client, mof_test_setup, demo_stage
):
    demo_stage("property_prediction")
    files = [("files", ("test1.cif", b"data_test1", "application/octet-stream"))]
    res = client.post(
        "/api/v1/mof/property-predictor/jobs",
        data={"profile_id": "demo-profile-without-private-settings"},
        files=files,
    )

    assert res.status_code == 200
    assert res.json()["status"] == "succeeded"
    _mof_routes_module().pmtransformer_runner.start_job.assert_not_called()


@pytest.mark.api
def test_create_property_predictor_job_demo_off_rejects_invalid_profile_before_dispatch(
    client, mof_test_setup, demo_stage
):
    demo_stage()
    files = [("files", ("test1.cif", b"data_test1", "application/octet-stream"))]
    res = client.post(
        "/api/v1/mof/property-predictor/jobs",
        data={"profile_id": "demo-profile-without-private-settings"},
        files=files,
    )

    assert res.status_code == 400
    assert res.json()["detail"] == "Invalid profile ID: demo-profile-without-private-settings"
    _mof_routes_module().pmtransformer_runner.start_job.assert_not_called()


@pytest.mark.api
def test_create_property_predictor_upload_job_demo_on_bypasses_invalid_profile_validation(
    client, mof_test_setup, demo_stage
):
    demo_stage("property_prediction")
    res = client.post(
        "/api/v1/mof/property-predictor/upload-jobs",
        json={
            "profile_id": "demo-profile-without-private-settings",
            "files": [{"filename": "test1.cif", "content": "data_test1"}],
        },
    )

    assert res.status_code == 200
    assert res.json()["status"] == "succeeded"
    _mof_routes_module().pmtransformer_runner.start_job.assert_not_called()


@pytest.mark.api
def test_create_property_predictor_upload_job_demo_off_rejects_invalid_profile_before_dispatch(
    client, mof_test_setup, demo_stage
):
    demo_stage()
    res = client.post(
        "/api/v1/mof/property-predictor/upload-jobs",
        json={
            "profile_id": "demo-profile-without-private-settings",
            "files": [{"filename": "test1.cif", "content": "data_test1"}],
        },
    )

    assert res.status_code == 400
    assert res.json()["detail"] == "Invalid profile ID: demo-profile-without-private-settings"
    _mof_routes_module().pmtransformer_runner.start_job.assert_not_called()


# ---------------------------------------------------------------------------
# Cross-stage combination (TODO 13.0 card e — finale)
#
# These two tests only make sense once all 3 route-file short-circuits
# (proposal.py + mof.py) exist together. They hit every covered route in a
# single test to catch cross-stage interference (e.g. a shared client
# singleton warmed up "real" in one stage bleeding into another), and confirm
# the "OFF is correct behavior" contract holds across all 4 stage flags at
# once, not just per-route in isolation.
# ---------------------------------------------------------------------------


@pytest.mark.api
def test_all_stages_demo_on_no_real_calls_or_subprocess_dispatch_across_all_routes(
    client, mof_test_setup, demo_stage
):
    """All 4 stage flags ON simultaneously: every covered route must return its
    demo fixture without calling agent_answer or dispatching a runner's
    start_job. Asserts zero outbound calls / subprocess dispatches across the
    whole set in one test, to catch cross-stage bleed-through."""
    demo_stage("proposal", "generate_new_idea", "property_prediction", "experiment_detail")

    with patch(
        "backend.services.knowledge_service.agent_answer"
    ) as mock_agent_answer:
        proposal_response = run_async(
            generate_proposal(ProposalRequest(research_goal="Design a Cu-BTC MOF"))
        )
        revision_response = run_async(
            revise_proposal(
                ProposalRevisionRequest(
                    original_proposal="original",
                    user_feedback="use ethanol instead",
                    chunks=[],
                )
            )
        )
        experiment_detail_response = run_async(
            generate_experiment_detail(
                ExperimentDetailRequest(proposal="some proposal text", chunks=[])
            )
        )

        cif_payload = {
            "node_id": "cu-paddlewheel",
            "linker_id": "btc",
            "topology": "tbo",
            "max_results": 10,
        }
        cif_res = client.post("/api/v1/mof/cif-generator/jobs", json=cif_payload)

        pp_files = [
            ("files", ("test1.cif", b"data_test1", "application/octet-stream")),
        ]
        pp_data = {"profile_id": "co2-298k-015bar"}
        pp_res = client.post(
            "/api/v1/mof/property-predictor/jobs", data=pp_data, files=pp_files
        )

        upload_payload = {
            "profile_id": "co2-298k-015bar",
            "files": [
                {"filename": "test1.cif", "content": "data_test1"},
            ],
        }
        upload_res = client.post(
            "/api/v1/mof/property-predictor/upload-jobs", json=upload_payload
        )

    # Zero outbound LLM calls across all 3 proposal.py routes.
    mock_agent_answer.assert_not_called()
    assert proposal_response.used_model == "demo-mode"
    assert revision_response.used_model == "demo-mode"
    assert "experiment_detail" in experiment_detail_response

    # Zero subprocess/runner dispatch across all 3 mof.py routes.
    routes_mof = _mof_routes_module()
    routes_mof.pormake_runner.start_job.assert_not_called()
    routes_mof.pmtransformer_runner.start_job.assert_not_called()

    assert cif_res.status_code == 200
    assert cif_res.json()["status"] == "succeeded"
    assert pp_res.status_code == 200
    assert pp_res.json()["status"] == "succeeded"
    assert upload_res.status_code == 200
    assert upload_res.json()["status"] == "succeeded"


@pytest.mark.api
def test_all_stages_demo_off_all_routes_still_attempt_real_call_or_subprocess(
    client, mof_test_setup, demo_stage
):
    """All 4 stage flags OFF: every covered route must still attempt its real
    outbound call / subprocess launch (mocked to a stub success so no actual
    network/subprocess happens, but the mock must have been invoked for every
    route). Protects the "OFF is correct behavior" contract: a stage whose
    flag is OFF hitting the real path is CORRECT and must not regress to
    always-mocked."""
    demo_stage()  # all stages off

    with patch(
        "backend.api.routes.proposal.chemical_service.extract_chemicals_with_drawings",
        return_value=([], [], "Stub real-path answer."),
    ), patch(
        "backend.services.knowledge_service.agent_answer",
        side_effect=_fake_agent_answer_success,
    ) as mock_agent_answer:
        proposal_response = run_async(
            generate_proposal(ProposalRequest(research_goal="Design a Cu-BTC MOF"))
        )
        revision_response = run_async(
            revise_proposal(
                ProposalRevisionRequest(
                    original_proposal="original",
                    user_feedback="use ethanol instead",
                    chunks=[],
                )
            )
        )
        experiment_detail_response = run_async(
            generate_experiment_detail(
                ExperimentDetailRequest(proposal="some proposal text", chunks=[])
            )
        )

    # agent_answer must have been invoked once per proposal.py route (3 calls).
    assert mock_agent_answer.call_count == 3
    assert proposal_response.proposal == "Stub real-path answer."
    assert revision_response.proposal == "Stub real-path answer."
    assert experiment_detail_response["experiment_detail"] == "Stub real-path answer."

    cif_payload = {
        "node_id": "cu-paddlewheel",
        "linker_id": "btc",
        "topology": "tbo",
        "max_results": 10,
    }
    cif_res = client.post("/api/v1/mof/cif-generator/jobs", json=cif_payload)

    pp_files = [
        ("files", ("test1.cif", b"data_test1", "application/octet-stream")),
    ]
    pp_data = {"profile_id": "co2-298k-015bar"}
    pp_res = client.post(
        "/api/v1/mof/property-predictor/jobs", data=pp_data, files=pp_files
    )

    upload_payload = {
        "profile_id": "co2-298k-015bar",
        "files": [
            {"filename": "test1.cif", "content": "data_test1"},
        ],
    }
    upload_res = client.post(
        "/api/v1/mof/property-predictor/upload-jobs", json=upload_payload
    )

    assert cif_res.status_code == 200
    assert cif_res.json()["status"] == "queued"
    assert pp_res.status_code == 200
    assert pp_res.json()["status"] == "queued"
    assert upload_res.status_code == 200
    assert upload_res.json()["status"] == "queued"

    # Runner start_job must have been invoked for every mof.py route: once for
    # cif-generator, twice for property-predictor (jobs + upload-jobs).
    routes_mof = _mof_routes_module()
    routes_mof.pormake_runner.start_job.assert_called_once()
    assert routes_mof.pmtransformer_runner.start_job.call_count == 2


# ---------------------------------------------------------------------------
# R1 mixed-mode route matrix
# ---------------------------------------------------------------------------


@pytest.mark.api
@pytest.mark.parametrize(
    ("enabled_stage", "expected_fixture", "expected_real_modes"),
    [
        ("proposal", "proposal", {"generate new idea", "expand to experiment detail"}),
        ("generate_new_idea", "revision", {"make proposal", "expand to experiment detail"}),
        ("experiment_detail", "experiment_detail", {"make proposal", "generate new idea"}),
        (
            "property_prediction",
            "property_prediction",
            {"make proposal", "generate new idea", "expand to experiment detail"},
        ),
    ],
)
def test_each_enabled_demo_stage_returns_its_named_fixture_while_unchecked_proposal_routes_reach_agent_answer(
    client,
    mof_test_setup,
    demo_stage,
    enabled_stage,
    expected_fixture,
    expected_real_modes,
):
    """Each checkbox owns only its named fixture route in a mixed-mode request."""
    demo_stage(enabled_stage)

    with patch(
        "backend.api.routes.proposal.chemical_service.extract_chemicals_with_drawings",
        return_value=([], [], "Stub real-path answer."),
    ), patch(
        "backend.core.generation.extract_mof_from_proposal",
        return_value={"is_mof_related": False},
    ), patch(
        "backend.services.knowledge_service.agent_answer",
        side_effect=_fake_agent_answer_success,
    ) as mock_agent_answer:
        proposal_response = run_async(
            generate_proposal(ProposalRequest(research_goal="Design a Cu-BTC MOF"))
        )
        revision_response = run_async(
            revise_proposal(
                ProposalRevisionRequest(
                    original_proposal="original",
                    user_feedback="use ethanol instead",
                    chunks=[],
                )
            )
        )
        experiment_response = run_async(
            generate_experiment_detail(
                ExperimentDetailRequest(proposal="some proposal text", chunks=[])
            )
        )

    if expected_fixture == "proposal":
        assert proposal_response.used_model == "demo-mode"
    elif expected_fixture == "revision":
        assert revision_response.used_model == "demo-mode"
    elif expected_fixture == "experiment_detail":
        assert "Synthesis Process" in experiment_response["experiment_detail"]
    else:
        cif_res = client.post(
            "/api/v1/mof/cif-generator/jobs",
            json={
                "node_id": "cu-paddlewheel",
                "linker_id": "btc",
                "topology": "tbo",
                "max_results": 10,
            },
        )
        assert cif_res.status_code == 200
        assert cif_res.json()["status"] == "succeeded"
        _mof_routes_module().pormake_runner.start_job.assert_not_called()

    assert {
        call.kwargs["mode"] for call in mock_agent_answer.call_args_list
    } == expected_real_modes


@pytest.mark.api
@pytest.mark.parametrize(
    "enabled_non_property_stage",
    ["proposal", "generate_new_idea", "experiment_detail"],
)
def test_property_routes_dispatch_real_runners_when_property_is_off_and_another_stage_is_demo(
    client, mof_test_setup, demo_stage, enabled_non_property_stage
):
    """Property-off must dispatch all route runners despite another Demo checkbox."""
    demo_stage(enabled_non_property_stage)

    cif_res = client.post(
        "/api/v1/mof/cif-generator/jobs",
        json={
            "node_id": "cu-paddlewheel",
            "linker_id": "btc",
            "topology": "tbo",
            "max_results": 10,
        },
    )
    property_res = client.post(
        "/api/v1/mof/property-predictor/jobs",
        data={"profile_id": "co2-298k-015bar"},
        files=[("files", ("test1.cif", b"data_test1", "application/octet-stream"))],
    )
    upload_res = client.post(
        "/api/v1/mof/property-predictor/upload-jobs",
        json={
            "profile_id": "co2-298k-015bar",
            "files": [{"filename": "test1.cif", "content": "data_test1"}],
        },
    )

    assert cif_res.json()["status"] == "queued"
    assert property_res.json()["status"] == "queued"
    assert upload_res.json()["status"] == "queued"
    routes_mof = _mof_routes_module()
    routes_mof.pormake_runner.start_job.assert_called_once()
    assert routes_mof.pmtransformer_runner.start_job.call_count == 2


@pytest.mark.api
def test_generate_proposal_keeps_proposal_stage_context_through_post_answer_extraction(
    demo_stage,
):
    """Extraction's downstream LLM guard must see the unchecked proposal stage."""
    from backend.core import demo_config

    demo_stage("property_prediction")

    def extraction_with_downstream_guard(*_args, **_kwargs):
        assert demo_config.is_active_stage_demo_or_any() is False
        return {"is_mof_related": False}

    with patch(
        "backend.api.routes.proposal.chemical_service.extract_chemicals_with_drawings",
        return_value=([], [], "Stub real-path answer."),
    ), patch(
        "backend.core.generation.extract_mof_from_proposal",
        side_effect=extraction_with_downstream_guard,
    ), patch(
        "backend.services.knowledge_service.agent_answer",
        side_effect=_fake_agent_answer_success,
    ) as mock_agent_answer:
        response = run_async(
            generate_proposal(ProposalRequest(research_goal="Design a Cu-BTC MOF"))
        )

    mock_agent_answer.assert_called_once()
    assert response.proposal == "Stub real-path answer."

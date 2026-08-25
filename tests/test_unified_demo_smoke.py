"""Application-real unified Demo ON/OFF smoke tests."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.core.settings_manager import settings_manager
from tests.test_demo_cross_stage_handoffs import (
    deterministic_mof_runner,  # pyright: ignore[reportUnusedImport] (pytest fixture re-export)
    proposal_resolver_double,  # pyright: ignore[reportUnusedImport] (pytest fixture re-export)
)
from tests.test_mof_routes import mof_test_setup  # pyright: ignore[reportUnusedImport] (pytest fixture re-export)


@pytest.fixture
def isolated_app_client(tmp_path, monkeypatch):
    """Use a temporary persisted Settings API record and no stage env overrides."""
    from backend.main import app

    for env_var in (
        "DEMO_MOCK_PROPOSAL",
        "DEMO_MOCK_GENERATE_NEW_IDEA",
        "DEMO_MOCK_PROPERTY_PREDICTION",
        "DEMO_MOCK_EXPERIMENT_DETAIL",
    ):
        monkeypatch.delenv(env_var, raising=False)
    monkeypatch.setattr(settings_manager, "settings_file", tmp_path / "settings.json")
    monkeypatch.setattr(settings_manager, "_current_settings", {})

    with TestClient(app) as test_client:
        yield test_client


@pytest.mark.e2e
@pytest.mark.api
def test_unified_demo_on_reaches_all_application_stages_without_real_dispatch(
    isolated_app_client,
    mof_test_setup,
    deterministic_mof_runner,
    proposal_resolver_double,
):
    """Settings API ON drives the full application flow using packaged fixtures."""
    client = isolated_app_client
    from backend.api.routes import mof as routes_mof

    settings_response = client.post("/api/v1/settings/demo-mode", json={"enabled": True})
    assert settings_response.status_code == 200, settings_response.text
    assert settings_response.json() == {
        "status": "success",
        "enabled": True,
        "mock_proposal": True,
        "mock_property_prediction": True,
        "mock_generate_new_idea": True,
        "mock_experiment_detail": True,
    }
    assert client.get("/api/v1/settings/demo-mode").json()["enabled"] is True

    with patch("backend.services.knowledge_service.agent_answer") as mock_agent_answer, patch(
        "backend.api.routes.mof.subprocess.run"
    ) as mock_subprocess_run:
        tools_response = client.get("/api/v1/mof/tools/status")
        profiles_response = client.get("/api/v1/mof/property-predictor/profiles")
        proposal_response = client.post(
            "/api/v1/proposal/generate",
            json={"research_goal": "Design a copper linker framework"},
        )
        assert proposal_response.status_code == 200, proposal_response.text
        proposal_payload = proposal_response.json()
        structured = proposal_payload["structured_proposal"]

        translate_response = client.post(
            "/api/v1/mof/proposal/translate",
            json={
                "metal_element": structured["mof_metal_element"],
                "linker_smiles": structured["mof_linker_smiles"],
            },
        )
        assert translate_response.status_code == 200, translate_response.text
        translated = translate_response.json()

        generator_response = client.post(
            "/api/v1/mof/cif-generator/jobs",
            json={
                "node_id": translated["node_id"],
                "linker_id": translated["linker_id"],
                "max_results": 10,
            },
        )
        assert generator_response.status_code == 200, generator_response.text
        generator_run_id = generator_response.json()["job_id"]
        generator_status = client.get(f"/api/v1/mof/runs/{generator_run_id}")
        assert generator_status.status_code == 200, generator_status.text
        generator_payload = generator_status.json()
        assert generator_payload["status"] == "succeeded", generator_payload
        assert len(generator_payload["artifacts"]) == 10

        generator_run = mof_test_setup["store"].get_run(generator_run_id)
        generator_manifest = json.loads(
            (generator_run.run_dir / "artifacts.json").read_text(encoding="utf-8")
        )
        generator_artifact_ids = [
            item["artifact_id"] for item in generator_manifest["artifacts"]
        ]
        generator_result = json.loads(
            (generator_run.run_dir / "result.json").read_text(encoding="utf-8")
        )
        assert generator_result["demo_manifest"]["fixture_count"] == 10
        assert len(generator_result["results"]) == 10
        assert all(item["is_demo"] for item in generator_result["results"])
        assert generator_artifact_ids == [
            item["artifact_id"] for item in generator_result["results"]
        ]

        property_response = client.post(
            "/api/v1/mof/property-predictor/jobs",
            data={
                "profile_id": "demo-canned-property-profile",
                "generator_run_id": generator_run_id,
                "artifact_ids": json.dumps(generator_artifact_ids),
            },
        )
        assert property_response.status_code == 200, property_response.text
        property_run_id = property_response.json()["job_id"]
        property_status = client.get(f"/api/v1/mof/runs/{property_run_id}")
        assert property_status.status_code == 200, property_status.text
        assert property_status.json()["status"] == "succeeded"
        property_run = mof_test_setup["store"].get_run(property_run_id)
        property_request = json.loads(
            (property_run.run_dir / "request.json").read_text(encoding="utf-8")
        )
        assert property_request["generator_run_id"] == generator_run_id
        assert property_request["artifact_ids"] == generator_artifact_ids
        property_result = json.loads(
            (property_run.run_dir / "result.json").read_text(encoding="utf-8")
        )
        assert len(property_result["results"]) == 10
        assert all(item["is_demo"] for item in property_result["results"])

        xrd_run_ids = []
        for artifact in generator_payload["artifacts"]:
            xrd_response = client.post(
                "/api/v1/mof/xrd/calculate",
                data={
                    "generator_run_id": generator_run_id,
                    "artifact_id": artifact["artifact_id"],
                },
            )
            assert xrd_response.status_code == 200, xrd_response.text
            assert xrd_response.json()["peaks"]
            latest_xrd = [
                run for run in mof_test_setup["store"].list_runs() if run.tool == "xrd"
            ]
            assert latest_xrd
            xrd_run_ids.append(latest_xrd[0].run_id)

        revision_response = client.post(
            "/api/v1/proposal/revise",
            json={
                "original_proposal": proposal_payload["proposal"],
                "user_feedback": "Use ethanol for purification.",
                "chunks": proposal_payload["chunks"],
            },
        )
        assert revision_response.status_code == 200, revision_response.text
        revision_payload = revision_response.json()

        experiment_response = client.post(
            "/api/v1/proposal/experiment-detail",
            json={
                "proposal": revision_payload["proposal"],
                "chunks": revision_payload["chunks"],
            },
        )
        assert experiment_response.status_code == 200, experiment_response.text

    assert tools_response.status_code == 200, tools_response.text
    assert tools_response.json()["pmtransformer"]["version"] == "demo-canned"
    assert profiles_response.status_code == 200, profiles_response.text
    assert profiles_response.json()["default_profile_id"] == "demo-canned-property-profile"
    assert proposal_payload["used_model"] == "demo-mode"
    assert revision_payload["used_model"] == "demo-mode"
    assert "experiment_detail" in experiment_response.json()
    assert len(xrd_run_ids) == 10
    assert len(set(xrd_run_ids)) == 10
    for xrd_run_id in xrd_run_ids:
        xrd_run = mof_test_setup["store"].get_run(xrd_run_id)
        assert xrd_run.status == "succeeded"
        xrd_request = json.loads(
            (xrd_run.run_dir / "request.json").read_text(encoding="utf-8")
        )
        assert xrd_request["generator_run_id"] == generator_run_id
        assert xrd_request["artifact_id"] in generator_artifact_ids
        xrd_result = json.loads(
            (xrd_run.run_dir / "result.json").read_text(encoding="utf-8")
        )
        assert xrd_result["results"] == [
            {"artifact_id": "xrd_pattern", "filename": "xrd_pattern.json"}
        ]

    mock_agent_answer.assert_not_called()
    routes_mof.pormake_runner.start_job.assert_not_called()
    routes_mof.pmtransformer_runner.start_job.assert_not_called()
    mock_subprocess_run.assert_not_called()
    assert deterministic_mof_runner["calls"] == {"generator": [], "property": []}
    assert proposal_resolver_double[0]["metal"] == structured["mof_metal_element"]
    assert proposal_resolver_double[0]["linker"] == structured["mof_linker_smiles"]


@pytest.mark.e2e
@pytest.mark.api
def test_unified_demo_off_keeps_real_route_dispatch_reachable(
    isolated_app_client,
    mof_test_setup,
    deterministic_mof_runner,
):
    """Settings API OFF preserves real route paths while all heavy calls are local stubs."""
    client = isolated_app_client
    from backend.api.routes import mof as routes_mof

    settings_response = client.post("/api/v1/settings/demo-mode", json={"enabled": False})
    assert settings_response.status_code == 200, settings_response.text
    assert all(value is False for key, value in settings_response.json().items() if key != "status")

    with patch(
        "backend.services.knowledge_service.agent_answer",
        side_effect=lambda *args, **kwargs: _off_agent_result(kwargs.get("mode", "real")),
    ) as mock_agent_answer, patch(
        "backend.api.routes.proposal.chemical_service.extract_chemicals_with_drawings",
        return_value=([], [], "real-path proposal"),
    ), patch(
        "backend.api.routes.proposal.chemical_metadata_extractor",
        return_value=([], [], ""),
    ), patch(
        "backend.core.generation.extract_mof_from_proposal",
        return_value={"is_mof_related": False},
    ):
        tools_response = client.get("/api/v1/mof/tools/status")
        profiles_response = client.get("/api/v1/mof/property-predictor/profiles")
        proposal_response = client.post(
            "/api/v1/proposal/generate",
            json={"research_goal": "Design a copper linker framework"},
        )
        assert proposal_response.status_code == 200, proposal_response.text
        revision_response = client.post(
            "/api/v1/proposal/revise",
            json={
                "original_proposal": proposal_response.json()["proposal"],
                "user_feedback": "Change the washing solvent.",
                "chunks": proposal_response.json()["chunks"],
            },
        )
        assert revision_response.status_code == 200, revision_response.text
        experiment_response = client.post(
            "/api/v1/proposal/experiment-detail",
            json={
                "proposal": revision_response.json()["proposal"],
                "chunks": revision_response.json()["chunks"],
            },
        )
        assert experiment_response.status_code == 200, experiment_response.text

        invalid_profile_response = client.post(
            "/api/v1/mof/property-predictor/jobs",
            data={"profile_id": "not-a-real-profile"},
            files={"files": ("input.cif", b"data_test", "application/octet-stream")},
        )
        assert invalid_profile_response.status_code == 400
        assert "not-a-real-profile" in invalid_profile_response.json()["detail"]

        generator_response = client.post(
            "/api/v1/mof/cif-generator/jobs",
            json={
                "node_id": "cu-paddlewheel",
                "linker_id": "btc",
                "max_results": 2,
            },
        )
        assert generator_response.status_code == 200, generator_response.text
        generator_run_id = generator_response.json()["job_id"]
        assert generator_response.json()["status"] == "queued"
        generator_status = client.get(f"/api/v1/mof/runs/{generator_run_id}")
        assert generator_status.json()["status"] == "succeeded"

        generator_artifact = generator_status.json()["artifacts"][0]
        with patch(
            "backend.api.routes.mof.run_xrd_calculation",
            return_value=_off_xrd_result(),
        ) as mock_xrd_calculation:
            xrd_response = client.post(
                "/api/v1/mof/xrd/calculate",
                data={
                    "generator_run_id": generator_run_id,
                    "artifact_id": generator_artifact["artifact_id"],
                },
            )
        assert xrd_response.status_code == 200, xrd_response.text
        assert xrd_response.json()["space_group"] == "P1"
        mock_xrd_calculation.assert_called_once()

        property_response = client.post(
            "/api/v1/mof/property-predictor/jobs",
            data={"profile_id": "co2-298k-015bar"},
            files={"files": ("input.cif", b"data_test", "application/octet-stream")},
        )
        assert property_response.status_code == 200, property_response.text
        property_run_id = property_response.json()["job_id"]
        assert property_response.json()["status"] == "queued"
        property_status = client.get(f"/api/v1/mof/runs/{property_run_id}")
        assert property_status.json()["status"] == "succeeded"

    assert tools_response.status_code == 200, tools_response.text
    assert tools_response.json()["pmtransformer"]["version"] != "demo-canned"
    assert profiles_response.status_code == 200, profiles_response.text
    assert profiles_response.json()["default_profile_id"] == "co2-298k-015bar"
    assert proposal_response.json()["used_model"] == "deterministic-real-path"
    assert revision_response.json()["used_model"] != "demo-mode"
    assert experiment_response.json()["experiment_detail"] == "real-path: expand to experiment detail"
    assert mock_agent_answer.call_count == 3
    assert routes_mof.pormake_runner.start_job.call_count == 1
    assert routes_mof.pmtransformer_runner.start_job.call_count == 1
    assert deterministic_mof_runner["calls"]["generator"]
    assert deterministic_mof_runner["calls"]["property"]

    generator_run = mof_test_setup["store"].get_run(generator_run_id)
    generator_result = json.loads(
        (generator_run.run_dir / "result.json").read_text(encoding="utf-8")
    )
    assert all("is_demo" not in item for item in generator_result["results"])
    property_run = mof_test_setup["store"].get_run(property_run_id)
    property_result = json.loads(
        (property_run.run_dir / "result.json").read_text(encoding="utf-8")
    )
    assert all("is_demo" not in item for item in property_result["results"])


def _off_agent_result(mode: str) -> dict:
    if mode == "expand to experiment detail":
        answer = "real-path: expand to experiment detail"
    elif mode == "generate new idea":
        answer = "real-path: generate new idea"
    else:
        answer = "real-path: make proposal"
    return {
        "answer": answer,
        "structured_proposal": {},
        "structured_experiment": {},
        "citations": [],
        "chunks": [],
        "used_model": "deterministic-real-path",
        "materials_list": [],
    }


def _off_xrd_result() -> dict:
    return {
        "space_group": "P1",
        "space_group_number": 1,
        "crystal_system": "triclinic",
        "wavelength": 1.54184,
        "num_peaks": 1,
        "peaks": [
            {"two_theta": 10.0, "intensity": 100.0, "hkl": "(100)", "d_spacing": 8.8}
        ],
        "profile": {"two_theta": [10.0], "intensity": [100.0]},
    }

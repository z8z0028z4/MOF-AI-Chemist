"""Application-real Demo handoff tests using deterministic local engine doubles."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from tests.test_mof_routes import mof_test_setup  # noqa: F401 (fixture re-export)


@pytest.fixture
def deterministic_mof_runner(mof_test_setup):
    """Replace route-level engine starts with synchronous run/artifact writers."""
    from backend.api.routes import mof as routes_mof

    store = mof_test_setup["store"]
    artifact_service = mof_test_setup["artifacts"]
    calls = {"generator": [], "property": []}

    def fake_generator_start(run_id: str) -> None:
        run = store.get_run(run_id)
        request = json.loads((run.run_dir / "request.json").read_text(encoding="utf-8"))
        calls["generator"].append({"run_id": run_id, "request": request})

        output_dir = run.run_dir / "generated_cifs"
        output_dir.mkdir(parents=True, exist_ok=True)
        manifest = []
        results = []
        for index, topology in enumerate(("hbk", "mfj"), start=1):
            filename = f"handoff_structure_{index}.cif"
            artifact_id = f"handoff-cif-{index}"
            (output_dir / filename).write_text(
                f"data_handoff_{index}\n_data_topology {topology}\n",
                encoding="utf-8",
            )
            manifest.append(
                {
                    "artifact_id": artifact_id,
                    "relative_path": f"generated_cifs/{filename}",
                    "source": "deterministic-test-runner",
                }
            )
            results.append(
                {
                    "artifact_id": artifact_id,
                    "filename": filename,
                    "topology": topology,
                    "node_catalog_id": request["node_id"],
                    "linker_catalog_id": request["linker_id"],
                }
            )

        artifact_service.write_manifest(run_id, manifest)
        (run.run_dir / "result.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "tool": "pormake",
                    "status": "succeeded",
                    "results": results,
                    "failures": [],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        store.update_status(run_id, "succeeded", progress=1.0, message="deterministic generator complete")

    def fake_property_start(run_id: str) -> None:
        run = store.get_run(run_id)
        request = json.loads((run.run_dir / "request.json").read_text(encoding="utf-8"))
        calls["property"].append({"run_id": run_id, "request": request})

        output_dir = run.run_dir / "predictions"
        output_dir.mkdir(parents=True, exist_ok=True)
        manifest = []
        results = []
        artifact_ids = request.get("artifact_ids")
        if artifact_ids is None:
            artifact_ids = [
                f"uploaded-{filename.rsplit('.', 1)[0]}"
                for filename in request.get("uploaded_files", [])
            ]
        for artifact_id in artifact_ids:
            filename = f"{artifact_id}.json"
            (output_dir / filename).write_text(
                json.dumps(
                    {
                        "artifact_id": artifact_id,
                        "generator_run_id": request.get("generator_run_id"),
                        "predicted_value": 1.234,
                    }
                ),
                encoding="utf-8",
            )
            manifest.append(
                {
                    "artifact_id": artifact_id,
                    "relative_path": f"predictions/{filename}",
                    "source": "deterministic-test-runner",
                }
            )
            results.append(
                {
                    "artifact_id": artifact_id,
                    "filename": filename,
                    "predicted_value": 1.234,
                    "unit": "mmol/g",
                    "target_property": "CO2 uptake",
                    "condition": "298 K, 0.15 bar",
                    "generator_run_id": request.get("generator_run_id"),
                }
            )

        artifact_service.write_manifest(run_id, manifest)
        (run.run_dir / "result.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "tool": "pmtransformer",
                    "status": "succeeded",
                    "results": results,
                    "failures": [],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        store.update_status(run_id, "succeeded", progress=1.0, message="deterministic property complete")

    routes_mof.pormake_runner.start_job.side_effect = fake_generator_start
    routes_mof.pmtransformer_runner.start_job.side_effect = fake_property_start
    yield {"calls": calls, **mof_test_setup}


@pytest.fixture
def proposal_resolver_double(monkeypatch):
    """Resolve actual Proposal structured fields without a PORMAKE runtime."""
    from backend.api.routes import mof as routes_mof

    calls = []

    def resolve_pormake_candidates(*, metal, linker, tool_env_service, max_candidates):
        calls.append(
            {
                "metal": metal,
                "linker": linker,
                "max_candidates": max_candidates,
                "tool_env_service": tool_env_service,
            }
        )
        return {
            "status": "success",
            "metal_element": metal,
            "linker_smiles": linker,
            "linker_identity": {"source": "proposal-structured-output"},
            "candidates": [
                {
                    "metal_id": "cu-paddlewheel",
                    "metal_element": metal,
                    "organic_id": "btc",
                    "organic_role": "linker",
                    "organic_coordination_number": 3,
                    "assembly_pattern": "metal-linker",
                    "match_kind": "deterministic-test-match",
                    "confidence": 1.0,
                    "covered_atom_fraction": 1.0,
                    "node_id": "cu-paddlewheel",
                    "linker_id": "btc",
                    "auto_generatable": True,
                    "compatible_topologies": ["hbk", "mfj"],
                }
            ],
            "scaffold_suggestions": [],
            "diagnostics": {"source": "deterministic-test-resolver"},
            "message": "resolved from Proposal structured output",
        }

    monkeypatch.setattr(routes_mof, "resolve_pormake_candidates", resolve_pormake_candidates)
    return calls


@pytest.mark.handoff
@pytest.mark.api
def test_mock_proposal_feeds_real_property_run_with_generator_artifact_handoff(
    client,
    demo_stage,
    mof_test_setup,
    deterministic_mof_runner,
    proposal_resolver_double,
):
    """Proposal fixture fields drive resolution, generation, and prediction IDs."""
    demo_stage("proposal")

    with patch("backend.services.knowledge_service.agent_answer") as mock_agent_answer:
        proposal_response = client.post(
            "/api/v1/proposal/generate",
            json={"research_goal": "Design a copper linker framework"},
        )

    assert proposal_response.status_code == 200
    proposal_payload = proposal_response.json()
    structured = proposal_payload["structured_proposal"]
    assert structured["mof_metal_element"]
    assert structured["mof_linker_smiles"]
    mock_agent_answer.assert_not_called()

    translate_response = client.post(
        "/api/v1/mof/proposal/translate",
        json={
            "metal_element": structured["mof_metal_element"],
            "linker_smiles": structured["mof_linker_smiles"],
        },
    )
    assert translate_response.status_code == 200, translate_response.text
    translated = translate_response.json()
    assert proposal_resolver_double[0]["metal"] == structured["mof_metal_element"]
    assert proposal_resolver_double[0]["linker"] == structured["mof_linker_smiles"]
    assert translated["node_id"]
    assert translated["linker_id"]

    generator_response = client.post(
        "/api/v1/mof/cif-generator/jobs",
        json={
            "node_id": translated["node_id"],
            "linker_id": translated["linker_id"],
            "max_results": 2,
        },
    )
    assert generator_response.status_code == 200, generator_response.text
    generator_run_id = generator_response.json()["job_id"]
    generator_status = client.get(f"/api/v1/mof/jobs/{generator_run_id}")
    assert generator_status.status_code == 200
    assert generator_status.json()["status"] == "succeeded"

    generator_run_status = client.get(f"/api/v1/mof/runs/{generator_run_id}")
    assert generator_run_status.status_code == 200, generator_run_status.text
    generator_run_payload = generator_run_status.json()
    assert generator_run_payload["status"] == "succeeded", generator_run_payload
    generator_run = mof_test_setup["store"].get_run(generator_run_id)
    manifest = json.loads((generator_run.run_dir / "artifacts.json").read_text(encoding="utf-8"))
    generator_artifact_ids = [item["artifact_id"] for item in manifest["artifacts"]]
    assert generator_artifact_ids == [item["artifact_id"] for item in generator_run_payload["artifacts"]]
    assert deterministic_mof_runner["calls"]["generator"] == [
        {
            "run_id": generator_run_id,
            "request": {
                "node_id": translated["node_id"],
                "linker_id": translated["linker_id"],
                "topology": None,
                "max_results": 2,
            },
        }
    ]

    property_response = client.post(
        "/api/v1/mof/property-predictor/jobs",
        data={
            "profile_id": "co2-298k-015bar",
            "generator_run_id": generator_run_id,
            "artifact_ids": json.dumps(generator_artifact_ids),
        },
    )
    assert property_response.status_code == 200, property_response.text
    property_run_id = property_response.json()["job_id"]
    property_status = client.get(f"/api/v1/mof/jobs/{property_run_id}")
    assert property_status.status_code == 200
    assert property_status.json()["status"] == "succeeded"

    property_run = mof_test_setup["store"].get_run(property_run_id)
    property_request = json.loads((property_run.run_dir / "request.json").read_text(encoding="utf-8"))
    assert property_request["generator_run_id"] == generator_run_id
    assert property_request["artifact_ids"] == generator_artifact_ids
    assert deterministic_mof_runner["calls"]["property"][0]["request"] == property_request

    property_run_status = client.get(f"/api/v1/mof/runs/{property_run_id}")
    assert property_run_status.status_code == 200, property_run_status.text
    property_run_payload = property_run_status.json()
    assert property_run_payload["status"] == "succeeded", property_run_payload
    property_artifact_ids = [item["artifact_id"] for item in property_run_payload["artifacts"]]
    assert set(property_artifact_ids) == set(generator_artifact_ids), (
        f"property run {property_run_id} must reference generator run "
        f"{generator_run_id}; generator manifest={manifest}; "
        f"property status={property_run_payload}"
    )
    property_result = json.loads((property_run.run_dir / "result.json").read_text(encoding="utf-8"))
    assert {item["generator_run_id"] for item in property_result["results"]} == {generator_run_id}


def _real_path_agent_result(answer: str) -> dict:
    return {
        "answer": answer,
        "structured_proposal": {},
        "citations": [],
        "chunks": [],
        "used_model": "deterministic-real-path",
        "materials_list": [],
    }


@pytest.mark.handoff
@pytest.mark.api
def test_mock_proposal_text_is_consumed_by_real_revision_and_next_stage(
    client,
    demo_stage,
):
    """Revision receives the actual generated Proposal text and exposes it onward."""
    demo_stage("proposal")
    proposal_response = client.post(
        "/api/v1/proposal/generate",
        json={"research_goal": "Design a copper linker framework"},
    )
    assert proposal_response.status_code == 200, proposal_response.text
    original_proposal = proposal_response.json()["proposal"]
    feedback = "Use ethanol for purification and retain the copper linker framework."
    calls = []

    def revision_agent_answer(*args, **kwargs):
        calls.append({"args": args, "kwargs": kwargs})
        if kwargs.get("mode") == "expand to experiment detail":
            return _real_path_agent_result("Experiment detail based on the revised proposal.")
        return _real_path_agent_result("Revised proposal with ethanol purification.")

    with patch(
        "backend.services.knowledge_service.agent_answer",
        side_effect=revision_agent_answer,
    ), patch(
        "backend.core.generation.extract_mof_from_proposal",
        return_value={"is_mof_related": False},
    ), patch(
        "backend.api.routes.proposal.chemical_metadata_extractor",
        return_value=([], [], ""),
    ):
        revision_response = client.post(
            "/api/v1/proposal/revise",
            json={
                "original_proposal": original_proposal,
                "user_feedback": feedback,
                "chunks": proposal_response.json()["chunks"],
            },
        )

        assert revision_response.status_code == 200, revision_response.text
        revision_payload = revision_response.json()
        next_stage_response = client.post(
            "/api/v1/proposal/experiment-detail",
            json={
                "proposal": revision_payload["proposal"],
                "chunks": revision_payload["chunks"],
            },
        )

    assert len(calls) == 2
    assert calls[0]["args"][0] == feedback
    assert calls[0]["kwargs"]["proposal"] == original_proposal
    assert revision_payload["proposal"] == "Revised proposal with ethanol purification."
    assert isinstance(revision_payload["structured_proposal"], dict)
    assert next_stage_response.status_code == 200, next_stage_response.text
    assert calls[1]["kwargs"]["proposal"] == revision_payload["proposal"]
    assert calls[1]["kwargs"]["proposal"] != original_proposal


@pytest.mark.handoff
@pytest.mark.api
def test_mock_revision_is_latest_content_consumed_by_real_experiment_detail(
    client,
    demo_stage,
):
    """Experiment Detail consumes the Proposal response returned by Demo Revision."""
    demo_stage("proposal", "generate_new_idea")
    proposal_response = client.post(
        "/api/v1/proposal/generate",
        json={"research_goal": "Design a copper linker framework"},
    )
    assert proposal_response.status_code == 200, proposal_response.text
    original_proposal = proposal_response.json()["proposal"]

    revision_response = client.post(
        "/api/v1/proposal/revise",
        json={
            "original_proposal": original_proposal,
            "user_feedback": "Use ethanol for purification.",
            "chunks": proposal_response.json()["chunks"],
        },
    )
    assert revision_response.status_code == 200, revision_response.text
    revision_payload = revision_response.json()
    latest_proposal = revision_payload["proposal"]
    assert latest_proposal != original_proposal

    calls = []

    def experiment_agent_answer(*args, **kwargs):
        calls.append({"args": args, "kwargs": kwargs})
        return _real_path_agent_result("Experiment detail generated from the latest revision.")

    with patch(
        "backend.services.knowledge_service.agent_answer",
        side_effect=experiment_agent_answer,
    ):
        experiment_response = client.post(
            "/api/v1/proposal/experiment-detail",
            json={
                "proposal": latest_proposal,
                "chunks": revision_payload["chunks"],
            },
        )

    assert experiment_response.status_code == 200, experiment_response.text
    assert experiment_response.json()["experiment_detail"] == (
        "Experiment detail generated from the latest revision."
    )
    assert len(calls) == 1
    assert calls[0]["kwargs"]["proposal"] == latest_proposal
    assert calls[0]["kwargs"]["proposal"] != original_proposal

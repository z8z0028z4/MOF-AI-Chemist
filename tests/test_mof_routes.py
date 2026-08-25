import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.api.models.mof_models import JobStatusResponse, RunStatusResponse
from backend.services.mof import (
    MofArtifactService,
    MofRunStore,
    ToolEnvService,
)


@pytest.fixture
def mof_test_setup(tmp_path):
    # Setup temp settings file
    checkpoint = tmp_path / "best.ckpt"
    checkpoint.write_bytes(b"private")
    settings_file = tmp_path / "private_settings.json"
    settings_file.write_text(
        json.dumps(
            {
                "default_profile_id": "co2-298k-015bar",
                "h_mof_cif_root": str(tmp_path),
                "profiles": [
                    {
                        "id": "co2-298k-015bar",
                        "label": "CO2 uptake - 298 K, 0.15 bar",
                        "checkpoint_path": str(checkpoint),
                        "downstream": "private_downstream",
                        "target_property": "CO2 uptake",
                        "condition": "298 K, 0.15 bar",
                        "unit": "mmol/g",
                        "normalization": {"mean": 1.23, "std": 0.45},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    temp_store = MofRunStore(tmp_path)
    temp_artifacts = MofArtifactService(temp_store)
    temp_env = ToolEnvService(tmp_path)

    from unittest.mock import MagicMock
    from backend.services.mof import PormakeRunner, PmTransformerRunner
    temp_pormake_runner = PormakeRunner(temp_store, temp_artifacts, temp_env)
    temp_pmtransformer_runner = PmTransformerRunner(temp_store, temp_artifacts, temp_env)
    temp_pormake_runner.start_job = MagicMock()
    temp_pormake_runner.cancel_job = MagicMock(return_value=True)
    temp_pmtransformer_runner.start_job = MagicMock()
    temp_pmtransformer_runner.cancel_job = MagicMock(return_value=True)

    import backend.api.routes.mof as routes_mof

    with patch.object(routes_mof, "run_store", temp_store), patch.object(
        routes_mof, "artifact_service", temp_artifacts
    ), patch.object(routes_mof, "tool_env_service", temp_env), patch.object(
        routes_mof, "pormake_runner", temp_pormake_runner
    ), patch.object(
        routes_mof, "pmtransformer_runner", temp_pmtransformer_runner
    ), patch(
        "backend.services.mof_settings_service.get_mof_private_settings_path",
        return_value=settings_file,
    ), patch(
        "backend.api.routes.mof.get_mof_private_settings_path",
        return_value=settings_file,
    ):
        yield {
            "tmp_path": tmp_path,
            "store": temp_store,
            "artifacts": temp_artifacts,
            "env_service": temp_env,
            "settings_file": settings_file,
            "checkpoint": checkpoint,
        }


@pytest.mark.fast
@pytest.mark.unit
def test_get_private_settings_status(client, mof_test_setup):
    res = client.get("/api/v1/mof/private-settings/status")
    assert res.status_code == 200
    data = res.json()
    assert data["settings_file_exists"] is True
    assert data["ready_for_real_run"] is True
    assert data["display"]["unit"] == "mmol/g"
    assert data["redacted"] is True


@pytest.mark.fast
@pytest.mark.unit
def test_get_tools_status(client, mof_test_setup):
    res = client.get("/api/v1/mof/tools/status")
    assert res.status_code == 200
    data = res.json()
    assert "pormake" in data
    assert "pmtransformer" in data
    assert data["pormake"]["installed"] is False
    assert data["pmtransformer"]["installed"] is False


@pytest.mark.fast
@pytest.mark.unit
def test_tool_install_trigger_and_status(client, mof_test_setup):
    # Trigger install for pormake
    res = client.post("/api/v1/mof/tools/pormake/install")
    assert res.status_code == 200
    assert res.json()["status"] == "installing"

    # Check install status
    res = client.get("/api/v1/mof/tools/pormake/install-status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ("installing", "success", "failed")
    assert data["progress"] > 0


@pytest.mark.fast
@pytest.mark.unit
def test_get_cif_generator_catalog(client, mof_test_setup):
    res = client.get("/api/v1/mof/cif-generator/catalog")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 2
    assert data[0]["id"] == "cu-paddlewheel"
    assert data[1]["id"] == "btc"


@pytest.mark.fast
@pytest.mark.unit
def test_get_cif_generator_topologies(client, mof_test_setup):
    res = client.get("/api/v1/mof/cif-generator/topologies")
    assert res.status_code == 200
    # Should work via fallback to source
    data = res.json()
    assert isinstance(data, list)
    assert len(data) > 0


@pytest.mark.fast
@pytest.mark.unit
def test_create_cif_generator_job_valid(client, mof_test_setup):
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
    assert data["status"] == "queued"
    assert data["tool"] == "pormake"


@pytest.mark.api
def test_demo_cif_generator_accepts_pormake_fixture_codes(
    client, mof_test_setup, demo_stage
):
    demo_stage("property_prediction")
    payload = {
        "node_id": "N409",
        "linker_id": "N10",
        "max_results": 10,
    }

    response = client.post("/api/v1/mof/cif-generator/jobs", json=payload)

    assert response.status_code == 200
    assert response.json()["status"] == "succeeded"
    status = client.get(f"/api/v1/mof/runs/{response.json()['job_id']}")
    assert status.status_code == 200
    assert len(status.json()["artifacts"]) == 10

    import backend.api.routes.mof as routes_mof

    routes_mof.pormake_runner.start_job.assert_not_called()


@pytest.mark.fast
@pytest.mark.unit
def test_create_cif_generator_job_invalid_catalog_id(client, mof_test_setup):
    payload = {
        "node_id": "cu-paddlewheel",
        "linker_id": "invalid-linker",
    }
    res = client.post("/api/v1/mof/cif-generator/jobs", json=payload)
    assert res.status_code == 400
    assert "Invalid building block ID" in res.json()["detail"]


@pytest.mark.fast
@pytest.mark.unit
def test_create_cif_generator_job_incompatible_topology(client, mof_test_setup):
    payload = {
        "node_id": "cu-paddlewheel",
        "linker_id": "btc",
        "topology": "invalid_topology",
    }
    res = client.post("/api/v1/mof/cif-generator/jobs", json=payload)
    assert res.status_code == 400
    assert "not compatible" in res.json()["detail"]


@pytest.mark.fast
@pytest.mark.unit
def test_get_property_predictor_profiles(client, mof_test_setup):
    res = client.get("/api/v1/mof/property-predictor/profiles")
    assert res.status_code == 200
    data = res.json()
    assert data["default_profile_id"] == "co2-298k-015bar"
    assert len(data["profiles"]) == 1
    p = data["profiles"][0]
    assert p["id"] == "co2-298k-015bar"
    assert p["ready"] is True
    # Verify no private leakage
    assert "checkpoint_path" not in p
    assert "normalization" not in p
    assert "downstream" not in p


@pytest.mark.fast
@pytest.mark.unit
def test_create_property_predictor_job_files(client, mof_test_setup):
    files = [
        (
            "files",
            (
                "test1.cif",
                b"data_test1",
                "application/octet-stream",
            ),
        ),
        (
            "files",
            (
                "test2.cif",
                b"data_test2",
                "application/octet-stream",
            ),
        ),
    ]
    data = {"profile_id": "co2-298k-015bar"}
    res = client.post(
        "/api/v1/mof/property-predictor/jobs",
        data=data,
        files=files,
    )
    assert res.status_code == 200
    job_info = res.json()
    assert job_info["job_id"]
    assert job_info["tool"] == "pmtransformer"
    assert job_info["status"] == "queued"

    # Verify files are stored in run input_cifs directory
    run_id = job_info["job_id"]
    store = mof_test_setup["store"]
    run = store.get_run(run_id)
    input_dir = run.run_dir / "input_cifs"
    assert (input_dir / "test1.cif").is_file()
    assert (input_dir / "test2.cif").is_file()
    assert (input_dir / "test1.cif").read_text() == "data_test1"


@pytest.mark.fast
@pytest.mark.unit
def test_create_property_predictor_json_upload_job(client, mof_test_setup):
    payload = {
        "profile_id": "co2-298k-015bar",
        "files": [
            {"filename": "test1.cif", "content": "data_test1"},
            {"filename": "test2.cif", "content": "data_test2"},
        ],
    }

    res = client.post(
        "/api/v1/mof/property-predictor/upload-jobs",
        json=payload,
    )

    assert res.status_code == 200
    job_info = res.json()
    run = mof_test_setup["store"].get_run(job_info["job_id"])
    input_dir = run.run_dir / "input_cifs"
    assert (input_dir / "test1.cif").read_text() == "data_test1"
    assert (input_dir / "test2.cif").read_text() == "data_test2"


@pytest.mark.fast
@pytest.mark.unit
def test_create_property_predictor_job_generator_run(client, mof_test_setup):
    # First create a generator run
    payload = {
        "node_id": "cu-paddlewheel",
        "linker_id": "btc",
        "topology": "tbo",
    }
    gen_res = client.post("/api/v1/mof/cif-generator/jobs", json=payload)
    gen_run_id = gen_res.json()["job_id"]

    # Now create prediction run referencing generator run
    data = {
        "profile_id": "co2-298k-015bar",
        "generator_run_id": gen_run_id,
        "artifact_ids": "cif-001,cif-002",
    }
    res = client.post("/api/v1/mof/property-predictor/jobs", data=data)
    assert res.status_code == 200
    job_info = res.json()
    assert job_info["job_id"]
    assert job_info["status"] == "queued"


@pytest.mark.fast
@pytest.mark.unit
def test_job_cancel(client, mof_test_setup):
    payload = {
        "node_id": "cu-paddlewheel",
        "linker_id": "btc",
    }
    res = client.post("/api/v1/mof/cif-generator/jobs", json=payload)
    job_id = res.json()["job_id"]

    cancel_res = client.post(f"/api/v1/mof/jobs/{job_id}/cancel")
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "cancelled"


@pytest.mark.fast
@pytest.mark.unit
def test_get_run_status_and_artifacts(client, mof_test_setup):
    store = mof_test_setup["store"]
    artifacts_svc = mof_test_setup["artifacts"]

    run = store.create_run("pormake", {})

    # Simulate success and write results
    store.update_status(run.run_id, "succeeded")
    generated_dir = run.run_dir / "generated_cifs"
    generated_dir.mkdir()
    cif_file = generated_dir / "tbo_N409_N10.cif"
    cif_file.write_text("cif_content", encoding="utf-8")

    artifacts_svc.write_manifest(
        run.run_id,
        [
            {
                "artifact_id": "cif-001",
                "relative_path": "generated_cifs/tbo_N409_N10.cif",
            }
        ],
    )

    # Write result.json
    result_path = run.run_dir / "result.json"
    result_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "tool": "pormake",
                "status": "succeeded",
                "results": [
                    {
                        "artifact_id": "cif-001",
                        "filename": "tbo_N409_N10.cif",
                        "topology": "tbo",
                        "max_rmsd": 0.12,
                        "node_catalog_id": "cu-paddlewheel",
                        "linker_catalog_id": "btc",
                    }
                ],
                "failures": [],
            }
        ),
        encoding="utf-8",
    )

    # Fetch status
    res = client.get(f"/api/v1/mof/runs/{run.run_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "succeeded"
    assert len(data["artifacts"]) == 1
    art = data["artifacts"][0]
    assert art["artifact_id"] == "cif-001"
    assert art["filename"] == "tbo_N409_N10.cif"
    assert art["relative_path"] == "generated_cifs/tbo_N409_N10.cif"
    assert art["max_rmsd"] == 0.12

    # Download artifact
    download_res = client.get(
        f"/api/v1/mof/runs/{run.run_id}/artifacts/cif-001"
    )
    assert download_res.status_code == 200
    assert download_res.text == "cif_content"

    # Download artifact text
    text_res = client.get(
        f"/api/v1/mof/runs/{run.run_id}/artifacts/cif-001/text"
    )
    assert text_res.status_code == 200
    assert text_res.text == "cif_content"


@pytest.mark.fast
@pytest.mark.unit
def test_list_runs_route(client, mof_test_setup):
    store = mof_test_setup["store"]
    store.create_run("pormake", {"node_id": "cu-paddlewheel"})
    store.create_run("pmtransformer", {})

    res = client.get("/api/v1/mof/runs")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 2
    assert data[0]["tool"] == "pmtransformer"
    assert data[1]["tool"] == "pormake"


@pytest.mark.fast
@pytest.mark.unit
def test_browse_checkpoints_route(client, mof_test_setup):
    tmp_path = mof_test_setup["tmp_path"]

    # Create a dummy .ckpt file
    ckpt_file = tmp_path / "model.ckpt"
    ckpt_file.write_bytes(b"some binary data for checkpoint")

    # Create a subfolder
    sub_dir = tmp_path / "subfolder"
    sub_dir.mkdir()

    # Mock ALLOWED_ROOTS inside the route to allow tmp_path
    import backend.api.routes.mof as routes_mof
    with patch.object(routes_mof, "ALLOWED_ROOTS", [tmp_path.resolve()]):
        res = client.get(f"/api/v1/mof/property-predictor/browse-ckpts?path={tmp_path}")
        assert res.status_code == 200
        data = res.json()
        assert data["current_path"] == str(tmp_path)
        assert len(data["dirs"]) == 1
        assert len(data["files"]) == 2
        filenames = [f["name"] for f in data["files"]]
        assert "model.ckpt" in filenames
        assert "best.ckpt" in filenames


@pytest.mark.fast
@pytest.mark.unit
def test_verify_checkpoint_route_not_exist(client, mof_test_setup):
    res = client.post(
        "/api/v1/mof/property-predictor/verify-ckpt",
        json={"checkpoint_path": "/nonexistent/path.ckpt"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is False
    assert "不存在" in data["error"]


@pytest.mark.fast
@pytest.mark.unit
def test_verify_checkpoint_route_invalid_ext(client, mof_test_setup):
    tmp_path = mof_test_setup["tmp_path"]
    txt_file = tmp_path / "not_a_ckpt.txt"
    txt_file.write_text("hello")

    res = client.post(
        "/api/v1/mof/property-predictor/verify-ckpt",
        json={"checkpoint_path": str(txt_file)},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is False
    assert "ckpt 格式" in data["error"]


@pytest.mark.fast
@pytest.mark.unit
def test_verify_checkpoint_route_too_small(client, mof_test_setup):
    tmp_path = mof_test_setup["tmp_path"]
    ckpt_file = tmp_path / "too_small.ckpt"
    ckpt_file.write_bytes(b"small")

    res = client.post(
        "/api/v1/mof/property-predictor/verify-ckpt",
        json={"checkpoint_path": str(ckpt_file)},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is False
    assert "檔案大小過小" in data["error"]


@pytest.mark.fast
@pytest.mark.unit
def test_create_property_predictor_job_custom_ckpt_params(client, mof_test_setup):
    # Create a mock checkpoint file that is large enough
    tmp_path = mof_test_setup["tmp_path"]
    ckpt_file = tmp_path / "valid_size.ckpt"
    ckpt_file.write_bytes(b"0" * 1024 * 1024)

    files = [
        (
            "files",
            (
                "test1.cif",
                b"data_test1",
                "application/octet-stream",
            ),
        ),
    ]
    data = {
        "profile_id": "co2-298k-015bar",
        "custom_checkpoint_path": str(ckpt_file),
        "custom_target_property": "N2 uptake",
        "custom_condition": "77 K, 1 bar",
        "custom_unit": "mmol/g",
        "custom_mean": "1.23",
        "custom_std": "4.56",
    }
    res = client.post(
        "/api/v1/mof/property-predictor/jobs",
        data=data,
        files=files,
    )
    assert res.status_code == 200
    job_info = res.json()
    assert job_info["job_id"]
    assert job_info["tool"] == "pmtransformer"
    assert job_info["status"] == "queued"

    # Verify parameters are saved to the run request payload
    run_id = job_info["job_id"]
    store = mof_test_setup["store"]
    run = store.get_run(run_id)
    req_path = run.run_dir / "request.json"
    assert req_path.is_file()
    req = json.loads(req_path.read_text(encoding="utf-8"))
    assert req["custom_checkpoint_path"] == str(ckpt_file)
    assert req["custom_target_property"] == "N2 uptake"
    assert req["custom_condition"] == "77 K, 1 bar"
    assert req["custom_unit"] == "mmol/g"
    assert req["custom_mean"] == 1.23
    assert req["custom_std"] == 4.56


@pytest.mark.fast
@pytest.mark.unit
def test_proposal_translate_route(client, mof_test_setup):
    mock_resolved = {
        "status": "success",
        "metal_element": "Cu",
        "linker_smiles": "O=C(O)c1cc(C(=O)O)cc(C(=O)O)c1",
        "linker_identity": {"source": "smiles"},
        "candidates": [
            {
                "metal_id": "N409",
                "metal_element": "Cu",
                "organic_id": "N10",
                "organic_role": "N",
                "organic_coordination_number": 3,
                "assembly_pattern": "N(metal)-N(organic)",
                "match_kind": "exact",
                "confidence": 0.98,
                "covered_atom_fraction": 1.0,
                "uncovered_elements": {},
                "evidence": ["fixture"],
                "warnings": [],
                "node_id": "N409",
                "linker_id": "N10",
                "auto_generatable": True,
                "compatible_topologies": ["tbo", "bor"],
            }
        ],
        "scaffold_suggestions": [],
        "message": "Found 1 exact PORMAKE candidate(s).",
    }

    with patch(
        "backend.api.routes.mof.resolve_pormake_candidates",
        return_value=mock_resolved,
    ):
        res = client.post(
            "/api/v1/mof/proposal/translate",
            json={
                "metal_element": "Cu",
                "linker_smiles": "C1=C(C=C(C=C1C(=O)O)C(=O)O)C(=O)O",
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert data["node_id"] == "N409"
        assert data["linker_id"] == "N10"
        assert "tbo" in data["compatible_topologies"]
        assert data["candidates"][0]["match_kind"] == "exact"


@pytest.mark.fast
@pytest.mark.unit
def test_cif_generator_resolve_route(client, mof_test_setup):
    mock_resolved = {
        "status": "scaffold_only",
        "metal_element": "Zr",
        "linker_smiles": "Cc1cc(C(=O)O)ccc1C(=O)O",
        "linker_identity": {"source": "smiles"},
        "candidates": [],
        "scaffold_suggestions": [],
        "message": "Only scaffold matches were found.",
    }
    with patch(
        "backend.api.routes.mof.resolve_pormake_candidates",
        return_value=mock_resolved,
    ):
        res = client.post(
            "/api/v1/mof/cif-generator/resolve",
            json={"metal": "zirconium", "linker": "2-methylterephthalic acid"},
        )

    assert res.status_code == 200
    assert res.json()["status"] == "scaffold_only"
    assert res.json()["candidates"] == []


@pytest.mark.fast
@pytest.mark.unit
def test_proposal_run_screening_route(client, mof_test_setup):
    res = client.post(
        "/api/v1/mof/proposal/run-screening",
        json={
            "node_id": "cu-paddlewheel",
            "linker_id": "btc",
            "topology": "tbo",
            "max_results": 3,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["generator_job_id"]
    assert data["node_id"] == "cu-paddlewheel"
    assert data["linker_id"] == "btc"
    assert data["topology"] == "tbo"

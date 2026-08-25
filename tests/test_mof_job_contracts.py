import json
from pathlib import Path

import pytest


@pytest.mark.fast
@pytest.mark.unit
def test_run_store_creates_managed_run_and_persists_status(tmp_path):
    from backend.services.mof.run_store import MofRunStore

    store = MofRunStore(tmp_path)
    run = store.create_run(tool="pormake", request={"node_id": "cu-paddlewheel"})

    assert run.run_id
    assert run.tool == "pormake"
    assert run.status == "queued"
    assert run.run_dir.parent == tmp_path / "runs"
    assert json.loads((run.run_dir / "request.json").read_text()) == {
        "node_id": "cu-paddlewheel"
    }

    updated = store.update_status(run.run_id, "running", progress=0.5, message="Building")
    loaded = store.get_run(run.run_id)

    assert updated.status == "running"
    assert loaded.status == "running"
    assert loaded.progress == 0.5
    assert loaded.message == "Building"


@pytest.mark.fast
@pytest.mark.unit
def test_run_store_rejects_invalid_status_transition(tmp_path):
    from backend.services.mof.run_store import InvalidRunTransition, MofRunStore

    store = MofRunStore(tmp_path)
    run = store.create_run(tool="pmtransformer", request={})
    store.update_status(run.run_id, "succeeded", progress=1)

    with pytest.raises(InvalidRunTransition):
        store.update_status(run.run_id, "running")


@pytest.mark.fast
@pytest.mark.unit
def test_artifact_service_only_resolves_manifested_files_inside_run(tmp_path):
    from backend.services.mof.artifact_service import (
        ArtifactNotFound,
        MofArtifactService,
    )
    from backend.services.mof.run_store import MofRunStore

    store = MofRunStore(tmp_path)
    run = store.create_run(tool="pormake", request={})
    generated = run.run_dir / "generated_cifs"
    generated.mkdir()
    cif_path = generated / "tbo_N409_N10.cif"
    cif_path.write_text("data_test", encoding="utf-8")

    artifacts = MofArtifactService(store)
    artifacts.write_manifest(
        run.run_id,
        [{"artifact_id": "cif-001", "relative_path": "generated_cifs/tbo_N409_N10.cif"}],
    )

    assert artifacts.resolve(run.run_id, "cif-001") == cif_path.resolve()

    with pytest.raises(ArtifactNotFound):
        artifacts.resolve(run.run_id, "../../settings.json")


@pytest.mark.fast
@pytest.mark.unit
def test_artifact_service_rejects_manifest_path_traversal(tmp_path):
    from backend.services.mof.artifact_service import InvalidArtifactManifest, MofArtifactService
    from backend.services.mof.run_store import MofRunStore

    store = MofRunStore(tmp_path)
    run = store.create_run(tool="pormake", request={})
    artifacts = MofArtifactService(store)

    with pytest.raises(InvalidArtifactManifest):
        artifacts.write_manifest(
            run.run_id,
            [{"artifact_id": "secret", "relative_path": "../../settings.json"}],
        )


@pytest.mark.fast
@pytest.mark.unit
def test_private_model_profiles_return_only_safe_fields(tmp_path):
    from backend.services.mof.pmtransformer_profiles import load_safe_model_profiles

    checkpoint = tmp_path / "best.ckpt"
    checkpoint.write_bytes(b"private")
    settings = tmp_path / "private_settings.json"
    settings.write_text(
        json.dumps(
            {
                "default_profile_id": "co2-298k-015bar",
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

    result = load_safe_model_profiles(settings)
    payload = json.dumps(result)

    assert result["default_profile_id"] == "co2-298k-015bar"
    assert result["profiles"] == [
        {
            "id": "co2-298k-015bar",
            "label": "CO2 uptake - 298 K, 0.15 bar",
            "target_property": "CO2 uptake",
            "condition": "298 K, 0.15 bar",
            "unit": "mmol/g",
            "ready": True,
        }
    ]
    assert str(checkpoint) not in payload
    assert "private_downstream" not in payload
    assert "1.23" not in payload
    assert "0.45" not in payload


@pytest.mark.fast
@pytest.mark.unit
def test_pormake_catalog_exposes_verified_friendly_labels_only():
    from backend.services.mof.pormake_catalog import get_public_catalog

    catalog = get_public_catalog()

    assert catalog == [
        {
            "id": "cu-paddlewheel",
            "label": "Cu paddlewheel",
            "role": "node",
            "coordination_number": 4,
        },
        {
            "id": "btc",
            "label": "BTC (benzene-1,3,5-tricarboxylate)",
            "role": "node",
            "coordination_number": 3,
        },
    ]
    assert all(not item["id"].startswith(("N", "E")) for item in catalog)


@pytest.mark.fast
@pytest.mark.unit
def test_run_store_lists_runs(tmp_path):
    from backend.services.mof.run_store import MofRunStore

    store = MofRunStore(tmp_path)
    run1 = store.create_run(tool="pormake", request={"node_id": "cu-paddlewheel"})
    run2 = store.create_run(tool="pmtransformer", request={})

    runs = store.list_runs()
    assert len(runs) == 2
    # Sorted by updated_at descending, so run2 (created second) should be first
    assert runs[0].run_id == run2.run_id
    assert runs[1].run_id == run1.run_id

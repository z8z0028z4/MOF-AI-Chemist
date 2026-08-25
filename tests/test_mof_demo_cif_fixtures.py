"""Contract tests for repository-owned synthetic CIFs in the MOF Demo path."""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import subprocess
import sys
import types
from unittest.mock import MagicMock

import pytest


def _load_mof_routes_module(monkeypatch):
    """Load this route source without unrelated optional route imports."""
    resolver = types.ModuleType("backend.services.mof.pormake_resolver")
    resolver.LinkerResolutionError = ValueError
    resolver.resolve_pormake_candidates = MagicMock()
    monkeypatch.setitem(sys.modules, resolver.__name__, resolver)
    route_path = Path(__file__).parents[1] / "backend/api/routes/mof.py"
    spec = importlib.util.spec_from_file_location("mof_routes_under_test", route_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.mark.fast
@pytest.mark.unit
def test_pormake_cif_fixture_inventory_is_exactly_ten_with_provenance_headers():
    from backend.services.demo_service import synthetic_cif_fixture_paths

    fixtures = synthetic_cif_fixture_paths()

    assert len(fixtures) == 10
    assert len({path.name for path in fixtures}) == 10
    assert all(path.suffix == ".cif" and path.is_file() for path in fixtures)
    assert all(path.name.startswith("synthetic_demo_") for path in fixtures)
    assert all(
        "PORMAKE-generated N409 + N10 Demo fixture" in path.read_text(encoding="utf-8")
        for path in fixtures
    )


@pytest.mark.fast
@pytest.mark.unit
def test_pormake_cif_fixtures_have_exact_ordered_topology_provenance():
    from backend.services.demo_service import synthetic_cif_fixture_paths

    expected = ["hbk", "mfj", "tfz", "ffc", "lil", "iab", "tfo", "sty", "tfn", "maw"]
    assert [path.read_text(encoding="utf-8").splitlines()[0].split("topology=")[1].split(";")[0] for path in synthetic_cif_fixture_paths()] == expected


@pytest.mark.fast
@pytest.mark.unit
def test_synthetic_cif_fixtures_are_explicitly_git_indexed_and_not_ignored():
    repo_root = Path(__file__).parents[1]
    fixtures = sorted((repo_root / "tests/test_data/mof/demo_cifs").glob("synthetic_demo_*.cif"))

    assert len(fixtures) == 10
    indexed_ignore_file = subprocess.run(
        ["git", "show", ":.gitignore"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert "!tests/test_data/mof/demo_cifs/*.cif" in indexed_ignore_file
    for fixture in fixtures:
        relative_path = fixture.relative_to(repo_root)
        # Prove the .gitignore negation is the winning pattern for these
        # fixtures: `git check-ignore --no-index --verbose` prints the rule
        # that actually excludes/re-includes the path. In this linked
        # worktree the plain rc semantics are environment-sensitive (git
        # 2.43 check-ignore rc differs between shell and subprocess), so
        # assert the negation rule itself is what git reports in effect.
        # Explicit indexing is covered by git ls-files --error-unmatch below.
        ignored = subprocess.run(
            ["git", "check-ignore", "--no-index", "--verbose", "--", str(relative_path)],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
        )
        assert "!tests/test_data/mof/demo_cifs/*.cif" in ignored.stdout
        subprocess.run(
            ["git", "ls-files", "--error-unmatch", "--", str(relative_path)],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )


@pytest.mark.fast
@pytest.mark.unit
def test_cif_generator_renders_pormake_demo_provenance_and_previews_downloaded_bytes():
    component = (
        Path(__file__).parents[1]
        / "frontend/src/components/mof/CifGeneratorTab.jsx"
    ).read_text(encoding="utf-8")

    assert "isPormakeDemo &&" in component
    assert "precomputed PORMAKE-generated N409 + N10 fixtures" in component
    assert "const cifText = await getRunArtifactText(currentJobId, artifactId)" in component
    assert "onPreviewCif(cifText, filename)" in component


@pytest.mark.fast
@pytest.mark.unit
def test_materialized_synthetic_cif_artifacts_preserve_packaged_bytes(tmp_path):
    from backend.services.demo_service import (
        materialize_synthetic_cif_demo_artifacts,
        synthetic_cif_fixture_paths,
    )
    from backend.services.mof.artifact_service import MofArtifactService
    from backend.services.mof.run_store import MofRunStore

    store = MofRunStore(tmp_path)
    run = store.create_run(tool="pormake", request={})
    artifacts, results = materialize_synthetic_cif_demo_artifacts(run.run_dir)
    artifact_service = MofArtifactService(store)
    artifact_service.write_manifest(run.run_id, artifacts)

    source_by_name = {path.name: path for path in synthetic_cif_fixture_paths()}
    assert len(artifacts) == len(results) == len(source_by_name) == 10
    assert all(item["fixture_kind"] == "pormake-precomputed-demo" for item in artifacts)
    assert [item["topology"] for item in results] == ["hbk", "mfj", "tfz", "ffc", "lil", "iab", "tfo", "sty", "tfn", "maw"]
    assert all(item["is_demo"] is True for item in results)
    for artifact in artifacts:
        resolved = artifact_service.resolve(run.run_id, artifact["artifact_id"])
        source = source_by_name[resolved.name]
        assert resolved.read_bytes() == source.read_bytes()
        assert artifact["sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()


@pytest.mark.fast
@pytest.mark.unit
def test_cif_generator_demo_status_preview_and_download_expose_packaged_bytes(
    monkeypatch, tmp_path, demo_stage
):
    from backend.api.models.mof_models import CifGeneratorJobRequest
    from backend.services.mof.artifact_service import MofArtifactService
    from backend.services.mof.run_store import MofRunStore

    routes_mof = _load_mof_routes_module(monkeypatch)
    demo_stage("property_prediction")
    store = MofRunStore(tmp_path)
    artifacts = MofArtifactService(store)
    runner = MagicMock()
    monkeypatch.setattr(routes_mof, "run_store", store)
    monkeypatch.setattr(routes_mof, "artifact_service", artifacts)
    monkeypatch.setattr(routes_mof, "pormake_runner", runner)
    monkeypatch.setattr(routes_mof, "resolve_catalog_id", lambda value: {"id": value})
    monkeypatch.setattr(routes_mof.tool_env_service, "get_compatible_topologies", lambda *_: [])

    response = routes_mof.create_cif_generator_job(
        CifGeneratorJobRequest(node_id="synthetic-node", linker_id="synthetic-linker")
    )
    status = routes_mof.get_run_status(response.job_id)

    assert response.status == "succeeded"
    assert "10 PORMAKE-generated N409 + N10 CIF fixtures" in response.message
    assert len(status.artifacts) == 10
    runner.start_job.assert_not_called()

    first = status.artifacts[0]
    preview = routes_mof.get_run_artifact_text(response.job_id, first.artifact_id)
    download = routes_mof.get_run_artifact(response.job_id, first.artifact_id)
    source = next(
        path
        for path in __import__("backend.services.demo_service", fromlist=["synthetic_cif_fixture_paths"])
        .synthetic_cif_fixture_paths()
        if path.name == first.filename
    )
    assert preview.body == source.read_bytes()
    assert Path(download.path).read_bytes() == source.read_bytes()


@pytest.mark.fast
@pytest.mark.unit
def test_cif_generator_demo_off_preserves_runner_dispatch(monkeypatch, tmp_path, demo_stage):
    from backend.api.models.mof_models import CifGeneratorJobRequest
    from backend.services.mof.artifact_service import MofArtifactService
    from backend.services.mof.run_store import MofRunStore

    routes_mof = _load_mof_routes_module(monkeypatch)
    demo_stage()
    store = MofRunStore(tmp_path)
    runner = MagicMock()
    monkeypatch.setattr(routes_mof, "run_store", store)
    monkeypatch.setattr(routes_mof, "artifact_service", MofArtifactService(store))
    monkeypatch.setattr(routes_mof, "pormake_runner", runner)
    monkeypatch.setattr(routes_mof, "resolve_catalog_id", lambda value: {"id": value})
    monkeypatch.setattr(routes_mof.tool_env_service, "get_compatible_topologies", lambda *_: [])

    response = routes_mof.create_cif_generator_job(
        CifGeneratorJobRequest(node_id="synthetic-node", linker_id="synthetic-linker")
    )

    assert response.status == "queued"
    runner.start_job.assert_called_once_with(response.job_id)

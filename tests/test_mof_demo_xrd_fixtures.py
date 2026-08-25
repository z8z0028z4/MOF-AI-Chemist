"""TDD contract for offline, authentic XRD fixtures in the MOF Demo path."""

from __future__ import annotations

import hashlib
import importlib.util
import math
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import sys
import types


def _load_mof_routes_module(monkeypatch):
    resolver = types.ModuleType("backend.services.mof.pormake_resolver")
    resolver.LinkerResolutionError = ValueError
    resolver.resolve_pormake_candidates = MagicMock()
    monkeypatch.setitem(sys.modules, resolver.__name__, resolver)
    route_path = Path(__file__).parents[1] / "backend/api/routes/mof.py"
    spec = importlib.util.spec_from_file_location("mof_routes_xrd_under_test", route_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.mark.fast
@pytest.mark.unit
def test_pormake_demo_xrd_manifest_has_exact_cif_to_pattern_bijection():
    """Each owned synthetic CIF must map to one hashed, precomputed pattern."""
    from backend.services.demo_service import get_synthetic_demo_xrd_manifest

    manifest = get_synthetic_demo_xrd_manifest()
    entries = manifest["entries"]

    assert manifest["ownership"] == "repository-owned PORMAKE database-generated Demo data"
    assert len(entries) == 10
    assert len({entry["cif_filename"] for entry in entries}) == 10
    assert len({entry["xrd_filename"] for entry in entries}) == 10

    repo_root = Path(__file__).parents[1]
    for entry in entries:
        cif_path = repo_root / "tests/test_data/mof/demo_cifs" / entry["cif_filename"]
        xrd_path = repo_root / "backend/demo_fixtures" / entry["xrd_filename"]
        assert cif_path.is_file()
        assert xrd_path.is_file()
        assert entry["source_cif_sha256"] == hashlib.sha256(cif_path.read_bytes()).hexdigest()
        assert entry["building_blocks"] == {"node": "N409", "node_cn": 4, "linker": "N10", "linker_cn": 3}
        assert entry["topology"] in {"hbk", "mfj", "tfz", "ffc", "lil", "iab", "tfo", "sty", "tfn", "maw"}
        assert entry["construction_rationale"]
        assert entry["validity_evidence"]
        assert entry["generator"]["representation"] == "Gaussian-broadened powder XRD"


@pytest.mark.fast
@pytest.mark.unit
def test_synthetic_demo_xrd_loader_is_deterministic_and_finite():
    """The fixture loader returns a detached finite pattern for every CIF."""
    from backend.services.demo_service import (
        get_synthetic_demo_xrd_manifest,
        get_synthetic_demo_xrd_pattern,
    )

    manifest = get_synthetic_demo_xrd_manifest()
    for entry in manifest["entries"]:
        pattern = get_synthetic_demo_xrd_pattern(entry["cif_filename"])
        repeated = get_synthetic_demo_xrd_pattern(entry["cif_filename"])

        assert pattern == repeated
        assert pattern is not repeated
        assert pattern["num_peaks"] == len(pattern["peaks"])
        assert len(pattern["profile"]["two_theta"]) == len(pattern["profile"]["intensity"])
        assert pattern["profile"]["two_theta"]
        numeric_values = [
            pattern["wavelength"],
            *pattern["profile"]["two_theta"],
            *pattern["profile"]["intensity"],
            *(value for peak in pattern["peaks"] for value in (peak["two_theta"], peak["intensity"], peak["d_spacing"])),
        ]
        assert all(math.isfinite(value) for value in numeric_values)


@pytest.mark.fast
@pytest.mark.unit
def test_synthetic_demo_xrd_loader_rejects_non_fixture_filename():
    """Demo lookup cannot select arbitrary user or runtime CIF paths."""
    from backend.services.demo_service import get_synthetic_demo_xrd_pattern

    with pytest.raises(KeyError):
        get_synthetic_demo_xrd_pattern("uploaded_structure.cif")


@pytest.mark.fast
@pytest.mark.unit
def test_demo_xrd_route_uses_matching_stored_pattern_without_calculator(
    monkeypatch, tmp_path, demo_stage
):
    """Demo XRD accepts exact packaged CIF bytes and never launches a calculator."""
    from backend.services.mof.artifact_service import MofArtifactService
    from backend.services.mof.run_store import MofRunStore

    routes_mof = _load_mof_routes_module(monkeypatch)
    demo_stage("property_prediction")
    store = MofRunStore(tmp_path)
    monkeypatch.setattr(routes_mof, "run_store", store)
    monkeypatch.setattr(routes_mof, "artifact_service", MofArtifactService(store))
    runner = MagicMock()
    monkeypatch.setattr(routes_mof, "run_xrd_calculation", runner)
    cif_path = Path(__file__).parents[1] / "tests/test_data/mof/demo_cifs/synthetic_demo_01.cif"

    class UploadedCif:
        filename = cif_path.name
        async def read(self):
            return cif_path.read_bytes()

    response = __import__('asyncio').run(
        routes_mof.calculate_xrd(
            file=UploadedCif(),
            cif_path=None,
            generator_run_id=None,
            artifact_id=None,
            wavelength=1.5406,
            max_two_theta=80.0,
            fwhm=0.1,
        )
    )

    assert response == __import__(
        "backend.services.demo_service", fromlist=["get_synthetic_demo_xrd_pattern"]
    ).get_synthetic_demo_xrd_pattern(cif_path.name)
    runner.assert_not_called()


@pytest.mark.fast
@pytest.mark.unit
def test_pormake_demo_manifest_does_not_contain_old_caf2_or_canned_markers():
    manifest = (Path(__file__).parents[1] / "backend/demo_fixtures/synthetic_demo_xrd_manifest.json").read_text(encoding="utf-8")
    assert "CaF2" not in manifest
    assert "canned" not in manifest.lower()

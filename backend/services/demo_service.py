"""
Demo-mode fixture loader (TODO 13.0).
=======================================

Thin, pure JSON-fixture loader for backend-side demo mode responses. No I/O
beyond reading the bundled JSON files under backend/demo_fixtures/, cached at
module load. Response shapes mirror the frontend's existing localStorage-based
demo fixtures in frontend/src/services/proposalDemo.js, so the frontend
rendering path stays compatible once these are wired into the route handlers.

Functions accept the same arguments the real routes take (research_goal,
feedback, proposal_text) for interface parity, but the returned fixtures are
deterministic canned data — inputs are accepted, not used to vary the output.
This keeps demo responses stable/reproducible across calls, which is the
point of demo mode.

v1 simplification (documented, approved by architect plan): experiment-detail
always returns the methanol fixture variant, regardless of proposal_text.
Ethanol-variant selection (mirroring the frontend's `/ethanol/i.test(...)`
heuristic) is an explicit follow-up, not implemented here.
"""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

_FIXTURES_DIR = Path(__file__).resolve().parents[1] / "demo_fixtures"
_SYNTHETIC_CIF_FIXTURES_DIR = (
    Path(__file__).resolve().parents[2] / "tests" / "test_data" / "mof" / "demo_cifs"
)


@lru_cache(maxsize=None)
def _load_fixture(name: str) -> Dict[str, Any]:
    path = _FIXTURES_DIR / name
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_proposal_response(research_goal: str = "") -> Dict[str, Any]:
    """Returns the demo fixture for /proposal/generate.

    research_goal is accepted for interface parity with the real route but
    does not vary the (deterministic) fixture output.
    """
    fixture = json.loads(json.dumps(_load_fixture("proposal.json")))
    fixture["proposal"] = fixture["proposal"].replace(
        "{research_goal}",
        "Develop a green, high-crystallinity Cu-BTC MOF via solvent-free grinding.",
    )
    return fixture


def get_revision_response(feedback: str = "") -> Dict[str, Any]:
    """Returns the demo fixture for /proposal/revise.

    feedback is accepted for interface parity with the real route but does
    not vary the (deterministic) fixture output.
    """
    fixture = json.loads(json.dumps(_load_fixture("generate_new_idea.json")))
    fixture["proposal"] = fixture["proposal"].replace(
        "{feedback}",
        "suggest an alternative solvent for methanol, for a less toxic synthesis route.",
    )
    return fixture


def get_property_prediction_response() -> Dict[str, Any]:
    """Returns the demo fixture covering both /cif-generator/jobs and
    /property-predictor/jobs+upload-jobs (single shared flag, per approved scope)."""
    return _load_fixture("property_prediction.json")


def synthetic_cif_fixture_paths() -> list[Path]:
    """Return the ordered repository-owned PORMAKE Demo CIF fixtures."""
    fixtures = sorted(_SYNTHETIC_CIF_FIXTURES_DIR.glob("synthetic_demo_*.cif"))
    if len(fixtures) != 10:
        raise RuntimeError("Demo mode requires exactly 10 PORMAKE CIF fixtures")
    return fixtures


def materialize_synthetic_cif_demo_artifacts(
    run_dir: Path,
) -> tuple[list[Dict[str, Any]], list[Dict[str, Any]]]:
    """Copy packaged PORMAKE CIF bytes into a run and describe its artifacts.

    This does no chemistry computation or external I/O. Existing artifact APIs
    then serve only the copied, precomputed PORMAKE fixture bytes.
    """
    output_dir = run_dir / "generated_cifs"
    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts: list[Dict[str, Any]] = []
    results: list[Dict[str, Any]] = []
    manifest_entries = get_synthetic_demo_xrd_manifest()["entries"]
    entries_by_filename = {entry["cif_filename"]: entry for entry in manifest_entries}
    for index, source in enumerate(synthetic_cif_fixture_paths(), start=1):
        entry = entries_by_filename[source.name]
        payload = source.read_bytes()
        destination = output_dir / source.name
        destination.write_bytes(payload)
        artifact_id = f"demo-cif-{index:02d}"
        artifacts.append(
            {
                "artifact_id": artifact_id,
                "relative_path": f"generated_cifs/{source.name}",
                "fixture_kind": "pormake-precomputed-demo",
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        )
        results.append(
            {
                "artifact_id": artifact_id,
                "filename": source.name,
                "topology": entry["topology"],
                "is_demo": True,
                "demo_label": "PORMAKE-generated N409 + N10 precomputed Demo CIF fixture",
            }
        )
    return artifacts, results


@lru_cache(maxsize=1)
def get_synthetic_demo_xrd_manifest() -> Dict[str, Any]:
    """Return the owned CIF-to-precomputed-XRD provenance manifest."""
    return _load_fixture("synthetic_demo_xrd_manifest.json")


def get_synthetic_demo_xrd_pattern(cif_filename: str) -> Dict[str, Any]:
    """Return a detached stored XRD fixture for a packaged PORMAKE CIF only."""
    manifest = get_synthetic_demo_xrd_manifest()
    entry = next(
        (item for item in manifest["entries"] if item["cif_filename"] == cif_filename),
        None,
    )
    if entry is None:
        raise KeyError(f"No stored Demo XRD fixture for {cif_filename}")
    return json.loads(json.dumps(_load_fixture(entry["xrd_filename"])))


def get_experiment_detail_response(proposal_text: str = "") -> Dict[str, Any]:
    """Returns the demo fixture for /proposal/experiment-detail.

    v1 always returns the methanol variant regardless of proposal_text; see
    module docstring for the documented simplification / follow-up.
    """
    return _load_fixture("experiment_detail_methanol.json")

from __future__ import annotations

from pathlib import Path

import pytest

from backend.services.mof.pormake_pairing import PairingCandidate, PairingResult
from backend.services.mof.pormake_resolver import (
    normalize_metal_input,
    resolve_linker_input,
    resolve_pormake_candidates,
)


class _FakeMatcher:
    def __init__(self, candidates: list[PairingCandidate]):
        self.candidates = candidates

    def match(self, *, metal: str, linker_smiles: str, max_results: int):
        del max_results
        return PairingResult(
            status="matched",
            metal=metal,
            linker_smiles=linker_smiles,
            candidates=self.candidates,
        )


class _FakeToolEnv:
    def __init__(self, bb_dir: Path):
        self.bb_dir = bb_dir

    def get_building_blocks_dir(self):
        return self.bb_dir

    def get_compatible_topologies(self, node_id: str, linker_id: str):
        return [f"topology-for-{node_id}-{linker_id}"]


def _candidate(*, metal_id: str, kind: str) -> PairingCandidate:
    return PairingCandidate(
        metal_id=metal_id,
        metal_element="Cu",
        organic_id="N10",
        organic_role="N",
        organic_coordination_number=3,
        assembly_pattern="N(metal)-N(organic)",
        match_kind=kind,
        confidence=0.98 if kind == "exact" else 0.8,
        covered_atom_fraction=1.0 if kind == "exact" else 0.8,
        uncovered_elements={} if kind == "exact" else {"N": 1},
        evidence=("fixture",),
        warnings=(),
    )


@pytest.mark.unit
def test_common_metal_names_and_symbols_are_normalized():
    assert normalize_metal_input("Cu") == "Cu"
    assert normalize_metal_input("copper(II) nitrate") == "Cu"
    assert normalize_metal_input("zirconium") == "Zr"


@pytest.mark.unit
def test_curated_linker_name_is_resolved_without_network():
    smiles, provenance = resolve_linker_input("trimesic acid")

    assert smiles == "O=C(O)c1cc(C(=O)O)cc(C(=O)O)c1"
    assert provenance["source"] == "curated-name"


@pytest.mark.unit
@pytest.mark.parametrize(
    ("name", "expected_smiles"),
    [
        ("1,3,5-benzenetricarboxylic acid", "O=C(O)c1cc(C(=O)O)cc(C(=O)O)c1"),
        ("1,4-benzenedicarboxylic acid", "O=C(O)c1ccc(C(=O)O)cc1"),
        ("oxalic acid", "O=C(O)C(=O)O"),
        ("2-methylimidazole", "Cc1c[nH]cn1"),
        ("1,2,4-triazole", "c1nnc[nH]1"),
        ("4,4'-bipyridine", "c1cc(-c2ccncc2)ccn1"),
    ],
)
def test_common_linker_synonyms_are_resolved_without_pubchem(
    monkeypatch, name: str, expected_smiles: str
):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("PubChem should not be called for curated synonyms")

    monkeypatch.setattr("backend.services.mof.pormake_resolver.requests.get", fail_if_called)

    smiles, provenance = resolve_linker_input(name)

    assert smiles == expected_smiles
    assert provenance["source"] == "curated-name"


@pytest.mark.unit
def test_pubchem_fallback_uses_default_certificate_verification(monkeypatch):
    calls = []

    class _Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "PropertyTable": {
                    "Properties": [
                        {
                            "CID": 123,
                            "ConnectivitySMILES": "O=C(O)CO",
                            "IUPACName": "2-hydroxyacetic acid",
                        }
                    ]
                }
            }

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return _Response()

    monkeypatch.setattr("backend.services.mof.pormake_resolver.requests.get", fake_get)

    smiles, provenance = resolve_linker_input("glycolic acid")

    assert smiles == "O=C(O)CO"
    assert provenance["source"] == "pubchem"
    assert "verify" not in calls[0][1]
    assert calls[0][1]["timeout"] == 8


@pytest.mark.unit
def test_exact_candidates_are_auto_generatable_and_common_sbu_is_ranked(
    monkeypatch, tmp_path: Path
):
    (tmp_path / "fixture.xyz").write_text("0\n\n", encoding="utf-8")
    matcher = _FakeMatcher(
        [_candidate(metal_id="N125", kind="exact"), _candidate(metal_id="N409", kind="exact")]
    )
    monkeypatch.setattr(
        "backend.services.mof.pormake_resolver._load_matcher",
        lambda *_: matcher,
    )

    result = resolve_pormake_candidates(
        metal="copper",
        linker="BTC",
        tool_env_service=_FakeToolEnv(tmp_path),
        max_candidates=5,
    )

    assert result["status"] == "success"
    assert result["candidates"][0]["node_id"] == "N409"
    assert all(item["auto_generatable"] for item in result["candidates"])
    assert result["candidates"][0]["compatible_topologies"]


@pytest.mark.unit
def test_scaffold_only_result_cannot_generate_cif(monkeypatch, tmp_path: Path):
    (tmp_path / "fixture.xyz").write_text("0\n\n", encoding="utf-8")
    matcher = _FakeMatcher([_candidate(metal_id="N409", kind="scaffold")])
    monkeypatch.setattr(
        "backend.services.mof.pormake_resolver._load_matcher",
        lambda *_: matcher,
    )

    result = resolve_pormake_candidates(
        metal="Cu",
        linker="BTC",
        tool_env_service=_FakeToolEnv(tmp_path),
    )

    assert result["status"] == "scaffold_only"
    assert result["candidates"] == []
    assert result["scaffold_suggestions"][0]["auto_generatable"] is False

from __future__ import annotations

from pathlib import Path

import pytest

from experiments.pormake_pairing import PairingMatcher, PormakeFragmentIndex


def _write_bb(
    directory: Path,
    name: str,
    symbols: list[str],
    bonds: list[tuple[int, int, str]],
) -> None:
    lines = [str(len(symbols)), ""]
    lines.extend(
        f"{symbol} {index * 1.1:.3f} 0.000 0.000"
        for index, symbol in enumerate(symbols)
    )
    lines.extend(f"{left} {right} {order}" for left, right, order in bonds)
    (directory / f"{name}.xyz").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _add_carboxylate_node(
    directory: Path,
    name: str,
    metal: str,
    coordination_number: int,
) -> None:
    symbols = [metal]
    bonds: list[tuple[int, int, str]] = []
    for _ in range(coordination_number):
        x_index = len(symbols)
        symbols.extend(["X", "C", "O", "O"])
        bonds.extend(
            [
                (x_index, x_index + 1, "S"),
                (x_index + 1, x_index + 2, "A"),
                (x_index + 1, x_index + 3, "A"),
                (0, x_index + 2, "S"),
                (0, x_index + 3, "S"),
            ]
        )
    _write_bb(directory, name, symbols, bonds)


def _add_benzene_core(
    directory: Path,
    name: str,
    port_atoms: tuple[int, ...],
) -> None:
    symbols = ["C"] * 6 + ["X"] * len(port_atoms)
    bonds = [(index, (index + 1) % 6, "A") for index in range(6)]
    bonds.extend(
        (6 + port_index, atom_index, "S")
        for port_index, atom_index in enumerate(port_atoms)
    )
    _write_bb(directory, name, symbols, bonds)


@pytest.fixture()
def pairing_matcher(tmp_path: Path) -> PairingMatcher:
    _add_carboxylate_node(tmp_path, "N409", "Cu", 4)
    _add_carboxylate_node(tmp_path, "N419", "Zr", 12)
    _add_carboxylate_node(tmp_path, "N577", "Zn", 6)
    _add_carboxylate_node(tmp_path, "N410", "Cu", 4)
    _add_carboxylate_node(tmp_path, "E999", "Cu", 2)

    _add_benzene_core(tmp_path, "N10", (0, 2, 4))
    _add_benzene_core(tmp_path, "E14", (0, 3))

    _write_bb(
        tmp_path,
        "E19",
        ["C", "C", "X", "X"],
        [(0, 1, "D"), (2, 0, "S"), (3, 1, "S")],
    )

    index = PormakeFragmentIndex.from_directory(tmp_path)
    return PairingMatcher(index)


@pytest.mark.unit
def test_exact_cu_btc_reconstruction(pairing_matcher: PairingMatcher) -> None:
    result = pairing_matcher.match(
        metal="Cu",
        linker_smiles="O=C(O)c1cc(C(=O)O)cc(C(=O)O)c1",
    )

    assert result.status == "matched"
    assert result.candidates
    top = result.candidates[0]
    assert top.metal_id in {"N409", "N410"}
    assert top.organic_id == "N10"
    assert top.organic_role == "N"
    assert top.match_kind == "exact"
    assert top.covered_atom_fraction == pytest.approx(1.0)
    assert top.confidence >= 0.9


@pytest.mark.unit
def test_exact_zr_bdc_reconstruction(pairing_matcher: PairingMatcher) -> None:
    result = pairing_matcher.match(
        metal="Zr",
        linker_smiles="O=C(O)c1ccc(C(=O)O)cc1",
    )

    top = result.candidates[0]
    assert (top.metal_id, top.organic_id) == ("N419", "E14")
    assert top.organic_role == "E"
    assert top.assembly_pattern == "N(metal)-E-N(metal)"
    assert top.match_kind == "exact"


@pytest.mark.unit
def test_exact_zn_fumarate_reconstruction(pairing_matcher: PairingMatcher) -> None:
    result = pairing_matcher.match(
        metal="Zn",
        linker_smiles="O=C(O)/C=C/C(=O)O",
    )

    top = result.candidates[0]
    assert (top.metal_id, top.organic_id) == ("N577", "E19")
    assert top.match_kind == "exact"


@pytest.mark.unit
def test_amino_bdc_is_scaffold_not_exact(pairing_matcher: PairingMatcher) -> None:
    result = pairing_matcher.match(
        metal="Zr",
        linker_smiles="Nc1cc(C(=O)O)ccc1C(=O)O",
    )

    top = result.candidates[0]
    assert (top.metal_id, top.organic_id) == ("N419", "E14")
    assert top.match_kind == "scaffold"
    assert top.uncovered_elements == {"N": 1}
    assert 0.7 <= top.confidence < 0.9
    assert any("catalog CIF omits" in warning for warning in top.warnings)


@pytest.mark.unit
def test_wrong_terminal_chemistry_is_rejected(
    pairing_matcher: PairingMatcher,
) -> None:
    result = pairing_matcher.match(
        metal="Cu",
        linker_smiles="N#Cc1ccc(C#N)cc1",
    )

    assert result.status == "no_match"
    assert result.candidates == []


@pytest.mark.unit
def test_scaffold_extension_must_not_change_mapped_heteroatom_class(
    pairing_matcher: PairingMatcher,
) -> None:
    result = pairing_matcher.match(
        metal="Zr",
        linker_smiles="O=[N+]([O-])c1cc(C(=O)O)ccc1C(=O)O",
    )

    assert result.candidates
    assert result.candidates[0].organic_id == "E14"
    assert result.candidates[0].match_kind == "scaffold"
    assert result.candidates[0].uncovered_elements == {"N": 1, "O": 2}


@pytest.mark.unit
def test_candidates_are_filtered_by_requested_metal(
    pairing_matcher: PairingMatcher,
) -> None:
    result = pairing_matcher.match(
        metal="Cu",
        linker_smiles="O=C(O)c1ccc(C(=O)O)cc1",
        max_results=20,
    )

    assert result.candidates
    assert {candidate.metal_element for candidate in result.candidates} == {"Cu"}
    assert {candidate.metal_id for candidate in result.candidates} == {
        "N409",
        "N410",
    }


@pytest.mark.unit
def test_invalid_smiles_is_reported(pairing_matcher: PairingMatcher) -> None:
    result = pairing_matcher.match(metal="Cu", linker_smiles="not-a-smiles")

    assert result.status == "invalid_input"
    assert result.candidates == []

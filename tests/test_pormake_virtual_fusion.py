from __future__ import annotations

from pathlib import Path

import networkx as nx
import pytest

from backend.services.mof.pormake_pairing import (
    PairingMatcher,
    PormakeFragmentIndex,
    fuse_connection_points,
)


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


def _add_direct_metal_node(directory: Path) -> None:
    _write_bb(
        directory,
        "N_ZN_DIRECT",
        ["Zn", "X", "X", "X", "X"],
        [(0, index, "S") for index in range(1, 5)],
    )


@pytest.mark.unit
def test_virtual_fusion_matches_pormake_real_neighbor_bond():
    left = nx.Graph()
    left.add_node(0, element="X")
    left.add_node(1, element="C")
    left.add_edge(0, 1, order="S")
    right = nx.Graph()
    right.add_node(0, element="X")
    right.add_node(1, element="N")
    right.add_edge(0, 1, order="S")

    fused = fuse_connection_points(left, 0, right, 0)

    assert set(fused.nodes) == {("left", 1), ("right", 1)}
    assert fused.edges[("left", 1), ("right", 1)] == {
        "order": "S",
        "virtual_fusion": True,
    }


@pytest.mark.unit
def test_virtual_fusion_rejects_ambiguous_x_neighbor():
    graph = nx.Graph()
    graph.add_nodes_from(
        [(0, {"element": "X"}), (1, {"element": "C"}), (2, {"element": "N"})]
    )
    graph.add_edges_from([(0, 1, {"order": "S"}), (0, 2, {"order": "S"})])

    with pytest.raises(ValueError, match="exactly one real neighbor"):
        fuse_connection_points(graph, 0, graph, 0)


@pytest.mark.unit
def test_zero_atom_edge_linker_is_exact_without_cap_guessing(tmp_path: Path):
    _add_direct_metal_node(tmp_path)
    _write_bb(
        tmp_path,
        "E_ALKENE",
        ["C", "C", "X", "X"],
        [(0, 1, "D"), (2, 0, "S"), (3, 1, "S")],
    )
    matcher = PairingMatcher(PormakeFragmentIndex.from_directory(tmp_path))

    result = matcher.match(metal="Zn", linker_smiles="C=C")

    assert result.status == "matched"
    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.organic_id == "E_ALKENE"
    assert candidate.match_kind == "exact"
    assert candidate.covered_atom_fraction == 1.0
    assert candidate.port_modes == ("zero_atom", "zero_atom")
    assert result.diagnostics["signature_candidate_count"] == 1
    assert result.diagnostics["evaluated_pair_count"] == 2


@pytest.mark.unit
def test_zero_atom_organic_node_representation_is_enumerated(tmp_path: Path):
    _add_direct_metal_node(tmp_path)
    _write_bb(
        tmp_path,
        "N_ORGANIC",
        ["C", "C", "C", "X", "X", "X"],
        [
            (0, 1, "S"),
            (1, 2, "S"),
            (3, 0, "S"),
            (4, 1, "S"),
            (5, 2, "S"),
        ],
    )
    matcher = PairingMatcher(PormakeFragmentIndex.from_directory(tmp_path))

    result = matcher.match(metal="Zn", linker_smiles="CCC")

    candidate = result.candidates[0]
    assert candidate.organic_id == "N_ORGANIC"
    assert candidate.organic_role == "N"
    assert candidate.assembly_pattern == "N(metal)-N(organic)"
    assert candidate.port_modes == ("zero_atom", "zero_atom", "zero_atom")


@pytest.mark.unit
def test_zero_atom_mode_rejects_unmatched_nonmetal_sbu_cap(tmp_path: Path):
    _write_bb(
        tmp_path,
        "N_ZN_CAPPED",
        ["Zn", "X", "C", "O", "X", "C", "O", "X", "C", "O"],
        [
            (0, 3, "S"),
            (0, 6, "S"),
            (0, 9, "S"),
            (1, 2, "S"),
            (2, 3, "S"),
            (4, 5, "S"),
            (5, 6, "S"),
            (7, 8, "S"),
            (8, 9, "S"),
        ],
    )
    _write_bb(
        tmp_path,
        "E_ALKENE",
        ["C", "C", "X", "X"],
        [(0, 1, "D"), (2, 0, "S"), (3, 1, "S")],
    )
    matcher = PairingMatcher(PormakeFragmentIndex.from_directory(tmp_path))

    result = matcher.match(metal="Zn", linker_smiles="C=C")

    assert result.status == "no_match"
    assert result.candidates == []


@pytest.mark.unit
def test_signature_prefilter_removes_element_incompatible_blocks(tmp_path: Path):
    _add_direct_metal_node(tmp_path)
    _write_bb(
        tmp_path,
        "E_CC",
        ["C", "C", "X", "X"],
        [(0, 1, "S"), (2, 0, "S"), (3, 1, "S")],
    )
    _write_bb(
        tmp_path,
        "E_NN",
        ["N", "N", "X", "X"],
        [(0, 1, "S"), (2, 0, "S"), (3, 1, "S")],
    )
    matcher = PairingMatcher(PormakeFragmentIndex.from_directory(tmp_path))

    result = matcher.match(metal="Zn", linker_smiles="CC")

    assert result.diagnostics["organic_core_count"] == 2
    assert result.diagnostics["signature_candidate_count"] == 1
    assert {candidate.organic_id for candidate in result.candidates} == {"E_CC"}

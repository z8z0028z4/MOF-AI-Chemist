from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

import networkx as nx
from rdkit import Chem


# Mirrors PORMAKE's metal-like classification so that the proof of concept
# interprets the bundled database the same way as PORMAKE does.
METAL_LIKE = frozenset(
    {
        "Li",
        "Be",
        "B",
        "Na",
        "Mg",
        "Al",
        "Si",
        "K",
        "Ca",
        "Sc",
        "Ti",
        "V",
        "Cr",
        "Mn",
        "Fe",
        "Co",
        "Ni",
        "Cu",
        "Zn",
        "Ga",
        "Ge",
        "As",
        "Rb",
        "Sr",
        "Y",
        "Zr",
        "Nb",
        "Mo",
        "Tc",
        "Ru",
        "Rh",
        "Pd",
        "Ag",
        "Cd",
        "In",
        "Sn",
        "Sb",
        "Te",
        "Cs",
        "Ba",
        "La",
        "Ce",
        "Pr",
        "Nd",
        "Pm",
        "Sm",
        "Eu",
        "Gd",
        "Tb",
        "Dy",
        "Ho",
        "Er",
        "Tm",
        "Yb",
        "Lu",
        "Hf",
        "Ta",
        "W",
        "Re",
        "Os",
        "Ir",
        "Pt",
        "Au",
        "Hg",
        "Tl",
        "Pb",
        "Bi",
        "Po",
        "Fr",
        "Ra",
        "Ac",
        "Th",
        "Pa",
        "U",
        "Np",
        "Pu",
    }
)


def _node_match(left: dict, right: dict) -> bool:
    return left["element"] == right["element"]


def _edge_match(left: dict, right: dict) -> bool:
    return left["order"] == right["order"]


def _cap_node_match(left: dict, right: dict) -> bool:
    return (
        left["element"] == right["element"]
        and bool(left.get("attachment")) == bool(right.get("attachment"))
    )


def _cap_edge_compatible(target_edge: dict, cap_edge: dict) -> bool:
    cap_order = cap_edge["order"]
    target_order = target_edge["order"]
    if cap_order == "A":
        # PORMAKE uses A for both aromatic and resonance-delocalised bonds.
        # A carboxylate A/A pair therefore corresponds to an acid S/D pair
        # after the metal is removed.
        return target_order in {"A", "S", "D"}
    return target_order == cap_order


def _normalise_bond_order(token: str) -> str:
    token = token.upper()
    if token in {"A", "D", "T"}:
        return token
    return "S"


@dataclass(frozen=True)
class PormakeFragment:
    fragment_id: str
    graph: nx.Graph
    x_nodes: tuple[int, ...]
    metal_elements: frozenset[str]
    source_path: Path

    @property
    def coordination_number(self) -> int:
        return len(self.x_nodes)

    @property
    def is_metal(self) -> bool:
        return bool(self.metal_elements)

    @property
    def role(self) -> str:
        return "E" if self.coordination_number == 2 else "N"


@dataclass(frozen=True)
class OrganicCore:
    fragment_id: str
    graph: nx.Graph
    port_anchors: tuple[int, ...]
    coordination_number: int
    role: str


@dataclass(frozen=True)
class GraphSignature:
    atom_count: int
    element_counts: tuple[tuple[str, int], ...]
    bond_order_counts: tuple[tuple[str, int], ...]
    cycle_rank: int


@dataclass(frozen=True)
class CapPattern:
    graph: nx.Graph
    support_count: int
    direct_to_metal: bool = False


@dataclass(frozen=True)
class PairingCandidate:
    metal_id: str
    metal_element: str
    organic_id: str
    organic_role: str
    organic_coordination_number: int
    assembly_pattern: str
    match_kind: str
    confidence: float
    covered_atom_fraction: float
    uncovered_elements: dict[str, int]
    evidence: tuple[str, ...]
    warnings: tuple[str, ...] = ()
    port_modes: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {
            "metal_id": self.metal_id,
            "metal_element": self.metal_element,
            "organic_id": self.organic_id,
            "organic_role": self.organic_role,
            "organic_coordination_number": self.organic_coordination_number,
            "assembly_pattern": self.assembly_pattern,
            "match_kind": self.match_kind,
            "confidence": self.confidence,
            "covered_atom_fraction": self.covered_atom_fraction,
            "uncovered_elements": dict(self.uncovered_elements),
            "evidence": list(self.evidence),
            "warnings": list(self.warnings),
            "port_modes": list(self.port_modes),
        }


@dataclass(frozen=True)
class PairingResult:
    status: str
    metal: str
    linker_smiles: str
    candidates: list[PairingCandidate]
    warnings: tuple[str, ...] = ()
    diagnostics: dict[str, int | float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "metal": self.metal,
            "linker_smiles": self.linker_smiles,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "warnings": list(self.warnings),
            "diagnostics": dict(self.diagnostics),
        }


@dataclass
class PormakeFragmentIndex:
    fragments: tuple[PormakeFragment, ...]
    parse_errors: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_directory(cls, directory: str | Path) -> "PormakeFragmentIndex":
        bb_dir = Path(directory)
        fragments: list[PormakeFragment] = []
        errors: dict[str, str] = {}
        for path in sorted(bb_dir.glob("*.xyz")):
            try:
                fragments.append(_read_fragment(path))
            except (OSError, ValueError, IndexError) as exc:
                errors[path.name] = str(exc)
        return cls(tuple(fragments), errors)

    def metal_fragments(self, element: str) -> tuple[PormakeFragment, ...]:
        return tuple(
            fragment
            for fragment in self.fragments
            if element in fragment.metal_elements
        )

    @property
    def organic_fragments(self) -> tuple[PormakeFragment, ...]:
        return tuple(fragment for fragment in self.fragments if not fragment.is_metal)


def _read_fragment(path: Path) -> PormakeFragment:
    lines = path.read_text(encoding="utf-8").splitlines()
    if len(lines) < 2:
        raise ValueError("missing XYZ header")
    atom_count = int(lines[0].strip())
    if len(lines) < atom_count + 2:
        raise ValueError("atom count exceeds available XYZ lines")

    graph = nx.Graph()
    x_nodes: list[int] = []
    metal_elements: set[str] = set()
    for index, line in enumerate(lines[2 : atom_count + 2]):
        tokens = line.split()
        if len(tokens) < 4:
            raise ValueError(f"invalid atom line {index + 3}")
        element = tokens[0]
        graph.add_node(index, element=element)
        if element == "X":
            x_nodes.append(index)
        elif element in METAL_LIKE:
            metal_elements.add(element)

    for line_number, line in enumerate(lines[atom_count + 2 :], atom_count + 3):
        tokens = line.split()
        if len(tokens) < 3:
            continue
        left, right = int(tokens[0]), int(tokens[1])
        if left not in graph or right not in graph:
            raise ValueError(f"bond index out of range on line {line_number}")
        order = _normalise_bond_order(tokens[2])
        if graph.has_edge(left, right):
            # PORMAKE contains duplicate undirected records. Preserve one edge
            # and reject only contradictory bond labels.
            if graph.edges[left, right]["order"] != order:
                raise ValueError(
                    f"conflicting duplicate bond {left}-{right} on line {line_number}"
                )
            continue
        graph.add_edge(left, right, order=order)

    return PormakeFragment(
        fragment_id=path.stem,
        graph=graph,
        x_nodes=tuple(x_nodes),
        metal_elements=frozenset(metal_elements),
        source_path=path,
    )


def fuse_connection_points(
    left: nx.Graph,
    left_x: int,
    right: nx.Graph,
    right_x: int,
) -> nx.Graph:
    """Mirror PORMAKE's X-X fusion on two molecular graphs.

    The returned graph contains tagged ``(side, original_index)`` nodes. Both
    X nodes are removed and their unique real neighbors are joined by a single
    bond, matching the final bond operation in PORMAKE's Builder.
    """

    def real_neighbor(graph: nx.Graph, x_node: int) -> int:
        if x_node not in graph or graph.nodes[x_node].get("element") != "X":
            raise ValueError("connection point must reference an X node")
        neighbors = [
            node
            for node in graph.neighbors(x_node)
            if graph.nodes[node].get("element") != "X"
        ]
        if len(neighbors) != 1:
            raise ValueError("connection point must have exactly one real neighbor")
        return neighbors[0]

    left_neighbor = real_neighbor(left, left_x)
    right_neighbor = real_neighbor(right, right_x)
    fused = nx.Graph()
    for side, graph, removed in (
        ("left", left, left_x),
        ("right", right, right_x),
    ):
        for node, data in graph.nodes(data=True):
            if node == removed:
                continue
            fused.add_node((side, node), **data, source_side=side, source_atom=node)
        for start, end, data in graph.edges(data=True):
            if removed in {start, end}:
                continue
            fused.add_edge((side, start), (side, end), **data)
    fused.add_edge(
        ("left", left_neighbor),
        ("right", right_neighbor),
        order="S",
        virtual_fusion=True,
    )
    return fused


def _organic_core(fragment: PormakeFragment) -> OrganicCore | None:
    graph = fragment.graph
    anchors: list[int] = []
    for x_node in fragment.x_nodes:
        real_neighbors = [
            node
            for node in graph.neighbors(x_node)
            if graph.nodes[node]["element"] not in {"X", "H"}
        ]
        if len(real_neighbors) != 1:
            return None
        anchors.append(real_neighbors[0])

    core_nodes = [
        node
        for node, data in graph.nodes(data=True)
        if data["element"] not in {"X", "H"}
    ]
    core = graph.subgraph(core_nodes).copy()
    if not core_nodes or not nx.is_connected(core):
        return None
    if any(anchor not in core for anchor in anchors):
        return None
    return OrganicCore(
        fragment_id=fragment.fragment_id,
        graph=core,
        port_anchors=tuple(anchors),
        coordination_number=fragment.coordination_number,
        role=fragment.role,
    )


def _graph_signature(graph: nx.Graph) -> GraphSignature:
    elements = Counter(data["element"] for _, data in graph.nodes(data=True))
    bond_orders = Counter(data["order"] for _, _, data in graph.edges(data=True))
    cycle_rank = graph.number_of_edges() - graph.number_of_nodes()
    if graph.number_of_nodes():
        cycle_rank += nx.number_connected_components(graph)
    return GraphSignature(
        atom_count=graph.number_of_nodes(),
        element_counts=tuple(sorted(elements.items())),
        bond_order_counts=tuple(sorted(bond_orders.items())),
        cycle_rank=max(cycle_rank, 0),
    )


def _signature_can_embed(core: GraphSignature, target: GraphSignature) -> bool:
    if core.atom_count > target.atom_count or core.cycle_rank > target.cycle_rank:
        return False
    target_elements = dict(target.element_counts)
    if any(count > target_elements.get(element, 0) for element, count in core.element_counts):
        return False
    target_bonds = dict(target.bond_order_counts)
    return not any(
        count > target_bonds.get(order, 0)
        for order, count in core.bond_order_counts
    )


def _cap_patterns(fragment: PormakeFragment) -> tuple[CapPattern, ...]:
    direct_support = 0
    for x_node in fragment.x_nodes:
        real_neighbors = [
            node
            for node in fragment.graph.neighbors(x_node)
            if fragment.graph.nodes[node]["element"] not in {"X", "H"}
        ]
        if len(real_neighbors) == 1:
            neighbor_element = fragment.graph.nodes[real_neighbors[0]]["element"]
            if neighbor_element in METAL_LIKE:
                direct_support += 1

    graph = fragment.graph.copy()
    removable = [
        node
        for node, data in graph.nodes(data=True)
        if data["element"] == "H" or data["element"] in METAL_LIKE
    ]
    graph.remove_nodes_from(removable)

    raw_patterns: list[nx.Graph] = []
    for component_nodes in nx.connected_components(graph):
        component = graph.subgraph(component_nodes).copy()
        x_nodes = [
            node
            for node, data in component.nodes(data=True)
            if data["element"] == "X"
        ]
        if len(x_nodes) != 1:
            continue
        x_node = x_nodes[0]
        neighbors = [
            node
            for node in component.neighbors(x_node)
            if component.nodes[node]["element"] != "X"
        ]
        if len(neighbors) != 1:
            continue
        attachment = neighbors[0]
        component.remove_node(x_node)
        if not component:
            continue
        nx.set_node_attributes(component, False, "attachment")
        component.nodes[attachment]["attachment"] = True
        raw_patterns.append(component)

    grouped: list[tuple[nx.Graph, int]] = []
    for pattern in raw_patterns:
        for index, (known, count) in enumerate(grouped):
            if nx.is_isomorphic(
                pattern,
                known,
                node_match=_cap_node_match,
                edge_match=_edge_match,
            ):
                grouped[index] = (known, count + 1)
                break
        else:
            grouped.append((pattern, 1))
    patterns = [
        CapPattern(graph=pattern, support_count=count)
        for pattern, count in grouped
    ]
    if direct_support:
        patterns.append(
            CapPattern(
                graph=nx.Graph(),
                support_count=direct_support,
                direct_to_metal=True,
            )
        )
    return tuple(patterns)


def _target_graph(smiles: str) -> nx.Graph | None:
    molecule = Chem.MolFromSmiles(smiles)
    if molecule is None:
        return None

    fragments = Chem.GetMolFrags(molecule, asMols=True, sanitizeFrags=True)
    if not fragments:
        return None
    molecule = max(fragments, key=lambda mol: mol.GetNumHeavyAtoms())

    graph = nx.Graph()
    rdkit_to_graph: dict[int, int] = {}
    for atom in molecule.GetAtoms():
        if atom.GetSymbol() == "H":
            continue
        graph_index = len(rdkit_to_graph)
        rdkit_to_graph[atom.GetIdx()] = graph_index
        graph.add_node(
            graph_index,
            element=atom.GetSymbol(),
            formal_charge=atom.GetFormalCharge(),
        )

    for bond in molecule.GetBonds():
        begin = rdkit_to_graph.get(bond.GetBeginAtomIdx())
        end = rdkit_to_graph.get(bond.GetEndAtomIdx())
        if begin is None or end is None:
            continue
        if bond.GetIsAromatic():
            order = "A"
        elif bond.GetBondType() == Chem.BondType.DOUBLE:
            order = "D"
        elif bond.GetBondType() == Chem.BondType.TRIPLE:
            order = "T"
        else:
            order = "S"
        graph.add_edge(begin, end, order=order)
    return graph


def _core_mappings(target: nx.Graph, core: OrganicCore) -> Iterator[dict[int, int]]:
    if core.graph.number_of_nodes() > target.number_of_nodes():
        return
    matcher = nx.algorithms.isomorphism.GraphMatcher(
        target,
        core.graph,
        node_match=_node_match,
        edge_match=_edge_match,
    )
    for count, target_to_core in enumerate(matcher.subgraph_isomorphisms_iter()):
        if count >= 256:
            break
        yield {core_node: target_node for target_node, core_node in target_to_core.items()}


def _matches_cap(
    target: nx.Graph,
    component_nodes: set[int],
    attachment_node: int,
    cap_patterns: tuple[CapPattern, ...],
) -> tuple[bool, int]:
    branch = target.subgraph(component_nodes).copy()
    nx.set_node_attributes(branch, False, "attachment")
    branch.nodes[attachment_node]["attachment"] = True
    for pattern in cap_patterns:
        if pattern.direct_to_metal:
            continue
        matcher = nx.algorithms.isomorphism.GraphMatcher(
            branch,
            pattern.graph,
            node_match=_cap_node_match,
            edge_match=_cap_edge_compatible,
        )
        for branch_to_pattern in matcher.isomorphisms_iter():
            cap_aromatic_edges = [
                (left, right)
                for left, right, data in pattern.graph.edges(data=True)
                if data["order"] == "A"
            ]
            if cap_aromatic_edges:
                pattern_to_branch = {
                    pattern_node: branch_node
                    for branch_node, pattern_node in branch_to_pattern.items()
                }
                observed_orders = {
                    branch.edges[
                        pattern_to_branch[left], pattern_to_branch[right]
                    ]["order"]
                    for left, right in cap_aromatic_edges
                }
                if observed_orders == {"S"}:
                    continue
            return True, pattern.support_count
    return False, 0


def _normalise_element(element: str) -> str:
    element = element.strip()
    if not element:
        return element
    return element[0].upper() + element[1:].lower()


class PairingMatcher:
    """Find graph-supported PORMAKE pairings without ligand-ID lookup tables."""

    def __init__(
        self,
        index: PormakeFragmentIndex,
        *,
        max_decoration_fraction: float = 0.25,
    ):
        self.index = index
        self.max_decoration_fraction = max_decoration_fraction
        self._organic_cores = tuple(
            (core, _graph_signature(core.graph))
            for fragment in index.organic_fragments
            if (core := _organic_core(fragment)) is not None
        )
        self._caps_by_metal_id = {
            fragment.fragment_id: _cap_patterns(fragment)
            for fragment in index.fragments
            if fragment.is_metal
        }

    def coverage_summary(self) -> dict[str, int | float]:
        metal_fragments = tuple(
            fragment
            for fragment in self.index.fragments
            if fragment.is_metal and fragment.role == "N"
        )
        cap_ready = sum(
            bool(self._caps_by_metal_id.get(fragment.fragment_id))
            for fragment in metal_fragments
        )
        organic_count = len(self.index.organic_fragments)
        return {
            "fragment_count": len(self.index.fragments),
            "organic_fragment_count": organic_count,
            "valid_organic_core_count": len(self._organic_cores),
            "metal_fragment_count": len(metal_fragments),
            "cap_ready_metal_count": cap_ready,
            "organic_parse_coverage": round(
                len(self._organic_cores) / organic_count if organic_count else 0.0,
                4,
            ),
            "metal_cap_coverage": round(
                cap_ready / len(metal_fragments) if metal_fragments else 0.0,
                4,
            ),
        }

    def match(
        self,
        *,
        metal: str,
        linker_smiles: str,
        max_results: int = 20,
    ) -> PairingResult:
        metal = _normalise_element(metal)
        target = _target_graph(linker_smiles)
        if target is None:
            return PairingResult(
                status="invalid_input",
                metal=metal,
                linker_smiles=linker_smiles,
                candidates=[],
                warnings=("The linker SMILES could not be parsed by RDKit.",),
            )
        target_signature = _graph_signature(target)
        possible_cores = tuple(
            core
            for core, signature in self._organic_cores
            if _signature_can_embed(signature, target_signature)
        )

        metal_fragments = tuple(
            fragment
            for fragment in self.index.metal_fragments(metal)
            if fragment.role == "N"
            if self._caps_by_metal_id.get(fragment.fragment_id)
        )
        if not metal_fragments:
            return PairingResult(
                status="no_match",
                metal=metal,
                linker_smiles=linker_smiles,
                candidates=[],
                warnings=(
                    f"No {metal} PORMAKE node exposed a conservative single-X cap.",
                ),
            )

        best: dict[tuple[str, str], PairingCandidate] = {}
        mapping_count = 0
        evaluated_pair_count = 0
        for core in possible_cores:
            for mapping in _core_mappings(target, core):
                mapping_count += 1
                for metal_fragment in metal_fragments:
                    evaluated_pair_count += 1
                    candidate = self._evaluate_mapping(
                        target=target,
                        core=core,
                        mapping=mapping,
                        metal_fragment=metal_fragment,
                        requested_metal=metal,
                    )
                    if candidate is None:
                        continue
                    key = (candidate.metal_id, candidate.organic_id)
                    previous = best.get(key)
                    if previous is None or (
                        candidate.confidence,
                        candidate.covered_atom_fraction,
                    ) > (
                        previous.confidence,
                        previous.covered_atom_fraction,
                    ):
                        best[key] = candidate

        candidates = sorted(
            best.values(),
            key=lambda candidate: (
                candidate.match_kind != "exact",
                -candidate.confidence,
                -candidate.organic_coordination_number,
                candidate.organic_id,
                candidate.metal_id,
            ),
        )[:max_results]
        return PairingResult(
            status="matched" if candidates else "no_match",
            metal=metal,
            linker_smiles=linker_smiles,
            candidates=candidates,
            warnings=(),
            diagnostics={
                "organic_core_count": len(self._organic_cores),
                "signature_candidate_count": len(possible_cores),
                "core_mapping_count": mapping_count,
                "evaluated_pair_count": evaluated_pair_count,
            },
        )

    def _evaluate_mapping(
        self,
        *,
        target: nx.Graph,
        core: OrganicCore,
        mapping: dict[int, int],
        metal_fragment: PormakeFragment,
        requested_metal: str,
    ) -> PairingCandidate | None:
        mapped_nodes = set(mapping.values())
        remainder = target.copy()
        remainder.remove_nodes_from(mapped_nodes)
        components = [set(nodes) for nodes in nx.connected_components(remainder)]

        target_port_counts = Counter(mapping[anchor] for anchor in core.port_anchors)
        port_components: dict[int, list[tuple[set[int], int]]] = defaultdict(list)
        decoration_components: list[set[int]] = []

        for component in components:
            attachment_edges = [
                (outside, inside)
                for outside in component
                for inside in target.neighbors(outside)
                if inside in mapped_nodes
            ]
            attached_core_nodes = {inside for _, inside in attachment_edges}
            if len(attachment_edges) == 1:
                outside, inside = attachment_edges[0]
                if inside in target_port_counts:
                    if target.edges[outside, inside]["order"] != "S":
                        return None
                    port_components[inside].append((component, outside))
                    continue
            if attached_core_nodes & set(target_port_counts):
                return None
            # Scaffold decorations are intentionally conservative. A single
            # substituent may extend a mapped carbon through a single bond,
            # but mapped heteroatoms may not silently change functional class
            # (for example amino -> nitro), and fused-ring extensions are not
            # accepted as simple decorations.
            if len(attachment_edges) != 1:
                return None
            outside, inside = attachment_edges[0]
            if target.nodes[inside]["element"] != "C":
                return None
            if target.edges[outside, inside]["order"] != "S":
                return None
            decoration_components.append(component)

        cap_patterns = self._caps_by_metal_id[metal_fragment.fragment_id]
        cap_support: list[int] = []
        covered_port_atoms = 0
        port_modes: list[str] = []
        has_direct_metal_port = any(
            pattern.direct_to_metal for pattern in cap_patterns
        )
        for anchor, required_count in target_port_counts.items():
            branches = port_components.get(anchor, [])
            if not branches:
                # PORMAKE may use X only as a zero-atom connection direction.
                # The linker graph is already present in the organic block; the
                # opposite X must be bonded directly to a metal. Otherwise
                # fusion would append an unmatched nonmetal fragment and the
                # input linker would no longer be an exact molecular graph.
                if not has_direct_metal_port:
                    return None
                port_modes.extend(["zero_atom"] * required_count)
                continue
            if len(branches) != required_count:
                return None
            for component, attachment_node in branches:
                matched, support = _matches_cap(
                    target,
                    component,
                    attachment_node,
                    cap_patterns,
                )
                if not matched:
                    return None
                covered_port_atoms += len(component)
                cap_support.append(support)
                port_modes.append("split_fragment")

        decoration_nodes = set().union(*decoration_components) if decoration_components else set()
        target_atom_count = target.number_of_nodes()
        decoration_fraction = len(decoration_nodes) / target_atom_count
        if decoration_fraction > self.max_decoration_fraction:
            return None

        covered_atoms = len(mapped_nodes) + covered_port_atoms
        covered_fraction = covered_atoms / target_atom_count
        exact = not decoration_nodes and covered_atoms == target_atom_count
        match_kind = "exact" if exact else "scaffold"

        port_support = (
            min(cap_support) / metal_fragment.coordination_number
            if cap_support and metal_fragment.coordination_number
            else 0.0
        )
        if exact:
            confidence = 0.94 + 0.04 * min(port_support, 1.0)
            warnings: tuple[str, ...] = ()
        else:
            confidence = min(0.89, 0.92 * covered_fraction)
            warnings = (
                "The catalog CIF omits unmatched linker decorations; "
                "generate a custom decorated building block before CIF generation.",
            )

        uncovered = Counter(
            target.nodes[node]["element"] for node in decoration_nodes
        )
        if set(port_modes) == {"zero_atom"}:
            port_evidence = (
                f"All {core.coordination_number} ports use PORMAKE zero-atom "
                "X fusion; the complete linker graph is retained in the "
                f"{core.fragment_id} block."
            )
        elif "zero_atom" in port_modes:
            port_evidence = (
                f"The {core.coordination_number} ports are covered by a mix "
                "of zero-atom X fusion and SBU-side fragments."
            )
        else:
            port_evidence = (
                f"All {core.coordination_number} ports matched caps observed "
                f"in {metal_fragment.fragment_id}."
            )
        evidence = (
            f"{core.fragment_id} heavy-atom core matched with bond orders.",
            port_evidence,
            (
                f"Covered {covered_atoms}/{target_atom_count} linker heavy atoms "
                "using PORMAKE-equivalent X fusion."
            ),
        )
        pattern = (
            "N(metal)-E-N(metal)"
            if core.role == "E"
            else "N(metal)-N(organic)"
        )
        return PairingCandidate(
            metal_id=metal_fragment.fragment_id,
            metal_element=requested_metal,
            organic_id=core.fragment_id,
            organic_role=core.role,
            organic_coordination_number=core.coordination_number,
            assembly_pattern=pattern,
            match_kind=match_kind,
            confidence=round(confidence, 4),
            covered_atom_fraction=round(covered_fraction, 4),
            uncovered_elements=dict(sorted(uncovered.items())),
            evidence=evidence,
            warnings=warnings,
            port_modes=tuple(sorted(port_modes)),
        )

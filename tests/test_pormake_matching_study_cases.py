from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import subprocess

import networkx as nx
import pytest

from backend.config import MOF_DATA_DIR
from backend.services.mof.pormake_pairing import (
    PormakeFragmentIndex,
    _edge_match,
    _node_match,
    _organic_core,
    _target_graph,
)
from backend.services.mof.pormake_resolver import resolve_pormake_candidates
from backend.services.mof.tool_env_service import ToolEnvService


@dataclass(frozen=True)
class DiscoveryCase:
    name: str
    metal: str
    linker_smiles: str
    expected_status: str
    expected_pair: tuple[str, str] | None


DISCOVERY_CASES = (
    DiscoveryCase(
        "HKUST-1",
        "Cu",
        "O=C(O)c1cc(C(=O)O)cc(C(=O)O)c1",
        "success",
        ("N409", "N10"),
    ),
    DiscoveryCase(
        "UiO-66",
        "Zr",
        "O=C(O)c1ccc(C(=O)O)cc1",
        "success",
        ("N419", "E14"),
    ),
    DiscoveryCase(
        "UiO-66-NH2",
        "Zr",
        "Nc1cc(C(=O)O)ccc1C(=O)O",
        "success",
        ("N419", "E72"),
    ),
    DiscoveryCase(
        "MOF-5",
        "Zn",
        "O=C(O)c1ccc(C(=O)O)cc1",
        "success",
        ("N577", "E14"),
    ),
    DiscoveryCase(
        "MIL-53",
        "Al",
        "O=C(O)c1ccc(C(=O)O)cc1",
        "success",
        ("N565", "E14"),
    ),
    DiscoveryCase(
        "MOF-801",
        "Zr",
        "O=C(O)/C=C/C(=O)O",
        "success",
        ("N419", "E19"),
    ),
    DiscoveryCase(
        "ZIF-8 direct donor",
        "Zn",
        "Cc1ncc[nH]1",
        "no_match",
        None,
    ),
    DiscoveryCase(
        "CALF-20 1,2,4-triazole",
        "Zn",
        "C1=NN=CN1",
        "no_match",
        None,
    ),
)

ASSEMBLY_CASES = (
    ("UiO-66", "N419", "E14", 12, 2, "fcu"),
    ("UiO-66-NH2", "N419", "E72", 12, 2, "fcu"),
    ("MOF-5", "N577", "E14", 6, 2, "pcu"),
    ("MIL-53", "N565", "E14", 4, 2, "sra"),
    ("MOF-801", "N419", "E19", 12, 2, "fcu"),
)


@pytest.fixture(scope="module")
def tool_env() -> ToolEnvService:
    service = ToolEnvService(MOF_DATA_DIR)
    if service.get_building_blocks_dir() is None:
        pytest.skip("PORMAKE building-block catalog is unavailable")
    return service


@pytest.mark.integration
@pytest.mark.parametrize("case", DISCOVERY_CASES, ids=lambda case: case.name)
def test_study_case_discovery(case: DiscoveryCase, tool_env: ToolEnvService):
    result = resolve_pormake_candidates(
        metal=case.metal,
        linker=case.linker_smiles,
        tool_env_service=tool_env,
        max_candidates=10,
    )

    assert result["status"] == case.expected_status
    pairs = {
        (candidate["node_id"], candidate["linker_id"])
        for candidate in result["candidates"]
    }
    if case.expected_pair is not None:
        assert case.expected_pair in pairs


@pytest.mark.integration
def test_e37_is_not_the_124_triazole_linker_used_by_calf20(
    tool_env: ToolEnvService,
):
    index = PormakeFragmentIndex.from_directory(tool_env.get_building_blocks_dir())
    e37 = next(fragment for fragment in index.fragments if fragment.fragment_id == "E37")
    e37_core = _organic_core(e37)
    calf20_triazole = _target_graph("C1=NN=CN1")

    assert e37_core is not None
    assert calf20_triazole is not None
    assert not nx.is_isomorphic(
        e37_core.graph,
        calf20_triazole,
        node_match=_node_match,
        edge_match=_edge_match,
    )


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.parametrize(
    ("name", "node", "linker", "node_cn", "linker_cn", "topology"),
    ASSEMBLY_CASES,
    ids=[case[0] for case in ASSEMBLY_CASES],
)
def test_study_case_assembly(
    name: str,
    node: str,
    linker: str,
    node_cn: int,
    linker_cn: int,
    topology: str,
    tmp_path: Path,
):
    del name
    project_root = Path(__file__).resolve().parents[1]
    python_exe = (
        project_root
        / "local_data"
        / "mof"
        / "tool_envs"
        / "pormake"
        / "bin"
        / "python"
    )
    if not python_exe.is_file():
        pytest.skip("PORMAKE execution environment is unavailable")

    request_path = tmp_path / "request.json"
    result_path = tmp_path / "result.json"
    request_path.write_text(
        json.dumps(
            {
                "node_code": node,
                "linker_code": linker,
                "node_cn": node_cn,
                "linker_cn": linker_cn,
                "node_id": node,
                "linker_id": linker,
                "topology": topology,
                "max_results": 1,
                "output_dir": str(tmp_path / "cifs"),
            }
        ),
        encoding="utf-8",
    )
    subprocess.run(
        [
            str(python_exe),
            str(project_root / "backend" / "workers" / "mof" / "pormake_worker.py"),
            "--request",
            str(request_path),
            "--result",
            str(result_path),
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )
    result = json.loads(result_path.read_text(encoding="utf-8"))

    assert result["status"] == "succeeded"
    assert result["results"]
    assert result["results"][0]["topology"] == topology
    assert result["results"][0]["local_prefilter_rmsd"] < 0.3
    assert result["results"][0]["max_rmsd"] < 0.3

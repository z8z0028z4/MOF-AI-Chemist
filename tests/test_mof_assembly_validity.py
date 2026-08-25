import json
import subprocess
import pytest
from pathlib import Path
import tempfile

# Locate project paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYTHON_EXE = PROJECT_ROOT / "local_data" / "mof" / "tool_envs" / "pormake" / "bin" / "python"
WORKER_SCRIPT = PROJECT_ROOT / "backend" / "workers" / "mof" / "pormake_worker.py"

pytestmark = [pytest.mark.external, pytest.mark.slow]
if not PYTHON_EXE.is_file():
    pytestmark.append(pytest.mark.skip(reason="PORMAKE tool environment is not installed locally"))

def run_pormake_assembly(node_code: str, linker_code: str, node_cn: int, linker_cn: int, topology: str) -> dict:
    """Invokes pormake_worker.py to assemble a MOF structure in a temp directory."""
    assert PYTHON_EXE.is_file(), f"PORMAKE Python executable not found at {PYTHON_EXE}"
    assert WORKER_SCRIPT.is_file(), f"pormake_worker.py not found at {WORKER_SCRIPT}"

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        req_path = temp_path / "request.json"
        res_path = temp_path / "result.json"
        out_dir = temp_path / "output_cifs"

        request_data = {
            "node_code": node_code,
            "linker_code": linker_code,
            "node_cn": node_cn,
            "linker_cn": linker_cn,
            "node_id": node_code,
            "linker_id": linker_code,
            "topology": topology,
            "max_results": 5,
            "output_dir": str(out_dir)
        }

        req_path.write_text(json.dumps(request_data, indent=2), encoding="utf-8")

        # Run worker subprocess in the pormake environment
        cmd = [
            str(PYTHON_EXE),
            str(WORKER_SCRIPT),
            "--request",
            str(req_path),
            "--result",
            str(res_path)
        ]

        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        if proc.returncode != 0:
            print("Subprocess Stderr:", proc.stderr)
            print("Subprocess Stdout:", proc.stdout)
            raise RuntimeError(f"Worker exited with code {proc.returncode}")

        assert res_path.exists(), "pormake_worker did not produce result.json"
        return json.loads(res_path.read_text(encoding="utf-8"))

def test_assembly_cu_btc():
    """單配體典型案例: Cu-Paddlewheel (N409, CN=4) + BTC (N10, CN=3) in tbo topology (HKUST-1)."""
    res = run_pormake_assembly(
        node_code="N409",
        linker_code="N10",
        node_cn=4,
        linker_cn=3,
        topology="tbo"
    )

    assert res["status"] == "succeeded", f"Assembly failed: {res.get('failures')}"
    assert len(res["results"]) > 0
    for item in res["results"]:
        assert item["topology"] == "tbo"
        assert item["max_rmsd"] < 0.3  # 符合化學合理性的幾何變形度限制

def test_assembly_zr_bdc():
    """單配體典型案例: Zr6-Cluster (N419, CN=12) + BDC (E3, CN=2) in fcu topology (UiO-66)."""
    res = run_pormake_assembly(
        node_code="N419",
        linker_code="E3",
        node_cn=12,
        linker_cn=2,
        topology="fcu"
    )

    assert res["status"] == "succeeded", f"Assembly failed: {res.get('failures')}"
    assert len(res["results"]) > 0
    for item in res["results"]:
        assert item["topology"] == "fcu"
        assert item["max_rmsd"] < 0.3

def test_assembly_zinc_triazole_oxalate():
    """雙配體典型案例 (CALF-20): Zn-oxalate composite SBU (N73, CN=4) + triazole (E37, CN=2) in dia topology."""
    # 雙配體在幾何上降維為單一 SBU + 主 Linker 連接
    res = run_pormake_assembly(
        node_code="N73",
        linker_code="E37",
        node_cn=4,
        linker_cn=2,
        topology="dia"
    )

    assert res["status"] == "succeeded", f"Assembly failed: {res.get('failures')}"
    assert len(res["results"]) > 0
    for item in res["results"]:
        assert item["topology"] == "dia"
        assert item["max_rmsd"] < 0.3

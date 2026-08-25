import os
import json
import pytest
from pathlib import Path
from backend.config import DATA_DIR
from backend.services.mof.pormake_catalog import (
    resolve_proposal_mof,
    _CACHE_PATH,
    get_full_catalog,
)

# Mock catalog database to isolate tests from local PORMAKE environment status
MOCK_TEST_CATALOG = [
    {
        "id": "N409",
        "label": "N409 (CN: 4, Formula: C4Cu2O8X4)",
        "pormake_code": "N409",
        "role": "node",
        "coordination_number": 4,
    },
    {
        "id": "N419",
        "label": "N419 (CN: 12, Formula: C12O32X12Zr6)",
        "pormake_code": "N419",
        "role": "node",
        "coordination_number": 12,
    },
    {
        "id": "N105_Zn_oxalate",
        "label": "N105_Zn_oxalate (CN: 4, Formula: C2O4ZnX4)",
        "pormake_code": "N105_Zn_oxalate",
        "role": "node",
        "coordination_number": 4,
    },
    {
        "id": "N10",
        "label": "N10 (CN: 3, Formula: C6H3X3)",
        "pormake_code": "N10",
        "role": "linker",
        "coordination_number": 3,
    },
    {
        "id": "E14",
        "label": "E14 (CN: 2, Formula: C6H4X2)",
        "pormake_code": "E14",
        "role": "linker",
        "coordination_number": 2,
    },
    {
        "id": "E37",
        "label": "E37 (CN: 2, Formula: C2HN3X2)",
        "pormake_code": "E37",
        "role": "linker",
        "coordination_number": 2,
    },
    {
        "id": "E13",
        "label": "E13 (CN: 2, Formula: C2O4X2)",
        "pormake_code": "E13",
        "role": "linker",
        "coordination_number": 2,
    },
]


@pytest.fixture(autouse=True)
def setup_test_catalog_cache(monkeypatch):
    """Setup a temporary mock catalog JSON cache for tests and force reload."""
    # Ensure cache directory exists
    _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Save original cache content if exists to restore later
    original_cache = None
    if _CACHE_PATH.is_file():
        original_cache = _CACHE_PATH.read_text(encoding="utf-8")

    # Write mock test catalog
    _CACHE_PATH.write_text(json.dumps(MOCK_TEST_CATALOG, indent=2), encoding="utf-8")

    # Clear memory cache global variable in pormake_catalog
    import backend.services.mof.pormake_catalog as pc
    monkeypatch.setattr(pc, "_CACHED_CATALOG", None)

    yield

    # Restore original cache
    if original_cache is not None:
        _CACHE_PATH.write_text(original_cache, encoding="utf-8")
    elif _CACHE_PATH.is_file():
        os.remove(str(_CACHE_PATH))

    monkeypatch.setattr(pc, "_CACHED_CATALOG", None)


def test_resolve_single_linker_cu_btc():
    """Test resolution of single linker Cu + BTC case."""
    # BTC SMILES: C1=C(C=C(C=C1C(=O)O)C(=O)O)C(=O)O
    btc_smiles = "C1=C(C=C(C=C1C(=O)O)C(=O)O)C(=O)O"
    result = resolve_proposal_mof(metal_element="Cu", linker_smiles=btc_smiles)

    assert result["status"] == "success"
    assert result["node_id"] == "N409"  # Cu SBU
    assert result["linker_id"] == "N10"   # BTC Linker


def test_resolve_single_linker_zr_bdc():
    """Test resolution of single linker Zr + BDC case."""
    # BDC SMILES: C1=CC(=CC=C1C(=O)O)C(=O)O
    bdc_smiles = "C1=CC(=CC=C1C(=O)O)C(=O)O"
    result = resolve_proposal_mof(metal_element="Zr", linker_smiles=bdc_smiles)

    assert result["status"] == "success"
    assert result["node_id"] == "N419"  # Zr6 SBU
    assert result["linker_id"] == "E14"    # BDC Linker (E14)


def test_resolve_double_linker_zinc_triazole_oxalate():
    """Test resolution of double linker Zn + triazole + oxalate (CALF-20 case)."""
    triazole_smiles = "C1=NC=NN1"
    oxalate_smiles = "C(=O)(C(=O)O)O"

    # Test case 1: triazole as linker_smiles, oxalate as linker_smiles_2
    result1 = resolve_proposal_mof(
        metal_element="Zn",
        linker_smiles=triazole_smiles,
        linker_smiles_2=oxalate_smiles
    )

    assert result1["status"] == "success"
    # Zn + oxalate should map to N105_Zn_oxalate composite node
    assert result1["node_id"] == "N105_Zn_oxalate"
    # Main linker should be triazole (E37)
    assert result1["linker_id"] == "E37"

    # Test case 2: oxalate as linker_smiles, triazole as linker_smiles_2 (order swap)
    result2 = resolve_proposal_mof(
        metal_element="Zn",
        linker_smiles=oxalate_smiles,
        linker_smiles_2=triazole_smiles
    )

    assert result2["status"] == "success"
    assert result2["node_id"] == "N105_Zn_oxalate"
    assert result2["linker_id"] == "E37"


def test_resolve_fuzzy_linker_matching():
    """Test fuzzy linker matching when smiles is not in static map."""
    # Mocking a molecule that is a chemically valid derivative of BDC
    similar_smiles = "Cc1cc(C(=O)O)ccc1C(=O)O"  # 2-methyl-BDC (CN=2)
    result = resolve_proposal_mof(metal_element="Cu", linker_smiles=similar_smiles)

    assert result["status"] == "success"
    assert result["linker_id"] == "E14"  # Should match E14 due to MCSS containment and CN conservation


def test_resolve_invalid_inputs():
    """Test failure scenarios for invalid metal or linker."""
    # Invalid linker SMILES
    result1 = resolve_proposal_mof(metal_element="Cu", linker_smiles="XYZ_INVALID_SMILES")
    assert result1["status"] == "failed"
    assert "無法將配體" in result1["message"]

    # Metal not in database (no corresponding SBU or formula element)
    result2 = resolve_proposal_mof(metal_element="U", linker_smiles="C1=NC=NN1")  # Uranium (U)
    assert result2["status"] == "failed"
    assert "無法為金屬元素 U 找到" in result2["message"]

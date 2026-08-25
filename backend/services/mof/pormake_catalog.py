from __future__ import annotations

import os
import json
import subprocess
from pathlib import Path
from typing import Any
from backend.config import MOF_DATA_DIR

# Keep the original HKUST-1 examples as fallback just in case
_FALLBACK_CATALOG = [
    {
        "id": "cu-paddlewheel",
        "label": "Cu paddlewheel",
        "pormake_code": "N409",
        "role": "node",
        "coordination_number": 4,
    },
    {
        "id": "btc",
        "label": "BTC (benzene-1,3,5-tricarboxylate)",
        "pormake_code": "N10",
        "role": "node",
        "coordination_number": 3,
    },
]

# Cache file inside MOF_DATA_DIR
_CACHE_PATH = Path(MOF_DATA_DIR) / "pormake_catalog_cache.json"

_CACHED_CATALOG: list[dict[str, Any]] | None = None

def _generate_cache() -> list[dict[str, Any]]:
    # Find pormake python executable
    mof_dir = Path(MOF_DATA_DIR)
    python_exe = mof_dir / "tool_envs" / "pormake" / "bin" / "python"

    if not python_exe.is_file():
        # If pormake environment is not ready, return fallback catalog
        return _FALLBACK_CATALOG

    # Run Python subprocess to load pormake and dump its building block catalog
    code = """
import json
import pormake as pm
try:
    db = pm.Database()
    catalog = []
    for name in db.bb_list:
        bb = db.get_bb(name)
        role = "node" if (bb.is_node and bb.has_metal) else "linker"
        formula = bb.atoms.get_chemical_formula()
        catalog.append({
            "id": name,
            "label": f"{name} (CN: {bb.n_connection_points}, Formula: {formula})",
            "pormake_code": name,
            "role": role,
            "coordination_number": bb.n_connection_points,
        })
    print(json.dumps(catalog))
except Exception as e:
    import sys
    sys.stderr.write(str(e))
    sys.exit(1)
"""
    try:
        result = subprocess.run(
            [str(python_exe), "-c", code],
            capture_output=True,
            text=True,
            timeout=15,
            check=True
        )
        data = json.loads(result.stdout)
        # Ensure directory exists before writing cache
        _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _CACHE_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    except Exception as e:
        # Fall back to curated list if command fails
        return _FALLBACK_CATALOG

def get_full_catalog() -> list[dict[str, Any]]:
    global _CACHED_CATALOG
    if _CACHED_CATALOG is not None and len(_CACHED_CATALOG) > 2:
        return _CACHED_CATALOG

    if _CACHE_PATH.is_file():
        try:
            data = json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
            if len(data) > 2:
                _CACHED_CATALOG = data
                return _CACHED_CATALOG
        except Exception:
            pass

    # Generate if not cached
    data = _generate_cache()
    if len(data) > 2:
        _CACHED_CATALOG = data
    return data

def get_public_catalog() -> list[dict[str, Any]]:
    catalog = get_full_catalog()
    return [
        {
            "id": item["id"],
            "label": item["label"],
            "role": item["role"],
            "coordination_number": item["coordination_number"],
        }
        for item in catalog
    ]

def resolve_catalog_id(catalog_id: str) -> dict[str, Any]:
    # Keep the public friendly IDs and the PORMAKE codes accepted at this
    # boundary. The Proposal Demo already carries the packaged fixture codes.
    if catalog_id == "N409":
        catalog_id = "cu-paddlewheel"
    elif catalog_id == "N10":
        catalog_id = "btc"

    if catalog_id == "cu-paddlewheel":
        return {
            "id": "cu-paddlewheel",
            "label": "Cu paddlewheel",
            "pormake_code": "N409",
            "role": "node",
            "coordination_number": 4,
        }
    if catalog_id == "btc":
        return {
            "id": "btc",
            "label": "BTC (benzene-1,3,5-tricarboxylate)",
            "pormake_code": "N10",
            "role": "node",  # Keep legacy role node for compatibility
            "coordination_number": 3,
        }

    catalog = get_full_catalog()
    for item in catalog:
        if item["id"] == catalog_id:
            return dict(item)
    raise KeyError(catalog_id)

# --- Mappings for proposal translation ---

_COMMON_METAL_SBU_MAP = {
    'Al': [('N50', 4, 'Al-OH chain SBU (MIL-53 type)')],
    'Co': [('N697', 4, 'Co paddlewheel SBU'), ('N167', 6, 'Co trimeric SBU')],
    'Cr': [('N536', 6, 'Cr3O trimeric SBU (MIL-101 type)')],
    'Cu': [('N409', 4, 'Cu paddlewheel (HKUST-1 type)')],
    'Fe': [('N481', 6, 'Fe3O trimeric SBU (MIL-100 type)'), ('N355', 4, 'Fe paddlewheel SBU')],
    'Ni': [('N649', 4, 'Ni paddlewheel SBU'), ('N589', 6, 'Ni trimeric SBU')],
    'Zn': [('N577', 6, 'Zn4O cluster (MOF-5 type)'), ('N73', 4, 'Zn SBU')],
    'Zr': [('N419', 12, 'Zr6 oxo-cluster (UiO-66 type)')]
}

try:
    from rdkit import Chem
    from rdkit.Chem import rdFMCS

    def _parse_and_canon(s: str) -> str:
        mol = Chem.MolFromSmiles(s)
        return Chem.MolToSmiles(mol, canonical=True) if mol else s

    _LIGAND_SMILES_MAP = {
        _parse_and_canon('O=C(O)c1ccc(C(=O)O)cc1'): 'E14',                   # BDC
        _parse_and_canon('O=C(O)c1ccc(-c2ccc(C(=O)O)cc2)cc1'): 'E34',         # BPDC
        _parse_and_canon('O=C(O)c1cc(C(=O)O)cc(C(=O)O)c1'): 'N10',           # BTC
        _parse_and_canon('O=C(O)C=CC(=O)O'): 'E19',                          # Fumaric acid
        _parse_and_canon('c1nc[nH]n1'): 'E37',                               # 1H-1,2,3-triazole
        _parse_and_canon('c1c[nH]cn1'): 'E146',                              # Imidazole
        _parse_and_canon('c1ccc(-c2ccccn2)nc1'): 'E35',                      # 2,2'-bipyridine
        _parse_and_canon('C1=CN=CC=C1C2=CC=NC=C2'): 'E35',                    # 4,4'-bipyridine
        _parse_and_canon('C1=CC(=CC=C1C(=C(C2=CC=C(C=C2)C(=O)O)C3=CC=C(C=C3)C(=O)O)C4=CC=C(C=C4)C(=O)O)C(=O)O'): 'N12', # TCPE
        _parse_and_canon('C1=CC(=CC=C1C2=CC(=C3C=CC4=C(C=C(C5=C4C3=C2C=C5)C6=CC=C(C=C6)C(=O)O)C7=CC=C(C=C7)C(=O)O)C8=CC=C(C=C8)C(=O)O)C(=O)O'): 'N1', # TBAPy
    }

    # We specify representative backbones explicitly (E35 uses 4,4'-bipyridine for MCSS derivatives matching)
    _REPRESENTATIVE_BACKBONES = {
        'E14': 'O=C(O)c1ccc(C(=O)O)cc1',
        'E34': 'O=C(O)c1ccc(-c2ccc(C(=O)O)cc2)cc1',
        'N10': 'O=C(O)c1cc(C(=O)O)cc(C(=O)O)c1',
        'E19': 'O=C(O)C=CC(=O)O',
        'E37': 'c1nc[nH]n1',
        'E146': 'c1c[nH]cn1',
        'E35': 'C1=CN=CC=C1C2=CC=NC=C2',  # 4,4'-bipyridine as representative
        'N12': 'C1=CC(=CC=C1C(=C(C2=CC=C(C=C2)C(=O)O)C3=CC=C(C=C3)C(=O)O)C4=CC=C(C=C4)C(=O)O)C(=O)O',
        'N1': 'C1=CC(=CC=C1C2=CC(=C3C=CC4=C(C=C(C5=C4C3=C2C=C5)C6=CC=C(C=C6)C(=O)O)C7=CC=C(C=C7)C(=O)O)C8=CC=C(C=C8)C(=O)O)C(=O)O'
    }

    _BACKBONES = {
        k: Chem.MolFromSmiles(smiles)
        for k, smiles in _REPRESENTATIVE_BACKBONES.items()
    }
except ImportError:
    _LIGAND_SMILES_MAP = {
        'O=C(O)c1ccc(C(=O)O)cc1': 'E14',
        'O=C(O)c1ccc(-c2ccc(C(=O)O)cc2)cc1': 'E34',
        'O=C(O)c1cc(C(=O)O)cc(C(=O)O)c1': 'N10',
        'O=C(O)C=CC(=O)O': 'E19',
        'c1nc[nH]n1': 'E37',
        'c1c[nH]cn1': 'E146',
        'c1ccc(-c2ccccn2)nc1': 'E35',
        'C1=CN=CC=C1C2=CC=NC=C2': 'E35'
    }
    _BACKBONES = {}


def count_carboxyls(mol) -> int:
    try:
        from rdkit import Chem
        pattern = Chem.MolFromSmarts('C(=O)[O;H1,H0-]')
        return len(mol.GetSubstructMatches(pattern))
    except ImportError:
        # Fallback if rdkit is missing
        return 0


def fuzzy_match_linker(smiles: str) -> str | None:
    """
    Use Maximum Common Substructure (MCSS) to map a proposed ligand SMILES
    to the closest standard PORMAKE backbone linker, applying CN conservation
    and substituent size-ratio thresholds.
    """
    # 1. First check if exact canonical SMILES is in the static map (fast path)
    exact_match = _LIGAND_SMILES_MAP.get(smiles)
    if exact_match:
        return exact_match

    try:
        from rdkit import Chem
        from rdkit.Chem import rdFMCS
    except ImportError:
        return _LIGAND_SMILES_MAP.get(smiles)

    proposed_mol = Chem.MolFromSmiles(smiles)
    if not proposed_mol:
        return None

    try:
        Chem.SanitizeMol(proposed_mol)
    except Exception:
        pass

    proposed_heavy_atoms = proposed_mol.GetNumHeavyAtoms()
    orig_carboxyls = count_carboxyls(proposed_mol)

    best_match = None

    for bb_id, bb_mol in _BACKBONES.items():
        if bb_mol is None:
            continue
        bb_mol_cp = Chem.Mol(bb_mol)
        try:
            Chem.SanitizeMol(bb_mol_cp)
        except Exception:
            pass
        bb_heavy_atoms = bb_mol_cp.GetNumHeavyAtoms()

        # Run MCS with connectivity constraints
        mcs_res = rdFMCS.FindMCS(
            [proposed_mol, bb_mol_cp],
            completeRingsOnly=True,
            ringMatchesRingOnly=True,
            timeout=3
        )

        # Check if backbone is 100% contained in the proposed molecule
        if mcs_res.numAtoms == bb_heavy_atoms:
            substituent_ratio = (proposed_heavy_atoms - bb_heavy_atoms) / proposed_heavy_atoms

            # Check gates: substituent ratio <= 40% AND carboxyl count is conserved
            size_pass = substituent_ratio <= 0.40

            bb_carboxyls = count_carboxyls(bb_mol_cp)
            cn_pass = orig_carboxyls == bb_carboxyls

            if size_pass and cn_pass:
                best_match = bb_id
                break

    return best_match


def resolve_proposal_mof(
    metal_element: str,
    linker_smiles: str,
    linker_smiles_2: str | None = None
) -> dict[str, Any]:
    """
    將 AI 提案中的金屬元素與配體 SMILES 映射到 PORMAKE 資料庫中的 Node 與 Linker 代號。

    採用高精確度的最大公共子結構 (MCSS) 比對機制對接配體骨架。
    """
    from rdkit import Chem

    # 1. 規範化輸入
    metal = metal_element.strip()

    def canonicalize_smiles(s: str | None) -> str | None:
        if not s or not s.strip():
            return None
        try:
            mol = Chem.MolFromSmiles(s.strip())
            if mol:
                return Chem.MolToSmiles(mol, canonical=True)
        except Exception:
            pass
        return s.strip()

    l1_smiles = canonicalize_smiles(linker_smiles)
    l2_smiles = canonicalize_smiles(linker_smiles_2)

    # 2. 配體角色判定與映射
    auxiliary_smiles_list = [
        canonicalize_smiles("C(=O)(C(=O)O)O"),  # oxalic acid
        canonicalize_smiles("C(=O)O"),          # formic acid / formate
        canonicalize_smiles("CC(=O)O"),         # acetic acid / acetate
        canonicalize_smiles("O"),               # water
    ]

    main_smiles = None
    aux_smiles = None

    # 如果有兩個配體，判斷誰主誰輔
    if l1_smiles and l2_smiles:
        is_l1_aux = l1_smiles in auxiliary_smiles_list
        is_l2_aux = l2_smiles in auxiliary_smiles_list

        if is_l2_aux and not is_l1_aux:
            main_smiles = l1_smiles
            aux_smiles = l2_smiles
        elif is_l1_aux and not is_l2_aux:
            main_smiles = l2_smiles
            aux_smiles = l1_smiles
        else:
            # 都不在名單中：如果兩者都是較大的有機配體 (MTV-MOF)，忽略第二配體，降級為單配體模式
            try:
                mol1 = Chem.MolFromSmiles(l1_smiles)
                mol2 = Chem.MolFromSmiles(l2_smiles)
                na1 = mol1.GetNumHeavyAtoms() if mol1 else 0
                na2 = mol2.GetNumHeavyAtoms() if mol2 else 0

                # 如果兩者重原子數都大於 5，代表都不是小分子輔助配體
                if na1 > 5 and na2 > 5:
                    main_smiles = l1_smiles
                    aux_smiles = None
                else:
                    if na1 < na2:
                        main_smiles = l2_smiles
                        aux_smiles = l1_smiles
                    else:
                        main_smiles = l1_smiles
                        aux_smiles = l2_smiles
            except Exception:
                main_smiles = l1_smiles
                aux_smiles = None
    else:
        # 單配體
        main_smiles = l1_smiles or l2_smiles

    if not main_smiles:
        return {
            "status": "failed",
            "message": f"無法將配體對接至 PORMAKE 資料庫，未提供有效的主要配體 SMILES",
        }

    # 3. 對接主要配體
    main_linker_id = fuzzy_match_linker(main_smiles)

    if not main_linker_id:
        return {
            "status": "failed",
            "message": f"無法將配體 SMILES 對接至 PORMAKE 資料庫: {linker_smiles}",
        }

    # 4. 金屬 Node 映射與複合 Node 過濾
    catalog = get_full_catalog()
    matched_node_id = None

    # 4.1 雙配體複合 Node 尋找 (如 Zn + oxalate)
    if aux_smiles:
        target_c = 0
        target_o = 0
        try:
            mol_aux = Chem.MolFromSmiles(aux_smiles)
            if mol_aux:
                target_c = sum(1 for a in mol_aux.GetAtoms() if a.GetSymbol() == 'C')
                target_o = sum(1 for a in mol_aux.GetAtoms() if a.GetSymbol() == 'O')
        except Exception:
            pass

        for item in catalog:
            if item["role"] == "node":
                label = item.get("label", "")
                formula_part = ""
                if "Formula: " in label:
                    formula_part = label.split("Formula: ")[1].split(")")[0]

                has_metal_symbol = metal in formula_part
                import re
                def get_atom_count(sym):
                    match = re.search(rf"{sym}(\d+)", formula_part)
                    if match:
                        return int(match.group(1))
                    if sym in formula_part:
                        return 1
                    return 0

                c_num = get_atom_count("C")
                o_num = get_atom_count("O")

                if has_metal_symbol and c_num >= target_c and o_num >= target_o:
                    matched_node_id = item["id"]
                    break

    # 4.2 常規金屬 SBU 映射
    if not matched_node_id:
        sbus = _COMMON_METAL_SBU_MAP.get(metal)
        if sbus:
            matched_node_id = sbus[0][0]
        else:
            # 若不在對照表中，挑選第一個含有該金屬元素的 Node
            for item in catalog:
                if item["role"] == "node":
                    label = item.get("label", "")
                    if f"Formula: " in label and metal in label.split("Formula: ")[1]:
                        matched_node_id = item["id"]
                        break

    if not matched_node_id:
        return {
            "status": "failed",
            "message": f"無法為金屬元素 {metal} 找到相容的 PORMAKE 金屬節點",
        }

    return {
        "status": "success",
        "node_id": matched_node_id,
        "linker_id": main_linker_id,
        "linker_id_2": None,
        "message": f"成功對接：金屬節點 {matched_node_id}，有機配體1 {main_linker_id}",
    }

"""Resolve user-facing metal/linker inputs to conservative PORMAKE candidates."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import re
from typing import Any
from urllib.parse import quote

import requests
from rdkit import Chem
from rdkit import rdBase

from .pormake_pairing import PairingMatcher, PormakeFragmentIndex
from .tool_env_service import ToolEnvService


_METAL_NAMES = {
    "aluminum": "Al",
    "aluminium": "Al",
    "cobalt": "Co",
    "chromium": "Cr",
    "copper": "Cu",
    "iron": "Fe",
    "magnesium": "Mg",
    "manganese": "Mn",
    "nickel": "Ni",
    "scandium": "Sc",
    "titanium": "Ti",
    "vanadium": "V",
    "zinc": "Zn",
    "zirconium": "Zr",
    "hafnium": "Hf",
    "cadmium": "Cd",
}

_LINKER_ALIASES = {
    "btc": "O=C(O)c1cc(C(=O)O)cc(C(=O)O)c1",
    "trimesic acid": "O=C(O)c1cc(C(=O)O)cc(C(=O)O)c1",
    "1,3,5-benzenetricarboxylic acid": "O=C(O)c1cc(C(=O)O)cc(C(=O)O)c1",
    "benzene-1,3,5-tricarboxylic acid": "O=C(O)c1cc(C(=O)O)cc(C(=O)O)c1",
    "bdc": "O=C(O)c1ccc(C(=O)O)cc1",
    "terephthalic acid": "O=C(O)c1ccc(C(=O)O)cc1",
    "1,4-benzenedicarboxylic acid": "O=C(O)c1ccc(C(=O)O)cc1",
    "benzene-1,4-dicarboxylic acid": "O=C(O)c1ccc(C(=O)O)cc1",
    "2-aminoterephthalic acid": "Nc1cc(C(=O)O)ccc1C(=O)O",
    "amino-bdc": "Nc1cc(C(=O)O)ccc1C(=O)O",
    "bpdc": "O=C(O)c1ccc(-c2ccc(C(=O)O)cc2)cc1",
    "biphenyl-4,4'-dicarboxylic acid": "O=C(O)c1ccc(-c2ccc(C(=O)O)cc2)cc1",
    "fumaric acid": "O=C(O)/C=C/C(=O)O",
    "oxalic acid": "O=C(O)C(=O)O",
    "2-methylimidazole": "Cc1c[nH]cn1",
    "1,2,4-triazole": "c1nnc[nH]1",
    "4,4-bipyridine": "c1cc(-c2ccncc2)ccn1",
    "4,4'-bipyridine": "c1cc(-c2ccncc2)ccn1",
    "4,4-bipyridyl": "c1cc(-c2ccncc2)ccn1",
    "4,4'-bipyridyl": "c1cc(-c2ccncc2)ccn1",
}

_COMMON_SBU_PRIORS = {
    "Al": ("N50",),
    "Co": ("N697", "N167"),
    "Cr": ("N536",),
    "Cu": ("N409",),
    "Fe": ("N481", "N355"),
    "Ni": ("N649", "N589"),
    "Zn": ("N577", "N73"),
    "Zr": ("N419",),
}


class LinkerResolutionError(ValueError):
    """Raised when a linker name/SMILES cannot be resolved safely."""


def normalize_metal_input(value: str) -> str:
    """Normalize an element symbol or common English metal name."""
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("Metal is required.")

    symbol = cleaned[0].upper() + cleaned[1:].lower()
    if re.fullmatch(r"[A-Z][a-z]?", symbol):
        try:
            if Chem.GetPeriodicTable().GetAtomicNumber(symbol) > 0:
                return symbol
        except RuntimeError:
            pass

    lowered = cleaned.casefold()
    for name, candidate in _METAL_NAMES.items():
        if re.search(rf"\b{re.escape(name)}\b", lowered):
            return candidate
    raise ValueError(f"Unsupported metal name or element symbol: {value}")


def _canonicalize(smiles: str) -> str | None:
    with rdBase.BlockLogs():
        mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    return Chem.MolToSmiles(mol, canonical=True, isomericSmiles=True)


def _resolve_name_from_pubchem(name: str) -> tuple[str, dict[str, Any]]:
    encoded = quote(name, safe="")
    url = (
        "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/"
        f"{encoded}/property/CanonicalSMILES,IsomericSMILES,IUPACName/JSON"
    )
    response = requests.get(url, timeout=8)
    response.raise_for_status()
    properties = response.json().get("PropertyTable", {}).get("Properties", [])
    if not properties:
        raise LinkerResolutionError(f"PubChem did not resolve linker name: {name}")
    item = properties[0]
    smiles = (
        item.get("IsomericSMILES")
        or item.get("CanonicalSMILES")
        or item.get("SMILES")
        or item.get("ConnectivitySMILES")
    )
    if not smiles:
        raise LinkerResolutionError(f"PubChem returned no SMILES for: {name}")
    return smiles, {
        "source": "pubchem",
        "query": name,
        "cid": item.get("CID"),
        "resolved_name": item.get("IUPACName") or name,
    }


def resolve_linker_input(value: str) -> tuple[str, dict[str, Any]]:
    """Resolve a SMILES string or chemical name to canonical SMILES."""
    cleaned = value.strip()
    if not cleaned:
        raise LinkerResolutionError("Linker name or SMILES is required.")

    alias = _LINKER_ALIASES.get(cleaned.casefold())
    if alias:
        canonical = _canonicalize(alias)
        if canonical:
            return canonical, {
                "source": "curated-name",
                "query": cleaned,
                "resolved_name": cleaned,
                "cid": None,
            }

    direct = _canonicalize(cleaned)
    if direct:
        return direct, {
            "source": "smiles",
            "query": cleaned,
            "resolved_name": None,
            "cid": None,
        }

    try:
        smiles, provenance = _resolve_name_from_pubchem(cleaned)
    except (requests.RequestException, ValueError, KeyError) as exc:
        raise LinkerResolutionError(
            f"Could not resolve linker name '{cleaned}'. Enter a valid SMILES or "
            "a PubChem-recognized chemical name."
        ) from exc

    canonical = _canonicalize(smiles)
    if not canonical:
        raise LinkerResolutionError(
            f"Resolved chemical structure for '{cleaned}' is not a valid SMILES."
        )
    return canonical, provenance


@lru_cache(maxsize=4)
def _load_matcher(bb_dir: str, fingerprint: tuple[int, int]) -> PairingMatcher:
    del fingerprint
    return PairingMatcher(PormakeFragmentIndex.from_directory(bb_dir))


def _catalog_fingerprint(bb_dir: Path) -> tuple[int, int]:
    files = list(bb_dir.glob("*.xyz"))
    newest = max((path.stat().st_mtime_ns for path in files), default=0)
    return len(files), newest


def resolve_pormake_candidates(
    *,
    metal: str,
    linker: str,
    tool_env_service: ToolEnvService,
    max_candidates: int = 5,
) -> dict[str, Any]:
    """Return exact auto-generatable candidates and diagnostic scaffold matches."""
    metal_element = normalize_metal_input(metal)
    linker_smiles, identity = resolve_linker_input(linker)
    bb_dir = tool_env_service.get_building_blocks_dir()
    if bb_dir is None:
        raise FileNotFoundError("PORMAKE building-block database is not available.")

    matcher = _load_matcher(str(bb_dir), _catalog_fingerprint(bb_dir))
    result = matcher.match(
        metal=metal_element,
        linker_smiles=linker_smiles,
        max_results=500,
    )

    exact = [
        candidate
        for candidate in result.candidates
        if candidate.match_kind == "exact"
    ]
    priors = _COMMON_SBU_PRIORS.get(metal_element, ())
    exact.sort(
        key=lambda candidate: (
            priors.index(candidate.metal_id)
            if candidate.metal_id in priors
            else len(priors),
            -candidate.confidence,
            -candidate.organic_coordination_number,
            candidate.organic_id,
            candidate.metal_id,
        )
    )
    exact = exact[:max_candidates]
    scaffold = [
        candidate
        for candidate in result.candidates
        if candidate.match_kind == "scaffold"
    ][:3]

    def serialize(candidate, auto_generatable: bool) -> dict[str, Any]:
        payload = candidate.to_dict()
        payload["node_id"] = candidate.metal_id
        payload["linker_id"] = candidate.organic_id
        payload["auto_generatable"] = auto_generatable
        payload["compatible_topologies"] = (
            tool_env_service.get_compatible_topologies(
                candidate.metal_id, candidate.organic_id
            )
            if auto_generatable
            else []
        )
        return payload

    candidates = [serialize(candidate, True) for candidate in exact]
    suggestions = [serialize(candidate, False) for candidate in scaffold]
    if candidates:
        status = "success"
        message = f"Found {len(candidates)} exact PORMAKE candidate(s)."
    elif suggestions:
        status = "scaffold_only"
        message = (
            "Only scaffold matches were found. Automatic CIF generation is "
            "disabled because linker atoms would be omitted."
        )
    else:
        status = result.status
        message = "No atom-complete PORMAKE candidate was found."

    return {
        "status": status,
        "metal_element": metal_element,
        "linker_smiles": linker_smiles,
        "linker_identity": identity,
        "candidates": candidates,
        "scaffold_suggestions": suggestions,
        "diagnostics": result.diagnostics,
        "message": message,
    }

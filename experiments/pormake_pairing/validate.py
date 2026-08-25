from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from .matcher import PairingMatcher, PormakeFragmentIndex


CASES = (
    {
        "name": "Cu_BTC",
        "metal": "Cu",
        "smiles": "O=C(O)c1cc(C(=O)O)cc(C(=O)O)c1",
        "expected_pair": ("N409", "N10"),
        "expected_kind": "exact",
    },
    {
        "name": "Zr_BDC",
        "metal": "Zr",
        "smiles": "O=C(O)c1ccc(C(=O)O)cc1",
        "expected_pair": ("N419", "E14"),
        "expected_kind": "exact",
    },
    {
        "name": "Zn_fumarate",
        "metal": "Zn",
        "smiles": "O=C(O)/C=C/C(=O)O",
        "expected_pair": ("N577", "E19"),
        "expected_kind": "exact",
    },
    {
        "name": "Zr_amino_BDC",
        "metal": "Zr",
        "smiles": "Nc1cc(C(=O)O)ccc1C(=O)O",
        "expected_pair": ("N419", "E72"),
        "expected_kind": "exact",
    },
    {
        "name": "Zr_BPDC",
        "metal": "Zr",
        "smiles": "O=C(O)c1ccc(-c2ccc(C(=O)O)cc2)cc1",
        "expected_pair": ("N419", "E34"),
        "expected_kind": "exact",
    },
    {
        "name": "Zr_methyl_BDC_fallback",
        "metal": "Zr",
        "smiles": "Cc1cc(C(=O)O)ccc1C(=O)O",
        "expected_pair": ("N419", "E14"),
        "expected_kind": "scaffold",
    },
    {
        "name": "Cu_dicyanobenzene",
        "metal": "Cu",
        "smiles": "N#Cc1ccc(C#N)cc1",
        "expected_pair": ("N307", "E14"),
        "expected_kind": "exact",
    },
    {
        "name": "Cu_benzene_disulfonate",
        "metal": "Cu",
        "smiles": "O=S(=O)(O)c1ccc(S(=O)(=O)O)cc1",
        "expected_pair": ("N518", "E14"),
        "expected_kind": "exact",
    },
    {
        "name": "Zn_benzene_diphosphonate",
        "metal": "Zn",
        "smiles": "O=P(O)(O)c1ccc(P(=O)(O)O)cc1",
        "expected_pair": ("N529", "E14"),
        "expected_kind": "exact",
    },
    {
        "name": "Cu_bipyridine_conservative_no_match",
        "metal": "Cu",
        "smiles": "n1ccc(-c2ccncc2)cc1",
        "expected_status": "no_match",
    },
)


def _discover_bb_dir() -> Path | None:
    configured = os.getenv("PORMAKE_BB_DIR")
    if configured:
        path = Path(configured).expanduser()
        if path.is_dir():
            return path

    repo_root = Path(__file__).resolve().parents[2]
    local_env = repo_root / "local_data" / "mof" / "tool_envs" / "pormake"
    for path in local_env.glob("lib/python*/site-packages/pormake/database/bbs"):
        if path.is_dir():
            return path

    sibling_checkout = repo_root.parent / "PORMAKE" / "src" / "pormake" / "database" / "bbs"
    if sibling_checkout.is_dir():
        return sibling_checkout
    return None


def run_validation(bb_dir: Path, *, max_results: int = 500) -> dict:
    started = time.perf_counter()
    index = PormakeFragmentIndex.from_directory(bb_dir)
    matcher = PairingMatcher(index)
    index_seconds = time.perf_counter() - started

    reports = []
    for case in CASES:
        case_started = time.perf_counter()
        result = matcher.match(
            metal=case["metal"],
            linker_smiles=case["smiles"],
            max_results=max_results,
        )
        expected_pair = case.get("expected_pair")
        if expected_pair is None:
            expected_rank = None
            case_passed = result.status == case["expected_status"]
        else:
            expected_rank = next(
                (
                    index + 1
                    for index, candidate in enumerate(result.candidates)
                    if (candidate.metal_id, candidate.organic_id) == expected_pair
                    and candidate.match_kind == case["expected_kind"]
                ),
                None,
            )
            case_passed = expected_rank is not None
        reports.append(
            {
                "name": case["name"],
                "status": result.status,
                "passed": case_passed,
                "expected_pair": list(expected_pair) if expected_pair else None,
                "expected_status": case.get("expected_status", "matched"),
                "expected_rank": expected_rank,
                "candidate_count": len(result.candidates),
                "exact_candidate_count": sum(
                    candidate.match_kind == "exact"
                    for candidate in result.candidates
                ),
                "organic_modes": sorted(
                    {candidate.organic_id for candidate in result.candidates}
                ),
                "top_candidates": [
                    candidate.to_dict() for candidate in result.candidates[:10]
                ],
                "seconds": round(time.perf_counter() - case_started, 4),
            }
        )

    return {
        "bb_dir": str(bb_dir),
        "fragment_count": len(index.fragments),
        "parse_errors": index.parse_errors,
        "coverage": matcher.coverage_summary(),
        "index_seconds": round(index_seconds, 4),
        "passed": all(report["passed"] for report in reports),
        "cases": reports,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate dynamic metal/linker pairing against a PORMAKE BB database."
    )
    parser.add_argument("--bb-dir", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--max-results", type=int, default=500)
    parser.add_argument("--metal")
    parser.add_argument("--smiles")
    args = parser.parse_args(argv)

    bb_dir = args.bb_dir or _discover_bb_dir()
    if bb_dir is None:
        parser.error(
            "PORMAKE building-block directory not found; pass --bb-dir or set PORMAKE_BB_DIR."
        )

    if bool(args.metal) != bool(args.smiles):
        parser.error("--metal and --smiles must be supplied together.")

    if args.metal and args.smiles:
        index = PormakeFragmentIndex.from_directory(bb_dir)
        matcher = PairingMatcher(index)
        result = matcher.match(
            metal=args.metal,
            linker_smiles=args.smiles,
            max_results=args.max_results,
        )
        report = {
            "bb_dir": str(bb_dir),
            "coverage": matcher.coverage_summary(),
            "query": result.to_dict(),
        }
        exit_code = 0 if result.status == "matched" else 1
    else:
        report = run_validation(bb_dir, max_results=args.max_results)
        exit_code = 0 if report["passed"] else 1

    payload = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())

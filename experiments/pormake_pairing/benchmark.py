from __future__ import annotations

import argparse
import json
from statistics import mean, median
import time

from backend.config import MOF_DATA_DIR
from backend.services.mof.pormake_resolver import resolve_pormake_candidates
from backend.services.mof.tool_env_service import ToolEnvService


CASES = (
    {
        "name": "HKUST-1",
        "metal": "Cu",
        "linker": "O=C(O)c1cc(C(=O)O)cc(C(=O)O)c1",
        "expected_status": "success",
        "expected_pair": ("N409", "N10"),
    },
    {
        "name": "UiO-66",
        "metal": "Zr",
        "linker": "O=C(O)c1ccc(C(=O)O)cc1",
        "expected_status": "success",
        "expected_pair": ("N419", "E14"),
    },
    {
        "name": "UiO-66-NH2",
        "metal": "Zr",
        "linker": "Nc1cc(C(=O)O)ccc1C(=O)O",
        "expected_status": "success",
        "expected_pair": ("N419", "E72"),
    },
    {
        "name": "UiO-67",
        "metal": "Zr",
        "linker": "O=C(O)c1ccc(-c2ccc(C(=O)O)cc2)cc1",
        "expected_status": "success",
        "expected_pair": ("N419", "E34"),
    },
    {
        "name": "MOF-5",
        "metal": "Zn",
        "linker": "O=C(O)c1ccc(C(=O)O)cc1",
        "expected_status": "success",
        "expected_pair": ("N577", "E14"),
    },
    {
        "name": "MIL-53",
        "metal": "Al",
        "linker": "O=C(O)c1ccc(C(=O)O)cc1",
        "expected_status": "success",
        "expected_pair": ("N565", "E14"),
    },
    {
        "name": "MOF-801",
        "metal": "Zr",
        "linker": "O=C(O)/C=C/C(=O)O",
        "expected_status": "success",
        "expected_pair": ("N419", "E19"),
    },
    {
        "name": "Cu-dicyanobenzene",
        "metal": "Cu",
        "linker": "N#Cc1ccc(C#N)cc1",
        "expected_status": "success",
        "expected_pair": ("N307", "E14"),
    },
    {
        "name": "Cu-benzene-disulfonate",
        "metal": "Cu",
        "linker": "O=S(=O)(O)c1ccc(S(=O)(=O)O)cc1",
        "expected_status": "success",
        "expected_pair": ("N518", "E14"),
    },
    {
        "name": "Zn-benzene-diphosphonate",
        "metal": "Zn",
        "linker": "O=P(O)(O)c1ccc(P(=O)(O)O)cc1",
        "expected_status": "success",
        "expected_pair": ("N529", "E14"),
    },
    {
        "name": "methyl-BDC-scaffold",
        "metal": "Zr",
        "linker": "Cc1cc(C(=O)O)ccc1C(=O)O",
        "expected_status": "scaffold_only",
        "expected_pair": None,
    },
    {
        "name": "ZIF-8",
        "metal": "Zn",
        "linker": "Cc1ncc[nH]1",
        "expected_status": "no_match",
        "expected_pair": None,
    },
    {
        "name": "CALF-20-triazole",
        "metal": "Zn",
        "linker": "C1=NN=CN1",
        "expected_status": "no_match",
        "expected_pair": None,
    },
    {
        "name": "Cu-bipyridine",
        "metal": "Cu",
        "linker": "n1ccc(-c2ccncc2)cc1",
        "expected_status": "no_match",
        "expected_pair": None,
    },
)


def run_benchmark(repeats: int = 3) -> dict:
    service = ToolEnvService(MOF_DATA_DIR)
    rows = []
    for case_index, case in enumerate(CASES):
        timings = []
        result = None
        for _ in range(repeats):
            started = time.perf_counter()
            result = resolve_pormake_candidates(
                metal=case["metal"],
                linker=case["linker"],
                tool_env_service=service,
                max_candidates=10,
            )
            timings.append(time.perf_counter() - started)

        pairs = [
            (candidate["node_id"], candidate["linker_id"])
            for candidate in result["candidates"]
        ]
        expected_pair = case["expected_pair"]
        rank = pairs.index(expected_pair) + 1 if expected_pair in pairs else None
        diagnostics = result["diagnostics"]
        rows.append(
            {
                "name": case["name"],
                "expected_status": case["expected_status"],
                "actual_status": result["status"],
                "status_correct": result["status"] == case["expected_status"],
                "expected_pair": expected_pair,
                "expected_pair_rank": rank,
                "candidate_count": len(result["candidates"]),
                "signature_candidates": diagnostics.get(
                    "signature_candidate_count", 0
                ),
                "organic_core_count": diagnostics.get("organic_core_count", 0),
                "evaluated_pairs": diagnostics.get("evaluated_pair_count", 0),
                "first_seconds": round(timings[0], 6),
                "median_seconds": round(median(timings), 6),
                "min_seconds": round(min(timings), 6),
                "cold_case": case_index == 0,
            }
        )

    positives = [row for row in rows if row["expected_pair"] is not None]
    exact_recall = {
        f"recall_at_{cutoff}": round(
            sum(
                row["expected_pair_rank"] is not None
                and row["expected_pair_rank"] <= cutoff
                for row in positives
            )
            / len(positives),
            4,
        )
        for cutoff in (1, 5, 10)
    }
    warm_timings = [
        row["median_seconds"]
        for row in rows
        if not row["cold_case"]
    ]
    signature_ratios = [
        row["signature_candidates"] / row["organic_core_count"]
        for row in rows
        if row["organic_core_count"]
    ]
    return {
        "case_count": len(rows),
        "positive_exact_case_count": len(positives),
        "status_accuracy": round(
            sum(row["status_correct"] for row in rows) / len(rows), 4
        ),
        **exact_recall,
        "cold_start_seconds": rows[0]["first_seconds"],
        "warm_median_seconds": round(median(warm_timings), 6),
        "warm_mean_seconds": round(mean(warm_timings), 6),
        "mean_signature_retention": round(mean(signature_ratios), 4),
        "mean_signature_reduction": round(1 - mean(signature_ratios), 4),
        "rows": rows,
        "limitations": [
            "Curated regression benchmark, not a random sample of MOF space.",
            "Expected no_match cases measure conservative rejection, not chemistry recall.",
            "CIF assembly and predictor latency are measured separately.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    print(json.dumps(run_benchmark(max(args.repeats, 1)), indent=2))


if __name__ == "__main__":
    main()

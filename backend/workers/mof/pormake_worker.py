import argparse
import json
import os
import sys
from pathlib import Path


def get_cgd_coordination_numbers(cgd_path):
    cns = set()
    try:
        with open(cgd_path, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped.startswith("NODE"):
                    parts = stripped.split()
                    if len(parts) >= 3:
                        cns.add(int(parts[2]))
    except Exception:
        pass
    return cns


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--result", required=True)
    args = parser.parse_args()

    request_path = Path(args.request)
    result_path = Path(args.result)

    try:
        req = json.loads(request_path.read_text(encoding="utf-8"))
    except Exception as e:
        sys.stderr.write(f"Failed to read request: {e}\n")
        sys.exit(1)

    node_code = req["node_code"]
    linker_code = req["linker_code"]
    node_cn = req["node_cn"]
    linker_cn = req["linker_cn"]
    node_id = req["node_id"]
    linker_id = req["linker_id"]
    topology = req.get("topology")
    max_results = req.get("max_results", 10)
    output_dir = Path(req["output_dir"])

    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        import pormake as pm
    except ImportError as e:
        result_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "tool": "pormake",
                    "status": "failed",
                    "results": [],
                    "failures": [
                        {
                            "topology": "",
                            "error_code": "IMPORT_ERROR",
                            "message": f"pormake import failed: {str(e)}",
                        }
                    ],
                }
            )
        )
        sys.exit(0)

    db = pm.Database()
    builder = pm.Builder()

    try:
        node_bb = db.get_bb(node_code)
        linker_bb = db.get_bb(linker_code)
    except Exception as e:
        result_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "tool": "pormake",
                    "status": "failed",
                    "results": [],
                    "failures": [
                        {
                            "topology": "",
                            "error_code": "BB_NOT_FOUND",
                            "message": f"Building block not found in database: {str(e)}",
                        }
                    ],
                }
            )
        )
        sys.exit(0)

    # Determine target topologies
    if topology:
        filtered_topos = [topology]
    else:
        if linker_code.startswith("E") or linker_cn == 2:
            target_cn_set = {node_cn}
        else:
            target_cn_set = {node_cn, linker_cn}

        filtered_topos = []
        for name in db.topo_list:
            cgd_path = db.topo_dir / (name + ".cgd")
            if cgd_path.exists():
                cns = get_cgd_coordination_numbers(cgd_path)
                if cns == target_cn_set:
                    filtered_topos.append(name)

    results = []
    failures = []
    artifact_count = 0

    for topo_name in filtered_topos:
        if artifact_count >= max_results:
            break
        try:
            topo = db.get_topo(topo_name)

            node_type_to_cn = {}
            for slot_idx in topo.node_indices:
                t = topo.node_types[slot_idx]
                cn = topo.atoms.info["cn"][slot_idx]
                node_type_to_cn[t] = cn

            if linker_code.startswith("E") or linker_cn == 2:
                node_bbs = {}
                for t, cn in node_type_to_cn.items():
                    if cn == node_cn:
                        node_bbs[t] = node_bb
                edge_bbs = {
                    tuple(edge_type): linker_bb
                    for edge_type in topo.unique_edge_types
                }
            else:
                node_bbs = {}
                for t, cn in node_type_to_cn.items():
                    if cn == node_cn:
                        node_bbs[t] = node_bb
                    elif cn == linker_cn:
                        node_bbs[t] = linker_bb
                edge_bbs = None

            # Cheap geometry gate before scaling/building the full framework.
            # One representative slot per node type is sufficient because all
            # slots of a type share the same local topology geometry.
            representative_slots = {}
            for slot_idx in topo.node_indices:
                representative_slots.setdefault(topo.node_types[slot_idx], slot_idx)
            local_rmsds = []
            for node_type, bb in node_bbs.items():
                slot_idx = representative_slots[node_type]
                target = topo.local_structure(slot_idx)
                rmsd = builder.locator.calculate_rmsd(target, bb)
                chiral_rmsd = builder.locator.calculate_rmsd(
                    target, bb.make_chiral_building_block()
                )
                local_rmsds.append(min(float(rmsd), float(chiral_rmsd)))
            local_prefilter_rmsd = max(local_rmsds, default=0.0)
            if local_prefilter_rmsd >= 0.3:
                failures.append(
                    {
                        "topology": topo_name,
                        "error_code": "LOCAL_GEOMETRY_MISMATCH",
                        "message": (
                            "Topology rejected before CIF build due to local "
                            f"X-direction RMSD: {local_prefilter_rmsd:.4f}"
                        ),
                    }
                )
                continue

            # Build structure
            framework = builder.build_by_type(
                topology=topo, node_bbs=node_bbs, edge_bbs=edge_bbs
            )
            rmsd = float(framework.info.get("max_rmsd", 0.0))

            if rmsd < 0.3:
                artifact_count += 1
                art_id = f"cif-{artifact_count:03d}"
                filename = f"{topo_name}_{node_code}_{linker_code}.cif"
                cif_path = output_dir / filename
                framework.write_cif(str(cif_path))

                results.append(
                    {
                        "artifact_id": art_id,
                        "filename": filename,
                        "topology": topo_name,
                        "local_prefilter_rmsd": local_prefilter_rmsd,
                        "max_rmsd": rmsd,
                        "node_catalog_id": node_id,
                        "linker_catalog_id": linker_id,
                    }
                )
            else:
                failures.append(
                    {
                        "topology": topo_name,
                        "error_code": "HIGH_RMSD",
                        "message": f"Structure rejected due to high RMSD: {rmsd:.4f}",
                    }
                )
        except Exception as e:
            failures.append(
                {
                    "topology": topo_name,
                    "error_code": "BUILD_FAILED",
                    "message": str(e),
                }
            )

    result_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "tool": "pormake",
                "status": "succeeded" if results else "failed",
                "attempted_topologies": len(filtered_topos),
                "results": results,
                "failures": failures,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()

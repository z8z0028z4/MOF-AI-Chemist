import argparse
import csv
import functools
import json
import os
import shutil
import sys
from pathlib import Path


def _patch_torch_load():
    """Monkey-patch ``torch.load`` so that ``weights_only`` defaults to
    ``False``.  PyTorch 2.6+ changed the default to ``True``, which
    breaks MOFTransformer checkpoints that embed sacred ConfigSummary
    objects.  We apply the patch early so every downstream call
    (including inside ``moftransformer.modules.module``) picks it up.
    """
    try:
        import torch

        _original = torch.load

        @functools.wraps(_original)
        def _patched_load(*args, **kwargs):
            kwargs.setdefault("weights_only", False)
            return _original(*args, **kwargs)

        torch.load = _patched_load
    except ImportError:
        pass


def _clean_cif_file(cif_path: Path):
    """Comment out any leading non-blank, non-comment lines that appear
    before the first 'data_' keyword to prevent ASE parser from crashing
    on non-standard metadata.
    """
    try:
        with open(cif_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

        modified = False
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.lower().startswith("data_"):
                break
            if stripped and not stripped.startswith("#"):
                lines[i] = "# " + line
                modified = True

        if modified:
            with open(cif_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
    except Exception as e:
        sys.stderr.write(f"Warning: Failed to clean CIF file {cif_path}: {e}\n")


def _preparation_diagnostic(filename: str, run_dir: Path) -> str | None:
    """Return the latest upstream logger message for one CIF, when available."""
    names = {filename, Path(filename).stem}
    candidates = [Path.cwd() / "prepare_data.log", Path.cwd() / "prepare_energy_grid.log"]
    candidates.extend([run_dir / "prepare_data.log", run_dir / "prepare_energy_grid.log"])
    messages = []
    for log_path in candidates:
        if not log_path.is_file():
            continue
        try:
            for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
                if any(name in line for name in names) and ("failed" in line.lower() or "error" in line.lower()):
                    messages.append(line.split(" - ", 3)[-1].strip())
        except OSError:
            continue
    return messages[-1] if messages else None


def _format_preparation_exception(filename: str, error: Exception) -> str:
    return f"{filename}: {type(error).__name__}: {error}"


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

    checkpoint_path = req["checkpoint_path"]
    downstream = req["downstream"]
    mean = req["mean"]
    std = req["std"]
    cif_paths = req["cif_paths"]
    run_dir = Path(req["run_dir"])

    # Setup directories
    dataset_dir = run_dir / "pmtransformer_dataset"
    test_dir = dataset_dir / "test"
    test_dir.mkdir(parents=True, exist_ok=True)

    try:
        from moftransformer.utils.prepare_data import make_prepared_data
    except ImportError as e:
        result_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "tool": "pmtransformer",
                    "status": "failed",
                    "results": [],
                    "failures": [
                        {
                            "filename": "",
                            "error_code": "IMPORT_ERROR",
                            "message": f"moftransformer import failed: {str(e)}",
                        }
                    ],
                }
            )
        )
        sys.exit(0)

    failures = []
    staged_cifs = []

    # 1. Prepare data (extract features)
    for path_str in cif_paths:
        path = Path(path_str)
        if not path.is_file():
            failures.append(
                {
                    "filename": path.name,
                    "error_code": "FILE_NOT_FOUND",
                    "message": "CIF file does not exist",
                }
            )
            continue

        try:
            # First copy the original cif to the test directory
            dest_cif = test_dir / path.name
            shutil.copy2(path, dest_cif)

            # Clean up any non-standard headers before feature extraction
            _clean_cif_file(dest_cif)

            # Extract features inside test directory
            success = make_prepared_data(
                cif=dest_cif,
                root_dataset_total=test_dir,
            )
            if success:
                staged_cifs.append(path.stem)
            else:
                failures.append(
                    {
                        "filename": path.name,
                        "error_code": "PREPARATION_FAILED",
                        "message": _preparation_diagnostic(path.name, run_dir)
                        or "make_prepared_data failed to extract features",
                    }
                )
        except Exception as e:
            failures.append(
                {
                    "filename": path.name,
                    "error_code": "PREPARATION_FAILED",
                    "message": _format_preparation_exception(path.name, e),
                }
            )

    if not staged_cifs:
        result_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "tool": "pmtransformer",
                    "status": "failed",
                    "results": [],
                    "failures": failures
                    + [
                        {
                            "filename": "",
                            "error_code": "NO_VALID_INPUTS",
                            "message": "No CIF files were successfully prepared for prediction",
                        }
                    ],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        sys.exit(0)

    # 2. Write metadata JSON
    # It maps each cif stem to a placeholder target value
    test_json = dataset_dir / f"test_{downstream}.json"
    test_json.write_text(
        json.dumps({stem: 0.0 for stem in staged_cifs}),
        encoding="utf-8",
    )

    # 3. Call predict API
    try:
        # Patch torch.load BEFORE importing moftransformer so that the
        # Module class picks up weights_only=False when loading ckpts
        # that contain sacred.ConfigSummary objects (PyTorch 2.6+).
        _patch_torch_load()

        from moftransformer import predict as mof_predict

        mof_predict(
            root_dataset=str(dataset_dir),
            load_path=str(checkpoint_path),
            downstream=downstream,
            split="test",
            save_dir=str(run_dir),
            mean=mean,
            std=std,
            # Force safe subprocess settings to prevent DDP/gloo hangs
            accelerator="cpu",
            devices=1,
            num_workers=0,
        )

        # 4. Read predictions CSV
        results = []
        csv_path = run_dir / "test_prediction.csv"
        if csv_path.is_file():
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                cif_col = next(
                    (c for c in reader.fieldnames if "cif_id" in c), None
                )
                val_col = next(
                    (
                        c
                        for c in reader.fieldnames
                        if "logit" in c or "pred" in c or "value" in c
                    ),
                    None,
                )

                if cif_col and val_col:
                    count = 0
                    for row in reader:
                        count += 1
                        cif_id = row[cif_col]
                        val = float(row[val_col])
                        results.append(
                            {
                                "artifact_id": f"pred-{count:03d}",
                                "cif_name": cif_id,
                                "predicted_value": val,
                                "unit": req.get("unit", "mmol/g"),
                                "target_property": req.get(
                                    "target_property", "CO2 uptake"
                                ),
                                "condition": req.get(
                                    "condition", "298 K, 0.15 bar"
                                ),
                            }
                        )
                else:
                    raise RuntimeError(
                        f"CSV columns not recognized in test_prediction.csv. Fields: {reader.fieldnames}"
                    )
        else:
            raise FileNotFoundError("test_prediction.csv was not generated")

        result_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "tool": "pmtransformer",
                    "status": "succeeded" if results else "failed",
                    "profile_id": req.get("profile_id"),
                    "results": results,
                    "failures": failures,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    except Exception as e:
        result_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "tool": "pmtransformer",
                    "status": "failed",
                    "results": [],
                    "failures": failures
                    + [
                        {
                            "filename": "",
                            "error_code": "PREDICT_FAILED",
                            "message": str(e),
                        }
                    ],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()

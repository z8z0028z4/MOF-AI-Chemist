from __future__ import annotations

import json
import shutil
import subprocess
import threading
from pathlib import Path

from backend.services.mof_settings_service import (
    get_mof_private_settings_path,
)
from backend.core import demo_config

_ACTIVE_PROCESSES: dict[str, subprocess.Popen] = {}
_PROCESS_LOCK = threading.Lock()


class PmTransformerRunner:
    def __init__(self, run_store, artifact_service, tool_env_service):
        self.run_store = run_store
        self.artifact_service = artifact_service
        self.tool_env_service = tool_env_service

    def start_job(self, run_id: str) -> None:
        thread = threading.Thread(
            target=self._run_worker_thread, args=(run_id,), daemon=True
        )
        thread.start()

    def cancel_job(self, run_id: str) -> bool:
        with _PROCESS_LOCK:
            proc = _ACTIVE_PROCESSES.get(run_id)
            if proc:
                try:
                    proc.terminate()
                    try:
                        proc.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                    return True
                except Exception:
                    pass
        return False

    def _run_worker_thread(self, run_id: str) -> None:
        try:
            run = self.run_store.update_status(
                run_id, "preparing", progress=0.1, message="Preparing request data"
            )

            req_path = run.run_dir / "request.json"
            if not req_path.is_file():
                self.run_store.update_status(
                    run_id,
                    "failed",
                    progress=1.0,
                    message="Missing request JSON",
                )
                return

            req = json.loads(req_path.read_text(encoding="utf-8"))
            profile_id = req["profile_id"]
            generator_run_id = req.get("generator_run_id")
            artifact_ids = req.get("artifact_ids", [])

            # Load private profiles
            settings_path = get_mof_private_settings_path()
            if not settings_path.is_file():
                self.run_store.update_status(
                    run_id,
                    "failed",
                    progress=1.0,
                    message="Private settings file not found",
                )
                return

            settings_data = json.loads(
                settings_path.read_text(encoding="utf-8")
            )
            # Find the active profile
            profiles = settings_data.get("profiles", [])
            profile = next((p for p in profiles if p.get("id") == profile_id), None)
            if not profile:
                self.run_store.update_status(
                    run_id,
                    "failed",
                    progress=1.0,
                    message=f"Model profile '{profile_id}' not found",
                )
                return

            checkpoint_path = req.get("custom_checkpoint_path") or profile["checkpoint_path"]
            downstream = profile["downstream"]

            target_property = req.get("custom_target_property") or profile.get("target_property", "CO2 uptake")
            condition = req.get("custom_condition") or profile.get("condition", "298 K, 0.15 bar")
            unit = req.get("custom_unit") or profile.get("unit", "mmol/g")

            mean = req.get("custom_mean")
            if mean is None:
                mean = profile["normalization"]["mean"]
            else:
                mean = float(mean)

            std = req.get("custom_std")
            if std is None:
                std = profile["normalization"]["std"]
            else:
                std = float(std)

            # Resolve CIF paths
            input_dir = run.run_dir / "input_cifs"
            input_dir.mkdir(parents=True, exist_ok=True)

            cif_paths = []
            if generator_run_id:
                # Resolve files from the generator run
                # If artifact_ids list is empty, we resolve all artifacts from generator run results
                gen_run = self.run_store.get_run(generator_run_id)
                gen_result_path = gen_run.run_dir / "result.json"
                if not gen_result_path.is_file():
                    self.run_store.update_status(
                        run_id,
                        "failed",
                        progress=1.0,
                        message=f"Generator run '{generator_run_id}' results not found",
                    )
                    return

                gen_result = json.loads(
                    gen_result_path.read_text(encoding="utf-8")
                )
                results_to_use = gen_result.get("results", [])
                if artifact_ids:
                    results_to_use = [
                        r
                        for r in results_to_use
                        if r.get("artifact_id") in artifact_ids
                    ]

                if not results_to_use:
                    self.run_store.update_status(
                        run_id,
                        "failed",
                        progress=1.0,
                        message="No matching generator artifacts found",
                    )
                    return

                for item in results_to_use:
                    art_id = item["artifact_id"]
                    try:
                        resolved_path = self.artifact_service.resolve(
                            generator_run_id, art_id
                        )
                        dest = input_dir / resolved_path.name
                        shutil.copy2(resolved_path, dest)
                        cif_paths.append(str(dest))
                    except Exception as e:
                        self.run_store.update_status(
                            run_id,
                            "failed",
                            progress=1.0,
                            message=f"Failed to copy generator artifact '{art_id}': {e}",
                        )
                        return
            else:
                # Uploaded files are already placed under input_cifs by the router
                cif_paths = [str(p) for p in input_dir.glob("*.cif")]

            if not cif_paths:
                self.run_store.update_status(
                    run_id,
                    "failed",
                    progress=1.0,
                    message="No CIF files found to predict",
                )
                return

            # Check environment
            if not self.tool_env_service.is_installed("pmtransformer"):
                self.run_store.update_status(
                    run_id,
                    "failed",
                    progress=1.0,
                    message="pmtransformer environment not installed",
                )
                return

            python_exe = self.tool_env_service.get_python_executable(
                "pmtransformer"
            )
            worker_script = (
                Path(__file__).resolve().parents[2]
                / "workers"
                / "mof"
                / "pmtransformer_worker.py"
            )

            # Create request for worker
            worker_req = {
                "profile_id": profile_id,
                "checkpoint_path": checkpoint_path,
                "downstream": downstream,
                "mean": mean,
                "std": std,
                "unit": unit,
                "target_property": target_property,
                "condition": condition,
                "cif_paths": cif_paths,
                "run_dir": str(run.run_dir),
            }

            worker_req_path = run.run_dir / "worker_request.json"
            worker_req_path.write_text(
                json.dumps(worker_req, indent=2), encoding="utf-8"
            )

            result_json_path = run.run_dir / "result.json"
            log_file_path = run.run_dir / "run.log"

            cmd = [
                str(python_exe),
                str(worker_script),
                "--request",
                str(worker_req_path),
                "--result",
                str(result_json_path),
            ]

            self.run_store.update_status(
                run_id,
                "running",
                progress=0.2,
                message="Running feature extraction and inference",
            )

            if demo_config.is_stage_demo("property_prediction"):
                self.run_store.update_status(
                    run_id,
                    "failed",
                    progress=1.0,
                    message="Refusing to launch pmtransformer subprocess: demo mode is active for property prediction",
                )
                return

            with open(log_file_path, "w", encoding="utf-8") as log_file:
                log_file.write(f"Executing command: {' '.join(cmd)}\n")
                log_file.flush()

                proc = subprocess.Popen(
                    cmd, stdout=log_file, stderr=log_file, text=True
                )

                with _PROCESS_LOCK:
                    current_run = self.run_store.get_run(run_id)
                    if current_run.status == "cancelled":
                        proc.terminate()
                        proc.wait()
                        return
                    _ACTIVE_PROCESSES[run_id] = proc

                try:
                    returncode = proc.wait(timeout=600)
                except subprocess.TimeoutExpired:
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except Exception:
                        proc.kill()
                    log_file.write("\nProcess timed out after 600 seconds.\n")
                    self.run_store.update_status(
                        run_id,
                        "failed",
                        progress=1.0,
                        message="Job timed out after 600 seconds",
                    )
                    return
                finally:
                    with _PROCESS_LOCK:
                        _ACTIVE_PROCESSES.pop(run_id, None)

            # Check status after execution
            current_run = self.run_store.get_run(run_id)
            if current_run.status == "cancelled":
                return

            if returncode != 0:
                self.run_store.update_status(
                    run_id,
                    "failed",
                    progress=1.0,
                    message=f"Worker process exited with code {returncode}",
                )
                return

            if not result_json_path.is_file():
                self.run_store.update_status(
                    run_id,
                    "failed",
                    progress=1.0,
                    message="Worker did not produce result.json",
                )
                return

            try:
                res_data = json.loads(
                    result_json_path.read_text(encoding="utf-8")
                )
            except Exception as e:
                self.run_store.update_status(
                    run_id,
                    "failed",
                    progress=1.0,
                    message=f"Failed to read result JSON: {e}",
                )
                return

            if res_data.get("status") == "failed":
                failures = res_data.get("failures", [])
                err_msg = (
                    failures[0].get("message", "Prediction failed")
                    if failures
                    else "Prediction failed"
                )
                self.run_store.update_status(
                    run_id, "failed", progress=1.0, message=err_msg
                )
                return

            # Register artifacts manifest
            manifest_items = []
            csv_path = run.run_dir / "test_prediction.csv"
            if csv_path.is_file():
                manifest_items.append(
                    {
                        "artifact_id": "predictions-csv",
                        "relative_path": "test_prediction.csv",
                    }
                )

            for item in res_data.get("results", []):
                cif_name = item["cif_name"]
                manifest_items.append(
                    {
                        "artifact_id": item["artifact_id"],
                        "relative_path": f"input_cifs/{cif_name}.cif",
                    }
                )

            if manifest_items:
                self.artifact_service.write_manifest(run_id, manifest_items)

            self.run_store.update_status(
                run_id,
                "succeeded",
                progress=1.0,
                message=f"Successfully predicted properties for {len(res_data.get('results', []))} CIFs",
            )

        except Exception as e:
            try:
                self.run_store.update_status(
                    run_id, "failed", progress=1.0, message=f"Error: {e}"
                )
            except Exception:
                pass

from __future__ import annotations

import json
import subprocess
import threading
from pathlib import Path

from backend.services.mof.pormake_catalog import resolve_catalog_id
from backend.core import demo_config

_ACTIVE_PROCESSES: dict[str, subprocess.Popen] = {}
_PROCESS_LOCK = threading.Lock()


class PormakeRunner:
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
            node_id = req["node_id"]
            linker_id = req["linker_id"]
            topology = req.get("topology")
            max_results = req.get("max_results", 10)

            try:
                node_bb = resolve_catalog_id(node_id)
                linker_bb = resolve_catalog_id(linker_id)
            except Exception as e:
                self.run_store.update_status(
                    run_id,
                    "failed",
                    progress=1.0,
                    message=f"Failed to resolve building blocks: {e}",
                )
                return

            # Prepare request for worker
            worker_req = {
                "node_code": node_bb["pormake_code"],
                "linker_code": linker_bb["pormake_code"],
                "node_cn": node_bb["coordination_number"],
                "linker_cn": linker_bb["coordination_number"],
                "node_id": node_id,
                "linker_id": linker_id,
                "topology": topology,
                "max_results": max_results,
                "output_dir": str(run.run_dir / "generated_cifs"),
            }

            worker_req_path = run.run_dir / "worker_request.json"
            worker_req_path.write_text(
                json.dumps(worker_req, indent=2), encoding="utf-8"
            )

            # Check environment
            if not self.tool_env_service.is_installed("pormake"):
                self.run_store.update_status(
                    run_id,
                    "failed",
                    progress=1.0,
                    message="PORMAKE environment not installed",
                )
                return

            python_exe = self.tool_env_service.get_python_executable("pormake")
            worker_script = (
                Path(__file__).resolve().parents[2]
                / "workers"
                / "mof"
                / "pormake_worker.py"
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
                message="Running geometric assembly",
            )

            if demo_config.is_stage_demo("property_prediction"):
                self.run_store.update_status(
                    run_id,
                    "failed",
                    progress=1.0,
                    message="Refusing to launch PORMAKE subprocess: demo mode is active for property prediction",
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
                    returncode = proc.wait(timeout=300)
                except subprocess.TimeoutExpired:
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except Exception:
                        proc.kill()
                    log_file.write("\nProcess timed out after 300 seconds.\n")
                    self.run_store.update_status(
                        run_id,
                        "failed",
                        progress=1.0,
                        message="Job timed out after 300 seconds",
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
                    failures[0].get("message", "Assembly failed")
                    if failures
                    else "Assembly failed"
                )
                self.run_store.update_status(
                    run_id, "failed", progress=1.0, message=err_msg
                )
                return

            # Register artifacts manifest
            manifest_items = []
            for item in res_data.get("results", []):
                manifest_items.append(
                    {
                        **item,
                        "artifact_id": item["artifact_id"],
                        "relative_path": f"generated_cifs/{item['filename']}",
                    }
                )

            if manifest_items:
                self.artifact_service.write_manifest(run_id, manifest_items)

            self.run_store.update_status(
                run_id,
                "succeeded",
                progress=1.0,
                message=f"Successfully built {len(manifest_items)} CIFs",
            )

        except Exception as e:
            try:
                self.run_store.update_status(
                    run_id, "failed", progress=1.0, message=f"Error: {e}"
                )
            except Exception:
                pass

from __future__ import annotations

import os
import subprocess
import threading
from pathlib import Path
from typing import Any, Dict, Optional
from backend.config import MOF_DATA_DIR
from backend.services.mof.griday_builder import discover_griday_root, ensure_griday_compatible


class ToolReadinessError(RuntimeError):
    """Raised when a tool cannot safely execute its worker."""


class ToolEnvService:
    def __init__(self, mof_data_dir: str | Path | None = None):
        self.mof_data_dir = Path(mof_data_dir or MOF_DATA_DIR).expanduser().resolve()
        self.envs_dir = self.mof_data_dir / "tool_envs"
        self.install_dir = self.mof_data_dir / "install"

        # In-memory status for active installations
        self._install_status: dict[str, dict[str, Any]] = {
            "pormake": {
                "status": "idle",
                "progress": 0.0,
                "message": "Not started",
            },
            "pmtransformer": {
                "status": "idle",
                "progress": 0.0,
                "message": "Not started",
            }
        }
        self._lock = threading.Lock()

    def get_env_dir(self, tool: str) -> Path:
        return self.envs_dir / tool

    def get_python_executable(self, tool: str) -> Path:
        return self.get_env_dir(tool) / "bin" / "python"

    def get_xrd_preflight(self) -> dict[str, Any]:
        """Validate the exact interpreter used by the XRD worker.

        Keep this check separate from the broader PMTransformer/GRIDAY status:
        XRD only needs its declared interpreter and pymatgen, and must never
        silently run under the backend interpreter.
        """
        python_exe = self.get_python_executable("pmtransformer")
        status: dict[str, Any] = {
            "ready": False,
            "installed": python_exe.is_file(),
            "python_executable": str(python_exe),
            "pymatgen": False,
            "error": None,
        }
        if not python_exe.is_file():
            status["error"] = (
                "PMTransformer environment is not installed. "
                "Install PMTransformer and retry XRD."
            )
            return status

        try:
            probe = subprocess.run(
                [
                    str(python_exe),
                    "-c",
                    "import pymatgen; print(getattr(pymatgen, '__version__', 'installed'))",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            status["error"] = f"PMTransformer Python preflight failed: {exc}"
            return status
        if probe.returncode != 0:
            detail = (probe.stderr or probe.stdout).strip()
            status["error"] = (
                "PMTransformer Python cannot import pymatgen. "
                "Reinstall PMTransformer dependencies and retry XRD."
                + (f" ({detail})" if detail else "")
            )
            return status

        status.update({"ready": True, "pymatgen": True, "pymatgen_version": probe.stdout.strip()})
        return status

    def require_xrd_ready(self) -> dict[str, Any]:
        status = self.get_xrd_preflight()
        if not status["ready"]:
            raise ToolReadinessError(status["error"] or "PMTransformer XRD environment is not ready")
        return status

    def is_installed(self, tool: str) -> bool:
        python_exe = self.get_python_executable(tool)
        return python_exe.is_file()

    def get_status(self, tool: str) -> dict[str, Any]:
        installed = self.is_installed(tool)
        if not installed:
            return {
                "ready": False,
                "installed": False,
                "version": None,
                "error": "Environment not created"
            }

        python_exe = self.get_python_executable(tool)
        try:
            lib_name = "pormake" if tool == "pormake" else "moftransformer"
            cmd = [
                str(python_exe),
                "-c",
                f"import importlib.metadata; print(importlib.metadata.version('{lib_name}'))",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                version = result.stdout.strip()
                griday_status = None
                if tool == "pmtransformer":
                    try:
                        griday_root = discover_griday_root(python_exe)
                        griday_status = ensure_griday_compatible(griday_root)
                    except Exception as exc:
                        return {
                            "ready": False,
                            "installed": True,
                            "version": version,
                            "error": f"GRIDAY readiness check failed: {exc}",
                        }
                    if not griday_status.ready:
                        return {
                            "ready": False,
                            "installed": True,
                            "version": version,
                            "error": f"GRIDAY is not ready: {griday_status.error}",
                        }
                return {
                    "ready": True,
                    "installed": True,
                    "version": version,
                    "error": None,
                    **({"griday": {"root": str(griday_status.root), "rebuilt": griday_status.rebuilt}}
                       if griday_status else {}),
                }
            else:
                return {
                    "ready": False,
                    "installed": True,
                    "version": None,
                    "error": f"Failed to import library: {result.stderr.strip()}"
                }
        except Exception as e:
            return {
                "ready": False,
                "installed": True,
                "version": None,
                "error": str(e)
            }

    def get_topologies_dir(self) -> Path | None:
        pormake_dir = self.get_env_dir("pormake")
        if not pormake_dir.is_dir():
            return None
        lib_dir = pormake_dir / "lib"
        if not lib_dir.is_dir():
            return None
        for py_dir in lib_dir.glob("python*"):
            topo_dir = py_dir / "site-packages" / "pormake" / "database" / "topologies"
            if topo_dir.is_dir():
                return topo_dir
        return None

    def get_building_blocks_dir(self) -> Path | None:
        """Return the installed PORMAKE building-block database directory."""
        pormake_dir = self.get_env_dir("pormake")
        if pormake_dir.is_dir():
            lib_dir = pormake_dir / "lib"
            if lib_dir.is_dir():
                for py_dir in lib_dir.glob("python*"):
                    bb_dir = (
                        py_dir
                        / "site-packages"
                        / "pormake"
                        / "database"
                        / "bbs"
                    )
                    if bb_dir.is_dir():
                        return bb_dir

        sibling_checkout = (
            Path(__file__).resolve().parents[4]
            / "PORMAKE"
            / "src"
            / "pormake"
            / "database"
            / "bbs"
        )
        if sibling_checkout.is_dir():
            return sibling_checkout
        return None

    def get_compatible_topologies(self, node_id: str | None = None, linker_id: str | None = None) -> list[str]:
        topo_dir = self.get_topologies_dir()
        if topo_dir is None or not topo_dir.is_dir():
            fallback = (
                Path(__file__).resolve().parents[4]
                / "PORMAKE"
                / "src"
                / "pormake"
                / "database"
                / "topologies"
            )
            if fallback.is_dir():
                topo_dir = fallback
            else:
                return []

        if not node_id and not linker_id:
            return sorted([p.stem for p in topo_dir.glob("*.cgd")])

        try:
            from backend.services.mof.pormake_catalog import resolve_catalog_id
            node_bb = resolve_catalog_id(node_id)
            linker_bb = resolve_catalog_id(linker_id)
        except KeyError:
            return []

        metal_cn = node_bb["coordination_number"]
        linker_cn = linker_bb["coordination_number"]
        pormake_linker_code = linker_bb["pormake_code"]

        if pormake_linker_code.startswith("E") or linker_cn == 2:
            target_cns = {metal_cn}
        else:
            target_cns = {metal_cn, linker_cn}

        topologies = []
        for p in topo_dir.glob("*.cgd"):
            cns = set()
            try:
               with open(p, 'r', encoding='utf-8') as f:
                   for line in f:
                       stripped = line.strip()
                       if stripped.startswith("NODE"):
                           parts = stripped.split()
                           if len(parts) >= 3:
                               cns.add(int(parts[2]))
            except Exception:
               continue
            if cns == target_cns:
               topologies.append(p.stem)

        return sorted(topologies)


    def get_install_status(self, tool: str) -> dict[str, Any]:
        with self._lock:
            status = dict(self._install_status.get(tool, {}))
            log_path = self.install_dir / f"{tool}_install.log"
            if log_path.is_file():
                status["log"] = log_path.read_text(encoding="utf-8")
            else:
                status["log"] = None
            return status

    def start_install(self, tool: str) -> dict[str, Any]:
        if tool not in ("pormake", "pmtransformer"):
            raise ValueError(f"Unknown tool: {tool}")

        with self._lock:
            current = self._install_status.get(tool, {})
            if current.get("status") == "installing":
                return {"status": "installing", "message": "Installation already in progress"}

            self._install_status[tool] = {
                "status": "installing",
                "progress": 0.1,
                "message": "Starting virtual environment creation",
            }

            thread = threading.Thread(target=self._run_install, args=(tool,), daemon=True)
            thread.start()

            return {"status": "installing", "message": "Installation started"}

    def _run_install(self, tool: str) -> None:
        self.install_dir.mkdir(parents=True, exist_ok=True)
        log_path = self.install_dir / f"{tool}_install.log"
        env_dir = self.get_env_dir(tool)

        with open(log_path, "w", encoding="utf-8") as log_file:
            log_file.write(f"=== Starting installation for {tool} ===\n")

            try:
                log_file.write(f"Creating venv at {env_dir}...\n")
                log_file.flush()
                import sys
                res = subprocess.run(
                    [sys.executable, "-m", "venv", str(env_dir)],
                    stdout=log_file,
                    stderr=log_file,
                    text=True
                )
                if res.returncode != 0:
                    raise RuntimeError("Failed to create virtual environment")

                with self._lock:
                    self._install_status[tool]["progress"] = 0.4
                    self._install_status[tool]["message"] = "Upgrading pip"

                python_exe = self.get_python_executable(tool)
                log_file.write("Upgrading pip...\n")
                log_file.flush()
                res = subprocess.run(
                    [str(python_exe), "-m", "pip", "install", "--upgrade", "pip"],
                    stdout=log_file,
                    stderr=log_file,
                    text=True
                )
                if res.returncode != 0:
                    raise RuntimeError("Failed to upgrade pip")

                with self._lock:
                    self._install_status[tool]["progress"] = 0.6
                    self._install_status[tool]["message"] = "Installing packages"

                log_file.write("Installing packages...\n")
                log_file.flush()
                if tool == "pormake":
                    res = subprocess.run(
                        [str(python_exe), "-m", "pip", "install", "pormake>=0.2.3"],
                        stdout=log_file,
                        stderr=log_file,
                        text=True
                    )
                else:
                    # Install dependencies first
                    deps = [
                        "torch",
                        "pytorch-lightning",
                        "pyyaml",
                        "numpy",
                        "ase",
                        "pymatgen",
                        "pandas",
                        "tqdm",
                        "scikit-learn",
                        "transformers",
                        "einops",
                        "timm",
                        "sacred",
                        "seaborn",
                        "wget",
                    ]
                    log_file.write(f"Installing dependencies: {deps}...\n")
                    log_file.flush()
                    res = subprocess.run(
                        [str(python_exe), "-m", "pip", "install"] + deps,
                        stdout=log_file,
                        stderr=log_file,
                        text=True
                    )
                    if res.returncode == 0:
                        log_file.write("Installing moftransformer with --no-deps...\n")
                        log_file.flush()
                        res = subprocess.run(
                            [str(python_exe), "-m", "pip", "install", "moftransformer>=2.2.0", "--no-deps"],
                            stdout=log_file,
                            stderr=log_file,
                            text=True
                        )
                if res.returncode != 0:
                    raise RuntimeError(f"Failed to install packages for {tool}")

                if tool == "pmtransformer":
                    log_file.write("Checking GRIDAY binary compatibility...\n")
                    log_file.flush()
                    griday_root = discover_griday_root(python_exe)
                    griday_status = ensure_griday_compatible(griday_root)
                    if not griday_status.ready:
                        raise RuntimeError(f"GRIDAY readiness failed: {griday_status.error}")
                    log_file.write(
                        f"GRIDAY ready at {griday_status.root} (rebuilt={griday_status.rebuilt})\n"
                    )

                with self._lock:
                    self._install_status[tool]["status"] = "success"
                    self._install_status[tool]["progress"] = 1.0
                    self._install_status[tool]["message"] = "Installation completed successfully"
                log_file.write("=== Installation finished successfully ===\n")

            except Exception as e:
                with self._lock:
                    self._install_status[tool]["status"] = "failed"
                    self._install_status[tool]["progress"] = 1.0
                    self._install_status[tool]["message"] = f"Installation failed: {str(e)}"
                log_file.write(f"=== Installation failed: {str(e)} ===\n")

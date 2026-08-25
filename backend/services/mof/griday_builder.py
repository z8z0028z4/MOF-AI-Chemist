from __future__ import annotations

import platform
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence


@dataclass(frozen=True)
class GridayStatus:
    ready: bool
    root: Path
    host_arch: str
    binary_arch: str | None = None
    rebuilt: bool = False
    error: str | None = None


_BUILD_LOCK = threading.Lock()


def normalize_arch(value: str) -> str:
    value = value.lower().replace("-", "_")
    if value in {"amd64", "x86_64", "x64"}:
        return "x86_64"
    if value in {"aarch64", "arm64", "arm_64"}:
        return "aarch64"
    return value


def binary_matches_host(host_arch: str, file_output: str) -> bool:
    host = normalize_arch(host_arch)
    output = file_output.lower()
    if host == "x86_64":
        return "x86-64" in output or "x86_64" in output
    if host == "aarch64":
        return "aarch64" in output or "arm aarch64" in output
    return normalize_arch(host) in output


def _file_info(path: Path) -> str:
    result = subprocess.run(["file", "-L", str(path)], capture_output=True, text=True, check=False)
    return result.stdout.strip() or result.stderr.strip()


def discover_griday_root(python_executable: str | Path) -> Path:
    code = (
        "import pathlib, moftransformer; "
        "root = pathlib.Path(getattr(moftransformer, '__root_dir__', "
        "pathlib.Path(moftransformer.__file__).resolve().parent)); "
        "print(root / 'libs' / 'GRIDAY')"
    )
    result = subprocess.run(
        [str(python_executable), "-c", code], capture_output=True, text=True, check=False, timeout=10
    )
    if result.returncode != 0:
        raise RuntimeError(f"Could not locate bundled GRIDAY: {result.stderr.strip()}")
    root = Path(result.stdout.strip()).expanduser().resolve()
    if not root.is_dir():
        raise RuntimeError(f"Bundled GRIDAY source directory is missing: {root}")
    return root


def _clean_objects(root: Path) -> None:
    for path in root.rglob("*.o"):
        path.unlink()


def _run_make(
    run: Callable[..., object], command: Sequence[str], root: Path, *, allow_failure: bool = False
) -> None:
    result = run(list(command), cwd=str(root), capture_output=True, text=True, check=False)
    if getattr(result, "returncode", 1) != 0 and not allow_failure:
        detail = (getattr(result, "stderr", "") or getattr(result, "stdout", "")).strip()
        raise RuntimeError(f"GRIDAY build command {' '.join(command)} failed: {detail}")


def ensure_griday_compatible(
    root: str | Path,
    *,
    host_arch: str | None = None,
    run: Callable[..., object] = subprocess.run,
    binary_info: Callable[[Path], str] = _file_info,
) -> GridayStatus:
    root = Path(root).expanduser().resolve()
    host_arch = normalize_arch(host_arch or platform.machine())
    grid_gen = root / "scripts" / "grid_gen"
    with _BUILD_LOCK:
        try:
            if grid_gen.is_file() and binary_matches_host(host_arch, binary_info(grid_gen)):
                return GridayStatus(True, root, host_arch, host_arch, False)
            if not (root / "Makefile").is_file() or not (root / "scripts" / "Makefile").is_file():
                raise RuntimeError(f"GRIDAY source/Makefiles are missing under {root}")
            _clean_objects(root)
            _run_make(run, ["make", "-C", "scripts", "clean"], root, allow_failure=True)
            _run_make(run, ["make", "clean"], root, allow_failure=True)
            _run_make(run, ["make"], root)
            _run_make(run, ["make", "-C", "scripts"], root)
            if not grid_gen.is_file():
                raise RuntimeError(f"GRIDAY build did not produce {grid_gen}")
            info = binary_info(grid_gen)
            if not binary_matches_host(host_arch, info):
                raise RuntimeError(f"rebuilt grid_gen is incompatible with host {host_arch}: {info}")
            return GridayStatus(True, root, host_arch, host_arch, True)
        except Exception as exc:
            return GridayStatus(False, root, host_arch, None, False, str(exc))

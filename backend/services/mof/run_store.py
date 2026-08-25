from __future__ import annotations

import json
import os
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


TERMINAL_STATUSES = {"succeeded", "failed", "cancelled"}
RUN_STATUSES = {"queued", "preparing", "running", *TERMINAL_STATUSES}


class RunNotFound(FileNotFoundError):
    pass


class InvalidRunTransition(ValueError):
    pass


@dataclass(frozen=True)
class MofRun:
    run_id: str
    tool: str
    status: str
    progress: float
    message: str
    created_at: str
    updated_at: str
    run_dir: Path


class MofRunStore:
    def __init__(self, root: str | Path):
        self.root = Path(root).expanduser().resolve()
        self.runs_dir = self.root / "runs"

    def create_run(self, tool: str, request: dict[str, Any]) -> MofRun:
        run_id = f"{datetime.now(UTC):%Y%m%dT%H%M%S}-{uuid.uuid4().hex[:10]}"
        run_dir = self.runs_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=False)
        now = datetime.now(UTC).isoformat()
        run = MofRun(
            run_id=run_id,
            tool=tool,
            status="queued",
            progress=0,
            message="",
            created_at=now,
            updated_at=now,
            run_dir=run_dir,
        )
        _write_json(run_dir / "request.json", request)
        self._write_status(run)
        return run

    def get_run(self, run_id: str) -> MofRun:
        run_dir = self._resolve_run_dir(run_id)
        status_path = run_dir / "status.json"
        if not status_path.is_file():
            raise RunNotFound(run_id)
        payload = json.loads(status_path.read_text(encoding="utf-8"))
        return MofRun(run_dir=run_dir, **payload)

    def update_status(
        self,
        run_id: str,
        status: str,
        *,
        progress: float | None = None,
        message: str | None = None,
    ) -> MofRun:
        if status not in RUN_STATUSES:
            raise ValueError(f"Unsupported run status: {status}")
        current = self.get_run(run_id)
        if current.status in TERMINAL_STATUSES and status != current.status:
            raise InvalidRunTransition(f"{current.status} -> {status}")
        next_progress = current.progress if progress is None else float(progress)
        if not 0 <= next_progress <= 1:
            raise ValueError("progress must be between 0 and 1")
        updated = MofRun(
            run_id=current.run_id,
            tool=current.tool,
            status=status,
            progress=next_progress,
            message=current.message if message is None else message,
            created_at=current.created_at,
            updated_at=datetime.now(UTC).isoformat(),
            run_dir=current.run_dir,
        )
        self._write_status(updated)
        return updated

    def list_runs(self) -> list[MofRun]:
        if not self.runs_dir.is_dir():
            return []
        runs = []
        for p in self.runs_dir.iterdir():
            if p.is_dir() and (p / "status.json").is_file():
                try:
                    payload = json.loads((p / "status.json").read_text(encoding="utf-8"))
                    runs.append(MofRun(run_dir=p, **payload))
                except Exception:
                    pass
        return sorted(runs, key=lambda r: r.updated_at, reverse=True)

    def _resolve_run_dir(self, run_id: str) -> Path:
        if not run_id or Path(run_id).name != run_id:
            raise RunNotFound(run_id)
        run_dir = (self.runs_dir / run_id).resolve()
        if run_dir.parent != self.runs_dir.resolve() or not run_dir.is_dir():
            raise RunNotFound(run_id)
        return run_dir

    def _write_status(self, run: MofRun) -> None:
        payload = asdict(run)
        payload.pop("run_dir")
        _write_json(run.run_dir / "status.json", payload)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .run_store import MofRunStore, _write_json


class ArtifactNotFound(FileNotFoundError):
    pass


class InvalidArtifactManifest(ValueError):
    pass


class MofArtifactService:
    def __init__(self, run_store: MofRunStore):
        self.run_store = run_store

    def write_manifest(self, run_id: str, artifacts: list[dict[str, Any]]) -> None:
        run = self.run_store.get_run(run_id)
        seen: set[str] = set()
        normalized: list[dict[str, Any]] = []
        for artifact in artifacts:
            artifact_id = str(artifact.get("artifact_id", "")).strip()
            relative_path = str(artifact.get("relative_path", "")).strip()
            if not artifact_id or artifact_id in seen:
                raise InvalidArtifactManifest("artifact_id must be unique and non-empty")
            resolved = _resolve_inside(run.run_dir, relative_path)
            if not resolved.is_file():
                raise InvalidArtifactManifest(f"artifact file does not exist: {relative_path}")
            seen.add(artifact_id)
            normalized.append({**artifact, "artifact_id": artifact_id, "relative_path": relative_path})
        _write_json(run.run_dir / "artifacts.json", {"artifacts": normalized})

    def resolve(self, run_id: str, artifact_id: str) -> Path:
        run = self.run_store.get_run(run_id)
        manifest_path = run.run_dir / "artifacts.json"
        if not manifest_path.is_file():
            raise ArtifactNotFound(artifact_id)
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        for artifact in payload.get("artifacts", []):
            if artifact.get("artifact_id") == artifact_id:
                resolved = _resolve_inside(run.run_dir, artifact.get("relative_path", ""))
                if resolved.is_file():
                    return resolved
        raise ArtifactNotFound(artifact_id)


def _resolve_inside(root: Path, relative_path: str) -> Path:
    if not relative_path or Path(relative_path).is_absolute():
        raise InvalidArtifactManifest("artifact path must be relative")
    root = root.resolve()
    resolved = (root / relative_path).resolve()
    if root not in resolved.parents:
        raise InvalidArtifactManifest("artifact path escapes run directory")
    return resolved

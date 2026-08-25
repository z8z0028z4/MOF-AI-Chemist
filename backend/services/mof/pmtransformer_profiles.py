from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SAFE_PROFILE_FIELDS = ("id", "label", "target_property", "condition", "unit")


def load_safe_model_profiles(settings_path: str | Path) -> dict[str, Any]:
    path = Path(settings_path).expanduser()
    if not path.is_file():
        return {"default_profile_id": "", "profiles": []}
    payload = json.loads(path.read_text(encoding="utf-8"))
    profiles = []
    for raw in payload.get("profiles", []):
        if not isinstance(raw, dict):
            continue
        safe = {field: str(raw.get(field, "")) for field in SAFE_PROFILE_FIELDS}
        safe["ready"] = _profile_is_ready(raw)
        profiles.append(safe)
    return {
        "default_profile_id": str(payload.get("default_profile_id", "")),
        "profiles": profiles,
    }


def _profile_is_ready(profile: dict[str, Any]) -> bool:
    checkpoint = profile.get("checkpoint_path")
    normalization = profile.get("normalization")
    if not isinstance(checkpoint, str) or not Path(checkpoint).expanduser().is_file():
        return False
    if not isinstance(profile.get("downstream"), str) or not profile["downstream"]:
        return False
    if not isinstance(normalization, dict):
        return False
    mean = normalization.get("mean")
    std = normalization.get("std")
    return _is_number(mean) and _is_number(std) and float(std) != 0


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)

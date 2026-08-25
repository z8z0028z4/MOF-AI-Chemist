"""
MOF private settings validation.

This module intentionally returns redacted status only. Private checkpoint
paths, CIF roots, downstream identifiers, and normalization values stay in a
gitignored local settings file and are not exposed through the public API.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


MOF_PRIVATE_SETTINGS_ENV = "MOF_PRIVATE_SETTINGS_PATH"
DEFAULT_PRIVATE_SETTINGS_PATH = Path("user_data") / "mof" / "private_settings.json"


def get_mof_private_settings_path() -> Path:
    configured_path = os.getenv(MOF_PRIVATE_SETTINGS_ENV)
    if configured_path:
        return Path(configured_path).expanduser()
    return DEFAULT_PRIVATE_SETTINGS_PATH


def get_mof_private_settings_status(settings_path: str | Path | None = None) -> dict[str, Any]:
    path = Path(settings_path).expanduser() if settings_path is not None else get_mof_private_settings_path()
    status = _base_status(_settings_location(path, settings_path is not None))

    if not path.exists():
        status["missing_fields"].append("settings_file")
        return status

    status["settings_file_exists"] = True

    try:
        raw_settings = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        status["invalid_fields"].append("settings_file.json")
        return status

    if not isinstance(raw_settings, dict):
        status["invalid_fields"].append("settings_file.object")
        return status

    profiles = raw_settings.get("profiles")
    if isinstance(profiles, list) and profiles:
        default_id = raw_settings.get("default_profile_id")
        active_profile = None
        if default_id:
            active_profile = next((p for p in profiles if isinstance(p, dict) and p.get("id") == default_id), None)
        if not active_profile and profiles:
            active_profile = profiles[0]

        if not isinstance(active_profile, dict):
            status["invalid_fields"].append("active_profile")
            return status

        cif_root = raw_settings.get("h_mof_cif_root") or active_profile.get("h_mof_cif_root")
        _validate_required_string({"h_mof_cif_root": cif_root}, "h_mof_cif_root", status)
        _validate_required_string(active_profile, "checkpoint_path", status)
        _validate_required_string(active_profile, "downstream", status)
        _validate_normalization(active_profile.get("normalization"), status)
        _validate_private_paths(
            {
                "checkpoint_path": active_profile.get("checkpoint_path"),
                "h_mof_cif_root": cif_root,
            },
            status,
        )
        _set_safe_display_fields(active_profile, status)
    else:
        _validate_required_string(raw_settings, "checkpoint_path", status)
        _validate_required_string(raw_settings, "h_mof_cif_root", status)
        _validate_required_string(raw_settings, "downstream", status)
        _validate_normalization(raw_settings.get("normalization"), status)
        _validate_private_paths(raw_settings, status)
        _set_safe_display_fields(raw_settings, status)

    status["ready_for_real_run"] = not status["missing_fields"] and not status["invalid_fields"]
    return status



def _base_status(settings_location: str) -> dict[str, Any]:
    return {
        "settings_file_exists": False,
        "settings_location": settings_location,
        "ready_for_real_run": False,
        "missing_fields": [],
        "invalid_fields": [],
        "configured_fields": {
            "checkpoint_path": False,
            "h_mof_cif_root": False,
            "downstream": False,
            "normalization": False,
        },
        "display": {
            "target_property": "",
            "condition": "",
            "unit": "",
        },
        "redacted": True,
    }


def _settings_location(path: Path, explicit_path: bool) -> str:
    if explicit_path:
        return "explicit"
    if os.getenv(MOF_PRIVATE_SETTINGS_ENV):
        return f"env:{MOF_PRIVATE_SETTINGS_ENV}"
    if path == DEFAULT_PRIVATE_SETTINGS_PATH:
        return "default:user_data/mof/private_settings.json"
    return "default"


def _validate_required_string(settings: dict[str, Any], field: str, status: dict[str, Any]) -> None:
    value = settings.get(field)
    if value in (None, ""):
        status["missing_fields"].append(field)
        return
    if not isinstance(value, str):
        status["invalid_fields"].append(field)
        return
    status["configured_fields"][field] = True


def _validate_normalization(value: Any, status: dict[str, Any]) -> None:
    if value in (None, ""):
        status["missing_fields"].append("normalization")
        return
    if not isinstance(value, dict):
        status["invalid_fields"].append("normalization")
        return

    mean = value.get("mean")
    std = value.get("std")

    if mean in (None, ""):
        status["missing_fields"].append("normalization.mean")
    elif not _is_real_number(mean):
        status["invalid_fields"].append("normalization.mean")

    if std in (None, ""):
        status["missing_fields"].append("normalization.std")
    elif not _is_real_number(std) or float(std) == 0:
        status["invalid_fields"].append("normalization.std")

    if (
        "normalization.mean" not in status["missing_fields"]
        and "normalization.mean" not in status["invalid_fields"]
        and "normalization.std" not in status["missing_fields"]
        and "normalization.std" not in status["invalid_fields"]
    ):
        status["configured_fields"]["normalization"] = True


def _validate_private_paths(settings: dict[str, Any], status: dict[str, Any]) -> None:
    checkpoint_path = settings.get("checkpoint_path")
    if isinstance(checkpoint_path, str) and checkpoint_path:
        if not Path(checkpoint_path).expanduser().is_file():
            status["invalid_fields"].append("checkpoint_path.exists")

    cif_root = settings.get("h_mof_cif_root")
    if isinstance(cif_root, str) and cif_root:
        if not Path(cif_root).expanduser().is_dir():
            status["invalid_fields"].append("h_mof_cif_root.exists")


def _set_safe_display_fields(settings: dict[str, Any], status: dict[str, Any]) -> None:
    for field in ("target_property", "condition", "unit"):
        value = settings.get(field)
        if isinstance(value, str):
            status["display"][field] = value


def _is_real_number(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return True
    return False

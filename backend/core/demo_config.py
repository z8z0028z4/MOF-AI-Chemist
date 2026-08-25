"""
Demo-mode stage configuration (TODO 13.0).
============================================

Per-stage backend DEMO_MODE flags, backed by explicit env overrides or persisted settings.

IMPORTANT — usage contract:
- `is_stage_demo(stage)` is what ROUTES must branch on to short-circuit a specific
  stage before any real LLM/subprocess call (e.g. proposal.py, mof.py route handlers).
- `is_demo_mode()` is an "any stage is on" umbrella for context-free safety guards.
  Downstream guards serving a routed request must use
  `is_active_stage_demo_or_any()` so an unchecked stage remains available when an
  unrelated stage is Demo.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Dict, Iterator, Optional

_STAGE_ENV_VARS: Dict[str, str] = {
    "proposal": "DEMO_MOCK_PROPOSAL",
    "generate_new_idea": "DEMO_MOCK_GENERATE_NEW_IDEA",
    "property_prediction": "DEMO_MOCK_PROPERTY_PREDICTION",
    "experiment_detail": "DEMO_MOCK_EXPERIMENT_DETAIL",
}

_TRUTHY_VALUES = {"1", "true", "yes"}
_active_stage: ContextVar[Optional[str]] = ContextVar("demo_active_stage", default=None)

_STAGE_SETTINGS_KEYS: Dict[str, str] = {
    "proposal": "mock_proposal",
    "generate_new_idea": "mock_generate_new_idea",
    "property_prediction": "mock_property_prediction",
    "experiment_detail": "mock_experiment_detail",
}


def _parse_bool(value: str) -> bool:
    return value.strip().lower() in _TRUTHY_VALUES


def _load() -> Dict[str, bool]:
    """Resolve each stage from an explicit env override or persisted settings."""
    from backend.core.settings_manager import settings_manager

    settings = settings_manager.get_demo_mode_settings()
    enabled = settings["enabled"]
    return {
        stage: (
            _parse_bool(os.environ[env_var])
            if env_var in os.environ
            else enabled and settings[_STAGE_SETTINGS_KEYS[stage]]
        )
        for stage, env_var in _STAGE_ENV_VARS.items()
    }


def is_stage_demo(stage: str) -> bool:
    """Per-stage check. Routes must branch on this, not is_demo_mode()."""
    return _load().get(stage, False)


def is_demo_mode() -> bool:
    """True if ANY stage flag is on. For context-free safety guards only."""
    return any(_load().values())


@contextmanager
def stage_context(stage: str) -> Iterator[None]:
    """Bind downstream demo guards to the stage serving this request."""
    token = _active_stage.set(stage)
    try:
        yield
    finally:
        _active_stage.reset(token)


def is_active_stage_demo_or_any() -> bool:
    """Use the active request stage when available; otherwise preserve global safety."""
    active_stage = _active_stage.get()
    return is_stage_demo(active_stage) if active_stage else is_demo_mode()


def reset_cache_for_tests() -> None:
    """Compatibility hook; stage configuration is resolved on every read."""

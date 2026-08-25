"""
Unit tests for backend.core.demo_config (TODO 13.0 card a).

Written FIRST per TDD: at the time these tests are added, backend/core/demo_config.py
does not exist, so all of these should fail with ImportError/ModuleNotFoundError (RED).
"""

from unittest.mock import patch

import pytest


STAGE_ENV_VARS = {
    "proposal": "DEMO_MOCK_PROPOSAL",
    "generate_new_idea": "DEMO_MOCK_GENERATE_NEW_IDEA",
    "property_prediction": "DEMO_MOCK_PROPERTY_PREDICTION",
    "experiment_detail": "DEMO_MOCK_EXPERIMENT_DETAIL",
}


def _clear_all(monkeypatch):
    for var in STAGE_ENV_VARS.values():
        monkeypatch.setenv(var, "false")


def test_all_stages_off_when_explicit_env_overrides_are_false(monkeypatch):
    from backend.core import demo_config

    _clear_all(monkeypatch)
    demo_config.reset_cache_for_tests()

    for stage in STAGE_ENV_VARS:
        assert demo_config.is_stage_demo(stage) is False
    assert demo_config.is_demo_mode() is False


def test_per_stage_flags_are_independent(monkeypatch):
    from backend.core import demo_config

    _clear_all(monkeypatch)
    monkeypatch.setenv("DEMO_MOCK_PROPOSAL", "true")
    demo_config.reset_cache_for_tests()

    assert demo_config.is_stage_demo("proposal") is True
    assert demo_config.is_stage_demo("generate_new_idea") is False
    assert demo_config.is_stage_demo("property_prediction") is False
    assert demo_config.is_stage_demo("experiment_detail") is False


def test_is_demo_mode_true_if_any_stage_on(monkeypatch):
    from backend.core import demo_config

    _clear_all(monkeypatch)
    monkeypatch.setenv("DEMO_MOCK_EXPERIMENT_DETAIL", "true")
    demo_config.reset_cache_for_tests()

    assert demo_config.is_demo_mode() is True


def test_is_demo_mode_false_if_all_stages_off(monkeypatch):
    from backend.core import demo_config

    _clear_all(monkeypatch)
    demo_config.reset_cache_for_tests()

    assert demo_config.is_demo_mode() is False


def test_stage_config_rereads_env_without_reset(monkeypatch):
    from backend.core import demo_config

    _clear_all(monkeypatch)
    demo_config.reset_cache_for_tests()
    assert demo_config.is_stage_demo("proposal") is False

    # Flip env after first access without resetting cache -> new value is used.
    monkeypatch.setenv("DEMO_MOCK_PROPOSAL", "true")
    assert demo_config.is_stage_demo("proposal") is True

    # The compatibility reset remains safe to call.
    demo_config.reset_cache_for_tests()
    assert demo_config.is_stage_demo("proposal") is True


def test_reset_cache_for_tests_clears_cache(monkeypatch):
    from backend.core import demo_config

    _clear_all(monkeypatch)
    monkeypatch.setenv("DEMO_MOCK_PROPOSAL", "true")
    demo_config.reset_cache_for_tests()
    assert demo_config.is_stage_demo("proposal") is True

    _clear_all(monkeypatch)
    demo_config.reset_cache_for_tests()
    assert demo_config.is_stage_demo("proposal") is False


@pytest.mark.parametrize(
    "env_value,expected",
    [
        ("true", True),
        ("1", True),
        ("yes", True),
        ("TRUE", True),
        ("false", False),
        ("0", False),
        ("", False),
    ],
)
def test_truthy_env_value_parsing(monkeypatch, env_value, expected):
    from backend.core import demo_config

    _clear_all(monkeypatch)
    monkeypatch.setenv("DEMO_MOCK_PROPOSAL", env_value)
    demo_config.reset_cache_for_tests()

    assert demo_config.is_stage_demo("proposal") is expected


def test_unknown_stage_name_returns_false(monkeypatch):
    from backend.core import demo_config

    _clear_all(monkeypatch)
    demo_config.reset_cache_for_tests()

    assert demo_config.is_stage_demo("not_a_real_stage") is False


def test_property_prediction_follows_persisted_settings_without_env_override(monkeypatch):
    """The Settings Demo toggle must drive the route gate when no process override exists."""
    from backend.core import demo_config

    for var in STAGE_ENV_VARS.values():
        monkeypatch.delenv(var, raising=False)
    demo_config.reset_cache_for_tests()

    with patch(
        "backend.core.settings_manager.settings_manager.get_demo_mode_settings",
        return_value={
            "enabled": True,
            "mock_proposal": False,
            "mock_property_prediction": True,
            "mock_generate_new_idea": False,
            "mock_experiment_detail": False,
        },
    ):
        assert demo_config.is_stage_demo("property_prediction") is True

import pytest

from backend.core.settings_manager import SettingsManager


@pytest.fixture
def demo_mode_api_client(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from backend.core.settings_manager import settings_manager
    from backend.main import app

    monkeypatch.setattr(settings_manager, "settings_file", tmp_path / "settings.json")
    monkeypatch.setattr(settings_manager, "_current_settings", {})

    with TestClient(app) as test_client:
        yield test_client, settings_manager


@pytest.mark.api
@pytest.mark.parametrize("enabled", [True, False])
def test_demo_mode_api_enabled_writes_all_stage_flags(demo_mode_api_client, enabled):
    client, manager = demo_mode_api_client

    response = client.post("/api/v1/settings/demo-mode", json={"enabled": enabled})

    expected = {
        "enabled": enabled,
        "mock_proposal": enabled,
        "mock_property_prediction": enabled,
        "mock_generate_new_idea": enabled,
        "mock_experiment_detail": enabled,
    }
    assert response.status_code == 200
    assert response.json() == {"status": "success", **expected}
    assert client.get("/api/v1/settings/demo-mode").json() == expected
    assert manager.get_demo_mode_settings() == expected


@pytest.mark.api
def test_demo_mode_api_stage_only_request_merges_without_disabling_demo(
    demo_mode_api_client,
):
    client, manager = demo_mode_api_client
    initial = {
        "enabled": True,
        "mock_proposal": False,
        "mock_property_prediction": True,
        "mock_generate_new_idea": True,
        "mock_experiment_detail": True,
    }
    manager._current_settings = {"demo_mode": initial}

    response = client.post(
        "/api/v1/settings/demo-mode",
        json={"mock_proposal": True},
    )

    expected = {**initial, "mock_proposal": True}
    assert response.status_code == 200
    assert response.json() == {"status": "success", **expected}
    assert client.get("/api/v1/settings/demo-mode").json() == expected


def test_demo_mode_settings_are_persisted_as_independent_stages(tmp_path):
    manager = SettingsManager()
    manager.settings_file = tmp_path / "settings.json"
    manager._current_settings = {}

    manager.set_demo_mode_settings(
        {
            "enabled": True,
            "mock_proposal": True,
            "mock_property_prediction": False,
            "mock_generate_new_idea": True,
            "mock_experiment_detail": False,
        }
    )

    assert manager.get_demo_mode_settings() == {
        "enabled": True,
        "mock_proposal": True,
        "mock_property_prediction": False,
        "mock_generate_new_idea": True,
        "mock_experiment_detail": False,
    }

    reloaded = SettingsManager()
    reloaded.settings_file = manager.settings_file
    reloaded._current_settings = reloaded._load_settings()
    assert reloaded.get_demo_mode_settings() == manager.get_demo_mode_settings()


def test_demo_mode_defaults_to_disabled(tmp_path):
    manager = SettingsManager()
    manager.settings_file = tmp_path / "settings.json"
    manager._current_settings = {}

    assert manager.get_demo_mode_settings() == {
        "enabled": False,
        "mock_proposal": False,
        "mock_property_prediction": False,
        "mock_generate_new_idea": False,
        "mock_experiment_detail": False,
    }

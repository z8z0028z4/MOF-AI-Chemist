import json

import pytest


@pytest.mark.fast
@pytest.mark.unit
def test_mof_private_settings_missing_file_reports_redacted_status(tmp_path):
    from backend.services.mof_settings_service import get_mof_private_settings_status

    status = get_mof_private_settings_status(tmp_path / "missing.json")

    assert status["settings_file_exists"] is False
    assert status["ready_for_real_run"] is False
    assert "settings_file" in status["missing_fields"]
    assert status["redacted"] is True
    assert "checkpoint_path" not in status
    assert "mean" not in json.dumps(status)


@pytest.mark.fast
@pytest.mark.unit
def test_mof_private_settings_valid_file_never_returns_private_values(tmp_path):
    from backend.services.mof_settings_service import get_mof_private_settings_status

    checkpoint = tmp_path / "private.ckpt"
    cif_root = tmp_path / "private_cifs"
    checkpoint.write_bytes(b"fake checkpoint")
    cif_root.mkdir()

    private_settings = tmp_path / "mof_private_config.json"
    private_settings.write_text(
        json.dumps(
            {
                "checkpoint_path": str(checkpoint),
                "h_mof_cif_root": str(cif_root),
                "downstream": "private_downstream_name",
                "target_property": "CO2 uptake",
                "condition": "298 K, 0.15 bar",
                "unit": "mmol/g",
                "normalization": {
                    "mean": 1.23,
                    "std": 0.45,
                    "std_source": "private_literature_spreadsheet_population_std",
                },
            }
        ),
        encoding="utf-8",
    )

    status = get_mof_private_settings_status(private_settings)
    payload = json.dumps(status)

    assert status["settings_file_exists"] is True
    assert status["ready_for_real_run"] is True
    assert status["missing_fields"] == []
    assert status["invalid_fields"] == []
    assert status["configured_fields"]["checkpoint_path"] is True
    assert status["configured_fields"]["h_mof_cif_root"] is True
    assert status["configured_fields"]["downstream"] is True
    assert status["configured_fields"]["normalization"] is True
    assert status["display"]["target_property"] == "CO2 uptake"
    assert status["display"]["condition"] == "298 K, 0.15 bar"
    assert status["display"]["unit"] == "mmol/g"
    assert str(checkpoint) not in payload
    assert str(cif_root) not in payload
    assert "private_downstream_name" not in payload
    assert "1.23" not in payload
    assert "0.45" not in payload


@pytest.mark.fast
@pytest.mark.unit
def test_mof_private_settings_invalid_numbers_block_real_run(tmp_path):
    from backend.services.mof_settings_service import get_mof_private_settings_status

    private_settings = tmp_path / "mof_private_config.json"
    private_settings.write_text(
        json.dumps(
            {
                "checkpoint_path": str(tmp_path / "missing.ckpt"),
                "h_mof_cif_root": str(tmp_path / "missing_cifs"),
                "downstream": "private_downstream_name",
                "normalization": {"mean": "bad", "std": 0},
            }
        ),
        encoding="utf-8",
    )

    status = get_mof_private_settings_status(private_settings)

    assert status["ready_for_real_run"] is False
    assert "normalization.mean" in status["invalid_fields"]
    assert "normalization.std" in status["invalid_fields"]
    assert "checkpoint_path.exists" in status["invalid_fields"]
    assert "h_mof_cif_root.exists" in status["invalid_fields"]


@pytest.mark.fast
@pytest.mark.api
def test_mof_private_settings_status_route_uses_redacted_service(monkeypatch):
    from backend.api.routes import mof as mof_routes

    fake_status = {
        "settings_file_exists": True,
        "settings_location": "env:MOF_PRIVATE_SETTINGS_PATH",
        "ready_for_real_run": False,
        "missing_fields": ["checkpoint_path"],
        "invalid_fields": [],
        "configured_fields": {
            "checkpoint_path": False,
            "h_mof_cif_root": True,
            "downstream": True,
            "normalization": True,
        },
        "display": {
            "target_property": "CO2 uptake",
            "condition": "298 K, 0.15 bar",
            "unit": "mmol/g",
        },
        "redacted": True,
    }

    monkeypatch.setattr(mof_routes, "get_mof_private_settings_status", lambda: fake_status)

    assert mof_routes.get_private_settings_status() == fake_status

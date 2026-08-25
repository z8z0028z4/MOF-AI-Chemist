"""
Tests for the theoretical XRD calculation API route.

These tests are written FIRST (TDD/RED phase) before the implementation.
They cover:
- Successful XRD calculation with an uploaded CIF file
- Successful XRD calculation using a server-side CIF path
- Error handling for missing/invalid files
- Error handling for corrupt CIF content
- Parameter validation (wavelength, max_two_theta, fwhm)
- Support for non-standard CIF formats (CoRE MOF DB, GCMC)
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# Minimal valid CIF content for testing (simple cubic MOF-like structure)
MINIMAL_VALID_CIF = """\
data_test_structure
_cell_length_a   10.0
_cell_length_b   10.0
_cell_length_c   10.0
_cell_angle_alpha  90.0
_cell_angle_beta   90.0
_cell_angle_gamma  90.0
_symmetry_space_group_name_H-M  'P 1'
_symmetry_Int_Tables_number  1
loop_
  _atom_site_label
  _atom_site_type_symbol
  _atom_site_fract_x
  _atom_site_fract_y
  _atom_site_fract_z
  Zn1  Zn  0.00  0.00  0.00
  C1   C   0.50  0.50  0.00
  O1   O   0.25  0.25  0.00
"""

# CIF with a non-standard JSON header (like CoRE MOF DB / GCMC simulation files)
GCMC_CIF_WITH_HEADER = """\
{"source": "GCMC", "year": 2012}
data_GCMC_structure
_cell_length_a   12.0
_cell_length_b   12.0
_cell_length_c   12.0
_cell_angle_alpha  90.0
_cell_angle_beta   90.0
_cell_angle_gamma  90.0
_symmetry_space_group_name_H-M  'P 1'
_symmetry_Int_Tables_number  1
loop_
  _atom_site_label
  _atom_site_type_symbol
  _atom_site_fract_x
  _atom_site_fract_y
  _atom_site_fract_z
  Cu1  Cu  0.00  0.00  0.00
  O1   O   0.25  0.25  0.00
"""


# Mock XRD result that simulate the xrd_calculator.py output
MOCK_XRD_RESULT = {
    "space_group": "P1",
    "space_group_number": 1,
    "crystal_system": "triclinic",
    "wavelength": 1.54184,
    "num_peaks": 3,
    "peaks": [
        {"two_theta": 8.84, "intensity": 100.0, "hkl": "(100)", "d_spacing": 10.0},
        {"two_theta": 12.52, "intensity": 62.3, "hkl": "(110)", "d_spacing": 7.07},
        {"two_theta": 17.74, "intensity": 30.1, "hkl": "(200)", "d_spacing": 5.0},
    ],
    "profile": {
        "two_theta": [5.0, 5.08, 5.15],
        "intensity": [0.0, 0.1, 0.3],
    },
}


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    from backend.main import app
    return TestClient(app)


@pytest.mark.fast
@pytest.mark.unit
def test_xrd_calculate_with_upload_success(client, tmp_path):
    """Test that a valid CIF upload returns a successful XRD pattern."""
    cif_content = MINIMAL_VALID_CIF.encode("utf-8")

    with patch("backend.api.routes.mof.run_xrd_calculation") as mock_calc:
        mock_calc.return_value = MOCK_XRD_RESULT

        res = client.post(
            "/api/v1/mof/xrd/calculate",
            files={"file": ("test.cif", cif_content, "chemical/x-cif")},
        )

    assert res.status_code == 200
    data = res.json()
    assert "peaks" in data
    assert "profile" in data
    assert "space_group" in data
    assert "crystal_system" in data
    assert "wavelength" in data
    assert isinstance(data["peaks"], list)
    assert len(data["peaks"]) > 0
    assert "two_theta" in data["peaks"][0]
    assert "intensity" in data["peaks"][0]
    assert "hkl" in data["peaks"][0]
    assert "d_spacing" in data["peaks"][0]
    assert "two_theta" in data["profile"]
    assert "intensity" in data["profile"]


@pytest.mark.fast
@pytest.mark.unit
def test_xrd_calculate_with_cif_path_success(client, tmp_path):
    """Test that a server-side CIF path returns a successful XRD pattern."""
    cif_file = tmp_path / "test.cif"
    cif_file.write_text(MINIMAL_VALID_CIF, encoding="utf-8")

    with patch("backend.api.routes.mof.run_xrd_calculation") as mock_calc:
        mock_calc.return_value = MOCK_XRD_RESULT

        res = client.post(
            "/api/v1/mof/xrd/calculate",
            data={"cif_path": str(cif_file)},
        )

    assert res.status_code == 200
    data = res.json()
    assert "peaks" in data
    assert data["num_peaks"] == 3


@pytest.mark.fast
@pytest.mark.unit
def test_xrd_calculate_no_input(client):
    """Test that missing both file and cif_path returns 400."""
    res = client.post("/api/v1/mof/xrd/calculate")
    assert res.status_code == 400
    data = res.json()
    assert "detail" in data


@pytest.mark.fast
@pytest.mark.unit
def test_xrd_calculate_cif_path_not_found(client):
    """Test that a non-existent cif_path returns 404."""
    res = client.post(
        "/api/v1/mof/xrd/calculate",
        data={"cif_path": "/nonexistent/path/structure.cif"},
    )
    assert res.status_code == 404


@pytest.mark.fast
@pytest.mark.unit
def test_xrd_calculate_invalid_extension(client):
    """Test that uploading a non-CIF file returns 400."""
    res = client.post(
        "/api/v1/mof/xrd/calculate",
        files={"file": ("not_a_cif.txt", b"hello world", "text/plain")},
    )
    assert res.status_code == 400
    data = res.json()
    assert "cif" in data["detail"].lower() or "format" in data["detail"].lower()


@pytest.mark.fast
@pytest.mark.unit
def test_xrd_calculate_custom_parameters(client, tmp_path):
    """Test that custom wavelength/max_two_theta/fwhm parameters are forwarded."""
    cif_content = MINIMAL_VALID_CIF.encode("utf-8")
    captured_kwargs = {}

    def capture_kwargs(cif_path, **kwargs):
        captured_kwargs.update(kwargs)
        return MOCK_XRD_RESULT

    with patch("backend.api.routes.mof.run_xrd_calculation", side_effect=capture_kwargs):
        res = client.post(
            "/api/v1/mof/xrd/calculate",
            files={"file": ("test.cif", cif_content, "chemical/x-cif")},
            data={
                "wavelength": "1.78897",
                "max_two_theta": "60.0",
                "fwhm": "0.2",
            },
        )

    assert res.status_code == 200
    assert abs(captured_kwargs.get("wavelength", 0) - 1.78897) < 1e-4
    assert abs(captured_kwargs.get("max_two_theta", 0) - 60.0) < 1e-4
    assert abs(captured_kwargs.get("fwhm", 0) - 0.2) < 1e-4


@pytest.mark.fast
@pytest.mark.unit
def test_xrd_calculate_worker_error_returns_500(client):
    """Test that an internal worker error returns 500."""
    cif_content = MINIMAL_VALID_CIF.encode("utf-8")

    with patch("backend.api.routes.mof.run_xrd_calculation") as mock_calc:
        mock_calc.side_effect = RuntimeError("pymatgen internal error")

        res = client.post(
            "/api/v1/mof/xrd/calculate",
            files={"file": ("test.cif", cif_content, "chemical/x-cif")},
        )

    assert res.status_code == 500
    data = res.json()
    assert "detail" in data


@pytest.mark.fast
@pytest.mark.unit
def test_xrd_calculate_gcmc_cif_with_header(client):
    """Test that a CIF with non-standard GCMC JSON header is accepted."""
    cif_content = GCMC_CIF_WITH_HEADER.encode("utf-8")

    with patch("backend.api.routes.mof.run_xrd_calculation") as mock_calc:
        mock_calc.return_value = MOCK_XRD_RESULT

        res = client.post(
            "/api/v1/mof/xrd/calculate",
            files={"file": ("gcmc.cif", cif_content, "chemical/x-cif")},
        )

    # Should succeed (CIF cleaning is done inside run_xrd_calculation)
    assert res.status_code == 200
    mock_calc.assert_called_once()


@pytest.mark.fast
@pytest.mark.unit
def test_xrd_result_structure(client):
    """Test that the result has the correct complete structure."""
    cif_content = MINIMAL_VALID_CIF.encode("utf-8")

    with patch("backend.api.routes.mof.run_xrd_calculation") as mock_calc:
        mock_calc.return_value = MOCK_XRD_RESULT

        res = client.post(
            "/api/v1/mof/xrd/calculate",
            files={"file": ("test.cif", cif_content, "chemical/x-cif")},
        )

    assert res.status_code == 200
    data = res.json()

    # Top-level fields
    required_fields = {"space_group", "space_group_number", "crystal_system",
                       "wavelength", "num_peaks", "peaks", "profile"}
    for field in required_fields:
        assert field in data, f"Missing field: {field}"

    # Profile structure
    assert "two_theta" in data["profile"]
    assert "intensity" in data["profile"]
    assert len(data["profile"]["two_theta"]) == len(data["profile"]["intensity"])

    # Peak structure
    if data["peaks"]:
        peak = data["peaks"][0]
        assert "two_theta" in peak
        assert "intensity" in peak
        assert "hkl" in peak
        assert "d_spacing" in peak


@pytest.mark.fast
@pytest.mark.unit
def test_xrd_calculate_with_generator_success(client, tmp_path):
    """Test that specifying a generator_run_id and artifact_id successfully calculates XRD."""
    # Create a mock CIF file that would be resolved by artifact_service
    cif_file = tmp_path / "resolved.cif"
    cif_file.write_text(MINIMAL_VALID_CIF, encoding="utf-8")

    # Mock run objects
    mock_gen_run = MagicMock()
    mock_gen_run.run_id = "gen_run_123"
    mock_gen_run.tool = "pormake"

    mock_xrd_run = MagicMock()
    mock_xrd_run.run_id = "xrd_run_456"
    mock_xrd_run.run_dir = tmp_path

    # Patch services
    with patch("backend.api.routes.mof.run_store.get_run", return_value=mock_gen_run) as mock_get_run, \
         patch("backend.api.routes.mof.artifact_service.resolve", return_value=cif_file) as mock_resolve, \
         patch("backend.api.routes.mof.run_store.create_run", return_value=mock_xrd_run) as mock_create_run, \
         patch("backend.api.routes.mof.run_store.update_status") as mock_update_status, \
         patch("backend.api.routes.mof.artifact_service.write_manifest") as mock_write_manifest, \
         patch("backend.api.routes.mof.run_xrd_calculation", return_value=MOCK_XRD_RESULT) as mock_calc:

        res = client.post(
            "/api/v1/mof/xrd/calculate",
            data={
                "generator_run_id": "gen_run_123",
                "artifact_id": "art_789",
            },
        )

    assert res.status_code == 200
    data = res.json()
    assert "peaks" in data

    # Verify interaction
    mock_get_run.assert_called_with("gen_run_123")
    mock_resolve.assert_called_with("gen_run_123", "art_789")
    mock_create_run.assert_called_once()
    assert mock_create_run.call_args[1]["tool"] == "xrd"
    mock_update_status.assert_any_call("xrd_run_456", "running", progress=0.2, message="Calculating XRD pattern")
    mock_update_status.assert_any_call("xrd_run_456", "succeeded", progress=1.0, message="Calculation complete")


@pytest.mark.fast
@pytest.mark.unit
def test_xrd_calculate_saves_to_run_store(client, tmp_path):
    """Test that a standard upload XRD calculation saves the run configuration and result to run_store."""
    cif_content = MINIMAL_VALID_CIF.encode("utf-8")

    mock_xrd_run = MagicMock()
    mock_xrd_run.run_id = "xrd_run_789"
    mock_xrd_run.run_dir = tmp_path

    with patch("backend.api.routes.mof.run_store.create_run", return_value=mock_xrd_run) as mock_create_run, \
         patch("backend.api.routes.mof.run_store.update_status") as mock_update_status, \
         patch("backend.api.routes.mof.artifact_service.write_manifest") as mock_write_manifest, \
         patch("backend.api.routes.mof.run_xrd_calculation", return_value=MOCK_XRD_RESULT) as mock_calc:

        res = client.post(
            "/api/v1/mof/xrd/calculate",
            files={"file": ("test.cif", cif_content, "chemical/x-cif")},
        )

    assert res.status_code == 200

    # Check that a run directory structure was created & artifacts saved
    mock_create_run.assert_called_once()
    assert mock_create_run.call_args[1]["tool"] == "xrd"

    # The result.json should be written in the mock run directory
    result_json_path = tmp_path / "result.json"
    assert result_json_path.is_file()
    result_data = json.loads(result_json_path.read_text(encoding="utf-8"))
    assert result_data["status"] == "succeeded"
    assert len(result_data["results"]) == 1
    assert result_data["results"][0]["artifact_id"] == "xrd_pattern"

    # The xrd_pattern.json should be written in the mock run directory
    xrd_pattern_json_path = tmp_path / "xrd_pattern.json"
    assert xrd_pattern_json_path.is_file()
    xrd_data = json.loads(xrd_pattern_json_path.read_text(encoding="utf-8"))
    assert "peaks" in xrd_data

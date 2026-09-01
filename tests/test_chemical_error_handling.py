"""Regression tests for PubChem not-found versus upstream failures."""

from unittest.mock import patch

import pytest
import requests
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.chemical_service import chemical_service
from backend.services.pubchem_service import (
    get_single_chemical,
    search_formula,
)
from backend.utils.exceptions import PubChemNotFoundError, PubChemUpstreamError


client = TestClient(app)


class Response:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self.ok = 200 <= status_code < 300
        self._payload = payload or {}

    def json(self):
        return self._payload


@pytest.mark.unit
@pytest.mark.parametrize("status", [429, 500, 502])
def test_name_upstream_http_errors_are_typed(status):
    with patch("backend.services.pubchem_service.requests.get", return_value=Response(status)):
        with pytest.raises(PubChemUpstreamError):
            get_single_chemical("ethanol")


@pytest.mark.unit
def test_name_transport_error_is_typed():
    with patch(
        "backend.services.pubchem_service.requests.get",
        side_effect=requests.exceptions.Timeout("timed out"),
    ):
        with pytest.raises(PubChemUpstreamError):
            get_single_chemical("ethanol")


@pytest.mark.unit
@pytest.mark.parametrize(
    "response",
    [Response(404), Response(200, {"IdentifierList": {"CID": []}})],
)
def test_name_verified_no_result_is_typed_not_found(response):
    with patch("backend.services.pubchem_service.requests.get", return_value=response):
        with pytest.raises(PubChemNotFoundError):
            get_single_chemical("not-a-chemical")


@pytest.mark.unit
@pytest.mark.parametrize("status", [429, 500])
def test_formula_upstream_http_errors_are_typed(status):
    with patch("backend.services.pubchem_service.requests.get", return_value=Response(status)):
        with pytest.raises(PubChemUpstreamError):
            search_formula("H2O")


@pytest.mark.unit
def test_formula_empty_identifiers_are_not_found():
    with patch(
        "backend.services.pubchem_service.requests.get",
        return_value=Response(200, {"IdentifierList": {"CID": []}}),
    ):
        with pytest.raises(PubChemNotFoundError):
            search_formula("Xx999999")


@pytest.mark.api
@pytest.mark.parametrize(
    "patch_target, status, detail",
    [
        ("backend.services.chemical_service.chemical_service.get_chemical_with_database_lookup", 503, "暫時無法使用"),
        ("backend.services.chemical_service.chemical_service.search_formula_candidates", 404, "未找到"),
        ("backend.services.chemical_service.chemical_service.get_selected_chemical", 503, "暫時無法使用"),
    ],
)
def test_single_lookup_maps_typed_errors(patch_target, status, detail):
    error = PubChemUpstreamError("offline") if status == 503 else PubChemNotFoundError()
    with patch(patch_target, side_effect=error):
        response = client.post(
            "/api/v1/chemical/search",
            json={
                "chemical_name": "H2O" if "formula" in patch_target else "ethanol",
                "selected_cid": 23 if "selected" in patch_target else None,
            },
        )
    assert response.status_code == status
    assert detail in response.json()["detail"]


@pytest.mark.unit
def test_upstream_failure_does_not_draw_or_save():
    with patch(
        "backend.services.chemical_service.get_single_chemical",
        side_effect=PubChemUpstreamError("offline"),
    ), patch.object(chemical_service, "add_smiles_drawing") as draw, patch(
        "backend.services.chemical_service.chemical_db_service.save_chemical"
    ) as save:
        with pytest.raises(PubChemUpstreamError):
            chemical_service.get_selected_chemical("ethanol", 702)
    draw.assert_not_called()
    save.assert_not_called()

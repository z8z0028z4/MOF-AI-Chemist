"""Focused contract tests for PubChem formula routing and CID selection."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.pubchem_service import classify_chemical_query, search_formula


client = TestClient(app)


@pytest.mark.unit
def test_classifier_is_bounded_and_preserves_name_routing():
    assert classify_chemical_query("C6H12O") == "formula"
    assert classify_chemical_query("H2O") == "formula"
    assert classify_chemical_query("ethanol") == "name"
    assert classify_chemical_query("water solution") == "name"


@pytest.mark.api
def test_formula_multiple_hits_are_bounded_and_do_not_detail_lookup():
    candidates = [
        {"cid": cid, "name": f"compound-{cid}", "formula": "C6H12O", "molecular_weight": "100"}
        for cid in range(1, 26)
    ]
    with patch("backend.services.chemical_service.search_formula", return_value=(candidates, 25)) as search, patch(
        "backend.services.chemical_service.chemical_service.get_selected_chemical"
    ) as selected:
        response = client.post("/api/v1/chemical/search", json={"chemical_name": "C6H12O"})

    assert response.status_code == 200
    data = response.json()
    assert data["query_type"] == "formula"
    assert data["candidate_count"] == 25
    assert len(data["candidates"]) == 20
    assert data["candidates"][0]["cid"] == 1
    search.assert_called_once_with("C6H12O", limit=20)
    selected.assert_not_called()


@pytest.mark.api
def test_formula_zero_hits_is_not_found():
    with patch("backend.services.chemical_service.search_formula", return_value=([], 0)):
        response = client.post("/api/v1/chemical/search", json={"chemical_name": "H2O"})
    assert response.status_code == 404


@pytest.mark.api
def test_formula_single_hit_uses_direct_cid_detail_lookup():
    candidate = {"cid": 962, "name": "oxidane", "formula": "H2O", "molecular_weight": "18.015"}
    with patch("backend.services.chemical_service.search_formula", return_value=([candidate], 1)), patch(
        "backend.services.chemical_service.chemical_service.get_selected_chemical",
        return_value={"cid": 962, "name": "oxidane", "formula": "H2O", "weight": "18.015"},
    ) as selected:
        response = client.post("/api/v1/chemical/search", json={"chemical_name": "H2O"})

    assert response.status_code == 200
    assert response.json()["query_type"] == "formula"
    assert response.json()["cid"] == 962
    selected.assert_called_once_with("H2O", 962)


@pytest.mark.api
def test_selected_cid_uses_direct_detail_path_and_preserves_query():
    detail = {"cid": 123, "name": "selected", "formula": "C6H12O", "weight": "100"}
    with patch(
        "backend.services.chemical_service.chemical_service.get_selected_chemical",
        return_value=detail,
    ) as selected, patch(
        "backend.services.chemical_service.chemical_service.get_chemical_with_database_lookup"
    ) as name_lookup:
        response = client.post(
            "/api/v1/chemical/search",
            json={"chemical_name": "C6H12O", "selected_cid": 123},
        )

    assert response.status_code == 200
    assert response.json()["cid"] == 123
    assert response.json()["query_type"] == "formula"
    selected.assert_called_once_with("C6H12O", 123, True, True)
    name_lookup.assert_not_called()


@pytest.mark.unit
def test_search_formula_uses_fastformula_and_strict_tls():
    class Response:
        ok = True

        def __init__(self, payload):
            self.payload = payload

        def json(self):
            return self.payload

    responses = iter(
        [
            Response({"IdentifierList": {"CID": [1, 2]}}),
            Response({"PropertyTable": {"Properties": [{"IUPACName": "one", "MolecularFormula": "H2O", "MolecularWeight": 18.0}]}}),
            Response({"PropertyTable": {"Properties": [{"IUPACName": "two", "MolecularFormula": "H2O", "MolecularWeight": 18.0}]}}),
        ]
    )
    with patch("backend.services.pubchem_service.requests.get", side_effect=lambda *args, **kwargs: responses.__next__()) as get:
        summaries, count = search_formula("H2O")

    assert count == 2
    assert [item["cid"] for item in summaries] == [1, 2]
    assert "/compound/fastformula/H2O/cids/JSON" in get.call_args_list[0].args[0]
    assert all(call.kwargs["verify"] is not False for call in get.call_args_list)

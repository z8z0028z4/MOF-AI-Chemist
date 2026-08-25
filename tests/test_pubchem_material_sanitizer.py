from __future__ import annotations

from unittest.mock import MagicMock, patch

from backend.services.pubchem_service import (
    _get_pubchem_view_json,
    extract_and_fetch_chemicals,
    get_boiling_and_melting_point,
    get_safety_info,
    sanitize_material_names,
)


def test_sanitize_material_names_rejects_prose_metadata_and_duplicates():
    materials = [
        " Zinc nitrate hexahydrate ",
        "2-methylimidazole",
        "N,N-dimethylformamide",
        "2-METHYLIMIDAZOLE",
        "mof_metal_element:Zn",
        "以下清單已移除並修正為其他材料列表",
        "Hexane-1,6-diamine溶液(僅為範例,實際不使用)已移除其餘清單",
        "x" * 121,
        "",
        None,
    ]

    accepted, ignored = sanitize_material_names(materials)

    assert accepted == [
        "Zinc nitrate hexahydrate",
        "2-methylimidazole",
        "N,N-dimethylformamide",
    ]
    assert "mof_metal_element:Zn" in ignored
    assert any("以下清單" in item for item in ignored)
    assert any("Hexane-1,6-diamine" in item for item in ignored)


def test_sanitize_material_names_caps_query_count():
    accepted, ignored = sanitize_material_names(
        [f"compound-{index}" for index in range(25)],
        max_items=20,
    )

    assert len(accepted) == 20
    assert ignored == [f"compound-{index}" for index in range(20, 25)]


def test_extract_and_fetch_chemicals_queries_only_clean_names_and_dedupes_cid(
    tmp_path,
):
    response = MagicMock()
    response.ok = True
    response.json.return_value = {"PC_Compounds": [{}]}

    def fake_parse(_payload):
        return {
            "cid": 12749,
            "name": "2-methyl-1H-imidazole",
            "iupac_name": "2-methyl-1H-imidazole",
            "formula": "C4H6N2",
            "weight": "82.11",
            "smiles": "CC1=NC=CN1",
            "image_url": "",
        }

    with (
        patch(
            "backend.services.pubchem_service.search_source",
            side_effect=lambda names, limit=2: [
                {"cid": 12749, "query": names[0], "source": "PubChem"}
            ],
        ) as search,
        patch("backend.services.pubchem_service.requests.get", return_value=response),
        patch(
            "backend.services.pubchem_service.parse_pubchem_json",
            side_effect=fake_parse,
        ),
        patch(
            "backend.services.pubchem_service.get_boiling_and_melting_point",
            return_value={},
        ),
        patch(
            "backend.services.pubchem_service.get_safety_info",
            return_value={"ghs_icons": [], "nfpa_image": None, "cas": None},
        ),
    ):
        summaries, not_found = extract_and_fetch_chemicals(
            [
                "2-methylimidazole",
                "2-methyl-1H-imidazole",
                "mof_linker_name:2-methylimidazole",
            ],
            save_dir=tmp_path,
        )

    assert len(summaries) == 1
    assert summaries[0]["cid"] == 12749
    assert not_found == []
    assert [call.args[0][0] for call in search.call_args_list] == [
        "2-methylimidazole",
        "2-methyl-1H-imidazole",
    ]


def test_pubchem_view_payload_is_shared_between_property_and_safety_parsers():
    response = MagicMock()
    response.ok = True
    response.json.return_value = {"Record": {"Section": []}}
    _get_pubchem_view_json.cache_clear()

    with patch(
        "backend.services.pubchem_service.requests.get",
        return_value=response,
    ) as request:
        get_boiling_and_melting_point(11138)
        get_safety_info(11138)

    assert request.call_count == 1

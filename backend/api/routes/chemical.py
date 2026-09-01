"""
化學品查詢 API 路由
==================

處理化學品信息查詢、安全數據等功能
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
import sys
import os

# 添加原項目路徑到 sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../app'))

# 導入新的模型和服務
from backend.api.models.chemical_models import (
    ChemicalRequest, ChemicalResponse, ChemicalBatchRequest,
    ChemicalBatchResponse, ChemicalDatabaseRecord, ChemicalSearchRequest, ChemicalSearchResponse
)
from backend.services.chemical_service import chemical_service
from backend.services.chemical_database_service import chemical_db_service
from backend.services.pubchem_service import chemical_metadata_extractor, classify_chemical_query
from backend.utils.exceptions import PubChemNotFoundError, PubChemUpstreamError

router = APIRouter()

# 模型定義已移至 chemical_models.py

@router.post("/chemical/search", response_model=ChemicalResponse)
async def search_chemical(request: ChemicalRequest):
    """
    查詢單個化學品信息（增強版，支持數據庫存儲和結構繪製）

    Args:
        request: 化學品查詢請求

    Returns:
        化學品詳細信息
    """
    try:
        query_type = classify_chemical_query(request.chemical_name)
        if query_type == "formula" and request.selected_cid is None:
            result = chemical_service.search_formula_candidates(request.chemical_name)
        elif request.selected_cid is not None:
            result = chemical_service.get_selected_chemical(
                request.chemical_name, request.selected_cid,
                request.include_structure, request.save_to_database
            )
        else:
            # Preserve the existing name-query service contract.
            result = chemical_service.get_chemical_with_database_lookup(
                chemical_name=request.chemical_name,
                include_structure=request.include_structure,
                save_to_db=request.save_to_database
            )

        if not result:
            raise HTTPException(status_code=404, detail="化學品未找到")

        if result.get("error"):
            if query_type == "formula":
                raise HTTPException(status_code=404, detail="化學品未找到")
            return ChemicalResponse(name=request.chemical_name, error=result.get("error"), query_type=query_type, candidate_count=result.get("candidate_count"))

        # 構建響應數據
        safety_data = None
        if request.include_safety and result.get("safety_icons"):
            safety_data = {
                "nfpa_image": result["safety_icons"].get("nfpa_image", ""),
                "ghs_icons": result["safety_icons"].get("ghs_icons", [])
            }

        properties = None
        if request.include_properties:
            properties = {
                "formula": result.get("formula"),
                "molecular_weight": result.get("weight"),
                "cas_number": result.get("cas"),
                "smiles": result.get("smiles"),
                "boiling_point": result.get("boiling_point_c"),
                "melting_point": result.get("melting_point_c")
            }

        return ChemicalResponse(
            name=result.get("name", request.chemical_name),
            formula=result.get("formula"),
            molecular_weight=result.get("weight"),
            cas_number=result.get("cas"),
            smiles=result.get("smiles"),
            boiling_point=result.get("boiling_point_c"),
            melting_point=result.get("melting_point_c"),
            pubchem_url=result.get("pubchem_url"),
            image_url=result.get("image_url"),
            svg_structure=result.get("svg_structure"),
            png_structure=result.get("png_structure"),
            safety_data=safety_data,
            properties=properties,
            cid=result.get("cid"),
            saved_to_database=result.get("saved_to_database", False),
            query_type=result.get("query_type", query_type),
            candidates=result.get("candidates", []),
            candidate_count=result.get("candidate_count")
        )

    except PubChemNotFoundError as exc:
        raise HTTPException(status_code=404, detail="化學品未找到") from exc
    except PubChemUpstreamError as exc:
        raise HTTPException(status_code=503, detail="PubChem 暫時無法使用，請稍後重試") from exc
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"化學品查詢失敗: {str(e)}")

@router.post("/chemical/batch-search", response_model=ChemicalBatchResponse)
async def batch_search_chemicals(request: ChemicalBatchRequest):
    """
    批量查詢化學品信息（增強版，支持數據庫存儲和結構繪製）

    Args:
        request: 批量化學品查詢請求

    Returns:
        批量查詢結果
    """
    try:
        # 使用增強的批量查詢服務
        results, not_found = chemical_service.batch_get_chemicals_with_database(
            chemical_names=request.chemical_names,
            include_structure=request.include_structure,
            save_to_db=request.save_to_database
        )

        # 轉換為響應格式
        chemical_responses = []
        saved_count = 0

        for result in results:
            if result.get("error"):
                continue

            # 構建響應數據
            safety_data = None
            if request.include_safety and result.get("safety_icons"):
                safety_data = {
                    "nfpa_image": result["safety_icons"].get("nfpa_image", ""),
                    "ghs_icons": result["safety_icons"].get("ghs_icons", [])
                }

            properties = None
            if request.include_properties:
                properties = {
                    "formula": result.get("formula"),
                    "molecular_weight": result.get("weight"),
                    "cas_number": result.get("cas"),
                    "smiles": result.get("smiles"),
                    "boiling_point": result.get("boiling_point_c"),
                    "melting_point": result.get("melting_point_c")
                }

            chemical_responses.append(ChemicalResponse(
                name=result.get("name"),
                formula=result.get("formula"),
                molecular_weight=result.get("weight"),
                cas_number=result.get("cas"),
                smiles=result.get("smiles"),
                boiling_point=result.get("boiling_point_c"),
                melting_point=result.get("melting_point_c"),
                pubchem_url=result.get("pubchem_url"),
                image_url=result.get("image_url"),
                svg_structure=result.get("svg_structure"),
                png_structure=result.get("png_structure"),
                safety_data=safety_data,
                properties=properties,
                cid=result.get("cid"),
                saved_to_database=result.get("saved_to_database", False)
            ))

            if result.get("saved_to_database"):
                saved_count += 1

        return ChemicalBatchResponse(
            results=chemical_responses,
            not_found=not_found,
            total_count=len(request.chemical_names),
            success_count=len(chemical_responses),
            saved_count=saved_count
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量化學品查詢失敗: {str(e)}")

@router.get("/chemical/safety/{chemical_name}")
async def get_chemical_safety(chemical_name: str):
    """
    獲取化學品安全信息

    Args:
        chemical_name: 化學品名稱

    Returns:
        安全信息數據
    """
    try:
        result = chemical_metadata_extractor(chemical_name)

        if not result or result.get("error"):
            raise HTTPException(status_code=404, detail="未找到化學品安全信息")

        safety_data = {
            "nfpa_image": result.get("safety_icons", {}).get("nfpa_image", ""),
            "ghs_icons": result.get("safety_icons", {}).get("ghs_icons", []),
            "hazard_statements": result.get("hazard_statements", []),
            "precautionary_statements": result.get("precautionary_statements", [])
        }

        return {
            "chemical_name": chemical_name,
            "safety_data": safety_data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"安全信息查詢失敗: {str(e)}")

@router.get("/chemical/properties/{chemical_name}")
async def get_chemical_properties(chemical_name: str):
    """
    獲取化學品物理化學性質

    Args:
        chemical_name: 化學品名稱

    Returns:
        物理化學性質數據
    """
    try:
        result = chemical_metadata_extractor(chemical_name)

        if not result or result.get("error"):
            raise HTTPException(status_code=404, detail="未找到化學品性質信息")

        properties = {
            "formula": result.get("formula"),
            "molecular_weight": result.get("weight"),
            "cas_number": result.get("cas"),
            "smiles": result.get("smiles"),
            "boiling_point": result.get("boiling_point_c"),
            "melting_point": result.get("melting_point_c"),
            "density": result.get("density"),
            "solubility": result.get("solubility")
        }

        return {
            "chemical_name": chemical_name,
            "properties": properties
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"性質信息查詢失敗: {str(e)}")


def _build_database_search_response(request: ChemicalSearchRequest) -> ChemicalSearchResponse:
    results = chemical_service.search_chemicals_in_database(
        query=request.query,
        limit=request.limit
    )

    db_records = []
    for result in results:
        if not result.get("error"):
            db_records.append(ChemicalDatabaseRecord(
                name=result.get("name"),
                formula=result.get("formula"),
                molecular_weight=result.get("weight"),
                cas_number=result.get("cas"),
                smiles=result.get("smiles"),
                boiling_point=result.get("boiling_point_c"),
                melting_point=result.get("melting_point_c"),
                pubchem_url=result.get("pubchem_url"),
                image_url=result.get("image_url"),
                svg_structure=result.get("svg_structure") if request.include_structure else None,
                png_structure=result.get("png_structure") if request.include_structure else None,
                safety_data=result.get("safety_icons", {}),
                properties=result.get("properties", {}),
                cid=result.get("cid")
            ))

    return ChemicalSearchResponse(
        results=db_records,
        total_count=len(db_records),
        query=request.query
    )


@router.post("/chemical/database-search", response_model=ChemicalSearchResponse)
async def search_chemicals_in_database(request: ChemicalSearchRequest):
    """
    在數據庫中搜索化學品

    Args:
        request: 搜索請求

    Returns:
        搜索結果
    """
    try:
        return _build_database_search_response(request)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"數據庫搜索失敗: {str(e)}")


@router.get("/chemical/database-search", response_model=ChemicalSearchResponse)
async def search_chemicals_in_database_get(query: str, limit: int = 10, include_structure: bool = True):
    """GET compatibility wrapper for database chemical search."""
    try:
        return _build_database_search_response(
            ChemicalSearchRequest(query=query, limit=limit, include_structure=include_structure)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"數據庫搜索失敗: {str(e)}")


@router.get("/chemical/database-stats")
async def get_database_stats():
    """
    獲取化學品數據庫統計信息

    Returns:
        統計信息
    """
    try:
        stats = chemical_service.get_database_stats()
        return stats

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取統計信息失敗: {str(e)}")


@router.get("/chemical/database-list")
async def get_database_chemicals(limit: int = 1000):
    """
    獲取數據庫中的所有化學品

    Args:
        limit: 結果數量限制

    Returns:
        化學品列表
    """
    try:
        results = chemical_db_service.get_all_chemicals(limit)
        return {
            "chemicals": results,
            "total_count": len(results)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取化學品列表失敗: {str(e)}")

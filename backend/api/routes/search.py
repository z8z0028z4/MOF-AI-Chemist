"""
文獻搜尋 API 路由
================

處理文獻搜尋、下載和查詢功能
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import sys
import os

# 添加原項目路徑到 sys.path
# sys.path.append(os.path.join(os.path.dirname(__file__), '../../../app'))  # 已重組，不再需要

from backend.services.search_service import search_and_download_only

router = APIRouter()

class SearchRequest(BaseModel):
    """搜尋請求模型"""
    query: str
    max_results: Optional[int] = 10

class SearchResponse(BaseModel):
    """搜尋響應模型"""
    success: bool
    message: str
    results: List[Dict[str, Any]]
    total_count: int



@router.post("/search/literature", response_model=SearchResponse)
async def search_literature(request: SearchRequest):
    """
    搜尋並下載文獻

    Args:
        request: 搜尋請求

    Returns:
        搜尋結果和下載狀態
    """
    try:
        # 調用原有的搜尋和下載功能
        pdfs = search_and_download_only(request.query)

        results = []
        for pdf_path in pdfs:
            results.append({
                "filename": os.path.basename(pdf_path),
                "path": pdf_path,
                "size": os.path.getsize(pdf_path) if os.path.exists(pdf_path) else 0
            })

        return SearchResponse(
            success=True,
            message=f"成功下載 {len(pdfs)} 篇文獻",
            results=results,
            total_count=len(results)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文獻搜尋失敗: {str(e)}")



@router.get("/search/history")
async def get_search_history():
    """
    獲取搜尋歷史

    Returns:
        搜尋歷史記錄
    """
    # TODO: 實現搜尋歷史功能
    return {
        "history": [],
        "message": "搜尋歷史功能待實現"
    }

@router.delete("/search/clear-history")
async def clear_search_history():
    """
    清除搜尋歷史

    Returns:
        清除結果
    """
    # TODO: 實現清除搜尋歷史功能
    return {
        "message": "搜尋歷史已清除"
    }

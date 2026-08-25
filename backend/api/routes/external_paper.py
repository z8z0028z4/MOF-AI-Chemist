"""
外部論文搜尋 API 路由
=====================

提供 Europe PMC 學術論文的搜尋、下載和 API 驗證功能
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.config import DOWNLOADED_PAPER_DIR, relative_to_project

# 導入 Europe PMC 服務
from backend.services.europepmc_handler import (
    search_source,
    download_and_store,
    validate_europepmc_api,
    get_publication_info,
    search_by_doi
)

router = APIRouter(prefix="/external-paper", tags=["external-paper"])

# ==================== Pydantic Models ====================

class PaperSearchRequest(BaseModel):
    """論文搜尋請求模型"""
    keywords: List[str] = Field(..., description="搜尋關鍵字列表", min_length=1)
    limit: int = Field(default=10, ge=1, le=50, description="結果數量限制")


class PaperDownloadRequest(BaseModel):
    """論文下載請求模型"""
    pmcid: str = Field(..., description="PubMed Central ID")
    title: str = Field(..., description="論文標題")
    pdf_url: str = Field(..., description="PDF 下載連結")


class DOISearchRequest(BaseModel):
    """DOI 搜尋請求模型"""
    doi: str = Field(..., description="數字對象標識符")


class PaperResult(BaseModel):
    """論文搜尋結果模型"""
    title: str
    pdf_url: str
    doi: Optional[str] = None
    pmcid: str
    source: Optional[str] = None
    abstract: Optional[str] = None


class SearchResponse(BaseModel):
    """搜尋回應模型"""
    success: bool
    papers: List[PaperResult]
    total_count: int
    keywords: List[str]
    message: Optional[str] = None


class DownloadResponse(BaseModel):
    """下載回應模型"""
    success: bool
    file_path: Optional[str] = None
    storage_target: Optional[str] = None
    storage_directory: Optional[str] = None
    message: str


class ValidateResponse(BaseModel):
    """API 驗證回應模型"""
    available: bool
    message: str


# ==================== API Endpoints ====================

@router.post("/search", response_model=SearchResponse)
async def search_papers(request: PaperSearchRequest) -> SearchResponse:
    """
    搜尋 Europe PMC 論文

    Args:
        request: 包含關鍵字和數量限制的搜尋請求

    Returns:
        搜尋結果列表
    """
    try:
        # 呼叫 Europe PMC 搜尋服務
        results = search_source(
            keywords=request.keywords,
            limit=request.limit
        )

        # 轉換為 Pydantic 模型
        papers = [
            PaperResult(
                title=paper.get("title", ""),
                pdf_url=paper.get("pdf_url", ""),
                doi=paper.get("doi"),
                pmcid=paper.get("pmcid", ""),
                source=paper.get("source"),
                abstract=paper.get("abstract")
            )
            for paper in results
        ]

        return SearchResponse(
            success=True,
            papers=papers,
            total_count=len(papers),
            keywords=request.keywords,
            message=f"成功找到 {len(papers)} 篇相關論文"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"搜尋論文失敗: {str(e)}"
        )


@router.post("/download", response_model=DownloadResponse)
async def download_paper(request: PaperDownloadRequest) -> DownloadResponse:
    """
    下載論文 PDF 並儲存至本地

    Args:
        request: 包含 PMCID、標題和 PDF URL 的下載請求

    Returns:
        下載結果，包含本地儲存路徑
    """
    try:
        # 準備下載記錄
        record = {
            "pmcid": request.pmcid,
            "title": request.title,
            "pdf_url": request.pdf_url
        }

        storage_folder = DOWNLOADED_PAPER_DIR

        # Europe PMC 下載只保存 PDF，不放入 embedding inbox。
        file_path = download_and_store(record, storage_folder)

        if file_path:
            return DownloadResponse(
                success=True,
                file_path=file_path,
                storage_target="downloaded_papers",
                storage_directory=relative_to_project(storage_folder),
                message=f"論文已成功下載至 {file_path}"
            )
        else:
            return DownloadResponse(
                success=False,
                file_path=None,
                storage_target="downloaded_papers",
                storage_directory=relative_to_project(storage_folder),
                message="下載失敗，可能是 PDF 連結無效或無法訪問"
            )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"下載論文失敗: {str(e)}"
        )


@router.get("/validate", response_model=ValidateResponse)
async def validate_api() -> ValidateResponse:
    """
    驗證 Europe PMC API 連線狀態

    Returns:
        API 可用性狀態
    """
    try:
        is_available = validate_europepmc_api()

        if is_available:
            return ValidateResponse(
                available=True,
                message="Europe PMC API 連線正常"
            )
        else:
            return ValidateResponse(
                available=False,
                message="Europe PMC API 無法連線"
            )

    except Exception as e:
        return ValidateResponse(
            available=False,
            message=f"驗證失敗: {str(e)}"
        )


@router.post("/search-by-doi")
async def search_paper_by_doi(request: DOISearchRequest) -> Dict[str, Any]:
    """
    根據 DOI 搜尋論文

    Args:
        request: 包含 DOI 的搜尋請求

    Returns:
        論文資訊
    """
    try:
        result = search_by_doi(request.doi)

        if result:
            return {
                "success": True,
                "paper": result,
                "message": "成功找到論文"
            }
        else:
            return {
                "success": False,
                "paper": None,
                "message": "未找到對應的論文"
            }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"DOI 搜尋失敗: {str(e)}"
        )


@router.get("/publication-info/{pmcid}")
async def get_paper_info(pmcid: str) -> Dict[str, Any]:
    """
    獲取論文的詳細出版資訊

    Args:
        pmcid: PubMed Central ID

    Returns:
        論文出版資訊
    """
    try:
        info = get_publication_info(pmcid)

        if info:
            return {
                "success": True,
                "publication_info": info,
                "message": "成功獲取出版資訊"
            }
        else:
            return {
                "success": False,
                "publication_info": None,
                "message": "未找到出版資訊"
            }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"獲取出版資訊失敗: {str(e)}"
        )

"""
文獻管理 API 路由
================

處理文獻文件的瀏覽、搜尋和管理功能
"""

import os
import json
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query
from pathlib import Path

from backend.config import PAPER_DIR

router = APIRouter()

# 文獻文件目錄
PAPERS_DIR = PAPER_DIR

@router.get("/paper/list")
async def get_paper_list(
    search: Optional[str] = Query(None, description="搜尋關鍵字"),
    limit: int = Query(1000, description="結果數量限制")
) -> Dict[str, Any]:
    """
    獲取文獻文件列表

    Args:
        search: 搜尋關鍵字（可選）
        limit: 結果數量限制

    Returns:
        文獻文件列表和統計資訊
    """
    try:
        if not os.path.exists(PAPERS_DIR):
            return {
                "papers": [],
                "total_count": 0,
                "message": "文獻目錄不存在"
            }

        # 獲取所有 PDF 文件
        paper_files = []
        for filename in os.listdir(PAPERS_DIR):
            if filename.lower().endswith('.pdf'):
                file_path = os.path.join(PAPERS_DIR, filename)
                file_stat = os.stat(file_path)

                paper_info = {
                    "filename": filename,
                    "file_path": file_path,
                    "size": file_stat.st_size,
                    "modified_time": file_stat.st_mtime,
                    "paper_id": filename.replace('.pdf', '').replace('_PAPER', ''),
                    "display_name": filename.replace('_PAPER.pdf', ''),
                    "download_url": f"/api/v1/paper/download/{filename}",
                    "view_url": f"/api/v1/paper/view/{filename}"
                }

                # 如果有搜尋關鍵字，進行過濾
                if search:
                    search_lower = search.lower()
                    if (search_lower in filename.lower() or
                        search_lower in paper_info["display_name"].lower()):
                        paper_files.append(paper_info)
                else:
                    paper_files.append(paper_info)

        # 按文件名排序
        paper_files.sort(key=lambda x: x["filename"])

        # 應用限制
        if limit > 0:
            paper_files = paper_files[:limit]

        return {
            "papers": paper_files,
            "total_count": len(paper_files),
            "search_query": search,
            "directory": PAPERS_DIR
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取文獻列表失敗: {str(e)}")

@router.get("/paper/download/{filename}")
async def download_paper(filename: str):
    """
    下載文獻文件

    Args:
        filename: 文件名

    Returns:
        文件內容
    """
    try:
        file_path = os.path.join(PAPERS_DIR, filename)

        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="文件不存在")

        from fastapi.responses import FileResponse
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type='application/pdf'
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"下載文件失敗: {str(e)}")

@router.get("/paper/view/{filename}")
async def view_paper(filename: str):
    """
    查看文獻文件（在瀏覽器中顯示）

    Args:
        filename: 文件名

    Returns:
        文件內容
    """
    try:
        file_path = os.path.join(PAPERS_DIR, filename)

        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="文件不存在")

        from fastapi.responses import FileResponse
        return FileResponse(
            path=file_path,
            media_type='application/pdf',
            headers={"Content-Disposition": "inline"}
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查看文件失敗: {str(e)}")

@router.get("/paper/stats")
async def get_paper_stats() -> Dict[str, Any]:
    """
    獲取文獻統計資訊

    Returns:
        文獻統計資訊
    """
    try:
        if not os.path.exists(PAPERS_DIR):
            return {
                "total_papers": 0,
                "total_size": 0,
                "directory": PAPERS_DIR,
                "message": "文獻目錄不存在"
            }

        total_papers = 0
        total_size = 0

        for filename in os.listdir(PAPERS_DIR):
            if filename.lower().endswith('.pdf'):
                file_path = os.path.join(PAPERS_DIR, filename)
                file_stat = os.stat(file_path)
                total_papers += 1
                total_size += file_stat.st_size

        return {
            "total_papers": total_papers,
            "total_size": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "directory": PAPERS_DIR,
            "last_updated": "2025-09-19T17:30:00"  # 可以從文件系統獲取實際時間
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取文獻統計失敗: {str(e)}")

@router.get("/paper/search")
async def search_papers(
    query: str = Query(..., description="搜尋關鍵字"),
    limit: int = Query(50, description="結果數量限制")
) -> Dict[str, Any]:
    """
    搜尋文獻文件

    Args:
        query: 搜尋關鍵字
        limit: 結果數量限制

    Returns:
        搜尋結果
    """
    try:
        if not os.path.exists(PAPERS_DIR):
            return {
                "papers": [],
                "total_count": 0,
                "query": query,
                "message": "文獻目錄不存在"
            }

        # 獲取所有 PDF 文件
        paper_files = []
        query_lower = query.lower()

        for filename in os.listdir(PAPERS_DIR):
            if filename.lower().endswith('.pdf'):
                file_path = os.path.join(PAPERS_DIR, filename)
                file_stat = os.stat(file_path)

                # 檢查文件名是否包含搜尋關鍵字
                if query_lower in filename.lower():
                    paper_info = {
                        "filename": filename,
                        "file_path": file_path,
                        "size": file_stat.st_size,
                        "modified_time": file_stat.st_mtime,
                        "paper_id": filename.replace('.pdf', '').replace('_PAPER', ''),
                        "display_name": filename.replace('_PAPER.pdf', ''),
                        "download_url": f"/api/v1/paper/download/{filename}",
                        "view_url": f"/api/v1/paper/view/{filename}",
                        "match_score": filename.lower().count(query_lower)  # 簡單的匹配分數
                    }
                    paper_files.append(paper_info)

        # 按匹配分數排序
        paper_files.sort(key=lambda x: x["match_score"], reverse=True)

        # 應用限制
        if limit > 0:
            paper_files = paper_files[:limit]

        return {
            "papers": paper_files,
            "total_count": len(paper_files),
            "query": query,
            "directory": PAPERS_DIR
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜尋文獻失敗: {str(e)}")

"""
實驗數據 API 路由
================

處理實驗數據的查詢、分析和導出功能
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import sys
import os
import pandas as pd

# 添加原項目路徑到 sys.path
# sys.path.append(os.path.join(os.path.dirname(__file__), '../../../app'))  # 已重組，不再需要

from backend.config import EXPERIMENT_DIR
from backend.services.excel_service import export_new_experiments_to_txt
from backend.services.embedding_service import embed_experiment_txt_batch

router = APIRouter()

class ExperimentDataRequest(BaseModel):
    """實驗數據請求模型"""
    experiment_file: str
    include_metadata: bool = True
    include_embeddings: bool = False

class ExperimentDataResponse(BaseModel):
    """實驗數據響應模型"""
    file_name: str
    txt_paths: List[str]
    metadata: Dict[str, Any]
    embeddings: Optional[List[Dict[str, Any]]] = None
    total_experiments: int

class ExperimentAnalysisRequest(BaseModel):
    """實驗分析請求模型"""
    experiment_ids: List[str]
    analysis_type: str  # "summary", "trend", "correlation"

class ExperimentAnalysisResponse(BaseModel):
    """實驗分析響應模型"""
    analysis_type: str
    results: Dict[str, Any]
    insights: List[str]

@router.post("/experiment/process", response_model=ExperimentDataResponse)
async def process_experiment_data(request: ExperimentDataRequest):
    """
    處理實驗數據文件

    Args:
        request: 實驗數據處理請求

    Returns:
        處理結果和元數據
    """
    try:
        # 檢查文件是否存在
        file_path = os.path.join(EXPERIMENT_DIR, request.experiment_file)
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="實驗文件不存在")

        # 導出實驗數據為文本
        txt_paths = export_new_experiments_to_txt(file_path)

        # 獲取元數據
        metadata = {
            "file_name": request.experiment_file,
            "file_size": os.path.getsize(file_path),
            "txt_count": len(txt_paths),
            "created_time": os.path.getctime(file_path),
            "modified_time": os.path.getmtime(file_path)
        }

        # 如果需要嵌入向量
        embeddings = None
        if request.include_embeddings:
            embeddings = embed_experiment_txt_batch(txt_paths)

        return ExperimentDataResponse(
            file_name=request.experiment_file,
            txt_paths=txt_paths,
            metadata=metadata,
            embeddings=embeddings,
            total_experiments=len(txt_paths)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"實驗數據處理失敗: {str(e)}")

@router.get("/experiment/list")
async def list_experiment_files():
    """
    列出所有實驗數據文件

    Returns:
        實驗文件列表
    """
    try:
        if not os.path.exists(EXPERIMENT_DIR):
            return {"files": [], "total": 0}

        files = []
        for file in os.listdir(EXPERIMENT_DIR):
            if file.endswith(('.xlsx', '.xls')):
                file_path = os.path.join(EXPERIMENT_DIR, file)
                files.append({
                    "name": file,
                    "size": os.path.getsize(file_path),
                    "created": os.path.getctime(file_path),
                    "modified": os.path.getmtime(file_path)
                })

        return {
            "files": files,
            "total": len(files)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取實驗文件列表失敗: {str(e)}")

@router.post("/experiment/analyze", response_model=ExperimentAnalysisResponse)
async def analyze_experiment_data(request: ExperimentAnalysisRequest):
    """
    分析實驗數據

    Args:
        request: 實驗分析請求

    Returns:
        分析結果和洞察
    """
    try:
        # TODO: 實現實驗數據分析功能
        # 這裡可以添加統計分析、趨勢分析等

        if request.analysis_type == "summary":
            results = {
                "total_experiments": len(request.experiment_ids),
                "success_rate": 0.85,
                "average_duration": "2.5 hours"
            }
            insights = [
                "實驗成功率較高",
                "平均實驗時間適中",
                "建議優化實驗流程"
            ]
        elif request.analysis_type == "trend":
            results = {
                "trend_data": [],
                "period": "monthly"
            }
            insights = [
                "實驗數量呈上升趨勢",
                "成功率保持穩定"
            ]
        else:
            results = {}
            insights = []

        return ExperimentAnalysisResponse(
            analysis_type=request.analysis_type,
            results=results,
            insights=insights
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"實驗分析失敗: {str(e)}")

@router.get("/experiment/export/{file_name}")
async def export_experiment_data(file_name: str, format: str = "csv"):
    """
    導出實驗數據

    Args:
        file_name: 文件名
        format: 導出格式 (csv, json, excel)

    Returns:
        導出的數據文件
    """
    try:
        file_path = os.path.join(EXPERIMENT_DIR, file_name)
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="實驗文件不存在")

        # 讀取 Excel 文件
        df = pd.read_excel(file_path)

        # 根據格式導出
        if format == "csv":
            output_path = file_path.replace('.xlsx', '.csv')
            df.to_csv(output_path, index=False)
        elif format == "json":
            output_path = file_path.replace('.xlsx', '.json')
            df.to_json(output_path, orient='records', indent=2)
        else:
            raise HTTPException(status_code=400, detail="不支持的導出格式")

        return {
            "message": f"數據已導出為 {format} 格式",
            "output_file": os.path.basename(output_path)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"數據導出失敗: {str(e)}")

@router.get("/experiment/stats")
async def get_experiment_statistics():
    """
    獲取實驗統計信息

    Returns:
        實驗統計數據
    """
    try:
        if not os.path.exists(EXPERIMENT_DIR):
            return {
                "total_files": 0,
                "total_experiments": 0,
                "file_types": {},
                "recent_files": []
            }

        total_files = 0
        total_experiments = 0
        file_types = {}
        recent_files = []

        for file in os.listdir(EXPERIMENT_DIR):
            if file.endswith(('.xlsx', '.xls')):
                total_files += 1
                file_ext = os.path.splitext(file)[1]
                file_types[file_ext] = file_types.get(file_ext, 0) + 1

                file_path = os.path.join(EXPERIMENT_DIR, file)
                recent_files.append({
                    "name": file,
                    "modified": os.path.getmtime(file_path)
                })

        # 按修改時間排序
        recent_files.sort(key=lambda x: x["modified"], reverse=True)
        recent_files = recent_files[:5]  # 只返回最近5個文件

        return {
            "total_files": total_files,
            "total_experiments": total_experiments,
            "file_types": file_types,
            "recent_files": recent_files
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取統計信息失敗: {str(e)}")

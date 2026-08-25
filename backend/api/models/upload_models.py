"""
上傳相關的數據模型
==================

定義文件上傳、處理狀態等相關的 Pydantic 模型
"""

from pydantic import BaseModel
from typing import Dict, Any, Optional


class FileUploadResponse(BaseModel):
    """文件上傳響應模型"""
    success: bool
    message: str
    file_info: Dict[str, Any]
    processing_status: str


class ProcessingStatus(BaseModel):
    """處理狀態模型"""
    task_id: str
    status: str  # pending, processing, completed, failed
    progress: int
    message: str
    results: Optional[Dict[str, Any]] = None


class VectorStatsResponse(BaseModel):
    """向量統計響應模型"""
    paper_vectors: int
    experiment_vectors: int
    total_vectors: int


class FileInfo(BaseModel):
    """文件信息模型"""
    type: str  # mixed, papers, experiments, others
    papers: list[str]
    experiments: list[str]
    others: list[str]


class ProcessingResult(BaseModel):
    """處理結果模型"""
    paper_results: list[Dict[str, Any]]
    experiment_results: list[Dict[str, Any]]
    file_info: Dict[str, Any]
    vector_stats: Dict[str, int]
    processing_time: float

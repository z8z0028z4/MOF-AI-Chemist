"""
類型定義
========

定義系統中使用的各種類型
"""

from enum import Enum
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel


class DocumentType(str, Enum):
    """文檔類型枚舉"""
    PAPER = "paper"
    EXPERIMENT = "experiment"
    PROPOSAL = "proposal"
    CHEMICAL = "chemical"


class ProcessingStatus(str, Enum):
    """處理狀態枚舉"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ModelType(str, Enum):
    """模型類型枚舉"""
    GPT4 = "gpt-4"
    GPT5 = "gpt-5"
    GPT5_MINI = "gpt-5-mini"


class SearchResult(BaseModel):
    """搜索結果模型"""
    content: str
    metadata: Dict[str, Any]
    score: float


class ChemicalData(BaseModel):
    """化學品數據模型"""
    name: str
    formula: Optional[str] = None
    molecular_weight: Optional[str] = None
    cas_number: Optional[str] = None
    smiles: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None
    safety: Optional[Dict[str, Any]] = None


class MetadataRecord(BaseModel):
    """元數據記錄模型"""
    id: str
    title: str
    filename: str
    document_type: DocumentType
    created_at: str
    updated_at: str
    metadata: Dict[str, Any]

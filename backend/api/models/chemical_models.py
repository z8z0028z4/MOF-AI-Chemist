"""
化學品數據模型
============

定義化學品查詢、存儲相關的 Pydantic 模型
"""

from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from datetime import datetime


class ChemicalRequest(BaseModel):
    """化學品查詢請求模型"""
    chemical_name: str
    include_safety: bool = True
    include_properties: bool = True
    include_structure: bool = True
    save_to_database: bool = True


class ChemicalResponse(BaseModel):
    """化學品查詢響應模型"""
    name: str
    formula: Optional[str] = None
    molecular_weight: Optional[str] = None
    cas_number: Optional[str] = None
    smiles: Optional[str] = None
    boiling_point: Optional[str] = None
    melting_point: Optional[str] = None
    pubchem_url: Optional[str] = None
    image_url: Optional[str] = None
    svg_structure: Optional[str] = None
    png_structure: Optional[str] = None
    safety_data: Optional[Dict[str, Any]] = None
    properties: Optional[Dict[str, Any]] = None
    cid: Optional[int] = None
    error: Optional[str] = None
    saved_to_database: bool = False


class ChemicalBatchRequest(BaseModel):
    """批量化學品查詢請求模型"""
    chemical_names: List[str]
    include_safety: bool = True
    include_properties: bool = True
    include_structure: bool = True
    save_to_database: bool = True


class ChemicalBatchResponse(BaseModel):
    """批量化學品查詢響應模型"""
    results: List[ChemicalResponse]
    not_found: List[str]
    total_count: int
    success_count: int
    saved_count: int


class ChemicalDatabaseRecord(BaseModel):
    """化學品數據庫記錄模型"""
    id: Optional[int] = None
    name: str
    formula: Optional[str] = None
    molecular_weight: Optional[str] = None
    cas_number: Optional[str] = None
    smiles: Optional[str] = None
    boiling_point: Optional[str] = None
    melting_point: Optional[str] = None
    pubchem_url: Optional[str] = None
    image_url: Optional[str] = None
    svg_structure: Optional[str] = None
    png_structure: Optional[str] = None
    safety_data: Optional[Dict[str, Any]] = None
    properties: Optional[Dict[str, Any]] = None
    cid: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ChemicalSearchRequest(BaseModel):
    """化學品搜索請求模型"""
    query: str
    limit: int = 10
    include_structure: bool = True


class ChemicalSearchResponse(BaseModel):
    """化學品搜索響應模型"""
    results: List[ChemicalDatabaseRecord]
    total_count: int
    query: str

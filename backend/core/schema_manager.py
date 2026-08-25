"""
Schema 管理模組
============

負責管理和創建各種 JSON Schema，用於結構化輸出
"""

import os
import sys
import logging
from typing import Dict, Any, Optional

# 配置日誌
logger = logging.getLogger(__name__)

__all__ = [
    'get_dynamic_schema_params',
    'create_research_proposal_schema',
    'create_experimental_detail_schema',
    'create_revision_proposal_schema',
    'create_revision_experimental_detail_schema',
    'create_mof_extraction_schema',
    'get_schema_by_type'
]

def get_dynamic_schema_params() -> Dict[str, int]:
    """
    從設定管理器獲取動態的 JSON Schema 參數

    Returns:
        Dict[str, int]: schema 參數字典
    """
    try:
        backend_path = os.path.join(os.path.dirname(__file__), "..", "..", "backend")
        if backend_path not in sys.path:
            sys.path.insert(0, backend_path)

        try:
            from backend.core.settings_manager import settings_manager
        except ImportError:
            from core.settings_manager import settings_manager

        json_schema_params = settings_manager.get_json_schema_parameters()

        return {
            "min_length": json_schema_params.get("min_length", 5),
            "max_length": json_schema_params.get("max_length", 100)
        }
    except Exception as e:
        logger.warning(f"無法獲取動態 schema 參數，使用預設值: {e}")
        return {
            "min_length": 5,
            "max_length": 2000
        }

def create_research_proposal_schema() -> Dict[str, Any]:
    """
    創建研究提案的 JSON Schema

    Returns:
        Dict[str, Any]: 研究提案的 schema
    """
    schema_params = get_dynamic_schema_params()

    return {
        "type": "object",
        "title": "ResearchProposal",
        "additionalProperties": False,
        "required": [
            "proposal_title",
            "need",
            "solution",
            "differentiation",
            "benefit",
            "experimental_overview",
            "materials_list"
        ],
        "properties": {
            "proposal_title": {
                "type": "string",
                "description": "研究提案的標題，總結研究目標 and 創新點 (建議 10-100 字)"
            },
            "need": {
                "type": "string",
                "description": "研究需求背景，說明為什麼需要這個研究 (建議 50-2000 字)"
            },
            "solution": {
                "type": "string",
                "description": "解決方案概述，描述如何解決研究需求 (建議 50-2000 字)"
            },
            "differentiation": {
                "type": "string",
                "description": "創新點和差異化，說明與現有研究的區別 (建議 50-2000 字)"
            },
            "benefit": {
                "type": "string",
                "description": "預期效益，說明研究的潛在影響 and 價值 (建議 50-2000 字)"
            },
            "experimental_overview": {
                "type": "string",
                "description": "實驗概述，簡要描述實驗設計和方法 (建議 50-2000 字)"
            },
            "materials_list": {
                "type": "array",
                "description": (
                    "材料清單，最多 20 項。每一項只能是單一、可供 PubChem "
                    "查詢的完整化學品名稱；不得包含數量、步驟、說明文字、"
                    "更正紀錄、mof_metal_element 或 mof_linker_name metadata，"
                    "也不得重複列出同一化學品。"
                ),
                "items": {
                    "type": "string",
                    "description": "單一化學品完整名稱"
                }
            }
        }
    }

def create_experimental_detail_schema() -> Dict[str, Any]:
    """
    創建實驗詳情的 JSON Schema

    Returns:
        Dict[str, Any]: 實驗詳情的 schema
    """
    # Gemini 不支援 minLength/maxLength，移至 description

    return {
        "type": "object",
        "title": "ExperimentalDetail",
        "additionalProperties": False,
        "required": [
            "synthesis_process",
            "materials_and_conditions",
            "analytical_methods",
            "precautions"
        ],
        "properties": {
            "synthesis_process": {
                "type": "string",
                "description": "詳細的合成步驟、條件、時間等 (建議詳細描述)"
            },
            "materials_and_conditions": {
                "type": "string",
                "description": "使用的材料、濃度、溫度、壓力和其他反應條件 (建議詳細描述)"
            },
            "analytical_methods": {
                "type": "string",
                "description": "表徵技術，如 XRD、SEM、NMR 等 (建議詳細描述)"
            },
            "precautions": {
                "type": "string",
                "description": "實驗注意事項和安全預防措施 (建議詳細描述)"
            }
        }
    }



def create_revision_proposal_schema() -> Dict[str, Any]:
    """
    創建修訂提案的 JSON Schema

    Returns:
        Dict[str, Any]: 修訂提案的 schema
    """
    # Gemini 不支援 minLength/maxLength，移至 description

    return {
        "type": "object",
        "title": "RevisionProposal",
        "additionalProperties": False,
        "required": [
            "revision_explanation",
            "proposal_title",
            "need",
            "solution",
            "differentiation",
            "benefit",
            "experimental_overview",
            "materials_list"
        ],
        "properties": {
            "revision_explanation": {
                "type": "string",
                "description": "修訂邏輯和關鍵改進的簡要說明 (建議詳細說明)"
            },
            "proposal_title": {
                "type": "string",
                "description": "研究提案標題 (建議 10-100 字)"
            },
            "need": {
                "type": "string",
                "description": "研究需求背景和當前限制 (建議 50-2000 字)"
            },
            "solution": {
                "type": "string",
                "description": "建議的設計和開發策略 (建議 50-2000 字)"
            },
            "differentiation": {
                "type": "string",
                "description": "與現有技術的比較 (建議 50-2000 字)"
            },
            "benefit": {
                "type": "string",
                "description": "預期改進和效益 (建議 50-2000 字)"
            },
            "experimental_overview": {
                "type": "string",
                "description": "實驗方法和方法論 (建議 50-2000 字)"
            },
            "materials_list": {
                "type": "array",
                "description": (
                    "材料清單，最多 20 項。每一項只能是單一、可供 PubChem "
                    "查詢的完整化學品名稱；不得包含說明文字、metadata 或重複項。"
                ),
                "items": {
                    "type": "string",
                    "description": "單一化學品完整名稱"
                }
            }
        }
    }

def create_revision_experimental_detail_schema() -> Dict[str, Any]:
    """
    創建修訂實驗細節的 JSON Schema

    Returns:
        Dict[str, Any]: 修訂實驗細節的 schema
    """
    # Gemini 不支援 minLength/maxLength，移至 description

    return {
        "type": "object",
        "title": "RevisionExperimentalDetail",
        "additionalProperties": False,
        "required": [
            "revision_explanation",
            "synthesis_process",
            "materials_and_conditions",
            "analytical_methods",
            "precautions"
        ],
        "properties": {
            "revision_explanation": {
                "type": "string",
                "description": "修訂邏輯和關鍵改進的簡要說明，基於用戶反饋 (建議詳細說明)"
            },
            "synthesis_process": {
                "type": "string",
                "description": "詳細的合成步驟、條件、時間等，包含修改後的內容 (建議詳細描述)"
            },
            "materials_and_conditions": {
                "type": "string",
                "description": "使用的材料、濃度、溫度、壓力和其他反應條件，包含修改後的內容 (建議詳細描述)"
            },
            "analytical_methods": {
                "type": "string",
                "description": "表徵技術，如 XRD、SEM、NMR 等，包含修改後的內容 (建議詳細描述)"
            },
            "precautions": {
                "type": "string",
                "description": "實驗注意事項和安全預防措施，包含修改後的內容 (建議詳細描述)"
            }
        }
    }

def get_schema_by_type(schema_type: str) -> Optional[Dict[str, Any]]:
    """
    根據類型獲取對應的 schema

    Args:
        schema_type: schema 類型

    Returns:
        Dict[str, Any]: 對應的 schema，如果不存在則返回 None
    """
    schema_functions = {
        "research_proposal": create_research_proposal_schema,
        "experimental_detail": create_experimental_detail_schema,
        "revision_proposal": create_revision_proposal_schema,
        "revision_experimental_detail": create_revision_experimental_detail_schema,
        "mof_extraction": create_mof_extraction_schema
    }

    if schema_type not in schema_functions:
        logger.warning(f"未知的 schema 類型: {schema_type}")
        return None

    try:
        return schema_functions[schema_type]()
    except Exception as e:
        logger.error(f"創建 schema 失敗 {schema_type}: {e}")
        return None


def create_mof_extraction_schema() -> Dict[str, Any]:
    """
    創建從提案中提取 MOF 金屬與配體資訊的 JSON Schema (供第二階段 AI 使用)
    """
    return {
        "type": "object",
        "title": "MofExtraction",
        "additionalProperties": False,
        "required": [
            "is_mof_related",
            "mof_metal_element",
            "mof_linker_name",
            "mof_linker_name_2"
        ],
        "properties": {
            "is_mof_related": {
                "type": "boolean",
                "description": "這篇提案是否與 MOF（金屬有機框架）材料的設計、合成、開發或改進相關？若是則為 true，若完全無關（如純多孔碳、純沸石、或是其他無機材料）則為 false。"
            },
            "mof_metal_element": {
                "type": "string",
                "description": "從提案內容中精確提取出被設計或合成的 MOF 所使用的主要金屬元素符號，如 Cu, Zn, Zr, Fe, Co, Ni, Cr, Al 等。若非 MOF 或無金屬則為空字串。"
            },
            "mof_linker_name": {
                "type": "string",
                "description": "從提案中精確提取出的主要有機配體（Linker）的完整化學名稱（例如 2-aminoterephthalic acid、benzene-1,3,5-tricarboxylic acid 等，必須與提案中使用的學名一致，且不要是 abbreviation/SMILES）。若無則為空字串。"
            },
            "mof_linker_name_2": {
                "type": "string",
                "description": "從提案中提取出的第二個輔助配體（如 oxalic acid 等，若存在於提案中）的化學名稱。若無則為空字串。"
            }
        }
    }

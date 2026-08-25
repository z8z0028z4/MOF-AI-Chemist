"""
模式管理器模組
============

負責管理知識代理的不同處理模式，包括：
1. 模式定義和驗證
2. 模式描述和文檔
3. 模式配置管理
"""

import logging
from typing import Dict, List, Optional

# 配置日誌
logger = logging.getLogger(__name__)

# 定義所有可用的處理模式
AVAILABLE_MODES = {
    "納入實驗資料，進行推論與建議": {
        "description": "整合文獻和實驗數據進行綜合推論",
        "category": "advanced",
        "requires_experiment_data": True,
        "allows_inference": True,
        "structured_output": False
    },
    "make proposal": {
        "description": "生成研究提案",
        "category": "proposal",
        "requires_experiment_data": False,
        "allows_inference": True,
        "structured_output": True
    },
    "允許延伸與推論": {
        "description": "基於文獻進行智能推論",
        "category": "inference",
        "requires_experiment_data": False,
        "allows_inference": True,
        "structured_output": False
    },
    "僅嚴謹文獻溯源": {
        "description": "嚴格基於文獻回答，無推論",
        "category": "strict",
        "requires_experiment_data": False,
        "allows_inference": False,
        "structured_output": False
    },
    "expand to experiment detail": {
        "description": "擴展實驗細節設計",
        "category": "experiment",
        "requires_experiment_data": False,
        "allows_inference": True,
        "structured_output": True
    },
    "generate new idea": {
        "description": "生成新的研究想法",
        "category": "innovation",
        "requires_experiment_data": False,
        "allows_inference": True,
        "structured_output": True
    }
}


def get_available_modes() -> List[str]:
    """
    獲取所有可用的處理模式

    Returns:
        List[str]: 可用模式列表
    """
    return list(AVAILABLE_MODES.keys())


def validate_mode(mode: str) -> bool:
    """
    驗證模式是否有效

    Args:
        mode (str): 要驗證的模式

    Returns:
        bool: 模式是否有效
    """
    return mode in AVAILABLE_MODES


def get_mode_description(mode: str) -> str:
    """
    獲取模式的詳細描述

    Args:
        mode (str): 模式名稱

    Returns:
        str: 模式描述
    """
    if not validate_mode(mode):
        logger.warning(f"未知模式: {mode}")
        return "未知模式"

    return AVAILABLE_MODES[mode]["description"]


def get_mode_config(mode: str) -> Optional[Dict]:
    """
    獲取模式的完整配置信息

    Args:
        mode (str): 模式名稱

    Returns:
        Optional[Dict]: 模式配置字典，如果模式不存在則返回 None
    """
    return AVAILABLE_MODES.get(mode)


def get_modes_by_category(category: str) -> List[str]:
    """
    根據類別獲取模式列表

    Args:
        category (str): 模式類別

    Returns:
        List[str]: 該類別下的模式列表
    """
    return [
        mode for mode, config in AVAILABLE_MODES.items()
        if config["category"] == category
    ]


def is_structured_output_mode(mode: str) -> bool:
    """
    檢查是否為結構化輸出模式

    Args:
        mode (str): 模式名稱

    Returns:
        bool: 是否為結構化輸出模式
    """
    config = get_mode_config(mode)
    return config.get("structured_output", False) if config else False


def requires_experiment_data(mode: str) -> bool:
    """
    檢查模式是否需要實驗數據

    Args:
        mode (str): 模式名稱

    Returns:
        bool: 是否需要實驗數據
    """
    config = get_mode_config(mode)
    return config.get("requires_experiment_data", False) if config else False


def allows_inference(mode: str) -> bool:
    """
    檢查模式是否允許推論

    Args:
        mode (str): 模式名稱

    Returns:
        bool: 是否允許推論
    """
    config = get_mode_config(mode)
    return config.get("allows_inference", False) if config else False


def get_mode_summary() -> Dict[str, List[str]]:
    """
    獲取按類別分組的模式摘要

    Returns:
        Dict[str, List[str]]: 按類別分組的模式字典
    """
    summary = {}
    for mode, config in AVAILABLE_MODES.items():
        category = config["category"]
        if category not in summary:
            summary[category] = []
        summary[category].append(mode)

    return summary

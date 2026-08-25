"""
格式轉換模組
==========

負責將結構化數據轉換為文本格式
"""

import json
from typing import Dict, Any

from backend.utils.logger import get_logger

logger = get_logger(__name__)


def structured_proposal_to_text(proposal_data: Dict[str, Any]) -> str:
    """
    將結構化提案轉換為傳統文本格式

    Args:
        proposal_data: 結構化提案數據

    Returns:
        str: 格式化的文本提案
    """
    if not proposal_data:
        return ""

    text_parts = []

    # 標題
    if proposal_data.get('proposal_title'):
        text_parts.append(f"Proposal: {proposal_data['proposal_title']}\n")

    # Need
    if proposal_data.get('need'):
        text_parts.append("Need:\n")
        text_parts.append(f"{proposal_data['need']}\n")

    # Solution
    if proposal_data.get('solution'):
        text_parts.append("Solution:\n")
        text_parts.append(f"{proposal_data['solution']}\n")

    # Differentiation
    if proposal_data.get('differentiation'):
        text_parts.append("Differentiation:\n")
        text_parts.append(f"{proposal_data['differentiation']}\n")

    # Benefit
    if proposal_data.get('benefit'):
        text_parts.append("Benefit:\n")
        text_parts.append(f"{proposal_data['benefit']}\n")

    # Experimental overview
    if proposal_data.get('experimental_overview'):
        text_parts.append("Experimental overview:\n")
        text_parts.append(f"{proposal_data['experimental_overview']}\n")

    # Materials list
    if proposal_data.get('materials_list'):
        materials_json = json.dumps(proposal_data['materials_list'], ensure_ascii=False, indent=2)
        text_parts.append(f"```json\n{materials_json}\n```\n")

    return "\n".join(text_parts)


def structured_experimental_detail_to_text(experimental_data: Dict[str, Any]) -> str:
    """
    將結構化實驗細節轉換為傳統文本格式

    Args:
        experimental_data: 結構化實驗細節數據

    Returns:
        str: 格式化的文本實驗細節
    """
    if not experimental_data:
        return ""

    text_parts = []

    # Synthesis Process
    if experimental_data.get('synthesis_process'):
        text_parts.append("## Synthesis Process")
        text_parts.append(f"{experimental_data['synthesis_process']}\n")

    # Materials and Conditions
    if experimental_data.get('materials_and_conditions'):
        text_parts.append("## Materials and Conditions")
        text_parts.append(f"{experimental_data['materials_and_conditions']}\n")

    # Analytical Methods
    if experimental_data.get('analytical_methods'):
        text_parts.append("## Analytical Methods")
        text_parts.append(f"{experimental_data['analytical_methods']}\n")

    # Precautions
    if experimental_data.get('precautions'):
        text_parts.append("## Precautions")
        text_parts.append(f"{experimental_data['precautions']}\n")

    return "\n".join(text_parts)


def structured_revision_proposal_to_text(revision_data: Dict[str, Any]) -> str:
    """
    將結構化修訂提案轉換為傳統文本格式

    Args:
        revision_data: 結構化修訂提案數據 (包含修訂說明)

    Returns:
        str: 格式化的文本提案
    """
    if not revision_data:
        return ""

    text_parts = []

    # 修訂說明
    if revision_data.get('revision_explanation'):
        text_parts.append("Revision Explanation:")
        text_parts.append(f"{revision_data['revision_explanation']}\n")

    # 標題
    if revision_data.get('proposal_title'):
        text_parts.append(f"Proposal: {revision_data['proposal_title']}\n")

    # Need
    if revision_data.get('need'):
        text_parts.append("Need:\n")
        text_parts.append(f"{revision_data['need']}\n")

    # Solution
    if revision_data.get('solution'):
        text_parts.append("Solution:\n")
        text_parts.append(f"{revision_data['solution']}\n")

    # Differentiation
    if revision_data.get('differentiation'):
        text_parts.append("Differentiation:\n")
        text_parts.append(f"{revision_data['differentiation']}\n")

    # Benefit
    if revision_data.get('benefit'):
        text_parts.append("Benefit:\n")
        text_parts.append(f"{revision_data['benefit']}\n")

    # Experimental Overview
    if revision_data.get('experimental_overview'):
        text_parts.append("Experimental Overview:\n")
        text_parts.append(f"{revision_data['experimental_overview']}\n")

    # Materials list
    if revision_data.get('materials_list'):
        materials_json = json.dumps(revision_data['materials_list'], ensure_ascii=False, indent=2)
        text_parts.append(f"```json\n{materials_json}\n```\n")

    return "\n".join(text_parts)


def structured_revision_experimental_detail_to_text(revision_data: Dict[str, Any]) -> str:
    """
    將結構化修訂實驗細節轉換為傳統文本格式

    Args:
        revision_data: 結構化修訂實驗細節數據 (包含修訂說明)

    Returns:
        str: 格式化的文本實驗細節
    """
    if not revision_data:
        return ""

    text_parts = []

    # 修訂說明
    if revision_data.get('revision_explanation'):
        text_parts.append("Revision Explanation:")
        text_parts.append(f"{revision_data['revision_explanation']}\n")

    # Synthesis Process
    if revision_data.get('synthesis_process'):
        text_parts.append("SYNTHESIS PROCESS:")
        text_parts.append(f"{revision_data['synthesis_process']}\n")

    # Materials and Conditions
    if revision_data.get('materials_and_conditions'):
        text_parts.append("MATERIALS AND CONDITIONS:")
        text_parts.append(f"{revision_data['materials_and_conditions']}\n")

    # Analytical Methods
    if revision_data.get('analytical_methods'):
        text_parts.append("ANALYTICAL METHODS:")
        text_parts.append(f"{revision_data['analytical_methods']}\n")

    # Precautions
    if revision_data.get('precautions'):
        text_parts.append("PRECAUTIONS:")
        text_parts.append(f"{revision_data['precautions']}\n")

    return "\n".join(text_parts)

__all__ = [
    'structured_proposal_to_text',
    'structured_experimental_detail_to_text',
    'structured_revision_proposal_to_text',
    'structured_revision_experimental_detail_to_text'
]

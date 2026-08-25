"""
查詢擴展模組
==========

負責將用戶的自然語言查詢擴展為多個語義搜索查詢
"""

from typing import List
import json

from backend.utils.logger import get_logger
# 移除模組級別的導入，避免循環依賴
# from backend.services.model_service import get_current_model, get_model_params

logger = get_logger(__name__)


def expand_query(user_prompt: str) -> List[str]:
    """
    將用戶輸入的自然語言問題轉換為多個語義搜索查詢語句。
    返回的英文語句可用於文獻向量檢索。

    Args:
        user_prompt: 用戶輸入的查詢

    Returns:
        List[str]: 擴展後的查詢列表
    """
    # 延遲導入避免循環依賴
    from backend.services.model_service import get_current_model, get_model_params

    # 獲取動態模型參數
    try:
        current_model = get_current_model()
        llm_params = get_model_params()
    except Exception as e:
        logger.error(f"❌ 無法獲取模型參數：{e}")
        raise Exception(f"無法獲取模型參數：{str(e)}")

    system_prompt = """You are a scientific assistant helping expand a user's synthesis question into multiple semantic search queries.
    Each query should be precise, relevant, and useful for retrieving related technical documents.
    Only return a list of 3 to 6 search queries in English. Do not explain, do not include numbering if not needed."""

    full_prompt = f"{system_prompt}\n\nUser question:\n{user_prompt}"

    # Remove dynamic imports causing issues and use unified generation
    from backend.core.generation import call_llm

    # 獲取動態模型參數
    try:
        current_model = get_current_model()
        llm_params = get_model_params()
    except Exception as e:
        logger.error(f"❌ 無法獲取模型參數：{e}")
        raise Exception(f"無法獲取模型參數：{str(e)}")

    system_prompt = """You are a scientific assistant helping expand a user's synthesis question into multiple semantic search queries.
    Each query should be precise, relevant, and useful for retrieving related technical documents.
    Only return a list of 3 to 6 search queries in English. Do not explain, do not include numbering if not needed."""

    full_prompt = f"{system_prompt}\n\nUser question:\n{user_prompt}"

    try:
        # Use unified generation function which supports both OpenAI and Gemini
        output = call_llm(full_prompt, model=current_model)
        output = output.strip()

        # 解析查詢列表
        queries = [line.strip("-• ").strip() for line in output.split("\n") if line.strip()]
        return [q for q in queries if len(q) > 4]

    except Exception as e:
        logger.error(f"❌ 查詢擴展失敗：{e}")
        raise Exception(f"查詢擴展失敗：{str(e)}")


def expand_query_with_fallback(user_prompt: str) -> List[str]:
    """
    查詢擴展功能（已移除 fallback）

    Args:
        user_prompt: 用戶輸入的查詢

    Returns:
        List[str]: 擴展後的查詢列表
    """
    return expand_query(user_prompt)

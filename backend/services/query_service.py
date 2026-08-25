"""
AI 研究助理 - 查詢解析器模塊
==========================

這個模塊負責解析和優化用戶的查詢，提取關鍵詞用於搜索。
主要功能包括：
1. 智能關鍵詞提取
2. 多語言查詢處理
3. 科學術語識別
4. 查詢優化和標準化

架構說明：
- 使用OpenAI GPT模型進行智能關鍵詞提取
- 支持中英文混合查詢
- 專注於科學文獻相關的關鍵詞識別
- 提供標準化的查詢處理流程
"""

from typing import List, Literal, Dict, Optional
import re
from openai import OpenAI
import os
# 直接定義配置變量，避免循環導入
LLM_MODEL_NAME = "gpt-5o-mini"
import ast

# ==================== OpenAI客戶端初始化 ====================
# 創建OpenAI API客戶端，用於調用GPT模型進行關鍵詞提取
# 使用環境變量中的API密鑰確保安全性
# 延遲初始化以避免在環境變量未載入時失敗
client = None

def get_openai_client():
    """獲取 OpenAI 客戶端，延遲初始化"""
    global client
    if client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key and api_key != "sk-dummy-key-placeholder":
            client = OpenAI(api_key=api_key)
        else:
            raise ValueError("OpenAI API Key 未配置或為 dummy key")
    return client

def extract_keywords(question: str) -> List[str]:
    """
    從用戶查詢中提取科學關鍵詞

    功能：
    1. 分析用戶的查詢內容
    2. 識別科學術語和材料名稱
    3. 將非英文查詢翻譯為英文關鍵詞
    4. 返回標準化的關鍵詞列表

    參數：
        question (str): 用戶的查詢問題，支持中英文

    返回：
        List[str]: 提取的英文關鍵詞列表

    示例：
        >>> keywords = extract_keywords("如何進行二氧化碳捕獲？")
        >>> print(keywords)  # ['carbon dioxide capture', 'CO2', 'direct air capture']
    """

    # ==================== 提示詞設計 ====================
    # 設計專門的提示詞，指導GPT模型提取科學關鍵詞
    # 強調只返回可能在科學論文摘要中出現的英文關鍵詞
    prompt = f"""
    You are an expert scientific assistant.
    Extract only the most relevant **English** scientific keywords or material names from the following research question.

    - Only return keywords or entities that are likely to appear in scientific English papers' abstract.
    - If the input is in another language (e.g., Chinese), translate the scientific terms and return **only English keywords**.
    - Do not return explanations or extra formatting.

    Return the result as a valid Python list of quoted strings.
    Example: ["direct air capture", "CO2", "MOFs"]

    Question: "{question}"
    """

    # ==================== GPT模型調用 ====================
    # 使用OpenAI GPT模型進行關鍵詞提取
    # 使用動態模型參數
    try:
        from model_config_bridge import get_model_params
        llm_params = get_model_params()

        response = get_openai_client().chat.completions.create(
            model=llm_params["model"],
            messages=[{"role": "user", "content": prompt}],
            max_tokens=llm_params.get("max_tokens", 4000),
            timeout=llm_params.get("timeout", 120),
        )

        # 獲取模型返回的原始文本
        raw = response.choices[0].message.content.strip()
        print("🧠 GPT模型原始返回：", raw)

    except Exception as e:
        print(f"❌ GPT模型調用失敗：{e}")
        return []

    # ==================== 結果解析 ====================
    # 使用正則表達式提取Python列表格式的結果
    # 然後使用ast.literal_eval安全地解析列表
    try:
        # 使用正則表達式匹配第一個類似list的[]片段
        # re.DOTALL 允許.匹配換行符
        match = re.search(r'\[.*\]', raw, re.DOTALL)

        if match:
            # 使用ast.literal_eval安全地解析字符串為Python列表
            # 這比eval()更安全，只允許字面量表達式
            keywords = ast.literal_eval(match.group(0))

            # 驗證結果是否為字符串列表
            if isinstance(keywords, list) and all(isinstance(k, str) for k in keywords):
                print(f"✅ 成功提取 {len(keywords)} 個關鍵詞：{keywords}")
                return keywords
            else:
                print("⚠️ 解析結果格式不正確")
                return []
        else:
            print("⚠️ 沒有檢測到合法的Python列表格式")
            return []

    except Exception as e:
        print(f"❌ 關鍵詞解析失敗：{e}")
        return []


def parse_query_intent(query: str) -> Dict[str, any]:
    """
    解析查詢意圖和類型

    功能：
    1. 識別查詢的類型（搜索、分析、比較等）
    2. 提取查詢的意圖和目標
    3. 識別查詢中的實體和關係

    參數：
        query (str): 用戶查詢

    返回：
        Dict[str, any]: 包含查詢意圖信息的字典
    """
    prompt = f"""
    Analyze the following research query and extract its intent and components.

    Return a JSON object with the following structure:
    {{
        "intent": "search|analyze|compare|synthesize",
        "entities": ["entity1", "entity2"],
        "relationships": ["relationship1"],
        "domain": "chemistry|biology|physics|materials",
        "complexity": "simple|moderate|complex"
    }}

    Query: "{query}"
    """

    try:
        from model_config_bridge import get_model_params
        llm_params = get_model_params()

        response = get_openai_client().chat.completions.create(
            model=llm_params["model"],
            messages=[{"role": "user", "content": prompt}],
            max_tokens=llm_params.get("max_tokens", 4000),
            timeout=llm_params.get("timeout", 120),
        )

        # 解析JSON結果
        import json
        result = json.loads(response.choices[0].message.content.strip())
        return result

    except Exception as e:
        print(f"❌ 查詢意圖解析失敗：{e}")
        return {
            "intent": "search",
            "entities": [],
            "relationships": [],
            "domain": "general",
            "complexity": "simple"
        }


def optimize_search_query(original_query: str, context: List[str] = None) -> str:
    """
    優化搜索查詢以提高搜索效果

    功能：
    1. 基於原始查詢生成更精確的搜索詞
    2. 考慮上下文信息進行查詢優化
    3. 添加相關的科學術語和同義詞

    參數：
        original_query (str): 原始查詢
        context (List[str]): 相關的上下文信息

    返回：
        str: 優化後的查詢字符串
    """
    context_text = ""
    if context:
        context_text = f"\nContext: {', '.join(context)}"

    prompt = f"""
    Optimize the following research query for better search results.

    Original query: "{original_query}"{context_text}

    Return only the optimized query string, no explanations.
    """

    try:
        from model_config_bridge import get_model_params
        llm_params = get_model_params()

        response = get_openai_client().chat.completions.create(
            model=llm_params["model"],
            messages=[{"role": "user", "content": prompt}],
            max_tokens=llm_params.get("max_tokens", 4000),
            timeout=llm_params.get("timeout", 120),
        )

        optimized_query = response.choices[0].message.content.strip()
        print(f"🔍 查詢優化：'{original_query}' → '{optimized_query}'")
        return optimized_query

    except Exception as e:
        print(f"❌ 查詢優化失敗：{e}")
        return original_query


def extract_chemical_entities(query: str) -> List[str]:
    """
    從查詢中提取化學實體（化合物、材料等）

    功能：
    1. 識別化學品名稱
    2. 識別材料名稱
    3. 識別化學反應類型
    4. 識別實驗方法

    參數：
        query (str): 用戶查詢

    返回：
        List[str]: 化學實體列表
    """
    prompt = f"""
    Extract chemical entities from the following query.
    Focus on:
    - Chemical compounds and materials
    - Reaction types
    - Experimental methods
    - Physical properties

    Return as a Python list of strings.

    Query: "{query}"
    """

    try:
        from model_config_bridge import get_model_params
        llm_params = get_model_params()

        response = get_openai_client().chat.completions.create(
            model=llm_params["model"],
            messages=[{"role": "user", "content": prompt}],
            max_tokens=llm_params.get("max_tokens", 4000),
            timeout=llm_params.get("timeout", 120),
        )

        raw = response.choices[0].message.content.strip()
        match = re.search(r'\[.*\]', raw, re.DOTALL)

        if match:
            entities = ast.literal_eval(match.group(0))
            print(f"🧪 提取化學實體：{entities}")
            return entities
        else:
            return []

    except Exception as e:
        print(f"❌ 化學實體提取失敗：{e}")
        return []


# ==================== 輔助函數 ====================
def validate_query(query: str) -> bool:
    """
    驗證查詢是否有效

    參數：
        query (str): 用戶查詢

    返回：
        bool: 查詢是否有效
    """
    if not query or not query.strip():
        return False

    # 檢查查詢長度
    if len(query.strip()) < 2:
        return False

    # 檢查是否包含有效字符
    if not re.search(r'[a-zA-Z\u4e00-\u9fff]', query):
        return False

    return True


def clean_query(query: str) -> str:
    """
    清理和標準化查詢

    參數：
        query (str): 原始查詢

    返回：
        str: 清理後的查詢
    """
    # 移除多餘的空白字符
    cleaned = re.sub(r'\s+', ' ', query.strip())

    # 移除特殊字符（保留中文、英文、數字和基本標點）
    cleaned = re.sub(r'[^\w\s\u4e00-\u9fff.,?!;:()\[\]{}]', '', cleaned)

    return cleaned

"""
LLM 管理模組
=========

負責管理大語言模型的配置、初始化和調用
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from langchain_openai import ChatOpenAI
# 移除模組級別的openai導入，改為延遲導入
# import openai

from .config import settings

# 為了向後兼容，定義舊的變量名
OPENAI_API_KEY = settings.openai_api_key
LLM_PARAMS = {
    "model": settings.openai_model,
    "max_tokens": settings.openai_max_tokens,
    "timeout": 120
}
from ..utils import safe_json_loads
from ..utils.exceptions import LLMError, APIKeyError

# 配置日誌
logger = logging.getLogger(__name__)

# 設定OpenAI API Key - 延遲設置
# if OPENAI_API_KEY:
#     openai.api_key = OPENAI_API_KEY
# else:
#     logger.warning("未設置 OPENAI_API_KEY")

class LLMManager:
    """LLM 管理器類別"""

    def __init__(self, model_name: Optional[str] = None):
        """
        初始化 LLM 管理器

        Args:
            model_name: 模型名稱，如果為 None 則使用配置中的默認模型
        """
        self.model_name = model_name or LLM_PARAMS.get("model", "gpt-5-mini")
        self.llm = None
        self._initialize_llm()

    def _initialize_llm(self) -> None:
        """初始化 LLM 實例"""
        try:
            if not OPENAI_API_KEY:
                raise APIKeyError("OpenAI")

            # 對於 GPT-5-mini 模型，不設置 temperature 參數，使用默認值
            llm_kwargs = {
                "model": self.model_name,
                "max_tokens": LLM_PARAMS.get("max_tokens", 4000),
                "timeout": LLM_PARAMS.get("timeout", 120)
            }

            # 只有非 GPT-5-mini 模型才設置 temperature
            if not self.model_name.startswith("gpt-5-mini"):
                llm_kwargs["temperature"] = 0.1

            self.llm = ChatOpenAI(**llm_kwargs)
            logger.info(f"LLM 初始化成功: {self.model_name}")

        except Exception as e:
            logger.error(f"LLM 初始化失敗: {e}")
            raise LLMError(f"初始化失敗: {e}", model_name=self.model_name)

    def generate_response(
        self,
        prompt: str,
        system_message: Optional[str] = None
    ) -> str:
        """
        生成 LLM 回應

        Args:
            prompt: 用戶提示
            system_message: 系統消息

        Returns:
            str: LLM 回應
        """
        try:
            if not self.llm:
                raise LLMError("LLM 未初始化")

            messages = []
            if system_message:
                messages.append({"role": "system", "content": system_message})
            messages.append({"role": "user", "content": prompt})

            response = self.llm.invoke(messages)
            return response.content

        except Exception as e:
            logger.error(f"LLM 回應生成失敗: {e}")
            raise LLMError(f"回應生成失敗: {e}", model_name=self.model_name)

    def generate_structured_response(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        生成結構化回應

        Args:
            prompt: 用戶提示
            schema: JSON Schema
            system_message: 系統消息

        Returns:
            Dict[str, Any]: 結構化回應
        """
        try:
            # 構建結構化提示
            structured_prompt = self._build_structured_prompt(prompt, schema)

            # 生成回應
            response_text = self.generate_response(
                structured_prompt,
                system_message=system_message
            )

            # 解析 JSON 回應
            return self._parse_json_response(response_text)

        except Exception as e:
            logger.error(f"結構化回應生成失敗: {e}")
            raise LLMError(f"結構化回應失敗: {e}", model_name=self.model_name)

    def _build_structured_prompt(self, prompt: str, schema: Dict[str, Any]) -> str:
        """
        構建結構化提示

        Args:
            prompt: 原始提示
            schema: JSON Schema

        Returns:
            str: 結構化提示
        """
        schema_str = json.dumps(schema, ensure_ascii=False, indent=2)

        structured_prompt = f"""
請根據以下提示生成回應，並以指定的 JSON 格式返回：

提示：{prompt}

請嚴格按照以下 JSON Schema 格式回應，不要添加任何額外的文字或說明：

{schema_str}

回應：
"""
        return structured_prompt

    def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """
        解析 JSON 回應

        Args:
            response_text: LLM 回應文本

        Returns:
            Dict[str, Any]: 解析後的 JSON 對象
        """
        try:
            # 嘗試直接解析
            return json.loads(response_text)
        except json.JSONDecodeError:
            # 嘗試提取 JSON 部分
            try:
                # 尋找 JSON 開始和結束的位置
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1

                if start_idx != -1 and end_idx != 0:
                    json_str = response_text[start_idx:end_idx]
                    return json.loads(json_str)
                else:
                    raise ValueError("未找到有效的 JSON 格式")

            except Exception as e:
                logger.error(f"JSON 解析失敗: {e}")
                logger.error(f"原始回應: {response_text}")
                raise LLMError(f"JSON 解析失敗: {e}")

    def validate_response(self, response: Dict[str, Any], schema: Dict[str, Any]) -> bool:
        """
        驗證回應是否符合 Schema

        Args:
            response: LLM 回應
            schema: JSON Schema

        Returns:
            bool: 是否符合 Schema
        """
        try:
            # 簡單的驗證：檢查必需字段
            required_fields = schema.get("required", [])
            for field in required_fields:
                if field not in response or response[field] is None:
                    logger.warning(f"缺少必需字段: {field}")
                    return False

            logger.info("回應驗證通過")
            return True

        except Exception as e:
            logger.error(f"回應驗證失敗: {e}")
            return False

def create_llm_manager(model_name: Optional[str] = None) -> LLMManager:
    """
    創建 LLM 管理器實例

    Args:
        model_name: 模型名稱

    Returns:
        LLMManager: LLM 管理器實例
    """
    return LLMManager(model_name)

def get_default_llm_manager() -> LLMManager:
    """
    獲取默認的 LLM 管理器

    Returns:
        LLMManager: 默認的 LLM 管理器實例
    """
    return LLMManager()

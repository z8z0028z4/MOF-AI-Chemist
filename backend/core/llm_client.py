"""
LLM 客戶端模組
==============

負責 LLM 調用的核心功能，避免循環導入問題
"""

import time
import json
from typing import Dict, Any, Optional, List
from openai import OpenAI

from backend.utils.logger import get_logger
from backend.utils.exceptions import LLMError, APIRequestError
from backend.core import demo_config

# 嘗試導入 Gemini 客戶端，如果 google-genai 未安裝則優雅處理
try:
    from backend.core.gemini_client import GeminiClient
    HAS_GEMINI = True
except ImportError:
    GeminiClient = None
    HAS_GEMINI = False

logger = get_logger(__name__)


class LLMClient:
    """LLM 客戶端類，封裝所有 LLM 調用邏輯"""

    def __init__(self):
        self.client = None
        self.gemini_client = None
        self._initialize_client()

    def reinitialize(self):
        """重新初始化客戶端"""
        logger.info("重新初始化 LLM 客戶端...")
        self._initialize_client()

    def _initialize_client(self):
        """初始化 OpenAI 和 Gemini 客戶端"""
        try:
            self.client = OpenAI()

            # 僅在 google-genai 安裝時初始化 Gemini 客戶端
            if HAS_GEMINI and GeminiClient is not None:
                self.gemini_client = GeminiClient()
            else:
                self.gemini_client = None
                logger.warning("⚠️ Gemini 客戶端未初始化（google-genai 模組未安裝）")

            # 添加 SSL 驗證禁用選項，解決企業網路環境的證書問題
            import httpx
            import os

            # 檢查環境變數，允許用戶控制 SSL 驗證
            disable_ssl_verify = os.getenv('DISABLE_SSL_VERIFY', 'false').lower() == 'true'
            if disable_ssl_verify:
                self.client._client = httpx.Client(verify=False)
                logger.warning("⚠️ SSL 驗證已禁用（環境變數控制）")
            else:
                # 嘗試使用預設設置，如果失敗則自動禁用
                try:
                    # 測試連接
                    test_client = httpx.Client()
                    test_client.close()
                except Exception as e:
                    if "certificate verify failed" in str(e).lower():
                        self.client._client = httpx.Client(verify=False)
                        logger.warning("⚠️ 檢測到 SSL 證書問題，自動禁用 SSL 驗證")
                    else:
                        raise e
        except Exception as e:
            logger.error(f"初始化 OpenAI 客戶端失敗: {e}")
            raise

    def call_llm(self, prompt: str, model: str, llm_params: Dict[str, Any], **kwargs) -> str:
        """
        調用 LLM 生成文本

        參數：
            prompt: 提示詞
            model: 模型名稱
            llm_params: 模型參數
            **kwargs: 額外參數

        返回：
            str: 生成的文本
        """
        try:
            logger.info(f"調用 LLM，模型：{model}")
            logger.debug(f"提示詞長度：{len(prompt)} 字符")

            if demo_config.is_active_stage_demo_or_any():
                raise LLMError("Refusing real LLM call: demo mode is active for this request stage")

            # 根據模型類型選擇不同的調用方式
            # 根據模型類型選擇不同的調用方式
            if model.startswith('gpt-5'):
                return self._call_gpt5_responses_api(prompt, model, llm_params, **kwargs)
            elif model.startswith('gemini-'):
                return self.gemini_client.generate_content_sync(model, prompt)
            else:
                return self._call_gpt4_chat_api(prompt, model, llm_params, **kwargs)

        except Exception as e:
            logger.error(f"LLM 調用失敗：{e}")
            raise LLMError(f"LLM 調用失敗：{str(e)}")

    def _call_gpt5_responses_api(self, prompt: str, model: str, llm_params: Dict[str, Any], **kwargs) -> str:
        """
        調用 GPT-5 Responses API

        參數：
            prompt: 提示詞
            model: 模型名稱
            llm_params: 模型參數
            **kwargs: 額外參數

        返回：
            str: 生成的文本
        """
        try:
            # 構建 Responses API 參數
            responses_params = {
                "model": model,
                "input": [{"role": "user", "content": prompt}],
                "max_output_tokens": llm_params.get("max_output_tokens", 2000),
                "timeout": llm_params.get("timeout", 60)
            }

            # 添加可選參數
            if "reasoning_effort" in llm_params:
                responses_params["reasoning"] = {"effort": llm_params["reasoning_effort"]}
            if "verbosity" in llm_params:
                responses_params["text"] = {"verbosity": llm_params["verbosity"]}
            if "temperature" in llm_params:
                responses_params["temperature"] = llm_params["temperature"]

            logger.debug(f"使用 Responses API，參數：{responses_params}")

            # 重試機制
            max_retries = 3
            base_tokens = llm_params.get("max_output_tokens", 2000)

            for retry_count in range(max_retries):
                # 每次重試時增加 1000 tokens
                current_tokens = base_tokens + (retry_count * 1000)
                responses_params["max_output_tokens"] = current_tokens

                logger.info(f"嘗試 {retry_count + 1}/{max_retries}，使用 {current_tokens} tokens")

                try:
                    response = self.client.responses.create(**responses_params)

                    # 檢查響應狀態
                    if hasattr(response, 'status') and response.status == 'incomplete':
                        logger.warning(f"檢測到 incomplete 狀態，嘗試提取部分內容")

                        # 對於非結構化輸出，嘗試提取部分文本
                        if hasattr(response, 'output_text') and response.output_text:
                            output = response.output_text
                            logger.info(f"從 incomplete 響應中提取部分文本: {len(output)} 字符")
                            return output

                        # 如果無法提取部分內容，則重試
                        if retry_count < max_retries - 1:
                            logger.warning(f"無法提取部分內容，重試 {retry_count + 1}/{max_retries}")
                            time.sleep(2)
                            continue

                    # 提取文本內容
                    if hasattr(response, 'output_text') and response.output_text:
                        output = response.output_text
                        logger.info(f"成功提取文本: {len(output)} 字符")
                        return output
                    elif hasattr(response, 'output') and response.output:
                        # 從 output 陣列中提取文本
                        output_parts = []
                        for item in response.output:
                            if hasattr(item, 'message') and hasattr(item.message, 'content'):
                                for content in item.message.content:
                                    if hasattr(content, 'text') and content.text:
                                        output_parts.append(content.text)
                        output = "".join(output_parts)
                        if output:
                            logger.info(f"成功提取文本: {len(output)} 字符")
                            return output

                    # 如果都失敗了，嘗試使用 content
                    if hasattr(response, 'content'):
                        output = response.content
                        logger.info(f"使用 content 提取文本: {len(output)} 字符")
                        return output

                except Exception as e:
                    logger.error(f"API 調用失敗 (嘗試 {retry_count + 1}/{max_retries}): {e}")
                    if retry_count < max_retries - 1:
                        time.sleep(2)
                        continue
                    raise

            raise APIRequestError("所有重試都失敗")

        except Exception as e:
            logger.error(f"GPT-5 Responses API 調用失敗: {e}")
            raise

    def _call_gpt4_chat_api(self, prompt: str, model: str, llm_params: Dict[str, Any], **kwargs) -> str:
        """
        調用 GPT-4 Chat Completions API

        參數：
            prompt: 提示詞
            model: 模型名稱
            llm_params: 模型參數
            **kwargs: 額外參數

        返回：
            str: 生成的文本
        """
        try:
            # 構建 Chat Completions API 參數
            chat_params = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": llm_params.get("max_tokens", 2000),
                "temperature": llm_params.get("temperature", 0.7)
            }

            logger.debug(f"使用 Chat Completions API，參數：{chat_params}")

            response = self.client.chat.completions.create(**chat_params)

            if response.choices and response.choices[0].message:
                output = response.choices[0].message.content
                logger.info(f"Chat API 調用成功，回應長度：{len(output)} 字符")
                return output
            else:
                raise APIRequestError("Chat API 返回空響應")

        except Exception as e:
            logger.error(f"Chat Completions API 調用失敗：{e}")
            raise

    def call_structured_llm(self, prompt: str, schema: Dict[str, Any], model: str, llm_params: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        調用結構化 LLM 生成 JSON 格式內容

        參數：
            prompt: 提示詞
            schema: JSON Schema
            model: 模型名稱
            llm_params: 模型參數
            **kwargs: 額外參數

        返回：
            Dict[str, Any]: 結構化數據
        """
        try:
            logger.info(f"調用結構化 LLM，模型：{model}")

            if demo_config.is_active_stage_demo_or_any():
                raise LLMError("Refusing real LLM call: demo mode is active for this request stage")

            if model.startswith('gemini-'):
                return self.gemini_client.generate_structured_content_sync(model, prompt, schema)

            # 只支援 GPT-5 系列 (和 Gemini)
            if not model.startswith('gpt-5'):
                raise LLMError(f"不支援的模型：{model}，只支援 GPT-5 系列和 Gemini")

            return self._call_gpt5_structured_api(prompt, schema, model, llm_params, **kwargs)

        except Exception as e:
            logger.error(f"結構化 LLM 調用失敗：{e}")
            raise LLMError(f"結構化 LLM 調用失敗：{str(e)}")

    def _call_gpt5_structured_api(self, prompt: str, schema: Dict[str, Any], model: str, llm_params: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        調用 GPT-5 結構化 API

        參數：
            prompt: 提示詞
            schema: JSON Schema
            model: 模型名稱
            llm_params: 模型參數
            **kwargs: 額外參數

        返回：
            Dict[str, Any]: 結構化數據
        """
        try:
            # 構建 Responses API 參數
            responses_params = {
                "model": model,
                "input": [{"role": "user", "content": prompt}],
                "text": {
                    "format": {
                        "type": "json_schema",
                        "name": "ResearchProposal",
                        "strict": True,
                        "schema": schema,
                    },
                    "verbosity": llm_params.get("verbosity", "low")
                },
                "max_output_tokens": llm_params.get("max_output_tokens", 2000),
                "timeout": llm_params.get("timeout", 60)
            }

            # 處理 reasoning 參數
            if 'reasoning' in llm_params:
                logger.info(f"🔍 [DEBUG] 使用適配後的 reasoning 參數: {llm_params['reasoning']}")
                responses_params['reasoning'] = llm_params['reasoning']
            else:
                logger.info(f"🔍 [DEBUG] 使用默認 reasoning 參數")
                responses_params['reasoning'] = {"effort": llm_params.get("reasoning_effort", "medium")}

            # 處理 text 參數
            if 'text' in llm_params:
                logger.info(f"🔍 [DEBUG] 使用適配後的 text 參數: {llm_params['text']}")
                # 保留 JSON Schema 格式信息，只更新 verbosity
                if 'verbosity' in llm_params['text']:
                    responses_params['text']['verbosity'] = llm_params['text']['verbosity']
                logger.info(f"🔍 [DEBUG] 更新後的 text 參數: {responses_params['text']}")
            else:
                logger.info(f"🔍 [DEBUG] 使用默認 text 參數")
                responses_params['text']['verbosity'] = llm_params.get("verbosity", "low")

            logger.debug(f"使用 Responses API with JSON Schema，參數：{responses_params}")

            # 重試機制
            max_retries = 3
            base_tokens = llm_params.get("max_output_tokens", 2000)

            for retry_count in range(max_retries):
                # 每次重試時增加 1000 tokens
                current_tokens = base_tokens + (retry_count * 1000)
                responses_params["max_output_tokens"] = current_tokens

                logger.info(f"嘗試 {retry_count + 1}/{max_retries}，使用 {current_tokens} tokens")

                try:
                    response = self.client.responses.create(**responses_params)

                    # 檢查響應狀態
                    if hasattr(response, 'status') and response.status == 'incomplete':
                        logger.warning(f"檢測到 incomplete 狀態，嘗試提取部分內容")

                        # 嘗試從 incomplete 響應中提取部分 JSON
                        partial_json = self._extract_partial_json_from_response(response)
                        if partial_json:
                            logger.info("成功從 incomplete 響應中提取部分 JSON")
                            return partial_json

                        # 如果無法提取部分內容，則重試
                        if retry_count < max_retries - 1:
                            logger.warning(f"無法提取部分內容，重試 {retry_count + 1}/{max_retries}")
                            time.sleep(2)
                            continue

                    # 提取 JSON 內容
                    if hasattr(response, 'output_text') and response.output_text:
                        try:
                            result = json.loads(response.output_text)
                            logger.info("成功解析 JSON 結構化提案")
                            return result
                        except json.JSONDecodeError as e:
                            logger.error(f"JSON 解析失敗: {e}")
                            logger.debug(f"嘗試的文本: {response.output_text[:200]}...")

                    # 如果 output_text 失敗，嘗試從 output 提取
                    if hasattr(response, 'output') and response.output:
                        text_content = ""
                        for item in response.output:
                            if hasattr(item, 'message') and hasattr(item.message, 'content'):
                                for content in item.message.content:
                                    if hasattr(content, 'text') and content.text:
                                        text_content += content.text

                        if text_content:
                            try:
                                result = json.loads(text_content)
                                logger.info("成功解析 JSON 結構化提案")
                                return result
                            except json.JSONDecodeError as e:
                                logger.error(f"JSON 解析失敗: {e}")
                                logger.debug(f"嘗試的文本: {text_content[:200]}...")

                    logger.warning("無法從 Responses API 提取 JSON 內容")

                except Exception as e:
                    logger.error(f"API 調用失敗 (嘗試 {retry_count + 1}/{max_retries}): {e}")
                    if retry_count < max_retries - 1:
                        time.sleep(2)
                        continue
                    raise

            raise APIRequestError("所有重試都失敗")

        except Exception as e:
            logger.error(f"GPT-5 結構化 API 調用失敗: {e}")
            raise

    def _extract_partial_json_from_response(self, response) -> Optional[Dict[str, Any]]:
        """
        從 incomplete 響應中提取部分 JSON 內容

        Args:
            response: OpenAI Responses API 響應對象

        Returns:
            Optional[Dict[str, Any]]: 提取的 JSON 對象，如果失敗則返回 None
        """
        try:
            # 嘗試從 output_text 提取
            if hasattr(response, 'output_text') and response.output_text:
                text = response.output_text
                logger.debug(f"嘗試從 output_text 提取部分 JSON: {text[:200]}...")

                # 嘗試找到最後一個完整的 JSON 對象
                brace_count = 0
                last_complete_pos = -1

                for i, char in enumerate(text):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            last_complete_pos = i

                if last_complete_pos > 0:
                    complete_json = text[:last_complete_pos + 1]
                    try:
                        result = json.loads(complete_json)
                        logger.info(f"成功修復不完整的 JSON，長度: {len(complete_json)} 字符")
                        return result
                    except json.JSONDecodeError as e:
                        logger.debug(f"JSON 修復失敗: {e}")

            # 嘗試從 output 陣列提取
            if hasattr(response, 'output') and response.output:
                text_content = ""
                for item in response.output:
                    if hasattr(item, 'message') and hasattr(item.message, 'content'):
                        for content in item.message.content:
                            if hasattr(content, 'text') and content.text:
                                text_content += content.text

                if text_content:
                    logger.debug(f"嘗試從 output 陣列提取部分 JSON: {text_content[:200]}...")

                    # 同樣嘗試修復不完整的 JSON
                    brace_count = 0
                    last_complete_pos = -1

                    for i, char in enumerate(text_content):
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                last_complete_pos = i

                    if last_complete_pos > 0:
                        complete_json = text_content[:last_complete_pos + 1]
                        try:
                            result = json.loads(complete_json)
                            logger.info(f"成功從 output 陣列修復不完整的 JSON，長度: {len(complete_json)} 字符")
                            return result
                        except json.JSONDecodeError as e:
                            logger.debug(f"output 陣列 JSON 修復失敗: {e}")

            logger.warning("無法從 incomplete 響應中提取有效的 JSON 內容")
            return None

        except Exception as e:
            logger.error(f"提取部分 JSON 時發生錯誤: {e}")
            return None


# 全局 LLM 客戶端實例
_llm_client = None


def get_llm_client() -> LLMClient:
    """獲取全局 LLM 客戶端實例"""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client

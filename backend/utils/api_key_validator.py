"""
API Key 驗證模組
==============

負責驗證 OpenAI API Key 的有效性
"""

import asyncio
import logging
from typing import Tuple
# 移除模組級別的openai導入，改為延遲導入
# import openai

logger = logging.getLogger(__name__)

class APIKeyValidator:
    """API Key 驗證器"""

    @staticmethod
    async def validate_openai_api_key(api_key: str) -> Tuple[bool, str]:
        """
        驗證 OpenAI API Key 有效性

        Args:
            api_key: OpenAI API Key

        Returns:
            Tuple[bool, str]: (是否有效, 錯誤訊息)
        """
        if not api_key or not api_key.strip():
            return False, "API Key 不能為空"

        try:
            # 延遲導入openai，避免模組級別導入問題
            import openai

            # 設置 API Key
            client = openai.AsyncOpenAI(api_key=api_key.strip())

            # 使用 models API 來驗證 key 有效性
            response = await asyncio.wait_for(
                client.models.list(),
                timeout=15.0  # 增加超時時間到15秒
            )

            # 檢查回應是否有效
            if response and hasattr(response, 'data') and len(response.data) > 0:
                logger.info("OpenAI API Key 驗證成功")
                return True, "API Key 驗證成功"
            else:
                return False, "API Key 驗證失敗：無法獲取模型列表"

        except asyncio.TimeoutError:
            logger.warning("OpenAI API Key 驗證超時")
            return False, "API Key 驗證超時，請檢查網路連接"

        except openai.AuthenticationError:
            logger.warning("OpenAI API Key 驗證失敗：認證錯誤")
            return False, "API Key 無效或已過期"

        except openai.RateLimitError:
            logger.warning("OpenAI API Key 驗證失敗：速率限制")
            return False, "API 調用頻率過高，請稍後再試"

        except openai.APIError as e:
            logger.warning(f"OpenAI API Key 驗證失敗：API 錯誤 - {e}")
            return False, f"API 錯誤：{str(e)}"

        except Exception as e:
            logger.error(f"OpenAI API Key 驗證時發生未知錯誤：{e}")
            return False, f"驗證過程中發生錯誤：{str(e)}"

    @staticmethod
    async def validate_google_api_key(api_key: str) -> Tuple[bool, str]:
        """
        驗證 Google API Key (Gemini) 有效性

        Args:
            api_key: Google API Key

        Returns:
            Tuple[bool, str]: (是否有效, 錯誤訊息)
        """
        if not api_key or not api_key.strip():
            return False, "API Key 不能為空"

        try:
            from google import genai

            # 設置 API Key
            client = genai.Client(api_key=api_key.strip())

            # 使用 models API 來驗證 key 有效性
            # google-genai SDK 的 list_models 是同步的，我們將其封裝在 to_thread 中
            response = await asyncio.to_thread(client.models.list)

            if response:
                logger.info("Google API Key 驗證成功")
                return True, "API Key 驗證成功"
            else:
                return False, "API Key 驗證失敗：無法獲取模型列表"

        except Exception as e:
            logger.warning(f"Google API Key 驗證失敗：{e}")
            return False, f"API Key 驗證失敗：{str(e)}"

    @staticmethod
    def validate_openai_api_key_sync(api_key: str) -> Tuple[bool, str]:
        """
        同步驗證 OpenAI API Key 有效性

        Args:
            api_key: OpenAI API Key

        Returns:
            Tuple[bool, str]: (是否有效, 錯誤訊息)
        """
        try:
            # 使用同步方式驗證
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                APIKeyValidator.validate_openai_api_key(api_key)
            )
            loop.close()
            return result
        except Exception as e:
            logger.error(f"同步驗證 API Key 時發生錯誤：{e}")
            return False, f"驗證過程中發生錯誤：{str(e)}"

# 創建全局實例
api_key_validator = APIKeyValidator()

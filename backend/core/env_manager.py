"""
環境變量管理模組
==============

負責管理 .env 檔案的讀取、寫入和驗證功能
"""

import os
import re
from pathlib import Path
from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class EnvManager:
    """環境變量管理器"""

    def __init__(self):
        # 獲取項目根目錄
        current_file = Path(__file__)
        self.project_root = current_file.parent.parent.parent
        self.env_file = self.project_root / ".env"

        logger.info(f"EnvManager 初始化: {self.env_file}")

    def read_env_file(self) -> Dict[str, str]:
        """
        讀取 .env 檔案內容

        Returns:
            Dict[str, str]: 環境變量字典
        """
        env_vars = {}

        if not self.env_file.exists():
            logger.warning(f".env 檔案不存在: {self.env_file}")
            return env_vars

        try:
            with open(self.env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    # 跳過空行和註釋
                    if not line or line.startswith('#'):
                        continue

                    # 解析 key=value 格式
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()

                        # 移除引號
                        if (value.startswith('"') and value.endswith('"')) or \
                           (value.startswith("'") and value.endswith("'")):
                            value = value[1:-1]

                        env_vars[key] = value

            logger.info(f"成功讀取 .env 檔案，包含 {len(env_vars)} 個變量")
            return env_vars

        except Exception as e:
            logger.error(f"讀取 .env 檔案失敗: {e}")
            return {}

    def write_env_file(self, env_vars: Dict[str, str]) -> bool:
        """
        寫入 .env 檔案

        Args:
            env_vars: 環境變量字典

        Returns:
            bool: 是否成功寫入
        """
        try:
            # 確保目錄存在
            self.env_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.env_file, 'w', encoding='utf-8') as f:
                for key, value in env_vars.items():
                    # 如果值包含空格或特殊字符，加上引號
                    if ' ' in value or '#' in value:
                        f.write(f'{key}="{value}"\n')
                    else:
                        f.write(f'{key}={value}\n')

            logger.info(f"成功寫入 .env 檔案: {self.env_file}")
            return True

        except Exception as e:
            logger.error(f"寫入 .env 檔案失敗: {e}")
            return False

    def update_env_variable(self, key: str, value: str) -> bool:
        """
        更新單個環境變量

        Args:
            key: 變量名稱
            value: 變量值

        Returns:
            bool: 是否成功更新
        """
        try:
            # 讀取現有內容
            env_vars = self.read_env_file()

            # 更新變量
            env_vars[key] = value

            # 寫回檔案
            return self.write_env_file(env_vars)

        except Exception as e:
            logger.error(f"更新環境變量失敗: {e}")
            return False

    def get_env_variable(self, key: str) -> Optional[str]:
        """
        獲取環境變量值

        Args:
            key: 變量名稱

        Returns:
            Optional[str]: 變量值，如果不存在則返回 None
        """
        env_vars = self.read_env_file()
        return env_vars.get(key)

    def get_provider_key(self, key: str) -> Optional[str]:
        """
        獲取 provider (LLM) API key，若任一 demo stage 為啟用中則拒絕回傳。

        這是 defense-in-depth 的 Layer A（Settings/狀態檢查用途）；實際網路呼叫的
        拒絕在 provider client（gemini_client.py / llm_client.py）中實作，較貼近真正
        開啟 socket 的位置。與 read_env_file()/write_env_file() 無關，不影響一般
        設定值的讀寫。

        Args:
            key: 變量名稱（例如 OPENAI_API_KEY、GOOGLE_API_KEY）

        Returns:
            Optional[str]: demo mode 啟用時一律回傳 None；否則委派給 get_env_variable。
        """
        from backend.core import demo_config

        if demo_config.is_active_stage_demo_or_any():
            logger.warning(
                f"Refusing to load provider key {key}: demo mode is active for this request stage"
            )
            return None
        return self.get_env_variable(key)

    def create_dummy_env_file(self) -> bool:
        """
        創建 dummy .env 檔案

        Returns:
            bool: 是否成功創建
        """
        dummy_vars = {
            "OPENAI_API_KEY": "sk-dummy-key-placeholder",
            "GOOGLE_API_KEY": "dummy-google-key-placeholder"
        }

        return self.write_env_file(dummy_vars)



    def get_env_file_status(self) -> Dict[str, any]:
        """
        獲取 .env 檔案狀態

        Returns:
            Dict[str, any]: 狀態信息
        """
        status = {
            "exists": self.env_file.exists(),
            "path": str(self.env_file),
            "exists": self.env_file.exists(),
            "path": str(self.env_file),
            "openai_key_configured": False,
            "google_key_configured": False
        }

        if status["exists"]:
            env_vars = self.read_env_file()
            openai_key = env_vars.get("OPENAI_API_KEY", "")

            # 檢查是否為 dummy key
            status["openai_key_configured"] = bool(
                openai_key and
                openai_key != "sk-dummy-key-placeholder" and
                not openai_key.startswith("sk-dummy")
            )

            google_key = env_vars.get("GOOGLE_API_KEY", "")
            status["google_key_configured"] = bool(
                google_key and
                google_key != "dummy-google-key-placeholder" and
                not google_key.startswith("dummy-google")
            )

        return status

# 創建全局實例
env_manager = EnvManager()

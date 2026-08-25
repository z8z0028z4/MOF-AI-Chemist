"""
配置管理模塊
============

管理應用程序的配置設置，包括環境變量、數據庫連接等
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# 載入環境變量
load_dotenv()

# Gemini Model Constants
GEMINI_3_PRO = "gemini-3-pro-preview"
GEMINI_3_FLASH = "gemini-3-flash-preview"
GEMINI_2_5_PRO = "gemini-2.5-pro"
GEMINI_2_5_FLASH = "gemini-2.5-flash"
GEMINI_2_5_FLASH_LITE = "gemini-2.5-flash-lite-preview"

class Settings(BaseSettings):
    """應用程序配置類"""

    # V2 Pydantic Configuration:
    # This combines the old 'class Config' and the 'model_config' into one.
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra='ignore'  # This is crucial to ignore ANONYMIZED_TELEMETRY
    )

    # 應用基本信息
    app_name: str = "AI Research Assistant"
    app_version: str = "1.0.0"
    debug: bool = False

    # API 配置
    api_prefix: str = "/api/v1"
    cors_origins: list = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    # 數據庫配置
    database_url: str = "sqlite:///./ai_research.db"

    # Redis 配置
    redis_url: str = "redis://localhost:6379"

    # 文件存儲配置
    upload_dir: str = "uploads"
    allowed_file_types: list = [
        ".pdf", ".docx", ".xlsx", ".txt",
        ".png", ".jpg", ".jpeg", ".gif"
    ]

    # AI 服務配置
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-5o-mini"
    openai_max_tokens: int = 4000

    # Gemini Configuration
    google_api_key: Optional[str] = None
    gemini_default_model: str = "gemini-3-flash-preview"

    # 化學品查詢配置
    pubchem_base_url: str = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"

    # 文獻搜尋配置
    europepmc_base_url: str = "https://www.ebi.ac.uk/europepmc/webservices/rest"

    # 安全配置
    secret_key: str = "your-secret-key-here"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

# 創建全局配置實例
settings = Settings()

# 確保上傳目錄存在
os.makedirs(settings.upload_dir, exist_ok=True)

def reload_config():
    """
    重新載入配置
    用於在 .env 檔案更新後重新載入配置
    """
    global settings

    # 重新載入環境變量
    from dotenv import load_dotenv
    load_dotenv(override=True)

    # 重新創建配置實例
    settings = Settings()

    return settings

def validate_config():
    """
    驗證配置是否完整
    """
    validation_result = {
        "openai_api_key_configured": bool(settings.openai_api_key and
                                          settings.openai_api_key != "sk-dummy-key-placeholder" and
                                          not settings.openai_api_key.startswith("sk-dummy")),
        "google_api_key_configured": bool(settings.google_api_key and
                                          settings.google_api_key != "dummy-google-key-placeholder" and
                                          not settings.google_api_key.startswith("dummy-google")),
        "config_complete": True
    }

    # 檢查必要的配置 (OpenAI OR Gemini should be enough, but for now let's say at least one)
    # But for this specific task, if we want to support Gemini, we should check it.
    # However, validate_config usually checks if the *required* stuff is there.
    # Let's assume user might only have one.
    if not (validation_result["openai_api_key_configured"] or validation_result["google_api_key_configured"]):
        validation_result["config_complete"] = False

    return validation_result

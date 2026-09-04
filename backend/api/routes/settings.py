"""
設定管理API路由
==============

提供系統設定的管理功能，包括LLM模型選擇和API Key管理等
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import json
from pathlib import Path

import sys
from pathlib import Path

# 添加項目根目錄到Python路徑
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.core.config import settings, reload_config, validate_config
from backend.core.settings_manager import settings_manager
from backend.core.env_manager import env_manager
from backend.utils.api_key_validator import api_key_validator
from backend.core.providers.openrouter_provider import OpenRouterCatalog

_openrouter_catalog = OpenRouterCatalog(lambda: env_manager.get_provider_key("OPENROUTER_API_KEY"))

router = APIRouter(prefix="/settings", tags=["settings"])

class ModelSettings(BaseModel):
    """模型設定模型"""
    llm_model: str
    llm_provider: Optional[str] = None

class LLMParameters(BaseModel):
    """LLM參數設定模型"""
    max_tokens: Optional[int] = None
    timeout: Optional[int] = None
    reasoning_effort: Optional[str] = None
    verbosity: Optional[str] = None

class ModelSettingsResponse(BaseModel):
    """模型設定回應模型"""
    current_model: str
    available_models: list
    provider: str = "openai"
    catalog_stale: bool = False
    catalog_error: Optional[str] = None


class LLMParametersResponse(BaseModel):
    """LLM參數回應模型"""
    max_tokens: int
    timeout: int
    reasoning_effort: Optional[str] = None
    verbosity: Optional[str] = None

class JSONSchemaParameters(BaseModel):
    """JSON Schema參數設定模型"""
    min_length: Optional[int] = None
    max_length: Optional[int] = None

class JSONSchemaParametersResponse(BaseModel):
    """JSON Schema參數回應模型"""
    min_length: int
    max_length: int

class ModelParametersInfo(BaseModel):
    """模型參數資訊回應模型"""
    supported_parameters: dict
    current_parameters: dict

class OpenAIKeySettings(BaseModel):
    """OpenAI API Key 設定模型"""
    openai_api_key: str

class GoogleKeySettings(BaseModel):
    """Google API Key 設定模型"""
    google_api_key: str

class ProviderKeySettings(BaseModel):
    provider: str
    api_key: Optional[str] = None
    clear: bool = False

class EnvFileStatus(BaseModel):
    """環境檔案狀態回應模型"""
    exists: bool
    path: str
    openai_key_configured: bool
    google_key_configured: bool
    openrouter_key_configured: bool = False

class DevModeSettings(BaseModel):
    """開發模式設定模型"""
    is_dev_mode: bool


class DemoModeSettings(BaseModel):
    """Proposal deterministic demo stages."""
    enabled: bool = False
    mock_proposal: bool = False
    mock_property_prediction: bool = False
    mock_generate_new_idea: bool = False
    mock_experiment_detail: bool = False

@router.get("/model", response_model=ModelSettingsResponse)
async def get_model_settings():
    """獲取當前LLM模型設定"""
    try:
        # 獲取當前模型；legacy settings are intentionally ignored.
        current_model = settings_manager.get_current_model()

        # 可用的模型列表
        available_models = [
            {
                "value": "gpt-5",
                "label": "GPT-5",
                "description": "最新的GPT-5模型，功能最強大，支援推理控制和工具鏈"
            },
            {
                "value": "gpt-5-nano",
                "label": "GPT-5 Nano",
                "description": "GPT-5的輕量版本，速度最快，適合簡單格式化任務"
            },
            {
                "value": "gpt-5-mini",
                "label": "GPT-5 Mini",
                "description": "GPT-5的平衡版本，速度與功能兼具，支援推理控制"
            },
            {
                "value": "gemini-3-pro-preview",
                "label": "Gemini 3 Pro",
                "description": "Google 最強大的多模態模型，適合複雜的研究分析與推理"
            },
            {
                "value": "gemini-3-flash-preview",
                "label": "Gemini 3 Flash",
                "description": "Google 的輕量高性能模型，適合快速響應與大規模數據處理"
            },
            {
                "value": "gemini-2.5-flash-lite-preview",
                "label": "Gemini 2.5 Flash Lite",
                "description": "Google 最經濟高效的模型，適合簡單的文本生成任務"
            },
            {
                "value": "gemini-2.5-flash",
                "label": "Gemini 2.5 Flash",
                "description": "Google 的主流高性能模型，速度與能力兼備 (穩定版)"
            },
            {
                "value": "gemini-2.5-pro",
                "label": "Gemini 2.5 Pro",
                "description": "Google 的高難度任務專用模型，具備優異的代碼和學術推理能力 (穩定版)"
            }
        ]

        provider = settings_manager.get_provider()
        catalog_stale = False
        catalog_error = None
        if provider == "openrouter":
            key = env_manager.get_provider_key("OPENROUTER_API_KEY")
            if key:
                try:
                    catalog_data = _openrouter_catalog.load()
                    available_models = [{"value": item.id, "label": item.name, "vendor": item.vendor} for item in catalog_data["models"]]
                    catalog_stale, catalog_error = catalog_data.get("stale", False), catalog_data.get("error")

                except Exception as exc:
                    available_models = []
                    catalog_stale = True
                    catalog_error = f"Unable to load the OpenRouter model catalog: {exc}"
            else:
                available_models = []
        return ModelSettingsResponse(
            current_model=current_model,
            available_models=available_models,
            provider=provider,
            catalog_stale=catalog_stale,
            catalog_error=catalog_error,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取設定失敗: {str(e)}")

@router.post("/model")
async def update_model_settings(model_settings: ModelSettings):
    """更新LLM模型設定"""
    try:
        provider = model_settings.llm_provider or settings_manager.get_provider()
        if provider == "openrouter":
            if not model_settings.llm_model or "/" not in model_settings.llm_model:
                raise ValueError("OpenRouter requires an explicitly selected model")
            try:
                eligible = _openrouter_catalog.contains(model_settings.llm_model, refresh=True)
            except Exception as exc:
                raise ValueError("OpenRouter model catalog unavailable; refresh and reselect a model") from exc
            if not eligible:
                raise ValueError("Selected OpenRouter model is unavailable; refresh and reselect a model")
        if model_settings.llm_provider:
            settings_manager.set_provider(model_settings.llm_provider)
        # 使用設定管理器更新主模型
        if model_settings.llm_model:
            settings_manager.set_current_model(model_settings.llm_model)

        return {
            "message": "模型設定已成功更新",
            "current_model": model_settings.llm_model,
            "provider": settings_manager.get_provider(),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新設定失敗: {str(e)}")


@router.get("/llm-parameters", response_model=LLMParametersResponse)
async def get_llm_parameters():
    """獲取當前LLM參數設定"""
    try:
        params = settings_manager.get_llm_parameters()
        return LLMParametersResponse(**params)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取LLM參數失敗: {str(e)}")

@router.post("/llm-parameters")
async def update_llm_parameters(parameters: LLMParameters):
    """更新LLM參數設定"""
    try:
        # 使用設定管理器更新參數
        settings_manager.set_llm_parameters(
            max_tokens=parameters.max_tokens,
            timeout=parameters.timeout,
            reasoning_effort=parameters.reasoning_effort,
            verbosity=parameters.verbosity
        )

        # 獲取更新後的參數
        updated_params = settings_manager.get_llm_parameters()

        return {
            "message": "LLM參數已成功更新",
            "parameters": updated_params
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新LLM參數失敗: {str(e)}")

@router.get("/model-parameters-info", response_model=ModelParametersInfo)
async def get_model_parameters_info(model_name: Optional[str] = None):
    """獲取指定模型支援的參數資訊"""
    try:
        if model_name is None:
            model_name = settings_manager.get_current_model()

        # 獲取模型支援的參數
        supported_params = settings_manager.get_model_supported_parameters(model_name)

        # 獲取當前參數
        current_params = settings_manager.get_llm_parameters()

        return ModelParametersInfo(
            supported_parameters=supported_params,
            current_parameters=current_params
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取模型參數資訊失敗: {str(e)}")

@router.get("/json-schema-parameters", response_model=JSONSchemaParametersResponse)
async def get_json_schema_parameters():
    """獲取當前JSON Schema參數設定"""
    try:
        params = settings_manager.get_json_schema_parameters()
        return JSONSchemaParametersResponse(**params)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取JSON Schema參數失敗: {str(e)}")

@router.post("/json-schema-parameters")
async def update_json_schema_parameters(parameters: JSONSchemaParameters):
    """更新JSON Schema參數設定"""
    try:
        # 使用設定管理器更新參數
        settings_manager.set_json_schema_parameters(
            min_length=parameters.min_length,
            max_length=parameters.max_length
        )

        # 獲取更新後的參數
        updated_params = settings_manager.get_json_schema_parameters()

        return {
            "message": "JSON Schema參數已成功更新",
            "parameters": updated_params
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新JSON Schema參數失敗: {str(e)}")

@router.get("/json-schema-parameters-info")
async def get_json_schema_parameters_info():
    """獲取JSON Schema參數資訊"""
    try:
        # 獲取支援的參數
        supported_params = settings_manager.get_json_schema_supported_parameters()

        # 獲取當前參數
        current_params = settings_manager.get_json_schema_parameters()

        return {
            "supported_parameters": supported_params,
            "current_parameters": current_params
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取JSON Schema參數資訊失敗: {str(e)}")

@router.get("/system")
async def get_system_settings():
    """獲取系統設定資訊"""
    try:
        return {
            "app_name": settings.app_name,
            "app_version": settings.app_version,
            "debug": settings.debug,
            "api_prefix": settings.api_prefix,
            "upload_dir": settings.upload_dir,
            "max_file_size": "unlimited",  # File size limit removed
            "allowed_file_types": settings.allowed_file_types
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取系統設定失敗: {str(e)}")

# ==================== API Key 管理端點 ====================

@router.get("/env-status", response_model=EnvFileStatus)
async def get_env_file_status():
    """獲取 .env 檔案狀態"""
    try:
        status = env_manager.get_env_file_status()
        status["openrouter_key_configured"] = bool(env_manager.get_env_variable("OPENROUTER_API_KEY"))
        return EnvFileStatus(**status)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取環境檔案狀態失敗: {str(e)}")


@router.post("/provider-key")
async def set_provider_key(payload: ProviderKeySettings):
    """Update only the selected provider key; never return key material."""
    names = {"openai": "OPENAI_API_KEY", "google": "GOOGLE_API_KEY", "openrouter": "OPENROUTER_API_KEY"}
    env_name = names.get(payload.provider)
    if not env_name:
        raise HTTPException(status_code=400, detail="Unsupported provider")
    if payload.clear:
        values = env_manager.read_env_file()
        values.pop(env_name, None)
        if not env_manager.write_env_file(values):
            raise HTTPException(status_code=500, detail="Unable to clear provider key")
        reload_config()
    elif payload.api_key and payload.api_key.strip():
        if not env_manager.update_env_variable(env_name, payload.api_key):
            raise HTTPException(status_code=500, detail="Unable to save provider key")
        reload_config()
    return {"provider": payload.provider, "configured": bool(env_manager.get_env_variable(env_name)), "status": "success"}


@router.get("/openrouter/models")
async def get_openrouter_models(refresh: bool = False):
    try:
        data = _openrouter_catalog.load(refresh=refresh)
        return {"models": [{"value": item.id, "label": item.name, "vendor": item.vendor} for item in data["models"]], "stale": data.get("stale", False), "error": data.get("error")}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

from backend.core.llm_client import get_llm_client

@router.post("/api-keys/openai")
async def set_openai_api_key(settings: OpenAIKeySettings):
    """設定 OpenAI API Key"""
    try:
        # API 驗證
        is_valid_api, api_message = await api_key_validator.validate_openai_api_key(
            settings.openai_api_key
        )
        if not is_valid_api:
            raise HTTPException(status_code=400, detail=api_message)

        # 3. 更新 .env 檔案
        success = env_manager.update_env_variable("OPENAI_API_KEY", settings.openai_api_key)
        if not success:
            raise HTTPException(status_code=500, detail="更新 .env 檔案失敗")

        # 4. 重新載入配置
        reload_config()

        # 5. 重新初始化 LLM 客戶端
        get_llm_client().reinitialize()

        return {
            "message": "OpenAI API Key 設定成功",
            "status": "success"
        }

    except HTTPException:
        # 重新拋出 HTTP 異常
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"設定 API Key 失敗: {str(e)}")

@router.post("/api-keys/google")
async def set_google_api_key(settings: GoogleKeySettings):
    """設定 Google API Key"""
    try:
        # API 驗證
        is_valid_api, api_message = await api_key_validator.validate_google_api_key(
            settings.google_api_key
        )
        if not is_valid_api:
            raise HTTPException(status_code=400, detail=api_message)

        # 3. 更新 .env 檔案
        success = env_manager.update_env_variable("GOOGLE_API_KEY", settings.google_api_key)
        if not success:
            raise HTTPException(status_code=500, detail="更新 .env 檔案失敗")

        # 4. 重新載入配置
        reload_config()

        # 5. 重新初始化 LLM 客戶端
        get_llm_client().reinitialize()

        return {
            "message": "Google API Key 設定成功",
            "status": "success"
        }

    except HTTPException:
        # 重新拋出 HTTP 異常
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"設定 API Key 失敗: {str(e)}")

@router.post("/env-file/create-dummy")
async def create_dummy_env_file():
    """創建 dummy .env 檔案"""
    try:
        success = env_manager.create_dummy_env_file()
        if not success:
            raise HTTPException(status_code=500, detail="創建 dummy .env 檔案失敗")

        return {
            "message": "Dummy .env 檔案創建成功",
            "status": "success"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"創建 dummy .env 檔案失敗: {str(e)}")

@router.get("/config-status")
async def get_config_status():
    """獲取配置狀態"""
    try:
        config_validation = validate_config()
        env_status = env_manager.get_env_file_status()

        return {
            "config_validation": config_validation,
            "env_status": env_status,
            "system_ready": config_validation["config_complete"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取配置狀態失敗: {str(e)}")

# ==================== 開發模式管理端點 ====================

@router.get("/dev-mode")
async def get_dev_mode_status():
    """獲取開發模式狀態"""
    try:
        # 從settings.json讀取開發模式狀態
        dev_mode = settings_manager.get_dev_mode_status()
        return {
            "is_dev_mode": dev_mode
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取開發模式狀態失敗: {str(e)}")

@router.post("/dev-mode")
async def set_dev_mode_status(settings: DevModeSettings):
    """設定開發模式狀態"""
    try:
        # 更新開發模式狀態
        success = settings_manager.set_dev_mode_status(settings.is_dev_mode)
        if not success:
            raise HTTPException(status_code=500, detail="設定開發模式狀態失敗")

        return {
            "message": f"開發模式已{'開啟' if settings.is_dev_mode else '關閉'}",
            "status": "success",
            "is_dev_mode": settings.is_dev_mode
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"設定開發模式狀態失敗: {str(e)}")


@router.get("/demo-mode")
async def get_demo_mode_settings():
    """Get deterministic Proposal demo-stage settings."""
    return settings_manager.get_demo_mode_settings()


@router.post("/demo-mode")
async def set_demo_mode_settings(settings: DemoModeSettings):
    """Persist deterministic Proposal demo-stage settings."""
    if "enabled" in settings.model_fields_set:
        enabled = settings.enabled
        settings_manager.set_demo_mode_settings(
            {
                "enabled": enabled,
                "mock_proposal": enabled,
                "mock_property_prediction": enabled,
                "mock_generate_new_idea": enabled,
                "mock_experiment_detail": enabled,
            }
        )
    else:
        settings_manager.set_demo_mode_settings(
            settings.model_dump(exclude_unset=True)
        )
    return {
        "status": "success",
        **settings_manager.get_demo_mode_settings(),
    }

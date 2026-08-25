"""
模型配置模組
============

負責模型參數和配置管理，避免循環導入問題
"""

from typing import Dict, Any, Optional
from backend.utils.logger import get_logger

logger = get_logger(__name__)


class ModelConfig:
    """模型配置管理器"""

    def __init__(self):
        self._current_model = "gpt-5-nano"
        self._model_params = {
            "model": "gpt-5-nano",
            "max_output_tokens": 12000,
            "timeout": 75,
            "reasoning_effort": "low",
            "verbosity": "low"
        }

    def get_current_model(self) -> str:
        """獲取當前模型名稱"""
        return self._current_model

    def set_current_model(self, model: str):
        """設置當前模型名稱"""
        self._current_model = model
        self._model_params["model"] = model
        logger.info(f"模型已設置為: {model}")

    def get_model_params(self) -> Dict[str, Any]:
        """獲取模型參數"""
        return self._model_params.copy()

    def set_model_params(self, params: Dict[str, Any]):
        """設置模型參數"""
        self._model_params.update(params)
        logger.info(f"模型參數已更新: {params}")

    def update_model_param(self, key: str, value: Any):
        """更新單個模型參數"""
        self._model_params[key] = value
        logger.debug(f"模型參數 {key} 已更新為: {value}")

    def get_model_param(self, key: str, default: Any = None) -> Any:
        """獲取單個模型參數"""
        return self._model_params.get(key, default)

    def reset_to_defaults(self):
        """重置為默認參數"""
        self._current_model = "gpt-5-nano"
        self._model_params = {
            "model": "gpt-5-nano",
            "max_output_tokens": 12000,
            "timeout": 75,
            "reasoning_effort": "low",
            "verbosity": "low"
        }
        logger.info("模型參數已重置為默認值")


# 全局模型配置實例
_model_config = None


def get_model_config() -> ModelConfig:
    """獲取全局模型配置實例"""
    global _model_config
    if _model_config is None:
        _model_config = ModelConfig()
    return _model_config


def get_current_model() -> str:
    """獲取當前模型名稱（向後兼容）"""
    return get_model_config().get_current_model()


def get_model_params() -> Dict[str, Any]:
    """獲取模型參數（向後兼容）"""
    return get_model_config().get_model_params()


def set_current_model(model: str):
    """設置當前模型名稱（向後兼容）"""
    get_model_config().set_current_model(model)


def set_model_params(params: Dict[str, Any]):
    """設置模型參數（向後兼容）"""
    get_model_config().set_model_params(params)

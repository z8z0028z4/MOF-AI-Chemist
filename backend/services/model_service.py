"""
模型配置橋接模組
==============

橋接app目錄和backend目錄的模型配置
基於GPT-5官方cookbook的最新參數支援
"""

import os
import sys
from typing import Dict, Any

# 添加backend目錄到Python路徑
backend_path = os.path.join(os.path.dirname(__file__), "..", "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# 嘗試導入參數檢測器
try:
    from .model_parameter_service import adapt_parameters, detect_model_parameters
    HAS_PARAMETER_DETECTOR = True
except ImportError:
    HAS_PARAMETER_DETECTOR = False
    print("警告：無法導入 model_parameter_detector，將使用基礎配置")

def get_current_model():
    """獲取當前模型名稱"""
    # 延遲導入避免循環依賴
    from backend.core.settings_manager import settings_manager
    return settings_manager.get_current_model()

def get_model_params(model_name=None):
    """獲取模型參數"""
    if model_name is None:
        model_name = get_current_model()

    # 延遲導入避免循環依賴
    from backend.core.settings_manager import settings_manager

    # 🔍 [DEBUG] 參數追蹤：檢查設定管理器返回的參數
    print(f"🔍 [MODEL_SERVICE] get_model_params 開始")
    print(f"🔍 [MODEL_SERVICE] - model_name: {model_name}")

    # 從設定管理器獲取動態參數
    llm_params = settings_manager.get_llm_parameters()
    print(f"🔍 [MODEL_SERVICE] - settings_manager.get_llm_parameters() 返回: {llm_params}")

    # 記錄關鍵參數
    print(f"🔍 [MODEL_SERVICE] 關鍵參數檢查:")
    print(f"   - max_tokens: {llm_params.get('max_tokens')}")
    print(f"   - timeout: {llm_params.get('timeout')}")
    print(f"   - reasoning_effort: {llm_params.get('reasoning_effort')}")
    print(f"   - verbosity: {llm_params.get('verbosity')}")

    # 使用新的參數適配器
    if HAS_PARAMETER_DETECTOR:
        try:
            adapted_params = adapt_parameters(model_name, llm_params)
            print(f"🔧 [MODEL_SERVICE] 模型參數適配完成: {adapted_params}")

            # 🔍 [DEBUG] 參數追蹤：檢查適配後的參數
            print(f"🔍 [MODEL_SERVICE] 適配後的參數:")
            print(f"   - adapted_params 類型: {type(adapted_params)}")
            print(f"   - adapted_params 內容: {adapted_params}")
            print(f"   - max_tokens: {adapted_params.get('max_tokens')}")
            print(f"   - max_output_tokens: {adapted_params.get('max_output_tokens')}")
            print(f"   - timeout: {adapted_params.get('timeout')}")
            print(f"   - reasoning: {adapted_params.get('reasoning')}")
            print(f"   - text: {adapted_params.get('text')}")
            print(f"   - verbosity: {adapted_params.get('verbosity')}")

            return adapted_params
        except Exception as e:
            print(f"⚠️ 參數適配失敗，使用基礎參數: {e}")

    # 如果適配失敗或沒有檢測器，使用基礎參數
    base_params = {
        "model": model_name,
        "max_tokens": llm_params.get("max_tokens", 12000),
        "timeout": llm_params.get("timeout", 75),
    }

    # 對於GPT-5系列模型，添加verbosity和reasoning_effort參數
    if model_name.startswith('gpt-5'):
        if "verbosity" in llm_params:
            base_params["verbosity"] = llm_params["verbosity"]
        if "reasoning_effort" in llm_params:
            base_params["reasoning_effort"] = llm_params["reasoning_effort"]

    print(f"🔍 [DEBUG] 使用基礎參數: {base_params}")
    return base_params

def get_model_supported_parameters(model_name: str = None) -> Dict[str, Any]:
    """
    獲取指定模型支援的參數資訊

    Args:
        model_name: 模型名稱，如果為None則使用當前模型

    Returns:
        包含支援參數資訊的字典
    """
    if model_name is None:
        model_name = get_current_model()

    if HAS_PARAMETER_DETECTOR:
        try:
            # 使用新的參數檢測器
            model_info = detect_model_parameters(model_name)
            return model_info['supported_parameters']
        except Exception as e:
            print(f"⚠️ 無法檢測模型參數，使用預設配置: {e}")

    # 如果檢測失敗或沒有檢測器，使用預設配置
    base_params = {
        'max_tokens': {'type': 'int', 'range': [1, 32000], 'default': 2000},
        'timeout': {'type': 'int', 'range': [10, 600], 'default': 60}
    }

    if model_name.startswith('gpt-5'):
        base_params.update({
            'reasoning_effort': {
                'type': 'select',
                'options': ['minimal', 'low', 'medium', 'high'],
                'default': 'medium'
            },
            'verbosity': {
                'type': 'select',
                'options': ['low', 'medium', 'high'],
                'default': 'medium'
            }
        })

    return base_params

def is_model_available(model_name):
    """檢查模型是否可用"""
    valid_models = [
        "gpt-5",
        "gpt-5-nano",
        "gpt-5-mini",
        "gemini-3-pro-preview",
        "gemini-3-flash-preview",
        "gemini-2.5-flash-lite-preview",
        "gemini-2.5-flash",
        "gemini-2.5-pro"
    ]
    return model_name in valid_models

# 為了向後兼容，提供舊的配置接口
def get_llm_params():
    """獲取LLM參數（向後兼容）"""
    return get_model_params()

def get_llm_model_name():
    """獲取LLM模型名稱（向後兼容）"""
    return get_current_model()

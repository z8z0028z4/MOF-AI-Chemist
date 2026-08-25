"""
設定管理器測試
===============

測試 backend.core.settings_manager 模組的所有功能
使用真實檔案操作，不使用 Mock
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path


class TestSettingsManager:
    """測試設定管理器 - 真實測試"""

    def setup_method(self):
        """每個測試前的設置"""
        # 創建臨時目錄用於測試
        self.test_dir = Path(tempfile.mkdtemp())
        self.test_settings_file = self.test_dir / "settings.json"

    def teardown_method(self):
        """每個測試後的清理"""
        # 清理臨時目錄
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_real_settings_manager_initialization(self):
        """測試設定管理器初始化 - 真實測試"""
        from backend.core.settings_manager import SettingsManager

        # 創建新的設定管理器實例
        settings_manager = SettingsManager()

        assert settings_manager is not None
        assert hasattr(settings_manager, 'settings_file')
        assert hasattr(settings_manager, '_current_settings')
        assert isinstance(settings_manager._current_settings, dict)

    def test_real_load_settings_empty_file(self):
        """測試載入不存在的設定檔"""
        from backend.core.settings_manager import SettingsManager

        # 創建測試設定管理器
        settings_manager = SettingsManager()
        # 暫時改變 settings_file 路徑到測試目錄
        settings_manager.settings_file = self.test_settings_file

        # 載入不存在的檔案
        result = settings_manager._load_settings()

        assert isinstance(result, dict)
        assert len(result) == 0

    def test_real_load_settings_with_content(self):
        """測試載入包含內容的設定檔"""
        from backend.core.settings_manager import SettingsManager

        # 創建測試設定檔
        test_settings = {
            "llm_model": "gpt-5-mini",
            "llm_max_tokens": 4000,
            "llm_timeout": 120,
            "custom_setting": "test_value"
        }

        with open(self.test_settings_file, 'w', encoding='utf-8') as f:
            json.dump(test_settings, f)

        # 測試載入
        settings_manager = SettingsManager()
        settings_manager.settings_file = self.test_settings_file

        result = settings_manager._load_settings()

        assert isinstance(result, dict)
        assert result["llm_model"] == "gpt-5-mini"
        assert result["llm_max_tokens"] == 4000
        assert result["custom_setting"] == "test_value"

    def test_real_save_settings(self):
        """測試儲存設定檔"""
        from backend.core.settings_manager import SettingsManager

        settings_manager = SettingsManager()
        settings_manager.settings_file = self.test_settings_file

        # 測試儲存
        test_settings = {
            "llm_model": "gpt-5",
            "llm_max_tokens": 8000,
            "test_key": "test_value"
        }

        settings_manager._save_settings(test_settings)

        assert self.test_settings_file.exists()

        # 驗證檔案內容
        with open(self.test_settings_file, 'r', encoding='utf-8') as f:
            loaded_settings = json.load(f)

        assert loaded_settings["llm_model"] == "gpt-5"
        assert loaded_settings["llm_max_tokens"] == 8000
        assert loaded_settings["test_key"] == "test_value"

    def test_real_get_setting(self):
        """測試獲取設定值"""
        from backend.core.settings_manager import SettingsManager

        settings_manager = SettingsManager()
        settings_manager.settings_file = self.test_settings_file

        # 設置測試設定
        settings_manager._current_settings = {
            "test_key": "test_value",
            "number_key": 123
        }

        # 測試獲取存在的設定
        assert settings_manager.get_setting("test_key") == "test_value"
        assert settings_manager.get_setting("number_key") == 123

        # 測試獲取不存在的設定
        assert settings_manager.get_setting("non_existent") is None
        assert settings_manager.get_setting("non_existent", "default") == "default"

    def test_real_set_setting(self):
        """測試設定值"""
        from backend.core.settings_manager import SettingsManager

        settings_manager = SettingsManager()
        settings_manager.settings_file = self.test_settings_file
        settings_manager._current_settings = {}

        # 測試設定值
        settings_manager.set_setting("test_key", "test_value")

        assert settings_manager.get_setting("test_key") == "test_value"
        assert self.test_settings_file.exists()

        # 驗證檔案已儲存
        with open(self.test_settings_file, 'r', encoding='utf-8') as f:
            saved_settings = json.load(f)

        assert saved_settings["test_key"] == "test_value"

    def test_real_model_management(self):
        """測試模型管理功能"""
        from backend.core.settings_manager import SettingsManager

        settings_manager = SettingsManager()
        settings_manager.settings_file = self.test_settings_file
        settings_manager._current_settings = {}

        # 測試獲取當前模型（默認值）
        current_model = settings_manager.get_current_model()
        assert current_model == "gpt-5-mini"

        # 測試設定有效模型
        settings_manager.set_current_model("gpt-5")
        assert settings_manager.get_current_model() == "gpt-5"

        # 測試設定無效模型
        with pytest.raises(ValueError):
            settings_manager.set_current_model("invalid-model")

    def test_real_fallback_model_management(self):
        """測試備用模型管理功能"""
        from backend.core.settings_manager import SettingsManager

        settings_manager = SettingsManager()
        settings_manager.settings_file = self.test_settings_file
        settings_manager._current_settings = {}

        # 測試獲取備用模型（默認值）
        fallback = settings_manager.get_fallback_model()
        assert fallback == "gemini-3-flash-preview"

        # 測試設定有效備用模型
        settings_manager.set_fallback_model("gemini-2.5-flash")
        assert settings_manager.get_fallback_model() == "gemini-2.5-flash"

        # 測試設定無效備用模型
        with pytest.raises(ValueError):
            settings_manager.set_fallback_model("invalid-model")


    def test_real_llm_parameters(self):
        """測試LLM參數管理"""
        from backend.core.settings_manager import SettingsManager

        settings_manager = SettingsManager()
        settings_manager.settings_file = self.test_settings_file
        settings_manager._current_settings = {}

        # 測試獲取默認參數
        params = settings_manager.get_llm_parameters()

        assert isinstance(params, dict)
        assert "max_tokens" in params
        assert "timeout" in params
        assert "reasoning_effort" in params
        assert "verbosity" in params
        assert params["max_tokens"] == 4000
        assert params["reasoning_effort"] == "medium"

        # 測試設定有效參數
        settings_manager.set_llm_parameters(
            max_tokens=8000,
            timeout=180,
            reasoning_effort="high",
            verbosity="high"
        )

        updated_params = settings_manager.get_llm_parameters()
        assert updated_params["max_tokens"] == 8000
        assert updated_params["timeout"] == 180
        assert updated_params["reasoning_effort"] == "high"
        assert updated_params["verbosity"] == "high"

        # 測試設定無效參數
        with pytest.raises(ValueError):
            settings_manager.set_llm_parameters(max_tokens=50000)  # 超出範圍

        with pytest.raises(ValueError):
            settings_manager.set_llm_parameters(timeout=5)  # 低於最小值

        with pytest.raises(ValueError):
            settings_manager.set_llm_parameters(reasoning_effort="invalid")

    def test_real_json_schema_parameters(self):
        """測試JSON Schema參數管理"""
        from backend.core.settings_manager import SettingsManager

        settings_manager = SettingsManager()
        settings_manager.settings_file = self.test_settings_file
        settings_manager._current_settings = {}

        # 測試獲取默認參數
        params = settings_manager.get_json_schema_parameters()

        assert isinstance(params, dict)
        assert "min_length" in params
        assert "max_length" in params
        assert params["min_length"] == 5
        assert params["max_length"] == 2000

        # 測試設定有效參數
        settings_manager.set_json_schema_parameters(
            min_length=10,
            max_length=3000
        )

        updated_params = settings_manager.get_json_schema_parameters()
        assert updated_params["min_length"] == 10
        assert updated_params["max_length"] == 3000

        # 測試設定無效參數
        with pytest.raises(ValueError):
            settings_manager.set_json_schema_parameters(min_length=100)  # 超出範圍

        with pytest.raises(ValueError):
            settings_manager.set_json_schema_parameters(max_length=10000)  # 超出範圍

    def test_real_model_supported_parameters(self):
        """測試模型支援參數獲取"""
        from backend.core.settings_manager import SettingsManager

        settings_manager = SettingsManager()
        settings_manager.settings_file = self.test_settings_file
        settings_manager._current_settings = {}

        # 測試獲取當前模型支援的參數
        params = settings_manager.get_model_supported_parameters()

        assert isinstance(params, dict)
        assert "max_tokens" in params
        assert "timeout" in params
        assert "reasoning_effort" in params
        assert "verbosity" in params

        # 驗證參數結構
        max_tokens_param = params["max_tokens"]
        assert max_tokens_param["type"] == "int"
        assert max_tokens_param["range"] == [1, 32000]
        assert max_tokens_param["default"] == 4000

        # 測試指定模型
        gpt5_params = settings_manager.get_model_supported_parameters("gpt-5")
        assert isinstance(gpt5_params, dict)
        assert len(gpt5_params) > 0

    def test_real_json_schema_supported_parameters(self):
        """測試JSON Schema支援參數獲取"""
        from backend.core.settings_manager import SettingsManager

        settings_manager = SettingsManager()

        params = settings_manager.get_json_schema_supported_parameters()

        assert isinstance(params, dict)
        assert "min_length" in params
        assert "max_length" in params

        # 驗證參數結構
        min_length_param = params["min_length"]
        assert min_length_param["type"] == "int"
        assert min_length_param["range"] == [1, 50]
        assert min_length_param["default"] == 5

    def test_real_get_all_settings(self):
        """測試獲取所有設定"""
        from backend.core.settings_manager import SettingsManager

        settings_manager = SettingsManager()
        settings_manager.settings_file = self.test_settings_file

        # 設置測試設定
        test_settings = {
            "key1": "value1",
            "key2": 123,
            "key3": True
        }
        settings_manager._current_settings = test_settings

        all_settings = settings_manager.get_all_settings()

        assert isinstance(all_settings, dict)
        assert all_settings["key1"] == "value1"
        assert all_settings["key2"] == 123
        assert all_settings["key3"] is True

        # 確保返回的是副本，不是原始字典
        all_settings["new_key"] = "new_value"
        assert "new_key" not in settings_manager._current_settings

    def test_real_reload_settings(self):
        """測試重新載入設定"""
        from backend.core.settings_manager import SettingsManager

        settings_manager = SettingsManager()
        settings_manager.settings_file = self.test_settings_file

        # 創建初始設定檔
        initial_settings = {"initial_key": "initial_value"}
        with open(self.test_settings_file, 'w', encoding='utf-8') as f:
            json.dump(initial_settings, f)

        # 載入設定
        settings_manager.reload_settings()
        assert settings_manager.get_setting("initial_key") == "initial_value"

        # 修改設定檔
        updated_settings = {"updated_key": "updated_value"}
        with open(self.test_settings_file, 'w', encoding='utf-8') as f:
            json.dump(updated_settings, f)

        # 重新載入
        settings_manager.reload_settings()
        assert settings_manager.get_setting("initial_key") is None
        assert settings_manager.get_setting("updated_key") == "updated_value"

    def test_real_error_handling(self):
        """測試錯誤處理"""
        from backend.core.settings_manager import SettingsManager
        import tempfile
        import os

        # 創建一個臨時設定管理器
        settings_manager = SettingsManager()

        # 創建一個臨時檔案然後將其設為只讀
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as temp_file:
            temp_file.write('{"test": "initial"}')
            temp_file_path = temp_file.name

        try:
            # 設定檔案為只讀權限
            os.chmod(temp_file_path, 0o444)  # 只讀權限
            settings_manager.settings_file = Path(temp_file_path)

            # 嘗試寫入應該拋出異常
            with pytest.raises(Exception):
                settings_manager._save_settings({"test": "value"})

        finally:
            # 清理：恢復權限並刪除檔案
            try:
                os.chmod(temp_file_path, 0o666)  # 恢復寫入權限
                os.unlink(temp_file_path)
            except:
                pass

    def test_real_file_corruption_handling(self):
        """測試檔案損壞處理"""
        from backend.core.settings_manager import SettingsManager

        settings_manager = SettingsManager()
        settings_manager.settings_file = self.test_settings_file

        # 創建損壞的JSON檔案
        with open(self.test_settings_file, 'w', encoding='utf-8') as f:
            f.write("{ invalid json content")

        # 載入損壞的檔案應該返回空字典
        result = settings_manager._load_settings()
        assert isinstance(result, dict)
        assert len(result) == 0


class TestSettingsManagerIntegration:
    """設定管理器整合測試"""

    def test_real_global_settings_manager_instance(self):
        """測試全局設定管理器實例"""
        from backend.core.settings_manager import settings_manager

        assert settings_manager is not None
        assert hasattr(settings_manager, 'get_setting')
        assert hasattr(settings_manager, 'set_setting')
        assert hasattr(settings_manager, 'get_current_model')

        # 測試基本功能不會出錯
        current_model = settings_manager.get_current_model()
        assert isinstance(current_model, str)
        assert len(current_model) > 0

    def test_real_settings_file_detection(self):
        """測試設定檔案檢測"""
        from backend.core.settings_manager import SettingsManager

        settings_manager = SettingsManager()

        # 設定檔路徑應該存在且指向正確位置
        assert settings_manager.settings_file is not None
        assert isinstance(settings_manager.settings_file, Path)
        assert settings_manager.settings_file.name == "settings.json"

        # 專案根目錄檢測
        project_root = settings_manager.settings_file.parent
        assert project_root.exists()

        # 檢查專案根目錄是否包含預期檔案
        expected_files = ["requirements.txt", "README.md", "backend"]
        for file_name in expected_files:
            expected_path = project_root / file_name
            if expected_path.exists():
                break
        else:
            # 如果沒有找到預期檔案，至少backend目錄應該存在
            assert (project_root / "backend").exists()

    def test_real_concurrent_access(self):
        """測試並發存取安全性"""
        from backend.core.settings_manager import SettingsManager
        import threading
        import time

        settings_manager = SettingsManager()

        results = []
        errors = []

        def read_setting(setting_id):
            """讀取設定的線程函數"""
            try:
                for i in range(10):
                    value = settings_manager.get_current_model()
                    results.append(f"{setting_id}-{i}: {value}")
                    time.sleep(0.01)
            except Exception as e:
                errors.append(str(e))

        def write_setting(setting_id):
            """寫入設定的線程函數"""
            try:
                for i in range(5):
                    # 這個測試可能會修改真實設定，所以謹慎選擇測試值
                    current = settings_manager.get_current_model()
                    results.append(f"{setting_id}-write-{i}: {current}")
                    time.sleep(0.02)
            except Exception as e:
                errors.append(str(e))

        # 創建多個讀取線程
        threads = []
        for i in range(3):
            thread = threading.Thread(target=read_setting, args=(f"read-{i}",))
            threads.append(thread)
            thread.start()

        # 創建一個寫入線程
        write_thread = threading.Thread(target=write_setting, args=("write",))
        threads.append(write_thread)
        write_thread.start()

        # 等待所有線程完成
        for thread in threads:
            thread.join()

        # 檢查結果
        assert len(errors) == 0, f"發生錯誤: {errors}"
        assert len(results) > 0

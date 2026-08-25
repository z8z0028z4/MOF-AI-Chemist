"""
環境管理模組測試
===============

測試 backend.core.env_manager 模組的所有功能
使用真實檔案操作，不使用 Mock
"""

import pytest
import os
import tempfile
import shutil
from pathlib import Path


class TestEnvManager:
    """測試環境管理器 - 真實測試"""

    def setup_method(self):
        """每個測試前的設置"""
        # 創建臨時目錄用於測試
        self.test_dir = Path(tempfile.mkdtemp())
        self.test_env_file = self.test_dir / ".env"

    def teardown_method(self):
        """每個測試後的清理"""
        # 清理臨時目錄
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_real_env_manager_initialization(self):
        """測試環境管理器初始化 - 真實測試"""
        from backend.core.env_manager import EnvManager

        # 創建新的環境管理器實例
        env_manager = EnvManager()

        assert env_manager is not None
        assert hasattr(env_manager, 'project_root')
        assert hasattr(env_manager, 'env_file')
        assert isinstance(env_manager.project_root, Path)
        assert isinstance(env_manager.env_file, Path)

    def test_real_read_env_file_empty(self):
        """測試讀取不存在的 .env 檔案"""
        from backend.core.env_manager import EnvManager

        # 創建測試環境管理器
        env_manager = EnvManager()
        # 暫時改變 env_file 路徑到測試目錄
        env_manager.env_file = self.test_env_file

        # 讀取不存在的檔案
        result = env_manager.read_env_file()

        assert isinstance(result, dict)
        assert len(result) == 0

    def test_real_read_env_file_with_content(self):
        """測試讀取包含內容的 .env 檔案"""
        from backend.core.env_manager import EnvManager

        # 創建測試 .env 檔案
        env_content = """# Test environment file
OPENAI_API_KEY=sk-test-key-123
APP_NAME="AI Research Assistant"
DEBUG=true
# Another comment
DATABASE_URL=postgresql://localhost:5432/test
"""

        with open(self.test_env_file, 'w', encoding='utf-8') as f:
            f.write(env_content)

        # 測試讀取
        env_manager = EnvManager()
        env_manager.env_file = self.test_env_file

        result = env_manager.read_env_file()

        assert isinstance(result, dict)
        assert len(result) == 4
        assert result["OPENAI_API_KEY"] == "sk-test-key-123"
        assert result["APP_NAME"] == "AI Research Assistant"
        assert result["DEBUG"] == "true"
        assert result["DATABASE_URL"] == "postgresql://localhost:5432/test"

    def test_real_write_env_file(self):
        """測試寫入 .env 檔案"""
        from backend.core.env_manager import EnvManager

        env_manager = EnvManager()
        env_manager.env_file = self.test_env_file

        # 測試寫入
        test_vars = {
            "API_KEY": "test-key",
            "APP_NAME": "Test App",
            "DEBUG": "false",
            "SPECIAL_VALUE": "value with spaces"
        }

        result = env_manager.write_env_file(test_vars)

        assert result is True
        assert self.test_env_file.exists()

        # 驗證檔案內容
        with open(self.test_env_file, 'r', encoding='utf-8') as f:
            content = f.read()

        assert "API_KEY=test-key" in content
        assert 'APP_NAME="Test App"' in content
        assert "DEBUG=false" in content
        assert 'SPECIAL_VALUE="value with spaces"' in content

    def test_real_update_env_variable(self):
        """測試更新環境變量"""
        from backend.core.env_manager import EnvManager

        env_manager = EnvManager()
        env_manager.env_file = self.test_env_file

        # 先創建初始檔案
        initial_vars = {
            "KEY1": "value1",
            "KEY2": "value2"
        }
        env_manager.write_env_file(initial_vars)

        # 更新變量
        result = env_manager.update_env_variable("KEY1", "updated_value")

        assert result is True

        # 驗證更新結果
        updated_vars = env_manager.read_env_file()
        assert updated_vars["KEY1"] == "updated_value"
        assert updated_vars["KEY2"] == "value2"  # 其他變量不變

    def test_real_get_env_variable(self):
        """測試獲取環境變量"""
        from backend.core.env_manager import EnvManager

        env_manager = EnvManager()
        env_manager.env_file = self.test_env_file

        # 創建測試檔案
        test_vars = {
            "TEST_KEY": "test_value",
            "ANOTHER_KEY": "another_value"
        }
        env_manager.write_env_file(test_vars)

        # 測試獲取存在的變量
        result = env_manager.get_env_variable("TEST_KEY")
        assert result == "test_value"

        # 測試獲取不存在的變量
        result = env_manager.get_env_variable("NON_EXISTENT_KEY")
        assert result is None

    def test_real_create_dummy_env_file(self):
        """測試創建 dummy .env 檔案"""
        from backend.core.env_manager import EnvManager

        env_manager = EnvManager()
        env_manager.env_file = self.test_env_file

        # 創建 dummy 檔案
        result = env_manager.create_dummy_env_file()

        assert result is True
        assert self.test_env_file.exists()

        # 驗證內容
        env_vars = env_manager.read_env_file()
        assert "OPENAI_API_KEY" in env_vars
        assert env_vars["OPENAI_API_KEY"] == "sk-dummy-key-placeholder"

    def test_real_get_env_file_status(self):
        """測試獲取 .env 檔案狀態"""
        from backend.core.env_manager import EnvManager

        env_manager = EnvManager()
        env_manager.env_file = self.test_env_file

        # 測試檔案不存在的狀態
        status = env_manager.get_env_file_status()

        assert isinstance(status, dict)
        assert "exists" in status
        assert "path" in status
        assert "openai_key_configured" in status
        assert status["exists"] is False
        assert status["openai_key_configured"] is False

        # 創建包含 dummy key 的檔案
        env_manager.create_dummy_env_file()

        status = env_manager.get_env_file_status()
        assert status["exists"] is True
        assert status["openai_key_configured"] is False  # dummy key 不算配置

        # 創建包含真實 key 的檔案
        env_manager.update_env_variable("OPENAI_API_KEY", "sk-real-key-123")

        status = env_manager.get_env_file_status()
        assert status["exists"] is True
        assert status["openai_key_configured"] is True

    def test_real_env_file_error_handling(self):
        """測試錯誤處理"""
        from backend.core.env_manager import EnvManager

        env_manager = EnvManager()

        # 測試寫入到無權限的目錄
        invalid_path = Path("/root/invalid_path/.env")  # 假設沒有權限
        env_manager.env_file = invalid_path

        # 寫入應該失敗但不崩潰
        result = env_manager.write_env_file({"KEY": "value"})
        # 結果可能是 True 或 False，取決於系統權限
        assert isinstance(result, bool)

    def test_real_env_file_special_characters(self):
        """測試特殊字符處理"""
        from backend.core.env_manager import EnvManager

        env_manager = EnvManager()
        env_manager.env_file = self.test_env_file

        # 測試包含特殊字符的值
        special_vars = {
            "VALUE_WITH_SPACES": "value with spaces",
            "VALUE_WITH_HASH": "value#with#hash",
            "VALUE_WITH_QUOTES": 'value"with"quotes',
            "SIMPLE_VALUE": "simple"
        }

        result = env_manager.write_env_file(special_vars)
        assert result is True

        # 讀取並驗證
        read_vars = env_manager.read_env_file()
        assert read_vars["VALUE_WITH_SPACES"] == "value with spaces"
        assert read_vars["VALUE_WITH_HASH"] == "value#with#hash"
        assert read_vars["VALUE_WITH_QUOTES"] == 'value"with"quotes'
        assert read_vars["SIMPLE_VALUE"] == "simple"


class TestEnvManagerIntegration:
    """環境管理器整合測試"""

    def test_real_global_env_manager_instance(self):
        """測試全局環境管理器實例"""
        from backend.core.env_manager import env_manager

        assert env_manager is not None
        assert hasattr(env_manager, 'read_env_file')
        assert hasattr(env_manager, 'write_env_file')
        assert hasattr(env_manager, 'get_env_file_status')

        # 測試狀態檢查不會出錯
        status = env_manager.get_env_file_status()
        assert isinstance(status, dict)
        assert "exists" in status
        assert "openai_key_configured" in status

    def test_real_project_root_detection(self):
        """測試專案根目錄檢測"""
        from backend.core.env_manager import EnvManager

        env_manager = EnvManager()

        # 專案根目錄應該存在且包含必要檔案
        assert env_manager.project_root.exists()
        assert env_manager.project_root.is_dir()

        # 檢查專案根目錄是否包含預期檔案
        expected_files = ["requirements.txt", "README.md", "backend"]
        for file_name in expected_files:
            expected_path = env_manager.project_root / file_name
            # 至少應該有一個檔案存在來確認這是正確的根目錄
            if expected_path.exists():
                break
        else:
            # 如果沒有找到任何預期檔案，檢查是否在正確的目錄結構中
            assert (env_manager.project_root / "backend").exists() or \
                   (env_manager.project_root / "tests").exists()

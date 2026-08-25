"""
AI Research Agent 測試套件
========================

這個測試套件包含：
1. 單元測試 - 測試個別函數和模組
2. 整合測試 - 測試模組間互動
3. 端到端測試 - 測試完整流程
4. 性能測試 - 測試系統性能

使用方法：
- 運行所有測試: pytest tests/
- 運行特定測試: pytest tests/test_embedding_service.py
- 生成覆蓋率報告: pytest --cov=backend tests/
"""

import os
import sys
from pathlib import Path

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

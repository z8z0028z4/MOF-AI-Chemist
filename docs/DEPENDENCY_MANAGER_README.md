# AI Research Assistant - 依賴管理器

## 概述

`dependency_manager.py` 是一個整合的依賴檢查和自動修復工具，用於管理 AI Research Assistant 的所有依賴。

## 功能

- ✅ **完整的依賴檢查**：檢查所有 Python 和前端依賴
- ✅ **自動修復**：自動安裝缺失的依賴
- ✅ **版本檢查**：顯示已安裝套件的版本
- ✅ **環境驗證**：檢查 Python 版本和 pip 可用性
- ✅ **前端支援**：檢查 Node.js、npm 和前端依賴
- ✅ **PyTorch 支援**：自動安裝 PyTorch（包含 CUDA 支援）

## 使用方法

### 1. 檢查依賴狀態

```bash
python dependency_manager.py
```

這會檢查所有依賴並顯示詳細報告。

### 2. 自動修復

當檢測到缺失依賴時，腳本會詢問是否要自動修復：

```
是否要自動修復缺失的依賴？(y/n): y
```

輸入 `y` 或 `yes` 開始自動修復。

## 檢查的依賴

### Python 依賴 (40 個)

**核心 AI 和 ML**
- langchain, langchain-openai, langchain-community, langchain-core
- langchain-huggingface, openai

**向量數據庫和嵌入**
- chromadb, sentence-transformers, transformers, tokenizers
- huggingface-hub, einops

**文檔處理**
- PyMuPDF, python-docx, openpyxl, PyYAML

**數據處理**
- pandas, scikit-learn, numpy, scipy

**Web 框架**
- streamlit, fastapi, uvicorn

**HTTP 和網絡**
- requests, certifi

**圖像處理**
- Pillow, svglib, reportlab

**Web 自動化**
- selenium

**環境和配置**
- python-dotenv, pydantic-settings

**進度追蹤**
- tqdm

**PyTorch**
- torch, torchaudio

**額外工具**
- urllib3, beautifulsoup4, lxml

**可選依賴**
- aiofiles, python-jose, passlib

### 前端依賴

**環境檢查**
- Node.js
- npm

**關鍵文件**
- package.json
- node_modules/.bin (包含 vite, eslint, tsc)
- vite.config.js

## 輸出範例

### 成功狀態

```
================================================================================
依賴檢查總結
================================================================================
[SUCCESS] 所有依賴都已準備就緒！
[OK] Python 依賴: 正常
[OK] 前端依賴: 正常

您現在可以運行 AI Research Assistant:
1. 啟動後端: 運行 restart_backend.bat
2. 啟動前端: 運行 start_react.bat
3. 或使用整合腳本: 運行 start_react.bat
```

### 需要修復

```
[WARN] 部分依賴缺失:
   - Python 依賴缺失: 3 個
   - 前端依賴問題: 1 個

是否要自動修復缺失的依賴？(y/n):
```

## 整合到其他腳本

`venv_setup.bat` 已經整合了依賴管理器，會在設置虛擬環境後自動運行依賴檢查。

## 注意事項

1. **虛擬環境**：建議在虛擬環境中運行此腳本
2. **權限**：某些操作可能需要管理員權限
3. **網絡**：自動修復需要網絡連接
4. **Node.js**：前端依賴檢查需要 Node.js 已安裝

## 故障排除

### 常見問題

1. **Python 版本過舊**
   - 需要 Python 3.10+
   - 從 https://python.org 下載最新版本

2. **Node.js 未安裝**
   - 從 https://nodejs.org 下載並安裝
   - 確保添加到 PATH

3. **pip 不可用**
   - 重新安裝 Python
   - 確保 pip 在 PATH 中

4. **權限錯誤**
   - 以管理員身份運行
   - 檢查目錄權限

### 手動修復

如果自動修復失敗，可以手動執行：

```bash
# 安裝 Python 依賴
pip install -r requirements.txt

# 安裝前端依賴
cd frontend
npm install
```

## 版本歷史

- **v1.0.0**: 初始版本，整合所有依賴檢查和修復功能

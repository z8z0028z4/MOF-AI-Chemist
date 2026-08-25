# Changelog

## [Embedding Model Improvement v3.2 - 2025-08-25]

### 🎉 重大更新：嵌入模型優化與系統修復

#### ✨ 新增功能
- **🔧 嵌入模型升級**：從 `BAAI/bge-small-zh-v1.5` 升級到 `BAAI/bge-base-en-v1.5`
  - 更高效的英文語義理解能力
  - 更好的跨語言檢索性能
  - CPU 友善的模型架構，降低資源消耗
  - 提升向量檢索的準確性和相關性
- **🛠️ 系統修復**：修復 `simple_setup.bat` 腳本問題
  - 改善虛擬環境設置流程
  - 優化依賴安裝過程
  - 提升安裝成功率

#### 🔧 技術改進
- **嵌入模型優化**：
  - 使用 `BAAI/bge-base-en-v1.5` 替代中文模型
  - 更好的英文學術文獻理解能力
  - 降低 CPU 使用率，提升處理效率
  - 改善向量檢索的語義相關性
- **安裝腳本修復**：
  - 修復 `simple_setup.bat` 中的路徑問題
  - 改善虛擬環境檢測邏輯
  - 優化錯誤處理機制

#### 🐛 修復
- 修復 `simple_setup.bat` 腳本執行問題
- 修復虛擬環境設置流程中的路徑錯誤
- 修復依賴安裝過程中的兼容性問題

#### 📦 依賴更新
- 更新嵌入模型配置到 `BAAI/bge-base-en-v1.5`
- 保持 ChromaDB 1.0.11 固定版本
- 優化 sentence-transformers 配置

#### 🚀 部署改進
- 改善 `simple_setup.bat` 的用戶體驗
- 優化安裝過程的錯誤提示
- 提升系統初始化的成功率


---

## [Model Selector Edition v3.1 - 2025-01-XX]

### 🎉 重大更新：模型選擇器系統 v1.0

#### ✨ 新增功能
- **模型選擇器系統 v1.0**：完整的模型選擇和管理功能
  - 支援 GPT-5、GPT-5-nano、GPT-5-mini 三種模型
  - 動態參數配置（max_tokens、timeout、reasoning_effort、verbosity）
  - 即時模型切換，無需重啟應用
  - 參數驗證和持久化設定
- **最新 Responses API + JSON Schema**：結構化輸出確保提案格式固定
  - 使用最新的 OpenAI Responses API
  - JSON Schema 結構化輸出，提高重現性和沿用性
  - 固定的提案格式，確保一致性
- **文獻查詢功能恢復**：重新啟用學術文獻搜尋
  - Europe PMC 整合
  - OpenAI API Key 管理功能
- 優雅啟動機制（支援無 .env 文件啟動）
  - 引用管理和追蹤
- **UI 功能調整**：多項使用者介面改進
  - 增強的側邊欄導航
  - 改進的頁面轉換效果
  - 更好的響應式設計

#### 🔧 技術改進
- **設定管理系統重構**：統一的設定管理架構
  - `backend/core/settings_manager.py` 集中化設定管理
  - `settings.json` 持久化設定儲存
  - 完整的設定管理 API
- **模型配置橋接**：`app/model_config_bridge.py` 連接前後端
  - 自動參數檢測和適配
  - 錯誤處理和 fallback 機制
  - 無縫的模型配置整合
- **依賴管理優化**：清理和更新依賴
  - 移除過時的安裝腳本
  - 更新 requirements.txt 到最新版本
  - 新增診斷工具

#### 🐛 修復
- 修復模型參數驗證問題
- 修復設定持久化問題
- 修復前端設定頁面顯示問題
- 修復文獻搜尋功能整合問題

#### 📦 依賴更新
- 更新 langchain 相關套件到最新版本
- 更新 FastAPI 和相關後端依賴
- 更新前端 React 依賴
- 新增模型參數檢測相關套件

#### 🚀 部署改進
- 簡化啟動腳本：`start_react.bat`
- 移除冗餘的啟動檔案
- 改進虛擬環境設置
- 新增跨平台支援

#### 📋 未來工作規劃
- **提高文章檢索能力**：改善 retriever 的檢索相關性
- **OSS-20B 本地 LLM**：更新和整合本地模型運行模組
- **選字反白高光偵測**：連動 LLM 進行解釋和修改
- **歷史對話功能**：增加對話歷史管理
- **Research Advisor 功能**：數據接收、顯示、AI 輔助分析
- **儀錶板功能**：啟動和改進儀錶板

---

## [React Version - 2024-01-XX]

### 🎉 重大更新：從 Streamlit 遷移到 React 前端

#### ✨ 新增功能
- **React 前端架構**：使用 React 18 + Vite + Ant Design
- **現代化 UI/UX**：響應式設計，流暢動畫，更好的用戶體驗
- **智能文本清理**：自動移除 markdown 格式，確保 DOCX 輸出乾淨
- **提案修訂功能**：支持基於用戶反饋的提案修訂
- **實驗細節生成**：獨立的實驗細節生成功能
- **DOCX 下載**：完整的 Word 文檔生成和下載
- **化學品查詢**：完整的化學品信息顯示和安全圖標

#### 🔧 技術改進
- **後端 API 重構**：使用 FastAPI 提供 RESTful API
- **模塊化架構**：組件化開發，更好的代碼組織
- **狀態管理**：使用 React Hooks 進行狀態管理
- **開發體驗**：熱重載，TypeScript 支持，ESLint 檢查
- **性能優化**：更快的加載速度和響應性

#### 🐛 修復
- 修復了 markdown 格式在 DOCX 中的顯示問題
- 修復了文本換行和寬度適配問題
- 修復了實驗細節生成的格式問題

#### 📦 依賴更新
- 新增 Node.js 16+ 依賴
- 新增 React 18 和相關前端依賴
- 更新 Python 依賴到最新穩定版本
- 新增 svglib 用於 SVG 到 PNG 轉換

#### 🚀 部署改進
- 跨平台虛擬環境設置：`venv_setup.bat`
- 跨平台啟動腳本：`start.py`
- Windows 專用啟動腳本：`run.bat`
- 自動依賴檢查和安裝
- 開發和生產環境配置

#### 📋 待實現功能
- 文獻助理頁面（RAG 模式選擇）
- 儀錶板功能恢復
- 文獻搜尋功能恢復
- 文件上傳處理
- 實驗顧問功能
- 數據顯示和比較
- 提案選擇器

---

## [Previous Versions]

### [0.1.0] - 2024-01-XX
- Initial Streamlit version
- Basic research proposal generation
- Chemical information lookup
- Document processing capabilities

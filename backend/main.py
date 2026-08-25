"""
AI Research Assistant Backend API
================================

FastAPI 後端服務，為 React 前端提供 API 接口
"""

import os
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
# Disable chromadb telemetry BEFORE any chromadb/langchain_chroma import
# to prevent posthog network connection hang in offline environments
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
os.environ.setdefault("CHROMA_TELEMETRY", "False")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import sys
import time
import logging
import threading
from dotenv import load_dotenv


# ----------------------------------------------------------------
# Get the specific logger that's causing the noise
telemetry_logger = logging.getLogger("chromadb.telemetry.product.posthog")

# Prevent its messages from propagating to the root logger
telemetry_logger.propagate = False

# Add a handler that does nothing (sends the logs to nowhere)
telemetry_logger.addHandler(logging.NullHandler())
# ----------------------------------------------------------------


# 添加原項目路徑到 sys.path (已重組，現在所有模組都在 backend 內)
# sys.path.append(os.path.join(os.path.dirname(__file__), '../app'))

# ==================== 啟動前 .env 檔案檢查 ====================
def check_and_create_env_file_before_startup():
    """
    在 FastAPI 應用啟動前檢查並創建 .env 檔案
    """
    try:
        # 獲取項目根目錄（backend 的父目錄）
        current_file = os.path.abspath(__file__)
        backend_dir = os.path.dirname(current_file)
        project_root = os.path.dirname(backend_dir)  # backend 的父目錄
        env_file = os.path.join(project_root, ".env")

        print(f"🔍 檢查 .env 檔案路徑: {env_file}")

        # 檢查 .env 檔案是否存在
        if not os.path.exists(env_file):
            print("📁 .env 檔案不存在，正在創建 dummy 檔案...")

            # 創建 dummy .env 檔案
            dummy_content = "OPENAI_API_KEY=sk-dummy-key-placeholder\n"

            try:
                with open(env_file, 'w', encoding='utf-8') as f:
                    f.write(dummy_content)
                print("✅ Dummy .env 檔案創建成功")
                print("💡 請在設定頁面配置真實的 API Key")
            except Exception as e:
                print(f"❌ 創建 dummy .env 檔案失敗: {e}")
        else:
            print("📁 .env 檔案已存在")

    except Exception as e:
        print(f"❌ 檢查 .env 檔案時發生錯誤: {e}")
        print("💡 系統將繼續啟動，但某些功能可能無法正常運作")

# 在載入環境變量前先檢查 .env 檔案
check_and_create_env_file_before_startup()

# 載入環境變量
load_dotenv()

# 過濾警告
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*LangChainDeprecationWarning.*")
warnings.filterwarnings("ignore", message=".*chromadb.telemetry.*")
warnings.filterwarnings("ignore", message=".*Failed to send telemetry event.*")
warnings.filterwarnings("ignore", message=".*capture.*takes 1 positional argument.*")

# 配置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 全局變量存儲向量統計信息
vector_stats_cache = {
    "paper_vectors": 0,
    "experiment_vectors": 0,
    "total_vectors": 0,
    "last_updated": None,
    "is_initialized": False
}

def initialize_vector_stats():
    """
    初始化向量統計信息
    在後端啟動時預先計算並緩存統計信息
    """
    global vector_stats_cache

    try:
        logger.info("🚀 開始初始化向量統計信息...")
        start_time = time.time()

        # 導入統計函數
        from backend.services.embedding_service import get_vectorstore_stats

        # 獲取論文和實驗向量統計
        paper_stats = get_vectorstore_stats("paper")
        experiment_stats = get_vectorstore_stats("experiment")

        # 提取統計數據
        paper_count = paper_stats.get("total_documents", 0) if isinstance(paper_stats, dict) else 0
        experiment_count = experiment_stats.get("total_documents", 0) if isinstance(experiment_stats, dict) else 0

        # 更新緩存
        vector_stats_cache.update({
            "paper_vectors": paper_count,
            "experiment_vectors": experiment_count,
            "total_vectors": paper_count + experiment_count,
            "last_updated": time.time(),
            "is_initialized": True
        })

        end_time = time.time()
        logger.info(f"✅ 向量統計初始化完成，耗時: {end_time - start_time:.2f}秒")
        logger.info(f"📊 統計結果 - 論文: {paper_count}, 實驗: {experiment_count}, 總計: {paper_count + experiment_count}")

    except Exception as e:
        logger.error(f"❌ 向量統計初始化失敗: {e}")
        # 設置默認值
        vector_stats_cache.update({
            "paper_vectors": 0,
            "experiment_vectors": 0,
            "total_vectors": 0,
            "last_updated": time.time(),
            "is_initialized": True
        })

def get_cached_vector_stats():
    """
    獲取緩存的向量統計信息
    """
    return vector_stats_cache

def update_vector_stats_cache():
    """
    更新向量統計緩存
    在文件處理完成後調用此函數
    """
    global vector_stats_cache

    try:
        logger.info("🔄 開始更新向量統計緩存...")
        from backend.services.embedding_service import get_vectorstore_stats

        paper_stats = get_vectorstore_stats("paper")
        experiment_stats = get_vectorstore_stats("experiment")

        paper_count = paper_stats.get("total_documents", 0) if isinstance(paper_stats, dict) else 0
        experiment_count = experiment_stats.get("total_documents", 0) if isinstance(experiment_stats, dict) else 0

        vector_stats_cache.update({
            "paper_vectors": paper_count,
            "experiment_vectors": experiment_count,
            "total_vectors": paper_count + experiment_count,
            "last_updated": time.time()
        })

        logger.info(f"✅ 向量統計緩存更新完成 - 論文: {paper_count}, 實驗: {experiment_count}, 總計: {paper_count + experiment_count}")

    except Exception as e:
        logger.error(f"❌ 更新向量統計緩存失敗: {e}")

# 創建 FastAPI 應用
app = FastAPI(
    title="AI Research Assistant API",
    description="AI 研究助理後端 API 服務",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React 開發服務器
        "http://localhost:5173",  # Vite 開發服務器
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 掛載靜態文件
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# 導入路由
from backend.api.routes import routers

# 註冊路由
for router in routers:
    app.include_router(router, prefix="/api/v1")

@app.on_event("startup")
async def startup_event():
    """
    應用啟動時的事件處理
    """
    logger.info("🚀 AI Research Assistant 後端服務啟動中...")

    # 初始化向量統計信息。這會載入 embedding/vector store，不能阻塞 API 啟動或 TestClient。
    if os.getenv("PYTEST_CURRENT_TEST"):
        vector_stats_cache["is_initialized"] = True
        logger.info("🧪 測試環境略過向量統計背景初始化")
    else:
        stats_thread = threading.Thread(target=initialize_vector_stats, daemon=True)
        stats_thread.start()

    logger.info("✅ 後端服務啟動完成")

@app.get("/")
async def root():
    """根路徑，返回 API 信息"""
    return {
        "message": "AI Research Assistant API",
        "version": "1.0.0",
        "docs": "/api/docs",
        "vector_stats_initialized": vector_stats_cache["is_initialized"]
    }

@app.get("/health")
async def health_check():
    """健康檢查端點"""
    return {
        "status": "healthy",
        "service": "ai-research-assistant",
        "vector_stats_initialized": vector_stats_cache["is_initialized"]
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

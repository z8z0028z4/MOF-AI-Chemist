"""
測試配置和 Fixtures
==================

提供測試環境的基礎配置和通用 fixtures
"""

import os
import sys
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 測試環境配置
os.environ["TESTING"] = "true"
# 移除錯誤的 API key 設置，讓測試使用真實配置
# os.environ["OPENAI_API_KEY"] = "test_key"
# os.environ["OPENAI_MODEL"] = "gpt-4o-mini"


@pytest.fixture(scope="session")
def test_environment():
    """設置測試環境"""
    # 設置測試目錄
    test_data_dir = project_root / "tests" / "test_data"
    test_data_dir.mkdir(exist_ok=True)

    # 設置測試向量存儲路徑
    test_vector_dir = project_root / "tests" / "test_vectors"
    test_vector_dir.mkdir(exist_ok=True)

    yield {
        "test_data_dir": test_data_dir,
        "test_vector_dir": test_vector_dir,
        "project_root": project_root
    }

    # 清理測試數據
    import shutil
    if test_data_dir.exists():
        shutil.rmtree(test_data_dir)
    if test_vector_dir.exists():
        shutil.rmtree(test_vector_dir)


@pytest.fixture
def mock_openai_api():
    """Mock OpenAI API"""
    with patch('openai.OpenAI') as mock_client:
        mock_response = Mock()
        mock_response.content = "這是一個測試回應"
        mock_response.choices = [Mock(message=Mock(content="這是一個測試回應"))]
        mock_response.model_dump.return_value = {
            "choices": [{"message": {"content": "這是一個測試回應", "role": "assistant"}}]
        }

        # 為結構化回應創建不同的 Mock
        mock_structured_response = Mock()
        mock_structured_response.content = '{"title": "測試標題", "content": "測試內容"}'
        mock_structured_response.choices = [Mock(message=Mock(content='{"title": "測試標題", "content": "測試內容"}'))]
        mock_structured_response.model_dump.return_value = {
            "choices": [{"message": {"content": '{"title": "測試標題", "content": "測試內容"}', "role": "assistant"}}]
        }

        # 根據調用次數返回不同的回應
        def side_effect(*args, **kwargs):
            if "JSON" in str(args) or "schema" in str(args):
                return mock_structured_response
            return mock_response

        mock_client.return_value.chat.completions.create.side_effect = side_effect

        mock_client.return_value.chat.completions.create.return_value = mock_response
        mock_client.return_value.responses.create.return_value = Mock(
            choices=[Mock(message=Mock(content="這是一個測試回應"))]
        )

        yield mock_client


@pytest.fixture
def mock_chroma_client():
    """Mock ChromaDB 客戶端"""
    with patch('chromadb.PersistentClient') as mock_client:
        mock_collection = Mock()
        mock_collection.count.return_value = 100
        mock_collection.get.return_value = {
            "documents": ["測試文檔1", "測試文檔2"],
            "metadatas": [{"source": "test1.pdf"}, {"source": "test2.pdf"}],
            "embeddings": [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        }

        mock_client.return_value.get_or_create_collection.return_value = mock_collection
        yield mock_client


@pytest.fixture
def sample_pdf_file(test_environment):
    """創建測試用的 PDF 文件"""
    pdf_path = test_environment["test_data_dir"] / "test.pdf"

    # 創建一個簡單的測試 PDF
    try:
        from reportlab.pdfgen import canvas
        c = canvas.Canvas(str(pdf_path))
        c.drawString(100, 750, "這是一個測試 PDF 文件")
        c.drawString(100, 700, "包含一些測試內容")
        c.save()
    except ImportError:
        # 如果沒有 reportlab，創建一個空文件
        pdf_path.write_text("PDF content placeholder")

    yield str(pdf_path)

    # 清理
    if pdf_path.exists():
        pdf_path.unlink()


@pytest.fixture
def sample_excel_file(test_environment):
    """創建測試用的 Excel 文件"""
    excel_path = test_environment["test_data_dir"] / "test.xlsx"

    try:
        import pandas as pd
        df = pd.DataFrame({
            "實驗ID": ["EXP001", "EXP002"],
            "實驗名稱": ["測試實驗1", "測試實驗2"],
            "描述": ["這是第一個測試實驗", "這是第二個測試實驗"]
        })
        df.to_excel(excel_path, index=False)
    except ImportError:
        # 如果沒有 pandas，創建一個簡單的 CSV
        csv_path = excel_path.with_suffix('.csv')
        csv_path.write_text("實驗ID,實驗名稱,描述\nEXP001,測試實驗1,這是第一個測試實驗\n")
        excel_path = csv_path

    yield str(excel_path)

    # 清理
    if excel_path.exists():
        excel_path.unlink()


@pytest.fixture
def mock_settings():
    """Mock 設置"""
    with patch('backend.core.config.settings') as mock_settings:
        mock_settings.openai_api_key = "test_key"
        mock_settings.openai_model = "gpt-5-nano"
        mock_settings.openai_max_tokens = 2000
        mock_settings.app_name = "AI Research Agent Test"
        mock_settings.debug = True
        yield mock_settings


@pytest.fixture
def test_vectorstore():
    """創建測試用的向量存儲"""
    with patch('backend.core.vector_store.get_chroma_instance') as mock_get_instance:
        mock_collection = Mock()
        mock_collection.count.return_value = 100
        mock_collection.get.return_value = {
            "documents": ["測試文檔1", "測試文檔2", "測試文檔3"],
            "metadatas": [
                {"source": "test1.pdf", "page": 1},
                {"source": "test2.pdf", "page": 2},
                {"source": "test3.pdf", "page": 3}
            ],
            "embeddings": [
                [0.1, 0.2, 0.3],
                [0.4, 0.5, 0.6],
                [0.7, 0.8, 0.9]
            ]
        }

        # Mock 檢索器
        mock_retriever = Mock()
        from langchain_core.documents import Document
        mock_retriever.get_relevant_documents.return_value = [
            Document(page_content="測試文檔內容1", metadata={"source": "test1.pdf"}),
            Document(page_content="測試文檔內容2", metadata={"source": "test2.pdf"})
        ]

        mock_vectorstore = Mock()
        mock_vectorstore._collection = mock_collection
        mock_vectorstore.as_retriever.return_value = mock_retriever
        mock_vectorstore.similarity_search.return_value = [
            Document(page_content="測試文檔內容1", metadata={"source": "test1.pdf"}),
            Document(page_content="測試文檔內容2", metadata={"source": "test2.pdf"})
        ]

        mock_get_instance.return_value = mock_vectorstore
        yield mock_vectorstore


@pytest.fixture
def mock_llm_manager():
    """Mock LLM 管理器"""
    with patch('backend.core.llm_manager.LLMManager') as mock_manager:
        mock_instance = Mock()
        mock_instance.generate_response.return_value = "這是一個測試 LLM 回應"
        mock_instance.generate_structured_response.return_value = {
            "title": "測試提案",
            "content": "這是一個測試研究提案",
            "citations": ["ref1", "ref2"]
        }
        mock_manager.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_embedding_model():
    """Mock 嵌入模型"""
    with patch('sentence_transformers.SentenceTransformer') as mock_model:
        mock_instance = Mock()
        mock_instance.encode.return_value = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        mock_model.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def sample_chunks():
    """提供測試用的文檔塊"""
    from langchain_core.documents import Document
    return [
        Document(
            page_content="這是第一個文檔塊的內容，包含一些研究信息。",
            metadata={"source": "paper1.pdf", "page": 1}
        ),
        Document(
            page_content="這是第二個文檔塊的內容，包含實驗方法。",
            metadata={"source": "paper2.pdf", "page": 2}
        ),
        Document(
            page_content="這是第三個文檔塊的內容，包含結果分析。",
            metadata={"source": "paper3.pdf", "page": 3}
        )
    ]


@pytest.fixture
def sample_schema():
    """提供測試用的 JSON Schema"""
    return {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "content": {"type": "string"},
            "citations": {"type": "array", "items": {"type": "string"}}
        },
        "required": ["title", "content"]
    }


@pytest.fixture
def mock_file_upload():
    """Mock 文件上傳"""
    return {
        "filename": "test.pdf",
        "content": b"PDF content",
        "size": 1024,
        "content_type": "application/pdf"
    }


@pytest.fixture
def mock_api_response():
    """Mock API 回應"""
    return {
        "status": "success",
        "data": {"task_id": "test_task_123"},
        "message": "操作成功"
    }


# 測試工具函數
def create_test_file(file_path: Path, content: str = "測試內容"):
    """創建測試文件"""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding='utf-8')


def cleanup_test_files(*file_paths):
    """清理測試文件"""
    for file_path in file_paths:
        if isinstance(file_path, str):
            file_path = Path(file_path)
        if file_path.exists():
            file_path.unlink()


def assert_response_structure(response, expected_keys):
    """斷言回應結構"""
    assert isinstance(response, dict), "回應應該是字典格式"
    for key in expected_keys:
        assert key in response, f"回應中應該包含鍵 '{key}'"


def assert_error_response(response, error_type=None):
    """斷言錯誤回應"""
    assert "error" in response or "status" in response, "錯誤回應應該包含 error 或 status 字段"
    if error_type:
        assert response.get("error_type") == error_type or response.get("status") == "error"


@pytest.fixture
def client():
    """FastAPI test client fixture for data analyzer tests."""
    from fastapi.testclient import TestClient
    from backend.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def tga_parser():
    """TGA analyzer fixture for testing."""
    from backend.services.analysis.tga_analysis import create_tga_analyzer
    return create_tga_analyzer()


@pytest.fixture
def bet_parser():
    """BET analyzer fixture for testing."""
    from backend.services.analysis.bet_analysis import create_bet_analyzer
    return create_bet_analyzer()


@pytest.fixture
def demo_stage(monkeypatch):
    """Sets the 4 per-stage DEMO_MODE env overrides and resets test state.

    Usage:
        def test_something(demo_stage):
            demo_stage("proposal")                       # turn ON just this stage
            demo_stage("proposal", "experiment_detail")   # turn ON multiple stages
            demo_stage()                                  # explicitly turn ALL stages OFF

    Reused across TODO 13.0 cards (b)/(c)/(e) so those cards don't duplicate this
    setup. Explicit false overrides keep tests isolated from persisted settings.
    """
    from backend.core import demo_config

    stage_env_vars = {
        "proposal": "DEMO_MOCK_PROPOSAL",
        "generate_new_idea": "DEMO_MOCK_GENERATE_NEW_IDEA",
        "property_prediction": "DEMO_MOCK_PROPERTY_PREDICTION",
        "experiment_detail": "DEMO_MOCK_EXPERIMENT_DETAIL",
    }

    def _set(*stages):
        for var in stage_env_vars.values():
            monkeypatch.setenv(var, "false")
        for stage in stages:
            monkeypatch.setenv(stage_env_vars[stage], "true")
        demo_config.reset_cache_for_tests()

    _set()
    yield _set

    demo_config.reset_cache_for_tests()

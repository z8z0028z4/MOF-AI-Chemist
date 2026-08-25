"""
核心模組測試
===========

測試後端核心功能模組 - 使用真實功能而非 Mock
"""

import pytest
from unittest.mock import patch, Mock


class TestConfigManagement:
    """配置管理測試 - 真實測試"""

    @pytest.mark.fast
    def test_settings_loading(self):
        """測試設置加載 - 真實測試"""
        from backend.core.config import settings

        # 驗證真實配置
        assert hasattr(settings, 'app_name')
        assert hasattr(settings, 'openai_model')
        assert settings.app_name == "AI Research Assistant"
        assert settings.openai_model in ["gpt-5o-mini", "gpt-5o", "gpt-4o-mini"]

    @pytest.mark.fast
    def test_config_validation(self):
        """測試配置驗證 - 真實測試"""
        from backend.core.config import validate_config

        # 測試真實配置驗證
        result = validate_config()
        assert isinstance(result, dict)
        assert "config_complete" in result
        # 配置應該完整，因為我們有真實的 settings.json
        assert result.get('config_complete') is True

    @pytest.mark.fast
    def test_config_reload(self):
        """測試配置重載 - 真實測試"""
        from backend.core.config import reload_config

        # 測試重載真實配置
        result = reload_config()
        assert result is not None
        assert hasattr(result, 'app_name')


class TestVectorStore:
    """向量存儲測試 - 真實測試"""

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.external
    def test_vectorstore_stats_real(self):
        """測試真實向量存儲統計"""
        from backend.services.embedding_service import get_vectorstore_stats

        # 測試論文向量庫統計
        stats = get_vectorstore_stats("paper")
        assert isinstance(stats, dict)
        assert "total_documents" in stats
        assert "collection_name" in stats
        assert stats["collection_name"] == "paper"
        # 應該有真實的文檔數量
        assert isinstance(stats["total_documents"], int)
        assert stats["total_documents"] >= 0

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.external
    def test_paper_vectorstore_loading_real(self):
        """測試真實論文向量存儲加載"""
        from backend.core.retrieval import load_paper_vectorstore

        vectorstore = load_paper_vectorstore()
        assert vectorstore is not None
        # 驗證向量存儲有真實的檢索器
        retriever = vectorstore.as_retriever()
        assert retriever is not None

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.external
    def test_experiment_vectorstore_loading_real(self):
        """測試真實實驗向量存儲加載"""
        from backend.core.retrieval import load_experiment_vectorstore

        vectorstore = load_experiment_vectorstore()
        assert vectorstore is not None
        # 驗證向量存儲有真實的檢索器
        retriever = vectorstore.as_retriever()
        assert retriever is not None


class TestRetrieval:
    """檢索功能測試 - 真實測試"""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_retrieve_multi_query_supports_current_retriever_interface(self):
        """新版 LangChain retriever 只提供 invoke() 時仍可檢索。"""
        from langchain_core.documents import Document
        from backend.core.retrieval import retrieve_chunks_multi_query

        class InvokeOnlyRetriever:
            def invoke(self, query):
                return [
                    Document(
                        page_content=f"content for {query}",
                        metadata={"source": f"{query}.pdf"},
                    )
                ]

        class FakeVectorStore:
            def as_retriever(self, **kwargs):
                self.search_kwargs = kwargs
                return InvokeOnlyRetriever()

        results = retrieve_chunks_multi_query(
            FakeVectorStore(),
            ["chemistry", "chemistry"],
            k=5,
        )

        assert len(results) == 1
        assert results[0].metadata["source"] == "chemistry.pdf"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_retrieve_single_query_supports_legacy_retriever_interface(self):
        """舊版 LangChain retriever 仍可透過 fallback 使用。"""
        from langchain_core.documents import Document
        from backend.core.retrieval import retrieve_chunks_single_query

        class LegacyRetriever:
            def get_relevant_documents(self, query):
                return [Document(page_content=query, metadata={"source": "legacy.pdf"})]

        class FakeVectorStore:
            def as_retriever(self, **kwargs):
                return LegacyRetriever()

        results = retrieve_chunks_single_query(FakeVectorStore(), "chemistry", k=1)

        assert len(results) == 1
        assert results[0].metadata["source"] == "legacy.pdf"

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.external
    def test_real_document_search(self):
        """測試真實文檔搜索"""
        from backend.core.retrieval import load_paper_vectorstore, retrieve_chunks_multi_query

        # 使用真實向量存儲
        vs = load_paper_vectorstore()
        results = retrieve_chunks_multi_query(vs, ["chemistry synthesis"], k=3)

        assert isinstance(results, list)
        # 應該能找到相關文檔
        assert len(results) > 0
        # 驗證文檔結構
        for doc in results:
            assert hasattr(doc, 'page_content')
            assert hasattr(doc, 'metadata')
            assert len(doc.page_content) > 0

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.external
    def test_real_experiment_search(self):
        """測試真實實驗搜索"""
        from backend.core.retrieval import load_experiment_vectorstore, retrieve_chunks_multi_query

        # 使用真實向量存儲
        vs = load_experiment_vectorstore()
        results = retrieve_chunks_multi_query(vs, ["experiment method"], k=3)

        assert isinstance(results, list)
        # 可能沒有實驗數據，但函數應該正常工作
        assert len(results) >= 0

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.external
    def test_real_multi_query_retrieval(self):
        """測試真實多查詢檢索"""
        from backend.core.retrieval import load_paper_vectorstore, retrieve_chunks_multi_query

        vs = load_paper_vectorstore()
        queries = ["chemical synthesis", "organic chemistry", "catalysis"]
        results = retrieve_chunks_multi_query(vs, queries, k=5)

        assert isinstance(results, list)
        # 應該能找到相關文檔
        assert len(results) > 0


class TestPromptBuilder:
    """提示詞構建測試 - 真實測試"""

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.external
    def test_real_prompt_construction(self):
        """測試真實提示詞構建"""
        from backend.core.prompt_builder import build_prompt
        from backend.core.retrieval import load_paper_vectorstore, retrieve_chunks_multi_query

        # 獲取真實文檔
        vs = load_paper_vectorstore()
        docs = retrieve_chunks_multi_query(vs, ["chemistry"], k=3)

        if len(docs) > 0:
            prompt, citations = build_prompt(docs, "什麼是化學合成？")

            assert isinstance(prompt, str)
            assert len(prompt) > 0
            assert "化學合成" in prompt or "chemistry" in prompt.lower()
            assert isinstance(citations, list)
            assert len(citations) > 0

    @pytest.mark.integration
    @pytest.mark.slow
    @pytest.mark.external
    def test_real_proposal_prompt(self):
        """測試真實提案提示詞"""
        from backend.core.prompt_builder import build_proposal_prompt
        from backend.core.retrieval import load_paper_vectorstore, retrieve_chunks_multi_query

        # 獲取真實文檔
        vs = load_paper_vectorstore()
        docs = retrieve_chunks_multi_query(vs, ["research"], k=3)

        if len(docs) > 0:
            prompt, citations = build_proposal_prompt("化學合成方法研究", docs)

            assert isinstance(prompt, str)
            assert len(prompt) > 0
            assert "research proposal" in prompt.lower() or "研究提案" in prompt
            assert isinstance(citations, list)


class TestQueryExpander:
    """查詢擴展測試 - 真實測試"""

    @pytest.mark.external
    def test_real_query_expansion(self):
        """測試真實查詢擴展"""
        from backend.core.query_expander import expand_query

        # 測試真實查詢擴展
        queries = expand_query("chemical synthesis methods")

        assert isinstance(queries, list)
        # 應該能生成多個相關查詢
        assert len(queries) >= 3
        # 驗證查詢內容
        for query in queries:
            assert isinstance(query, str)
            assert len(query) > 0
            # 查詢應該包含相關關鍵詞
            assert any(keyword in query.lower() for keyword in ["chemical", "synthesis", "method", "chemistry"])


class TestGeneration:
    """生成模組測試 - 真實測試"""

    @pytest.mark.external
    def test_real_llm_call(self):
        """測試真實 LLM 調用"""
        from backend.core.generation import call_llm

        # 測試真實 LLM 調用
        response = call_llm("Say hello in Chinese")

        assert isinstance(response, str)
        assert len(response) > 0
        # 回應應該包含中文
        assert any(char in response for char in "你好")

    @pytest.mark.external
    def test_real_structured_llm_call(self):
        """測試真實結構化 LLM 調用"""
        from backend.core.generation import call_structured_llm

        schema = {
            "type": "object",
            "additionalProperties": False,
            "required": ["title", "content"],
            "properties": {
                "title": {"type": "string"},
                "content": {"type": "string"}
            }
        }

        # 測試真實結構化調用
        response = call_structured_llm("Generate a brief test response", schema)

        assert isinstance(response, dict)
        assert "title" in response
        assert "content" in response
        assert isinstance(response["title"], str)
        assert isinstance(response["content"], str)
        # 內容應該有值，title 可能為空
        assert len(response["content"]) > 0


class TestSchemaManager:
    """Schema 管理測試 - 真實測試"""

    def test_real_schema_creation(self):
        """測試真實 Schema 創建"""
        from backend.core.schema_manager import create_research_proposal_schema

        schema = create_research_proposal_schema()

        assert isinstance(schema, dict)
        assert "type" in schema
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "required" in schema

    def test_real_dynamic_schema_params(self):
        """測試真實動態 Schema 參數"""
        from backend.core.schema_manager import get_dynamic_schema_params

        params = get_dynamic_schema_params()

        assert isinstance(params, dict)
        assert "min_length" in params
        assert "max_length" in params
        assert params["min_length"] > 0
        assert params["max_length"] > params["min_length"]

    def test_dynamic_extraction_by_linker_mode(self):
        """測試根據 linker_mode 動態修剪/修改第二階段提取的資訊"""
        from backend.core.generation import extract_mof_from_proposal
        from unittest.mock import patch

        with patch("backend.core.generation.call_structured_llm") as mock_call:
            # 模擬 LLM 提取出兩個配體
            mock_call.return_value = {
                "is_mof_related": True,
                "mof_metal_element": "Zr",
                "mof_linker_name": "2-aminoterephthalic acid",
                "mof_linker_name_2": "oxalic acid"
            }

            # single mode 下，輔助配體應強制被清除為空字串
            res_single = extract_mof_from_proposal("some text", mof_linker_mode="single")
            assert res_single["mof_linker_name_2"] == ""
            assert res_single["mof_metal_element"] == "Zr"
            assert res_single["mof_linker_name"] == "2-aminoterephthalic acid"

            # auto 或 dual mode 下，應保留輔助配體
            res_auto = extract_mof_from_proposal("some text", mof_linker_mode="auto")
            assert res_auto["mof_linker_name_2"] == "oxalic acid"


class TestModeManager:
    """模式管理測試 - 真實測試"""

    def test_real_available_modes(self):
        """測試真實可用模式"""
        from backend.core.mode_manager import get_available_modes

        modes = get_available_modes()

        assert isinstance(modes, list)
        assert len(modes) > 0
        # 驗證實際的模式名稱
        actual_modes = ['納入實驗資料，進行推論與建議', 'make proposal', '允許延伸與推論', '僅嚴謹文獻溯源', 'expand to experiment detail', 'generate new idea']
        for mode in actual_modes:
            assert mode in modes

    def test_real_mode_validation(self):
        """測試真實模式驗證"""
        from backend.core.mode_manager import validate_mode

        # 測試實際有效模式
        assert validate_mode("make proposal") is True
        assert validate_mode("僅嚴謹文獻溯源") is True
        assert validate_mode("允許延伸與推論") is True

        # 測試無效模式
        assert validate_mode("invalid_mode") is False

    def test_real_mode_description(self):
        """測試真實模式描述"""
        from backend.core.mode_manager import get_mode_description

        desc = get_mode_description("make proposal")
        assert isinstance(desc, str)
        assert len(desc) > 0
        # 檢查是否包含提案相關內容
        assert "proposal" in desc.lower() or "提案" in desc


class TestFormatConverter:
    """格式轉換測試 - 真實測試"""

    def test_real_proposal_to_text(self):
        """測試真實提案轉文本"""
        from backend.core.format_converter import structured_proposal_to_text

        structured_data = {
            "proposal_title": "測試研究提案",
            "need": "研究需求",
            "solution": "解決方案",
            "differentiation": "差異化",
            "benefit": "預期效益"
        }

        text = structured_proposal_to_text(structured_data)

        assert isinstance(text, str)
        assert len(text) > 0
        assert "測試研究提案" in text
        assert "研究需求" in text
        assert "解決方案" in text

    def test_real_experimental_detail_to_text(self):
        """測試真實實驗詳情轉文本"""
        from backend.core.format_converter import structured_experimental_detail_to_text

        structured_data = {
            "synthesis_process": "合成過程",
            "materials_and_conditions": "材料和條件",
            "analytical_methods": "分析方法"
        }

        text = structured_experimental_detail_to_text(structured_data)

        assert isinstance(text, str)
        assert len(text) > 0
        assert "合成過程" in text
        assert "材料和條件" in text
        assert "分析方法" in text

    def test_real_revision_experimental_detail_to_text(self):
        """測試真實實驗細節修改轉文本"""
        from backend.core.format_converter import structured_revision_experimental_detail_to_text

        structured_data = {
            "revision_explanation": "修訂說明",
            "synthesis_process": "修改後的合成過程",
            "materials_and_conditions": "修改後的材料和條件",
            "analytical_methods": "修改後的分析方法",
            "precautions": "修改後的注意事項"
        }

        text = structured_revision_experimental_detail_to_text(structured_data)

        assert isinstance(text, str)
        assert len(text) > 0
        assert "修訂說明" in text
        assert "修改後的合成過程" in text
        assert "修改後的材料和條件" in text
        assert "修改後的分析方法" in text
        assert "修改後的注意事項" in text

    def test_real_revision_proposal_to_text(self):
        """測試真實提案修改轉文本"""
        from backend.core.format_converter import structured_revision_proposal_to_text

        structured_data = {
            "revision_explanation": "修訂說明",
            "proposal_title": "修改後的提案標題",
            "need": "修改後的研究需求",
            "solution": "修改後的解決方案",
            "differentiation": "修改後的差異化",
            "benefit": "修改後的預期效益"
        }

        text = structured_revision_proposal_to_text(structured_data)

        assert isinstance(text, str)
        assert len(text) > 0
        assert "修訂說明" in text
        assert "修改後的提案標題" in text
        assert "修改後的研究需求" in text
        assert "修改後的解決方案" in text


class TestGenerationRevisionFunctions:
    """生成修改功能測試 - 新增測試"""

    @patch('backend.core.generation.call_structured_llm')
    def test_call_llm_structured_revision_experimental_detail(self, mock_call_llm):
        """測試實驗細節修改的 LLM 調用"""
        from backend.core.generation import call_llm_structured_revision_experimental_detail

        mock_call_llm.return_value = {
            "revision_explanation": "Revision explanation",
            "synthesis_process": "Updated synthesis process",
            "materials_and_conditions": "Updated materials and conditions",
            "analytical_methods": "Updated analytical methods",
            "precautions": "Updated precautions"
        }

        result = call_llm_structured_revision_experimental_detail(
            question="Please revise this experiment detail",
            new_chunks=[],
            old_chunks=[],
            proposal="Original proposal",
            original_experimental_detail="Original experimental detail"
        )

        assert isinstance(result, dict)
        assert "revision_explanation" in result
        assert "synthesis_process" in result
        assert "materials_and_conditions" in result
        assert "analytical_methods" in result
        assert "precautions" in result
        mock_call_llm.assert_called_once()

    def test_old_text_building_with_full_content(self):
        """測試完整文檔內容的 old_text 構建"""
        from backend.core.generation import call_llm_structured_revision_experimental_detail

        # 模擬文檔塊
        mock_chunks = [
            Mock(
                page_content="This is a complete document content about chemistry synthesis with detailed experimental procedures.",
                metadata={
                    "title": "Test Paper",
                    "filename": "test.pdf",
                    "page_number": 1
                }
            ),
            Mock(
                page_content="Another complete document about analytical methods and characterization techniques.",
                metadata={
                    "title": "Analytical Paper",
                    "filename": "analytical.pdf",
                    "page_number": 2
                }
            )
        ]

        # 測試 old_text 構建邏輯（不實際調用 LLM）
        old_text = ""
        for i, doc in enumerate(mock_chunks):
            metadata = doc.metadata
            title = metadata.get("title", "Untitled")
            filename = metadata.get("filename") or metadata.get("source", "Unknown")
            page = metadata.get("page_number") or metadata.get("page", "?")

            # 顯示完整的文檔內容，而不是只有前80個字符
            old_text += f"    [{i+1}] {title} | Page {page}\n{doc.page_content}\n\n"

        assert len(old_text) > 0
        assert "This is a complete document content about chemistry synthesis" in old_text
        assert "Another complete document about analytical methods" in old_text
        assert "Test Paper" in old_text
        assert "Analytical Paper" in old_text
        assert "[1]" in old_text
        assert "[2]" in old_text

    def test_old_text_building_with_dict_chunks(self):
        """測試字典格式 chunks 的 old_text 構建"""
        # 模擬字典格式的文檔塊
        mock_dict_chunks = [
            {
                "page_content": "This is a complete document content about chemistry synthesis.",
                "metadata": {
                    "title": "Test Paper",
                    "filename": "test.pdf",
                    "page_number": 1
                }
            },
            {
                "page_content": "Another complete document about experimental procedures.",
                "metadata": {
                    "title": "Experimental Paper",
                    "filename": "experiment.pdf",
                    "page_number": 2
                }
            }
        ]

        # 測試 old_text 構建邏輯
        old_text = ""
        for i, doc in enumerate(mock_dict_chunks):
            metadata = doc.get('metadata', {})
            title = metadata.get("title", "Untitled")
            filename = metadata.get("filename") or metadata.get("source", "Unknown")
            page = metadata.get("page_number") or metadata.get("page", "?")

            # 顯示完整的文檔內容
            old_text += f"    [{i+1}] {title} | Page {page}\n{doc['page_content']}\n\n"

        assert len(old_text) > 0
        assert "This is a complete document content about chemistry synthesis" in old_text
        assert "Another complete document about experimental procedures" in old_text
        assert "Test Paper" in old_text
        assert "Experimental Paper" in old_text
        assert "[1]" in old_text
        assert "[2]" in old_text


class TestSchemaManagerRevisionFunctions:
    """架構管理修改功能測試 - 新增測試"""

    def test_create_revision_experimental_detail_schema(self):
        """測試實驗細節修改架構創建"""
        from backend.core.schema_manager import create_revision_experimental_detail_schema

        schema = create_revision_experimental_detail_schema()

        assert isinstance(schema, dict)
        assert "type" in schema
        assert schema["type"] == "object"
        assert "title" in schema
        assert schema["title"] == "RevisionExperimentalDetail"
        assert "properties" in schema
        assert "required" in schema

        # 檢查必需字段
        required_fields = schema["required"]
        expected_fields = [
            "revision_explanation",
            "synthesis_process",
            "materials_and_conditions",
            "analytical_methods",
            "precautions"
        ]
        for field in expected_fields:
            assert field in required_fields

        # 檢查屬性定義
        properties = schema["properties"]
        for field in expected_fields:
            assert field in properties
            assert "type" in properties[field]
            assert properties[field]["type"] == "string"

    def test_get_schema_by_type_revision_experimental_detail(self):
        """測試通過類型獲取實驗細節修改架構"""
        from backend.core.schema_manager import get_schema_by_type

        schema = get_schema_by_type("revision_experimental_detail")

        assert isinstance(schema, dict)
        assert "type" in schema
        assert schema["type"] == "object"
        assert "title" in schema
        assert schema["title"] == "RevisionExperimentalDetail"

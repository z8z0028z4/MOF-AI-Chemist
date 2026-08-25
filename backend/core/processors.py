"""
處理器模組
========

包含各種模式的具體處理邏輯，每個處理器負責一種特定的處理模式
"""

import time
import logging
from typing import Dict, List, Any, Optional, Tuple

from .vector_store import load_paper_vectorstore, load_experiment_vectorstore, search_documents
from .llm_manager import get_default_llm_manager
from .schema_manager import get_schema_by_type
from ..utils import extract_text_snippet
from ..utils.exceptions import LLMError, VectorStoreError

# 配置日誌
logger = logging.getLogger(__name__)


class BaseProcessor:
    """處理器基類"""

    def __init__(self):
        self.llm_manager = get_default_llm_manager()

    def _build_context(self, chunks: List[Any]) -> str:
        """構建上下文文本"""
        context_parts = []

        for i, chunk in enumerate(chunks, 1):
            try:
                metadata = chunk.metadata
                content = chunk.page_content

                filename = metadata.get("filename", "Unknown")
                page = metadata.get("page", "")

                clean_content = extract_text_snippet(content, max_length=300)

                context_part = f"文檔 {i}: {filename} (頁碼: {page})\n{clean_content}\n"
                context_parts.append(context_part)

            except Exception as e:
                logger.warning(f"處理文檔塊 {i} 失敗: {e}")

        return "\n".join(context_parts)


class AdvancedInferenceProcessor(BaseProcessor):
    """高級推論處理器 - 整合文獻和實驗數據"""

    def process(self, question: str, k: int = 5) -> Dict[str, Any]:
        """處理高級推論模式"""
        logger.info("🧪 啟用模式：納入實驗資料 + 推論")

        # 載入雙重向量庫
        paper_vectorstore = load_paper_vectorstore()
        experiment_vectorstore = load_experiment_vectorstore()

        logger.info(f"📦 Paper 向量庫：{paper_vectorstore._collection.count()}")
        logger.info(f"📦 Experiment 向量庫：{experiment_vectorstore._collection.count()}")

        # 檢索文獻和實驗數據
        chunks_paper = search_documents(paper_vectorstore, question, k=k)
        experiment_chunks = search_documents(experiment_vectorstore, question, k=k)

        # 構建雙重推論提示詞
        prompt = self._build_dual_inference_prompt(question, chunks_paper, experiment_chunks)

        # 調用 LLM
        response = self.llm_manager.generate_response(prompt)

        return {
            "answer": response,
            "citations": self._extract_citations(chunks_paper + experiment_chunks),
            "chunks": chunks_paper + experiment_chunks,
            "paper_chunks": chunks_paper,
            "experiment_chunks": experiment_chunks
        }

    def _build_dual_inference_prompt(self, question: str, paper_chunks: List[Any], experiment_chunks: List[Any]) -> str:
        """構建雙重推論提示詞"""
        paper_context = self._build_context(paper_chunks)
        experiment_context = self._build_context(experiment_chunks)

        return f"""
基於以下文獻和實驗數據，對問題進行綜合分析和推論：

問題：{question}

相關文獻：
{paper_context}

相關實驗數據：
{experiment_context}

請結合文獻理論和實驗數據，提供：
1. 綜合分析
2. 推論和建議
3. 可能的改進方向
4. 相關的實驗驗證建議

請確保回答既有理論基礎，又有實驗支撐。
"""

    def _extract_citations(self, chunks: List[Any]) -> List[str]:
        """提取引用信息"""
        citations = []
        for chunk in chunks:
            try:
                filename = chunk.metadata.get("filename", "")
                page = chunk.metadata.get("page", "")
                if filename:
                    citations.append(f"{filename} (頁碼: {page})")
            except Exception as e:
                logger.warning(f"提取引用信息失敗: {e}")

        return list(set(citations))


class ProposalProcessor(BaseProcessor):
    """研究提案處理器"""

    def process(self, question: str, k: int = 10) -> Dict[str, Any]:
        """處理研究提案生成"""
        logger.info("📝 啟用模式：make proposal (結構化輸出)")

        paper_vectorstore = load_paper_vectorstore()
        logger.info(f"📦 Paper 向量庫：{paper_vectorstore._collection.count()}")

        chunks = search_documents(paper_vectorstore, question, k=k)
        logger.info(f"📄 檢索到 {len(chunks)} 個文檔塊")

        # 構建上下文
        context = self._build_context(chunks)

        # 獲取 schema
        schema = get_schema_by_type("research_proposal")
        if not schema:
            raise ValueError("無法獲取研究提案 schema")

        # 構建提示
        prompt = self._build_proposal_prompt(question, context)

        # 生成結構化回應
        structured_data = self.llm_manager.generate_structured_response(
            prompt=prompt,
            schema=schema,
            system_message="你是一個專業的研究提案生成助手，擅長基於文獻分析生成高質量的研究提案。"
        )

        # 驗證回應
        if not self.llm_manager.validate_response(structured_data, schema):
            raise LLMError("生成的提案不符合 schema 要求")

        # 轉換為文本格式
        text_proposal = self._structured_proposal_to_text(structured_data)

        return {
            "answer": text_proposal,
            "citations": structured_data.get('citations', []),
            "chunks": chunks,
            "structured_proposal": structured_data
        }

    def _build_proposal_prompt(self, question: str, context: str) -> str:
        """構建研究提案提示"""
        return f"""
基於以下研究主題和相關文獻，生成一個詳細的研究提案：

研究主題：{question}

相關文獻：
{context}

請生成一個包含以下要素的研究提案：
1. 研究背景和需求分析
2. 創新解決方案
3. 與現有研究的差異化
4. 預期效益
5. 實驗概述
6. 所需材料清單

請確保提案具有創新性、可行性和實用價值。
"""

    def _structured_proposal_to_text(self, structured_data: Dict[str, Any]) -> str:
        """將結構化提案轉換為文本格式"""
        if not structured_data:
            return ""

        text_parts = []

        # 標題
        if structured_data.get('proposal_title'):
            text_parts.append(f"# {structured_data['proposal_title']}\n")

        # 需求分析
        if structured_data.get('need'):
            text_parts.append(f"## 研究需求\n{structured_data['need']}\n")

        # 解決方案
        if structured_data.get('solution'):
            text_parts.append(f"## 解決方案\n{structured_data['solution']}\n")

        # 差異化
        if structured_data.get('differentiation'):
            text_parts.append(f"## 與現有研究的差異化\n{structured_data['differentiation']}\n")

        # 預期效益
        if structured_data.get('benefit'):
            text_parts.append(f"## 預期效益\n{structured_data['benefit']}\n")

        # 實驗概述
        if structured_data.get('experimental_overview'):
            text_parts.append(f"## 實驗概述\n{structured_data['experimental_overview']}\n")

        # 材料清單
        if structured_data.get('materials_list'):
            text_parts.append(f"## 所需材料清單\n")
            for material in structured_data['materials_list']:
                text_parts.append(f"- {material}")
            text_parts.append("")

        return "\n".join(text_parts)


class InferenceProcessor(BaseProcessor):
    """推論處理器"""

    def process(self, question: str, k: int = 30) -> Dict[str, Any]:
        """處理推論模式"""
        logger.info("🧠 啟用模式：推論模式（不納入實驗資料）")

        paper_vectorstore = load_paper_vectorstore()
        chunks = search_documents(paper_vectorstore, question, k=k)

        logger.info(f"📦 Paper 向量庫：{paper_vectorstore._collection.count()}")

        prompt = self._build_inference_prompt(question, chunks)
        response = self.llm_manager.generate_response(prompt)

        return {
            "answer": response,
            "citations": self._extract_citations(chunks),
            "chunks": chunks
        }

    def _build_inference_prompt(self, question: str, chunks: List[Any]) -> str:
        """構建推論提示詞"""
        context = self._build_context(chunks)

        return f"""
基於以下文獻資料，對問題進行深入分析和推論：

問題：{question}

相關文獻：
{context}

請提供：
1. 基於文獻的深入分析
2. 合理的推論和延伸
3. 可能的應用場景
4. 未來研究方向建議

請確保推論有理有據，基於文獻但不局限於文獻。
"""

    def _extract_citations(self, chunks: List[Any]) -> List[str]:
        """提取引用信息"""
        citations = []
        for chunk in chunks:
            try:
                filename = chunk.metadata.get("filename", "")
                page = chunk.metadata.get("page", "")
                if filename:
                    citations.append(f"{filename} (頁碼: {page})")
            except Exception as e:
                logger.warning(f"提取引用信息失敗: {e}")

        return list(set(citations))


class StrictProcessor(BaseProcessor):
    """嚴謹處理器"""

    def process(self, question: str, k: int = 20) -> Dict[str, Any]:
        """處理嚴謹模式"""
        logger.info("📚 啟用模式：嚴謹模式（僅文獻，無推論）")

        paper_vectorstore = load_paper_vectorstore()
        chunks = search_documents(paper_vectorstore, question, k=k)

        logger.info(f"📦 Paper 向量庫：{paper_vectorstore._collection.count()}")

        prompt = self._build_strict_prompt(question, chunks)
        response = self.llm_manager.generate_response(prompt)

        return {
            "answer": response,
            "citations": self._extract_citations(chunks),
            "chunks": chunks
        }

    def _build_strict_prompt(self, question: str, chunks: List[Any]) -> str:
        """構建嚴謹提示詞"""
        context = self._build_context(chunks)

        return f"""
基於以下文獻資料，嚴格回答問題：

問題：{question}

相關文獻：
{context}

請嚴格基於上述文獻資料回答問題，不要進行任何推論或延伸。
如果文獻資料不足以回答問題，請明確說明。
"""

    def _extract_citations(self, chunks: List[Any]) -> List[str]:
        """提取引用信息"""
        citations = []
        for chunk in chunks:
            try:
                filename = chunk.metadata.get("filename", "")
                page = chunk.metadata.get("page", "")
                if filename:
                    citations.append(f"{filename} (頁碼: {page})")
            except Exception as e:
                logger.warning(f"提取引用信息失敗: {e}")

        return list(set(citations))


class ExperimentDetailProcessor(BaseProcessor):
    """實驗細節處理器"""

    def process(self, question: str, chunks: List[Any], proposal: str) -> Dict[str, Any]:
        """處理實驗細節擴展"""
        logger.info("🔬 啟用模式：expand to experiment detail (結構化輸出)")

        # 構建上下文
        context = self._build_context(chunks)

        # 獲取 schema
        schema = get_schema_by_type("experimental_detail")
        if not schema:
            raise ValueError("無法獲取實驗詳情 schema")

        # 構建提示
        prompt = self._build_experiment_detail_prompt(question, context, proposal)

        # 生成結構化回應
        structured_data = self.llm_manager.generate_structured_response(
            prompt=prompt,
            schema=schema,
            system_message="你是一個專業的實驗設計助手，擅長基於文獻分析生成詳細的實驗方案。"
        )

        # 驗證回應
        if not self.llm_manager.validate_response(structured_data, schema):
            raise LLMError("生成的實驗詳情不符合 schema 要求")

        # 轉換為文本格式
        text_experiment = self._structured_experiment_to_text(structured_data)

        return {
            "answer": text_experiment,
            "citations": structured_data.get('citations', []),
            "chunks": chunks,
            "structured_experiment": structured_data
        }

    def _build_experiment_detail_prompt(self, question: str, context: str, proposal: str) -> str:
        """構建實驗細節提示"""
        return f"""
基於以下實驗主題、相關文獻和提案，生成詳細的實驗方案：

實驗主題：{question}

相關文獻：
{context}

研究提案：
{proposal}

請生成一個包含以下要素的實驗方案：
1. 實驗目標
2. 實驗方法
3. 所需材料清單
4. 詳細實驗步驟
5. 預期結果

請確保實驗方案具有可操作性和可重複性。
"""

    def _structured_experiment_to_text(self, structured_data: Dict[str, Any]) -> str:
        """將結構化實驗詳情轉換為文本格式"""
        if not structured_data:
            return ""

        text_parts = []

        # 實驗目標
        if structured_data.get('experiment_objective'):
            text_parts.append(f"## 實驗目標\n{structured_data['experiment_objective']}\n")

        # 實驗方法
        if structured_data.get('experiment_method'):
            text_parts.append(f"## 實驗方法\n{structured_data['experiment_method']}\n")

        # 材料清單
        if structured_data.get('materials_list'):
            text_parts.append(f"## 所需材料清單\n")
            for material in structured_data['materials_list']:
                text_parts.append(f"- {material}")
            text_parts.append("")

        # 實驗步驟
        if structured_data.get('experiment_steps'):
            text_parts.append(f"## 詳細實驗步驟\n{structured_data['experiment_steps']}\n")

        # 預期結果
        if structured_data.get('expected_results'):
            text_parts.append(f"## 預期結果\n{structured_data['expected_results']}\n")

        return "\n".join(text_parts)


class InnovationProcessor(BaseProcessor):
    """創新想法處理器"""

    def process(self, question: str, old_chunks: List[Any], proposal: str, k: int = 5) -> Dict[str, Any]:
        """處理新想法生成"""
        logger.info("💡 啟用模式：generate new idea (結構化輸出)")

        paper_vectorstore = load_paper_vectorstore()
        logger.info(f"📦 Paper 向量庫：{paper_vectorstore._collection.count()}")

        # 檢索新的文檔塊
        new_chunks = search_documents(paper_vectorstore, question, k=k)

        # 構建上下文
        new_context = self._build_context(new_chunks)
        old_context = self._build_context(old_chunks)

        # 獲取 schema
        schema = get_schema_by_type("revision_proposal")
        if not schema:
            raise ValueError("無法獲取修訂提案 schema")

        # 構建提示
        prompt = self._build_innovation_prompt(question, new_context, old_context, proposal)

        # 生成結構化回應
        structured_data = self.llm_manager.generate_structured_response(
            prompt=prompt,
            schema=schema,
            system_message="你是一個專業的研究創新助手，擅長基於新文獻生成創新的研究想法。"
        )

        # 驗證回應
        if not self.llm_manager.validate_response(structured_data, schema):
            raise LLMError("生成的修訂提案不符合 schema 要求")

        # 轉換為文本格式
        text_proposal = self._structured_revision_to_text(structured_data)

        return {
            "answer": text_proposal,
            "citations": structured_data.get('citations', []),
            "chunks": new_chunks + old_chunks,
            "structured_proposal": structured_data,
            "materials_list": structured_data.get('materials_list', [])
        }

    def _build_innovation_prompt(self, question: str, new_context: str, old_context: str, proposal: str) -> str:
        """構建創新提示"""
        return f"""
基於新的文獻資料和現有提案，生成創新的研究想法：

研究主題：{question}

新發現的文獻：
{new_context}

原有文獻：
{old_context}

現有提案：
{proposal}

請生成一個包含以下要素的創新提案：
1. 修訂說明（基於新文獻的改進）
2. 新的研究背景和需求分析
3. 改進的解決方案
4. 與原提案的差異化
5. 預期效益
6. 實驗概述
7. 所需材料清單

請確保新提案具有創新性和可行性。
"""

    def _structured_revision_to_text(self, structured_data: Dict[str, Any]) -> str:
        """將結構化修訂提案轉換為文本格式"""
        if not structured_data:
            return ""

        text_parts = []

        # 修訂說明
        if structured_data.get('revision_explanation'):
            text_parts.append(f"## 修訂說明\n{structured_data['revision_explanation']}\n")

        # 提案標題
        if structured_data.get('proposal_title'):
            text_parts.append(f"# {structured_data['proposal_title']}\n")

        # 需求分析
        if structured_data.get('need'):
            text_parts.append(f"## 研究需求\n{structured_data['need']}\n")

        # 解決方案
        if structured_data.get('solution'):
            text_parts.append(f"## 解決方案\n{structured_data['solution']}\n")

        # 差異化
        if structured_data.get('differentiation'):
            text_parts.append(f"## 與現有研究的差異化\n{structured_data['differentiation']}\n")

        # 預期效益
        if structured_data.get('benefit'):
            text_parts.append(f"## 預期效益\n{structured_data['benefit']}\n")

        # 實驗概述
        if structured_data.get('experimental_overview'):
            text_parts.append(f"## 實驗概述\n{structured_data['experimental_overview']}\n")

        # 材料清單
        if structured_data.get('materials_list'):
            text_parts.append(f"## 所需材料清單\n")
            for material in structured_data['materials_list']:
                text_parts.append(f"- {material}")
            text_parts.append("")

        return "\n".join(text_parts)


# 處理器工廠
PROCESSOR_MAP = {
    "納入實驗資料，進行推論與建議": AdvancedInferenceProcessor,
    "make proposal": ProposalProcessor,
    "允許延伸與推論": InferenceProcessor,
    "僅嚴謹文獻溯源": StrictProcessor,
    "expand to experiment detail": ExperimentDetailProcessor,
    "generate new idea": InnovationProcessor
}


def get_processor(mode: str) -> Optional[BaseProcessor]:
    """
    根據模式獲取對應的處理器

    Args:
        mode (str): 處理模式

    Returns:
        Optional[BaseProcessor]: 對應的處理器實例，如果模式不存在則返回 None
    """
    processor_class = PROCESSOR_MAP.get(mode)
    if processor_class:
        return processor_class()
    return None

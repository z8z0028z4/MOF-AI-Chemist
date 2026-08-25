"""
AI 研究助理 - 知識代理模塊
========================

這個模塊是整個AI研究助理系統的核心，負責整合多源信息並生成智能回答。
主要功能包括：
1. 多模式知識處理
2. 文獻和實驗數據整合
3. 智能推論和建議生成
4. 實驗方案設計

架構說明：
- 作為知識處理層的核心協調器
- 整合RAG核心功能
- 支持多種處理模式
- 提供統一的知識處理接口
"""

import pandas as pd
# 導入核心模組 - 直接從具體模塊導入避免循環導入
from ..core.vector_store import load_paper_vectorstore, load_experiment_vectorstore
from ..core.prompt_builder import (
    build_prompt,
    build_proposal_prompt,
    build_detail_experimental_plan_prompt,
    build_inference_prompt,
    build_dual_inference_prompt,
    build_iterative_proposal_prompt
)
from ..core.generation import call_llm
from ..core.query_expander import expand_query
from ..core.format_converter import (
    structured_proposal_to_text,
    structured_experimental_detail_to_text,
    structured_revision_proposal_to_text
)

# 直接定義檢索函數，避免循環導入
def retrieve_chunks_multi_query(
    vectorstore,
    query_list: list[str],
    k: int = 10,
    fetch_k: int = 20,
    score_threshold: float = 0.35
) -> list:
    """
    多查詢文檔檢索功能
    """
    from langchain_core.documents import Document
    import logging
    logger = logging.getLogger(__name__)

    try:
        retriever = vectorstore.as_retriever(
            search_type="mmr",
            search_kwargs={"k": k, "fetch_k": fetch_k, "score_threshold": score_threshold}
        )

        # 使用字典進行去重
        chunk_dict = {}
        logger.info(f"開始多查詢檢索，查詢列表：{query_list}")

        # 對每個查詢進行檢索
        for q in query_list:
            from ..core.retrieval import invoke_retriever
            docs = invoke_retriever(retriever, q)
            for doc in docs:
                # 使用唯一標識符進行去重
                chunk_id = doc.metadata.get("chunk_id", doc.page_content[:50])
                if chunk_id not in chunk_dict:
                    chunk_dict[chunk_id] = doc

        result = list(chunk_dict.values())
        logger.info(f"檢索完成，共找到 {len(result)} 個唯一文檔塊")
        return result

    except Exception as e:
        logger.error(f"多查詢檢索失敗: {e}")
        return []

def preview_chunks(chunks: list, title: str, max_preview: int = 5) -> None:
    """
    預覽文檔塊內容
    """
    print(f"\n📄 {title} (顯示前 {min(max_preview, len(chunks))} 個):")
    for i, chunk in enumerate(chunks[:max_preview]):
        print(f"  {i+1}. {chunk.page_content[:100]}...")
        print(f"     來源: {chunk.metadata.get('source', 'Unknown')}")
        print(f"     頁碼: {chunk.metadata.get('page', 'Unknown')}")
        print()

# 導入便捷函數
from backend.services.rag_service import (
    generate_iterative_structured_proposal,
    generate_structured_experimental_detail,

    generate_structured_revision_proposal,
    generate_structured_proposal
)

import os
from backend.config import EXPERIMENT_DIR

def agent_answer(question: str, mode: str = "make proposal", **kwargs):
    """
    知識代理的主要回答函數

    功能：
    1. 根據不同模式處理用戶查詢
    2. 整合文獻和實驗數據
    3. 生成智能回答和建議
    4. 提供相關引用信息

    參數：
        question (str): 用戶問題
        mode (str): 處理模式，支持多種模式
        **kwargs: 額外參數，如chunks、proposal、k等

    返回：
        dict: 包含回答、引用和相關文檔塊的字典

    支持的模式：
    - "納入實驗資料，進行推論與建議": 整合實驗數據進行推論
    - "make proposal": 生成研究提案
    - "允許延伸與推論": 基於文獻進行推論
    - "僅嚴謹文獻溯源": 嚴格基於文獻回答
    - "expand to experiment detail": 擴展實驗細節
    - "generate new idea": 生成新想法
    """

    import time
    import uuid
    import traceback

    # 生成唯一的請求 ID
    request_id = str(uuid.uuid4())[:8]
    start_time = time.time()

    # 獲取調用堆疊信息
    stack_info = traceback.extract_stack()
    caller_info = stack_info[-2] if len(stack_info) > 1 else stack_info[-1]

    print(f"🧠 [AGENT-{request_id}] ========== agent_answer 被調用 ==========")
    print(f"🧠 [AGENT-{request_id}] 時間戳: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🧠 [AGENT-{request_id}] 調用位置: {caller_info.filename}:{caller_info.lineno}")
    print(f"🧠 [AGENT-{request_id}] 調用函數: {caller_info.name}")
    print(f"🧠 [AGENT-{request_id}] question = '{question}'")
    print(f"🧠 [AGENT-{request_id}] mode = '{mode}'")
    print(f"🧠 [AGENT-{request_id}] kwargs = {kwargs}")

    # 獲取檢索參數
    k = kwargs.get("k", 10)  # 預設檢索 10 個文檔
    fetch_k = k * 2  # fetch_k 自動設為 k 的 2 倍

    print(f"🧠 [AGENT-{request_id}] k = {k}, fetch_k = {fetch_k}")
    print(f"🧠 [AGENT-{request_id}] mode type = {type(mode)}")
    print(f"🧠 [AGENT-{request_id}] mode == 'make proposal' = {mode == 'make proposal'}")
    print(f"🧠 [AGENT-{request_id}] mode == 'default' = {mode == 'default'}")

    # ==================== 模式1：納入實驗資料，進行推論與建議 ====================
    if mode == "納入實驗資料，進行推論與建議":
        """
        高級模式：整合文獻和實驗數據進行綜合推論

        特點：
        - 使用雙重檢索器（文獻 + 實驗數據）
        - 語義查詢擴展
        - 綜合推論和建議
        """
        print("🧪 啟用模式：納入實驗資料 + 推論")

        # 載入雙重向量庫
        paper_vectorstore = load_paper_vectorstore()  # 文獻向量庫
        experiment_vectorstore = load_experiment_vectorstore()  # 實驗向量庫
        print("📦 Paper 向量庫：", paper_vectorstore._collection.count())
        print("📦 Experiment 向量庫：", experiment_vectorstore._collection.count())

        # 語義查詢擴展和檢索
        query_list = expand_query(question)  # 為文獻檢索進行語義擴展
        chunks_paper = retrieve_chunks_multi_query(paper_vectorstore, query_list, k=5)
        experiment_chunks = retrieve_chunks_multi_query(experiment_vectorstore, [question], k=5)  # 實驗數據檢索

        # 預覽檢索結果
        preview_chunks(chunks_paper, title="文獻向量庫")
        preview_chunks(experiment_chunks, title="實驗向量庫")

        # 構建雙重推論提示詞
        prompt, citations = build_dual_inference_prompt(
            chunks_paper, question, experiment_chunks
        )

    # ==================== 模式2：生成研究提案 ====================
    elif mode == "make proposal":
        """
        研究提案生成模式

        特點：
        - 基於文獻生成研究提案
        - 使用較多的檢索結果（k=10）
        - 專注於提案結構化生成
        - 優先使用結構化輸出，失敗時回退到傳統格式
        """
        print(f"📝 [AGENT-{request_id}] 啟用模式：make proposal (結構化輸出)")
        paper_vectorstore = load_paper_vectorstore()
        print(f"📦 [AGENT-{request_id}] Paper 向量庫：{paper_vectorstore._collection.count()}")
        chunks = retrieve_chunks_multi_query(paper_vectorstore, [question], k=k, fetch_k=fetch_k)
        print(f"📄 [AGENT-{request_id}] 檢索到 {len(chunks)} 個文檔塊")

        mof_linker_mode = kwargs.get("mof_linker_mode", "auto")
        # 使用新的結構化提案生成功能
        structured_data = generate_structured_proposal(chunks, question, mof_linker_mode=mof_linker_mode)

        # 將結構化數據轉換為文本格式
        text_proposal = structured_proposal_to_text(structured_data) if structured_data else ""

        end_time = time.time()
        duration = end_time - start_time

        print(f"✅ [AGENT-{request_id}] ========== make proposal 完成 ==========")
        print(f"✅ [AGENT-{request_id}] 總耗時: {duration:.2f} 秒")
        print(f"✅ [AGENT-{request_id}] 文本提案長度: {len(text_proposal)}")
        print(f"✅ [AGENT-{request_id}] 結構化數據鍵: {list(structured_data.keys()) if structured_data else 'None'}")

        # 返回結構化結果
        return {
            "answer": text_proposal,
            "citations": structured_data.get('citations', []),
            "chunks": chunks,
            "structured_proposal": structured_data
        }

    # ==================== 模式3：允許延伸與推論 ====================
    elif mode == "允許延伸與推論":
        """
        推論模式：基於文獻進行智能推論

        特點：
        - 僅使用文獻數據
        - 允許AI進行推論和延伸
        - 不納入實驗數據
        """
        # 使用單一檢索器（僅文獻）
        paper_vectorstore = load_paper_vectorstore()
        chunks = retrieve_chunks_multi_query(paper_vectorstore, [question], k = 30, fetch_k = 50)
        print("📦 Paper 向量庫：", paper_vectorstore._collection.count())
        print("🧠 啟用模式：推論模式（不納入實驗資料）")
        prompt, citations = build_inference_prompt(chunks, [question])

    # ==================== 模式4：僅嚴謹文獻溯源 ====================
    elif mode == "僅嚴謹文獻溯源":
        """
        嚴謹模式：嚴格基於文獻回答

        特點：
        - 僅基於檢索到的文獻片段回答
        - 不進行推論和延伸
        - 確保回答的可追溯性
        """
        print("📚 啟用模式：嚴謹模式（僅文獻，無推論）")
        paper_vectorstore = load_paper_vectorstore()
        chunks = retrieve_chunks_multi_query(paper_vectorstore, [question], k = 20, fetch_k = 30)
        print("📦 Paper 向量庫：", paper_vectorstore._collection.count())
        prompt, citations = build_prompt(chunks, [question])

    # ==================== 模式5：擴展實驗細節 ====================
    elif mode == "expand to experiment detail":
        """
        實驗細節擴展模式

        特點：
        - 基於提案和文獻塊生成詳細實驗計劃
        - 需要外部提供chunks和proposal
        - 專注於實驗設計細節
        - 使用結構化輸出
        """
        print("🔬 啟用模式：expand to experiment detail (結構化輸出)")
        chunks = kwargs.get("chunks", [])
        proposal = kwargs.get("proposal", "")

        # 使用新的結構化實驗細節生成功能
        structured_data = generate_structured_experimental_detail(chunks, proposal)

        # 轉換為文本格式
        text_experiment = structured_experimental_detail_to_text(structured_data)

        # 返回結構化結果
        return {
            "answer": text_experiment,
            "citations": structured_data.get('citations', []),
            "chunks": chunks,
            "structured_experiment": structured_data
        }

    # ==================== 模式6：生成新想法 ====================
    elif mode == "generate new idea":
        """
        新想法生成模式

        特點：
        - 基於現有提案生成新的研究想法
        - 使用迭代式提案生成
        - 需要外部提供old_chunks和proposal
        - 使用結構化輸出
        - 新增：包含修訂說明
        """
        print("💡 啟用模式：generate new idea (結構化輸出)")
        paper_vectorstore = load_paper_vectorstore()
        print("📦 Paper 向量庫：", paper_vectorstore._collection.count())
        query_list = expand_query(question)  # 語義擴展

        # 可調整的檢索參數
        k_new_chunks = kwargs.get("k_new_chunks", 3)  # 每個查詢檢索的chunks數量，預設3（降低查詢量）
        print(f"🔍 新chunks檢索參數: k={k_new_chunks}")

        new_chunks = retrieve_chunks_multi_query(paper_vectorstore, query_list, k=k_new_chunks)
        old_chunks = kwargs.get("old_chunks", [])
        proposal = kwargs.get("proposal", "")

        mof_linker_mode = kwargs.get("mof_linker_mode", "auto")
        # 使用新的單次 LLM 調用生成修訂提案 (包含修訂說明)
        structured_data = generate_structured_revision_proposal(
            question, new_chunks, old_chunks, proposal, mof_linker_mode=mof_linker_mode
        )

        # 轉換為文本格式
        text_proposal = structured_revision_proposal_to_text(structured_data)

        # ✅ 修復：將新檢索到的chunks轉換為citations格式
        def chunks_to_citations(chunks_list):
            """將chunks轉換為citations格式"""
            citations_list = []
            for chunk in chunks_list:
                citation = {
                    "source": chunk.metadata.get("source", "Unknown"),
                    "page": str(chunk.metadata.get("page", "Unknown")),
                    "content": chunk.page_content[:200] + "..." if len(chunk.page_content) > 200 else chunk.page_content
                }
                citations_list.append(citation)
            return citations_list

        # 合併結構化數據中的citations和新chunks轉換的citations
        structured_citations = structured_data.get('citations', [])
        new_chunks_citations = chunks_to_citations(new_chunks)
        all_citations = structured_citations + new_chunks_citations

        print(f"🔍 [DEBUG] 結構化citations數量: {len(structured_citations)}")
        print(f"🔍 [DEBUG] 新chunks轉換的citations數量: {len(new_chunks_citations)}")
        print(f"🔍 [DEBUG] 總citations數量: {len(all_citations)}")

        # 返回結構化結果
        return {
            "answer": text_proposal,
            "citations": all_citations,  # ✅ 修復：返回合併後的citations
            "chunks": new_chunks + old_chunks,
            "structured_proposal": structured_data,
            "materials_list": structured_data.get('materials_list', [])  # 直接傳遞材料列表
        }

    # ==================== 錯誤處理 ====================
    else:
        print(f"❌ DEBUG: 未知的模式：'{mode}'")
        print(f"❌ DEBUG: 可用的模式：{get_available_modes()}")
        raise ValueError(f"❌ 未知的模式：{mode}")

    # ==================== 調用LLM生成回答 ====================
    # 檢查是否已經有直接返回的結果（結構化模式）
    if 'prompt' not in locals():
        print(f"🔍 [AGENT-{request_id}] 檢測到結構化模式，已直接返回結果")
        result = locals().get('result', {})

        end_time = time.time()
        duration = end_time - start_time
        print(f"✅ [AGENT-{request_id}] ========== agent_answer 完成 (結構化模式) ==========")
        print(f"✅ [AGENT-{request_id}] 總耗時: {duration:.2f} 秒")
        return result

    print(f"🔍 [AGENT-{request_id}] 準備調用 call_llm")
    print(f"🔍 [AGENT-{request_id}] prompt 長度: {len(prompt)}")
    print(f"🔍 [AGENT-{request_id}] prompt 前200字符: {prompt[:200]}...")

    response = call_llm(prompt)

    print(f"🔍 [AGENT-{request_id}] call_llm 返回結果")
    print(f"🔍 [AGENT-{request_id}] response 類型: {type(response)}")
    print(f"🔍 [AGENT-{request_id}] response 長度: {len(response) if response else 0}")
    print(f"🔍 [AGENT-{request_id}] response 內容: {response[:500] if response else 'None'}...")

    # ==================== 獲取使用的模型信息 ====================
    try:
        from backend.services.model_service import get_current_model
        used_model = get_current_model()
        print(f"🔍 [AGENT-{request_id}] 使用的模型: {used_model}")
    except Exception as e:
        print(f"❌ [AGENT-{request_id}] 獲取模型信息失敗: {e}")
        used_model = "unknown"

    # ==================== 返回結果 ====================
    result = {
        "answer": response,      # AI生成的回答
        "citations": citations,  # 相關引用信息
        "chunks": chunks,       # 檢索到的相關文檔塊
        "used_model": used_model  # 使用的模型信息
    }

    end_time = time.time()
    duration = end_time - start_time

    print(f"✅ [AGENT-{request_id}] ========== agent_answer 完成 (傳統模式) ==========")
    print(f"✅ [AGENT-{request_id}] 總耗時: {duration:.2f} 秒")
    print(f"✅ [AGENT-{request_id}] answer 長度: {len(result['answer'])}")
    print(f"✅ [AGENT-{request_id}] citations 數量: {len(result['citations'])}")
    print(f"✅ [AGENT-{request_id}] chunks 數量: {len(result['chunks'])}")

    return result


# ==================== 輔助函數 ====================
def get_available_modes():
    """
    獲取所有可用的處理模式

    返回：
        List[str]: 可用模式列表
    """
    return [
        "納入實驗資料，進行推論與建議",
        "make proposal",
        "允許延伸與推論",
        "僅嚴謹文獻溯源",
        "expand to experiment detail",
        "generate new idea"
    ]


def validate_mode(mode: str) -> bool:
    """
    驗證模式是否有效

    參數：
        mode (str): 要驗證的模式

    返回：
        bool: 模式是否有效
    """
    available_modes = get_available_modes()
    return mode in available_modes


def get_mode_description(mode: str) -> str:
    """
    獲取模式的詳細描述

    參數：
        mode (str): 模式名稱

    返回：
        str: 模式描述
    """
    descriptions = {
        "納入實驗資料，進行推論與建議": "整合文獻和實驗數據進行綜合推論",
        "make proposal": "生成研究提案",
        "允許延伸與推論": "基於文獻進行智能推論",
        "僅嚴謹文獻溯源": "嚴格基於文獻回答，無推論",
        "expand to experiment detail": "擴展實驗細節設計",
        "generate new idea": "生成新的研究想法"
    }
    return descriptions.get(mode, "未知模式")

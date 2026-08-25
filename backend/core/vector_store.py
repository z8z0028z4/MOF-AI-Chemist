"""
向量庫管理模組
==========

負責管理向量數據庫的載入、檢索和統計功能
"""

import os
import logging
from typing import List, Dict, Any, Optional
from langchain_core.documents import Document
from langchain_chroma import Chroma

# 移除模組級別的導入，避免循環依賴
# from ..services.embedding_service import get_chroma_instance
from ..utils import extract_text_snippet

# 配置日誌
logger = logging.getLogger(__name__)

def load_paper_vectorstore() -> Chroma:
    """
    載入論文向量數據庫

    Returns:
        Chroma: 論文向量數據庫實例
    """
    try:
        # 延遲導入避免循環依賴
        from ..services.embedding_service import get_chroma_instance
        vectorstore = get_chroma_instance("paper")
        logger.info("論文向量數據庫載入成功")
        return vectorstore
    except Exception as e:
        logger.error(f"論文向量數據庫載入失敗: {e}")
        raise

def load_experiment_vectorstore() -> Chroma:
    """
    載入實驗向量數據庫

    Returns:
        Chroma: 實驗向量數據庫實例
    """
    try:
        # 延遲導入避免循環依賴
        from ..services.embedding_service import get_chroma_instance
        vectorstore = get_chroma_instance("experiment")
        logger.info("實驗向量數據庫載入成功")
        return vectorstore
    except Exception as e:
        logger.error(f"實驗向量數據庫載入失敗: {e}")
        raise

def search_documents(
    vectorstore: Chroma,
    query: str,
    k: int = 5,
    fetch_k: int = 20,
    filter_dict: Optional[Dict[str, Any]] = None
) -> List[Document]:
    """
    在向量數據庫中搜索文檔

    Args:
        vectorstore: 向量數據庫實例
        query: 搜索查詢
        k: 返回的文檔數量
        fetch_k: 檢索的文檔數量
        filter_dict: 過濾條件

    Returns:
        List[Document]: 搜索結果文檔列表
    """
    try:
        if filter_dict:
            docs = vectorstore.similarity_search_with_relevance_scores(
                query, k=fetch_k, filter=filter_dict
            )
        else:
            docs = vectorstore.similarity_search_with_relevance_scores(
                query, k=fetch_k
            )

        # 按相關性排序並返回前k個
        docs.sort(key=lambda x: x[1], reverse=True)
        return [doc[0] for doc in docs[:k]]

    except Exception as e:
        logger.error(f"文檔搜索失敗: {e}")
        return []

def get_vectorstore_stats(vectorstore_type: str = "paper") -> Dict[str, Any]:
    """
    獲取向量數據庫統計信息

    Args:
        vectorstore_type: 向量數據庫類型 ("paper" 或 "experiment")

    Returns:
        Dict[str, Any]: 統計信息
    """
    try:
        # 延遲導入避免循環依賴
        from ..services.embedding_service import get_vectorstore_stats as get_stats
        return get_stats(vectorstore_type)
    except Exception as e:
        logger.error(f"獲取向量數據庫統計失敗: {e}")
        return {"error": str(e)}

def preview_chunks(chunks: List[Document], title: str, max_preview: int = 5) -> None:
    """
    預覽文檔塊內容

    Args:
        chunks: 文檔塊列表
        title: 預覽標題
        max_preview: 最大預覽數量
    """
    logger.info(f"📄 {title} - 檢索到 {len(chunks)} 個文檔塊")

    for i, chunk in enumerate(chunks[:max_preview]):
        try:
            # 提取文檔信息
            metadata = chunk.metadata
            content_preview = extract_text_snippet(chunk.page_content, max_length=150)

            # 記錄預覽信息
            logger.info(f"  #{i+1} | {metadata.get('filename', 'Unknown')} | {content_preview}")

        except Exception as e:
            logger.warning(f"  #{i+1} | 預覽失敗: {e}")

    if len(chunks) > max_preview:
        logger.info(f"  ... 還有 {len(chunks) - max_preview} 個文檔塊")

def combine_search_results(
    paper_chunks: List[Document],
    experiment_chunks: List[Document],
    max_total: int = 10
) -> List[Document]:
    """
    合併論文和實驗的搜索結果

    Args:
        paper_chunks: 論文文檔塊
        experiment_chunks: 實驗文檔塊
        max_total: 最大總數

    Returns:
        List[Document]: 合併後的文檔塊列表
    """
    combined_chunks = []

    # 添加論文文檔塊
    for chunk in paper_chunks:
        if len(combined_chunks) >= max_total:
            break
        combined_chunks.append(chunk)

    # 添加實驗文檔塊
    for chunk in experiment_chunks:
        if len(combined_chunks) >= max_total:
            break
        combined_chunks.append(chunk)

    logger.info(f"合併搜索結果: {len(paper_chunks)} 論文 + {len(experiment_chunks)} 實驗 = {len(combined_chunks)} 總計")

    return combined_chunks

def format_search_results(chunks: List[Document]) -> List[Dict[str, Any]]:
    """
    格式化搜索結果

    Args:
        chunks: 文檔塊列表

    Returns:
        List[Dict[str, Any]]: 格式化後的結果
    """
    formatted_results = []

    for i, chunk in enumerate(chunks):
        try:
            metadata = chunk.metadata
            content = chunk.page_content

            formatted_result = {
                "index": i + 1,
                "filename": metadata.get("filename", "Unknown"),
                "file_path": metadata.get("file_path", ""),
                "page": metadata.get("page", ""),
                "content": content,
                "content_preview": extract_text_snippet(content, max_length=200),
                "metadata": metadata
            }

            formatted_results.append(formatted_result)

        except Exception as e:
            logger.warning(f"格式化搜索結果失敗 #{i+1}: {e}")

    return formatted_results

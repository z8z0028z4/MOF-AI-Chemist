"""
Backend core package.

This initializer intentionally avoids eager imports. Import concrete modules
directly where possible; legacy `from backend.core import ...` access is served
through lazy exports below.
"""

from importlib import import_module

_LAZY_EXPORTS = {
    # LLM/model config
    "get_current_model": "backend.core.model_config",
    "get_model_params": "backend.core.model_config",
    # 檢索系統
    "load_paper_vectorstore": "backend.core.retrieval",
    "load_experiment_vectorstore": "backend.core.retrieval",
    "search_documents": "backend.core.vector_store",
    "search_experiments": "backend.core.retrieval",
    # 生成系統
    "call_llm": "backend.core.generation",
    "call_structured_llm": "backend.core.generation",
    "generate_research_proposal": "backend.core.generation",
    "generate_experimental_detail": "backend.core.generation",
    "generate_revision_proposal": "backend.core.generation",
    # Schema 管理
    "create_research_proposal_schema": "backend.core.schema_manager",
    "create_experimental_detail_schema": "backend.core.schema_manager",
    "create_revision_proposal_schema": "backend.core.schema_manager",
    "get_dynamic_schema_params": "backend.core.schema_manager",
    # 向量存儲
    "get_chroma_instance": "backend.services.embedding_service",
    "get_vectorstore_stats": "backend.core.vector_store",
    # 查詢擴展
    "expand_query": "backend.core.query_expander",
    # 模式管理
    "get_mode_config": "backend.core.mode_manager",
    "set_mode_config": "backend.core.mode_manager",
    # 格式轉換
    "convert_format": "backend.core.format_converter",
    # 處理器
    "process_documents": "backend.core.processors",
    # 提示詞構建
    "build_prompt": "backend.core.prompt_builder",
    "build_inference_prompt": "backend.core.prompt_builder",
}

__all__ = sorted(_LAZY_EXPORTS)


def __getattr__(name):
    module_name = _LAZY_EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module = import_module(module_name)
    value = getattr(module, name)
    globals()[name] = value
    return value

"""
Backend services package.

Keep package import lightweight. Individual services should be imported from
their concrete modules, for example `backend.services.chemical_service`.
"""

from importlib import import_module

_LAZY_EXPORTS = {
    # 化學服務
    "chemical_service": "backend.services.chemical_service",
    "chemical_metadata_extractor": "backend.services.pubchem_service",
    "extract_and_fetch_chemicals": "backend.services.chemical_service",
    "remove_json_chemical_block": "backend.services.chemical_service",
    # 文件服務
    "process_uploaded_files": "backend.services.file_service",
    # 知識服務
    "agent_answer": "backend.services.knowledge_service",
    # 搜索服務
    "search_and_download_only": "backend.services.search_service",
    # 語義服務
    "semantic_search": "backend.services.semantic_service",
    # 查詢服務
    "parse_query": "backend.services.query_service",
    # 元數據服務
    "extract_metadata": "backend.services.metadata_service",
    "register_metadata": "backend.services.metadata_registry",
    "register_experiment_metadata": "backend.services.metadata_experiment_registry",
    # 模型服務
    "get_current_model": "backend.services.model_service",
    "get_model_params": "backend.services.model_service",
    "detect_model_parameters": "backend.services.model_parameter_service",
    # 外部 API 服務
    "europepmc_search": "backend.services.external_api_service",
    # 嵌入服務
    "embed_documents": "backend.services.embedding_service",
    "get_vectorstore_stats": "backend.services.embedding_service",
    "get_chroma_instance": "backend.services.embedding_service",
    # Excel 服務
    "export_experiments_to_txt": "backend.services.excel_service",
    # 文檔服務
    "read_pdf": "backend.services.document_service",
    "rename_documents": "backend.services.document_renamer",
    # RAG 服務
    "generate_iterative_structured_proposal": "backend.services.rag_service",
    "generate_structured_experimental_detail": "backend.services.rag_service",
    # PubChem 服務
    "fetch_chemical_data": "backend.services.pubchem_service",
    # SMILES 繪製服務
    "draw_smiles": "backend.services.smiles_drawer",
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

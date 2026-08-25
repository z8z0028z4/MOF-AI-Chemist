"""
工具模組
======

提供系統中常用的工具函數和類別，包括：
- 日誌配置
- 異常處理
- 通用工具函數
"""

from .logger import setup_logger, get_logger, default_logger
from .exceptions import (
    AIResearchAgentError,
    ConfigurationError,
    APIKeyError,
    FileProcessingError,
    FileNotFoundError,
    UnsupportedFileFormatError,
    VectorStoreError,
    EmbeddingError,
    LLMError,
    APIRequestError,
    ValidationError,
    DatabaseError,
    ProcessingTimeoutError,
    handle_exception
)
from .helpers import (
    sanitize_filename,
    generate_file_hash,
    validate_file_format,
    get_file_info,
    clean_text,
    extract_text_snippet,
    validate_json_schema,
    safe_json_dumps,
    safe_json_loads,
    format_file_size,
    create_timestamp,
    generate_unique_id,
    ensure_directory_exists,
    list_files_in_directory,
    copy_file_safely
)

__all__ = [
    # 日誌相關
    "setup_logger",
    "get_logger",
    "default_logger",

    # 異常處理
    "AIResearchAgentError",
    "ConfigurationError",
    "APIKeyError",
    "FileProcessingError",
    "FileNotFoundError",
    "UnsupportedFileFormatError",
    "VectorStoreError",
    "EmbeddingError",
    "LLMError",
    "APIRequestError",
    "ValidationError",
    "DatabaseError",
    "ProcessingTimeoutError",
    "handle_exception",

    # 工具函數
    "sanitize_filename",
    "generate_file_hash",
    "validate_file_format",
    "get_file_info",
    "clean_text",
    "extract_text_snippet",
    "validate_json_schema",
    "safe_json_dumps",
    "safe_json_loads",
    "format_file_size",
    "create_timestamp",
    "generate_unique_id",
    "ensure_directory_exists",
    "list_files_in_directory",
    "copy_file_safely"
]

"""
自定義異常類別
===========

定義系統中使用的自定義異常，提供統一的錯誤處理機制
"""

from typing import Optional, Dict, Any


class AIResearchAgentError(Exception):
    """AI研究助理系統的基礎異常類別"""

    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}

    def __str__(self):
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message


class ConfigurationError(AIResearchAgentError):
    """配置相關錯誤"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "CONFIG_ERROR", details)


class APIKeyError(ConfigurationError):
    """API密鑰相關錯誤"""

    def __init__(self, api_name: str, details: Optional[Dict[str, Any]] = None):
        message = f"缺少或無效的 {api_name} API密鑰"
        super().__init__(message, details)


class FileProcessingError(AIResearchAgentError):
    """文件處理相關錯誤"""

    def __init__(self, message: str, file_path: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        if file_path:
            message = f"{message} (文件: {file_path})"
        super().__init__(message, "FILE_PROCESSING_ERROR", details)


class FileNotFoundError(FileProcessingError):
    """文件不存在錯誤"""

    def __init__(self, file_path: str, details: Optional[Dict[str, Any]] = None):
        message = f"文件不存在"
        super().__init__(message, file_path, details)


class UnsupportedFileFormatError(FileProcessingError):
    """不支持的文件格式錯誤"""

    def __init__(self, file_path: str, supported_formats: Optional[list] = None, details: Optional[Dict[str, Any]] = None):
        message = f"不支持的文件格式"
        if supported_formats:
            message += f"，支持格式: {', '.join(supported_formats)}"
        super().__init__(message, file_path, details)


class VectorStoreError(AIResearchAgentError):
    """向量數據庫相關錯誤"""

    def __init__(self, message: str, vectorstore_type: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        if vectorstore_type:
            message = f"{message} (向量庫類型: {vectorstore_type})"
        super().__init__(message, "VECTOR_STORE_ERROR", details)


class EmbeddingError(VectorStoreError):
    """向量嵌入相關錯誤"""

    def __init__(self, message: str, model_name: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        if model_name:
            message = f"{message} (模型: {model_name})"
        super().__init__(message, "EMBEDDING_ERROR", details)


class LLMError(AIResearchAgentError):
    """大語言模型相關錯誤"""

    def __init__(self, message: str, model_name: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        if model_name:
            message = f"{message} (模型: {model_name})"
        super().__init__(message, "LLM_ERROR", details)


class APIRequestError(AIResearchAgentError):
    """API請求相關錯誤"""

    def __init__(self, message: str, api_name: Optional[str] = None, status_code: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        if api_name:
            message = f"{message} (API: {api_name})"
        if status_code:
            message += f" (狀態碼: {status_code})"
        super().__init__(message, "API_REQUEST_ERROR", details)


class ValidationError(AIResearchAgentError):
    """數據驗證相關錯誤"""

    def __init__(self, message: str, field_name: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        if field_name:
            message = f"{message} (欄位: {field_name})"
        super().__init__(message, "VALIDATION_ERROR", details)


class DatabaseError(AIResearchAgentError):
    """數據庫相關錯誤"""

    def __init__(self, message: str, operation: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        if operation:
            message = f"{message} (操作: {operation})"
        super().__init__(message, "DATABASE_ERROR", details)


class ProcessingTimeoutError(AIResearchAgentError):
    """處理超時錯誤"""

    def __init__(self, message: str, timeout_seconds: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        if timeout_seconds:
            message = f"{message} (超時時間: {timeout_seconds}秒)"
        super().__init__(message, "TIMEOUT_ERROR", details)


def handle_exception(func):
    """
    異常處理裝飾器

    用於統一處理函數中的異常，提供更好的錯誤信息
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except AIResearchAgentError:
            # 重新拋出自定義異常
            raise
        except Exception as e:
            # 將其他異常轉換為自定義異常
            raise AIResearchAgentError(
                f"未預期的錯誤: {str(e)}",
                "UNEXPECTED_ERROR",
                {"original_exception": type(e).__name__, "args": args, "kwargs": kwargs}
            )
    return wrapper

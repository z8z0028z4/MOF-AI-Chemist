"""
Backend Config Module
====================

配置管理模組，包含：
- 實驗目錄配置
- API 配置
- 模型配置
- 系統配置
"""

import os
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
from pathlib import Path

from ..core.config import settings, reload_config, validate_config

# Centralized private/runtime data root.
#
# Default layout:
#   local_data/
#     papers/
#     downloaded_papers/
#     experiment/
#     vector_index/{paper_vector,experiment_vector}/
#     parsed_chemicals/
#     metadata_registry.xlsx
#
# Override with MOF_AI_DATA_DIR for local/private storage outside the repo.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if os.getenv("TESTING") == "true":
    DATA_DIR = (PROJECT_ROOT / "tests" / "test_data").resolve()
else:
    DATA_DIR = Path(os.getenv("MOF_AI_DATA_DIR", PROJECT_ROOT / "local_data")).expanduser().resolve()
EXPERIMENT_DIR = str(DATA_DIR / "experiment")
PAPER_DIR = str(DATA_DIR / "papers")
DOWNLOADED_PAPER_DIR = str(DATA_DIR / "downloaded_papers")
MOF_DATA_DIR = str(DATA_DIR / "mof")
VECTOR_INDEX_DIR = str(DATA_DIR / "vector_index")
PARSED_CHEMICALS_DIR = str(DATA_DIR / "parsed_chemicals")
METADATA_REGISTRY_PATH = str(DATA_DIR / "metadata_registry.xlsx")


def relative_to_project(path: str | os.PathLike[str]) -> str:
    """Return a project-relative path when possible for API metadata compatibility."""
    resolved = Path(path).expanduser().resolve()
    try:
        return str(resolved.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(resolved)


def resolve_project_path(path: str | os.PathLike[str]) -> str:
    """Resolve relative paths from the repository root, independent of current cwd."""
    expanded = Path(path).expanduser()
    if expanded.is_absolute():
        return str(expanded.resolve())
    return str((PROJECT_ROOT / expanded).resolve())

# 支持的文件格式
SUPPORTED_FORMATS = {
    "pdf": [".pdf"],
    "word": [".docx", ".doc"],
    "excel": [".xlsx", ".xls"],
    "text": [".txt"]
}

def get_supported_extensions() -> list:
    """
    獲取所有支持的文件擴展名

    Returns:
        list: 支持的文件擴展名列表
    """
    extensions = []
    for format_exts in SUPPORTED_FORMATS.values():
        extensions.extend(format_exts)
    return extensions

# API 配置
API_CONFIG = {
    "prefix": settings.api_prefix,
    "cors_origins": settings.cors_origins,
    "secret_key": settings.secret_key,
    "algorithm": settings.algorithm,
    "access_token_expire_minutes": settings.access_token_expire_minutes
}

# 模型配置
MODEL_CONFIG = {
    "openai_api_key": settings.openai_api_key,
    "openai_model": settings.openai_model,
    "openai_max_tokens": settings.openai_max_tokens
}

# 系統配置
SYSTEM_CONFIG = {
    "app_name": settings.app_name,
    "app_version": settings.app_version,
    "debug": settings.debug,
    "upload_dir": settings.upload_dir,
    "allowed_file_types": settings.allowed_file_types
}

__all__ = [
    "settings",
    "reload_config",
    "validate_config",
    "PROJECT_ROOT",
    "DATA_DIR",
    "EXPERIMENT_DIR",
    "PAPER_DIR",
    "DOWNLOADED_PAPER_DIR",
    "MOF_DATA_DIR",
    "VECTOR_INDEX_DIR",
    "PARSED_CHEMICALS_DIR",
    "METADATA_REGISTRY_PATH",
    "relative_to_project",
    "resolve_project_path",
    "SUPPORTED_FORMATS",
    "get_supported_extensions",
    "API_CONFIG",
    "MODEL_CONFIG",
    "SYSTEM_CONFIG",
]

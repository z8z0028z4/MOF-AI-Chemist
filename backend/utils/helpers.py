"""
通用工具函數模組
============

提供系統中常用的輔助功能，包括：
1. 文件處理工具
2. 文本處理工具
3. 數據驗證工具
4. 格式化工具
"""

import os
import re
import hashlib
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from datetime import datetime

from .exceptions import FileNotFoundError, UnsupportedFileFormatError, ValidationError

# 支持的文件格式 - 直接定義在這裡避免循環導入
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

# 配置日誌
logger = logging.getLogger(__name__)


def sanitize_filename(filename: str, max_length: int = 100) -> str:
    """
    清理文件名，移除不安全的字符

    Args:
        filename: 原始文件名
        max_length: 最大長度限制

    Returns:
        清理後的文件名
    """
    # 移除或替換不安全的字符
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # 移除多餘的空格和點
    filename = re.sub(r'\s+', ' ', filename).strip()
    filename = re.sub(r'\.+', '.', filename)
    # 限制長度
    if len(filename) > max_length:
        name, ext = os.path.splitext(filename)
        filename = name[:max_length-len(ext)] + ext

    return filename


def generate_file_hash(file_path: str, algorithm: str = 'md5') -> str:
    """
    生成文件的哈希值

    Args:
        file_path: 文件路徑
        algorithm: 哈希算法 ('md5', 'sha1', 'sha256')

    Returns:
        文件的哈希值
    """
    hash_functions = {
        'md5': hashlib.md5,
        'sha1': hashlib.sha1,
        'sha256': hashlib.sha256
    }

    if algorithm not in hash_functions:
        raise ValueError(f"不支持的哈希算法: {algorithm}")

    hash_func = hash_functions[algorithm]()

    try:
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_func.update(chunk)
        return hash_func.hexdigest()
    except Exception as e:
        logger.error(f"生成文件哈希失敗 {file_path}: {e}")
        raise


def validate_file_format(file_path: str) -> str:
    """
    驗證文件格式是否支持

    Args:
        file_path: 文件路徑

    Returns:
        文件格式類型

    Raises:
        UnsupportedFileFormatError: 不支持的文件格式
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(file_path)

    file_ext = Path(file_path).suffix.lower()
    supported_extensions = get_supported_extensions()

    if file_ext not in supported_extensions:
        raise UnsupportedFileFormatError(
            file_path,
            supported_formats=supported_extensions
        )

    # 返回文件格式類型
    for format_type, extensions in SUPPORTED_FORMATS.items():
        if file_ext in extensions:
            return format_type

    return "unknown"


def get_file_info(file_path: str) -> Dict[str, Any]:
    """
    獲取文件的詳細信息

    Args:
        file_path: 文件路徑

    Returns:
        文件信息字典
    """
    try:
        stat = os.stat(file_path)
        file_info = {
            "filename": os.path.basename(file_path),
            "file_path": file_path,
            "file_size": stat.st_size,
            "created_time": datetime.fromtimestamp(stat.st_ctime),
            "modified_time": datetime.fromtimestamp(stat.st_mtime),
            "file_format": validate_file_format(file_path),
            "file_hash": generate_file_hash(file_path)
        }
        return file_info
    except Exception as e:
        logger.error(f"獲取文件信息失敗 {file_path}: {e}")
        raise


def clean_text(text: str, remove_newlines: bool = True, remove_extra_spaces: bool = True) -> str:
    """
    清理文本內容

    Args:
        text: 原始文本
        remove_newlines: 是否移除換行符
        remove_extra_spaces: 是否移除多餘空格

    Returns:
        清理後的文本
    """
    if not text:
        return ""

    # 移除換行符
    if remove_newlines:
        text = text.replace('\n', ' ').replace('\r', ' ')

    # 移除多餘空格
    if remove_extra_spaces:
        text = re.sub(r'\s+', ' ', text).strip()

    return text


def extract_text_snippet(text: str, max_length: int = 200, include_ellipsis: bool = True) -> str:
    """
    提取文本片段

    Args:
        text: 原始文本
        max_length: 最大長度
        include_ellipsis: 是否包含省略號

    Returns:
        文本片段
    """
    if not text:
        return ""

    text = clean_text(text)

    if len(text) <= max_length:
        return text

    snippet = text[:max_length]
    if include_ellipsis:
        snippet += "..."

    return snippet


def validate_json_schema(data: Dict[str, Any], required_fields: List[str]) -> bool:
    """
    驗證JSON數據結構

    Args:
        data: 要驗證的數據
        required_fields: 必需字段列表

    Returns:
        是否驗證通過

    Raises:
        ValidationError: 驗證失敗
    """
    if not isinstance(data, dict):
        raise ValidationError("數據必須是字典格式")

    missing_fields = []
    for field in required_fields:
        if field not in data or data[field] is None:
            missing_fields.append(field)

    if missing_fields:
        raise ValidationError(
            f"缺少必需字段: {', '.join(missing_fields)}",
            field_name="required_fields"
        )

    return True


def safe_json_dumps(obj: Any, default: Any = None) -> str:
    """
    安全的JSON序列化

    Args:
        obj: 要序列化的對象
        default: 默認值

    Returns:
        JSON字符串
    """
    try:
        return json.dumps(obj, ensure_ascii=False, indent=2)
    except (TypeError, ValueError) as e:
        logger.warning(f"JSON序列化失敗: {e}")
        return json.dumps(default or str(obj), ensure_ascii=False)


def safe_json_loads(json_str: str, default: Any = None) -> Any:
    """
    安全的JSON反序列化

    Args:
        json_str: JSON字符串
        default: 默認值

    Returns:
        反序列化的對象
    """
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning(f"JSON反序列化失敗: {e}")
        return default


def format_file_size(size_bytes: int) -> str:
    """
    格式化文件大小

    Args:
        size_bytes: 文件大小（字節）

    Returns:
        格式化後的文件大小字符串
    """
    if size_bytes == 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1

    return f"{size_bytes:.1f} {size_names[i]}"


def create_timestamp() -> str:
    """
    創建時間戳字符串

    Returns:
        時間戳字符串 (YYYY-MM-DD_HH-MM-SS)
    """
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def generate_unique_id(prefix: str = "id") -> str:
    """
    生成唯一標識符

    Args:
        prefix: 標識符前綴

    Returns:
        唯一標識符
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    random_suffix = os.urandom(4).hex()
    return f"{prefix}_{timestamp}_{random_suffix}"


def ensure_directory_exists(directory_path: str) -> bool:
    """
    確保目錄存在

    Args:
        directory_path: 目錄路徑

    Returns:
        是否成功創建或已存在
    """
    try:
        Path(directory_path).mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"創建目錄失敗 {directory_path}: {e}")
        return False


def list_files_in_directory(directory_path: str, extensions: Optional[List[str]] = None) -> List[str]:
    """
    列出目錄中的文件

    Args:
        directory_path: 目錄路徑
        extensions: 文件擴展名過濾列表

    Returns:
        文件路徑列表
    """
    if not os.path.exists(directory_path):
        return []

    files = []
    for file_path in Path(directory_path).iterdir():
        if file_path.is_file():
            if extensions is None or file_path.suffix.lower() in extensions:
                files.append(str(file_path))

    return sorted(files)


def copy_file_safely(source_path: str, dest_path: str, overwrite: bool = False) -> bool:
    """
    安全地複製文件

    Args:
        source_path: 源文件路徑
        dest_path: 目標文件路徑
        overwrite: 是否覆蓋已存在的文件

    Returns:
        是否複製成功
    """
    try:
        if not os.path.exists(source_path):
            raise FileNotFoundError(f"源文件不存在: {source_path}")

        if os.path.exists(dest_path) and not overwrite:
            logger.warning(f"目標文件已存在: {dest_path}")
            return False

        # 確保目標目錄存在
        dest_dir = os.path.dirname(dest_path)
        ensure_directory_exists(dest_dir)

        # 複製文件
        import shutil
        shutil.copy2(source_path, dest_path)
        logger.info(f"文件複製成功: {source_path} -> {dest_path}")
        return True

    except Exception as e:
        logger.error(f"文件複製失敗 {source_path} -> {dest_path}: {e}")
        return False

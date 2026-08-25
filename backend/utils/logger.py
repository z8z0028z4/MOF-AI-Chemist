"""
統一日誌配置模組
==============

提供統一的日誌配置，確保所有模組使用一致的日誌格式和級別
"""

import logging
import sys
from typing import Optional
from pathlib import Path

# 日誌格式
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 日誌級別映射
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL
}

def setup_logger(
    name: str,
    level: Optional[str] = None,
    log_file: Optional[Path] = None,
    console_output: bool = True
) -> logging.Logger:
    """
    建立統一的日誌配置

    Args:
        name: 日誌器名稱
        level: 日誌級別 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 日誌文件路徑
        console_output: 是否輸出到控制台

    Returns:
        配置好的日誌器
    """
    logger = logging.getLogger(name)

    # 避免重複配置
    if logger.handlers:
        return logger

    # 設置日誌級別
    log_level = LOG_LEVELS.get(level or "INFO", logging.INFO)
    logger.setLevel(log_level)

    # 建立格式化器
    formatter = logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT)

    # 控制台處理器
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # 文件處理器
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger

def get_logger(name: str) -> logging.Logger:
    """
    獲取已配置的日誌器

    Args:
        name: 日誌器名稱

    Returns:
        日誌器實例
    """
    return logging.getLogger(name)

# 建立默認日誌器
default_logger = setup_logger("ai_research_agent")

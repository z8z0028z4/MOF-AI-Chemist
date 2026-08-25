"""
文件分類服務
============

負責根據文件副檔名將文件分類為論文、實驗資料等類型
"""

import os
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class FileClassifier:
    """文件分類器"""

    # 支援的文件類型
    PAPER_EXTENSIONS = [".pdf", ".docx", ".doc"]
    EXPERIMENT_EXTENSIONS = [".xlsx", ".xls"]

    @classmethod
    def classify_files(cls, file_paths: List[str]) -> Dict[str, List[str]]:
        """
        根據副檔名將檔案分類為論文或實驗資料

        Args:
            file_paths: 文件路徑列表

        Returns:
            分類結果字典
        """
        papers: List[str] = []
        experiments: List[str] = []
        others: List[str] = []

        for path in file_paths:
            ext = os.path.splitext(path)[1].lower()
            if ext in cls.PAPER_EXTENSIONS:
                papers.append(path)
            elif ext in cls.EXPERIMENT_EXTENSIONS:
                experiments.append(path)
            else:
                others.append(path)

        # 確定主要類型
        if papers and experiments:
            file_type = "mixed"
        elif papers:
            file_type = "papers"
        elif experiments:
            file_type = "experiments"
        else:
            file_type = "others"

        result = {
            "type": file_type,
            "papers": papers,
            "experiments": experiments,
            "others": others
        }

        logger.info(f"📂 文件分類完成 - 類型: {file_type}")
        logger.info(f"   📚 論文: {len(papers)} 個")
        logger.info(f"   🧪 實驗: {len(experiments)} 個")
        logger.info(f"   📄 其他: {len(others)} 個")

        return result

    @classmethod
    def get_supported_extensions(cls) -> Dict[str, List[str]]:
        """獲取支援的文件類型"""
        return {
            "papers": cls.PAPER_EXTENSIONS,
            "experiments": cls.EXPERIMENT_EXTENSIONS
        }

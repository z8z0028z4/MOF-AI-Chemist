"""
文件處理服務
============

負責處理上傳的文件，包括論文和實驗資料的處理
"""

import os
import sys
import time
import logging
import shutil
from typing import List, Dict, Any, Callable

# 添加原項目路徑到 sys.path
# sys.path.append(os.path.join(os.path.dirname(__file__), '../../../app'))  # 已重組，不再需要

from backend.services.file_service import process_uploaded_files
from backend.services.embedding_service import embed_documents_from_metadata, embed_experiment_txt_batch
from backend.services.excel_service import export_new_experiments_to_txt
from backend.config import EXPERIMENT_DIR

from .file_classifier import FileClassifier
from .progress_tracker import progress_tracker

logger = logging.getLogger(__name__)


class FileProcessor:
    """文件處理器"""

    def __init__(self):
        self.classifier = FileClassifier()

    async def process_files(self, task_id: str, file_paths: List[str], temp_dir: str) -> None:
        """
        處理文件的主要方法

        Args:
            task_id: 任務 ID
            file_paths: 文件路徑列表
            temp_dir: 臨時目錄
        """
        start_time = time.time()
        logger.info(f"🚀 開始處理任務 {task_id}，共 {len(file_paths)} 個文件")

        try:
            # 更新狀態為處理中
            progress_tracker.update_task(task_id, status="processing", progress=0, message="開始處理...")

            # 分類文件
            file_info = self.classifier.classify_files(file_paths)
            progress_tracker.update_task(task_id, progress=10, message="文件分類完成")

            # 處理論文資料
            paper_results = await self._process_papers(task_id, file_info)

            # 處理實驗資料
            experiment_results = await self._process_experiments(task_id, file_info)

            # 更新向量統計
            vector_stats = await self._update_vector_stats()

            # 完成任務
            results = {
                "paper_results": paper_results,
                "experiment_results": experiment_results,
                "file_info": file_info,
                "vector_stats": vector_stats
            }

            progress_tracker.complete_task(task_id, results)

        except Exception as e:
            logger.error(f"❌ 任務 {task_id} 處理失敗: {e}")
            progress_tracker.fail_task(task_id, str(e))
        finally:
            # 清理臨時目錄
            self._cleanup_temp_dir(temp_dir)

    async def _process_papers(self, task_id: str, file_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """處理論文資料"""
        papers = file_info.get("papers", [])
        if not papers:
            return []

        logger.info(f"📚 開始處理 {len(papers)} 個論文文件")

        # 創建進度回調
        progress_callback = progress_tracker.create_progress_callback(
            task_id, start_progress=10, end_progress=50
        )

        # 提取元數據
        progress_callback("📄 開始元數據提取...", 0)
        metadata_list = process_uploaded_files(papers, status_callback=progress_callback)

        # 向量嵌入
        progress_callback("🔢 開始向量嵌入...", 50)
        embed_progress_callback = progress_tracker.create_progress_callback(
            task_id, start_progress=50, end_progress=90
        )
        embed_documents_from_metadata(metadata_list, status_callback=embed_progress_callback)

        logger.info(f"✅ 論文處理完成，共處理 {len(metadata_list)} 個文件")
        return metadata_list

    async def _process_experiments(self, task_id: str, file_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """處理實驗資料"""
        experiments = file_info.get("experiments", [])
        if not experiments:
            return []

        logger.info(f"🧪 開始處理 {len(experiments)} 個實驗文件")

        experiment_results = []
        progress_callback = progress_tracker.create_progress_callback(
            task_id, start_progress=90, end_progress=98
        )

        for i, file_path in enumerate(experiments):
            try:
                progress_callback(f"處理實驗文件 {i+1}/{len(experiments)}: {os.path.basename(file_path)}")

                # 轉換 Excel 為 TXT
                df, txt_paths = export_new_experiments_to_txt(
                    excel_path=file_path,
                    output_dir=EXPERIMENT_DIR
                )

                # 向量嵌入
                result = embed_experiment_txt_batch(txt_paths)

                experiment_results.append({
                    "file": file_path,
                    "txt_paths": txt_paths,
                    "embedded_count": len(txt_paths)
                })

            except Exception as e:
                logger.error(f"❌ 實驗文件處理失敗 {os.path.basename(file_path)}: {e}")
                experiment_results.append({
                    "file": file_path,
                    "error": str(e)
                })

        logger.info(f"✅ 實驗處理完成，共處理 {len(experiments)} 個文件")
        return experiment_results

    async def _update_vector_stats(self) -> Dict[str, int]:
        """更新向量統計緩存"""
        try:
            from main import update_vector_stats_cache, get_cached_vector_stats
            update_vector_stats_cache()
            cached_stats = get_cached_vector_stats()

            vector_stats = {
                "paper_vectors": cached_stats["paper_vectors"],
                "experiment_vectors": cached_stats["experiment_vectors"],
                "total_vectors": cached_stats["total_vectors"]
            }

            logger.info(f"📊 向量統計更新完成: {vector_stats}")
            return vector_stats

        except Exception as e:
            logger.error(f"⚠️ 無法更新向量統計緩存: {e}")
            return {"paper_vectors": 0, "experiment_vectors": 0, "total_vectors": 0}

    def _cleanup_temp_dir(self, temp_dir: str) -> None:
        """清理臨時目錄"""
        try:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                logger.info(f"🧹 清理臨時目錄: {temp_dir}")
        except Exception as e:
            logger.warning(f"⚠️ 清理臨時目錄失敗: {e}")


# 全局文件處理器實例
file_processor = FileProcessor()

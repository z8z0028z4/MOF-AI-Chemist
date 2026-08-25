"""
化學品服務模組
============

統一管理化學品查詢和處理邏輯，提供快取機制和錯誤處理
"""

import time
from typing import List, Dict, Any, Tuple

from ..utils.logger import get_logger
from ..utils.exceptions import APIRequestError
from .pubchem_service import chemical_metadata_extractor, get_single_chemical
from .smiles_drawer import smiles_drawer
from .chemical_database_service import chemical_db_service

logger = get_logger(__name__)


class ChemicalService:
    """化學品服務類"""

    def __init__(self):
        self.cache = {}
        self.cache_ttl = 3600  # 快取1小時

    def extract_chemicals_from_text(self, text: str) -> Tuple[List[Dict[str, Any]], List[str], str]:
        """
        從文本中提取化學品信息

        Args:
            text: 包含化學品信息的文本

        Returns:
            Tuple[List[Dict], List[str], str]: (化學品列表, 未找到的化學品, 處理後的文本)
        """
        try:
            logger.info("開始從文本中提取化學品信息")
            start_time = time.time()

            # 檢查快取
            cache_key = hash(text)
            if cache_key in self.cache:
                cache_time, result = self.cache[cache_key]
                if time.time() - cache_time < self.cache_ttl:
                    logger.info("使用快取的化學品查詢結果")
                    return result

            # 調用原始函數
            result = chemical_metadata_extractor(text)

            # 儲存到快取
            self.cache[cache_key] = (time.time(), result)

            end_time = time.time()
            logger.info(f"化學品提取完成，耗時: {end_time - start_time:.2f}秒")

            return result

        except Exception as e:
            logger.error(f"化學品提取失敗: {e}")
            raise APIRequestError(f"化學品提取失敗: {str(e)}")

    def get_chemical_info(self, chemical_name: str) -> Dict[str, Any]:
        """
        獲取單個化學品信息

        Args:
            chemical_name: 化學品名稱

        Returns:
            化學品信息字典
        """
        try:
            logger.info(f"查詢化學品信息: {chemical_name}")

            # 檢查快取
            if chemical_name in self.cache:
                cache_time, result = self.cache[chemical_name]
                if time.time() - cache_time < self.cache_ttl:
                    logger.info(f"使用快取的化學品信息: {chemical_name}")
                    return result

            # 調用單個化學品查詢函數
            result = get_single_chemical(chemical_name)

            if result and not result.get("error"):
                # 儲存到快取
                self.cache[chemical_name] = (time.time(), result)
                return result
            else:
                raise APIRequestError(f"未找到化學品: {chemical_name}")

        except Exception as e:
            logger.error(f"化學品查詢失敗: {e}")
            raise APIRequestError(f"化學品查詢失敗: {str(e)}")

    def batch_get_chemicals(self, chemical_names: List[str]) -> Dict[str, Any]:
        """
        批量查詢化學品信息

        Args:
            chemical_names: 化學品名稱列表

        Returns:
            化學品信息字典，鍵為化學品名稱
        """
        try:
            logger.info(f"批量查詢化學品信息: {len(chemical_names)} 個")
            results = {}

            for name in chemical_names:
                try:
                    results[name] = self.get_chemical_info(name)
                except APIRequestError as e:
                    logger.warning(f"化學品 {name} 查詢失敗: {e}")
                    results[name] = {"error": str(e)}

            return results

        except Exception as e:
            logger.error(f"批量化學品查詢失敗: {e}")
            raise APIRequestError(f"批量化學品查詢失敗: {str(e)}")

    def clear_cache(self):
        """清除快取"""
        self.cache.clear()
        logger.info("化學品服務快取已清除")

    def get_cache_stats(self) -> Dict[str, Any]:
        """獲取快取統計信息"""
        current_time = time.time()
        valid_entries = 0
        expired_entries = 0

        for cache_time, _ in self.cache.values():
            if current_time - cache_time < self.cache_ttl:
                valid_entries += 1
            else:
                expired_entries += 1

        return {
            "total_entries": len(self.cache),
            "valid_entries": valid_entries,
            "expired_entries": expired_entries,
            "cache_ttl": self.cache_ttl
        }

    def add_smiles_drawing(self, chemical_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        為化學品數據添加 SMILES 繪製的分子結構圖

        Args:
            chemical_data: 化學品數據字典

        Returns:
            添加了結構圖的化學品數據
        """
        try:
            logger.info(f"🔍 [DEBUG] 開始為化學品添加 SMILES 繪製: {chemical_data.get('name', 'Unknown')}")
            logger.info(f"🔍 [DEBUG] 化學品數據鍵: {list(chemical_data.keys())}")

            smiles = chemical_data.get('smiles', '')
            logger.info(f"🔍 [DEBUG] SMILES 字符串: {smiles}")

            if not smiles:
                logger.warning("化學品沒有 SMILES 數據，無法繪製結構圖")
                return chemical_data

            # 檢查 RDKit 是否可用
            if not hasattr(smiles_drawer, 'validate_smiles'):
                logger.error("❌ SMILES drawer 未正確初始化")
                return chemical_data

            # 驗證 SMILES
            if not smiles_drawer.validate_smiles(smiles):
                logger.warning(f"無效的 SMILES: {smiles}")
                return chemical_data

            logger.info(f"✅ SMILES 驗證通過: {smiles}")

            # 生成 SVG 結構圖
            logger.info(f"🔍 [DEBUG] 開始生成 SVG 結構圖...")
            svg_structure = smiles_drawer.smiles_to_svg(smiles, width=300, height=300)
            if svg_structure:
                chemical_data['svg_structure'] = svg_structure
                logger.info(f"✅ 成功為化學品 {chemical_data.get('name', 'Unknown')} 生成 SVG 結構圖")
            else:
                logger.warning(f"❌ SVG 結構圖生成失敗: {chemical_data.get('name', 'Unknown')}")

            # 生成 PNG 結構圖（Base64）
            logger.info(f"🔍 [DEBUG] 開始生成 PNG 結構圖...")
            png_structure = smiles_drawer.smiles_to_png_base64(smiles, width=300, height=300)
            if png_structure:
                chemical_data['png_structure'] = png_structure
                logger.info(f"✅ 成功為化學品 {chemical_data.get('name', 'Unknown')} 生成 PNG 結構圖")
            else:
                logger.warning(f"❌ PNG 結構圖生成失敗: {chemical_data.get('name', 'Unknown')}")

            logger.info(f"🔍 [DEBUG] 最終化學品數據鍵: {list(chemical_data.keys())}")
            return chemical_data

        except Exception as e:
            logger.error(f"❌ SMILES 繪製失敗: {e}")
            logger.error(f"❌ 化學品名稱: {chemical_data.get('name', 'Unknown')}")
            return chemical_data

    def extract_chemicals_with_drawings(self, text: str) -> Tuple[List[Dict[str, Any]], List[str], str]:
        """
        從文本中提取化學品信息並添加分子結構圖

        Args:
            text: 包含化學品信息的文本

        Returns:
            Tuple[List[Dict], List[str], str]: (化學品列表, 未找到的化學品, 處理後的文本)
        """
        try:
            # 先提取化學品信息
            chemicals, not_found, cleaned_text = self.extract_chemicals_from_text(text)

            # 為每個化學品添加結構圖
            enhanced_chemicals = []
            for chemical in chemicals:
                enhanced_chemical = self.add_smiles_drawing(chemical)
                enhanced_chemicals.append(enhanced_chemical)

            logger.info(f"成功為 {len(enhanced_chemicals)} 個化學品添加結構圖")
            return enhanced_chemicals, not_found, cleaned_text

        except Exception as e:
            logger.error(f"化學品提取和繪製失敗: {e}")
            raise APIRequestError(f"化學品提取和繪製失敗: {str(e)}")

    def batch_add_drawings(self, chemicals_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        批量為化學品列表添加結構圖

        Args:
            chemicals_list: 化學品數據列表

        Returns:
            添加了結構圖的化學品列表
        """
        try:
            enhanced_chemicals = []
            for chemical in chemicals_list:
                enhanced_chemical = self.add_smiles_drawing(chemical)
                enhanced_chemicals.append(enhanced_chemical)

            logger.info(f"批量添加結構圖完成: {len(enhanced_chemicals)} 個化學品")
            return enhanced_chemicals

        except Exception as e:
            logger.error(f"批量添加結構圖失敗: {e}")
            return chemicals_list  # 返回原始數據，不拋出異常

    def get_chemical_with_database_lookup(self, chemical_name: str, include_structure: bool = True, save_to_db: bool = True) -> Dict[str, Any]:
        """
        查詢化學品信息，優先從數據庫獲取，如果沒有則從API獲取並保存到數據庫

        Args:
            chemical_name: 化學品名稱
            include_structure: 是否包含分子結構圖
            save_to_db: 是否保存到數據庫

        Returns:
            化學品信息字典
        """
        try:
            logger.info(f"查詢化學品信息: {chemical_name}")

            # 首先嘗試從數據庫獲取
            db_record = chemical_db_service.get_chemical_by_name(chemical_name)
            if db_record:
                logger.info(f"從數據庫獲取化學品信息: {chemical_name}")
                result = self._db_record_to_dict(db_record)

                # 如果沒有結構圖且需要生成，則生成結構圖
                if include_structure and not result.get('svg_structure') and not result.get('png_structure'):
                    logger.info(f"為數據庫化學品生成結構圖: {chemical_name}")
                    result = self.add_smiles_drawing(result)

                return result

            # 數據庫中沒有，從API獲取
            logger.info(f"數據庫中未找到，從API查詢: {chemical_name}")
            result = get_single_chemical(chemical_name)

            if not result or result.get("error"):
                logger.warning(f"API查詢失敗: {chemical_name}")
                return {"name": chemical_name, "error": "未找到化學品信息"}

            # 添加分子結構圖
            if include_structure:
                result = self.add_smiles_drawing(result)

            # 保存到數據庫
            if save_to_db:
                try:
                    success = chemical_db_service.save_chemical(result)
                    if success:
                        logger.info(f"化學品數據已保存到數據庫: {chemical_name}")
                        result['saved_to_database'] = True
                    else:
                        logger.warning(f"保存到數據庫失敗: {chemical_name}")
                        result['saved_to_database'] = False
                except Exception as e:
                    logger.error(f"保存到數據庫時發生錯誤: {e}")
                    result['saved_to_database'] = False

            return result

        except Exception as e:
            logger.error(f"化學品查詢失敗: {e}")
            raise APIRequestError(f"化學品查詢失敗: {str(e)}")

    def batch_get_chemicals_with_database(self, chemical_names: List[str], include_structure: bool = True, save_to_db: bool = True) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        批量查詢化學品信息，優先從數據庫獲取

        Args:
            chemical_names: 化學品名稱列表
            include_structure: 是否包含分子結構圖
            save_to_db: 是否保存到數據庫

        Returns:
            Tuple[List[Dict], List[str]]: (化學品列表, 未找到的化學品列表)
        """
        try:
            results = []
            not_found = []

            for chemical_name in chemical_names:
                try:
                    result = self.get_chemical_with_database_lookup(
                        chemical_name, include_structure, save_to_db
                    )

                    if result.get("error"):
                        not_found.append(chemical_name)
                    else:
                        results.append(result)

                except Exception as e:
                    logger.error(f"查詢化學品失敗: {chemical_name}, {e}")
                    not_found.append(chemical_name)

            logger.info(f"批量查詢完成: 成功 {len(results)} 個, 失敗 {len(not_found)} 個")
            return results, not_found

        except Exception as e:
            logger.error(f"批量查詢化學品失敗: {e}")
            raise APIRequestError(f"批量查詢化學品失敗: {str(e)}")

    def search_chemicals_in_database(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        在數據庫中搜索化學品

        Args:
            query: 搜索查詢
            limit: 結果數量限制

        Returns:
            化學品信息列表
        """
        try:
            db_records = chemical_db_service.search_chemicals(query, limit)
            return [self._db_record_to_dict(record) for record in db_records]

        except Exception as e:
            logger.error(f"搜索化學品失敗: {e}")
            return []

    def get_database_stats(self) -> Dict[str, Any]:
        """
        獲取數據庫統計信息

        Returns:
            統計信息字典
        """
        try:
            return chemical_db_service.get_database_stats()
        except Exception as e:
            logger.error(f"獲取數據庫統計失敗: {e}")
            return {}

    def _db_record_to_dict(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        將數據庫記錄轉換為字典格式

        Args:
            record: 數據庫記錄字典

        Returns:
            化學品信息字典
        """
        try:
            # 直接返回記錄，因為現在已經是字典格式
            record["saved_to_database"] = True
            return record
        except Exception as e:
            logger.error(f"轉換數據庫記錄失敗: {e}")
            return {"name": record.get("name", "Unknown") if record else "Unknown", "error": "數據轉換失敗"}


# 全局服務實例
chemical_service = ChemicalService()


# 向後相容的函數
def extract_chemicals_from_text(text: str) -> Tuple[List[Dict[str, Any]], List[str], str]:
    """
    向後相容的化學品提取函數

    Args:
        text: 包含化學品信息的文本

    Returns:
        Tuple[List[Dict], List[str], str]: (化學品列表, 未找到的化學品, 處理後的文本)
    """
    return chemical_service.extract_chemicals_from_text(text)


def get_chemical_info(chemical_name: str) -> Dict[str, Any]:
    """
    向後相容的化學品查詢函數

    Args:
        chemical_name: 化學品名稱

    Returns:
        化學品信息字典
    """
    return chemical_service.get_chemical_info(chemical_name)

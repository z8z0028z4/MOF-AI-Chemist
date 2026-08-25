"""
AI 研究助理 - Semantic Scholar 元數據查詢模塊
==========================================

這個模塊負責從 Semantic Scholar API 查詢論文元數據，包括：
1. 基於 DOI 的精確查詢
2. 基於標題的模糊查詢和匹配
3. 智能重試機制和頻率限制處理
4. API 金鑰支援和錯誤處理

架構說明：
- 優先使用 DOI 查詢（更準確）
- 備用標題查詢（支援模糊匹配）
- 智能延遲避免頻率限制
- 自動重試和錯誤恢復
- 可配置 API 金鑰提高限制

技術細節：
- 基礎延遲：2-4 秒避免請求過快
- 429 錯誤延遲：20-40 秒
- 超時設定：20 秒
- 最佳匹配算法：基於詞彙重疊計算相似度

最佳實踐遵循：
- 集中配置管理（支援環境變數 SEMANTIC_SCHOLAR_API_KEY）
- 統一錯誤處理和日誌記錄
- 智能重試策略避免無效請求
- 模組化設計便於維護和測試
"""

import requests
import time
import random
import os
import logging
from backend.core.tls import tls_verify_setting

# 配置日誌
logger = logging.getLogger(__name__)

def lookup_semantic_scholar_metadata(doi=None, title=None, max_retries=3, api_key=None):
    """
    查詢Semantic Scholar元數據

    Args:
        doi: DOI號碼
        title: 論文標題
        max_retries: 最大重試次數
        api_key: 可選的API金鑰，用於提高請求限制

    Returns:
        Dict: 元數據字典
    """
    base_url = "https://api.semanticscholar.org/graph/v1/paper"
    fields = "title,authors,year,venue,url,externalIds"

    # 從環境變數獲取API金鑰（如果未提供）
    if not api_key:
        api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")

    # 優先使用DOI查詢
    if doi:
        return _query_by_doi(base_url, doi, fields, max_retries, api_key)

    # 備用標題查詢
    elif title:
        return _query_by_title(base_url, title, fields, max_retries, api_key)

    else:
        logger.warning("⚠️ 沒有提供DOI或標題，無法查詢")
        return {}

def _query_by_doi(base_url, doi, fields, max_retries, api_key=None):
    """使用DOI查詢"""
    url = f"{base_url}/DOI:{doi}?fields={fields}"

    # 準備請求標頭
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    if api_key:
        headers["x-api-key"] = api_key

    for attempt in range(max_retries):
        try:
            # 添加基礎延遲避免請求過快
            if attempt > 0:
                delay = random.uniform(2, 4)
                logger.info(f"   💤 等待 {delay:.1f} 秒後重試...")
                time.sleep(delay)

            response = requests.get(url, headers=headers, verify=tls_verify_setting(), timeout=15)

            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ DOI查詢成功: {doi}")
                return data
            elif response.status_code == 404:
                logger.warning(f"⚠️ DOI不存在: {doi}")
                return {}
            elif response.status_code == 429:  # Rate limit
                wait_time = random.uniform(15, 30)  # 增加等待時間
                logger.warning(f"⚠️ DOI查詢被限制 (嘗試 {attempt+1}/{max_retries})，等待 {wait_time:.1f} 秒")
                if attempt < max_retries - 1:
                    time.sleep(wait_time)
                    continue
                return {}
            else:
                logger.warning(f"⚠️ DOI查詢失敗 (嘗試 {attempt+1}/{max_retries}): {response.status_code}")
                if attempt < max_retries - 1:
                    time.sleep(random.uniform(3, 6))  # 增加延遲時間
                    continue
                return {}

        except requests.exceptions.Timeout:
            logger.warning(f"⚠️ DOI查詢超時 (嘗試 {attempt+1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(random.uniform(3, 6))
                continue
            return {}
        except Exception as e:
            logger.warning(f"⚠️ DOI查詢異常 (嘗試 {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(random.uniform(2, 4))
                continue
            return {}

    return {}

def _query_by_title(base_url, title, fields, max_retries, api_key=None):
    """使用標題查詢（備用方案）"""
    search_url = f"{base_url}/search"

    # 準備請求標頭
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    if api_key:
        headers["x-api-key"] = api_key

    for attempt in range(max_retries):
        try:
            # 添加基礎延遲，即使是第一次請求也要延遲
            base_delay = random.uniform(2, 4)  # 基礎延遲 2-4 秒
            if attempt > 0:
                retry_delay = random.uniform(5, 10)  # 重試額外延遲
                total_delay = base_delay + retry_delay
                logger.info(f"   💤 第 {attempt+1} 次嘗試，等待 {total_delay:.1f} 秒...")
                time.sleep(total_delay)
            else:
                logger.info(f"   💤 基礎延遲 {base_delay:.1f} 秒避免請求過快...")
                time.sleep(base_delay)

            # 嘗試不同的查詢參數
            params = {
                "query": title,
                "fields": fields,
                "limit": 3,  # 增加限制數量以提高匹配機會
                "offset": 0
            }

            logger.info(f"   🔍 查詢標題: {title[:60]}...")

            response = requests.get(
                search_url,
                params=params,
                headers=headers,
                verify=tls_verify_setting(),
                timeout=20  # 增加超時時間
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("data") and len(data["data"]) > 0:
                    logger.info(f"✅ 標題查詢成功: {title[:50]}...")

                    # 嘗試找到最佳匹配
                    best_match = _find_best_title_match(title, data["data"])
                    return best_match
                else:
                    logger.warning(f"⚠️ 標題查詢無結果: {title[:50]}...")
                    return {}
            elif response.status_code == 429:  # Rate limit
                wait_time = random.uniform(20, 40)  # 大幅增加等待時間
                logger.warning(f"⚠️ 標題查詢被限制 (嘗試 {attempt+1}/{max_retries})，等待 {wait_time:.1f} 秒")
                if attempt < max_retries - 1:
                    time.sleep(wait_time)
                    continue
                return {}
            elif response.status_code == 403:  # Forbidden
                wait_time = random.uniform(10, 20)
                logger.warning(f"⚠️ 標題查詢被拒絕訪問 (嘗試 {attempt+1}/{max_retries})，等待 {wait_time:.1f} 秒")
                if attempt < max_retries - 1:
                    time.sleep(wait_time)
                    continue
                return {}
            else:
                logger.warning(f"⚠️ 標題查詢失敗 (嘗試 {attempt+1}/{max_retries}): {response.status_code}")
                if attempt < max_retries - 1:
                    time.sleep(random.uniform(5, 10))  # 增加一般錯誤的延遲
                    continue
                return {}

        except requests.exceptions.Timeout:
            logger.warning(f"⚠️ 標題查詢超時 (嘗試 {attempt+1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(random.uniform(5, 10))
                continue
            return {}
        except Exception as e:
            logger.warning(f"⚠️ 標題查詢異常 (嘗試 {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(random.uniform(3, 6))
                continue
            return {}

    return {}

def _find_best_title_match(query_title, results):
    """從多個結果中找到最佳標題匹配"""
    if not results:
        return {}

    # 簡單的相似度計算
    def calculate_similarity(title1, title2):
        if not title1 or not title2:
            return 0.0

        words1 = set(title1.lower().split())
        words2 = set(title2.lower().split())

        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))

        return intersection / union if union > 0 else 0.0

    best_match = results[0]
    best_score = 0.0

    for result in results:
        result_title = result.get('title', '')
        score = calculate_similarity(query_title, result_title)

        if score > best_score:
            best_score = score
            best_match = result

    logger.info(f"   📊 最佳匹配相似度: {best_score:.2f}")
    logger.info(f"   📄 匹配標題: {best_match.get('title', 'N/A')[:60]}...")

    return best_match

if __name__ == "__main__":
    # 測試用
    test_doi = "10.1016/j.matchemphys.2019.122601"
    metadata = lookup_semantic_scholar_metadata(doi=test_doi)
    print(metadata)

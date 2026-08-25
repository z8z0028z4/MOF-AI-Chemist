"""
AI 研究助理 - Europe PMC醫學文獻數據庫處理模塊
==========================================

這個模塊負責與Europe PMC（歐洲醫學文獻數據庫）進行交互，提供醫學和生命科學文獻的搜索和下載功能。
主要功能包括：
1. 醫學文獻搜索和檢索
2. PDF文獻下載和存儲
3. 文獻元數據提取
4. 相關性評分和排序

架構說明：
- 使用Europe PMC REST API進行文獻搜索
- 支持OR邏輯查詢和關鍵詞匹配
- 提供PDF文獻下載功能
- 集成到搜索代理中

⚠️ 注意：此模塊專門處理醫學和生命科學文獻，依賴於Europe PMC API的可用性
"""

import requests
import warnings
from typing import List, Dict
import os
# 兼容性導入：支持相對導入和絕對導入
try:
    from .document_renamer import sanitize_filename
except ImportError:
    # 當作為模組導入時使用絕對導入
    from document_renamer import sanitize_filename

# ==================== 警告配置 ====================
# 忽略未驗證HTTPS請求的警告
warnings.filterwarnings("ignore", message="Unverified HTTPS request")


def search_source(keywords: List[str], limit: int = 5, or_batch: int = 30) -> List[Dict]:
    """
    在Europe PMC中搜索醫學文獻

    功能：
    1. 使用OR邏輯查詢ABSTRACT字段
    2. 根據摘要中關鍵詞出現次數排序
    3. 返回高相關性的論文，包含PMCID和PDF訪問
    4. 支持批量查詢和結果過濾

    參數：
        keywords (List[str]): 搜索關鍵詞列表
        limit (int): 返回結果的最大數量
        or_batch (int): 初始查詢的批次大小

    返回：
        List[Dict]: 包含文獻信息的結果列表

    技術細節：
    - 使用OR查詢語法提高檢索範圍
    - 基於關鍵詞在摘要中的出現頻率評分
    - 優先返回有PMCID和PDF訪問的文獻
    - 支持多個關鍵詞的組合查詢

    示例：
        >>> results = search_source(["cancer", "therapy"], limit=3)
        >>> print(f"找到 {len(results)} 篇相關文獻")
    """

    def run_query(query: str) -> List[Dict]:
        """
        執行Europe PMC API查詢

        功能：
        1. 構建API查詢URL
        2. 發送HTTP請求到Europe PMC
        3. 解析JSON響應
        4. 提取文獻元數據

        參數：
            query (str): 查詢字符串

        返回：
            List[Dict]: 原始查詢結果
        """
        # 構建Europe PMC API查詢URL
        url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query={query}&format=json&pageSize={or_batch}"

        # 發送HTTP請求
        response = requests.get(url, verify=False)

        # 檢查響應狀態
        if response.status_code != 200:
            print(f"❌ Europe PMC API錯誤：{response.status_code}")
            return []

        # 解析JSON響應
        items = response.json().get("resultList", {}).get("result", [])
        results = []

        # 提取每個文獻的信息
        for item in items:
            pmcid = item.get("pmcid")
            if not pmcid:
                continue

            # 提取文獻基本信息
            title = item.get("title", "no_title")
            doi = item.get("doi", "")
            source = item.get("source", "")
            abstract = item.get("abstractText", "") or ""

            # 構建PDF下載URL
            pdf_url = f"https://europepmc.org/articles/{pmcid}?pdf=render"

            # 構建結果字典
            results.append({
                "title": title,
                "pdf_url": pdf_url,
                "doi": doi,
                "pmcid": pmcid,
                "source": source,
                "abstract": abstract,
            })

        return results

    def score_result(item: Dict, keywords: List[str]) -> int:
        """
        計算文獻的相關性評分

        功能：
        1. 統計關鍵詞在摘要中出現的次數
        2. 返回相關性評分（出現次數越多評分越高）

        參數：
            item (Dict): 文獻信息
            keywords (List[str]): 關鍵詞列表

        返回：
            int: 相關性評分
        """
        abstract = item.get("abstract", "").lower()
        return sum(1 for kw in keywords if kw.lower() in abstract)

    # ==================== 執行查詢 ====================
    # 構建OR查詢語法
    or_query = " OR ".join([f'ABSTRACT:"{kw}"' for kw in keywords])
    print(f"🔍 執行Europe PMC查詢：{or_query}")

    # 執行初始查詢
    raw_results = run_query(or_query)
    print(f"📚 找到 {len(raw_results)} 篇原始文獻")

    # ==================== 結果排序 ====================
    # 根據摘要中關鍵詞出現次數進行排序
    scored_results = sorted(raw_results, key=lambda r: score_result(r, keywords), reverse=True)

    # 返回前N個高相關性結果
    final_results = scored_results[:limit]
    print(f"🎯 返回前 {len(final_results)} 個高相關性文獻")

    return final_results


def download_and_store(record: Dict, folder: str) -> str:
    """
    下載並存儲PDF文獻

    功能：
    1. 從Europe PMC下載PDF文獻
    2. 使用重定向機制處理PDF URL
    3. 保存到本地文件系統
    4. 返回保存的文件路徑

    參數：
        record (Dict): 包含文獻信息的記錄
        folder (str): 保存目錄路徑

    返回：
        str: 保存的文件路徑，失敗時返回空字符串

    技術細節：
    - 使用Europe PMC的重定向機制
    - 添加User-Agent頭部避免被阻擋
    - 驗證Content-Type確保下載的是PDF
    - 自動創建保存目錄

    下載流程：
    1. 提取文獻標題和PMCID
    2. 構建PDF下載URL
    3. 發送HTTP請求並跟隨重定向
    4. 驗證響應內容類型
    5. 保存PDF文件到本地
    """
    # 提取文獻信息
    title = sanitize_filename(record.get("title", "no_title"))
    pmcid = record.get("pmcid", "")
    pdf_url = record.get("pdf_url")

    # 驗證必要信息
    if not pmcid or not pdf_url:
        print("❌ 缺少PMCID或PDF連結")
        return ""

    # 創建保存目錄
    os.makedirs(folder, exist_ok=True)
    filepath = os.path.join(folder, f"{title}_{pmcid}.pdf")

    # 設置HTTP請求頭部
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        # 發送HTTP請求下載PDF
        r = requests.get(
            pdf_url,
            timeout=20,
            verify=False,
            headers=headers,
            allow_redirects=True
        )

        # 檢查響應狀態和內容類型
        if r.ok and "pdf" in r.headers.get("Content-Type", "").lower():
            # 保存PDF文件
            with open(filepath, "wb") as f:
                f.write(r.content)
            print(f"✅ 已下載：{filepath}")
            return filepath
        else:
            print(f"⚠️ PDF響應異常（可能仍為HTML）：{pdf_url}")

    except Exception as e:
        print(f"❌ 下載錯誤：{e}")

    return ""


# ==================== 輔助函數 ====================

def validate_europepmc_api():
    """
    驗證Europe PMC API是否可用

    功能：
    1. 發送測試請求到Europe PMC API
    2. 檢查響應狀態和格式
    3. 返回API可用性狀態

    返回：
        bool: API是否可用
    """
    try:
        test_url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=test&format=json&pageSize=1"
        response = requests.get(test_url, verify=False, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if "resultList" in data:
                print("✅ Europe PMC API驗證成功")
                return True
            else:
                print("❌ Europe PMC API響應格式異常")
                return False
        else:
            print(f"❌ Europe PMC API響應錯誤：{response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Europe PMC API連接失敗：{e}")
        return False


def get_publication_info(pmcid: str) -> Dict:
    """
    獲取文獻的詳細出版信息

    功能：
    1. 根據PMCID查詢文獻詳細信息
    2. 提取作者、期刊、出版日期等
    3. 返回結構化的出版信息

    參數：
        pmcid (str): PubMed Central ID

    返回：
        Dict: 包含詳細出版信息的字典
    """
    try:
        url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=PMCID:{pmcid}&format=json"
        response = requests.get(url, verify=False, timeout=10)

        if response.status_code == 200:
            data = response.json()
            results = data.get("resultList", {}).get("result", [])

            if results:
                item = results[0]
                return {
                    "pmcid": pmcid,
                    "title": item.get("title", ""),
                    "authors": item.get("authorString", ""),
                    "journal": item.get("journalTitle", ""),
                    "publication_date": item.get("firstPublicationDate", ""),
                    "doi": item.get("doi", ""),
                    "abstract": item.get("abstractText", "")
                }

        return {}

    except Exception as e:
        print(f"❌ 獲取出版信息失敗：{e}")
        return {}


def search_by_doi(doi: str) -> Dict:
    """
    根據DOI搜索文獻

    功能：
    1. 使用DOI在Europe PMC中搜索文獻
    2. 返回文獻的完整信息
    3. 提供DOI到PMCID的轉換

    參數：
        doi (str): 數字對象標識符

    返回：
        Dict: 文獻信息字典
    """
    try:
        url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:{doi}&format=json"
        response = requests.get(url, verify=False, timeout=10)

        if response.status_code == 200:
            data = response.json()
            results = data.get("resultList", {}).get("result", [])

            if results:
                return results[0]

        return {}

    except Exception as e:
        print(f"❌ DOI搜索失敗：{e}")
        return {}


# ==================== 測試代碼 ====================
if __name__ == "__main__":
    """
    測試Europe PMC處理功能

    這個測試代碼用於驗證Europe PMC API是否正常工作
    """
    print("🧪 開始測試Europe PMC功能...")

    # 驗證API可用性
    if validate_europepmc_api():
        print("✅ Europe PMC API驗證通過")

        # 測試搜索功能
        test_keywords = ["cancer", "therapy"]
        results = search_source(test_keywords, limit=2)

        print(f"📚 搜索結果：找到 {len(results)} 篇文獻")
        for i, result in enumerate(results, 1):
            print(f"  {i}. {result.get('title', 'Unknown')}")
            print(f"     PMCID: {result.get('pmcid', 'N/A')}")
            print(f"     DOI: {result.get('doi', 'N/A')}")
    else:
        print("❌ Europe PMC API驗證失敗")

# app/utils.py

import fitz  # PyMuPDF
import os

from backend.config import resolve_project_path

def load_and_parse_file(filepath):
    """讀取 PDF 檔案的全文文字"""
    try:
        doc = fitz.open(filepath)
        full_text = "\n".join([page.get_text() for page in doc])
        doc.close()
        return full_text
    except Exception as e:
        print(f"❌ 讀取文件失敗 {filepath}: {e}")
        raise

def get_page_number_for_chunk(filepath, chunk_text):
    """比對 chunk 對應的原始頁碼"""
    try:
        # 將相對路徑轉換為絕對路徑
        if not os.path.isabs(filepath):
            absolute_path = resolve_project_path(filepath)
        else:
            absolute_path = filepath

        # 檢查文件是否存在
        if not os.path.exists(absolute_path):
            print(f"❌ 文件不存在: {absolute_path}")
            return "?"

        doc = fitz.open(absolute_path)
        for i, page in enumerate(doc):
            if chunk_text[:50] in page.get_text():
                doc.close()
                return i + 1  # PDF 頁碼從 1 開始
        doc.close()
        return "?"  # 無法找到對應頁碼
    except Exception as e:
        print(f"⚠️ 無法獲取頁碼信息 {filepath}: {e}")
        return "?"

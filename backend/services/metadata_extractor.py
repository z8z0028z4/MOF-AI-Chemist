"""
元數據提取模塊
============

從PDF和DOCX文件中提取元數據信息。

實作說明：
- 使用 GPT-5-nano 的 Chat Completions API，並透過 response_format=json_schema 輸出結構化結果。
- 明確設定 max_tokens=256 以避免在長標題或較長 JSON 結果時因預設輸出預算過小而發生截斷，確保 JSON 可被完整解析。
- 不使用 temperature（GPT-5-nano 不支援），提升結果穩定性與可重現性。
"""

import os
import re
import json
import logging
# 移除模組級別的openai導入，改為延遲導入
# import openai
from PyPDF2 import PdfReader
from docx import Document

# 配置日誌
logger = logging.getLogger(__name__)

def extract_text_from_pdf(pdf_path):
    """從PDF文件中提取文本"""
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        logger.error(f"PDF文本提取失敗 {pdf_path}: {e}")
        return ""

def extract_text_from_docx(docx_path):
    """從DOCX文件中提取文本"""
    try:
        doc = Document(docx_path)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text
    except Exception as e:
        logger.error(f"DOCX文本提取失敗 {docx_path}: {e}")
        return ""

def gpt_detect_type_and_title(text, filename):
    """使用GPT判斷文件類型和提取標題"""
    try:
        # 延遲導入openai，避免模組級別導入問題
        import openai

        # 從環境變量獲取API密鑰
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("未設置OPENAI_API_KEY環境變量")
            return "unknown", filename

        client = openai.OpenAI(api_key=api_key)

        prompt = f"""
        請分析以下文本內容，判斷文件類型為paper或supporting information (SI)，並提取標題。

        文件名：{filename}
        文本內容（前1000字符）：
        {text[:1000]}

        請以JSON格式回答：
        {{
            "type": "paper" 或 "SI",
            "title": "提取的標題"
        }}

        判斷標準：
        - paper: 主要研究論文，包含完整的實驗方法、結果和討論
        - supporting_info: 支持信息，如補充材料、圖表說明等，通常包含supporting information的字眼、且不會有DOI。
        - unknown: 無法確定類型
        """

        response = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=256,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "file_classification",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": ["paper", "SI", "unknown"]
                            },
                            "title": {
                                "type": "string"
                            }
                        },
                        "required": ["type", "title"]
                    }
                }
            }
        )

        result = (response.choices[0].message.content or "").strip()

        # 嘗試解析JSON
        try:
            data = json.loads(result)
            return data.get("type", "unknown"), data.get("title", filename)
        except json.JSONDecodeError:
            logger.warning(f"GPT 回傳格式錯誤：{result}")
            return "unknown", filename

    except Exception as e:
        logger.warning(f"GPT 調用失敗：{e}")
        return "unknown", filename

def extract_metadata(file_path):
    """提取文件元數據"""
    try:
        # 獲取文件基本信息
        filename = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)

        # 設定預設值，確保在任何情況下都有type值
        file_type = "unknown"  # 預設值

        # 提取文本內容
        if file_path.lower().endswith('.pdf'):
            content = extract_text_from_pdf(file_path)
        elif file_path.lower().endswith('.docx'):
            content = extract_text_from_docx(file_path)
        else:
            logger.warning(f"不支持的文件格式：{file_path}")
            return None

        # 提取DOI
        doi_pattern = r'10\.\d{4,}/[-._;()/:\w]+'
        doi_match = re.search(doi_pattern, content)
        doi = doi_match.group() if doi_match else None

        if doi:
            logger.info(f"找到DOI: {doi}，判斷為主論文")
            file_type = "paper"  # 標準流程：有DOI時設為paper
            title = filename  # 使用文件名作為標題
        else:
            # 嘗試從內容提取標題
            try:
                # 簡單的標題提取邏輯
                lines = content.split('\n')
                for line in lines[:10]:  # 檢查前10行
                    line = line.strip()
                    if len(line) > 10 and len(line) < 200 and not line.startswith('Abstract'):
                        title = line
                        break
                else:
                    title = filename
                logger.info(f"從內容提取到標題: {title}")
            except Exception as e:
                logger.warning(f"從內容提取標題失敗: {e}")
                title = filename

            logger.warning("未找到DOI，使用LLM分析文件類型...")
            try:
                file_type, extracted_title = gpt_detect_type_and_title(content, filename)

                if file_type == "SI":
                    logger.info("LLM判斷為Supporting Information")
                elif file_type == "paper":
                    logger.info("LLM判斷為主論文")
                elif file_type == "supporting_info":  # 保持向後兼容
                    logger.info("LLM判斷為Supporting Information")
                    file_type = "SI"  # 標準化為 SI
                elif file_type == "main_paper":  # 保持向後兼容
                    logger.info("LLM判斷為主論文")
                    file_type = "paper"  # 標準化為 paper
                else:
                    logger.warning(f"LLM無法確定類型，返回: {file_type}")
                    file_type = "unknown"  # 確保是有效值
            except Exception as e:
                logger.error(f"LLM分析失敗: {e}")
                file_type = "unknown"  # 備用值
                extracted_title = filename

            # 如果LLM提取到更好的標題，使用它
            if extracted_title and extracted_title != filename:
                title = extracted_title

        metadata = {
            "filename": filename,
            "file_path": file_path,
            "file_size": file_size,
            "type": file_type,
            "title": title,
            "doi": doi,
            "content_preview": content[:500] if content else ""
        }

        return metadata

    except Exception as e:
        logger.error(f"元數據提取失敗 {file_path}: {e}")
        return None

# 測試代碼
if __name__ == "__main__":
    # 測試元數據提取
    test_file = "test.pdf"  # 替換為實際的測試文件
    if os.path.exists(test_file):
        metadata = extract_metadata(test_file)
        logger.info(metadata)
    else:
        logger.warning(f"測試文件不存在：{test_file}")

"""
文字互動 API 路由
==============

處理文字反白互動功能的 API 端點
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import time
import uuid

from backend.services.text_interaction_service import process_text_interaction, extract_context_paragraph
from backend.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


class TextInteractionRequest(BaseModel):
    """文字互動請求模型"""
    highlighted_text: str
    context_paragraph: Optional[str] = None
    full_text: Optional[str] = None
    user_input: str
    interaction_type: str  # "explain" 或 "revise"
    highlighted_area: str = "proposal"  # 🔍 [NEW] 反白區域
    proposal: Optional[str] = None
    old_chunks: Optional[List[Dict[str, Any]]] = None
    mode: str = "make proposal"
    context_size: int = 200


class TextInteractionResponse(BaseModel):
    """文字互動響應模型"""
    answer: str
    citations: List[Dict[str, Any]]
    chunks: List[Dict[str, Any]]
    interaction_type: str
    highlighted_text: str
    user_input: str
    timestamp: float
    structured_proposal: Optional[Dict[str, Any]] = None
    structured_experiment: Optional[Dict[str, Any]] = None  # 添加實驗細節字段
    chemicals: Optional[List[Dict[str, Any]]] = None  # 添加化學品字段
    request_id: str


@router.post("/text-interaction", response_model=TextInteractionResponse)
async def handle_text_interaction(request: TextInteractionRequest):
    """
    處理文字反白互動請求

    Args:
        request: 包含反白文字、用戶輸入等信息的請求

    Returns:
        TextInteractionResponse: 包含 LLM 回答、引用等信息的響應
    """

    # 生成唯一的請求 ID
    request_id = str(uuid.uuid4())[:8]
    start_time = time.time()

    logger.info(f"🚀 [API-{request_id}] ========== 文字互動 API 請求開始 ==========")
    logger.info(f"🚀 [API-{request_id}] 時間戳: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"🚀 [API-{request_id}] 互動類型: {request.interaction_type}")
    logger.info(f"🚀 [API-{request_id}] 反白文字長度: {len(request.highlighted_text)}")
    logger.info(f"🚀 [API-{request_id}] 用戶輸入長度: {len(request.user_input)}")

    try:
        # 驗證請求參數
        if not request.highlighted_text.strip():
            raise HTTPException(status_code=400, detail="反白文字不能為空")

        if not request.user_input.strip():
            raise HTTPException(status_code=400, detail="用戶輸入不能為空")

        if request.interaction_type not in ["explain", "revise"]:
            raise HTTPException(status_code=400, detail="不支援的互動類型")

        # 處理上下文段落
        context_paragraph = request.context_paragraph
        if not context_paragraph and request.full_text:
            context_paragraph = extract_context_paragraph(
                request.full_text,
                request.highlighted_text,
                request.context_size
            )

        if not context_paragraph:
            context_paragraph = request.highlighted_text

        # 處理修改功能需要的參數
        if request.interaction_type == "revise":
            if not request.proposal:
                raise HTTPException(status_code=400, detail="修改功能需要提供原始提案")
            if not request.old_chunks:
                request.old_chunks = []

        logger.info(f"🔍 [API-{request_id}] 開始處理文字互動")

        # 調用文字互動服務
        result = process_text_interaction(
            highlighted_text=request.highlighted_text,
            context_paragraph=context_paragraph,
            user_input=request.user_input,
            interaction_type=request.interaction_type,
            highlighted_area=request.highlighted_area,  # 🔍 [NEW] 添加反白區域
            proposal=request.proposal,
            old_chunks=request.old_chunks,
            mode=request.mode
        )

        # 添加請求 ID 到結果中
        result["request_id"] = request_id

        end_time = time.time()
        duration = end_time - start_time

        logger.info(f"✅ [API-{request_id}] ========== 文字互動 API 請求成功 ==========")
        logger.info(f"✅ [API-{request_id}] 總耗時: {duration:.2f}秒")
        logger.info(f"✅ [API-{request_id}] 回答長度: {len(result.get('answer', ''))}")
        logger.info(f"✅ [API-{request_id}] 引用數量: {len(result.get('citations', []))}")
        logger.info(f"✅ [API-{request_id}] 文檔塊數量: {len(result.get('chunks', []))}")

        return TextInteractionResponse(**result)

    except HTTPException:
        # 重新拋出 HTTP 異常
        raise
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time

        logger.error(f"❌ [API-{request_id}] ========== 文字互動 API 請求失敗 ==========")
        logger.error(f"❌ [API-{request_id}] 總耗時: {duration:.2f}秒")
        logger.error(f"❌ [API-{request_id}] 錯誤: {str(e)}")

        raise HTTPException(
            status_code=500,
            detail=f"處理文字互動請求失敗: {str(e)}"
        )


@router.get("/text-interaction/health")
async def health_check():
    """
    健康檢查端點

    Returns:
        Dict: 健康狀態信息
    """
    return {
        "status": "healthy",
        "service": "text-interaction",
        "timestamp": time.time()
    }

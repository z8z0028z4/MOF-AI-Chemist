/**
 * 浮動彈窗組件
 *
 * 顯示在反白文字右下角，提供 Explain 和 Revise 選項
 */

import React, { useState, useRef, useEffect } from 'react';
import { Button, Space, Tooltip } from 'antd';
import { QuestionCircleOutlined, EditOutlined, CloseOutlined } from '@ant-design/icons';
import { useTextHighlight } from './TextHighlightProvider';
import InteractionInput from './InteractionInput';
import InteractionResponse from './InteractionResponse';

const HighlightPopup = () => {
  const {
    showPopup,
    popupPosition,
    highlightedText,
    currentMode,
    isProcessing,
    handleTextInteraction,
    clearHighlight
  } = useTextHighlight();

  const [showInput, setShowInput] = useState(false);
  const [inputType, setInputType] = useState('');
  const [lastResponse, setLastResponse] = useState(null);
  const popupRef = useRef(null);

  // 檢查是否為知識庫助理模式（只有解釋功能）
  const isKnowledgeMode = currentMode === 'knowledge_assistant';

  // 處理選項點擊
  const handleOptionClick = (type) => {
    setInputType(type);
    setShowInput(true);
  };

  // 處理輸入提交
  const handleInputSubmit = async (userInput) => {
    try {
      const result = await handleTextInteraction(inputType, userInput);

      // 只有解釋功能才設置 lastResponse，修改功能會自動關閉彈窗
      if (inputType === 'explain') {
        setLastResponse(result);
      }

      setShowInput(false);
    } catch (error) {
      console.error('互動處理失敗:', error);
    }
  };

  // 處理輸入取消
  const handleInputCancel = () => {
    setShowInput(false);
    setInputType('');
  };

  // 處理回應關閉
  const handleResponseClose = () => {
    setLastResponse(null);
    clearHighlight();
  };

  // 調整彈窗位置，確保不超出視窗邊界
  useEffect(() => {
    if (popupRef.current && showPopup) {
      const popup = popupRef.current;
      const rect = popup.getBoundingClientRect();
      const viewportWidth = window.innerWidth;
      const viewportHeight = window.innerHeight;

      let adjustedX = popupPosition.x;
      let adjustedY = popupPosition.y;

      // 檢查右邊界
      if (rect.right > viewportWidth) {
        adjustedX = viewportWidth - rect.width - 10;
      }

      // 檢查下邊界
      if (rect.bottom > viewportHeight) {
        adjustedY = viewportHeight - rect.height - 10;
      }

      // 檢查左邊界
      if (adjustedX < 0) {
        adjustedX = 10;
      }

      // 檢查上邊界
      if (adjustedY < 0) {
        adjustedY = 10;
      }

      popup.style.left = `${adjustedX}px`;
      popup.style.top = `${adjustedY}px`;
    }
  }, [showPopup, popupPosition]);

  console.log('🔍 [HIGHLIGHT-POPUP] 渲染狀態:', { showPopup, popupPosition, highlightedText });

  if (!showPopup) {
    console.log('🔍 [HIGHLIGHT-POPUP] 彈窗未顯示');
    return null;
  }

  return (
    <>
      {/* 主彈窗 */}
      <div
        ref={popupRef}
        className="highlight-popup"
        style={{
          position: 'fixed',
          left: popupPosition.x,
          top: popupPosition.y,
          zIndex: 1000,
          background: '#fff',
          border: '1px solid #d9d9d9',
          borderRadius: '8px',
          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
          padding: '8px',
          minWidth: '120px',
          animation: 'fadeIn 0.2s ease-in-out'
        }}
      >
        <div style={{
          fontSize: '12px',
          color: '#666',
          marginBottom: '8px',
          textAlign: 'center',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <span>已選擇: {highlightedText.length > 30 ? `${highlightedText.substring(0, 30)}...` : highlightedText}</span>
          <Button
            type="text"
            size="small"
            icon={<CloseOutlined />}
            onClick={clearHighlight}
            style={{ padding: '0 4px', minWidth: 'auto' }}
          />
        </div>

        <Space direction="vertical" style={{ width: '100%' }}>
          <Tooltip title="解釋選中的文字">
            <Button
              type="text"
              size="small"
              icon={<QuestionCircleOutlined />}
              onClick={() => handleOptionClick('explain')}
              style={{ width: '100%', textAlign: 'left' }}
              loading={isProcessing && inputType === 'explain'}
            >
              解釋 (Explain)
            </Button>
          </Tooltip>

          {!isKnowledgeMode && (
            <Tooltip title="修改選中的文字">
              <Button
                type="text"
                size="small"
                icon={<EditOutlined />}
                onClick={() => handleOptionClick('revise')}
                style={{ width: '100%', textAlign: 'left' }}
                loading={isProcessing && inputType === 'revise'}
              >
                修改 (Revise)
              </Button>
            </Tooltip>
          )}
        </Space>
      </div>

      {/* 輸入框 */}
      {showInput && (
        <InteractionInput
          type={inputType}
          highlightedText={highlightedText}
          onSubmit={handleInputSubmit}
          onCancel={handleInputCancel}
          isProcessing={isProcessing}
        />
      )}

      {/* 回應顯示 - 只有解釋功能才顯示 */}
      {lastResponse && inputType === 'explain' && (
        <InteractionResponse
          response={lastResponse}
          type={inputType}
          onClose={handleResponseClose}
        />
      )}

      <style>{`
        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: scale(0.9);
          }
          to {
            opacity: 1;
            transform: scale(1);
          }
        }

        .highlight-popup {
          animation: fadeIn 0.2s ease-in-out;
        }
      `}</style>
    </>
  );
};

export default HighlightPopup;

/**
 * 互動輸入框組件
 *
 * 用於用戶輸入問題或修改意見
 */

import React, { useState, useRef, useEffect } from 'react';
import { Input, Button, Space, Card } from 'antd';
import { SendOutlined, CloseOutlined } from '@ant-design/icons';

const { TextArea } = Input;

const InteractionInput = ({
  type,
  highlightedText,
  onSubmit,
  onCancel,
  isProcessing
}) => {
  const [inputValue, setInputValue] = useState('');
  const inputRef = useRef(null);

  // 根據類型設置預設提示文字
  const getPlaceholder = () => {
    if (type === 'explain') {
      return '請輸入您想了解的問題，例如：這段話是什麼意思？這個概念如何解釋？';
    } else if (type === 'revise') {
      return '請輸入修改意見，例如：這段描述不夠詳細，需要補充更多技術細節';
    }
    return '請輸入您的問題或意見...';
  };

  const getTitle = () => {
    if (type === 'explain') {
      return '解釋文字';
    } else if (type === 'revise') {
      return '修改文字';
    }
    return '互動';
  };

  // 處理提交
  const handleSubmit = () => {
    if (inputValue.trim()) {
      onSubmit(inputValue.trim());
    }
  };

  // 處理鍵盤事件
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    } else if (e.key === 'Escape') {
      onCancel();
    }
  };

  // 自動聚焦
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.focus();
    }
  }, []);

  return (
    <div
      style={{
        position: 'fixed',
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
        zIndex: 1001,
        width: '500px',
        maxWidth: '90vw'
      }}
    >
      <Card
        title={getTitle()}
        extra={
          <Button
            type="text"
            icon={<CloseOutlined />}
            onClick={onCancel}
            disabled={isProcessing}
          />
        }
        style={{
          boxShadow: '0 8px 24px rgba(0, 0, 0, 0.15)',
          borderRadius: '8px'
        }}
      >
        <div style={{ marginBottom: '16px' }}>
          <div style={{ fontSize: '14px', color: '#666', marginBottom: '8px' }}>
            已選擇的文字：
          </div>
          <div
            style={{
              background: '#f5f5f5',
              padding: '8px 12px',
              borderRadius: '4px',
              fontSize: '14px',
              maxHeight: '80px',
              overflow: 'auto',
              border: '1px solid #d9d9d9'
            }}
          >
            {highlightedText}
          </div>
        </div>

        <div style={{ marginBottom: '16px' }}>
          <TextArea
            ref={inputRef}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder={getPlaceholder()}
            rows={4}
            onKeyDown={handleKeyDown}
            disabled={isProcessing}
            style={{ resize: 'none' }}
          />
        </div>

        <div style={{ textAlign: 'right' }}>
          <Space>
            <Button onClick={onCancel} disabled={isProcessing}>
              取消
            </Button>
            <Button
              type="primary"
              icon={<SendOutlined />}
              onClick={handleSubmit}
              loading={isProcessing}
              disabled={!inputValue.trim()}
            >
              發送
            </Button>
          </Space>
        </div>

        <div style={{ fontSize: '12px', color: '#999', marginTop: '8px' }}>
          提示：按 Enter 發送，按 Esc 取消
        </div>
      </Card>
    </div>
  );
};

export default InteractionInput;

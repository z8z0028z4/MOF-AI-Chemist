/**
 * 互動回應顯示組件
 *
 * 以摺疊卡片形式顯示 LLM 回答和 citation 信息
 */

import React, { useState } from 'react';
import { Card, Collapse, Button, Space, Typography, Tag, Divider } from 'antd';
import { CloseOutlined, FileTextOutlined, LinkOutlined } from '@ant-design/icons';

const { Text, Paragraph } = Typography;
const { Panel } = Collapse;

const InteractionResponse = ({ response, type, onClose }) => {
  const [activeKey, setActiveKey] = useState(['answer']);

  const getTypeLabel = () => {
    return type === 'explain' ? '解釋' : '修改';
  };

  const getTypeColor = () => {
    return type === 'explain' ? 'blue' : 'green';
  };

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp * 1000).toLocaleString('zh-TW');
  };

  const renderCitations = () => {
    if (!response.citations || response.citations.length === 0) {
      return (
        <div style={{ textAlign: 'center', color: '#999', padding: '20px' }}>
          暫無引用信息
        </div>
      );
    }

    return response.citations.map((citation, index) => (
      <div
        key={index}
        style={{
          border: '1px solid #f0f0f0',
          borderRadius: '6px',
          padding: '12px',
          marginBottom: '12px',
          background: '#fafafa'
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Tag color="blue">{citation.label || `[${index + 1}]`}</Tag>
            <Text strong style={{ fontSize: '14px' }}>
              {citation.title || 'Untitled'}
            </Text>
          </div>
          <div style={{ fontSize: '12px', color: '#666' }}>
            {citation.filename && `檔案: ${citation.filename}`}
            {citation.page && ` | 頁面: ${citation.page}`}
          </div>
        </div>

        <Paragraph
          style={{
            fontSize: '13px',
            lineHeight: '1.5',
            color: '#333',
            margin: 0,
            maxHeight: '100px',
            overflow: 'auto'
          }}
        >
          {citation.content}
        </Paragraph>
      </div>
    ));
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
        zIndex: 1002,
        width: '600px',
        maxWidth: '90vw',
        maxHeight: '80vh'
      }}
    >
      <Card
        title={
          <Space>
            <Tag color={getTypeColor()}>{getTypeLabel()}</Tag>
            <span>AI 回應</span>
          </Space>
        }
        extra={
          <Button
            type="text"
            icon={<CloseOutlined />}
            onClick={onClose}
          />
        }
        style={{
          boxShadow: '0 8px 24px rgba(0, 0, 0, 0.15)',
          borderRadius: '8px',
          maxHeight: '80vh',
          overflow: 'hidden'
        }}
        bodyStyle={{
          padding: '16px',
          maxHeight: 'calc(80vh - 120px)',
          overflow: 'auto'
        }}
      >
        {/* 基本信息 */}
        <div style={{ marginBottom: '16px', padding: '12px', background: '#f8f9fa', borderRadius: '6px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <Text type="secondary" style={{ fontSize: '12px' }}>
              請求 ID: {response.request_id}
            </Text>
            <Text type="secondary" style={{ fontSize: '12px' }}>
              {formatTimestamp(response.timestamp)}
            </Text>
          </div>
          <div style={{ fontSize: '12px', color: '#666' }}>
            反白文字: {response.highlighted_text.length > 50
              ? `${response.highlighted_text.substring(0, 50)}...`
              : response.highlighted_text}
          </div>
        </div>

        {/* 摺疊內容 */}
        <Collapse
          activeKey={activeKey}
          onChange={setActiveKey}
          style={{ marginBottom: '16px' }}
        >
          <Panel
            header={
              <Space>
                <FileTextOutlined />
                <span>AI 回答</span>
                <Tag color="green">{response.answer.length} 字符</Tag>
              </Space>
            }
            key="answer"
          >
            <div
              style={{
                fontSize: '14px',
                lineHeight: '1.6',
                color: '#333',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word'
              }}
            >
              {response.answer}
            </div>
          </Panel>

          <Panel
            header={
              <Space>
                <LinkOutlined />
                <span>引用信息</span>
                <Tag color="blue">{response.citations?.length || 0} 個引用</Tag>
              </Space>
            }
            key="citations"
          >
            {renderCitations()}
          </Panel>
        </Collapse>

        {/* 操作按鈕 */}
        <div style={{ textAlign: 'right', borderTop: '1px solid #f0f0f0', paddingTop: '12px' }}>
          <Space>
            <Button onClick={onClose}>
              關閉
            </Button>
          </Space>
        </div>
      </Card>
    </div>
  );
};

export default InteractionResponse;

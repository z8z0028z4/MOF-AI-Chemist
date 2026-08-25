/**
 * 歷史記錄對話框組件
 *
 * 顯示所有與 LLM 的對話記錄
 */

import React, { useState } from 'react';
import { Modal, List, Tag, Typography, Space, Button, Empty, Collapse } from 'antd';
import { HistoryOutlined, DeleteOutlined, FileTextOutlined, LinkOutlined } from '@ant-design/icons';

const { Text, Paragraph } = Typography;
const { Panel } = Collapse;

const HistoryDialog = ({ visible, onClose, history, onClearHistory }) => {
  const [selectedItem, setSelectedItem] = useState(null);

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleString('zh-TW');
  };

  const getTypeLabel = (type) => {
    return type === 'explain' ? '解釋' : '修改';
  };

  const getTypeColor = (type) => {
    return type === 'explain' ? 'blue' : 'green';
  };

  const getContextLabel = (context) => {
    const contextMap = {
      'make proposal': '研究提案',
      'knowledge_assistant': '知識庫助理',
      'experiment_detail': '實驗細節',
      'revise_proposal': '修改提案'
    };
    return contextMap[context] || context;
  };

  const renderHistoryItem = (item) => (
    <List.Item
      style={{
        padding: '16px',
        border: '1px solid #f0f0f0',
        borderRadius: '8px',
        marginBottom: '12px',
        background: '#fff',
        cursor: 'pointer',
        transition: 'all 0.2s'
      }}
      onClick={() => setSelectedItem(selectedItem?.id === item.id ? null : item)}
    >
      <div style={{ width: '100%' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
          <Space>
            <Tag color={getTypeColor(item.type)}>{getTypeLabel(item.type)}</Tag>
            <Tag color="orange">{getContextLabel(item.context)}</Tag>
            <Text type="secondary" style={{ fontSize: '12px' }}>
              {formatTimestamp(item.timestamp)}
            </Text>
          </Space>
          <Text type="secondary" style={{ fontSize: '12px' }}>
            ID: {item.requestId}
          </Text>
        </div>

        <div style={{ marginBottom: '8px' }}>
          <Text strong style={{ fontSize: '14px' }}>
            反白文字:
          </Text>
          <Text style={{ fontSize: '13px', color: '#666', marginLeft: '8px' }}>
            {item.highlightedText.length > 60
              ? `${item.highlightedText.substring(0, 60)}...`
              : item.highlightedText}
          </Text>
        </div>

        <div style={{ marginBottom: '8px' }}>
          <Text strong style={{ fontSize: '14px' }}>
            用戶輸入:
          </Text>
          <Text style={{ fontSize: '13px', color: '#666', marginLeft: '8px' }}>
            {item.userInput.length > 80
              ? `${item.userInput.substring(0, 80)}...`
              : item.userInput}
          </Text>
        </div>

        {selectedItem?.id === item.id && (
          <div style={{ marginTop: '12px', padding: '12px', background: '#f8f9fa', borderRadius: '6px' }}>
            <Collapse size="small" defaultActiveKey={['answer']}>
              <Panel
                header={
                  <Space>
                    <FileTextOutlined />
                    <span>AI 回答</span>
                    <Tag color="green">{item.llmResponse.length} 字符</Tag>
                  </Space>
                }
                key="answer"
              >
                <div
                  style={{
                    fontSize: '13px',
                    lineHeight: '1.5',
                    color: '#333',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                    maxHeight: '200px',
                    overflow: 'auto'
                  }}
                >
                  {item.llmResponse}
                </div>
              </Panel>

              <Panel
                header={
                  <Space>
                    <LinkOutlined />
                    <span>引用信息</span>
                    <Tag color="blue">{item.citations?.length || 0} 個引用</Tag>
                  </Space>
                }
                key="citations"
              >
                {item.citations && item.citations.length > 0 ? (
                  item.citations.map((citation, index) => (
                    <div
                      key={index}
                      style={{
                        border: '1px solid #e8e8e8',
                        borderRadius: '4px',
                        padding: '8px',
                        marginBottom: '8px',
                        background: '#fff'
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                        <Tag color="blue" size="small">{citation.label || `[${index + 1}]`}</Tag>
                        <Text strong style={{ fontSize: '12px' }}>
                          {citation.title || 'Untitled'}
                        </Text>
                      </div>
                      <Text style={{ fontSize: '11px', color: '#666' }}>
                        {citation.filename && `檔案: ${citation.filename}`}
                        {citation.page && ` | 頁面: ${citation.page}`}
                      </Text>
                      <Paragraph
                        style={{
                          fontSize: '11px',
                          lineHeight: '1.4',
                          color: '#333',
                          margin: '4px 0 0 0',
                          maxHeight: '60px',
                          overflow: 'auto'
                        }}
                      >
                        {citation.content}
                      </Paragraph>
                    </div>
                  ))
                ) : (
                  <div style={{ textAlign: 'center', color: '#999', padding: '20px' }}>
                    暫無引用信息
                  </div>
                )}
              </Panel>
            </Collapse>
          </div>
        )}
      </div>
    </List.Item>
  );

  return (
    <Modal
      title={
        <Space>
          <HistoryOutlined />
          <span>互動歷史記錄</span>
          <Tag color="blue">{history.length} 條記錄</Tag>
        </Space>
      }
      open={visible}
      onCancel={onClose}
      width={800}
      footer={[
        <Button key="clear" icon={<DeleteOutlined />} onClick={onClearHistory}>
          清空歷史
        </Button>,
        <Button key="close" onClick={onClose}>
          關閉
        </Button>
      ]}
      style={{ top: 20 }}
    >
      {history.length === 0 ? (
        <Empty
          description="暫無互動記錄"
          style={{ margin: '40px 0' }}
        />
      ) : (
        <List
          dataSource={history}
          renderItem={renderHistoryItem}
          style={{ maxHeight: '60vh', overflow: 'auto' }}
        />
      )}
    </Modal>
  );
};

export default HistoryDialog;

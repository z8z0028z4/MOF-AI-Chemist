import React, { useMemo, useState, useEffect } from 'react';
import { Alert, Card, Form, Input, Button, message, Space, Typography, List, Tag, Divider, Select, Radio, Collapse } from 'antd';
import { useTextHighlight } from '../components/TextHighlight/TextHighlightProvider';
import { useAppState } from '../contexts/AppStateContext';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';
import { getApiErrorMessage } from '../services/apiClient';
import { getDocumentUrl } from '../services/documentApi';
import { queryKnowledge } from '../services/knowledgeApi';

const { Title, Paragraph, Text } = Typography;
const { TextArea } = Input;
const { Option } = Select;

const KnowledgeQuery = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  // 使用全局狀態管理
  const { state, setKnowledgeFormData, setKnowledgeResult } = useAppState();
  const {
    formData,
    answer,
    citations,
    chunks,
    retrievalCount,
    answerMode,
    hasQueried
  } = state.knowledgeQuery;

  // 文字反白功能
  const { setMode, setText, handleTextSelection } = useTextHighlight();

  const hasResult = useMemo(
    () => Boolean(answer) || citations.length > 0,
    [answer, citations]
  );

  // 設置文字反白模式
  useEffect(() => {
    setMode('knowledge_assistant');
  }, [setMode]);

  // 同步表單數據
  useEffect(() => {
    if (formData.question !== form.getFieldValue('question')) {
      form.setFieldsValue(formData);
    }
  }, [formData, form]);

  const showError = (e, fallbackMsg) => {
    message.error(getApiErrorMessage(e, fallbackMsg));
  };

  const onQuery = async () => {
    const question = form.getFieldValue('question');
    if (!question) return message.warning('Please enter your question');

    // 保存表單數據到全局狀態
    setKnowledgeFormData({ question });

    setLoading(true);
    try {
      const data = await queryKnowledge({
        question: question,
        retrievalCount: retrievalCount,
        answerMode: answerMode,
      });

      // 使用全局狀態管理更新結果
      setKnowledgeResult({
        answer: data.answer || '',
        citations: data.citations || [],
        chunks: data.chunks || [],
        retrievalCount: retrievalCount,
        answerMode: answerMode
      });

      // 設置文字反白功能的數據
      setText(data.answer || '');
    } catch (e) {
      showError(e, 'Query failed');
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const onClear = () => {
    form.resetFields();
    setKnowledgeFormData({ question: '' });
    setKnowledgeResult({
      answer: '',
      citations: [],
      chunks: [],
      retrievalCount: 10,
      answerMode: 'rigorous'
    });
  };

  return (
    <div>
      <Title level={2}>知識庫查詢</Title>
      <Paragraph>
        基於上傳之材料科學文獻進行智慧問答與檢索，支援嚴謹文獻引用與推理分析模式。
      </Paragraph>
      <Alert
        type="warning"
        showIcon
        style={{ marginBottom: 16 }}
        message="目前系統僅支援英文輸入與英文檢索"
        description="The current vector index was built with an English embedding model. For reliable retrieval, enter questions and keywords in English until multilingual embedding support is implemented."
      />

      <Card title="查詢與檢索設定" style={{ marginBottom: 16 }}>
        <Form form={form} layout="vertical" initialValues={formData}>
          <Form.Item
            label="查詢問題"
            name="question"
            rules={[{ required: true, message: '請輸入您的問題' }]}
          >
            <TextArea
              rows={4}
              placeholder="請輸入您的問題，例如：'Please introduce the synthesis methods of HKUST-1'"
              onChange={(e) => setKnowledgeFormData({ question: e.target.value })}
            />
          </Form.Item>

          <Space direction="vertical" style={{ width: '100%' }}>
            <div>
              <Text strong>回答生成模式：</Text>
              <Radio.Group
                value={answerMode}
                onChange={(e) => setKnowledgeFormData({ answerMode: e.target.value })}
                style={{ marginLeft: 16 }}
              >
                <Radio.Button value="rigorous">嚴謹引用模式</Radio.Button>
                <Radio.Button value="inference">推理分析模式</Radio.Button>
              </Radio.Group>
            </div>

            <div>
              <Text strong>文獻檢索數量：</Text>
              <Select
                value={retrievalCount}
                onChange={(value) => setKnowledgeFormData({ retrievalCount: value })}
                style={{ width: 120, marginLeft: 16 }}
              >
                <Option value={5}>5 篇文檔</Option>
                <Option value={10}>10 篇文檔</Option>
                <Option value={15}>15 篇文檔</Option>
                <Option value={20}>20 篇文檔</Option>
                <Option value={25}>25 篇文檔</Option>
                <Option value={30}>30 篇文檔</Option>
              </Select>
            </div>
          </Space>

          <Form.Item style={{ marginTop: 16 }}>
            <Space>
              <Button
                type="primary"
                onClick={onQuery}
                loading={loading}
                size="large"
              >
                🔍 開始查詢
              </Button>
              <Button onClick={onClear} size="large">
                清空結果
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>

      {hasQueried && hasResult && (
        <>
          {/* Query Result Summary */}
          <Card style={{ marginBottom: 16 }}>
            <div style={{ marginBottom: 16 }}>
              <Tag color="blue">回答模式：{answerMode === 'rigorous' ? '嚴謹引用' : '推理分析'}</Tag>
              <Tag color="green">檢索：{retrievalCount} 篇文獻</Tag>
              <Tag color="orange">匹配：{chunks.length} 個文字區塊</Tag>
            </div>
          </Card>

          {/* AI Answer - Collapsible Card */}
          <Collapse
            defaultActiveKey={['answer']}
            style={{ marginBottom: 16 }}
            items={[
              {
                key: 'answer',
                label: <span style={{ fontWeight: 700, fontSize: 27 }}>🤖 AI 查詢回答</span>,
                children: (
                  <div
                    onMouseUp={handleTextSelection}
                    style={{
                      fontSize: '16px',
                      lineHeight: '1.6',
                      maxWidth: '100%',
                      width: '100%',
                      cursor: 'text'
                    }}
                  >
                    <ReactMarkdown
                      remarkPlugins={[remarkMath]}
                      rehypePlugins={[rehypeKatex]}
                      components={{
                        // 自定義渲染組件以保持樣式一致性
                        h1: ({ node, ...props }) => <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#1890ff', marginTop: '16px', marginBottom: '8px' }} {...props} />,
                        h2: ({ node, ...props }) => <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#1890ff', marginTop: '14px', marginBottom: '8px' }} {...props} />,
                        h3: ({ node, ...props }) => <div style={{ fontSize: '18px', fontWeight: 'bold', marginTop: '12px', marginBottom: '6px' }} {...props} />,
                        p: ({ node, ...props }) => <div style={{ marginBottom: '1em' }} {...props} />,
                        ul: ({ node, ...props }) => <ul style={{ paddingLeft: '20px', marginBottom: '1em' }} {...props} />,
                        ol: ({ node, ...props }) => <ol style={{ paddingLeft: '20px', marginBottom: '1em' }} {...props} />,
                        li: ({ node, ...props }) => <li style={{ marginBottom: '0.5em' }} {...props} />,
                        a: ({ node, ...props }) => <a style={{ color: '#1890ff', textDecoration: 'underline' }} target="_blank" rel="noopener noreferrer" {...props} />,
                        blockquote: ({ node, ...props }) => <blockquote style={{ borderLeft: '4px solid #d9d9d9', paddingLeft: '16px', color: '#666', margin: '1em 0' }} {...props} />,
                        code: ({ node, inline, className, children, ...props }) => {
                          return inline ?
                            <code style={{ background: '#f5f5f5', padding: '2px 4px', borderRadius: '3px', fontFamily: 'monospace' }} {...props}>{children}</code> :
                            <pre style={{ background: '#f5f5f5', padding: '16px', borderRadius: '6px', overflow: 'auto' }}><code {...props}>{children}</code></pre>
                        }
                      }}
                    >
                      {answer}
                    </ReactMarkdown>
                  </div>
                ),
              },
            ]}
          />

          {/* Citations - Collapsible Card */}
          {citations.length > 0 && (
            <Collapse
              defaultActiveKey={['citations']}
              style={{ marginBottom: 16 }}
              items={[
                {
                  key: 'citations',
                  label: <span style={{ fontWeight: 700, fontSize: 27 }}>📚 參考文獻引用</span>,
                  children: (
                    <List
                      dataSource={citations}
                      renderItem={(citation, index) => (
                        <List.Item style={{ padding: '16px 0', borderBottom: '1px solid #f0f0f0' }}>
                          <div style={{ width: '100%' }}>
                            <div style={{ display: 'flex', gap: '16px', alignItems: 'flex-start' }}>
                              {/* Citation Label */}
                              <div style={{ flex: '0 0 60px' }}>
                                <Tag color="blue" style={{ fontSize: '16px', fontWeight: 'bold' }}>
                                  {citation.label}
                                </Tag>
                              </div>

                              {/* Citation Content */}
                              <div style={{ flex: '1' }}>
                                <Text strong style={{ fontSize: '18px', marginBottom: '8px', display: 'block', color: '#1890ff' }}>
                                  <a
                                    href={getDocumentUrl(citation.source)}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    style={{ color: '#1890ff', textDecoration: 'underline' }}
                                  >
                                    {citation.title || citation.source || 'Unknown Title'}
                                  </a>
                                </Text>
                                <div style={{
                                  fontSize: '14px',
                                  lineHeight: '1.5',
                                  wordBreak: 'break-word',
                                  overflowWrap: 'break-word'
                                }}>
                                  <div><strong>文獻來源：</strong> {citation.source}</div>
                                  {citation.page && citation.page !== '?' && (
                                    <div><strong>頁碼：</strong> {citation.page}</div>
                                  )}
                                  <div style={{ marginTop: '8px' }}>
                                    <strong>原文摘錄：</strong> {citation.snippet}
                                  </div>
                                </div>
                              </div>
                            </div>
                          </div>
                        </List.Item>
                      )}
                    />
                  ),
                },
              ]}
            />
          )}

          {/* Retrieved Document Chunks - Collapsible Card */}
          {chunks.length > 0 && (
            <Collapse
              defaultActiveKey={['chunks']}
              style={{ marginBottom: 16 }}
              items={[
                {
                  key: 'chunks',
                  label: <span style={{ fontWeight: 700, fontSize: 27 }}>📄 檢索到的文獻區塊</span>,
                  children: (
                    <List
                      dataSource={chunks}
                      renderItem={(chunk, index) => (
                        <List.Item style={{ padding: '16px 0', borderBottom: '1px solid #f0f0f0' }}>
                          <div style={{ width: '100%' }}>
                            <div style={{ display: 'flex', gap: '16px', alignItems: 'flex-start' }}>
                              {/* Chunk Number */}
                              <div style={{ flex: '0 0 80px' }}>
                                <Tag color="green" style={{ fontSize: '16px', fontWeight: 'bold' }}>
                                  區塊 {index + 1}
                                </Tag>
                              </div>

                              {/* Chunk Content */}
                              <div style={{ flex: '1' }}>
                                <Text strong style={{ fontSize: '18px', marginBottom: '8px', display: 'block', color: '#1890ff' }}>
                                  {chunk.metadata?.title || chunk.metadata?.filename || 'Unknown Title'}
                                </Text>
                                <div style={{
                                  fontSize: '14px',
                                  lineHeight: '1.5',
                                  wordBreak: 'break-word',
                                  overflowWrap: 'break-word'
                                }}>
                                  <div><strong>文獻來源：</strong> {chunk.metadata?.filename || chunk.metadata?.source || 'Unknown Source'}</div>
                                  {chunk.metadata?.page_number && (
                                    <div><strong>頁碼：</strong> {chunk.metadata.page_number}</div>
                                  )}
                                  <div style={{
                                    marginTop: '12px',
                                    background: '#f8f9fa',
                                    padding: '12px',
                                    borderRadius: '6px',
                                    maxHeight: '200px',
                                    overflow: 'auto',
                                    fontSize: '14px',
                                    lineHeight: '1.6'
                                  }}>
                                    <Text>{chunk.page_content}</Text>
                                  </div>
                                </div>
                              </div>
                            </div>
                          </div>
                        </List.Item>
                      )}
                    />
                  ),
                },
              ]}
            />
          )}
        </>
      )}
    </div>
  );
};

export default KnowledgeQuery;

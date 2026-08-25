/**
 * 狀態管理工具組件
 *
 * 提供以下功能：
 * - 數據導出/導入
 * - 清除特定頁面數據
 * - 清除所有數據
 * - 顯示數據統計信息
 * - 自動保存設置
 */

import React, { useState } from 'react';
import { Button, Modal, Space, Typography, Upload, message, Card, Statistic, Row, Col, Switch, Divider } from 'antd';
import { UploadOutlined, DownloadOutlined, DeleteOutlined, SettingOutlined, InfoCircleOutlined } from '@ant-design/icons';
import { useAppState } from '../../contexts/AppStateContext';

const { Title, Text } = Typography;

const StateManager = () => {
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [confirmClearVisible, setConfirmClearVisible] = useState(false);
  const [clearType, setClearType] = useState('');

  const {
    state,
    clearProposal,
    clearSearch,
    clearKnowledge,
    clearAllData,
    exportData,
    importData
  } = useAppState();

  // 計算數據統計
  const getDataStats = () => {
    const { proposal, search, knowledgeQuery } = state;

    return {
      proposal: {
        hasContent: proposal.hasGeneratedContent,
        proposalLength: proposal.proposal.length,
        chemicalsCount: proposal.chemicals.length,
        citationsCount: proposal.citations.length,
        hasExperiment: !!proposal.experimentDetail
      },
      search: {
        hasResults: search.hasSearched,
        resultsCount: search.results.length,
        query: search.searchQuery
      },
      knowledge: {
        hasAnswer: knowledgeQuery.hasQueried,
        answerLength: knowledgeQuery.answer.length,
        citationsCount: knowledgeQuery.citations.length,
        question: knowledgeQuery.formData.question
      }
    };
  };

  const stats = getDataStats();

  // 處理檔案導入
  const handleImport = (file) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const data = JSON.parse(e.target.result);
        importData(data);
        setIsModalVisible(false);
      } catch (error) {
        message.error('檔案格式錯誤，請選擇有效的JSON檔案');
      }
    };
    reader.readAsText(file);
    return false; // 阻止自動上傳
  };

  // 確認清除數據
  const handleClearData = (type) => {
    setClearType(type);
    setConfirmClearVisible(true);
  };

  const confirmClear = () => {
    switch (clearType) {
      case 'proposal':
        clearProposal();
        break;
      case 'search':
        clearSearch();
        break;
      case 'knowledge':
        clearKnowledge();
        break;
      case 'all':
        clearAllData();
        break;
      default:
        break;
    }
    setConfirmClearVisible(false);
  };

  return (
    <>
      <Button
        icon={<SettingOutlined />}
        onClick={() => setIsModalVisible(true)}
        type="text"
        title="狀態管理"
      >
        狀態管理
      </Button>

      {/* 主模態框 */}
      <Modal
        title={
          <Space>
            <SettingOutlined />
            <span>狀態管理</span>
          </Space>
        }
        open={isModalVisible}
        onCancel={() => setIsModalVisible(false)}
        footer={null}
        width={800}
      >
        {/* 數據統計 */}
        <Card title="數據統計" style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col span={8}>
              <Statistic
                title="提案頁面"
                value={stats.proposal.hasContent ? '有數據' : '無數據'}
                valueStyle={{ color: stats.proposal.hasContent ? '#3f8600' : '#cf1322' }}
              />
              {stats.proposal.hasContent && (
                <div style={{ fontSize: '12px', color: '#666' }}>
                  提案長度: {stats.proposal.proposalLength} 字符<br />
                  化學品: {stats.proposal.chemicalsCount} 個<br />
                  引用: {stats.proposal.citationsCount} 個<br />
                  實驗細節: {stats.proposal.hasExperiment ? '有' : '無'}
                </div>
              )}
            </Col>
            <Col span={8}>
              <Statistic
                title="搜尋頁面"
                value={stats.search.hasResults ? '有結果' : '無結果'}
                valueStyle={{ color: stats.search.hasResults ? '#3f8600' : '#cf1322' }}
              />
              {stats.search.hasResults && (
                <div style={{ fontSize: '12px', color: '#666' }}>
                  結果數量: {stats.search.resultsCount} 個<br />
                  查詢: {stats.search.query}
                </div>
              )}
            </Col>
            <Col span={8}>
              <Statistic
                title="知識查詢"
                value={stats.knowledge.hasAnswer ? '有答案' : '無答案'}
                valueStyle={{ color: stats.knowledge.hasAnswer ? '#3f8600' : '#cf1322' }}
              />
              {stats.knowledge.hasAnswer && (
                <div style={{ fontSize: '12px', color: '#666' }}>
                  答案長度: {stats.knowledge.answerLength} 字符<br />
                  引用: {stats.knowledge.citationsCount} 個<br />
                  問題: {stats.knowledge.question}
                </div>
              )}
            </Col>
          </Row>
        </Card>

        <Divider />

        {/* 數據操作 */}
        <Card title="數據操作" style={{ marginBottom: 16 }}>
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            {/* 導出數據 */}
            <div>
              <Text strong>導出數據：</Text>
              <Button
                icon={<DownloadOutlined />}
                onClick={exportData}
                type="primary"
                style={{ marginLeft: 8 }}
              >
                導出所有數據
              </Button>
              <Text type="secondary" style={{ marginLeft: 8, fontSize: '12px' }}>
                將所有頁面數據導出為JSON檔案
              </Text>
            </div>

            {/* 導入數據 */}
            <div>
              <Text strong>導入數據：</Text>
              <Upload
                accept=".json"
                beforeUpload={handleImport}
                showUploadList={false}
              >
                <Button icon={<UploadOutlined />} style={{ marginLeft: 8 }}>
                  選擇檔案
                </Button>
              </Upload>
              <Text type="secondary" style={{ marginLeft: 8, fontSize: '12px' }}>
                從JSON檔案導入數據（會覆蓋現有數據）
              </Text>
            </div>
          </Space>
        </Card>

        <Divider />

        {/* 清除數據 */}
        <Card title="清除數據" style={{ marginBottom: 16 }}>
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            <div>
              <Text strong>清除特定頁面：</Text>
              <Space style={{ marginLeft: 8 }}>
                <Button
                  icon={<DeleteOutlined />}
                  onClick={() => handleClearData('proposal')}
                  disabled={!stats.proposal.hasContent}
                  danger
                >
                  清除提案
                </Button>
                <Button
                  icon={<DeleteOutlined />}
                  onClick={() => handleClearData('search')}
                  disabled={!stats.search.hasResults}
                  danger
                >
                  清除搜尋
                </Button>
                <Button
                  icon={<DeleteOutlined />}
                  onClick={() => handleClearData('knowledge')}
                  disabled={!stats.knowledge.hasAnswer}
                  danger
                >
                  清除知識查詢
                </Button>
              </Space>
            </div>

            <div>
              <Text strong>清除所有數據：</Text>
              <Button
                icon={<DeleteOutlined />}
                onClick={() => handleClearData('all')}
                danger
                style={{ marginLeft: 8 }}
              >
                清除所有數據
              </Button>
              <Text type="secondary" style={{ marginLeft: 8, fontSize: '12px' }}>
                清除所有頁面的數據（不可恢復）
              </Text>
            </div>
          </Space>
        </Card>

        {/* 說明 */}
        <Card title="說明" size="small">
          <ul style={{ margin: 0, paddingLeft: 20 }}>
            <li>數據會自動保存到瀏覽器的localStorage中</li>
            <li>頁面刷新或重新打開瀏覽器後，數據會自動恢復</li>
            <li>導出的數據包含所有頁面的狀態信息</li>
            <li>清除操作不可恢復，請謹慎操作</li>
          </ul>
        </Card>
      </Modal>

      {/* 確認清除模態框 */}
      <Modal
        title="確認清除"
        open={confirmClearVisible}
        onOk={confirmClear}
        onCancel={() => setConfirmClearVisible(false)}
        okText="確認"
        cancelText="取消"
        okButtonProps={{ danger: true }}
      >
        <p>
          確定要清除
          {clearType === 'proposal' && '提案頁面的所有數據'}
          {clearType === 'search' && '搜尋頁面的所有結果'}
          {clearType === 'knowledge' && '知識查詢頁面的所有數據'}
          {clearType === 'all' && '所有頁面的所有數據'}
          嗎？此操作不可恢復。
        </p>
      </Modal>
    </>
  );
};

export default StateManager;

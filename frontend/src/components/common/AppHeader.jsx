import React, { useState } from 'react'
import { Layout, Typography, Space, Button, Avatar, Badge } from 'antd'
import { ExperimentOutlined, UserOutlined, HistoryOutlined } from '@ant-design/icons'
import { useTextHighlight } from '../TextHighlight/TextHighlightProvider'
import HistoryDialog from '../TextHighlight/HistoryDialog'
import StateManager from './StateManager'

const { Header } = Layout
const { Title } = Typography

const AppHeader = () => {
  const { interactionHistory, clearHistory } = useTextHighlight();
  const [historyVisible, setHistoryVisible] = useState(false);

  const handleHistoryClick = () => {
    setHistoryVisible(true);
  };

  const handleHistoryClose = () => {
    setHistoryVisible(false);
  };

  return (
    <>
      <Header
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          padding: '0 24px',
          height: '64px',
          lineHeight: '64px',
        }}
      >
        <Space>
          <ExperimentOutlined style={{ fontSize: '24px', color: 'white' }} />
          <Title level={3} style={{ color: 'white', margin: 0 }}>
            MOF AI Chemist
          </Title>
        </Space>

        <Space>
          <Badge count={interactionHistory.length} size="small">
            <Button
              type="text"
              style={{ color: 'white' }}
              icon={<HistoryOutlined />}
              onClick={handleHistoryClick}
            >
              歷史記錄
            </Button>
          </Badge>
          <StateManager />
          <Button type="text" style={{ color: 'white' }}>
            <UserOutlined />
            用戶中心
          </Button>
          <Avatar icon={<UserOutlined />} />
        </Space>
      </Header>

      <HistoryDialog
        visible={historyVisible}
        onClose={handleHistoryClose}
        history={interactionHistory}
        onClearHistory={clearHistory}
      />
    </>
  )
}

export default AppHeader

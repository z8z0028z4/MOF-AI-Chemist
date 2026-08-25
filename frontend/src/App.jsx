import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { Layout } from 'antd'
import AppHeader from './components/common/AppHeader'
import AppSidebar from './components/common/AppSidebar'
import Dashboard from './pages/Dashboard'
import Proposal from './pages/Proposal'
import Search from './pages/Search'
import Chemical from './pages/Chemical'
import Upload from './pages/Upload'
import Settings from './pages/Settings'
import KnowledgeQuery from './pages/KnowledgeQuery'
import MOF from './pages/MOF'
import { TextHighlightProvider } from './components/TextHighlight/TextHighlightProvider'
import { AppStateProvider } from './contexts/AppStateContext'
import HighlightPopup from './components/TextHighlight/HighlightPopup'
import './App.css'

const { Content } = Layout

function App() {
  return (
    <AppStateProvider>
      <TextHighlightProvider>
        <Layout style={{ minHeight: '100vh' }}>
          <AppHeader />
          <Layout>
            <AppSidebar />
            <Layout style={{ padding: '0 24px 24px' }}>
              <Content
                style={{
                  padding: 24,
                  margin: 0,
                  minHeight: 280,
                  background: '#fff',
                  borderRadius: '8px',
                  marginTop: '16px'
                }}
              >
                <Routes>
                  <Route path="/" element={<Dashboard />} />
                  <Route path="/proposal" element={<Proposal />} />
                  <Route path="/search" element={<Search />} />
                  <Route path="/chemical" element={<Chemical />} />
                  <Route path="/upload" element={<Upload />} />
                  <Route path="/settings" element={<Settings />} />
                  <Route path="/data-analyzer" element={<Navigate to="/" replace />} />
                  <Route path="/knowledge" element={<KnowledgeQuery />} />
                  <Route path="/mof" element={<MOF />} />
                </Routes>
              </Content>
            </Layout>
          </Layout>
        </Layout>
        <HighlightPopup />
      </TextHighlightProvider>
    </AppStateProvider>
  )
}

export default App

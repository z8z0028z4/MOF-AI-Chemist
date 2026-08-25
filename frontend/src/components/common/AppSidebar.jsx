import React from 'react'
import { Layout, Menu } from 'antd'
import { useNavigate, useLocation } from 'react-router-dom'
import {
  DashboardOutlined,
  FileTextOutlined,
  SearchOutlined,
  ExperimentOutlined,
  UploadOutlined,
  SettingOutlined,
  BookOutlined,
  ClusterOutlined,
} from '@ant-design/icons'

const { Sider } = Layout

const menuItems = [
  {
    key: '/',
    icon: <DashboardOutlined />,
    label: '儀表板',
  },
  {
    key: '/proposal',
    icon: <FileTextOutlined />,
    label: '研究提案',
  },
  {
    key: '/search',
    icon: <SearchOutlined />,
    label: '文獻搜尋',
  },
  {
    key: '/knowledge',
    icon: <BookOutlined />,
    label: '知識庫查詢',
  },
  {
    key: '/chemical',
    icon: <ExperimentOutlined />,
    label: '化學品查詢',
  },
  {
    key: '/mof',
    icon: <ClusterOutlined />,
    label: 'MOF AI 工具',
  },
  {
    key: '/upload',
    icon: <UploadOutlined />,
    label: '檔案上傳',
  },
  {
    key: '/settings',
    icon: <SettingOutlined />,
    label: '系統設定',
  },
]

const AppSidebar = () => {
  const navigate = useNavigate()
  const location = useLocation()

  const handleMenuClick = ({ key }) => {
    navigate(key)
  }

  return (
    <Sider
      width={200}
      style={{
        background: '#fff',
        borderRight: '1px solid #f0f0f0',
      }}
    >
      <Menu
        mode="inline"
        selectedKeys={[location.pathname]}
        style={{ height: '100%', borderRight: 0 }}
        items={menuItems}
        onClick={handleMenuClick}
      />
    </Sider>
  )
}

export default AppSidebar

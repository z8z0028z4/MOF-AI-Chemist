import React, { useEffect, useState, useCallback } from 'react'
import { Card, Table, Tag, Space, Button, Typography, message, Popconfirm, Spin } from 'antd'
import {
  ReloadOutlined,
  EyeOutlined,
  StopOutlined,
  LoadingOutlined,
  PlayCircleOutlined,
} from '@ant-design/icons'
import { listRuns, cancelJob } from '../../services/mofApi'

const { Text } = Typography

const MofRunResults = ({ onReopenRun }) => {
  const [runs, setRuns] = useState([])
  const [loading, setLoading] = useState(false)

  const loadRuns = useCallback(async () => {
    setLoading(true)
    try {
      const data = await listRuns()
      setRuns(data)
    } catch (err) {
      message.error('載入歷史任務失敗')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadRuns()
  }, [loadRuns])

  const handleCancel = async (jobId) => {
    try {
      await cancelJob(jobId)
      message.success('已送出取消請求')
      loadRuns()
    } catch (err) {
      message.error(err?.data?.detail || '取消任務失敗')
    }
  }

  const columns = [
    {
      title: '任務 ID (Job ID)',
      dataIndex: 'job_id',
      key: 'job_id',
      render: (text) => <Text code>{text}</Text>,
    },
    {
      title: '運作工具',
      dataIndex: 'tool',
      key: 'tool',
      render: (tool) => {
        if (tool === 'pormake') {
          return <Tag color="blue">CIF Generator (PORMAKE)</Tag>
        } else if (tool === 'xrd') {
          return <Tag color="orange">XRD Predictor</Tag>
        } else {
          return <Tag color="purple">Property Predictor (PMTransformer)</Tag>
        }
      },
    },
    {
      title: '狀態',
      dataIndex: 'status',
      key: 'status',
      render: (status) => {
        let color = 'blue'
        if (status === 'succeeded') color = 'green'
        else if (status === 'failed') color = 'red'
        else if (status === 'cancelled') color = 'gray'
        return <Tag color={color}>{status.toUpperCase()}</Tag>
      },
    },
    {
      title: '進度',
      dataIndex: 'progress',
      key: 'progress',
      render: (val, record) => {
        if (record.status === 'succeeded') return '100%'
        if (record.status === 'failed' || record.status === 'cancelled') return '-'
        return `${Math.round(val * 100)}%`
      },
    },
    {
      title: '最後更新時間',
      dataIndex: 'updated_at',
      key: 'updated_at',
      render: (t) => new Date(t).toLocaleString(),
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space size="middle">
          {record.status === 'succeeded' && (
            <Button
              size="small"
              icon={<EyeOutlined />}
              onClick={() => onReopenRun(record.job_id, record.tool)}
            >
              載入結果
            </Button>
          )}
          {(record.status === 'running' || record.status === 'queued' || record.status === 'preparing') && (
            <Popconfirm
              title="確定要取消此任務嗎？"
              onConfirm={() => handleCancel(record.job_id)}
              okText="是"
              cancelText="否"
            >
              <Button size="small" danger icon={<StopOutlined />}>
                取消
              </Button>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ]

  return (
    <Card
      title="歷史任務與 Runs 管理"
      size="small"
      className="mof-card-glow"
      extra={
        <Button size="small" icon={<ReloadOutlined />} onClick={loadRuns} loading={loading}>
          重新整理
        </Button>
      }
    >
      <Table
        size="small"
        loading={loading}
        dataSource={runs.map((r) => ({ ...r, key: r.job_id }))}
        columns={columns}
        locale={{ emptyText: '尚無任何執行紀錄。' }}
      />
    </Card>
  )
}

export default MofRunResults

import React, { useMemo, useState } from 'react'
import { Typography, Row, Col, Card, Form, Select, DatePicker, Button, Table, Space, Tag, Divider, message, Upload, Spin, Input, List } from 'antd'
import { DatabaseOutlined, LineChartOutlined, DownloadOutlined, UploadOutlined } from '@ant-design/icons'
import { useQuery, useMutation } from 'react-query'
import Plot from 'react-plotly.js'

const { Title, Paragraph, Text } = Typography
const { RangePicker } = DatePicker

const metricCards = [
  {
    key: 'datasets',
    title: 'Active Datasets',
    value: 12,
    icon: <DatabaseOutlined />,
    description: 'Dynamic collections synced from experiments and uploads.'
  },
  {
    key: 'trends',
    title: 'Detected Trends',
    value: 47,
    icon: <LineChartOutlined />,
    description: 'Signals with statistically significant variations.'
  },
  {
    key: 'exports',
    title: 'Exports This Week',
    value: 8,
    icon: <DownloadOutlined />,
    description: 'Reports generated and downloaded by the research team.'
  }
]

const datasetOptions = [
  { label: 'Experiment Results', value: 'experiment_results' },
  { label: 'Sensor Streams', value: 'sensor_streams' },
  { label: 'Literature Insights', value: 'literature_insights' }
]

const columns = [
  {
    title: 'Feature',
    dataIndex: 'feature',
    key: 'feature'
  },
  {
    title: 'Signal Strength',
    dataIndex: 'signal',
    key: 'signal',
    render: (value) => <Tag color={value > 0.75 ? 'red' : value > 0.45 ? 'orange' : 'blue'}>{value.toFixed(2)}</Tag>
  },
  {
    title: 'Last Updated',
    dataIndex: 'updatedAt',
    key: 'updatedAt'
  },
  {
    title: 'Recommended Action',
    dataIndex: 'action',
    key: 'action'
  }
]

const mockData = {
  experiment_results: [
    { key: '1', feature: 'Catalyst Efficiency', signal: 0.82, updatedAt: '2025-09-15 10:20', action: 'Schedule deeper experiment review.' },
    { key: '2', feature: 'Yield Consistency', signal: 0.63, updatedAt: '2025-09-14 16:05', action: 'Monitor next batch closely.' },
    { key: '3', feature: 'Thermal Stability', signal: 0.34, updatedAt: '2025-09-13 09:12', action: 'No action required.' }
  ],
  sensor_streams: [
    { key: '1', feature: 'Ambient Humidity', signal: 0.58, updatedAt: '2025-09-15 07:44', action: 'Correlate with material deviation logs.' },
    { key: '2', feature: 'Reactive Emissions', signal: 0.77, updatedAt: '2025-09-14 21:18', action: 'Escalate to safety officer.' },
    { key: '3', feature: 'Equipment Vibration', signal: 0.49, updatedAt: '2025-09-14 18:56', action: 'Flag for maintenance diagnostics.' }
  ],
  literature_insights: [
    { key: '1', feature: 'Emerging Catalysts', signal: 0.71, updatedAt: '2025-09-10 13:34', action: 'Prioritise for proposal drafting.' },
    { key: '2', feature: 'Safety Regulations', signal: 0.28, updatedAt: '2025-09-08 08:22', action: 'Archive for compliance reference.' },
    { key: '3', feature: 'Process Innovations', signal: 0.66, updatedAt: '2025-09-11 11:05', action: 'Share digest with wider team.' }
  ]
}

const DataAnalyzer = () => {
  const [selectedDataset, setSelectedDataset] = useState('experiment_results')
  const [selectedRange, setSelectedRange] = useState(null)
  const [uploadedFiles, setUploadedFiles] = useState({
    original: {},  // 原始材料檔案
    modified: {}   // 改質材料檔案
  })
  const [analysisResult, setAnalysisResult] = useState(null)
  const [modificationDescription, setModificationDescription] = useState('')
  const [userQuery, setUserQuery] = useState('')

  const tableData = useMemo(() => mockData[selectedDataset] || [], [selectedDataset])

  // API functions
  const analyzeMaterials = async (analysisData) => {
    const formData = new FormData()

    // 添加原始材料檔案
    Object.entries(analysisData.files.original).forEach(([technique, file]) => {
      if (file) {
        formData.append(`original_${technique}`, file)
      }
    })

    // 添加改質材料檔案
    Object.entries(analysisData.files.modified).forEach(([technique, file]) => {
      if (file) {
        formData.append(`modified_${technique}`, file)
      }
    })

    // 添加描述和查詢
    if (analysisData.modificationDescription) {
      formData.append('modificationDescription', analysisData.modificationDescription)
    }
    if (analysisData.userQuery) {
      formData.append('userQuery', analysisData.userQuery)
    }

    const response = await fetch('/api/v1/data-analyzer/analyze', {
      method: 'POST',
      body: formData,
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Analysis failed')
    }

    return response.json()
  }

  const exportReport = async (analysisResult) => {
    const response = await fetch('/api/v1/data-analyzer/export', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        analysisResult,
        format: 'docx'
      }),
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Export failed')
    }

    // Download the file
    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'material_analysis_report.docx'
    document.body.appendChild(a)
    a.click()
    window.URL.revokeObjectURL(url)
    document.body.removeChild(a)
  }

  // React Query mutations
  const analyzeMutation = useMutation(analyzeMaterials, {
    onSuccess: (data) => {
      setAnalysisResult(data)
      message.success('Analysis completed successfully!')
    },
    onError: (error) => {
      message.error(`Analysis failed: ${error.message}`)
    },
  })

  const exportMutation = useMutation(exportReport, {
    onSuccess: () => {
      message.success('Report exported successfully!')
    },
    onError: (error) => {
      message.error(`Export failed: ${error.message}`)
    },
  })

  const handleFileUpload = (technique, file, type) => {
    console.log('File upload triggered:', { technique, file: file.name, type })

    // Validate file type
    const allowedTypes = {
      xrd: ['.csv', '.txt'],
      ir: ['.csv', '.txt'],
      tga: ['.xlsx'],
      bet: ['.pdf']
    }

    const fileExtension = '.' + file.name.split('.').pop().toLowerCase()
    if (!allowedTypes[technique] || !allowedTypes[technique].includes(fileExtension)) {
      message.error(`Invalid file type for ${technique.toUpperCase()}. Allowed: ${allowedTypes[technique].join(', ')}`)
      return false
    }

    // Update state
    setUploadedFiles(prev => ({
      ...prev,
      [type]: {
        ...prev[type],
        [technique]: file
      }
    }))

    message.success(`${technique.toUpperCase()} file selected: ${file.name}`)
    return false // Prevent default upload
  }

  const handleAnalyze = () => {
    // 檢查是否有檔案上傳
    const hasOriginalFiles = uploadedFiles.original && Object.keys(uploadedFiles.original).length > 0
    const hasModifiedFiles = uploadedFiles.modified && Object.keys(uploadedFiles.modified).length > 0

    if (!hasOriginalFiles && !hasModifiedFiles) {
      message.warning('Please upload at least one file for analysis.')
      return
    }

    // 創建正確的分析數據結構
    const analysisData = {
      files: {
        original: uploadedFiles.original || {},
        modified: uploadedFiles.modified || {}
      },
      modificationDescription,
      userQuery
    }

    analyzeMutation.mutate(analysisData)
  }

  const handleExport = () => {
    if (!analysisResult) {
      message.warning('Please run analysis first.')
      return
    }

    exportMutation.mutate(analysisResult)
  }

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div>
        <Title level={2}>Data Analyzer</Title>
        <Paragraph>
          Explore consolidated datasets, surface actionable signals, and orchestrate exports for your research workflow.
        </Paragraph>
      </div>

      <Row gutter={[16, 16]}>
        {metricCards.map((card) => (
          <Col key={card.key} xs={24} sm={12} lg={8}>
            <Card>
              <Space direction="vertical" size="middle">
                <Space size="middle" align="center">
                  {card.icon}
                  <div>
                    <Text strong>{card.title}</Text>
                    <Paragraph type="secondary" style={{ marginBottom: 0 }}>
                      {card.description}
                    </Paragraph>
                  </div>
                </Space>
                <Title level={3} style={{ margin: 0 }}>
                  {card.value}
                </Title>
              </Space>
            </Card>
          </Col>
        ))}
      </Row>

      <Card title="Material Analysis & Comparison" bordered>
        <Form layout="vertical">
          {/* 原始材料檔案上傳 */}
          <div style={{ marginBottom: 24 }}>
            <Title level={4}>原始材料 (Original Material)</Title>
            <Row gutter={16}>
              <Col xs={24} md={6}>
                <Form.Item label="XRD Data (CSV/TXT)">
                  <Upload
                    beforeUpload={(file) => handleFileUpload('xrd', file, 'original')}
                    accept=".csv,.txt"
                    showUploadList={false}
                    onError={(error) => {
                      console.error('Upload error:', error)
                      message.error('File upload failed')
                    }}
                  >
                    <Button icon={<UploadOutlined />}>
                      {uploadedFiles.original.xrd ? uploadedFiles.original.xrd.name : 'Select Original XRD File'}
                    </Button>
                  </Upload>
                </Form.Item>
              </Col>
              <Col xs={24} md={6}>
                <Form.Item label="IR Data (CSV/TXT)">
                  <Upload
                    beforeUpload={(file) => handleFileUpload('ir', file, 'original')}
                    accept=".csv,.txt"
                    showUploadList={false}
                    onError={(error) => {
                      console.error('Upload error:', error)
                      message.error('File upload failed')
                    }}
                  >
                    <Button icon={<UploadOutlined />}>
                      {uploadedFiles.original.ir ? uploadedFiles.original.ir.name : 'Select Original IR File'}
                    </Button>
                  </Upload>
                </Form.Item>
              </Col>
              <Col xs={24} md={6}>
                <Form.Item label="TGA Data (XLSX)">
                  <Upload
                    beforeUpload={(file) => handleFileUpload('tga', file, 'original')}
                    accept=".xlsx"
                    showUploadList={false}
                    onError={(error) => {
                      console.error('Upload error:', error)
                      message.error('File upload failed')
                    }}
                  >
                    <Button icon={<UploadOutlined />}>
                      {uploadedFiles.original.tga ? uploadedFiles.original.tga.name : 'Select Original TGA File'}
                    </Button>
                  </Upload>
                </Form.Item>
              </Col>
              <Col xs={24} md={6}>
                <Form.Item label="BET Data (PDF)">
                  <Upload
                    beforeUpload={(file) => handleFileUpload('bet', file, 'original')}
                    accept=".pdf"
                    showUploadList={false}
                    onError={(error) => {
                      console.error('Upload error:', error)
                      message.error('File upload failed')
                    }}
                  >
                    <Button icon={<UploadOutlined />}>
                      {uploadedFiles.original.bet ? uploadedFiles.original.bet.name : 'Select Original BET File'}
                    </Button>
                  </Upload>
                </Form.Item>
              </Col>
            </Row>
          </div>

          {/* 改質材料檔案上傳 */}
          <div style={{ marginBottom: 24 }}>
            <Title level={4}>改質材料 (Modified Material)</Title>
            <Row gutter={16}>
              <Col xs={24} md={6}>
                <Form.Item label="XRD Data (CSV/TXT)">
                  <Upload
                    beforeUpload={(file) => handleFileUpload('xrd', file, 'modified')}
                    accept=".csv,.txt"
                    showUploadList={false}
                    onError={(error) => {
                      console.error('Upload error:', error)
                      message.error('File upload failed')
                    }}
                  >
                    <Button icon={<UploadOutlined />}>
                      {uploadedFiles.modified.xrd ? uploadedFiles.modified.xrd.name : 'Select Modified XRD File'}
                    </Button>
                  </Upload>
                </Form.Item>
              </Col>
              <Col xs={24} md={6}>
                <Form.Item label="IR Data (CSV/TXT)">
                  <Upload
                    beforeUpload={(file) => handleFileUpload('ir', file, 'modified')}
                    accept=".csv,.txt"
                    showUploadList={false}
                    onError={(error) => {
                      console.error('Upload error:', error)
                      message.error('File upload failed')
                    }}
                  >
                    <Button icon={<UploadOutlined />}>
                      {uploadedFiles.modified.ir ? uploadedFiles.modified.ir.name : 'Select Modified IR File'}
                    </Button>
                  </Upload>
                </Form.Item>
              </Col>
              <Col xs={24} md={6}>
                <Form.Item label="TGA Data (XLSX)">
                  <Upload
                    beforeUpload={(file) => handleFileUpload('tga', file, 'modified')}
                    accept=".xlsx"
                    showUploadList={false}
                    onError={(error) => {
                      console.error('Upload error:', error)
                      message.error('File upload failed')
                    }}
                  >
                    <Button icon={<UploadOutlined />}>
                      {uploadedFiles.modified.tga ? uploadedFiles.modified.tga.name : 'Select Modified TGA File'}
                    </Button>
                  </Upload>
                </Form.Item>
              </Col>
              <Col xs={24} md={6}>
                <Form.Item label="BET Data (PDF)">
                  <Upload
                    beforeUpload={(file) => handleFileUpload('bet', file, 'modified')}
                    accept=".pdf"
                    showUploadList={false}
                    onError={(error) => {
                      console.error('Upload error:', error)
                      message.error('File upload failed')
                    }}
                  >
                    <Button icon={<UploadOutlined />}>
                      {uploadedFiles.modified.bet ? uploadedFiles.modified.bet.name : 'Select Modified BET File'}
                    </Button>
                  </Upload>
                </Form.Item>
              </Col>
            </Row>
          </div>

          {/* 分析描述和查詢 */}
          <Row gutter={16}>
            <Col xs={24} md={12}>
              <Form.Item label="Modification Description (Optional)">
                <Input.TextArea
                  rows={4}
                  placeholder="Describe the modifications made to the material..."
                  value={modificationDescription}
                  onChange={(e) => setModificationDescription(e.target.value)}
                />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item label="Specific Query (Optional)">
                <Input.TextArea
                  rows={4}
                  placeholder="Ask specific questions about the analysis..."
                  value={userQuery}
                  onChange={(e) => setUserQuery(e.target.value)}
                />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col xs={24} md={12}>
              <Form.Item label="Actions">
                <Space>
                  <Button
                    type="primary"
                    onClick={handleAnalyze}
                    loading={analyzeMutation.isLoading}
                    disabled={Object.keys({...uploadedFiles.original, ...uploadedFiles.modified}).length === 0}
                  >
                    Run Analysis
                  </Button>
                  <Button
                    onClick={handleExport}
                    loading={exportMutation.isLoading}
                    disabled={!analysisResult}
                  >
                    Export Report
                  </Button>
                </Space>
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Card>

      {analysisResult && (
        <>
          <Card title="Analysis Results" bordered>
            <Spin spinning={analyzeMutation.isLoading}>
              {analysisResult.summary && (
                <div style={{ marginBottom: 24 }}>
                  <Title level={4}>AI Analysis Summary</Title>
                  <Paragraph>{analysisResult.summary}</Paragraph>
                </div>
              )}

              {analysisResult.recommendations && analysisResult.recommendations.length > 0 && (
                <div style={{ marginBottom: 24 }}>
                  <Title level={4}>Recommendations</Title>
                  <List
                    size="small"
                    dataSource={analysisResult.recommendations}
                    renderItem={(item) => (
                      <List.Item>
                        <Text>{item}</Text>
                      </List.Item>
                    )}
                  />
                </div>
              )}

              {analysisResult.structured_analysis && Object.keys(analysisResult.structured_analysis).length > 0 && (
                <div style={{ marginBottom: 24 }}>
                  <Title level={4}>Detailed Analysis</Title>
                  <Row gutter={[16, 16]}>
                    {Object.entries(analysisResult.structured_analysis).map(([technique, analysis]) => (
                      <Col xs={24} key={technique}>
                        <Card size="small" title={`${technique.toUpperCase()} Analysis`}>
                          <Space direction="vertical" style={{ width: '100%' }}>
                            {Object.entries(analysis).map(([key, value]) => (
                              <div key={key}>
                                <Text strong style={{ textTransform: 'capitalize' }}>
                                  {key.replace(/_/g, ' ')}:
                                </Text>
                                <div style={{ marginTop: 4 }}>
                                  {Array.isArray(value) ? (
                                    <List
                                      size="small"
                                      dataSource={value}
                                      renderItem={(item) => <List.Item>{item}</List.Item>}
                                    />
                                  ) : (
                                    <Text>{String(value)}</Text>
                                  )}
                                </div>
                              </div>
                            ))}
                          </Space>
                        </Card>
                      </Col>
                    ))}
                  </Row>
                </div>
              )}

              {analysisResult.features && Object.keys(analysisResult.features).length > 0 && (
                <div style={{ marginBottom: 24 }}>
                  <Title level={4}>Extracted Features</Title>
                  <Row gutter={[16, 16]}>
                    {Object.entries(analysisResult.features).map(([technique, features]) => (
                      <Col xs={24} md={12} key={technique}>
                        <Card size="small" title={`${technique.toUpperCase()} Features`}>
                          <Space direction="vertical" style={{ width: '100%' }}>
                            {Object.entries(features).map(([key, value]) => (
                              <div key={key}>
                                <Text strong>{key}:</Text> {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                              </div>
                            ))}
                          </Space>
                        </Card>
                      </Col>
                    ))}
                  </Row>
                </div>
              )}

              {analysisResult.plots && Object.keys(analysisResult.plots).length > 0 && (
                <div>
                  <Title level={4}>Data Visualizations</Title>
                  <Row gutter={[16, 16]}>
                    {Object.entries(analysisResult.plots).map(([technique, plotData]) => {
                      // Handle nested plot data structure (original vs modified)
                      if (plotData && typeof plotData === 'object' && !Array.isArray(plotData)) {
                        // Check if it has original/modified structure
                        if (plotData.original || plotData.modified) {
                          return Object.entries(plotData).map(([materialType, materialPlot]) => {
                            if (materialPlot && materialPlot.data && materialPlot.layout) {
                              return (
                                <Col xs={24} md={12} key={`${technique}-${materialType}`}>
                                  <Card size="small" title={`${technique.toUpperCase()} - ${materialType.charAt(0).toUpperCase() + materialType.slice(1)}`}>
                                    <Plot
                                      data={materialPlot.data}
                                      layout={materialPlot.layout}
                                      style={{ width: '100%', height: '400px' }}
                                    />
                                  </Card>
                                </Col>
                              );
                            }
                            return null;
                          }).filter(Boolean);
                        } else if (plotData.data && plotData.layout) {
                          // Single plot data structure
                          return (
                            <Col xs={24} md={12} key={technique}>
                              <Card size="small" title={`${technique.toUpperCase()} Plot`}>
                                <Plot
                                  data={plotData.data}
                                  layout={plotData.layout}
                                  style={{ width: '100%', height: '400px' }}
                                />
                              </Card>
                            </Col>
                          );
                        }
                      }
                      return null;
                    }).flat().filter(Boolean)}
                  </Row>
                </div>
              )}
            </Spin>
          </Card>
        </>
      )}

      <Card title="Signal Overview" bordered>
        <Table
          columns={columns}
          dataSource={tableData}
          pagination={{ pageSize: 5 }}
        />
      </Card>

      <Divider plain>Analysis Notes</Divider>
      <Paragraph type="secondary">
        The Data Analyzer provides material characterization analysis across multiple techniques (XRD, IR, TGA, BET).
        Upload your data files and get AI-powered insights about material properties, structural changes, and recommendations.
      </Paragraph>
    </Space>
  )
}

export default DataAnalyzer

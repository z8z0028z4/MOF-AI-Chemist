import React, { useEffect, useState, useCallback, useRef } from 'react'
import {
  Card,
  Col,
  Row,
  Select,
  Button,
  Table,
  Space,
  Tag,
  Progress,
  Typography,
  Alert,
  Collapse,
  Spin,
  Input,
  InputNumber,
  message,
} from 'antd'
import {
  PlayCircleOutlined,
  LoadingOutlined,
  DownloadOutlined,
  EyeOutlined,
  StopOutlined,
  InfoCircleOutlined,
  SearchOutlined,
} from '@ant-design/icons'
import {
  getToolsStatus,
  installTool,
  getToolInstallStatus,
  getCifGeneratorCatalog,
  getCifGeneratorTopologies,
  resolveCifGeneratorInputs,
  createCifGeneratorJob,
  getJobStatus,
  cancelJob,
  getRunStatus,
  getRunArtifactText,
} from '../../services/mofApi'

const { Title, Text, Paragraph } = Typography
const { Panel } = Collapse

const CifGeneratorTab = ({ onPreviewCif, activeJobId, onJobSuccess, onJobLoaded }) => {
  // Env status states
  const [envStatus, setEnvStatus] = useState(null)
  const [installing, setInstalling] = useState(false)
  const [installProgress, setInstallProgress] = useState(0)
  const [installMsg, setInstallMsg] = useState('')
  const [installLog, setInstallLog] = useState('')

  // Catalog & Form states
  const [catalog, setCatalog] = useState([])
  const [nodes, setNodes] = useState([])
  const [linkers, setLinkers] = useState([])
  const [selectedNode, setSelectedNode] = useState(null)
  const [selectedLinker, setSelectedLinker] = useState(null)
  const [topologies, setTopologies] = useState([])
  const [selectedTopology, setSelectedTopology] = useState(null)
  const [metalInput, setMetalInput] = useState('')
  const [linkerInput, setLinkerInput] = useState('')
  const [resolvingInputs, setResolvingInputs] = useState(false)
  const [resolution, setResolution] = useState(null)
  const [selectedCandidateKey, setSelectedCandidateKey] = useState(null)
  const [maxResults, setMaxResults] = useState(() => {
    const saved = localStorage.getItem('mof_max_results')
    return saved ? parseInt(saved, 10) : 10
  })

  useEffect(() => {
    localStorage.setItem('mof_max_results', String(maxResults))
  }, [maxResults])

  // Job states
  const [currentJobId, setCurrentJobId] = useState(null)
  const [jobStatus, setJobStatus] = useState(null)
  const [runDetails, setRunDetails] = useState(null)
  const [loadingTopologies, setLoadingTopologies] = useState(false)
  const [submittingJob, setSubmittingJob] = useState(false)

  // Polling refs
  const installPollRef = useRef(null)
  const jobPollRef = useRef(null)

  // 1. Fetch env status and catalog
  const loadEnvStatus = useCallback(async () => {
    try {
      const res = await getToolsStatus()
      setEnvStatus(res.pormake)
      if (res.pormake.installed && !res.pormake.ready) {
        // If installed but not ready, check if it's installing right now
        checkInstallStatus()
      }
    } catch (err) {
      console.error('Failed to load tools status:', err)
    }
  }, [])

  const checkInstallStatus = useCallback(async () => {
    try {
      const res = await getToolInstallStatus('pormake')
      if (res.status === 'installing') {
        setInstalling(true)
        setInstallProgress(Math.round(res.progress * 100))
        setInstallMsg(res.message)
        setInstallLog(res.log || '')

        // Start polling if not already
        if (!installPollRef.current) {
          installPollRef.current = setInterval(checkInstallStatus, 3000)
        }
      } else {
        if (installPollRef.current) {
          clearInterval(installPollRef.current)
          installPollRef.current = null
        }
        setInstalling(false)
        loadEnvStatus()
        if (res.status === 'success') {
          message.success('PORMAKE 環境安裝成功！')
        } else if (res.status === 'failed') {
          message.error(`PORMAKE 環境安裝失敗: ${res.message}`)
        }
      }
    } catch (err) {
      console.error(err)
    }
  }, [loadEnvStatus])

  const handleInstall = async () => {
    try {
      setInstalling(true)
      setInstallProgress(10)
      setInstallMsg('啟動安裝程序...')
      await installTool('pormake')
      checkInstallStatus()
    } catch (err) {
      setInstalling(false)
      message.error(err?.data?.detail || '無法啟動安裝。')
    }
  }

  const loadCatalog = useCallback(async () => {
    try {
      const res = await getCifGeneratorCatalog()
      setCatalog(res)
      // Filter node and linker options based on role
      setNodes(res.filter((item) => item.role === 'node'))
      setLinkers(res.filter((item) => item.role === 'linker'))
    } catch (err) {
      message.error('載入 catalog 失敗。')
    }
  }, [])

  useEffect(() => {
    loadEnvStatus()
    loadCatalog()
    return () => {
      if (installPollRef.current) clearInterval(installPollRef.current)
      if (jobPollRef.current) clearInterval(jobPollRef.current)
    }
  }, [loadEnvStatus, loadCatalog])

  // Hook to handle reopening historical runs
  useEffect(() => {
    if (activeJobId) {
      setCurrentJobId(activeJobId)
      pollJobStatus(activeJobId)

      // Start polling if the job is active (not terminal)
      getJobStatus(activeJobId).then((res) => {
        if (res.status === 'queued' || res.status === 'running' || res.status === 'preparing') {
          if (jobPollRef.current) clearInterval(jobPollRef.current)
          jobPollRef.current = setInterval(() => pollJobStatus(activeJobId), 2000)
        }
      }).catch(console.error)

      if (onJobLoaded) {
        onJobLoaded()
      }
    }
  }, [activeJobId])

  // 2. Fetch compatible topologies when building blocks change
  useEffect(() => {
    const fetchTopologies = async () => {
      if (!selectedNode || !selectedLinker) {
        setTopologies([])
        setSelectedTopology(null)
        return
      }
      setLoadingTopologies(true)
      try {
        const res = await getCifGeneratorTopologies(selectedNode, selectedLinker)
        setTopologies(res)
        setSelectedTopology(null)
      } catch (err) {
        console.error(err)
      } finally {
        setLoadingTopologies(false)
      }
    }
    fetchTopologies()
  }, [selectedNode, selectedLinker])

  const selectResolvedCandidate = useCallback((candidateKey, candidates = resolution?.candidates || []) => {
    const candidate = candidates.find(
      (item) => `${item.node_id}:${item.linker_id}` === candidateKey
    )
    if (!candidate) return
    setSelectedCandidateKey(candidateKey)
    setSelectedNode(candidate.node_id)
    setSelectedLinker(candidate.linker_id)
    setSelectedTopology(null)
  }, [resolution])

  const handleResolveInputs = async () => {
    if (!metalInput.trim() || !linkerInput.trim()) {
      message.warning('請輸入 metal 與 linker 名稱或 SMILES。')
      return
    }
    // A new chemical query invalidates any candidate selected by an earlier
    // query. Clear it before resolving so failures cannot leave CIF generation
    // enabled for stale node/linker IDs.
    setResolution(null)
    setSelectedCandidateKey(null)
    setSelectedNode(null)
    setSelectedLinker(null)
    setSelectedTopology(null)
    setResolvingInputs(true)
    try {
      const result = await resolveCifGeneratorInputs({
        metal: metalInput.trim(),
        linker: linkerInput.trim(),
        max_candidates: 5,
      })
      setResolution(result)
      if (result.candidates?.length) {
        const first = result.candidates[0]
        const key = `${first.node_id}:${first.linker_id}`
        selectResolvedCandidate(key, result.candidates)
        message.success(`找到 ${result.candidates.length} 個完整原子覆蓋候選。`)
      } else {
        message.warning(result.message || '找不到可自動生成 CIF 的完整匹配。')
      }
    } catch (err) {
      message.error(err?.data?.detail || '無法解析 metal/linker 輸入。')
    } finally {
      setResolvingInputs(false)
    }
  }

  // 3. Submit CIF generation job
  const handleGenerate = async () => {
    if (!selectedNode || !selectedLinker) {
      message.warning('請先選擇 Node 與 Linker！')
      return
    }
    setSubmittingJob(true)
    try {
      const payload = {
        node_id: selectedNode,
        linker_id: selectedLinker,
        topology: selectedTopology || null,
        max_results: maxResults,
      }
      const res = await createCifGeneratorJob(payload)
      setCurrentJobId(res.job_id)
      setJobStatus(res)
      setRunDetails(null)
      message.success('CIF 生成任務已提交至佇列！')

      // Start polling job status
      if (jobPollRef.current) clearInterval(jobPollRef.current)
      jobPollRef.current = setInterval(() => pollJobStatus(res.job_id), 2000)
    } catch (err) {
      message.error(err?.data?.detail || '任務提交失敗')
    } finally {
      setSubmittingJob(false)
    }
  }

  const pollJobStatus = async (jobId) => {
    try {
      const res = await getJobStatus(jobId)
      setJobStatus(res)

      if (res.status === 'succeeded' || res.status === 'failed' || res.status === 'cancelled') {
        clearInterval(jobPollRef.current)
        jobPollRef.current = null

        // Fetch run details including artifacts
        const details = await getRunStatus(jobId)
        setRunDetails(details)

        if (res.status === 'succeeded') {
          message.success('CIF 結構生成完成！')
          if (onJobSuccess) {
            onJobSuccess(jobId)
          }
        } else if (res.status === 'failed') {
          message.error(`生成失敗: ${res.message || '未知錯誤'}`)
        }
      }
    } catch (err) {
      console.error('Error polling job status:', err)
    }
  }

  const handleCancel = async () => {
    if (!currentJobId) return
    try {
      await cancelJob(currentJobId)
      message.info('取消任務請求已發送。')
    } catch (err) {
      message.error(err?.data?.detail || '取消任務失敗。')
    }
  }

  // 4. Preview CIF
  const handlePreview = async (artifactId, filename) => {
    if (!currentJobId) return
    try {
      const cifText = await getRunArtifactText(currentJobId, artifactId)
      onPreviewCif(cifText, filename)
      message.success(`已將 ${filename} 載入 3D 預覽視窗。`)
    } catch (err) {
      message.error('取得 CIF 檔案內容失敗。')
    }
  }

  const columns = [
    {
      title: '檔案名稱',
      dataIndex: 'filename',
      key: 'filename',
      render: (text) => <Text code>{text}</Text>,
    },
    {
      title: '拓撲結構 (Topology)',
      dataIndex: 'topology',
      key: 'topology',
      render: (text) => <Tag color="blue">{text}</Tag>,
    },
    {
      title: '最大 RMSD',
      dataIndex: 'max_rmsd',
      key: 'max_rmsd',
      render: (val) => (val !== null ? `${val.toFixed(4)} Å` : '-'),
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space size="middle">
          <Button
            type="primary"
            ghost
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handlePreview(record.artifact_id, record.filename)}
          >
            3D 預覽
          </Button>
          <Button
            size="small"
            icon={<DownloadOutlined />}
            href={`/api/v1/mof/runs/${encodeURIComponent(currentJobId)}/artifacts/${encodeURIComponent(record.artifact_id)}`}
            download
          >
            下載
          </Button>
        </Space>
      ),
    },
  ]

  const buildingBlocksSelected = selectedNode && selectedLinker
  const isPormakeDemo = envStatus?.version === 'demo-canned'
    || jobStatus?.message?.includes('PORMAKE-generated N409 + N10 CIF fixtures')
  const ready = isPormakeDemo || envStatus?.ready === true

  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} lg={8}>
        {/* Environment Status */}
        <Card title="PORMAKE 環境狀態" size="small" className="mof-card-glow">
          {envStatus ? (
            <Space direction="vertical" style={{ width: '100%' }} size={12}>
              <div className="mof-control-row">
                <Text>安裝狀態:</Text>
                {ready ? (
                  <Tag color="green">
                    {isPormakeDemo ? 'Static/canned synthetic ready' : `Ready (v${envStatus.version})`}
                  </Tag>
                ) : (
                  <Tag color="orange">{envStatus.installed ? 'Need repair' : 'Not installed'}</Tag>
                )}
              </div>

              {!ready && !installing && (
                <Alert
                  type="warning"
                  showIcon
                  message="未偵測到 PORMAKE 隔離虛擬環境"
                  description="CIF 生成器需要在 local_data/mof/ 建立獨立的 python 環境以執行 pormake 套件。請點擊下方按鈕進行一鍵安裝。"
                  action={
                    <Button type="primary" size="small" onClick={handleInstall}>
                      一鍵安裝
                    </Button>
                  }
                />
              )}

              {installing && (
                <div style={{ marginTop: 8 }}>
                  <Text type="secondary">{installMsg}</Text>
                  <Progress percent={installProgress} status="active" />
                  <Collapse ghost style={{ marginTop: 8 }}>
                    <Panel header="安裝日誌" key="log">
                      <pre className="mof-log-window">{installLog}</pre>
                    </Panel>
                  </Collapse>
                </div>
              )}
            </Space>
          ) : (
            <div style={{ textAlign: 'center', padding: '10px 0' }}>
              <Spin indicator={<LoadingOutlined style={{ fontSize: 24 }} spin />} />
            </div>
          )}
        </Card>

        <Card title="以化學名稱或 SMILES 自動選擇" size="small" className="mof-panel-gap mof-card-glow" style={{ opacity: ready ? 1 : 0.6 }}>
          <Space direction="vertical" style={{ width: '100%' }} size={12}>
            <Input
              disabled={!ready}
              value={metalInput}
              onChange={(event) => setMetalInput(event.target.value)}
              placeholder="Metal，例如 Cu、copper、zirconium"
            />
            <Input.TextArea
              disabled={!ready}
              value={linkerInput}
              onChange={(event) => setLinkerInput(event.target.value)}
              autoSize={{ minRows: 2, maxRows: 4 }}
              placeholder="Linker 化學名稱或 SMILES，例如 trimesic acid 或 O=C(O)c1cc(C(=O)O)cc(C(=O)O)c1"
            />
            <Button
              block
              icon={<SearchOutlined />}
              loading={resolvingInputs}
              disabled={!ready}
              onClick={handleResolveInputs}
            >
              解析並尋找 PORMAKE 候選
            </Button>

            {resolution?.candidates?.length > 0 && (
              <>
                <Alert
                  type="success"
                  showIcon
                  message={`${resolution.metal_element} / ${resolution.linker_smiles}`}
                  description="僅列出完整覆蓋 linker 原子的 exact 候選；系統已自動選擇第一名，可改選其他 SBU/N/E 組合。"
                />
                <Select
                  className="mof-full-width-control"
                  value={selectedCandidateKey}
                  onChange={selectResolvedCandidate}
                  options={resolution.candidates.map((candidate, index) => ({
                    value: `${candidate.node_id}:${candidate.linker_id}`,
                    label: `#${index + 1} ${candidate.node_id} + ${candidate.linker_id} · ${(candidate.confidence * 100).toFixed(1)}% · ${candidate.compatible_topologies.length} topologies`,
                  }))}
                />
              </>
            )}

            {resolution?.status === 'scaffold_only' && (
              <Alert
                type="warning"
                showIcon
                message="只有 scaffold 近似"
                description="PORMAKE catalog 會遺漏 linker 取代基，因此 MVP 不會自動選擇或生成 CIF。"
              />
            )}
          </Space>
        </Card>

        {/* Building block selections */}
        <Card title="選擇結構組裝基底" size="small" className="mof-panel-gap mof-card-glow" style={{ opacity: ready ? 1 : 0.6 }}>
          <Space direction="vertical" style={{ width: '100%' }} size={16}>
            <div>
              <Text strong>金屬節點 (Node / Metal)</Text>
              <Select
                showSearch
                disabled={!ready}
                className="mof-full-width-control"
                placeholder="請選擇或搜尋金屬節點"
                value={selectedNode}
                onChange={setSelectedNode}
                filterOption={(input, option) =>
                  (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                }
                options={nodes.map((item) => ({
                  value: item.id,
                  label: item.label,
                }))}
              />
            </div>

            <div>
              <Text strong>有機配體 (Linker / Organic)</Text>
              <Select
                showSearch
                disabled={!ready}
                className="mof-full-width-control"
                placeholder="請選擇或搜尋配體"
                value={selectedLinker}
                onChange={setSelectedLinker}
                filterOption={(input, option) =>
                  (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                }
                options={linkers.map((item) => ({
                  value: item.id,
                  label: item.label,
                }))}
              />
            </div>

            <div>
              <Text strong>拓撲空間篩選 (Topology Space)</Text>
              <Select
                disabled={!ready || loadingTopologies || topologies.length === 0}
                loading={loadingTopologies}
                className="mof-full-width-control"
                placeholder={
                  topologies.length === 0
                    ? '請先選擇 Node 與 Linker'
                    : 'Auto - 篩選相容拓撲 (預設)'
                }
                value={selectedTopology}
                onChange={setSelectedTopology}
                allowClear
                options={topologies.map((t) => ({ value: t, label: t }))}
              />
              {buildingBlocksSelected && topologies.length === 0 && !loadingTopologies && (
                <Text type="secondary" style={{ fontSize: '12px' }}>
                  ⚠️ 沒有找到完全相容的拓撲結構。
                </Text>
              )}
            </div>

            <div>
              <Text strong>最大生成數量上限 (Max Results)</Text>
              <div style={{ marginTop: 6 }}>
                <InputNumber
                  disabled={!ready}
                  min={1}
                  max={20}
                  value={maxResults}
                  onChange={setMaxResults}
                  style={{ width: '100%' }}
                />
              </div>
            </div>

            <Button
              type="primary"
              block
              size="large"
              icon={jobStatus?.status === 'running' || jobStatus?.status === 'queued' ? <LoadingOutlined spin /> : <PlayCircleOutlined />}
              disabled={!ready || !buildingBlocksSelected || submittingJob || jobStatus?.status === 'running' || jobStatus?.status === 'queued'}
              onClick={handleGenerate}
            >
              開始生成 CIF 結構
            </Button>
          </Space>
        </Card>
      </Col>

      <Col xs={24} lg={16}>
        {/* Job status & progress */}
        {jobStatus && (
          <Card title="生成任務進度" size="small" className="mof-card-glow">
            <Space direction="vertical" style={{ width: '100%' }} size={12}>
              <div className="mof-control-row">
                <Text strong>Job ID:</Text>
                <Text code>{jobStatus.job_id}</Text>
                <Tag
                  color={
                    jobStatus.status === 'succeeded'
                      ? 'green'
                      : jobStatus.status === 'failed'
                      ? 'red'
                      : jobStatus.status === 'cancelled'
                      ? 'gray'
                      : 'blue'
                  }
                >
                  {jobStatus.status.toUpperCase()}
                </Tag>
              </div>

              {(jobStatus.status === 'queued' || jobStatus.status === 'preparing' || jobStatus.status === 'running') && (
                <div>
                  <Text type="secondary">{jobStatus.message || '組裝中...'}</Text>
                  <Progress percent={Math.round(jobStatus.progress * 100)} status="active" />
                  <Button
                    danger
                    icon={<StopOutlined />}
                    onClick={handleCancel}
                    style={{ marginTop: 8 }}
                  >
                    取消任務
                  </Button>
                </div>
              )}

              {jobStatus.status === 'failed' && (
                <Alert
                  type="error"
                  showIcon
                  message="組裝失敗"
                  description={jobStatus.message || '執行 subprocess 錯誤。詳細日誌請查看後端儲存區。'}
                />
              )}
            </Space>
          </Card>
        )}

        {/* Results table */}
        {runDetails && (
          <Card
            title={`組裝結果 (${runDetails.artifacts?.length || 0} 個 CIF 已產出)`}
            size="small"
            className={jobStatus ? "mof-panel-gap mof-card-glow" : "mof-card-glow"}
          >
            {isPormakeDemo && (
              <Alert
                type="info"
                showIcon
                message="Demo output: precomputed PORMAKE-generated N409 + N10 fixtures."
                description="Preview and download use the exact packaged PORMAKE CIF bytes shown below; no runtime PORMAKE or PMTransformer job is launched."
                style={{ marginBottom: 12 }}
              />
            )}
            <Table
              size="small"
              dataSource={runDetails.artifacts?.map((art) => ({ ...art, key: art.artifact_id }))}
              columns={columns}
              locale={{ emptyText: '此配對組裝無可行結構產出。' }}
            />
          </Card>
        )}

        {!jobStatus && !runDetails && (
          <div className="mof-empty-viewer" style={{ minHeight: '380px' }}>
            <Space direction="vertical" align="center">
              <InfoCircleOutlined style={{ fontSize: 32, color: '#1890ff' }} />
              <Paragraph style={{ marginTop: 8, textAlign: 'center' }}>
                請在左側選擇金屬與配體，以生成可行之 MOF 多孔晶體結構。<br />
                組裝完成後，可立即透過 3D 結構器預覽與下載 CIF 檔案。
              </Paragraph>
            </Space>
          </div>
        )}
      </Col>
    </Row>
  )
}

export default CifGeneratorTab

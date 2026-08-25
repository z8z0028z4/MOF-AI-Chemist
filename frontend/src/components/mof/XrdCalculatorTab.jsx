import React, { useState, useCallback, useRef, useEffect } from 'react'
import {
  Alert,
  Button,
  Card,
  Col,
  Divider,
  Form,
  InputNumber,
  Radio,
  Row,
  Select,
  Space,
  Spin,
  Table,
  Tag,
  Tooltip,
  Typography,
  Upload,
  message,
} from 'antd'
import {
  BarChartOutlined,
  CheckCircleOutlined,
  CloudUploadOutlined,
  DownloadOutlined,
  ExperimentOutlined,
  InboxOutlined,
  InfoCircleOutlined,
  PlayCircleOutlined,
  ReloadOutlined,
  UploadOutlined,
} from '@ant-design/icons'
import Plot from 'react-plotly.js'
import { calculateXrd, getRunArtifactText, getRunStatus, getToolsStatus, listRuns } from '../../services/mofApi'

const { Title, Text, Paragraph } = Typography

// ─── CONSTANTS ───────────────────────────────────────────────────────────────

const WAVELENGTH_PRESETS = [
  { label: 'Cu Kα (1.5406 Å) — 最常用', value: 1.54060 },
  { label: 'Cu Kα1 (1.5406 Å)', value: 1.54060 },
  { label: 'Mo Kα (0.7107 Å)', value: 0.71073 },
  { label: 'Co Kα (1.7890 Å)', value: 1.78900 },
  { label: 'Fe Kα (1.9374 Å)', value: 1.93736 },
  { label: 'Ag Kα (0.5609 Å)', value: 0.56086 },
  { label: '自訂', value: 'custom' },
]

const PEAK_TABLE_COLUMNS = [
  {
    title: '排名',
    dataIndex: 'rank',
    key: 'rank',
    width: 60,
    render: (v) => <Text strong>{v}</Text>,
  },
  {
    title: '2θ (°)',
    dataIndex: 'two_theta',
    key: 'two_theta',
    width: 100,
    render: (v) => <Text>{v.toFixed(3)}</Text>,
    sorter: (a, b) => a.two_theta - b.two_theta,
  },
  {
    title: 'd 面間距 (Å)',
    dataIndex: 'd_spacing',
    key: 'd_spacing',
    width: 120,
    render: (v) => <Text>{v.toFixed(4)}</Text>,
    sorter: (a, b) => a.d_spacing - b.d_spacing,
  },
  {
    title: '相對強度',
    dataIndex: 'intensity',
    key: 'intensity',
    width: 140,
    render: (v) => (
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <div
          style={{
            width: `${Math.max(4, v)}%`,
            maxWidth: 80,
            height: 8,
            background: 'linear-gradient(90deg, #7b2ff7, #a855f7)',
            borderRadius: 4,
            minWidth: 4,
          }}
        />
        <Text>{v.toFixed(1)}</Text>
      </div>
    ),
    sorter: (a, b) => a.intensity - b.intensity,
    defaultSortOrder: 'descend',
  },
  {
    title: '米勒指數 (hkl)',
    dataIndex: 'hkl',
    key: 'hkl',
    render: (v) => (
      <Tag color="purple" style={{ fontFamily: 'monospace' }}>
        {v}
      </Tag>
    ),
  },
]

// ─── HELPERS ─────────────────────────────────────────────────────────────────

function makePlotData(result) {
  if (!result) return []

  const profileTrace = {
    type: 'scatter',
    mode: 'lines',
    name: '連續 XRD 圖譜',
    x: result.profile.two_theta,
    y: result.profile.intensity,
    line: { color: '#7b2ff7', width: 2 },
    fill: 'tozeroy',
    fillcolor: 'rgba(123, 47, 247, 0.10)',
    hovertemplate: '2θ = %{x:.3f}°<br>強度 = %{y:.1f}<extra></extra>',
  }

  const peakTrace = {
    type: 'scatter',
    mode: 'markers',
    name: '繞射峰',
    x: result.peaks.map((p) => p.two_theta),
    y: result.peaks.map((p) => p.intensity),
    marker: {
      color: '#a855f7',
      size: 8,
      symbol: 'triangle-up',
      line: { color: '#7b2ff7', width: 1.5 },
    },
    text: result.peaks.map((p) => p.hkl),
    hovertemplate:
      '2θ = %{x:.3f}°<br>強度 = %{y:.1f}<br>%{text}<extra></extra>',
  }

  return [profileTrace, peakTrace]
}

function downloadCsv(result) {
  const rows = [['排名', '2θ (°)', 'd 面間距 (Å)', '相對強度', '米勒指數']]
  result.peaks.forEach((p, i) => {
    rows.push([i + 1, p.two_theta.toFixed(4), p.d_spacing.toFixed(4), p.intensity.toFixed(2), p.hkl])
  })
  const csv = rows.map((r) => r.join(',')).join('\n')
  const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'xrd_peaks.csv'
  a.click()
  URL.revokeObjectURL(url)
}

// ─── MAIN COMPONENT ───────────────────────────────────────────────────────────

const XrdCalculatorTab = ({ lastGeneratorCifPath, lastGeneratorRunId, activeJobId, onJobLoaded, initialParams }) => {
  const autoRunExecutedRef = useRef(false)
  // Input mode: 'upload' | 'generator'
  const [inputMode, setInputMode] = useState('upload')
  const [uploadedFile, setUploadedFile] = useState(null)

  // Generator mode states
  const [generatorRunId, setGeneratorRunId] = useState('')
  const [generatorRuns, setGeneratorRuns] = useState([])
  const [selectedArtifactId, setSelectedArtifactId] = useState('')
  const [availableArtifacts, setAvailableArtifacts] = useState([])
  const [loadingRuns, setLoadingRuns] = useState(false)
  const [loadingArtifacts, setLoadingArtifacts] = useState(false)

  // Parameters
  const [wavelengthPreset, setWavelengthPreset] = useState(1.54060)
  const [customWavelength, setCustomWavelength] = useState(1.54060)
  const [maxTwoTheta, setMaxTwoTheta] = useState(80.0)
  const [fwhm, setFwhm] = useState(0.1)

  // State
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [isPrecomputedSyntheticDemo, setIsPrecomputedSyntheticDemo] = useState(false)

  const effectiveWavelength =
    wavelengthPreset === 'custom' ? customWavelength : wavelengthPreset

  useEffect(() => {
    getToolsStatus()
      .then((status) => setIsPrecomputedSyntheticDemo(status?.pmtransformer?.version === 'demo-canned'))
      .catch(() => setIsPrecomputedSyntheticDemo(false))
  }, [])

  const loadGeneratorRuns = useCallback(async () => {
    setLoadingRuns(true)
    try {
      const res = await listRuns()
      const pormakeRuns = (res || []).filter(
        (run) => run.tool === 'pormake' && run.status === 'succeeded'
      )
      setGeneratorRuns(pormakeRuns)
    } catch (err) {
      console.error('Failed to load generator runs:', err)
      message.error('無法載入組裝任務列表')
    } finally {
      setLoadingRuns(false)
    }
  }, [])

  const loadArtifactsForRun = useCallback(async (runId) => {
    if (!runId) {
      setAvailableArtifacts([])
      return
    }
    setLoadingArtifacts(true)
    try {
      const res = await getRunStatus(runId)
      const cifArtifacts = (res.artifacts || []).filter(
        (art) => art.filename && art.filename.toLowerCase().endsWith('.cif')
      )
      setAvailableArtifacts(cifArtifacts)
    } catch (err) {
      console.error('Failed to load run artifacts:', err)
      message.error('無法載入該任務的 CIF 結構列表')
      setAvailableArtifacts([])
    } finally {
      setLoadingArtifacts(false)
    }
  }, [])

  // Load generator runs when inputMode is generator
  useEffect(() => {
    if (inputMode === 'generator') {
      loadGeneratorRuns()
    }
  }, [inputMode, loadGeneratorRuns])

  // Load artifacts when generatorRunId changes
  useEffect(() => {
    loadArtifactsForRun(generatorRunId)
  }, [generatorRunId, loadArtifactsForRun])

  // Automatically use the last generator run ID if available
  useEffect(() => {
    if (lastGeneratorRunId) {
      setGeneratorRunId(lastGeneratorRunId)
      setInputMode('generator')
      loadGeneratorRuns()
    }
  }, [lastGeneratorRunId, loadGeneratorRuns])

  // Support activeJobId reopening
  useEffect(() => {
    if (activeJobId) {
      const fetchHistoryResult = async () => {
        setLoading(true)
        setError('')
        setResult(null)
        try {
          const runStatus = await getRunStatus(activeJobId)
          const xrdPatternArt = (runStatus.artifacts || []).find(
            (art) => art.artifact_id === 'xrd_pattern'
          )
          if (!xrdPatternArt) {
            throw new Error('該任務不包含 XRD 計算結果')
          }
          const text = await getRunArtifactText(activeJobId, 'xrd_pattern')
          const data = JSON.parse(text)
          // Enrich peaks with rank index
          data.peaks = data.peaks.map((p, i) => ({ ...p, rank: i + 1, key: i }))
          setResult(data)
        } catch (err) {
          setError(err.message || '載入歷史 XRD 紀錄失敗')
        } finally {
          setLoading(false)
          if (onJobLoaded) {
            onJobLoaded()
          }
        }
      }
      fetchHistoryResult()
    }
  }, [activeJobId, onJobLoaded])

  const handleCalculate = useCallback(async (overrideArtifactId) => {
    setError('')
    setResult(null)
    setLoading(true)
    try {
      const opts = {
        wavelength: effectiveWavelength,
        maxTwoTheta,
        fwhm,
      }
      if (inputMode === 'upload') {
        if (!uploadedFile) {
          setError('請先選擇一個 CIF 檔案上傳。')
          setLoading(false)
          return
        }
        opts.file = uploadedFile
      } else {
        const runId = generatorRunId || lastGeneratorRunId
        if (!runId) {
          setError('請選擇一個組裝任務。')
          setLoading(false)
          return
        }
        const artId = (overrideArtifactId && typeof overrideArtifactId === 'string') ? overrideArtifactId : selectedArtifactId
        if (!artId) {
          setError('請指定一個 CIF 結構。')
          setLoading(false)
          return
        }
        opts.generatorRunId = runId
        opts.artifactId = artId
      }
      const data = await calculateXrd(opts)
      // Enrich peaks with rank index
      data.peaks = data.peaks.map((p, i) => ({ ...p, rank: i + 1, key: i }))
      setResult(data)
    } catch (err) {
      setError(err.message || 'XRD 計算失敗，請確認 CIF 檔案格式是否正確。')
    } finally {
      setLoading(false)
    }
  }, [inputMode, uploadedFile, generatorRunId, lastGeneratorRunId, selectedArtifactId, effectiveWavelength, maxTwoTheta, fwhm])

  // Handle autoRun calculation when redirected from Proposal page
  useEffect(() => {
    if (
      initialParams &&
      initialParams.autoRun &&
      availableArtifacts &&
      availableArtifacts.length > 0 &&
      !autoRunExecutedRef.current
    ) {
      // Prefer the explicit Proposal artifact; retain topology fallback for existing routes.
      const explicitArtifact = initialParams.artifactId
      const targetTopology = initialParams.topology || '';
      const matchedArt = availableArtifacts.find(art => art.artifact_id === explicitArtifact) || availableArtifacts.find(art =>
        art.filename &&
        art.filename.toLowerCase().includes(targetTopology.toLowerCase())
      ) || availableArtifacts[0];

      if (matchedArt) {
        console.log('🚀 [XRD-AUTORUN] Automatically selecting and calculating XRD for:', matchedArt.artifact_id, matchedArt.filename);
        setSelectedArtifactId(matchedArt.artifact_id);

        // Mark as executed
        autoRunExecutedRef.current = true;

        // Execute calculation immediately
        handleCalculate(matchedArt.artifact_id);
      }
    }
  }, [initialParams, availableArtifacts, handleCalculate])

  const handleReset = () => {
    setResult(null)
    setError('')
    setUploadedFile(null)
    setGeneratorRunId(lastGeneratorRunId || '')
    setSelectedArtifactId('')
  }

  // ── Render ──────────────────────────────────────────────────────────────────
  return (
    <div style={{ padding: '0 4px' }}>
      {/* ─── Header ──────────────────────────────────────────────────────── */}
      <Alert
        type="info"
        showIcon
        icon={<ExperimentOutlined />}
        message="理論 XRD 圖譜計算"
        description={
          <span>
            根據 CIF 晶體結構檔案，使用 <strong>pymatgen</strong> 計算理論粉末 X 射線繞射 (PXRD) 圖譜。
            若您真正合成出這個 MOF，其 XRD 結果應與此圖譜接近。
            支援 PORMAKE、GCMC 模擬輸出及 CoRE MOF DB 格式。
          </span>
        }
        style={{ marginBottom: 20 }}
      />

      {isPrecomputedSyntheticDemo && (
        <Alert
          type="warning"
          showIcon
          message="Precomputed synthetic Demo XRD data"
          description="This Demo view uses only the matching repository-owned synthetic CIF and its stored offline XRD pattern; it does not run an XRD calculation."
          style={{ marginBottom: 20 }}
        />
      )}

      <Row gutter={[16, 16]}>
        {/* ─── Left Panel: Input + Parameters ──────────────────────────── */}
        <Col xs={24} lg={8}>
          <Card
            title={
              <Space>
                <UploadOutlined />
                <span>CIF 輸入來源</span>
              </Space>
            }
            size="small"
            style={{ marginBottom: 12 }}
          >
            <Radio.Group
              value={inputMode}
              onChange={(e) => setInputMode(e.target.value)}
              style={{ marginBottom: 16, width: '100%' }}
              buttonStyle="solid"
            >
              <Radio.Button value="upload" style={{ width: '50%', textAlign: 'center' }}>
                上傳 CIF 檔案
              </Radio.Button>
              <Radio.Button value="generator" style={{ width: '50%', textAlign: 'center' }}>
                使用組裝結果
              </Radio.Button>
            </Radio.Group>

            {inputMode === 'upload' ? (
              <Upload.Dragger
                accept=".cif"
                multiple={false}
                beforeUpload={(file) => {
                  setUploadedFile(file)
                  setResult(null)
                  setError('')
                  return false // prevent auto-upload
                }}
                onRemove={() => setUploadedFile(null)}
                fileList={
                  uploadedFile
                    ? [
                        {
                          uid: '-1',
                          name: uploadedFile.name,
                          status: 'done',
                        },
                      ]
                    : []
                }
                style={{ borderColor: '#7b2ff7' }}
              >
                <p className="ant-upload-drag-icon">
                  <CloudUploadOutlined style={{ color: '#7b2ff7', fontSize: 32 }} />
                </p>
                <p className="ant-upload-text" style={{ color: '#7b2ff7' }}>
                  點擊或拖曳 CIF 檔案至此處
                </p>
                <p className="ant-upload-hint" style={{ fontSize: 11 }}>
                  支援 PORMAKE、GCMC 模擬輸出及 CoRE MOF DB 格式
                </p>
              </Upload.Dragger>
            ) : (
              <Space direction="vertical" style={{ width: '100%' }} size={12}>
                <div>
                  <div style={{ marginBottom: 4 }}>
                    <Text type="secondary" style={{ fontSize: '12px' }}>選擇組裝任務 ID (Generator Run ID)</Text>
                  </div>
                  <Select
                    loading={loadingRuns}
                    style={{ width: '100%' }}
                    placeholder="請選擇組裝任務"
                    value={generatorRunId || undefined}
                    onChange={(val) => {
                      setGeneratorRunId(val)
                      setSelectedArtifactId('') // Reset artifact selection on run change
                    }}
                    options={generatorRuns.map((run) => ({
                      value: run.job_id,
                      label: `${run.job_id} (${run.message || '組裝成功'})`,
                    }))}
                  />
                  {lastGeneratorRunId && lastGeneratorRunId === generatorRunId && (
                    <div style={{ marginTop: 4 }}>
                      <span style={{ fontSize: '11px', color: 'green' }}>
                        <CheckCircleOutlined /> 已自動帶入您剛才完成的組裝結果
                      </span>
                    </div>
                  )}
                </div>
                <div>
                  <div style={{ marginBottom: 4 }}>
                    <Text type="secondary" style={{ fontSize: '12px' }}>指定 CIF 結構名稱</Text>
                  </div>
                  <Select
                    loading={loadingArtifacts}
                    disabled={!generatorRunId}
                    style={{ width: '100%' }}
                    placeholder={generatorRunId ? "請選擇 CIF 結構名稱" : "請先選擇組裝任務"}
                    value={selectedArtifactId || undefined}
                    onChange={setSelectedArtifactId}
                    options={availableArtifacts.map((art) => ({
                      value: art.artifact_id,
                      label: `${art.filename} (${art.artifact_id})`,
                    }))}
                  />
                </div>
              </Space>
            )}
          </Card>

          <Card
            title={
              <Space>
                <BarChartOutlined />
                <span>計算參數</span>
              </Space>
            }
            size="small"
          >
            <Form layout="vertical" size="small">
              <Form.Item
                label={
                  <Space>
                    <span>X 射線波長</span>
                    <Tooltip title="不同 X 射線源對應不同波長，最常用的是銅靶 Cu Kα (1.5406 Å)">
                      <InfoCircleOutlined style={{ color: '#8c8c8c' }} />
                    </Tooltip>
                  </Space>
                }
              >
                <Select
                  value={wavelengthPreset}
                  onChange={setWavelengthPreset}
                  options={WAVELENGTH_PRESETS.map((p) => ({ label: p.label, value: p.value }))}
                />
                {wavelengthPreset === 'custom' && (
                  <InputNumber
                    value={customWavelength}
                    onChange={setCustomWavelength}
                    min={0.1}
                    max={10}
                    step={0.0001}
                    precision={4}
                    addonAfter="Å"
                    style={{ width: '100%', marginTop: 8 }}
                  />
                )}
              </Form.Item>

              <Form.Item
                label={
                  <Space>
                    <span>最大 2θ 角度</span>
                    <Tooltip title="XRD 圖譜掃描的最大 2θ 角度範圍（度），通常 80° 或 60° 已足夠">
                      <InfoCircleOutlined style={{ color: '#8c8c8c' }} />
                    </Tooltip>
                  </Space>
                }
              >
                <InputNumber
                  value={maxTwoTheta}
                  onChange={setMaxTwoTheta}
                  min={20}
                  max={180}
                  step={5}
                  addonAfter="°"
                  style={{ width: '100%' }}
                />
              </Form.Item>

              <Form.Item
                label={
                  <Space>
                    <span>峰寬 (FWHM)</span>
                    <Tooltip title="Gaussian 展寬的半高全寬 (Full Width at Half Maximum)。數值越大，峰越寬。實際儀器展寬通常 0.1°~0.3°">
                      <InfoCircleOutlined style={{ color: '#8c8c8c' }} />
                    </Tooltip>
                  </Space>
                }
              >
                <InputNumber
                  value={fwhm}
                  onChange={setFwhm}
                  min={0.01}
                  max={2.0}
                  step={0.05}
                  precision={2}
                  addonAfter="°"
                  style={{ width: '100%' }}
                />
              </Form.Item>
            </Form>

            <Divider style={{ margin: '12px 0' }} />
            <Space style={{ width: '100%', justifyContent: 'space-between' }}>
              <Button icon={<ReloadOutlined />} size="small" onClick={handleReset} disabled={loading}>
                重置
              </Button>
              <Button
                type="primary"
                icon={loading ? <Spin size="small" /> : <ExperimentOutlined />}
                onClick={() => handleCalculate()}
                loading={loading}
                disabled={loading}
                style={{ background: 'linear-gradient(135deg, #7b2ff7, #a855f7)', border: 'none' }}
              >
                {loading ? '計算中…' : '計算 XRD 圖譜'}
              </Button>
            </Space>
          </Card>
        </Col>

        {/* ─── Right Panel: Result ─────────────────────────────────────── */}
        <Col xs={24} lg={16}>
          {error && (
            <Alert
              type="error"
              showIcon
              message="計算錯誤"
              description={error}
              style={{ marginBottom: 16 }}
              closable
              onClose={() => setError('')}
            />
          )}

          {loading && (
            <Card style={{ textAlign: 'center', padding: 60 }}>
              <Spin size="large" />
              <div style={{ marginTop: 16, color: '#7b2ff7' }}>
                <Text type="secondary">正在計算理論 XRD 圖譜，請稍候（通常需 10–30 秒）…</Text>
              </div>
            </Card>
          )}

          {!loading && !result && !error && (
            <Card
              style={{
                minHeight: 400,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                background: 'linear-gradient(135deg, #f9f0ff 0%, #faf5ff 100%)',
                border: '2px dashed #d3adf7',
              }}
            >
              <div style={{ textAlign: 'center', color: '#a855f7' }}>
                <ExperimentOutlined style={{ fontSize: 56, marginBottom: 16 }} />
                <div>
                  <Text style={{ color: '#7b2ff7', fontSize: 16 }}>
                    上傳或指定 CIF 檔案，再點擊「計算 XRD 圖譜」開始分析
                  </Text>
                </div>
              </div>
            </Card>
          )}

          {result && !loading && (
            <>
              {/* ── Info bar ── */}
              <Card size="small" style={{ marginBottom: 12, background: '#f9f0ff', borderColor: '#d3adf7' }}>
                <Row gutter={16}>
                  <Col span={6}>
                    <Text type="secondary" style={{ fontSize: 11 }}>空間群</Text>
                    <div>
                      <Tag color="purple" style={{ fontFamily: 'monospace', fontSize: 13 }}>
                        {result.space_group} (#{result.space_group_number})
                      </Tag>
                    </div>
                  </Col>
                  <Col span={5}>
                    <Text type="secondary" style={{ fontSize: 11 }}>晶系</Text>
                    <div>
                      <Tag color="geekblue">{result.crystal_system}</Tag>
                    </div>
                  </Col>
                  <Col span={6}>
                    <Text type="secondary" style={{ fontSize: 11 }}>波長</Text>
                    <div>
                      <Text strong style={{ fontFamily: 'monospace' }}>{result.wavelength.toFixed(5)} Å</Text>
                    </div>
                  </Col>
                  <Col span={4}>
                    <Text type="secondary" style={{ fontSize: 11 }}>繞射峰數</Text>
                    <div>
                      <Text strong>{result.num_peaks}</Text>
                    </div>
                  </Col>
                  <Col span={3} style={{ textAlign: 'right' }}>
                    <Button
                      size="small"
                      icon={<DownloadOutlined />}
                      onClick={() => downloadCsv(result)}
                      style={{ marginTop: 4 }}
                    >
                      CSV
                    </Button>
                  </Col>
                </Row>
              </Card>

              {/* ── Plotly XRD Chart ── */}
              <Card
                title={
                  <Space>
                    <CheckCircleOutlined style={{ color: '#52c41a' }} />
                    <span>理論 PXRD 圖譜</span>
                  </Space>
                }
                size="small"
                style={{ marginBottom: 12 }}
              >
                <Plot
                  data={makePlotData(result)}
                  layout={{
                    margin: { t: 20, r: 20, b: 50, l: 60 },
                    xaxis: {
                      title: { text: '2θ (°)', font: { size: 13 } },
                      showgrid: true,
                      gridcolor: '#f0e6ff',
                      range: [5, maxTwoTheta],
                    },
                    yaxis: {
                      title: { text: '相對強度 (%)', font: { size: 13 } },
                      showgrid: true,
                      gridcolor: '#f0e6ff',
                      range: [0, 110],
                    },
                    legend: { orientation: 'h', y: -0.15 },
                    paper_bgcolor: 'transparent',
                    plot_bgcolor: '#fdfbff',
                    hovermode: 'closest',
                    dragmode: 'pan',
                  }}
                  config={{
                    responsive: true,
                    displayModeBar: true,
                    displaylogo: false,
                    modeBarButtonsToRemove: ['select2d', 'lasso2d'],
                    toImageButtonOptions: {
                      format: 'png',
                      filename: 'xrd_pattern',
                      scale: 2,
                    },
                  }}
                  style={{ width: '100%', height: 320 }}
                  useResizeHandler
                />
              </Card>

              {/* ── Peak Table ── */}
              <Card
                title={
                  <Space>
                    <BarChartOutlined style={{ color: '#7b2ff7' }} />
                    <span>繞射峰列表（依強度排序）</span>
                  </Space>
                }
                size="small"
              >
                <Table
                  dataSource={result.peaks}
                  columns={PEAK_TABLE_COLUMNS}
                  size="small"
                  pagination={{ pageSize: 10, showSizeChanger: false }}
                  scroll={{ x: 500 }}
                  rowKey="key"
                />
              </Card>
            </>
          )}
        </Col>
      </Row>
    </div>
  )
}

export default XrdCalculatorTab

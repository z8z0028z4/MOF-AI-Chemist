import React, { useCallback, useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { Card, Tabs, Typography, Alert, Button } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import CifViewerTab from '../components/mof/CifViewerTab'
import CifGeneratorTab from '../components/mof/CifGeneratorTab'
import PropertyPredictorTab from '../components/mof/PropertyPredictorTab'
import MofRunResults from '../components/mof/MofRunResults'
import XrdCalculatorTab from '../components/mof/XrdCalculatorTab'
import { getMofPrivateSettingsStatus, getToolsStatus } from '../services/mofApi'
import { parseCifCharges } from '../utils/mof/cifChargeParser'
import './MOF.css'

const { Paragraph, Title, Text } = Typography

const MOF = () => {
  const location = useLocation()
  const [activeTab, setActiveTab] = useState('viewer')

  const [initialXrdParams, setInitialXrdParams] = useState(null)

  // Listen to redirect state from router
  useEffect(() => {
    if (location.state?.tab) {
      setActiveTab(location.state.tab)
      if (location.state.tab === 'viewer' && location.state.cifText) {
        setCifText(location.state.cifText)
        setFileName(location.state.filename || 'structure.cif')
        try {
          const parsed = parseCifCharges(location.state.cifText)
          setParseResult(parsed)
        } catch (err) {
          setParseResult({ charges: [], atomLabels: [], hasChargeColumn: false })
        }
      } else if (location.state.tab === 'xrd' && location.state.runId) {
        setLastGeneratorRunId(location.state.runId)
        if (!location.state.autoRun) {
          setReopenJobId(location.state.runId)
          setReopenTool('xrd')
        } else {
          setReopenJobId(null)
          setReopenTool(null)
        }
        setInitialXrdParams({
          topology: location.state.topology,
          nodeId: location.state.nodeId,
          linkerId: location.state.linkerId,
          artifactId: location.state.artifactId,
          autoRun: location.state.autoRun
        })
      }
    }
  }, [location])


  // Active CIF states (for the viewer)
  const [fileName, setFileName] = useState('')
  const [cifText, setCifText] = useState('')
  const [parseResult, setParseResult] = useState({ charges: [], atomLabels: [], hasChargeColumn: false })
  const [uploadError, setUploadError] = useState('')

  // Viewer options
  const [styleMode, setStyleMode] = useState('stick')
  const [showSurface, setShowSurface] = useState(true)
  const [surfaceType, setSurfaceType] = useState('VDW')
  const [surfaceOpacity, setSurfaceOpacity] = useState(0.5)

  // Settings status
  const [privateSettingsStatus, setPrivateSettingsStatus] = useState(null)
  const [privateSettingsError, setPrivateSettingsError] = useState('')
  const [isPropertyPredictionDemo, setIsPropertyPredictionDemo] = useState(false)

  // Integration states between tabs
  const [lastGeneratorRunId, setLastGeneratorRunId] = useState('')
  const [lastGeneratorCifPath, setLastGeneratorCifPath] = useState('')
  const [reopenJobId, setReopenJobId] = useState(null)
  const [reopenTool, setReopenTool] = useState(null)

  const loadPrivateSettingsStatus = useCallback(async () => {
    setPrivateSettingsError('')
    try {
      const status = await getMofPrivateSettingsStatus()
      setPrivateSettingsStatus(status)
    } catch (error) {
      setPrivateSettingsError(error?.data?.detail || 'PMTransformer 私有設定狀態讀取失敗。')
    }
  }, [])

  useEffect(() => {
    loadPrivateSettingsStatus()
  }, [loadPrivateSettingsStatus])

  useEffect(() => {
    getToolsStatus()
      .then((status) => setIsPropertyPredictionDemo(status?.pmtransformer?.version === 'demo-canned'))
      .catch(() => setIsPropertyPredictionDemo(false))
  }, [])

  const handleUploadCif = (name, text, parsed) => {
    setFileName(name)
    setCifText(text)
    setParseResult(parsed)
  }

  const handlePreviewCif = (text, name) => {
    setCifText(text)
    setFileName(name)
    try {
      const parsed = parseCifCharges(text)
      setParseResult(parsed)
    } catch (err) {
      setParseResult({ charges: [], atomLabels: [], hasChargeColumn: false })
    }
    setActiveTab('viewer')
  }

  const handleReset = () => {
    setFileName('')
    setCifText('')
    setParseResult({ charges: [], atomLabels: [], hasChargeColumn: false })
    setUploadError('')
  }

  const handleReopenRun = (jobId, tool) => {
    setReopenJobId(jobId)
    setReopenTool(tool)
    if (tool === 'pormake') {
      setActiveTab('generator')
    } else if (tool === 'xrd') {
      setActiveTab('xrd')
    } else {
      setActiveTab('predictor')
    }
  }

  const handleJobLoaded = () => {
    // Reset reopen states after child tabs have successfully loaded
    setReopenJobId(null)
    setReopenTool(null)
  }

  const handleGeneratorSuccess = (runId, cifPath) => {
    setLastGeneratorRunId(runId)
    if (cifPath) setLastGeneratorCifPath(cifPath)
  }

  const tabItems = [
    {
      key: 'viewer',
      label: '🔍 CIF Viewer',
      children: (
        <CifViewerTab
          fileName={fileName}
          cifText={cifText}
          parseResult={parseResult}
          styleMode={styleMode}
          setStyleMode={setStyleMode}
          showSurface={showSurface}
          setShowSurface={setShowSurface}
          surfaceType={surfaceType}
          setSurfaceType={setSurfaceType}
          surfaceOpacity={surfaceOpacity}
          setSurfaceOpacity={setSurfaceOpacity}
          uploadError={uploadError}
          setUploadError={setUploadError}
          onUploadCif={handleUploadCif}
          onReset={handleReset}
        />
      ),
    },
    {
      key: 'generator',
      label: '🧩 CIF Generator',
      children: (
        <CifGeneratorTab
          onPreviewCif={handlePreviewCif}
          activeJobId={reopenTool === 'pormake' ? reopenJobId : null}
          onJobLoaded={handleJobLoaded}
          onJobSuccess={handleGeneratorSuccess}
        />
      ),
    },
    {
      key: 'predictor',
      label: '🔮 Property Predictor',
      children: (
        <PropertyPredictorTab
          onPreviewCif={handlePreviewCif}
          lastGeneratorRunId={lastGeneratorRunId}
          activeJobId={reopenTool === 'pmtransformer' ? reopenJobId : null}
          onJobLoaded={handleJobLoaded}
        />
      ),
    },
    {
      key: 'xrd',
      label: '📈 XRD Predictor',
      children: (
        <XrdCalculatorTab
          lastGeneratorCifPath={lastGeneratorCifPath}
          lastGeneratorRunId={lastGeneratorRunId}
          activeJobId={reopenTool === 'xrd' ? reopenJobId : null}
          onJobLoaded={handleJobLoaded}
          initialParams={initialXrdParams}
        />
      ),
    },
    {
      key: 'runs',
      label: '📜 Runs',
      children: (
        <MofRunResults onReopenRun={handleReopenRun} />
      ),
    },
  ]

  return (
    <div className="mof-page">
      <div className="mof-page-header">
        <div>
          <Title level={2}>MOF AI 工具</Title>
          <Paragraph>
            本模組提供多孔晶體結構 (MOF) 的 CIF 3D 結構視覺化、基於拓撲與 PORMAKE 的幾何組裝生成，以及基於 PMTransformer 深度學習的氣體吸附量預測。
          </Paragraph>
        </div>
      </div>

      {!isPropertyPredictionDemo && privateSettingsStatus && privateSettingsStatus.ready_for_real_run === false && (
        <Alert
          type="warning"
          showIcon
          message="PMTransformer 私有權重設定未完成"
          description="系統需要包含私有模型 Checkpoint 路徑、Downstream 性質以及反正規化 mean/std 之 private_settings.json 才能執行真實預測。"
        />
      )}

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={tabItems}
        size="large"
        tabBarGutter={16}
        more={{ icon: <span className="mof-tabs-more-label">更多功能</span> }}
        className="mof-main-tabs"
      />
    </div>
  )
}

export default MOF

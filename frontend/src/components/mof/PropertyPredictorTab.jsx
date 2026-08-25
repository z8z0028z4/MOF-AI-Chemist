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
  Upload,
  Input,
  Checkbox,
  Modal,
  List,
  Tooltip,
  message,
} from 'antd'
import {
  PlayCircleOutlined,
  LoadingOutlined,
  DownloadOutlined,
  EyeOutlined,
  StopOutlined,
  InboxOutlined,
  InfoCircleOutlined,
  CheckCircleOutlined,
  FolderOpenOutlined,
  FolderOutlined,
  FileOutlined,
  ArrowLeftOutlined,
  CheckOutlined,
} from '@ant-design/icons'
import {
  getToolsStatus,
  installTool,
  getToolInstallStatus,
  getPropertyPredictorProfiles,
  createPropertyPredictorJob,
  createPropertyPredictorUploadJob,
  getJobStatus,
  cancelJob,
  listRuns,
  getRunStatus,
  getRunArtifactText,
  browseCheckpoints,
  verifyCheckpoint,
} from '../../services/mofApi'

const { Title, Text, Paragraph } = Typography
const { Panel } = Collapse
const { Dragger } = Upload

const PropertyPredictorTab = ({ onPreviewCif, lastGeneratorRunId, activeJobId, onJobLoaded }) => {
  // Env status states
  const [envStatus, setEnvStatus] = useState(null)
  const [installing, setInstalling] = useState(false)
  const [installProgress, setInstallProgress] = useState(0)
  const [installMsg, setInstallMsg] = useState('')
  const [installLog, setInstallLog] = useState('')

  // Profiles
  const [profiles, setProfiles] = useState([])
  const [selectedProfile, setSelectedProfile] = useState(() => {
    return localStorage.getItem('mof_selected_profile_id') || null
  })

  // Custom Checkpoint states
  const [customCkptPath, setCustomCkptPath] = useState(() => {
    return localStorage.getItem('mof_selected_custom_ckpt') || ''
  })
  const [ckptHistory, setCkptHistory] = useState([])
  const [verifying, setVerifying] = useState(false)
  const [verificationResult, setVerificationResult] = useState(null) // { valid: boolean, message: string, type: 'success' | 'error' | 'warning' }
  const [customParamsCollapsed, setCustomParamsCollapsed] = useState(false)
  const useCustomCkpt = !!customCkptPath

  const [customProperty, setCustomProperty] = useState(() => {
    return localStorage.getItem('mof_selected_custom_property') || 'CO2 uptake'
  })
  const [customCondition, setCustomCondition] = useState(() => {
    return localStorage.getItem('mof_selected_custom_condition') || '298 K, 0.15 bar'
  })
  const [customUnit, setCustomUnit] = useState(() => {
    return localStorage.getItem('mof_selected_custom_unit') || 'mmol/g'
  })
  const [customMean, setCustomMean] = useState(() => {
    return localStorage.getItem('mof_selected_custom_mean') || '0.0'
  })
  const [customStd, setCustomStd] = useState(() => {
    return localStorage.getItem('mof_selected_custom_std') || '1.0'
  })

  useEffect(() => {
    if (selectedProfile) {
      localStorage.setItem('mof_selected_profile_id', selectedProfile)
    } else {
      localStorage.removeItem('mof_selected_profile_id')
    }
    localStorage.setItem('mof_selected_custom_ckpt', customCkptPath || '')
    localStorage.setItem('mof_selected_custom_property', customProperty || '')
    localStorage.setItem('mof_selected_custom_condition', customCondition || '')
    localStorage.setItem('mof_selected_custom_unit', customUnit || '')
    localStorage.setItem('mof_selected_custom_mean', customMean || '')
    localStorage.setItem('mof_selected_custom_std', customStd || '')
  }, [selectedProfile, customCkptPath, customProperty, customCondition, customUnit, customMean, customStd])

  const updateCustomParam = (field, val) => {
    if (field === 'customProperty') setCustomProperty(val)
    if (field === 'customCondition') setCustomCondition(val)
    if (field === 'customUnit') setCustomUnit(val)
    if (field === 'customMean') setCustomMean(val)
    if (field === 'customStd') setCustomStd(val)
  }

  /** Save current custom params to ckptHistory + localStorage and collapse the panel. */
  const handleApplyCustomParams = () => {
    if (!customCkptPath) {
      message.warning('請先選擇一個權重檔案')
      return
    }
    setCkptHistory((prev) => {
      const arr = Array.isArray(prev) ? prev : []
      const updated = arr.map((item) => {
        if (item.ckptPath === customCkptPath) {
          return {
            ...item,
            customProperty,
            customCondition,
            customUnit,
            customMean,
            customStd,
          }
        }
        return item
      })
      localStorage.setItem('mof_ckpt_history_v2', JSON.stringify(updated))
      return updated
    })
    setCustomParamsCollapsed(true)
    message.success('自定義參數已套用並儲存！')
  }

  // Browsing modal states
  const [isBrowserOpen, setIsBrowserOpen] = useState(false)
  const [browserCurrentPath, setBrowserCurrentPath] = useState('')
  const [browserData, setBrowserData] = useState({ dirs: [], files: [], parent_path: null })
  const [loadingBrowser, setLoadingBrowser] = useState(false)
  const [selectedBrowserFile, setSelectedBrowserFile] = useState(null) // { name, path, size_bytes }

  // Input selection states
  const [inputMode, setInputMode] = useState('upload') // 'upload' or 'generator'
  const [fileList, setFileList] = useState([])
  const [generatorRunId, setGeneratorRunId] = useState('')
  const [selectedArtifactIds, setSelectedArtifactIds] = useState([]) // Array of selected artifact IDs
  const [generatorRuns, setGeneratorRuns] = useState([])
  const [loadingRuns, setLoadingRuns] = useState(false)
  const [availableArtifacts, setAvailableArtifacts] = useState([])
  const [loadingArtifacts, setLoadingArtifacts] = useState(false)
  const [confirmedHeavy, setConfirmedHeavy] = useState(false)

  // Job states
  const [currentJobId, setCurrentJobId] = useState(null)
  const [jobStatus, setJobStatus] = useState(null)
  const [runDetails, setRunDetails] = useState(null)
  const [submittingJob, setSubmittingJob] = useState(false)

  // Polling refs
  const installPollRef = useRef(null)
  const jobPollRef = useRef(null)

  // 1. Fetch env status, profiles, and set defaults
  const loadEnvStatus = useCallback(async () => {
    try {
      const res = await getToolsStatus()
      setEnvStatus(res.pmtransformer)
      if (res.pmtransformer.installed && !res.pmtransformer.ready) {
        checkInstallStatus()
      }
    } catch (err) {
      console.error('Failed to load pmtransformer tool status:', err)
    }
  }, [])

  const checkInstallStatus = useCallback(async () => {
    try {
      const res = await getToolInstallStatus('pmtransformer')
      if (res.status === 'installing') {
        setInstalling(true)
        setInstallProgress(Math.round(res.progress * 100))
        setInstallMsg(res.message)
        setInstallLog(res.log || '')

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
          message.success('PMTransformer 環境安裝成功！')
        } else if (res.status === 'failed') {
          message.error(`PMTransformer 環境安裝失敗: ${res.message}`)
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
      await installTool('pmtransformer')
      checkInstallStatus()
    } catch (err) {
      setInstalling(false)
      message.error(err?.data?.detail || '無法啟動安裝。')
    }
  }

  const loadProfiles = useCallback(async () => {
    try {
      const res = await getPropertyPredictorProfiles()
      setProfiles(res.profiles || [])
      if (res.default_profile_id) {
        setSelectedProfile(res.default_profile_id)
      } else if (res.profiles?.length > 0) {
        setSelectedProfile(res.profiles[0].id)
      }
    } catch (err) {
      console.error('Failed to load profiles:', err)
    }
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

  useEffect(() => {
    loadEnvStatus()
    loadProfiles()
    return () => {
      if (installPollRef.current) clearInterval(installPollRef.current)
      if (jobPollRef.current) clearInterval(jobPollRef.current)
    }
  }, [loadEnvStatus, loadProfiles])

  // Hook to handle reopening historical runs
  useEffect(() => {
    if (activeJobId) {
      setCurrentJobId(activeJobId)
      pollJobStatus(activeJobId)

      // Start polling if the job is active (not terminal)
      getJobStatus(activeJobId).then((res) => {
        if (res.status === 'queued' || res.status === 'running' || res.status === 'preparing') {
          if (jobPollRef.current) clearInterval(jobPollRef.current)
          jobPollRef.current = setInterval(() => pollJobStatus(activeJobId), 3000)
        }
      }).catch(console.error)

      if (onJobLoaded) {
        onJobLoaded()
      }
    }
  }, [activeJobId])

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

  // Load ckpt history from localStorage
  useEffect(() => {
    try {
      const stored = localStorage.getItem('mof_ckpt_history_v2')
      if (stored) {
        setCkptHistory(JSON.parse(stored))
      }
    } catch (err) {
      console.error('Failed to load ckpt history from localStorage:', err)
    }
  }, [])

  const saveToHistory = (profileId, ckptPath, targetProperty = '', condition = '', unit = '', mean = '', std = '') => {
    if (!profileId || !ckptPath) return
    const filename = ckptPath.split('/').pop()
    setCkptHistory((prev) => {
      const arr = Array.isArray(prev) ? prev : []
      const filtered = arr.filter((item) => item.ckptPath !== ckptPath)
      const updated = [{
        profileId,
        ckptPath,
        filename,
        customProperty: targetProperty,
        customCondition: condition,
        customUnit: unit,
        customMean: mean,
        customStd: std
      }, ...filtered].slice(0, 10)
      localStorage.setItem('mof_ckpt_history_v2', JSON.stringify(updated))
      return updated
    })
  }

  const handleVerifyCkpt = async (pathToCheck, shouldSelectOnSuccess = false) => {
    const targetPath = pathToCheck || customCkptPath
    if (!targetPath) {
      message.warning('請先輸入或選擇權重檔案路徑')
      return false
    }
    setVerifying(true)
    setVerificationResult(null)
    try {
      const res = await verifyCheckpoint(targetPath)
      if (res.valid) {
        setVerificationResult({
          valid: true,
          message: res.info || '驗證成功！',
          type: 'success',
        })
        message.success('權重檔案驗證成功！')
        const profile = profiles.find(p => p.id === selectedProfile)
        const initProp = profile?.target_property || 'CO2 uptake'
        const initCond = profile?.condition || '298 K, 0.15 bar'
        const initUnit = profile?.unit || 'mmol/g'
        const initMean = String(profile?.normalization?.mean || '0.0')
        const initStd = String(profile?.normalization?.std || '1.0')

        setCustomProperty(initProp)
        setCustomCondition(initCond)
        setCustomUnit(initUnit)
        setCustomMean(initMean)
        setCustomStd(initStd)

        saveToHistory(selectedProfile, targetPath, initProp, initCond, initUnit, initMean, initStd)
        setCustomParamsCollapsed(false) // Show expanded form so user can adjust params before "套用"
        if (shouldSelectOnSuccess) {
          setCustomCkptPath(targetPath)
        }
        return true
      } else {
        setVerificationResult({
          valid: false,
          message: res.error || '驗證失敗',
          type: 'error',
        })
        message.error(`驗證失敗: ${res.error || '未知錯誤'}`)
        if (shouldSelectOnSuccess) {
          setCustomCkptPath('')
        }
        return false
      }
    } catch (err) {
      const errorMsg = err?.data?.detail || err.message || '連線驗證失敗'
      setVerificationResult({
        valid: false,
        message: errorMsg,
        type: 'error',
      })
      message.error('驗證過程中發生錯誤')
      if (shouldSelectOnSuccess) {
        setCustomCkptPath('')
      }
      return false
    } finally {
      setVerifying(false)
    }
  }

  const handleOpenBrowser = async () => {
    setIsBrowserOpen(true)
    setSelectedBrowserFile(null)
    await loadBrowserPath(browserCurrentPath || '')
  }

  const loadBrowserPath = async (path) => {
    setLoadingBrowser(true)
    try {
      const res = await browseCheckpoints(path)
      setBrowserCurrentPath(res.current_path)
      setBrowserData({
        dirs: res.dirs || [],
        files: res.files || [],
        parent_path: res.parent_path,
      })
    } catch (err) {
      message.error(err?.data?.detail || '無法讀取伺服器目錄')
    } finally {
      setLoadingBrowser(false)
    }
  }

  const formatBytes = (bytes, decimals = 2) => {
    if (!bytes) return '0 Bytes'
    const k = 1024
    const dm = decimals < 0 ? 0 : decimals
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i]
  }

  // 2. Submit prediction job
  const isDemoCanned = envStatus?.version === 'demo-canned'

  const handlePredict = async () => {
    if (!selectedProfile) {
      message.warning('請選擇模型 Profile！')
      return
    }
    if (useCustomCkpt && !customCkptPath) {
      message.warning('請設定自定義微調權重檔路徑！')
      return
    }
    if (inputMode === 'upload' && fileList.length === 0) {
      message.warning('請先選擇上傳 CIF 檔案！')
      return
    }
    if (inputMode === 'generator' && !generatorRunId) {
      message.warning('請選擇組裝任務！')
      return
    }
    if (!isDemoCanned && !confirmedHeavy) {
      message.warning('請勾選確認執行重型模型推論！')
      return
    }

    setSubmittingJob(true)
    try {
      let res
      if (inputMode === 'generator') {
        const formData = new FormData()
        formData.append('profile_id', selectedProfile)
        if (useCustomCkpt && customCkptPath) {
          formData.append('custom_checkpoint_path', customCkptPath)
          formData.append('custom_target_property', customProperty)
          formData.append('custom_condition', customCondition)
          formData.append('custom_unit', customUnit)
          formData.append('custom_mean', customMean)
          formData.append('custom_std', customStd)
        }
        formData.append('generator_run_id', generatorRunId)
        if (selectedArtifactIds && selectedArtifactIds.length > 0) {
          formData.append('artifact_ids', selectedArtifactIds.join(','))
        }
        res = await createPropertyPredictorJob(formData)
      } else {
        const files = await Promise.all(
          fileList.map(async (file) => ({
            filename: file.name,
            content: await file.text(),
          }))
        )
        res = await createPropertyPredictorUploadJob({
          profile_id: selectedProfile,
          files,
          ...(useCustomCkpt && customCkptPath
            ? {
                custom_checkpoint_path: customCkptPath,
                custom_target_property: customProperty,
                custom_condition: customCondition,
                custom_unit: customUnit,
                custom_mean: Number(customMean),
                custom_std: Number(customStd),
              }
            : {}),
        })
      }

      setCurrentJobId(res.job_id)
      setJobStatus(res)
      setRunDetails(null)
      message.success(isDemoCanned ? 'Demo 靜態/罐裝性質預測結果已載入！' : '性質預測任務已提交！')

      if (jobPollRef.current) clearInterval(jobPollRef.current)
      jobPollRef.current = setInterval(() => pollJobStatus(res.job_id), 3000)
    } catch (err) {
      console.error('Property predictor job submission failed:', err)
      message.error(err?.data?.detail || err?.message || '任務提交失敗')
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

        const details = await getRunStatus(jobId)
        setRunDetails(details)

        if (res.status === 'succeeded') {
          message.success(isDemoCanned ? 'Demo 靜態/罐裝性質預測結果已載入！' : '性質預測計算完成！')
        } else if (res.status === 'failed') {
          message.error(`預測失敗: ${res.message || '未知錯誤'}`)
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

  // 3. Preview CIF
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

  const uploadProps = {
    accept: '.cif',
    multiple: true,
    fileList,
    onRemove: (file) => {
      const index = fileList.indexOf(file)
      const newFileList = fileList.slice()
      newFileList.splice(index, 1)
      setFileList(newFileList)
    },
    beforeUpload: (file) => {
      if (!file.name.toLowerCase().endsWith('.cif')) {
        message.error(`${file.name} 不是 CIF 檔案！`)
        return Upload.LIST_IGNORE
      }
      if (fileList.length >= 10) {
        message.warning('最多只能上傳 10 個 CIF 檔案。')
        return Upload.LIST_IGNORE
      }
      setFileList((prev) => [...prev, file])
      return false
    },
  }

  const activeProfileData = profiles.find((p) => p.id === selectedProfile)
  const ready = envStatus?.ready === true

  const handleSelectProfileOrCkpt = (val) => {
    if (val.startsWith('custom:')) {
      const parts = val.substring(7).split('|')
      const profileId = parts[0]
      const ckptPath = parts.slice(1).join('|')
      setSelectedProfile(profileId)
      setCustomCkptPath(ckptPath)

      const historyItem = ckptHistory.find(h => h.ckptPath === ckptPath)
      const profile = profiles.find(p => p.id === profileId)

      setCustomProperty(historyItem?.customProperty || profile?.target_property || 'CO2 uptake')
      setCustomCondition(historyItem?.customCondition || profile?.condition || '298 K, 0.15 bar')
      setCustomUnit(historyItem?.customUnit || profile?.unit || 'mmol/g')
      setCustomMean(historyItem?.customMean !== undefined ? String(historyItem.customMean) : String(profile?.normalization?.mean || '0.0'))
      setCustomStd(historyItem?.customStd !== undefined ? String(historyItem.customStd) : String(profile?.normalization?.std || '1.0'))

      // Restore previously saved params – show collapsed
      setCustomParamsCollapsed(true)
      setVerificationResult({
        valid: true,
        message: `已選定自定義權重：${ckptPath.split('/').pop()}`,
        type: 'success',
      })
    } else {
      setSelectedProfile(val)
      setCustomCkptPath('')
      setCustomParamsCollapsed(false)
      setVerificationResult(null)
    }
  }

  const currentDropdownValue = customCkptPath
    ? `custom:${selectedProfile}|${customCkptPath}`
    : selectedProfile

  const presetOptions = profiles.map((p) => ({
    value: p.id,
    label: p.label,
  }))

  const combinedOptions = [
    {
      label: '標準性質模型 Profile',
      options: presetOptions,
    },
  ]

  const profileMap = new Map(profiles.map(p => [p.id, p]))
  if (ckptHistory && ckptHistory.length > 0) {
    const customOptions = ckptHistory.map((h) => {
      const profile = profileMap.get(h.profileId)
      const profileLabel = profile ? profile.label : h.profileId
      return {
        value: `custom:${h.profileId}|${h.ckptPath}`,
        label: `${profileLabel} (微調檔: ${h.filename})`,
      }
    })
    combinedOptions.push({
      label: '已選定之自定義微調權重 (.ckpt)',
      options: customOptions,
    })
  }

  const columns = [
    {
      title: 'CIF 結構名稱',
      dataIndex: 'filename',
      key: 'filename',
      render: (text) => <Text code>{text}</Text>,
    },
    {
      title: '性質預測值',
      dataIndex: 'predicted_value',
      key: 'predicted_value',
      render: (val, record) => (
        <span style={{ fontWeight: 'bold', color: '#722ed1', fontSize: '15px' }}>
          {val !== null ? val.toFixed(4) : '-'} {record.unit}
        </span>
      ),
      sorter: (a, b) => (a.predicted_value || 0) - (b.predicted_value || 0),
      defaultSortOrder: 'descend',
    },
    {
      title: '預測屬性 / 條件',
      key: 'property_cond',
      render: (_, record) => (
        <Space direction="vertical" size={2}>
          <Tag color="purple">{record.target_property}</Tag>
          <Text type="secondary" style={{ fontSize: '11px' }}>{record.condition}</Text>
        </Space>
      ),
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
        </Space>
      ),
    },
  ]

  return (
    <>
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={8}>
          {/* Environment Status */}
          <Card title={isDemoCanned ? 'Demo 性質預測狀態' : 'PMTransformer 環境狀態'} size="small" className="mof-card-glow">
            {envStatus ? (
              <Space direction="vertical" style={{ width: '100%' }} size={12}>
                {isDemoCanned && (
                  <Alert
                    type="info"
                    showIcon
                    message="Demo static/canned/synthetic output"
                    description="此路徑只顯示包裝的靜態範例結果；不會載入 PMTransformer、PyTorch 或私有 checkpoint，也不會進行真實計算。"
                  />
                )}
                <div className="mof-control-row">
                  <Text>{isDemoCanned ? 'Demo 狀態:' : '安裝狀態:'}</Text>
                  {envStatus.ready ? (
                    <Tag color="green">{isDemoCanned ? 'Static/canned synthetic ready' : `Ready (v${envStatus.version})`}</Tag>
                  ) : (
                    <Tag color="orange">{envStatus.installed ? 'Need repair' : 'Not installed'}</Tag>
                  )}
                </div>

                {!isDemoCanned && !envStatus.ready && !installing && (
                  <Alert
                    type="warning"
                    showIcon
                    message="未偵測到 PMTransformer 隔離環境"
                    description="PMTransformer 預測功能依賴 PyTorch, PyTorch Lightning 與 MOFTransformer 重型環境，需要幾分鐘時間下載安裝。請點擊按鈕進行一鍵安裝。"
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

          {/* Model Profile & Inputs */}
          <Card title="設定性質預測與輸入" size="small" className="mof-panel-gap mof-card-glow" style={{ opacity: ready ? 1 : 0.6 }}>
            <Space direction="vertical" style={{ width: '100%' }} size={16}>
              <div>
                <Text strong style={{ display: 'block', marginBottom: '6px' }}>性質模型 Profile</Text>
                <div style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
                  <Select
                    disabled={!ready || profiles.length === 0}
                    style={{ flex: 1 }}
                    value={currentDropdownValue}
                    onChange={handleSelectProfileOrCkpt}
                    options={combinedOptions}
                    placeholder="選擇性質模型 Profile 或已驗證的微調檔"
                    dropdownRender={(menu) => (
                      <>
                        {menu}
                        {ckptHistory && ckptHistory.length > 0 && (
                          <div style={{ borderTop: '1px solid #f0f0f0', padding: '4px 8px', textAlign: 'right' }}>
                            <Button
                              type="text"
                              danger
                              size="small"
                              onClick={() => {
                                setCkptHistory([])
                                localStorage.removeItem('mof_ckpt_history_v2')
                                handleSelectProfileOrCkpt(selectedProfile)
                              }}
                            >
                              清除歷史紀錄
                            </Button>
                          </div>
                        )}
                      </>
                    )}
                  />
                  <Button
                    disabled={!ready || !selectedProfile}
                    icon={<FolderOpenOutlined />}
                    onClick={handleOpenBrowser}
                  >
                    瀏覽
                  </Button>
                </div>

                {/* Verification result + loading indicator */}
                {verifying && (
                  <div style={{ marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 8px', background: '#f6f0ff', borderRadius: '4px', border: '1px solid #d3adf7' }}>
                    <Spin size="small" />
                    <Text style={{ fontSize: '12px', color: '#722ed1' }}>正在驗證權重檔案...</Text>
                  </div>
                )}

                {!verifying && verificationResult && (
                  <div style={{ marginBottom: '8px' }}>
                    <Alert
                      message={
                        <span style={{ fontSize: '12px' }}>
                          {verificationResult.valid ? (
                            <CheckCircleOutlined style={{ color: '#52c41a', marginRight: '4px' }} />
                          ) : (
                            <StopOutlined style={{ color: '#ff4d4f', marginRight: '4px' }} />
                          )}
                          {verificationResult.message}
                        </span>
                      }
                      type={verificationResult.type}
                      showIcon={false}
                      size="small"
                      style={{ padding: '4px 8px' }}
                    />
                  </div>
                )}

                {activeProfileData && !customCkptPath && (
                  <div style={{ fontSize: '12px', color: 'rgba(0,0,0,0.45)', background: '#fafafa', padding: '8px', borderRadius: '4px', border: '1px solid #f0f0f0' }}>
                    目標性質: <Tag color="blue" size="small">{activeProfileData.target_property}</Tag><br />
                    測量條件: <Text strong>{activeProfileData.condition}</Text><br />
                    單位: <Text strong>{activeProfileData.unit}</Text>
                  </div>
                )}

                {customCkptPath && (
                  <div style={{ background: '#fcf8ff', padding: '12px', borderRadius: '4px', border: '1px dashed #d3adf7', marginTop: '8px' }}>
                    {/* Collapsed summary view */}
                    {customParamsCollapsed ? (
                      <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <div style={{ fontSize: '12px' }}>
                            <Tag color="purple">{customProperty}</Tag>
                            <Text type="secondary">{customCondition}</Text>
                            {customUnit && <Text type="secondary" style={{ marginLeft: '4px' }}>({customUnit})</Text>}
                            <Text type="secondary" style={{ marginLeft: '8px', fontSize: '11px' }}>Mean={customMean}, Std={customStd}</Text>
                          </div>
                          <Button
                            type="link"
                            size="small"
                            onClick={() => setCustomParamsCollapsed(false)}
                            style={{ padding: 0, fontSize: '12px' }}
                          >
                            編輯參數
                          </Button>
                        </div>
                        <div style={{ marginTop: '4px', fontSize: '10px', color: 'rgba(0,0,0,0.35)', wordBreak: 'break-all' }}>
                          {customCkptPath.split('/').pop()}
                        </div>
                      </div>
                    ) : (
                      /* Expanded edit form */
                      <>
                        <div style={{ marginBottom: '8px', fontWeight: 'bold', color: '#722ed1', fontSize: '13px' }}>
                          自定義微調模型參數設定
                        </div>
                        <Row gutter={[8, 8]}>
                          <Col span={12}>
                            <div style={{ fontSize: '11px', marginBottom: '2px' }}>預測性質名稱</div>
                            <Input
                              size="small"
                              value={customProperty}
                              onChange={(e) => updateCustomParam('customProperty', e.target.value)}
                              placeholder="例如: CO2 uptake"
                            />
                          </Col>
                          <Col span={12}>
                            <div style={{ fontSize: '11px', marginBottom: '2px' }}>預測條件</div>
                            <Input
                              size="small"
                              value={customCondition}
                              onChange={(e) => updateCustomParam('customCondition', e.target.value)}
                              placeholder="例如: 298 K, 0.15 bar"
                            />
                          </Col>
                          <Col span={24}>
                            <div style={{ fontSize: '11px', marginBottom: '2px' }}>預測單位</div>
                            <Input
                              size="small"
                              value={customUnit}
                              onChange={(e) => updateCustomParam('customUnit', e.target.value)}
                              placeholder="例如: mmol/g"
                            />
                          </Col>
                          <Col span={12}>
                            <div style={{ fontSize: '11px', marginBottom: '2px' }}>正規化平均值 (Mean)</div>
                            <Input
                              size="small"
                              type="number"
                              step="any"
                              value={customMean}
                              onChange={(e) => updateCustomParam('customMean', e.target.value)}
                              placeholder="0.0"
                            />
                          </Col>
                          <Col span={12}>
                            <div style={{ fontSize: '11px', marginBottom: '2px' }}>正規化標準差 (Std)</div>
                            <Input
                              size="small"
                              type="number"
                              step="any"
                              value={customStd}
                              onChange={(e) => updateCustomParam('customStd', e.target.value)}
                              placeholder="1.0"
                            />
                          </Col>
                        </Row>
                        <div style={{ marginTop: '10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <div style={{ fontSize: '11px', color: 'rgba(0,0,0,0.45)', wordBreak: 'break-all', flex: 1, marginRight: '8px' }}>
                            權重路徑: <Text code style={{ fontSize: '10px' }}>{customCkptPath}</Text>
                          </div>
                          <Button
                            type="primary"
                            size="small"
                            icon={<CheckOutlined />}
                            onClick={handleApplyCustomParams}
                          >
                            套用設定
                          </Button>
                        </div>
                      </>
                    )}
                  </div>
                )}
              </div>

              <div>
                <Text strong>CIF 輸入來源</Text>
                <div style={{ marginTop: 8, marginBottom: 8 }}>
                  <Button.Group style={{ width: '100%' }}>
                    <Button
                      disabled={!ready}
                      type={inputMode === 'upload' ? 'primary' : 'default'}
                      onClick={() => setInputMode('upload')}
                      style={{ width: '50%' }}
                    >
                      上傳 CIF 檔案
                    </Button>
                    <Button
                      disabled={!ready}
                      type={inputMode === 'generator' ? 'primary' : 'default'}
                      onClick={() => setInputMode('generator')}
                      style={{ width: '50%' }}
                    >
                      使用組裝結果
                    </Button>
                  </Button.Group>
                </div>

                {inputMode === 'upload' ? (
                  <div>
                    <Dragger {...uploadProps} disabled={!ready}>
                      <p className="ant-upload-drag-icon">
                        <InboxOutlined />
                      </p>
                      <p className="ant-upload-text">選擇 1~10 個 CIF 檔案</p>
                    </Dragger>
                  </div>
                ) : (
                  <Space direction="vertical" style={{ width: '100%' }} size={12}>
                    <div>
                      <div style={{ marginBottom: 4 }}>
                        <Text type="secondary" style={{ fontSize: '12px' }}>選擇組裝任務 ID (Generator Run ID)</Text>
                      </div>
                      <Select
                        loading={loadingRuns}
                        disabled={!ready}
                        className="mof-full-width-control"
                        placeholder="請選擇組裝任務"
                        value={generatorRunId || undefined}
                        onChange={(val) => {
                          setGeneratorRunId(val)
                          setSelectedArtifactIds([]) // Reset artifact selection on run change
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
                        <Text type="secondary" style={{ fontSize: '12px' }}>指定 CIF 結構名稱 (選填)</Text>
                      </div>
                      <Select
                        mode="multiple"
                        loading={loadingArtifacts}
                        disabled={!ready || !generatorRunId}
                        className="mof-full-width-control"
                        placeholder={generatorRunId ? "請選擇 CIF 結構名稱 (留空預設預測全部)" : "請先選擇組裝任務"}
                        value={selectedArtifactIds}
                        onChange={setSelectedArtifactIds}
                        options={availableArtifacts.map((art) => ({
                          value: art.artifact_id,
                          label: `${art.filename} (${art.artifact_id})`,
                        }))}
                        maxTagCount="responsive"
                      />
                    </div>
                  </Space>
                )}
              </div>

              {isDemoCanned ? (
                <Alert
                  type="info"
                  showIcon
                  message="Demo static/canned/synthetic click-through"
                  description="可使用 Demo Generator 結果或上傳包裝的 synthetic CIF；開始後只會取得既有的靜態/罐裝結果。"
                />
              ) : (
                <div style={{ background: '#fffbe6', border: '1px solid #ffe58f', borderRadius: '4px', padding: '10px' }}>
                  <Checkbox
                    disabled={!ready}
                    checked={confirmedHeavy}
                    onChange={(e) => setConfirmedHeavy(e.target.checked)}
                  >
                    <span style={{ fontSize: '12px', color: 'rgba(0,0,0,0.85)' }}>
                      ⚠️ 我已知悉 PMTransformer 需要進行特徵提取與深度學習推論，此計算屬於重型工作。
                    </span>
                  </Checkbox>
                </div>
              )}

              <Button
                type="primary"
                block
                size="large"
                icon={jobStatus?.status === 'running' || jobStatus?.status === 'queued' ? <LoadingOutlined spin /> : <PlayCircleOutlined />}
                disabled={!ready || (!isDemoCanned && !confirmedHeavy) || submittingJob || jobStatus?.status === 'running' || jobStatus?.status === 'queued'}
                onClick={handlePredict}
              >
                開始進行性質預測
              </Button>
            </Space>
          </Card>
        </Col>

        <Col xs={24} lg={16}>
          {/* Job status & progress */}
          {jobStatus && (
            <Card title="推論任務進度" size="small" className="mof-card-glow">
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
                    <Text type="secondary">{jobStatus.message || '預測特徵與載入模型中...'}</Text>
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
                    message="預測失敗"
                    description={jobStatus.message || '執行深度推論錯誤。詳細日誌請查看後端儲存區。'}
                  />
                )}
              </Space>
            </Card>
          )}

          {/* Results table */}
          {runDetails && (
            <Card
              title={`性質排序結果`}
              size="small"
              className={jobStatus ? "mof-panel-gap mof-card-glow" : "mof-card-glow"}
              extra={
                runDetails.artifacts?.some(a => a.artifact_id === 'predictions-csv') && (
                  <Button
                    size="small"
                    icon={<DownloadOutlined />}
                    href={`/api/v1/mof/runs/${encodeURIComponent(currentJobId)}/artifacts/predictions-csv`}
                    download
                  >
                    下載 CSV
                  </Button>
                )
              }
            >
              {isDemoCanned && (
                <Alert
                  type="info"
                  showIcon
                  style={{ marginBottom: 12 }}
                  message="Demo result: static/canned/synthetic output"
                  description="這些數值為預先包裝的示範資料，並非 PMTransformer 計算結果。"
                />
              )}
              {runDetails.failures?.length > 0 && (
                <Collapse ghost style={{ marginBottom: 16 }}>
                  <Panel header={<Text type="danger">⚠️ 部分結構預測失敗項目 ({runDetails.failures.length})</Text>} key="fails">
                    <Table
                      size="small;;"
                      pagination={false}
                      dataSource={runDetails.failures.map((f, i) => ({ ...f, key: i }))}
                      columns={[
                        { title: '檔案', dataIndex: 'filename', key: 'filename' },
                        { title: '原因', dataIndex: 'message', key: 'message', render: (text) => <span style={{ color: 'red' }}>{text}</span> },
                      ]}
                    />
                  </Panel>
                </Collapse>
              )}

              <Table
                size="small"
                dataSource={runDetails.artifacts?.filter(a => a.artifact_id !== 'predictions-csv').map((art) => ({ ...art, key: art.artifact_id }))}
                columns={columns}
                locale={{ emptyText: '無可行之預測結果。' }}
              />
            </Card>
          )}

          {!jobStatus && !runDetails && (
            <div className="mof-empty-viewer" style={{ minHeight: '380px' }}>
              <Space direction="vertical" align="center">
                <InfoCircleOutlined style={{ fontSize: 32, color: '#722ed1' }} />
                <Paragraph style={{ marginTop: 8, textAlign: 'center' }}>
                  請在左側選擇性質預測模型 Profile 並且上傳 CIF 結構，或帶入剛才組裝完成的結構項目。<br />
                  深度學習模型將預測實際物理吸附量，並進行排序。組裝完成後可預覽 3D 結構與下載結果報告。
                </Paragraph>
              </Space>
            </div>
          )}
        </Col>
      </Row>

      {/* File Browser Modal */}
      <Modal
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <FolderOpenOutlined style={{ color: '#722ed1' }} />
            <span>選擇伺服器權重檔案 (.ckpt)</span>
          </div>
        }
        visible={isBrowserOpen}
        onCancel={() => setIsBrowserOpen(false)}
        width={700}
        footer={[
          <Button key="cancel" onClick={() => setIsBrowserOpen(false)}>
            取消
          </Button>,
          <Button
            key="select"
            type="primary"
            disabled={!selectedBrowserFile}
            onClick={() => {
              if (selectedBrowserFile) {
                setVerificationResult(null)
                setIsBrowserOpen(false)
                handleVerifyCkpt(selectedBrowserFile.path, true)
              }
            }}
          >
            確定選擇
          </Button>,
        ]}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {/* Path Navigation Bar */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              background: '#f5f5f5',
              padding: '6px 12px',
              borderRadius: '4px',
              border: '1px solid #d9d9d9',
            }}
          >
            <Button
              size="small"
              icon={<ArrowLeftOutlined />}
              disabled={!browserData.parent_path}
              onClick={() => loadBrowserPath(browserData.parent_path)}
            />
            <Text code style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {browserCurrentPath}
            </Text>
          </div>

          {/* Directory & File List */}
          <div
            style={{
              border: '1px solid #f0f0f0',
              borderRadius: '4px',
              maxHeight: '350px',
              overflowY: 'auto',
              minHeight: '200px',
            }}
          >
            {loadingBrowser ? (
              <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '200px' }}>
                <Spin tip="讀取目錄中..." />
              </div>
            ) : (
              <List
                size="small"
                dataSource={[
                  ...(browserData.dirs || []).map(d => ({ ...d, d_key: `dir-${d.path}`, isDir: true })),
                  ...(browserData.files || []).map(f => ({ ...f, d_key: `file-${f.path}`, isDir: false }))
                ]}
                renderItem={(item) => {
                  const isSelected = selectedBrowserFile && selectedBrowserFile.path === item.path
                  return (
                    <List.Item
                      key={item.d_key}
                      onClick={() => {
                        if (item.isDir) {
                          loadBrowserPath(item.path)
                        } else {
                          setSelectedBrowserFile(item)
                        }
                      }}
                      onDoubleClick={() => {
                        if (item.isDir) {
                          loadBrowserPath(item.path)
                        } else {
                          setSelectedBrowserFile(item)
                          setVerificationResult(null)
                          setIsBrowserOpen(false)
                          handleVerifyCkpt(item.path, true)
                        }
                      }}
                      style={{
                        cursor: 'pointer',
                        background: isSelected ? '#f9f0ff' : 'transparent',
                        borderBottom: '1px solid #f0f0f0',
                        padding: '8px 16px',
                        transition: 'background 0.2s',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', width: '100%', gap: '8px' }}>
                        {item.isDir ? (
                          <FolderOutlined style={{ color: '#ffc53d', fontSize: '16px' }} />
                        ) : (
                          <FileOutlined style={{ color: '#597ef7', fontSize: '16px' }} />
                        )}

                        <div style={{ flex: 1, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <span style={{ fontWeight: item.isDir ? 500 : 'normal' }}>
                            {item.name}
                          </span>
                          {!item.isDir && (
                            <Text type="secondary" style={{ fontSize: '12px' }}>
                              {formatBytes(item.size_bytes)}
                            </Text>
                          )}
                        </div>

                        {isSelected && <CheckOutlined style={{ color: '#722ed1' }} />}
                      </div>
                    </List.Item>
                  )
                }}
                locale={{ emptyText: '無資料或權限不足' }}
              />
            )}
          </div>
        </div>
      </Modal>
    </>
  )
}

export default PropertyPredictorTab

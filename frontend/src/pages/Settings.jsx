import { InfoCircleOutlined, KeyOutlined, ReloadOutlined, SaveOutlined, SettingOutlined } from '@ant-design/icons'
import { Alert, Button, Card, Col, Divider, Form, Input, InputNumber, message, Row, Select, Slider, Space, Switch, Typography } from 'antd'
import React, { useEffect, useState } from 'react'
import { getApiErrorMessage } from '../services/apiClient'
import {
  getDevModeStatus,
  getDemoModeSettings,
  getEnvStatus,
  getJsonSchemaParameters,
  getJsonSchemaParametersInfo,
  getLlmParameters,
  getModelParametersInfo,
  getModelSettings,
  saveGoogleApiKey,
  saveOpenAiApiKey,
  updateDevModeStatus,
  updateDemoModeSettings,
  updateJsonSchemaParameters,
  updateLlmParameters,
  updateModelSettings,
} from '../services/settingsApi'

const { Title, Text } = Typography
const { Option } = Select
const { Password } = Input

const Settings = () => {
  const [form] = Form.useForm()
  const [apiKeyForm] = Form.useForm()
  const [googleApiKeyForm] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [currentModel, setCurrentModel] = useState('')
  const [selectedModel, setSelectedModel] = useState('') // 新增：追蹤當前選擇的模型
  const [envStatus, setEnvStatus] = useState({
    exists: false,
    openai_key_configured: false,
    google_key_configured: false
  })
  const [llmParams, setLlmParams] = useState({
    max_tokens: 4000,
    timeout: 120,
    reasoning_effort: 'medium',
    verbosity: 'medium',
  })
  const [supportedParams, setSupportedParams] = useState({})
  const [modelParamsInfo, setModelParamsInfo] = useState({})
  const [jsonSchemaParams, setJsonSchemaParams] = useState({
    min_length: 5,
    max_length: 100
  })
  const [jsonSchemaSupportedParams, setJsonSchemaSupportedParams] = useState({})
  const [isDevMode, setIsDevMode] = useState(false) // 開發模式狀態
  const [demoMode, setDemoMode] = useState({
    enabled: false,
    mock_proposal: false,
    mock_property_prediction: false,
    mock_generate_new_idea: false,
    mock_experiment_detail: false,
  })

  const defaultModelOptions = [
    {
      value: 'gpt-5',
      label: 'GPT-5',
      description: '最新的GPT-5模型，功能最強大，支援推理控制和工具鏈'
    },
    {
      value: 'gpt-5-nano',
      label: 'GPT-5 Nano',
      description: 'GPT-5的輕量版本，速度最快，適合簡單格式化任務'
    },
    {
      value: 'gpt-5-mini',
      label: 'GPT-5 Mini',
      description: 'GPT-5的平衡版本，速度與功能兼具，支援推理控制'
    },
    {
      value: 'gemini-3-pro-preview',
      label: 'Gemini 3 Pro',
      description: 'Google 最強大的多模態模型，適合複雜的研究分析與推理'
    },
    {
      value: 'gemini-3-flash-preview',
      label: 'Gemini 3 Flash',
      description: 'Google 的輕量高性能模型，適合快速響應與大規模數據處理'
    },
    {
      value: 'gemini-2.5-flash-lite-preview',
      label: 'Gemini 2.5 Flash Lite',
      description: 'Google 最經濟高效的模型，適合簡單的文本生成任務'
    },
    {
      value: 'gemini-2.5-flash',
      label: 'Gemini 2.5 Flash',
      description: 'Google 的主流高性能模型，速度與能力兼備 (穩定版)'
    },
    {
      value: 'gemini-2.5-pro',
      label: 'Gemini 2.5 Pro',
      description: 'Google 的高難度任務專用模型，具備優異的代碼和學術推理能力 (穩定版)'
    }
  ]

  const [availableModels, setAvailableModels] = useState(defaultModelOptions)
  const [fallbackModel, setFallbackModel] = useState('')


  // 載入當前設定
  useEffect(() => {
    loadCurrentSettings()
    loadJsonSchemaParametersInfo()
    loadEnvStatus()
    loadDevModeStatus()
    loadDemoModeSettings()
  }, [])

  // 當選擇的模型改變時重新載入參數資訊
  useEffect(() => {
    if (selectedModel) {
      loadModelParametersInfo(selectedModel)
    }
  }, [selectedModel])

  const loadCurrentSettings = async () => {
    try {
      setLoading(true)

      const [modelData, paramsData, jsonSchemaData] = await Promise.all([
        getModelSettings(),
        getLlmParameters(),
        getJsonSchemaParameters(),
      ])

      setCurrentModel(modelData.current_model)
      setSelectedModel(modelData.current_model) // 初始化選擇的模型
      setFallbackModel(modelData.fallback_model) // 備用模型
      if (modelData.available_models && modelData.available_models.length > 0) {
        setAvailableModels(modelData.available_models)
      }
      setLlmParams(paramsData)
      setJsonSchemaParams(jsonSchemaData)

      form.setFieldsValue({
        llm_model: modelData.current_model,
        llm_fallback_model: modelData.fallback_model,
        ...paramsData,
        ...jsonSchemaData
      })
    } catch (error) {
      console.error('載入設定錯誤:', error)
      message.error('載入設定時發生錯誤')
    } finally {
      setLoading(false)
    }
  }

  const loadModelParametersInfo = async (modelName) => {
    try {
      const data = await getModelParametersInfo(modelName)
      setSupportedParams(data.supported_parameters)
      setModelParamsInfo(data)

      // 更新表單的初始值以反映新模型的參數
      // 但保留用戶已修改但尚未保存的設定
      const currentFormValues = form.getFieldsValue()
      const newFormValues = {
        ...data.current_parameters,
        llm_model: currentFormValues.llm_model || selectedModel
      }
      form.setFieldsValue(newFormValues)
    } catch (error) {
      console.error('載入模型參數資訊錯誤:', error)
    }
  }

  const loadJsonSchemaParametersInfo = async () => {
    try {
      const data = await getJsonSchemaParametersInfo()
      setJsonSchemaSupportedParams(data.supported_parameters)
    } catch (error) {
      console.error('載入JSON Schema參數資訊錯誤:', error)
    }
  }

  const loadEnvStatus = async () => {
    try {
      const data = await getEnvStatus()
      setEnvStatus(data)
    } catch (error) {
      console.error('載入環境狀態錯誤:', error)
      message.error('載入環境狀態時發生錯誤')
    }
  }

  const loadDevModeStatus = async () => {
    try {
      const data = await getDevModeStatus()
      setIsDevMode(data.is_dev_mode || false)
    } catch (error) {
      console.error('載入開發模式狀態錯誤:', error)
    }
  }

  const handleToggleDevMode = async () => {
    try {
      setLoading(true)
      const newDevMode = !isDevMode

      await updateDevModeStatus(newDevMode)
      setIsDevMode(newDevMode)
      message.success(`開發模式已${newDevMode ? '開啟' : '關閉'}`)
    } catch (error) {
      console.error('切換開發模式錯誤:', error)
      message.error('切換開發模式時發生錯誤')
    } finally {
      setLoading(false)
    }
  }

  const storeDemoMode = (config) => {
    setDemoMode(config)
    localStorage.setItem('proposal_demo_config', JSON.stringify(config))
    window.dispatchEvent(new CustomEvent('demo-config-updated', { detail: config }))
  }

  const loadDemoModeSettings = async () => {
    try {
      const data = await getDemoModeSettings()
      storeDemoMode(data)
    } catch (error) {
      console.error('載入 Demo 模式設定錯誤:', error)
    }
  }

  const saveDemoMode = async (enabled) => {
    try {
      setLoading(true)
      const saved = await updateDemoModeSettings({ enabled })
      storeDemoMode({
        enabled: saved.enabled,
        mock_proposal: saved.mock_proposal,
        mock_property_prediction: saved.mock_property_prediction,
        mock_generate_new_idea: saved.mock_generate_new_idea,
        mock_experiment_detail: saved.mock_experiment_detail,
      })
      message.success('Demo 模式設定已更新')
    } catch (error) {
      console.error('更新 Demo 模式設定錯誤:', error)
      message.error('更新 Demo 模式設定失敗')
    } finally {
      setLoading(false)
    }
  }


  const handleSaveOpenAIKey = async (values) => {
    try {
      setLoading(true)

      await saveOpenAiApiKey(values.openai_api_key)
      message.success('OpenAI API Key 設定成功')
      apiKeyForm.resetFields()
      window.dispatchEvent(new Event('demo-config-updated'))
      loadEnvStatus() // 重新載入狀態
    } catch (error) {
      console.error('設定 API Key 錯誤:', error)
      message.error(getApiErrorMessage(error, '設定 API Key 時發生錯誤'))
    } finally {
      setLoading(false)
    }
  }

  const handleSaveGoogleKey = async (values) => {
    try {
      setLoading(true)

      await saveGoogleApiKey(values.google_api_key)
      message.success('Google API Key 設定成功')
      googleApiKeyForm.resetFields()
      window.dispatchEvent(new Event('demo-config-updated'))
      loadEnvStatus() // 重新載入狀態
    } catch (error) {
      console.error('設定 API Key 錯誤:', error)
      message.error(getApiErrorMessage(error, '設定 API Key 時發生錯誤'))
    } finally {
      setLoading(false)
    }
  }

  // 處理模型選擇變更
  const handleModelChange = (value) => {
    setSelectedModel(value)
    console.log('模型選擇變更為:', value)
  }

  // 儲存所有設定（模型 + 參數）
  const handleSaveAllSettings = async (values) => {
    try {
      setLoading(true)

      await updateModelSettings(values.llm_model, values.llm_fallback_model)

      // 2. 儲存LLM參數設定
      const paramsToSend = {}
      Object.keys(supportedParams).forEach(key => {
        if (values[key] !== undefined) {
          paramsToSend[key] = values[key]
        }
      })

      await updateLlmParameters(paramsToSend)

      // 3. 儲存JSON Schema參數設定
      if (values.llm_model) {
        const jsonSchemaParamsToSend = {}
        if (values.min_length !== undefined) {
          jsonSchemaParamsToSend.min_length = values.min_length
        }
        if (values.max_length !== undefined) {
          jsonSchemaParamsToSend.max_length = values.max_length
        }

        if (Object.keys(jsonSchemaParamsToSend).length > 0) {
          await updateJsonSchemaParameters(jsonSchemaParamsToSend)
        }
      }

      message.success('所有設定已成功儲存')
      setCurrentModel(values.llm_model)

      // 重新載入設定以確保同步
      await loadCurrentSettings()
    } catch (error) {
      console.error('儲存設定錯誤:', error)
      message.error(getApiErrorMessage(error, '儲存設定時發生錯誤'))
    } finally {
      setLoading(false)
    }
  }

  // 重置為預設設定
  const handleResetToDefault = async () => {
    try {
      setLoading(true)

      // 設定預設值：gpt-5-mini 與預設設定
      const defaultSettings = {
        llm_model: 'gpt-5-mini',
        max_tokens: 4000,
        timeout: 120,
        reasoning_effort: 'medium',
        verbosity: 'medium'
      }

      await updateModelSettings(defaultSettings.llm_model)
      await updateLlmParameters({
        max_tokens: defaultSettings.max_tokens,
        timeout: defaultSettings.timeout,
        reasoning_effort: defaultSettings.reasoning_effort,
        verbosity: defaultSettings.verbosity
      })

      message.success('已重置為預設設定 (GPT-5 Mini)')

      // 更新本地狀態
      setCurrentModel(defaultSettings.llm_model)
      setSelectedModel(defaultSettings.llm_model)
      setLlmParams({
        max_tokens: defaultSettings.max_tokens,
        timeout: defaultSettings.timeout,
        reasoning_effort: defaultSettings.reasoning_effort,
        verbosity: defaultSettings.verbosity
      })

      // 更新表單
      form.setFieldsValue({
        llm_model: defaultSettings.llm_model,
        max_tokens: defaultSettings.max_tokens,
        timeout: defaultSettings.timeout,
        reasoning_effort: defaultSettings.reasoning_effort,
        verbosity: defaultSettings.verbosity
      })

      // 重新載入參數資訊
      await loadModelParametersInfo(defaultSettings.llm_model)
    } catch (error) {
      console.error('重置設定錯誤:', error)
      message.error(getApiErrorMessage(error, '重置設定時發生錯誤'))
    } finally {
      setLoading(false)
    }
  }

  // 渲染參數控制項
  const renderParameterControl = (paramName, paramConfig) => {
    const currentValue = llmParams[paramName] || paramConfig.default

    switch (paramConfig.type) {
      case 'float':
        return (
          <Slider
            min={paramConfig.range[0]}
            max={paramConfig.range[1]}
            step={0.1}
            marks={{
              [paramConfig.range[0]]: paramConfig.range[0].toString(),
              [(paramConfig.range[0] + paramConfig.range[1]) / 2]: ((paramConfig.range[0] + paramConfig.range[1]) / 2).toFixed(1),
              [paramConfig.range[1]]: paramConfig.range[1].toString()
            }}
            tooltip={{
              formatter: (value) => `${value}`,
            }}
          />
        )

      case 'int':
        return (
          <InputNumber
            min={paramConfig.range[0]}
            max={paramConfig.range[1]}
            style={{ width: '100%' }}
            placeholder={`設定${paramName}`}
          />
        )

      case 'select':
        return (
          <Select
            placeholder={`選擇${paramName}`}
            style={{ width: '100%' }}
          >
            {paramConfig.options.map(option => (
              <Option key={option} value={option}>
                {option}
              </Option>
            ))}
          </Select>
        )

      default:
        return null
    }
  }

  // 渲染參數說明
  const renderParameterDescription = (paramName, paramConfig) => {
    const descriptions = {
      max_tokens: {
        low: "較小值: 回應更簡潔，成本更低",
        medium: "較大值: 回應更詳細，但成本更高",
        suggestion: "建議: 根據需求調整，一般2000-8000較合適"
      },
      timeout: {
        low: "較小值: 響應更快，但可能超時",
        medium: "較大值: 更穩定，但等待時間長",
        suggestion: "建議: 一般60-180秒較合適"
      },
      reasoning_effort: {
        minimal: "minimal: 最低推理成本，適合簡單任務",
        low: "low: 較低推理成本，適合一般任務",
        medium: "medium: 平衡推理能力和成本",
        high: "high: 最高推理能力，適合複雜任務"
      },
      verbosity: {
        low: "low: 簡潔輸出，適合快速回應",
        medium: "medium: 平衡詳盡度",
        high: "high: 詳細輸出，適合需要解釋的任務"
      },
      min_length: {
        low: "較小值 (1-10): 適合標題、簡短描述",
        medium: "中等值 (10-30): 適合一般內容",
        high: "較大值 (30-50): 適合詳細描述"
      },
      max_length: {
        low: "較小限制 (10-500): 強制簡潔輸出",
        medium: "中等限制 (500-1500): 平衡長度控制",
        high: "較大限制 (1500-5000): 允許詳細輸出"
      }
    }

    const desc = descriptions[paramName]
    if (!desc) return null

    return (
      <div style={{
        background: '#f6f8fa',
        padding: '12px',
        borderRadius: '6px',
        fontSize: '12px',
        lineHeight: '1.4'
      }}>
        {Object.entries(desc).map(([key, text]) => (
          <div key={key}>
            <Text strong>{text.split(':')[0]}:</Text> {text.split(':')[1]}
          </div>
        ))}
      </div>
    )
  }

  return (
    <div style={{ maxWidth: 1000, margin: '0 auto' }}>
      <Title level={2}>
        <SettingOutlined style={{ marginRight: 8 }} />
        系統設定
      </Title>

      {/* 語言模型設定 */}
      <Card style={{ marginBottom: 16 }}>
        <Title level={4}>語言模型設定</Title>
        <Text type="secondary">
          選擇用於整個系統的語言模型。不同的模型在性能和成本上有所差異。
        </Text>

        <Divider />

        <Form
          form={form}
          layout="vertical"
          onFinish={handleSaveAllSettings}
          initialValues={{
            llm_model: currentModel,
            llm_fallback_model: fallbackModel
          }}
        >
          <Form.Item
            label="主 LLM 模型"
            name="llm_model"
            rules={[
              {
                required: true,
                message: '請選擇主語言模型',
              },
            ]}
          >
            <Select
              placeholder="選擇主語言模型"
              style={{ width: '100%' }}
              loading={loading}
              optionLabelProp="label"
              onChange={handleModelChange}
            >
              {availableModels.map((option) => (
                <Option
                  key={option.value}
                  value={option.value}
                  label={option.label}
                >
                  <div style={{ padding: '4px 0' }}>
                    <div style={{
                      fontWeight: 'bold',
                      fontSize: '14px',
                      lineHeight: '1.4',
                      marginBottom: '4px'
                    }}>
                      {option.label}
                    </div>
                    <div style={{
                      fontSize: '12px',
                      color: '#666',
                      lineHeight: '1.3'
                    }}>
                      {option.description}
                    </div>
                  </div>
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            label="備用降級 LLM 模型 (Fallback Model)"
            name="llm_fallback_model"
            tooltip="當主模型調用失敗或發生異常時，系統會自動降級至此備用模型以確保服務可用性"
            rules={[
              {
                required: true,
                message: '請選擇備用語言模型',
              },
            ]}
          >
            <Select
              placeholder="選擇備用語言模型"
              style={{ width: '100%' }}
              loading={loading}
              optionLabelProp="label"
            >
              {availableModels.map((option) => (
                <Option
                  key={option.value}
                  value={option.value}
                  label={option.label}
                >
                  <div style={{ padding: '4px 0' }}>
                    <div style={{
                      fontWeight: 'bold',
                      fontSize: '14px',
                      lineHeight: '1.4',
                      marginBottom: '4px'
                    }}>
                      {option.label}
                    </div>
                    <div style={{
                      fontSize: '12px',
                      color: '#666',
                      lineHeight: '1.3'
                    }}>
                      {option.description}
                    </div>
                  </div>
                </Option>
              ))}
            </Select>
          </Form.Item>


          {selectedModel && (
            <div style={{
              background: '#f6f8fa',
              padding: '12px',
              borderRadius: '6px',
              marginBottom: '16px'
            }}>
              <Text strong>目前選擇的模型：</Text> {selectedModel}
              {selectedModel !== currentModel && (
                <div style={{ marginTop: '4px' }}>
                  <Text type="warning">⚠️ 模型已變更，請儲存設定以套用變更</Text>
                </div>
              )}
            </div>
          )}

          <Form.Item>
            <Space>
              <Button
                type="primary"
                htmlType="submit"
                loading={loading}
                icon={<SaveOutlined />}
              >
                儲存所有設定
              </Button>
              <Button
                onClick={handleResetToDefault}
                disabled={loading}
                icon={<ReloadOutlined />}
              >
                重置為預設 (GPT-5 Mini)
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>

      {/* API 金鑰設定 */}
      <Card style={{ marginBottom: 16 }}>
        <Title level={4}>
          <KeyOutlined style={{ marginRight: 8 }} />
          API 金鑰設定
        </Title>
        <Text type="secondary">
          配置 OpenAI API Key 以啟用 AI 功能。系統會自動驗證 API Key 的有效性。
        </Text>

        <Divider />

        {/* 環境狀態顯示 */}
        <Alert
          message="環境狀態"
          description={
            <div>
              <p><strong>.env 檔案：</strong> {envStatus.exists ? '✅ 已存在' : '❌ 不存在'}</p>
              <p><strong>OpenAI API Key：</strong> {envStatus.openai_key_configured ? '✅ 已配置' : '❌ 未配置'}</p>
              <p><strong>Google API Key：</strong> {envStatus.google_key_configured ? '✅ 已配置' : '❌ 未配置'}</p>
            </div>
          }
          type={envStatus.openai_key_configured && envStatus.google_key_configured ? "success" : "warning"}
          showIcon
          style={{ marginBottom: 16 }}
        />

        {/* API Key 設定表單 */}
        <Form
          form={apiKeyForm}
          layout="vertical"
          onFinish={handleSaveOpenAIKey}
        >
          <Form.Item
            label="OpenAI API Key"
            name="openai_api_key"
            rules={[
              {
                required: true,
                message: '請輸入 OpenAI API Key',
              },
            ]}
          >
            <Password
              placeholder="sk-..."
              style={{ width: '100%' }}
            />
          </Form.Item>

          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              loading={loading}
              icon={<SaveOutlined />}
            >
              驗證並儲存 OpenAI API Key
            </Button>
          </Form.Item>
        </Form>

        <Divider />

        <Form
          form={googleApiKeyForm}
          layout="vertical"
          onFinish={handleSaveGoogleKey}
        >
          <Form.Item
            label="Google API Key (Gemini)"
            name="google_api_key"
            rules={[
              {
                required: true,
                message: '請輸入 Google API Key',
              },
            ]}
          >
            <Password
              placeholder="AIza..."
              style={{ width: '100%' }}
            />
          </Form.Item>

          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              loading={loading}
              icon={<SaveOutlined />}
            >
              驗證並儲存 Google API Key
            </Button>
          </Form.Item>
        </Form>
      </Card>

      {/* LLM參數設定 */}
      {selectedModel && Object.keys(supportedParams).length > 0 && (
        <Card>
          <Title level={4}>LLM 參數設定</Title>
          <Text type="secondary">
            調整語言模型的生成參數，影響回應的長度和響應時間。
            GPT-5系列支援推理控制和輸出詳盡度參數。
          </Text>

          <Divider />

          <Form
            form={form}
            layout="vertical"
            onFinish={handleSaveAllSettings}
          >
            {Object.entries(supportedParams).map(([paramName, paramConfig]) => (
              <Row gutter={24} key={paramName} style={{ marginBottom: 24 }}>
                <Col span={12}>
                  <Form.Item
                    label={
                      <Space>
                        <Text>{paramName.charAt(0).toUpperCase() + paramName.slice(1)}</Text>
                        {paramConfig.type === 'float' && (
                          <Text type="secondary" style={{ fontSize: '12px' }}>
                            ({paramConfig.range[0]} - {paramConfig.range[1]})
                          </Text>
                        )}
                        {paramConfig.type === 'int' && (
                          <Text type="secondary" style={{ fontSize: '12px' }}>
                            ({paramConfig.range[0]} - {paramConfig.range[1]})
                          </Text>
                        )}
                        {paramConfig.type === 'select' && (
                          <Text type="secondary" style={{ fontSize: '12px' }}>
                            ({paramConfig.options.join(', ')})
                          </Text>
                        )}
                      </Space>
                    }
                    name={paramName}
                    rules={[
                      {
                        required: true,
                        message: `請設定${paramName}值`,
                      },
                    ]}
                  >
                    {renderParameterControl(paramName, paramConfig)}
                  </Form.Item>
                </Col>

                <Col span={12}>
                  <Form.Item
                    label={`${paramName.charAt(0).toUpperCase() + paramName.slice(1)} 說明`}
                    style={{ marginBottom: 0 }}
                  >
                    {renderParameterDescription(paramName, paramConfig)}
                  </Form.Item>
                </Col>
              </Row>
            ))}
          </Form>
        </Card>
      )}

      {/* JSON Schema 參數設定 */}
      {selectedModel && Object.keys(jsonSchemaSupportedParams).length > 0 && (
        <Card style={{ marginTop: 16 }}>
          <Title level={4}>JSON Schema 參數設定</Title>
          <Text type="secondary">
            設定結構化輸出的欄位約束，控制生成內容的長度和格式要求。
            這些參數主要用於研究提案生成等結構化輸出任務。
          </Text>

          <Divider />

          <Form
            form={form}
            layout="vertical"
            onFinish={handleSaveAllSettings}
          >
            {Object.entries(jsonSchemaSupportedParams).map(([paramName, paramConfig]) => (
              <Row gutter={24} key={paramName} style={{ marginBottom: 24 }}>
                <Col span={12}>
                  <Form.Item
                    label={
                      <Space>
                        <Text>{paramName === 'min_length' ? '最小長度 (minLength)' : '最大長度 (maxLength)'}</Text>
                        {paramConfig.type === 'int' && (
                          <Text type="secondary" style={{ fontSize: '12px' }}>
                            ({paramConfig.range[0]} - {paramConfig.range[1]})
                          </Text>
                        )}
                      </Space>
                    }
                    name={paramName}
                    rules={[
                      {
                        required: true,
                        message: `請設定${paramName === 'min_length' ? '最小長度' : '最大長度'}值`,
                      },
                    ]}
                  >
                    <InputNumber
                      min={paramConfig.range[0]}
                      max={paramConfig.range[1]}
                      style={{ width: '100%' }}
                      placeholder={`設定${paramName === 'min_length' ? '最小長度' : '最大長度'}`}
                    />
                  </Form.Item>
                </Col>

                <Col span={12}>
                  <Form.Item
                    label={`${paramName === 'min_length' ? '最小長度' : '最大長度'}說明`}
                    style={{ marginBottom: 0 }}
                  >
                    {renderParameterDescription(paramName, paramConfig)}
                  </Form.Item>
                </Col>
              </Row>
            ))}

            <Form.Item>
              <Alert
                message="JSON Schema 參數說明"
                description="這些參數會影響結構化輸出的文字數上限，不會影響LLM輸出量，若過低會有截斷的現象，建議維持>3000字以上。若要調整輸出量，請調整verbosity。"
                type="info"
                showIcon
                icon={<InfoCircleOutlined />}
              />
            </Form.Item>
          </Form>
        </Card>
      )}

      {/* 開發模式設定 */}
      <Card style={{ marginTop: 16 }}>
        <Title level={4}>開發模式設定</Title>
        <Text type="secondary">
          開發模式用於快速測試和調試，會影響系統的檢索行為和響應速度。
        </Text>

        <Divider />

        <Row gutter={24} style={{ marginBottom: 24 }}>
          <Col span={12}>
            <Form.Item label="開發模式">
              <Button
                type={isDevMode ? "primary" : "default"}
                onClick={handleToggleDevMode}
                loading={loading}
                style={{ width: 200 }}
              >
                {isDevMode ? "🔧 Dev Mode ON" : "🔧 Dev Mode OFF"}
              </Button>
            </Form.Item>
          </Col>

          <Col span={12}>
            <Form.Item label="開發模式說明" style={{ marginBottom: 0 }}>
              <div>
                <p><strong>開發模式功能：</strong></p>
                <ul>
                  <li><strong>快速檢索：</strong> 修訂提案時每個查詢只檢索1個chunk（正常模式為3個）</li>
                  <li><strong>快速測試：</strong> 減少API調用次數，加快響應速度</li>
                  <li><strong>調試友好：</strong> 便於開發和測試新功能</li>
                </ul>
                <p><strong>注意：</strong> 開發模式會影響檢索的完整性和準確性，僅建議在開發和測試時使用。</p>
              </div>
            </Form.Item>
          </Col>
        </Row>

        <Divider />

        <Title level={5}>Demo 模式</Title>
        <Text type="secondary">
          開啟後所有 Demo 功能會使用固定資料，不呼叫 LLM、PubChem、PORMAKE 或 predictor。
        </Text>

        <div style={{ marginTop: 16 }}>
          <Space align="center">
            <Text>Demo 模式</Text>
            <Switch
              checked={demoMode.enabled}
              onChange={saveDemoMode}
              loading={loading}
              checkedChildren="ON"
              unCheckedChildren="OFF"
            />
          </Space>
        </div>
      </Card>

      {/* 模型特性說明 */}
      {selectedModel && (
        <Card style={{ marginTop: 16 }}>
          <Title level={4}>模型特性說明</Title>
          <Alert
            message="模型特性"
            description={
              <div>
                <p><strong>GPT-5系列特性：</strong></p>
                <ul>
                  <li><strong>推理控制 (reasoning.effort)：</strong> 控制模型的推理密度和成本</li>
                  <li><strong>輸出詳盡度 (verbosity)：</strong> 控制回應的詳細程度</li>
                  <li><strong>工具鏈支援：</strong> 支援function calling和工具使用</li>
                  <li><strong>結構化輸出：</strong> 支援JSON等格式的強制輸出</li>
                  <li><strong>JSON Schema 驗證：</strong> 支援欄位長度和格式約束</li>
                </ul>
                <Divider style={{ margin: '12px 0' }} />
                <p><strong>Gemini系列特性：</strong></p>
                <ul>
                  <li><strong>強大多模態能力：</strong> 擅長處理文本、圖像和化學結構分析</li>
                  <li><strong>超長上下文窗口：</strong> 適合一次性處理海量學術論文數據</li>
                  <li><strong>結構化輸出支援：</strong> 支援 Pydantic 模式的 JSON 生成</li>
                  <li><strong>高性價比：</strong> Flash 系列模型在保持性能的同時顯著降低成本</li>
                </ul>
              </div>
            }
            type="info"
            showIcon
            icon={<InfoCircleOutlined />}
          />
        </Card>
      )}
    </div>
  )
}

export default Settings

import React, { useMemo } from 'react'
import { Card, Col, Row, Segmented, Select, Slider, Switch, Typography, Upload, Alert, Space, Statistic, Tag, Button } from 'antd'
import { InboxOutlined, ReloadOutlined } from '@ant-design/icons'
import CifChargeViewer from './CifChargeViewer'
import { parseCifCharges, summarizeCharges } from '../../utils/mof/cifChargeParser'

const { Dragger } = Upload
const { Text } = Typography

const STYLE_OPTIONS = [
  { label: '棒狀', value: 'stick' },
  { label: '球棒', value: 'ball-stick' },
  { label: '比例', value: 'space-filling' },
]

const SURFACE_TYPE_OPTIONS = [
  { label: '電子雲密度 VDW', value: 'VDW' },
  { label: '溶劑可及表面 SAS', value: 'SAS' },
  { label: '溶劑排除表面 SES', value: 'SES' },
]

const CifViewerTab = ({
  fileName,
  cifText,
  parseResult,
  styleMode,
  setStyleMode,
  showSurface,
  setShowSurface,
  surfaceType,
  setSurfaceType,
  surfaceOpacity,
  setSurfaceOpacity,
  uploadError,
  setUploadError,
  onUploadCif,
  onReset,
}) => {
  const chargeSummary = useMemo(() => {
    return summarizeCharges(parseResult.charges, parseResult.atomLabels)
  }, [parseResult])

  const hasRenderableCif = cifText?.trim().length > 0
  const hasCompleteCharges = parseResult?.charges?.length > 0

  const uploadProps = {
    accept: '.cif',
    multiple: false,
    showUploadList: false,
    beforeUpload: async (file) => {
      setUploadError('')
      if (!file.name.toLowerCase().endsWith('.cif')) {
        setUploadError('請選擇 .cif 檔案。')
        return Upload.LIST_IGNORE
      }
      try {
        const text = await file.text()
        const parsed = parseCifCharges(text)
        onUploadCif(file.name, text, parsed)
      } catch (error) {
        setUploadError(error?.message || 'CIF 檔案讀取失敗。')
      }
      return false
    },
  }

  return (
    <Row gutter={[16, 16]} className="mof-workspace">
      <Col xs={24} lg={7}>
        <Card title="匯入 CIF" size="small" extra={hasRenderableCif && (
          <Button size="small" icon={<ReloadOutlined />} onClick={onReset}>
            清除
          </Button>
        )}>
          <Dragger {...uploadProps}>
            <p className="ant-upload-drag-icon">
              <InboxOutlined />
            </p>
            <p className="ant-upload-text">拖曳或點擊選擇 CIF 檔案</p>
            <p className="ant-upload-hint">支援一般 CIF 與含 PACMAN charge 欄位的 CIF。</p>
          </Dragger>

          {uploadError && (
            <Alert className="mof-panel-gap" type="error" message={uploadError} showIcon />
          )}

          <Space className="mof-panel-gap" direction="vertical" size={8}>
            <Text type="secondary">目前檔案</Text>
            {fileName ? <Tag color="blue">{fileName}</Tag> : <Tag>尚未載入</Tag>}
            {hasRenderableCif && (
              <Tag color={hasCompleteCharges ? 'purple' : 'default'}>
                {hasCompleteCharges
                  ? `偵測到 ${parseResult.charges.length} 筆電荷`
                  : '未偵測到電荷欄位'}
              </Tag>
            )}
          </Space>
        </Card>

        <Card className="mof-panel-gap" title="顯示顯示模式" size="small">
          <Segmented block options={STYLE_OPTIONS} value={styleMode} onChange={setStyleMode} />
        </Card>

        <Card className="mof-panel-gap" title="電子雲" size="small">
          {hasCompleteCharges ? (
            <Space direction="vertical" size={12} className="mof-control-stack">
              <div className="mof-control-row">
                <Text>顯示電子雲</Text>
                <Switch checked={showSurface} onChange={setShowSurface} />
              </div>
              <div>
                <Text type="secondary">表面模型</Text>
                <Select
                  className="mof-full-width-control"
                  options={SURFACE_TYPE_OPTIONS}
                  value={surfaceType}
                  onChange={setSurfaceType}
                  disabled={!showSurface}
                />
              </div>
              <div>
                <Text type="secondary">透明度 {surfaceOpacity.toFixed(1)}</Text>
                <Slider
                  min={0.1}
                  max={0.9}
                  step={0.1}
                  value={surfaceOpacity}
                  onChange={setSurfaceOpacity}
                  disabled={!showSurface}
                />
              </div>
            </Space>
          ) : (
            <Text type="secondary">載入含電荷欄位的 CIF 後可顯示電子雲。</Text>
          )}
        </Card>

        <Card className="mof-panel-gap" title="電荷統計" size="small">
          {hasCompleteCharges ? (
            <Row gutter={[12, 12]}>
              <Col span={12}>
                <Statistic title="Atoms" value={chargeSummary.atomsCount} />
              </Col>
              <Col span={12}>
                <Statistic title="Net Charge" value={chargeSummary.sumCharge} precision={4} suffix="e" />
              </Col>
              <Col span={12}>
                <Statistic title="Max +" value={chargeSummary.maxCharge} precision={4} suffix="e" />
                <div style={{ wordBreak: 'break-all', fontSize: '12px', color: 'rgba(0,0,0,0.45)' }}>{chargeSummary.maxPosLabel}</div>
              </Col>
              <Col span={12}>
                <Statistic title="Max -" value={chargeSummary.minCharge} precision={4} suffix="e" />
                <div style={{ wordBreak: 'break-all', fontSize: '12px', color: 'rgba(0,0,0,0.45)' }}>{chargeSummary.maxNegLabel}</div>
              </Col>
            </Row>
          ) : (
            <Text type="secondary">載入含電荷欄位的 CIF 後會顯示統計。</Text>
          )}
        </Card>
      </Col>

      <Col xs={24} lg={17}>
        <Card
          size="small"
          title="CIF 3D Viewer"
          extra={hasCompleteCharges ? <Tag color="purple">Charge coloring</Tag> : <Tag>CPK coloring</Tag>}
        >
          {hasRenderableCif ? (
            <CifChargeViewer
              cifText={cifText}
              charges={parseResult.charges}
              atomLabels={parseResult.atomLabels}
              styleMode={styleMode}
              showSurface={showSurface}
              surfaceType={surfaceType}
              surfaceOpacity={surfaceOpacity}
            />
          ) : (
            <div className="mof-empty-viewer">
              <Text type="secondary">請先匯入 CIF 檔案。</Text>
            </div>
          )}
        </Card>
      </Col>
    </Row>
  )
}

export default CifViewerTab

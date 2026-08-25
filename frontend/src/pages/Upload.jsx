import { DatabaseOutlined, FileTextOutlined, InboxOutlined, UploadOutlined } from '@ant-design/icons';
import { Alert, Button, Card, Col, List, message, Progress, Row, Space, Statistic, Tag, Typography, Upload } from 'antd';
import React, { useEffect, useRef, useState } from 'react';
import { getUploadStats, getUploadStatus, refreshUploadStats, uploadFiles } from '../services/uploadApi';

const { Title, Paragraph } = Typography;
const { Dragger } = Upload;

const getUploadSummary = (results) => {
  if (!results) {
    return null;
  }

  if (results.summary) {
    return results.summary;
  }

  const paperFiles = results.file_info?.papers?.length || 0;
  const paperFilesProcessed = Array.isArray(results.paper_results) ? results.paper_results.length : 0;
  const experimentFiles = results.file_info?.experiments?.length || 0;
  const experimentFilesEmbedded = Array.isArray(results.experiment_results)
    ? results.experiment_results.reduce((acc, item) => acc + (item.embedded_count || 0), 0)
    : 0;
  const otherFiles = results.file_info?.others?.length || 0;
  const paperFilesSkipped = Math.max(paperFiles - paperFilesProcessed, 0);

  return {
    paper_files: paperFiles,
    paper_files_processed: paperFilesProcessed,
    paper_files_skipped: paperFilesSkipped,
    experiment_files: experimentFiles,
    experiment_files_embedded: experimentFilesEmbedded,
    experiment_files_failed: 0,
    other_files: otherFiles,
    total_files: paperFiles + experimentFiles + otherFiles,
    total_files_with_no_new_vectors: paperFilesSkipped + otherFiles,
  };
};

const UploadPage = () => {
  const [fileList, setFileList] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [taskId, setTaskId] = useState(null);
  const [serverMessage, setServerMessage] = useState('');
  const [results, setResults] = useState(null);
  const [vectorStats, setVectorStats] = useState({ paper_vectors: 0, experiment_vectors: 0, total_vectors: 0 });
  const pollingRef = useRef(null);

  // 獲取向量統計信息
  const fetchVectorStats = async () => {
    try {
      console.log('📊 開始獲取向量統計信息...');
      const data = await getUploadStats();
      console.log('📊 向量統計響應:', data);
      setVectorStats(data);
    } catch (error) {
      console.error('❌ 獲取向量統計失敗:', error);
      // 如果是網絡錯誤，設置默認值
      if (error.code === 'ECONNREFUSED' || error.code === 'ERR_NETWORK') {
        console.log('⚠️ 後端不可用，使用默認統計');
        setVectorStats({ paper_vectors: 0, experiment_vectors: 0, total_vectors: 0 });
      }
    }
  };

  // 刷新向量統計信息（重新計算）
  const refreshVectorStats = async () => {
    try {
      console.log('🔄 開始刷新向量統計信息...');
      const data = await refreshUploadStats();
      console.log('🔄 向量統計刷新響應:', data);
      setVectorStats(data);
    } catch (error) {
      console.error('❌ 刷新向量統計失敗:', error);
      // 如果刷新失敗，嘗試獲取緩存數據
      fetchVectorStats();
    }
  };

  // 頁面加載時獲取統計信息（現在使用後端緩存，響應更快）
  useEffect(() => {
    fetchVectorStats();
  }, []);

  const handleUpload = async () => {
    if (fileList.length === 0) {
      message.warning('Please select files to upload');
      return;
    }

    console.log('🚀 開始檔案上傳流程...');
    console.log('📁 選中的檔案:', fileList.map(f => f.name));

    setUploading(true);
    setUploadProgress(0);
    setServerMessage('');
    setResults(null);

    try {
      fileList.forEach((file) => {
        console.log('📄 準備上傳檔案:', file.name, '大小:', file.size);
      });

      console.log('📤 開始上傳檔案到後端...');
      const uploadResponse = await uploadFiles(fileList);

      console.log('✅ 檔案上傳成功，響應:', uploadResponse);
      const { file_info } = uploadResponse;
      const newTaskId = file_info?.task_id;
      console.log('🆔 任務ID:', newTaskId);
      setTaskId(newTaskId);
      message.success('Upload started. Processing on server...');

      // 開始輪詢任務狀態
      const poll = async () => {
        try {
          console.log('🔄 開始輪詢任務狀態:', newTaskId);
          const statusData = await getUploadStatus(newTaskId);
          const { status, progress, message: msg, results: r } = statusData;

          console.log('📊 後端狀態響應:', {
            status,
            progress,
            message: msg,
            hasResults: !!r
          });

          // 直接同步後端進度：後端進度就是前端進度
          // 處理progress可能為null或undefined的情況
          const safeProgress = progress !== null && progress !== undefined ? progress : 0;
          // 直接使用後端進度，不再轉換
          const backendProgress = safeProgress;
          console.log('📈 進度同步:', {
            後端進度: progress,
            安全進度: safeProgress,
            前端進度: backendProgress,
            說明: '直接同步後端進度'
          });

          // 確保進度不會倒退，只會向前更新
          setUploadProgress(prevProgress => {
            const newProgress = Math.max(prevProgress, backendProgress);
            if (newProgress !== prevProgress) {
              console.log(`📈 進度更新: ${prevProgress}% → ${newProgress}%`);
            }
            return newProgress;
          });
          setServerMessage(msg || '');

          if (status === 'completed') {
            console.log('✅ 任務完成，結果:', r);
            setResults(r || {});
            setUploading(false);
            setFileList([]);
            setTaskId(null);
            setUploadProgress(100);
            pollingRef.current && clearTimeout(pollingRef.current);
            const summary = getUploadSummary(r);
            if (summary?.total_files_with_no_new_vectors > 0) {
              message.warning('Processing completed, but some files did not add new vectors.');
            } else {
              message.success('Processing completed.');
            }
            // 更新統計信息
            fetchVectorStats();
            return;
          }
          if (status === 'failed' || status === 'cancelled') {
            console.log('❌ 任務失敗或取消:', status, msg);
            setUploading(false);
            setTaskId(null);
            pollingRef.current && clearTimeout(pollingRef.current);
            message.error(msg || 'Processing failed');
            return;
          }

          console.log('⏳ 任務進行中，繼續輪詢...');
          // 繼續輪詢，縮短輪詢間隔以更頻繁地更新進度
          pollingRef.current = setTimeout(poll, 500);
        } catch (e) {
          console.error('❌ 輪詢狀態失敗:', e);
          pollingRef.current && clearTimeout(pollingRef.current);
          setUploading(false);
          setTaskId(null);
          message.error('Failed to get processing status');
        }
      };
      poll();

    } catch (error) {
      console.error('❌ 檔案上傳失敗:', error);
      message.error('Upload failed');
      setUploading(false);
      setUploadProgress(0);
    }
  };

  const uploadProps = {
    name: 'file',
    multiple: true,
    fileList: fileList,
    beforeUpload: (file) => {
      // Check file type
      const isAccepted = file.type === 'application/pdf' ||
        file.type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' ||
        file.type === 'application/vnd.ms-excel' ||
        file.type === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' ||
        file.type === 'text/plain';

      if (!isAccepted) {
        message.error('You can only upload PDF, Word, Excel, or text files!');
        return false;
      }

      // File size check removed - no limit

      setFileList(prev => [...prev, file]);
      return false; // Prevent default upload behavior
    },
    onRemove: (file) => {
      setFileList(prev => prev.filter(item => item.uid !== file.uid));
    },
  };

  const getFileIcon = (file) => {
    if (file.type === 'application/pdf') {
      return <FileTextOutlined style={{ color: '#ff4d4f' }} />;
    } else if (file.type.includes('word')) {
      return <FileTextOutlined style={{ color: '#1890ff' }} />;
    } else if (file.type.includes('excel')) {
      return <FileTextOutlined style={{ color: '#52c41a' }} />;
    } else {
      return <FileTextOutlined style={{ color: '#faad14' }} />;
    }
  };

  return (
    <div>
      <Title level={2}>檔案上傳</Title>
      <Paragraph>
        上傳學術論文、研究報告與實驗數據檔案，以進行語意分析與向量化資料庫建立。
      </Paragraph>

      {/* 向量數據庫統計信息 */}
      <Card
        title="向量資料庫統計資訊"
        style={{ marginBottom: 24 }}
        extra={
          <Button
            type="primary"
            size="small"
            onClick={refreshVectorStats}
            icon={<DatabaseOutlined />}
          >
            刷新數據
          </Button>
        }
      >
        <Row gutter={16}>
          <Col span={8}>
            <Statistic
              title="總向量數據區塊"
              value={vectorStats.total_vectors}
              prefix={<DatabaseOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Col>
          <Col span={8}>
            <Statistic
              title="學術文獻向量數"
              value={vectorStats.paper_vectors}
              prefix={<FileTextOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Col>
          <Col span={8}>
            <Statistic
              title="實驗數據向量數"
              value={vectorStats.experiment_vectors}
              prefix={<DatabaseOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Col>
        </Row>
      </Card>

      <Card title="上傳學術或實驗檔案" style={{ marginBottom: 24 }}>
        <Dragger {...uploadProps} disabled={uploading}>
          <p className="ant-upload-drag-icon">
            <InboxOutlined />
          </p>
          <p className="ant-upload-text">點擊或拖曳檔案至此區域以進行上傳</p>
          <p className="ant-upload-hint">
            支援 PDF、Word (.docx)、Excel (.xlsx) 及 TXT 檔案，單一檔案無容量上限。
          </p>
        </Dragger>

        {fileList.length > 0 && (
          <div style={{ marginTop: 16 }}>
            <List
              size="small"
              dataSource={fileList}
              renderItem={(file) => (
                <List.Item>
                  <List.Item.Meta
                    avatar={getFileIcon(file)}
                    title={file.name}
                    description={`${(file.size / 1024 / 1024).toFixed(2)} MB`}
                  />
                </List.Item>
              )}
            />
          </div>
        )}

        {uploading && (
          <div style={{ marginTop: 16 }}>
            <Progress
              percent={uploadProgress}
              status="active"
              strokeColor={{
                '0%': '#108ee9',
                '100%': '#87d068',
              }}
              format={(percent) => `${percent}%`}
            />
            {serverMessage && (
              <div style={{ marginTop: 8 }}>
                <Paragraph style={{ margin: 0, color: '#1890ff' }}>
                  {serverMessage}
                </Paragraph>
                {/* 根據進度顯示處理階段 */}
                <div style={{ marginTop: 4 }}>
                  {uploadProgress >= 0 && uploadProgress < 25 && (
                    <Tag color="blue">🔍 檔案分析階段</Tag>
                  )}
                  {uploadProgress >= 25 && uploadProgress < 50 && (
                    <Tag color="orange">📄 元數據提取階段</Tag>
                  )}
                  {uploadProgress >= 50 && uploadProgress < 95 && (
                    <Tag color="green">🔢 向量嵌入階段</Tag>
                  )}
                  {uploadProgress >= 95 && uploadProgress < 98 && (
                    <Tag color="cyan">📊 統計更新階段</Tag>
                  )}
                  {uploadProgress >= 98 && uploadProgress < 100 && (
                    <Tag color="purple">🎯 完成處理階段</Tag>
                  )}
                  {uploadProgress === 100 && (
                    <Tag color="success">✅ 處理完成</Tag>
                  )}
                </div>
                {/* 根據消息內容顯示詳細狀態 */}
                {uploadProgress > 0 && uploadProgress < 100 && (
                  <div style={{ marginTop: 4 }}>
                    {(serverMessage.includes('分析檔案類型') || serverMessage.includes('開始處理論文資料')) && (
                      <Tag color="blue">🔍 檔案分析</Tag>
                    )}
                    {(serverMessage.includes('提取檔案元數據') || serverMessage.includes('提取第') && serverMessage.includes('個檔案元數據')) && (
                      <Tag color="blue">📄 提取檔案元數據</Tag>
                    )}
                    {(serverMessage.includes('檢查') && serverMessage.includes('重複')) && (
                      <Tag color="orange">🔍 檢查檔案重複</Tag>
                    )}
                    {(serverMessage.includes('開始檔案分塊處理') || (serverMessage.includes('處理第') && serverMessage.includes('個檔案：'))) && (
                      <Tag color="cyan">📚 檔案分塊處理</Tag>
                    )}
                    {(serverMessage.includes('開始向量嵌入') || serverMessage.includes('向量嵌入批次')) && (
                      <Tag color="green">🔢 向量嵌入處理</Tag>
                    )}
                    {(serverMessage.includes('處理實驗資料') || serverMessage.includes('處理實驗檔案')) && (
                      <Tag color="purple">🧪 處理實驗數據</Tag>
                    )}
                    {serverMessage.includes('完成處理') && (
                      <Tag color="success">✅ 完成處理</Tag>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        <div style={{ marginTop: 16 }}>
          <Space>
            <Button
              type="primary"
              icon={<UploadOutlined />}
              onClick={handleUpload}
              loading={uploading}
              disabled={fileList.length === 0}
            >
              {uploading ? '上傳處理中...' : '開始上傳檔案'}
            </Button>
            <Button
              onClick={() => setFileList([])}
              disabled={fileList.length === 0 || uploading}
            >
              清除全部
            </Button>
          </Space>
        </div>
      </Card>

      {results && (
        <Card title="處理結果與統計" style={{ marginBottom: 24 }}>
          {getUploadSummary(results)?.total_files_with_no_new_vectors > 0 && (
            <Alert
              type="warning"
              showIcon
              style={{ marginBottom: 16 }}
              message="處理已完成，但並非所有檔案皆新增了向量區塊。"
              description="略過的檔案通常為重複檔案、不受支援格式、或無法正常解析的檔案。重複的檔案不會重新計算向量庫。"
            />
          )}
          <Paragraph>向量嵌入已完成，處理摘要：</Paragraph>
          <ul>
            {results.file_info && (
              <li>
                檔案分類：
                <Space size="small" style={{ marginLeft: 8 }}>
                  <Tag color="blue">學術文獻 (papers): {results.file_info.papers?.length || 0}</Tag>
                  <Tag color="green">實驗報告 (experiments): {results.file_info.experiments?.length || 0}</Tag>
                  {results.file_info.others && results.file_info.others.length > 0 && (
                    <Tag>其他 (others): {results.file_info.others.length}</Tag>
                  )}
                </Space>
              </li>
            )}
            {getUploadSummary(results) && (
              <li>
                學術論文檔案：
                <Space size="small" style={{ marginLeft: 8 }}>
                  <Tag color="blue">分類歸屬 (classified): {getUploadSummary(results).paper_files}</Tag>
                  <Tag color="green">已處理數 (processed): {getUploadSummary(results).paper_files_processed}</Tag>
                  {getUploadSummary(results).paper_files_skipped > 0 && (
                    <Tag color="warning">略過數 (skipped): {getUploadSummary(results).paper_files_skipped}</Tag>
                  )}
                </Space>
              </li>
            )}
            {getUploadSummary(results) && (
              <li>
                實驗報告檔案：
                <Space size="small" style={{ marginLeft: 8 }}>
                  <Tag color="blue">分類歸屬 (classified): {getUploadSummary(results).experiment_files}</Tag>
                  <Tag color="green">已處理數 (processed): {getUploadSummary(results).experiment_files_embedded}</Tag>
                  {getUploadSummary(results).experiment_files_failed > 0 && (
                    <Tag color="error">失敗數 (failed): {getUploadSummary(results).experiment_files_failed}</Tag>
                  )}
                </Space>
              </li>
            )}
            {results.vector_stats && (
              <li>
                向量資料庫當前區塊總數：
                <Space size="small" style={{ marginLeft: 8 }}>
                  <Tag color="blue">學術文獻向量 (papers): {results.vector_stats.paper_vectors || 0}</Tag>
                  <Tag color="green">實驗數據向量 (experiments): {results.vector_stats.experiment_vectors || 0}</Tag>
                </Space>
              </li>
            )}
          </ul>
        </Card>
      )}

      <Card title="上傳規範與指南">
        <ul>
          <li>支援的檔案格式：PDF、Word (.docx)、Excel (.xlsx) 及 TXT 檔案</li>
          <li>單一檔案無容量上限</li>
          <li>上傳檔案將自動進行光學文字提取與語意分塊分析</li>
          <li>所有檔案均儲存於伺服器專有專區，保障數據安全性與隱私性</li>
        </ul>
      </Card>
    </div>
  );
};

export default UploadPage;

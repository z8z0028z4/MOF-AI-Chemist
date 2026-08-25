import React, { useState, useEffect } from 'react';
import {
  Card,
  Input,
  Button,
  List,
  Typography,
  Space,
  Select,
  message,
  Row,
  Col,
  Statistic,
  Tag,
  Divider,
  Spin,
  Empty,
  Tooltip,
  Tabs,
  Alert,
  Modal,
  Badge
} from 'antd';
import {
  SearchOutlined,
  FileTextOutlined,
  DownloadOutlined,
  EyeOutlined,
  FolderOutlined,
  FilePdfOutlined,
  ReloadOutlined,
  GlobalOutlined,
  CloudDownloadOutlined,
} from '@ant-design/icons';
import {
  downloadExternalPaper,
  searchExternalPapers,
  validateExternalPaperApi,
} from '../services/externalPaperApi';
import { getApiErrorMessage } from '../services/apiClient';
import {
  getPaperDownloadUrl,
  getPaperStats,
  getPaperViewUrl,
  listPapers,
  searchPapers as searchLocalPapers,
} from '../services/paperApi';

const { Title, Paragraph, Text } = Typography;
const { Search } = Input;
const { Option } = Select;
const BULK_DOWNLOAD_DELAY_MS = 1500;

const SearchPage = () => {
  // 本地文獻狀態
  const [loading, setLoading] = useState(false);
  const [paperLoading, setPaperLoading] = useState(false);
  const [papers, setPapers] = useState([]);
  const [paperStats, setPaperStats] = useState({});
  const [searchQuery, setSearchQuery] = useState('');
  const [searchType, setSearchType] = useState('all');
  const [results, setResults] = useState([]);
  const [hasSearched, setHasSearched] = useState(false);

  // 線上搜尋狀態
  const [onlineSearchLoading, setOnlineSearchLoading] = useState(false);
  const [onlineSearchKeywords, setOnlineSearchKeywords] = useState('');
  const [onlineSearchLimit, setOnlineSearchLimit] = useState(10);
  const [onlineResults, setOnlineResults] = useState([]);
  const [hasOnlineSearched, setHasOnlineSearched] = useState(false);
  const [apiAvailable, setApiAvailable] = useState(null);
  const [downloadingPapers, setDownloadingPapers] = useState({});
  const [bulkDownloading, setBulkDownloading] = useState(false);
  const [bulkDownloadProgress, setBulkDownloadProgress] = useState({ completed: 0, total: 0 });

  // 載入文獻統計資訊
  const loadPaperStats = async () => {
    try {
      const data = await getPaperStats();
      setPaperStats(data);
    } catch (error) {
      console.error('獲取文獻統計失敗:', error);
    }
  };

  // 載入文獻列表
  const loadPapers = async (search = '') => {
    setPaperLoading(true);
    try {
      const data = await listPapers({ search, limit: 1000 });
      setPapers(data.papers || []);
    } catch (error) {
      console.error('載入文獻列表失敗:', error);
      message.error('載入文獻列表失敗');
    } finally {
      setPaperLoading(false);
    }
  };

  // 搜尋文獻
  const searchPapers = async (query) => {
    if (!query.trim()) {
      message.warning('請輸入搜尋關鍵字');
      return;
    }

    setLoading(true);
    try {
      const data = await searchLocalPapers({ query, limit: 50 });
      setResults(data.papers || []);
      setHasSearched(true);
      message.success(`找到 ${data.total_count} 個文獻`);
    } catch (error) {
      console.error('搜尋文獻失敗:', error);
      message.error('搜尋文獻失敗');
    } finally {
      setLoading(false);
    }
  };

  // 處理搜尋
  const handleSearch = async () => {
    if (searchType === 'papers' || searchType === 'all') {
      await searchPapers(searchQuery);
    } else {
      message.info('此功能尚未實現');
    }
  };

  // 下載文獻
  const downloadPaper = (filename) => {
    window.open(getPaperDownloadUrl(filename), '_blank');
  };

  // 查看文獻
  const viewPaper = (filename) => {
    window.open(getPaperViewUrl(filename), '_blank');
  };

  // ==================== 線上搜尋功能 ====================

  // 驗證 Europe PMC API 狀態
  const validateApiStatus = async () => {
    try {
      const data = await validateExternalPaperApi();
      setApiAvailable(data.available);
    } catch (error) {
      console.error('API 驗證失敗:', error);
      setApiAvailable(false);
    }
  };

  // 線上搜尋論文
  const searchOnlinePapers = async () => {
    if (!onlineSearchKeywords.trim()) {
      message.warning('請輸入搜尋關鍵字');
      return;
    }

    // 將關鍵字分割為陣列
    const keywords = onlineSearchKeywords
      .split(/[,，\s]+/)
      .filter(k => k.trim().length > 0);

    if (keywords.length === 0) {
      message.warning('請輸入有效的關鍵字');
      return;
    }

    setOnlineSearchLoading(true);
    try {
      const data = await searchExternalPapers({
        keywords: keywords,
        limit: onlineSearchLimit,
      });

      if (data.success) {
        setOnlineResults(data.papers || []);
        setHasOnlineSearched(true);
        message.success(`成功找到 ${data.total_count} 篇相關論文`);
      } else {
        message.warning('搜尋未返回結果');
        setOnlineResults([]);
      }
    } catch (error) {
      console.error('線上搜尋失敗:', error);
      message.error('線上搜尋失敗: ' + getApiErrorMessage(error, error.message));
    } finally {
      setOnlineSearchLoading(false);
    }
  };

  // 下載線上論文至本地
  const downloadOnlinePaper = async (paper, options = {}) => {
    const { refreshAfterDownload = true, silentSuccess = false } = options;
    const paperId = paper.pmcid;
    setDownloadingPapers(prev => ({ ...prev, [paperId]: true }));

    try {
      const data = await downloadExternalPaper({
        pmcid: paper.pmcid,
        title: paper.title,
        pdfUrl: paper.pdf_url,
      });

      if (data.success) {
        if (!silentSuccess) {
          message.success(`論文已下載至: ${data.file_path}`);
        }
        if (refreshAfterDownload) {
          loadPapers();
          loadPaperStats();
        }
        return true;
      } else {
        message.warning(data.message || '下載失敗');
        return false;
      }
    } catch (error) {
      console.error('下載論文失敗:', error);
      message.error('下載論文失敗: ' + getApiErrorMessage(error, error.message));
      return false;
    } finally {
      setDownloadingPapers(prev => ({ ...prev, [paperId]: false }));
    }
  };

  const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

  const downloadAllOnlinePapers = async () => {
    if (onlineResults.length === 0) {
      message.warning('目前沒有可下載的搜尋結果');
      return;
    }

    setBulkDownloading(true);
    setBulkDownloadProgress({ completed: 0, total: onlineResults.length });

    let successCount = 0;
    let failureCount = 0;

    try {
      for (let index = 0; index < onlineResults.length; index += 1) {
        const paper = onlineResults[index];
        const ok = await downloadOnlinePaper(paper, {
          refreshAfterDownload: false,
          silentSuccess: true,
        });

        if (ok) {
          successCount += 1;
        } else {
          failureCount += 1;
        }

        setBulkDownloadProgress({ completed: index + 1, total: onlineResults.length });

        if (index < onlineResults.length - 1) {
          await sleep(BULK_DOWNLOAD_DELAY_MS);
        }
      }

      if (successCount > 0) {
        loadPapers();
        loadPaperStats();
      }

      if (failureCount > 0) {
        message.warning(`批次下載完成：成功 ${successCount} 篇，失敗 ${failureCount} 篇`);
      } else {
        message.success(`批次下載完成：成功 ${successCount} 篇`);
      }
    } finally {
      setBulkDownloading(false);
    }
  };

  const getOnlinePaperViewUrl = (paper) => {
    if (paper.doi) {
      return `https://doi.org/${paper.doi}`;
    }
    return `https://europepmc.org/article/PMC/${paper.pmcid}`;
  };

  // 格式化檔案大小
  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  // 格式化時間
  const formatTime = (timestamp) => {
    return new Date(timestamp * 1000).toLocaleString('zh-TW');
  };

  // 渲染文獻項目
  const renderPaperItem = (paper) => (
    <List.Item
      actions={[
        <Tooltip title="查看文獻">
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => viewPaper(paper.filename)}
          >
            查看
          </Button>
        </Tooltip>,
        <Tooltip title="下載文獻">
          <Button
            type="link"
            icon={<DownloadOutlined />}
            onClick={() => downloadPaper(paper.filename)}
          >
            下載
          </Button>
        </Tooltip>
      ]}
    >
      <List.Item.Meta
        avatar={<FilePdfOutlined style={{ fontSize: '24px', color: '#ff4d4f' }} />}
        title={
          <Space>
            <span>{paper.display_name}</span>
            <Tag color="blue">PDF</Tag>
          </Space>
        }
        description={
          <div>
            <div><strong>檔案名:</strong> {paper.filename}</div>
            <div><strong>檔案大小:</strong> {formatFileSize(paper.size)}</div>
            <div><strong>修改時間:</strong> {formatTime(paper.modified_time)}</div>
            <div><strong>文獻ID:</strong> {paper.paper_id}</div>
          </div>
        }
      />
    </List.Item>
  );

  // 渲染搜尋結果
  const renderSearchResult = (paper) => (
    <List.Item
      actions={[
        <Tooltip title="查看文獻">
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => viewPaper(paper.filename)}
          >
            查看
          </Button>
        </Tooltip>,
        <Tooltip title="下載文獻">
          <Button
            type="link"
            icon={<DownloadOutlined />}
            onClick={() => downloadPaper(paper.filename)}
          >
            下載
          </Button>
        </Tooltip>
      ]}
    >
      <List.Item.Meta
        avatar={<FilePdfOutlined style={{ fontSize: '24px', color: '#ff4d4f' }} />}
        title={
          <Space>
            <span>{paper.display_name}</span>
            <Tag color="blue">PDF</Tag>
            {paper.match_score > 0 && <Tag color="green">匹配度: {paper.match_score}</Tag>}
          </Space>
        }
        description={
          <div>
            <div><strong>檔案名:</strong> {paper.filename}</div>
            <div><strong>檔案大小:</strong> {formatFileSize(paper.size)}</div>
            <div><strong>修改時間:</strong> {formatTime(paper.modified_time)}</div>
          </div>
        }
      />
    </List.Item>
  );

  // 渲染線上搜尋結果
  const renderOnlineResult = (paper) => (
    <List.Item
      actions={[
        <Tooltip title={paper.doi ? '透過 DOI 查看文獻' : '在 Europe PMC 查看'}>
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => window.open(getOnlinePaperViewUrl(paper), '_blank')}
          >
            查看
          </Button>
        </Tooltip>,
        <Tooltip title="下載至 local_data/downloaded_papers，不會建立 embedding">
          <Button
            type="link"
            icon={<CloudDownloadOutlined />}
            loading={downloadingPapers[paper.pmcid]}
            disabled={bulkDownloading}
            onClick={() => downloadOnlinePaper(paper)}
          >
            下載
          </Button>
        </Tooltip>
      ].filter(Boolean)}
    >
      <List.Item.Meta
        avatar={<GlobalOutlined style={{ fontSize: '24px', color: '#1890ff' }} />}
        title={
          <Space wrap>
            <span>{paper.title}</span>
            <Tag color="green">Open Access</Tag>
            {paper.source && <Tag color="purple">{paper.source}</Tag>}
          </Space>
        }
        description={
          <div>
            <div><strong>PMCID:</strong> {paper.pmcid}</div>
            {paper.doi && <div><strong>DOI:</strong> {paper.doi}</div>}
            {paper.abstract && (
              <div style={{ marginTop: 8 }}>
                <Text type="secondary" ellipsis={{ rows: 2, expandable: true, symbol: '更多' }}>
                  {paper.abstract}
                </Text>
              </div>
            )}
          </div>
        }
      />
    </List.Item>
  );

  // 初始化載入
  useEffect(() => {
    loadPaperStats();
    loadPapers();
    validateApiStatus();
  }, []);

  return (
    <div>
      <Title level={2}>文獻搜尋與瀏覽</Title>
      <Paragraph>
        瀏覽本地文獻或搜尋 Europe PMC 學術資料庫中的 Open Access 論文。
      </Paragraph>

      <Tabs
        defaultActiveKey="local"
        size="large"
        items={[
          {
            key: 'local',
            label: <span><FolderOutlined />本地文獻</span>,
            children: (
              <>
          {/* 文獻統計資訊 */}
          <Card title="文獻統計" style={{ marginBottom: 24 }}>
            <Row gutter={16}>
              <Col span={6}>
                <Statistic
                  title="總文獻數"
                  value={paperStats.total_papers || 0}
                  prefix={<FileTextOutlined />}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="總大小"
                  value={paperStats.total_size_mb || 0}
                  suffix="MB"
                  prefix={<FolderOutlined />}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="資料夾"
                  value={paperStats.directory || 'experiment_data/papers'}
                  prefix={<FolderOutlined />}
                />
              </Col>
              <Col span={6}>
                <Button
                  icon={<ReloadOutlined />}
                  onClick={loadPaperStats}
                  loading={paperLoading}
                >
                  刷新統計
                </Button>
              </Col>
            </Row>
          </Card>

          {/* 搜尋功能 */}
          <Card title="文獻搜尋" style={{ marginBottom: 24 }}>
            <Space direction="vertical" style={{ width: '100%' }} size="large">
              <Space>
                <Search
                  placeholder="輸入搜尋關鍵字..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onPressEnter={handleSearch}
                  style={{ width: 400 }}
                />
                <Select
                  value={searchType}
                  onChange={setSearchType}
                  style={{ width: 150 }}
                >
                  <Option value="papers">文獻</Option>
                  <Option value="experiments">實驗</Option>
                  <Option value="all">全部</Option>
                </Select>
                <Button
                  type="primary"
                  icon={<SearchOutlined />}
                  onClick={handleSearch}
                  loading={loading}
                >
                  搜尋
                </Button>
              </Space>
            </Space>
          </Card>

          {/* 搜尋結果 */}
          {hasSearched && (
            <Card title={`搜尋結果 (${results.length})`} style={{ marginBottom: 24 }}>
              {results.length > 0 ? (
                <List
                  itemLayout="horizontal"
                  dataSource={results}
                  renderItem={renderSearchResult}
                />
              ) : (
                <Empty description="沒有找到匹配的文獻" />
              )}
            </Card>
          )}

          <Divider />

          {/* 文獻瀏覽 */}
          <Card
            title="文獻瀏覽"
            extra={
              <Space>
                <Search
                  placeholder="篩選文獻..."
                  onSearch={loadPapers}
                  style={{ width: 200 }}
                  allowClear
                />
                <Button
                  icon={<ReloadOutlined />}
                  onClick={() => loadPapers()}
                  loading={paperLoading}
                >
                  刷新
                </Button>
              </Space>
            }
          >
            <Spin spinning={paperLoading}>
              {papers.length > 0 ? (
                <List
                  itemLayout="horizontal"
                  dataSource={papers}
                  renderItem={renderPaperItem}
                  pagination={{
                    pageSize: 10,
                    showSizeChanger: false,
                    showQuickJumper: false,
                    showTotal: (total, range) =>
                      `第 ${range[0]}-${range[1]} 項，共 ${total} 項`
                  }}
                />
              ) : (
                <Empty description="沒有找到文獻檔案" />
              )}
            </Spin>
          </Card>
              </>
            ),
          },

          {
            key: 'online',
            label: (
              <span>
                <GlobalOutlined />
                線上搜尋
                {apiAvailable !== null && (
                  <Badge
                    status={apiAvailable ? "success" : "error"}
                    style={{ marginLeft: 8 }}
                  />
                )}
              </span>
            ),
            children: (
              <>
          {/* API 狀態提示 */}
          {apiAvailable === false && (
            <Alert
              message="Europe PMC API 無法連線"
              description="線上搜尋功能目前不可用，請檢查網路連線後重試。"
              type="warning"
              showIcon
              style={{ marginBottom: 24 }}
              action={
                <Button size="small" onClick={validateApiStatus}>
                  重新檢測
                </Button>
              }
            />
          )}

          {apiAvailable === true && (
            <Alert
              message="Europe PMC API 連線正常"
              description="您可以搜尋 Open Access 學術論文並下載至本地。"
              type="success"
              showIcon
              style={{ marginBottom: 24 }}
            />
          )}

          {/* 線上搜尋表單 */}
          <Card title="搜尋 Europe PMC 論文" style={{ marginBottom: 24 }}>
            <Space direction="vertical" style={{ width: '100%' }} size="large">
              <Row gutter={16} align="middle">
                <Col span={14}>
                  <Input
                    placeholder="輸入關鍵字（多個關鍵字用逗號或空格分隔，例如: MOF, CO2 adsorption）"
                    value={onlineSearchKeywords}
                    onChange={(e) => setOnlineSearchKeywords(e.target.value)}
                    onPressEnter={searchOnlinePapers}
                    prefix={<SearchOutlined />}
                    size="large"
                  />
                </Col>
                <Col span={4}>
                  <Select
                    value={onlineSearchLimit}
                    onChange={setOnlineSearchLimit}
                    style={{ width: '100%' }}
                    size="large"
                  >
                    <Option value={5}>5 篇</Option>
                    <Option value={10}>10 篇</Option>
                    <Option value={20}>20 篇</Option>
                    <Option value={30}>30 篇</Option>
                    <Option value={50}>50 篇</Option>
                  </Select>
                </Col>
                <Col span={6}>
                  <Button
                    type="primary"
                    icon={<GlobalOutlined />}
                    onClick={searchOnlinePapers}
                    loading={onlineSearchLoading}
                    disabled={apiAvailable === false}
                    size="large"
                    block
                  >
                    搜尋 Open Access 論文
                  </Button>
                </Col>
              </Row>
              <Alert
                type="info"
                showIcon
                message="下載不會自動 embedding"
                description="Europe PMC 下載會保存到 local_data/downloaded_papers。需要建立向量時，請再使用檔案上傳/匯入流程。批次下載會自動加入間隔。"
              />
            </Space>
          </Card>

          {/* 線上搜尋結果 */}
          {hasOnlineSearched && (
            <Card
              title={
                <Space>
                  <span>搜尋結果</span>
                  <Tag color="blue">{onlineResults.length} 篇論文</Tag>
                  {bulkDownloading && (
                    <Tag color="processing">
                      下載中 {bulkDownloadProgress.completed}/{bulkDownloadProgress.total}
                    </Tag>
                  )}
                </Space>
              }
              extra={
                <Button
                  icon={<CloudDownloadOutlined />}
                  onClick={downloadAllOnlinePapers}
                  loading={bulkDownloading}
                  disabled={onlineResults.length === 0 || apiAvailable === false}
                >
                  全部下載
                </Button>
              }
              style={{ marginBottom: 24 }}
            >
              <Spin spinning={onlineSearchLoading}>
                {onlineResults.length > 0 ? (
                  <List
                    itemLayout="horizontal"
                    dataSource={onlineResults}
                    renderItem={renderOnlineResult}
                    pagination={{
                      pageSize: 5,
                      showSizeChanger: false,
                      showTotal: (total) => `共 ${total} 篇論文`
                    }}
                  />
                ) : (
                  <Empty description="沒有找到匹配的論文" />
                )}
              </Spin>
            </Card>
          )}

          {/* 使用說明 */}
          {!hasOnlineSearched && (
            <Card title="使用說明">
              <Paragraph>
                <ul>
                  <li><strong>搜尋關鍵字：</strong>輸入與您研究相關的關鍵字，多個關鍵字可用逗號或空格分隔</li>
                  <li><strong>搜尋數量：</strong>選擇每次搜尋返回的論文數量上限</li>
                  <li><strong>查看論文：</strong>點擊「查看」按鈕可透過 DOI 或 Europe PMC 開啟文獻頁面</li>
                  <li><strong>下載論文：</strong>點擊「下載」可將 PDF 儲存至您選擇的本地資料夾；預設只下載，不會建立 embedding</li>
                  <li><strong>全部下載：</strong>搜尋結果出現後可批次下載全部論文，系統會依設定間隔逐篇下載</li>
                </ul>
              </Paragraph>
              <Paragraph type="secondary">
                注意：僅支援 Open Access 論文的下載，部分論文可能因版權限制無法直接下載 PDF。
              </Paragraph>
            </Card>
          )}
              </>
            ),
          },
        ]}
      />
    </div>
  );
};

export default SearchPage;

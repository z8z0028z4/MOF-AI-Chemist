import React, { useState, useEffect } from 'react';
import { Card, Input, Button, Table, Typography, Space, message, Tag, List, Switch, Row, Col, Statistic, Spin, Image, Divider, Collapse } from 'antd';
import { SearchOutlined, ExperimentOutlined, DatabaseOutlined, SaveOutlined, EyeOutlined } from '@ant-design/icons';
import SmilesDrawer from '../components/SmilesDrawer';
import {
  getChemicalDatabaseStats,
  listDatabaseChemicals,
  searchChemical,
} from '../services/chemicalApi';

const { Title, Paragraph, Text } = Typography;
const { Search } = Input;

const Chemical = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [chemicalData, setChemicalData] = useState(null);
  const [formulaCandidates, setFormulaCandidates] = useState([]);
  const [candidateCount, setCandidateCount] = useState(null);
  const [databaseStats, setDatabaseStats] = useState(null);
  // 移除不需要的狀態變量
  const [databaseChemicals, setDatabaseChemicals] = useState([]);
  const [showDatabase, setShowDatabase] = useState(false);
  const [databaseSearchQuery, setDatabaseSearchQuery] = useState('');
  const [filteredDatabaseChemicals, setFilteredDatabaseChemicals] = useState([]);

  // Load database statistics
  const loadDatabaseStats = async () => {
    try {
      const stats = await getChemicalDatabaseStats();
      setDatabaseStats(stats);
    } catch (error) {
      console.error('Failed to load database stats:', error);
    }
  };

  // Load database chemicals
  const loadDatabaseChemicals = async () => {
    try {
      console.log('🔄 [DATABASE-LIST] 開始載入數據庫化學品列表...');
      const data = await listDatabaseChemicals();
      console.log('🔄 [DATABASE-LIST] 載入完成，化學品數量:', data.chemicals?.length || 0);
      setDatabaseChemicals(data.chemicals || []);
      // 初始化過濾列表
      setFilteredDatabaseChemicals(data.chemicals || []);
    } catch (error) {
      console.error('Failed to load database chemicals:', error);
    }
  };

  // Filter database chemicals based on search query
  const filterDatabaseChemicals = (query) => {
    if (!query.trim()) {
      setFilteredDatabaseChemicals(databaseChemicals);
    } else {
      const filtered = databaseChemicals.filter(chemical =>
        chemical.name.toLowerCase().includes(query.toLowerCase()) ||
        (chemical.formula && chemical.formula.toLowerCase().includes(query.toLowerCase())) ||
        (chemical.cas && chemical.cas.toLowerCase().includes(query.toLowerCase()))
      );
      setFilteredDatabaseChemicals(filtered);
    }
  };

  // Load initial data
  useEffect(() => {
    loadDatabaseStats();
  }, []);

  const runChemicalSearch = async (chemicalName, selectedCid = undefined) => {
    if (!chemicalName.trim()) {
      message.warning('Please enter a chemical name or formula');
      return;
    }

    setLoading(true);
    setChemicalData(null);
    setFormulaCandidates([]);
    setCandidateCount(null);
    try {
      console.log('Searching for chemical:', chemicalName);

      const data = await searchChemical({
        chemicalName,
        includeSafety: true,
        includeProperties: true,
        includeStructure: true,
        saveToDatabase: true,
        selectedCid,
      });

      console.log('🔍 [CHEMICAL-SEARCH] API 響應數據:', data);
      console.log('🔍 [CHEMICAL-SEARCH] 是否有 svg_structure:', !!data.svg_structure);
      console.log('🔍 [CHEMICAL-SEARCH] 是否有 png_structure:', !!data.png_structure);
      console.log('🔍 [CHEMICAL-SEARCH] 是否有 safety_data:', !!data.safety_data);
      console.log('🔍 [CHEMICAL-SEARCH] safety_data 內容:', data.safety_data);

      if (data.error) {
        message.error(data.error);
        setChemicalData(null);
      } else {
        setFormulaCandidates(data.candidates || []);
        setCandidateCount(data.candidate_count ?? null);
        setChemicalData(data.candidates?.length ? null : data);
        message.success(`Chemical information found${data.saved_to_database ? ' and saved to database' : ''}`);

        // Refresh database stats and list if saved
        if (data.saved_to_database) {
          console.log('🔄 [CHEMICAL-SEARCH] 化學品已保存到數據庫，開始刷新...');
          loadDatabaseStats();
          // 如果 Database 視圖已經打開，重新載入列表
          if (showDatabase) {
            console.log('🔄 [CHEMICAL-SEARCH] Database 視圖已打開，重新載入列表...');
            loadDatabaseChemicals();
          } else {
            console.log('🔄 [CHEMICAL-SEARCH] Database 視圖未打開，跳過列表刷新');
          }
        }
      }
    } catch (error) {
      setChemicalData(null);
      setFormulaCandidates([]);
      setCandidateCount(null);
      if (error?.status === 503) {
        message.error('PubChem 暫時無法使用，請稍後重試');
      } else if (error?.status === 404) {
        message.error('未找到化學品資訊');
      } else {
        message.error('查詢化學品資訊失敗');
      }
      console.error('Chemical search error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async () => {
    await runChemicalSearch(searchQuery);
  };

  const columns = [
    {
      title: 'Property',
      dataIndex: 'property',
      key: 'property',
      width: '30%',
    },
    {
      title: 'Value',
      dataIndex: 'value',
      key: 'value',
      width: '70%',
    },
  ];

  const renderChemicalInfo = () => {
    if (!chemicalData) return null;

    return (
      <Collapse
        defaultActiveKey={['chemicals']}
        style={{ marginBottom: 16 }}
        items={[
          {
            key: 'chemicals',
            label: <span style={{ fontWeight: 700, fontSize: 27 }}>🧪 化學品屬性資訊</span>,
            children: (
              <List
                dataSource={[chemicalData]}
                renderItem={(c, index) => {
                  console.log('🔍 [CHEMICAL-DISPLAY] 化學品數據:', c);
                  console.log('🔍 [CHEMICAL-DISPLAY] 是否有 svg_structure:', !!c.svg_structure);
                  console.log('🔍 [CHEMICAL-DISPLAY] 是否有 png_structure:', !!c.png_structure);
                  console.log('🔍 [CHEMICAL-DISPLAY] 是否有 safety_icons:', !!c.safety_icons);
                  console.log('🔍 [CHEMICAL-DISPLAY] safety_icons 內容:', c.safety_icons);

                  return (
                    <List.Item style={{ padding: '16px 0', borderBottom: '1px solid #f0f0f0' }}>
                      <div style={{ width: '100%' }}>
                        <div style={{ display: 'flex', gap: '16px', alignItems: 'flex-start' }}>
                          {/* Structure Image - 優先使用 SMILES 繪製的結構圖 */}
                          <div style={{ flex: '0 0 150px' }}>
                            <SmilesDrawer
                              svgStructure={c.svg_structure}
                              pngStructure={c.png_structure}
                              imageUrl={c.image_url}
                              smiles={c.smiles}
                              name={c.name}
                              width={120}
                              height={120}
                              showSmiles={false}
                              loading={false}
                              error={null}
                            />
                            {/* 調試信息 */}
                            <div style={{ fontSize: '10px', color: '#666', marginTop: '4px' }}>
                              Debug: SVG={!!c.svg_structure}, PNG={!!c.png_structure}, SMILES={c.smiles}
                            </div>
                          </div>

                          {/* Chemical Name and Properties */}
                          <div style={{ flex: '1', display: 'flex', gap: '24px' }}>
                            {/* Properties */}
                            <div style={{ flex: '1' }}>
                              <Text strong style={{ fontSize: '24px', marginBottom: '8px', display: 'block' }}>
                                {c.pubchem_url ? (
                                  <a href={c.pubchem_url} target="_blank" rel="noopener noreferrer" style={{ color: '#1890ff', fontSize: '24px', fontWeight: 'bold' }}>
                                    {c.name}
                                  </a>
                                ) : (
                                  <span style={{ color: '#1890ff', fontSize: '24px', fontWeight: 'bold' }}>{c.name}</span>
                                )}
                              </Text>
                              <div style={{
                                fontSize: '14px',
                                lineHeight: '1.5',
                                wordBreak: 'break-word',
                                overflowWrap: 'break-word'
                              }}>
                                <div><strong>分子式 (Formula)：</strong> <code>{c.formula || '-'}</code></div>
                                <div><strong>分子量 (Molecular Weight)：</strong> <code>{c.weight || c.molecular_weight || '-'}</code></div>
                                <div><strong>沸點 (Boiling Point)：</strong> <code>{c.boiling_point_c || c.boiling_point || '-'}</code></div>
                                <div><strong>熔點 (Melting Point)：</strong> <code>{c.melting_point_c || c.melting_point || '-'}</code></div>
                                <div><strong>CAS 編號 (CAS No.)：</strong> <code>{c.cas || c.cas_number || '-'}</code></div>
                                <div><strong>SMILES 結構式：</strong> <code>{c.smiles || '-'}</code></div>
                                {c.cid && <div><strong>PubChem CID:</strong> <code>{c.cid}</code></div>}
                              </div>
                            </div>

                            {/* Safety Icons */}
                            <div style={{ flex: '0 0 150px' }}>
                              <Text strong style={{ fontSize: '14px', marginBottom: '8px', display: 'block' }}>
                                安全防護標示 (Handling Safety)
                              </Text>
                              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                {/* NFPA Diamond */}
                                {(c.safety_icons?.nfpa_image || c.safety_data?.nfpa_image) && (
                                  <img
                                    src={c.safety_icons?.nfpa_image || c.safety_data?.nfpa_image}
                                    alt="NFPA"
                                    style={{ width: '50px', height: '50px' }}
                                  />
                                )}
                                {/* GHS Icons */}
                                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', maxWidth: '120px' }}>
                                  {(c.safety_icons?.ghs_icons || c.safety_data?.ghs_icons || []).map((icon, index) => (
                                    <img
                                      key={index}
                                      src={icon}
                                      alt="GHS"
                                      style={{ width: '40px', height: '40px' }}
                                    />
                                  ))}
                                </div>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </List.Item>
                  );
                }}
              />
            ),
          },
        ]}
      />
    );
  };

  const renderFormulaCandidates = () => {
    if (!formulaCandidates.length) return null;
    return (
      <Card title={`Formula matches (${candidateCount ?? formulaCandidates.length})`} style={{ marginBottom: 16 }}>
        <List
          bordered
          dataSource={formulaCandidates}
          renderItem={(candidate) => (
            <List.Item
              actions={[<Button key="select" type="primary" onClick={() => runChemicalSearch(searchQuery, candidate.cid)}>Select</Button>]}
            >
              <List.Item.Meta
                title={`${candidate.name} (CID ${candidate.cid})`}
                description={`Formula: ${candidate.formula || '-'} | Molecular weight: ${candidate.molecular_weight || '-'}`}
              />
            </List.Item>
          )}
        />
      </Card>
    );
  };

  return (
    <div>
      <Title level={2}>化學品查詢</Title>
      <Paragraph>
        搜尋化學原料並檢視其分子物理性質、安全防護標示（GHS/NFPA）與分子結構。查詢結果會自動快取至資料庫中。
      </Paragraph>

      {/* Search Section */}
      <Card title="化學品搜尋" style={{ marginBottom: 24 }}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Space>
            <Search
              placeholder="請輸入化學品名稱或分子式（例如：methanol, C6H12O6...）"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onPressEnter={handleSearch}
              style={{ width: 400 }}
            />
            <Button
              type="primary"
              icon={<SearchOutlined />}
              onClick={handleSearch}
              loading={loading}
            >
              搜尋
            </Button>
            <Button
              icon={<EyeOutlined />}
              onClick={() => {
                setShowDatabase(!showDatabase);
                if (!showDatabase) {
                  loadDatabaseChemicals();
                }
              }}
            >
              {showDatabase ? '隱藏' : '檢視'} 數據庫 ({databaseStats?.total_chemicals || 0})
            </Button>
          </Space>

          {/* 移除不需要的選項 */}
        </Space>
      </Card>

      {/* Chemical Information Display - 移到前面 */}
      {renderFormulaCandidates()}
      {renderChemicalInfo()}

      {/* Database Chemicals List - 移到後面，使用固定高度 */}
      {showDatabase && (
        <Card title="已存儲化學品列表" style={{ marginBottom: 24 }}>
          {/* 搜尋功能 */}
          <div style={{ marginBottom: 16 }}>
            <Search
              placeholder="搜尋化學品名稱、分子式或 CAS 號碼"
              value={databaseSearchQuery}
              onChange={(e) => {
                setDatabaseSearchQuery(e.target.value);
                filterDatabaseChemicals(e.target.value);
              }}
              onSearch={(value) => filterDatabaseChemicals(value)}
              style={{ width: '100%' }}
            />
          </div>

          <Spin spinning={databaseChemicals.length === 0}>
            <div style={{
              maxHeight: '400px',
              overflowY: 'auto',
              border: '1px solid #f0f0f0',
              borderRadius: '6px',
              padding: '8px'
            }}>
              <List
                dataSource={filteredDatabaseChemicals}
                renderItem={(chemical) => (
                <List.Item
                  actions={[
                    <Button
                      type="link"
                      onClick={async () => {
                        setSearchQuery(chemical.name);
                        await runChemicalSearch(chemical.name);
                      }}
                    >
                      檢視詳情
                    </Button>
                  ]}
                >
                  <List.Item.Meta
                    title={chemical.name}
                    description={`分子式：${chemical.formula || 'N/A'} | CAS 編號：${chemical.cas || chemical.cas_number || 'N/A'}`}
                  />
                </List.Item>
              )}
              />
            </div>
          </Spin>
        </Card>
      )}
    </div>
  );
};

export default Chemical;

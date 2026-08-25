import { Alert, Button, Card, Collapse, Divider, Form, Input, List, message, Select, Space, Typography, Spin, Progress, Tag, Table } from 'antd';
import React, { useMemo, useRef, useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import SmilesDrawer from '../components/SmilesDrawer';
import { useTextHighlight } from '../components/TextHighlight/TextHighlightProvider';
import { useAppState } from '../contexts/AppStateContext';
import { getApiErrorMessage } from '../services/apiClient';
import { getDocumentUrl } from '../services/documentApi';
import {
  getRunStatus,
  getJobStatus,
  createPropertyPredictorJob,
  createCifGeneratorJob,
  getRunArtifactText,
  getCifGeneratorTopologies
} from '../services/mofApi';
import {
  downloadProposalDocx,
  generateExperimentDetail,
  generateProposal,
  reviseProposal,
  translateProposalMof,
  runProposalScreening
} from '../services/proposalApi';
import { getDemoModeSettings } from '../services/settingsApi';
import {
  createDemoProposal,
  createDemoRevision,
  DEFAULT_DEMO_CONFIG,
  DEMO_EXPERIMENT_DETAIL,
  DEMO_PORMAKE_CANDIDATE,
  DEMO_SCREENING_RESULTS,
  readDemoConfig,
  getDemoExperimentDetailByProposal,
} from '../services/proposalDemo';

const { Title, Paragraph, Text } = Typography;
const { TextArea } = Input;
const { Option } = Select;

const Proposal = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [isTextareaFocused, setIsTextareaFocused] = useState(false); // 追蹤輸入框是否被聚焦
  const [isReviseInputFocused, setIsReviseInputFocused] = useState(false); // 追蹤修訂輸入框是否被聚焦
  const reviseInputRef = useRef(null); // 修訂輸入框的 ref

  // 使用全局狀態管理
  const {
    state,
    setProposalFormData,
    setProposalResult,
    setProposalExperiment,
    setProposalState
  } = useAppState();

  const {
    formData = {},
    proposal = '',
    chemicals = [],
    notFound = [],
    citations = [],
    chunks = [],
    experimentDetail = '',
    structuredExperiment = null,
    structuredProposal = null,
    retrievalCount = 10,
    mofLinkerMode = 'auto',
    hasGeneratedContent = false,
    showReviseInput = false,
    reviseFeedback = '',
    screeningLoading = false,
    screeningStep = 'assembling',
    screeningProgress = 0,
    screeningError = '',
    screeningResults = []
  } = state.proposal || {};

  // 文字反白功能
  const { setMode, setProposal: setTextHighlightProposal, setText, handleTextSelection, setReviseCallback } = useTextHighlight();

  const navigate = useNavigate();
  const [translationLoading, setTranslationLoading] = useState(false);
  const [resolvedNodeId, setResolvedNodeId] = useState('');
  const [resolvedLinkerId, setResolvedLinkerId] = useState('');
  const [resolvedLinkerId2, setResolvedLinkerId2] = useState('');
  const [pairingCandidates, setPairingCandidates] = useState([]);
  const [pairingStatus, setPairingStatus] = useState('');
  const [pairingMessage, setPairingMessage] = useState('');

  const [extractedMetalElement, setExtractedMetalElement] = useState('');
  const [extractedLinkerName, setExtractedLinkerName] = useState('');
  const [extractedLinkerSmiles, setExtractedLinkerSmiles] = useState('');
  const [extractedLinkerName2, setExtractedLinkerName2] = useState('');
  const [extractedLinkerSmiles2, setExtractedLinkerSmiles2] = useState('');
  const [loadingCifId, setLoadingCifId] = useState('');
  const [demoConfig, setDemoConfig] = useState(() => readDemoConfig());

  const isDemoStage = useCallback(
    (stage) => Boolean(demoConfig.enabled && demoConfig[stage]),
    [demoConfig]
  );

  useEffect(() => {
    let active = true;
    const syncDemoConfig = async () => {
      try {
        const config = await getDemoModeSettings();
        if (active) {
          const next = { ...DEFAULT_DEMO_CONFIG, ...config };
          setDemoConfig(next);
          localStorage.setItem('proposal_demo_config', JSON.stringify(next));
        }
      } catch (error) {
        console.warn('Demo mode settings unavailable; using local cache.', error);
      }
    };
    const handleDemoUpdate = (event) => {
      setDemoConfig({
        ...DEFAULT_DEMO_CONFIG,
        ...(event.detail || readDemoConfig()),
      });
    };
    syncDemoConfig();
    window.addEventListener('demo-config-updated', handleDemoUpdate);
    return () => {
      active = false;
      window.removeEventListener('demo-config-updated', handleDemoUpdate);
    };
  }, []);

  // 從化學品清單自動解析金屬與配體
  const extractMetalAndLinkers = useCallback((chemList) => {
    if (!chemList || chemList.length === 0) return { metal: '', l1: '', l1_name: '', l2: '', l2_name: '' };

    const metals = chemList.filter(c =>
      (c.role && c.role.toLowerCase().includes('metal')) ||
      (c.name && /^(copper|zinc|zirconium|iron|cobalt|nickel|chromium|aluminum|titanium|magnesium|manganese)/i.test(c.name))
    );

    const linkers = chemList.filter(c =>
      (c.role && (c.role.toLowerCase().includes('linker') || c.role.toLowerCase().includes('ligand'))) ||
      (c.smiles && c.smiles !== '-' && !/metal/i.test(c.role || '') && !/solvent/i.test(c.role || ''))
    );

    let metalElement = '';
    if (metals.length > 0) {
      const mName = metals[0].name.toLowerCase();
      if (mName.includes('copper') || mName.includes('cu')) metalElement = 'Cu';
      else if (mName.includes('zinc') || mName.includes('zn')) metalElement = 'Zn';
      else if (mName.includes('zirconium') || mName.includes('zr')) metalElement = 'Zr';
      else if (mName.includes('iron') || mName.includes('fe')) metalElement = 'Fe';
      else if (mName.includes('cobalt') || mName.includes('co')) metalElement = 'Co';
      else if (mName.includes('nickel') || mName.includes('ni')) metalElement = 'Ni';
      else if (mName.includes('chromium') || mName.includes('cr')) metalElement = 'Cr';
      else if (mName.includes('aluminum') || mName.includes('al')) metalElement = 'Al';
      else if (mName.includes('titanium') || mName.includes('ti')) metalElement = 'Ti';
    }

    return {
      metal: metalElement || (metals[0] ? metals[0].name : ''),
      l1: linkers[0] ? linkers[0].smiles : '',
      l1_name: linkers[0] ? linkers[0].name : '',
      l2: linkers[1] ? linkers[1].smiles : '',
      l2_name: linkers[1] ? linkers[1].name : ''
    };
  }, []);

  // 當 structuredProposal 或 chemicals 改變時，自動擷取並對接 PORMAKE
  useEffect(() => {
    const autoTranslate = async () => {
      if (
        isDemoStage('mock_property_prediction')
        && (structuredProposal || chemicals.length > 0 || proposal)
      ) {
        setExtractedMetalElement('Cu');
        setExtractedLinkerName('benzene-1,3,5-tricarboxylic acid');
        setExtractedLinkerSmiles('C1=C(C=C(C=C1C(=O)O)C(=O)O)C(=O)O');
        setExtractedLinkerName2('');
        setExtractedLinkerSmiles2('');
        setPairingCandidates([DEMO_PORMAKE_CANDIDATE]);
        setPairingStatus('success');
        setPairingMessage('Deterministic demo candidate.');
        setResolvedNodeId('N409');
        setResolvedLinkerId('N10');
        setResolvedLinkerId2('');
        return;
      }

      let metal = '';
      let l1_name = '';
      let l1_smiles = '';
      let l2_name = '';
      let l2_smiles = '';

      if (structuredProposal) {
        metal = structuredProposal.mof_metal_element || '';
        l1_name = structuredProposal.mof_linker_name || '';
        l1_smiles = structuredProposal.mof_linker_smiles || '';
        l2_name = structuredProposal.mof_linker_name_2 || '';
        l2_smiles = structuredProposal.mof_linker_smiles_2 || '';
      } else if (chemicals && chemicals.length > 0) {
        const extracted = extractMetalAndLinkers(chemicals);
        metal = extracted.metal;
        l1_name = extracted.l1_name;
        l1_smiles = extracted.l1;
        l2_name = extracted.l2_name;
        l2_smiles = extracted.l2;
      }

      setExtractedMetalElement(metal);
      setExtractedLinkerName(l1_name);
      setExtractedLinkerSmiles(l1_smiles);
      setExtractedLinkerName2(l2_name);
      setExtractedLinkerSmiles2(l2_smiles);

      if (!metal || !l1_smiles) {
        setResolvedNodeId('');
        setResolvedLinkerId('');
        setResolvedLinkerId2('');
        setPairingCandidates([]);
        setPairingStatus('');
        setPairingMessage('');
        return;
      }

      setTranslationLoading(true);
      try {
        console.log('🔄 [AUTO-TRANSLATE] 開始對接 PORMAKE...', { metal, l1_smiles, l2_smiles });
        const res = await translateProposalMof({
          metalElement: metal,
          linkerSmiles: l1_smiles,
          linkerSmiles2: l2_smiles || undefined
        });
        console.log('🔄 [AUTO-TRANSLATE] 對接結果:', res);
        const exactCandidates = res.candidates || [];
        setPairingCandidates(exactCandidates);
        setPairingStatus(res.status || '');
        setPairingMessage(res.message || '');
        const first = exactCandidates[0];
        setResolvedNodeId(first?.node_id || '');
        setResolvedLinkerId(first?.linker_id || '');
        setResolvedLinkerId2('');
      } catch (err) {
        console.error('❌ [AUTO-TRANSLATE] 對接失敗:', err);
        setResolvedNodeId('');
        setResolvedLinkerId('');
        setResolvedLinkerId2('');
        setPairingCandidates([]);
        setPairingStatus('failed');
        setPairingMessage(getApiErrorMessage(err));
      } finally {
        setTranslationLoading(false);
      }
    };

    autoTranslate();
  }, [structuredProposal, chemicals, proposal, extractMetalAndLinkers, isDemoStage]);

  const onRunScreening = async () => {
    const node_id = resolvedNodeId;
    const linker_id = resolvedLinkerId;
    const linker_id_2 = resolvedLinkerId2;

    if (!node_id || !linker_id) {
      return message.warning('缺少自動對接的金屬節點或配體代號，無法執行篩選。');
    }

    if (isDemoStage('mock_property_prediction')) {
      const generatorJob = await createCifGeneratorJob({
        node_id: 'N409',
        linker_id: 'N10',
        topology: null,
        max_results: 10,
      });
      const generatorRunDetails = await getRunStatus(generatorJob.job_id);
      const demoArtifacts = generatorRunDetails.artifacts || [];

      if (
        generatorJob.status !== 'succeeded'
        || generatorRunDetails.status !== 'succeeded'
        || demoArtifacts.length !== 10
        || !demoArtifacts.every((artifact, index) => artifact.artifact_id === `demo-cif-${String(index + 1).padStart(2, '0')}`)
      ) {
        throw new Error('Demo CIF generator did not return the required 10 synthetic artifacts.');
      }

      setProposalState({
        screeningLoading: false,
        screeningStep: 'predicting',
        screeningProgress: 100,
        screeningError: '',
        screeningResults: DEMO_SCREENING_RESULTS.map((record, index) => ({
          ...record,
          artifact_id: `demo-cif-${String(index + 1).padStart(2, '0')}`,
          generator_run_id: generatorJob.job_id,
          filename: demoArtifacts[index].filename,
        }))
      });
      message.success('Demo property prediction completed.');
      return;
    }

    setProposalState({
      screeningLoading: true,
      screeningStep: 'assembling',
      screeningProgress: 10,
      screeningError: '',
      screeningResults: []
    });

    // 只有當 linker_id_2 存在且與 linker_id 不同時，才進行雙通道預測
    const isDualChannel = linker_id_2 && linker_id_2 !== linker_id;

    const maxResultsSetting = parseInt(localStorage.getItem('mof_max_results') || '10', 10);
    const maxResultsEach = isDualChannel ? Math.max(2, Math.floor(maxResultsSetting / 2)) : maxResultsSetting;
    const profileId = localStorage.getItem('mof_selected_profile_id') || 'co2-298k-015bar';
    const customCkptPath = localStorage.getItem('mof_selected_custom_ckpt') || '';

    const runSingleChannel = async (lid, maxRes, channelName) => {
      console.log(`🔍 [SCREENING-${channelName}] 開始幾何相容性比對...`, { node_id, lid });
      const compatibleRes = await getCifGeneratorTopologies(node_id, lid);
      const compatible_topologies = Array.isArray(compatibleRes) ? compatibleRes : (compatibleRes.topologies || []);
      console.log(`✅ [SCREENING-${channelName}] 相容拓撲列表:`, compatible_topologies);

      if (!compatible_topologies || compatible_topologies.length === 0) {
        throw new Error(`未找到與配體 ${lid} 幾何相容的拓撲。`);
      }

      // 啟動幾何組裝
      const screeningRes = await runProposalScreening({
        nodeId: node_id,
        linkerId: lid,
        topology: undefined,
        maxResults: maxRes
      });

      const pormakeRunId = screeningRes.generator_job_id;
      console.log(`🚀 [SCREENING-${channelName}] 幾何組裝任務啟動:`, pormakeRunId);

      let pormakeSucceeded = false;
      let pormakeRunDetails = null;

      // 輪詢 pormake 狀態
      for (let i = 0; i < 220; i++) {
        await new Promise(resolve => setTimeout(resolve, 1500));
        const statusRes = await getRunStatus(pormakeRunId);

        // 只有單通道時更新進度，雙通道由主函數更新
        if (!isDualChannel) {
          setProposalState({ screeningProgress: Math.min(50, screeningProgress + 1) });
        }

        if (statusRes.status === 'succeeded') {
          pormakeSucceeded = true;
          pormakeRunDetails = statusRes;
          break;
        } else if (statusRes.status === 'failed') {
          throw new Error(`[幾何組裝-${channelName}] 失敗: ` + (statusRes.message || '未知錯誤'));
        }
      }

      if (!pormakeSucceeded) {
        throw new Error(`[幾何組裝-${channelName}] 超時`);
      }

      if (!isDualChannel) {
        setProposalState({
          screeningProgress: 60,
          screeningStep: 'predicting'
        });
      }

      // 啟動性質預測
      const formData = new FormData();
      formData.append('profile_id', profileId);
      formData.append('generator_run_id', pormakeRunId);

      if (customCkptPath) {
        formData.append('custom_checkpoint_path', customCkptPath);
        formData.append('custom_target_property', localStorage.getItem('mof_selected_custom_property') || '');
        formData.append('custom_condition', localStorage.getItem('mof_selected_custom_condition') || '');
        formData.append('custom_unit', localStorage.getItem('mof_selected_custom_unit') || '');
        formData.append('custom_mean', localStorage.getItem('mof_selected_custom_mean') || '0');
        formData.append('custom_std', localStorage.getItem('mof_selected_custom_std') || '1');
      }

      console.log(`🚀 [SCREENING-${channelName}] 啟動性質預測任務...`);
      const predictorRes = await createPropertyPredictorJob(formData);
      const predictorJobId = predictorRes.job_id;

      let predictorSucceeded = false;
      let predictorRunDetails = null;

      // 輪詢 predictor
      for (let i = 0; i < 420; i++) {
        await new Promise(resolve => setTimeout(resolve, 1500));
        const jobStatusRes = await getJobStatus(predictorJobId);

        if (!isDualChannel) {
          setProposalState({ screeningProgress: Math.min(95, screeningProgress + 1) });
        }

        if (jobStatusRes.status === 'succeeded') {
          predictorSucceeded = true;
          predictorRunDetails = await getRunStatus(predictorJobId);
          break;
        } else if (jobStatusRes.status === 'failed' || jobStatusRes.status === 'cancelled') {
          throw new Error(`[性質預測-${channelName}] 失敗: ` + (jobStatusRes.message || '未知錯誤'));
        }
      }

      if (!predictorSucceeded) {
        throw new Error(`[性質預測-${channelName}] 超時`);
      }

      // 解析結果
      return (predictorRunDetails.artifacts || [])
        .filter(a => a.artifact_id !== 'predictions-csv')
        .map(art => {
          const parts = art.filename.replace('.cif', '').split('_');
          return {
            node_id: art.node_catalog_id || parts[1] || node_id,
            linker_id: art.linker_catalog_id || parts[2] || lid,
            topology: art.topology || parts[0] || 'unknown',
            uptake: art.predicted_value,
            unit: art.unit || 'mmol/g',
            artifact_id: art.artifact_id,
            generator_run_id: pormakeRunId
          };
        });
    };

    try {
      if (isDualChannel) {
        // 雙配體並行預測
        setProposalState({
          screeningStep: 'assembling',
          screeningProgress: 30
        });

        // 啟動並行任務
        const [res1, res2] = await Promise.all([
          runSingleChannel(linker_id, maxResultsEach, '配體1通道'),
          runSingleChannel(linker_id_2, maxResultsEach, '配體2通道')
        ]);

        setProposalState({
          screeningProgress: 100,
          screeningResults: [...res1, ...res2]
        });
        message.success('混合配體理論性質篩選完成！');
      } else {
        // 單配體正常預測
        setProposalState({
          screeningStep: 'assembling',
          screeningProgress: 20
        });
        const res = await runSingleChannel(linker_id, maxResultsSetting, '單通道');
        setProposalState({
          screeningProgress: 100,
          screeningResults: res
        });
        message.success('幾何組裝與性能篩選完成！');
      }
    } catch (err) {
      console.error('❌ [SCREENING] 篩選失敗:', err);
      setProposalState({
        screeningError: err.message || '未知錯誤',
        screeningLoading: false
      });
    } finally {
      setProposalState({ screeningLoading: false });
    }
  };

  const onViewCifStructure = async (generatorRunId, artifactId, topology, nodeId, linkerId, artifactFilename) => {
    if (generatorRunId === 'demo-pormake-run') {
      message.info('Demo CIF preview uses the fixed N409 + N10 fixture.');
      return;
    }
    setLoadingCifId(artifactId);
    try {
      const text = await getRunArtifactText(generatorRunId, artifactId);
      navigate('/mof', {
        state: {
          tab: 'viewer',
          cifText: text,
          artifactId,
          filename: artifactFilename || `${topology}_${nodeId}_${linkerId}.cif`
        }
      });
    } catch (err) {
      console.error('Failed to view CIF:', err);
      message.error('無法讀取晶體結構檔案');
    } finally {
      setLoadingCifId('');
    }
  };

  const onViewXrd = (generatorRunId, artifactId, topology, nodeId, linkerId) => {
    if (generatorRunId === 'demo-pormake-run') {
      message.info('Demo XRD preview is intentionally deterministic.');
      return;
    }
    navigate('/mof', {
      state: {
        tab: 'xrd',
        runId: generatorRunId,
        artifactId,
        topology,
        nodeId,
        linkerId,
        autoRun: true
      }
    });
  };

  const hasResult = useMemo(
    () => Boolean(proposal) || (chemicals?.length || 0) > 0 || (citations?.length || 0) > 0,
    [proposal, chemicals, citations]
  );

  // 設置文字反白模式
  useEffect(() => {
    setMode('make proposal');
  }, [setMode]);

  // 同步表單數據
  useEffect(() => {
    if (formData.goal !== form.getFieldValue('goal')) {
      form.setFieldsValue(formData);
    }
  }, [formData, form]);

  // 設置文字反白功能的修改回調
  useEffect(() => {
    setReviseCallback((result) => {
      console.log('🔍 [PROPOSAL] 文字反白修改回調被調用');
      console.log('🔍 [PROPOSAL] result:', result);
      console.log('🔍 [PROPOSAL] result.answer:', result.answer);
      console.log('🔍 [PROPOSAL] result.structured_proposal:', result.structured_proposal);
      console.log('🔍 [PROPOSAL] result.structured_experiment:', result.structured_experiment);

      // 根據互動類型處理不同的修改
      if (result.interaction_type === 'revise') {
        if (result.structured_proposal) {
          // 修改提案
          setProposalResult({
            proposal: result.answer || '',
            structuredProposal: result.structured_proposal,
            chemicals: result.chemicals || [],
            notFound: result.not_found || [],
            citations: result.citations || [],
            chunks: result.chunks || [],
            experimentDetail: '', // 清空實驗細節
            structuredExperiment: null // 清空結構化實驗細節
          });
        } else if (result.structured_experiment) {
          // 修改實驗細節
          setProposalExperiment({
            experimentDetail: result.answer || '',
            structuredExperiment: result.structured_experiment,
            citations: result.citations || []
          });
        }

        // 更新文字反白功能的數據
        setTextHighlightProposal(result.answer || '', result.chunks || []);
        setText(result.answer || '');

        console.log('✅ [PROPOSAL] 文字反白修改已應用');
        console.log('✅ [PROPOSAL] 修改類型:', result.structured_proposal ? 'proposal' : 'experiment');
      }
    });
  }, [setReviseCallback, setTextHighlightProposal, setText, setProposalResult, setProposalExperiment]);

  // 監控 chemicals 狀態變化
  useEffect(() => {
    console.log('🔍 [PROPOSAL] chemicals 狀態變化:', chemicals);
    console.log('🔍 [PROPOSAL] chemicals 長度:', chemicals.length);
    if (chemicals.length > 0) {
      console.log('🔍 [PROPOSAL] 第一個化學品:', chemicals[0]);
      console.log('🔍 [PROPOSAL] 第一個化學品的鍵:', Object.keys(chemicals[0]));
    }
  }, [chemicals]);

  const showError = (e, fallbackMsg) => {
    message.error(getApiErrorMessage(e, fallbackMsg));
  };

  const onGenerate = async () => {
    const goal = form.getFieldValue('goal');
    const formRetrievalCount = form.getFieldValue('retrievalCount') || retrievalCount;
    const formMofLinkerMode = form.getFieldValue('mofLinkerMode') || mofLinkerMode;
    if (!goal) return message.warning('請輸入研究目標');

    // 保存表單數據到全局狀態
    setProposalFormData({ goal, retrievalCount: formRetrievalCount, mofLinkerMode: formMofLinkerMode });

    // 生成唯一的請求 ID
    const requestId = Math.random().toString(36).substr(2, 8);
    const startTime = Date.now();

    console.log(`🚀 [FRONTEND-${requestId}] ========== 開始生成提案 ==========`);
    console.log(`🚀 [FRONTEND-${requestId}] 時間戳: ${new Date().toLocaleString()}`);
    console.log(`🚀 [FRONTEND-${requestId}] 研究目標: ${goal}`);
    console.log(`🚀 [FRONTEND-${requestId}] 檢索數量: ${formRetrievalCount}`);
    console.log(`🚀 [FRONTEND-${requestId}] loading 狀態: ${loading}`);

    setProposalState({
      screeningResults: [],
      screeningError: '',
      screeningProgress: 0
    });
    setLoading(true);
    try {
      if (isDemoStage('mock_proposal')) {
        const data = createDemoProposal(goal);

        setProposalResult({
          proposal: data.proposal,
          chemicals: data.chemicals,
          notFound: data.not_found,
          citations: data.citations,
          chunks: data.chunks,
          experimentDetail: '',
          structuredProposal: data.structured_proposal,
          structuredExperiment: null,
          retrievalCount: formRetrievalCount,
          mofLinkerMode: formMofLinkerMode,
        });
        setTextHighlightProposal(data.proposal, data.chunks);
        setText(data.proposal);
        message.success('Demo proposal generated successfully.');
        return;
      }

      console.log(`🔍 [FRONTEND-${requestId}] 發送 API 請求...`);
      const data = await generateProposal({
        researchGoal: goal,
        retrievalCount: formRetrievalCount,
        mofLinkerMode: formMofLinkerMode,
      });

      const endTime = Date.now();
      const duration = endTime - startTime;

      console.log(`✅ [FRONTEND-${requestId}] ========== API 響應成功 ==========`);
      console.log(`✅ [FRONTEND-${requestId}] 總耗時: ${duration}ms`);
      console.log(`✅ [FRONTEND-${requestId}] 提案長度: ${data.proposal?.length || 0}`);
      console.log(`✅ [FRONTEND-${requestId}] 化學品數量: ${data.chemicals?.length || 0}`);
      console.log(`✅ [FRONTEND-${requestId}] 引用數量: ${data.citations?.length || 0}`);
      console.log(`✅ [FRONTEND-${requestId}] 文檔塊數量: ${data.chunks?.length || 0}`);

      // 使用全局狀態管理更新結果
      setProposalResult({
        proposal: data.proposal || '',
        chemicals: data.chemicals || [],
        notFound: data.not_found || [],
        citations: data.citations || [],
        chunks: data.chunks || [],
        experimentDetail: '',
        structuredProposal: data.structured_proposal || null,
        structuredExperiment: null,
        retrievalCount: formRetrievalCount,
        mofLinkerMode: formMofLinkerMode
      });

      // 設置文字反白功能的數據
      setTextHighlightProposal(data.proposal || '', data.chunks || []);
      setText(data.proposal || '');

      console.log(`✅ [FRONTEND-${requestId}] 狀態更新完成`);

    } catch (e) {
      const endTime = Date.now();
      const duration = endTime - startTime;

      console.error(`❌ [FRONTEND-${requestId}] ========== 生成失敗 ==========`);
      console.error(`❌ [FRONTEND-${requestId}] 總耗時: ${duration}ms`);
      console.error(`❌ [FRONTEND-${requestId}] 錯誤:`, e);

      showError(e, '生成提案失敗');
    } finally {
      setLoading(false);
      console.log(`🔚 [FRONTEND-${requestId}] loading 狀態設為 false`);
    }
  };



  const onRevise = useCallback(async () => {
    console.log('🔍 [PROPOSAL] onRevise triggered via CLICK');

    // Fallback: 如果 state 為空，嘗試從 ref 讀取
    let currentFeedback = reviseFeedback;
    if (!currentFeedback && reviseInputRef.current) {
      try {
        // AntD TextArea ref structure might vary, try standard access
        currentFeedback = reviseInputRef.current.resizableTextArea?.textArea.value ||
          reviseInputRef.current.value;
        console.log('⚠️ [PROPOSAL] Used ref fallback for feedback:', currentFeedback);
      } catch (err) {
        console.error('Error reading ref:', err);
      }
    }

    console.log('🔍 [PROPOSAL] reviseFeedback state:', reviseFeedback);
    console.log('🔍 [PROPOSAL] Final feedback to use:', currentFeedback);

    if (!currentFeedback) {
      console.warn('⚠️ [PROPOSAL] No feedback found');
      return message.warning('請輸入修訂意見');
    }

    setProposalState({
      screeningResults: [],
      screeningError: '',
      screeningProgress: 0
    });
    setLoading(true);
    try {
      if (isDemoStage('mock_generate_new_idea')) {
        const data = createDemoRevision(currentFeedback);

        setProposalResult({
          proposal: data.proposal,
          chemicals: data.chemicals,
          notFound: data.not_found,
          citations: data.citations,
          chunks: data.chunks,
          experimentDetail: '',
          structuredProposal: data.structured_proposal,
          structuredExperiment: null,
          mofLinkerMode,
          showReviseInput: false,
          reviseFeedback: '',
        });
        setTextHighlightProposal(data.proposal, data.chunks);
        setText(data.proposal);
        message.success('Demo proposal revision completed.');
        return;
      }

      console.log('🔍 [PROPOSAL] Sending revise request to backend...');
      const data = await reviseProposal({
        originalProposal: proposal,
        userFeedback: currentFeedback,
        chunks,
        mofLinkerMode,
      });
      console.log('✅ [PROPOSAL] Revise response received:', data);

      // 使用全局狀態管理更新結果
      setProposalResult({
        proposal: data.proposal || '',
        chemicals: data.chemicals || [],
        notFound: data.not_found || [],
        citations: data.citations || [],
        chunks: data.chunks || [],
        experimentDetail: '',
        structuredProposal: data.structured_proposal || null,
        structuredExperiment: null,
        mofLinkerMode: mofLinkerMode,
        showReviseInput: false, // 隱藏修訂輸入框
        reviseFeedback: '' // 清空修訂意見
      });



      // 更新文字反白功能的數據
      setTextHighlightProposal(data.proposal || '', data.chunks || []);
      setText(data.proposal || '');

      message.success('提案修訂成功！');
    } catch (e) {
      console.error('❌ [PROPOSAL] Revise failed:', e);
      showError(e, '修訂失敗');
    } finally {
      setLoading(false);
    }
  }, [reviseFeedback, proposal, chunks, setProposalResult, setTextHighlightProposal, setText, isDemoStage, mofLinkerMode]);

  // Expose onRevise for debugging
  useEffect(() => {
    window.debugOnRevise = onRevise;
  }, [onRevise]);


  const onShowReviseInput = () => {
    if (showReviseInput) {
      // 如果已經顯示，則直接隱藏
      setProposalState({ showReviseInput: false, reviseFeedback: '' });
      setIsReviseInputFocused(false);
    } else {
      // 如果未顯示，則顯示並聚焦
      setProposalState({ showReviseInput: true });
      // 使用 setTimeout 確保 DOM 更新後再聚焦
      setTimeout(() => {
        reviseInputRef.current?.focus();
      }, 0);
    }
  };

  const onGenerateExperimentDetail = async () => {
    if (!proposal) return message.warning('請先生成或修訂提案');
    setLoading(true);
    try {
      const data = isDemoStage('mock_experiment_detail')
        ? getDemoExperimentDetailByProposal(proposal)
        : await generateExperimentDetail({ proposal, chunks });

      // 使用全局狀態管理更新實驗細節
      setProposalExperiment({
        experimentDetail: data.experiment_detail || '',
        structuredExperiment: data.structured_experiment || null,
        citations: data.citations || citations // 如果有新的citations則更新，否則保留原有的
      });

      // 顯示重試信息
      if (data.retry_info) {
        console.log('🔄 重試信息:', data.retry_info);
        if (data.retry_info.retry_count > 0) {
          message.info(`重試 ${data.retry_info.retry_count} 次，最終使用 ${data.retry_info.final_tokens} tokens`);
        }
      }
    } catch (e) {
      showError(e, '生成實驗細節失敗');
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const onDownloadDocx = async () => {
    if (!proposal) return message.warning('請先生成提案');
    setLoading(true);
    try {
      console.log('🔍 FRONTEND DEBUG: 開始下載 DOCX');
      console.log('🔍 FRONTEND DEBUG: proposal 長度:', proposal.length);
      console.log('🔍 FRONTEND DEBUG: chemicals 數量:', chemicals.length);
      console.log('🔍 FRONTEND DEBUG: experiment_detail 長度:', experimentDetail.length);
      console.log('🔍 FRONTEND DEBUG: citations 數量:', citations.length);

      // 清理 markdown 格式的函數
      const cleanMarkdownText = (text) => {
        if (!text) return "";
        return text
          .replace(/\*\*(.*?)\*\*/g, '$1') // 移除粗體標記
          .replace(/\*(.*?)\*/g, '$1') // 移除斜體標記
          .replace(/`(.*?)`/g, '$1') // 移除代碼標記
          .replace(/^#+\s*(.*)$/gm, '$1') // 移除標題標記
          .replace(/^\s*[-*+]\s+/gm, '- ') // 統一項目符號
          .replace(/^\s*\d+\.\s+/gm, (match) => match.replace(/^\s*\d+\.\s+/, '')) // 移除編號
          .replace(/\n\s*\n\s*\n/g, '\n\n') // 移除多餘空行
          .replace(/\n\s*\*\*/g, '\n') // 移除粗體前的換行
          .replace(/\*\*\s*\n/g, '\n'); // 移除粗體後的換行
      };

      const blob = await downloadProposalDocx({
        proposal: cleanMarkdownText(proposal),
        chemicals,
        notFound,
        experimentDetail: cleanMarkdownText(experimentDetail),
        citations,
      });

      // 創建下載鏈接
      console.log('🔍 FRONTEND DEBUG: blob 大小:', blob.size);

      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'proposal_report.docx';
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      message.success('檔案下載成功！');
    } catch (e) {
      console.error('❌ FRONTEND DEBUG: 下載失敗:', e);
      showError(e, '下載失敗');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <Title level={2}>
        研究提案
        {demoConfig.enabled && (
          <Tag color="purple" style={{ marginLeft: 12, verticalAlign: 'middle' }}>
            演示模式
          </Tag>
        )}
      </Title>
      <Paragraph>輸入研究目標，由 AI 結合文獻資料庫自動生成完整的實驗設計與提案報告。</Paragraph>
      {demoConfig.enabled && (
        <Alert
          type="warning"
          showIcon
          message="Illustrative Demo content"
          description="Demo proposals, revisions, experiment text, chemical safety graphics, and screening values are synthetic/non-experimental examples. They are not safety instructions, calibrated predictions, or validated laboratory procedures."
          style={{ marginBottom: 24 }}
        />
      )}

      <Card title="新建研究提案" style={{ marginBottom: 24, position: 'relative' }}>
        <Form form={form} layout="vertical" initialValues={{ retrievalCount, ...formData }}>
          <Form.Item name="goal" label="研究目標" rules={[{ required: true, message: '請輸入您的研究目標' }]}>
            <TextArea
              rows={hasGeneratedContent && !isTextareaFocused ? 1 : 12}
              placeholder="請輸入您的研究目標（例如：優化 Cu-BTC 的合成製程以提高 CO2 吸附性能...）"
              onFocus={() => setIsTextareaFocused(true)}
              onBlur={() => setIsTextareaFocused(false)}
              onChange={(e) => setProposalFormData({ goal: e.target.value })}
            />
          </Form.Item>

          <Form.Item
            name="retrievalCount"
            label="參考文獻檢索數量"
          >
            <Select
              style={{ width: 220 }}
              onChange={(value) => setProposalFormData({ retrievalCount: value })}
            >
              <Option value={1}>1 篇文獻 (開發測試)</Option>
              <Option value={5}>5 篇文獻 (快速模式)</Option>
              <Option value={10}>10 篇文獻 (均衡模式)</Option>
              <Option value={15}>15 篇文獻 (詳盡模式)</Option>
              <Option value={20}>20 篇文獻 (完整模式)</Option>
            </Select>
          </Form.Item>



          <Space wrap>
            <Button type="primary" size="large" onClick={onGenerate} loading={loading}>
              ✍️ 開始生成研究提案
            </Button>
          </Space>
        </Form>

        {/* 下載按鈕 - 只在有提案時顯示 */}
        {proposal && (
          <div style={{
            position: 'absolute',
            bottom: '16px',
            right: '16px'
          }}>
            <Button
              type="primary"
              size="large"
              onClick={onDownloadDocx}
              loading={loading}
              icon="📥"
            >
              下載 Word 提案檔 (DOCX)
            </Button>
          </div>
        )}
      </Card>

      {hasResult && (
        <>
          {/* 修訂說明卡片 - 僅在修訂提案時顯示 */}
          {structuredProposal?.revision_explanation && (
            <Collapse
              defaultActiveKey={['revision']}
              style={{ marginBottom: 16 }}
              items={[
                {
                  key: 'revision',
                  label: <span style={{ fontWeight: 700, fontSize: 27 }}>📝 修訂說明</span>,
                  children: (
                    <div style={{
                      whiteSpace: 'pre-wrap',
                      fontSize: '16px',
                      lineHeight: '1.6',
                      wordBreak: 'break-word',
                      overflowWrap: 'break-word',
                      maxWidth: '100%',
                      width: '100%',
                      fontWeight: 'normal'
                    }}>
                      {structuredProposal.revision_explanation}
                    </div>
                  ),
                },
              ]}
            />
          )}

          {/* 提案卡片 - 第一次提案和修訂提案都顯示 */}
          <Collapse
            defaultActiveKey={['proposal']}
            style={{ marginBottom: 16 }}
            items={[
              {
                key: 'proposal',
                label: <span style={{ fontWeight: 700, fontSize: 27 }}>🤖 AI 研究提案</span>,
                children: (
                  <div
                    data-area="proposal"
                    data-testid="proposal-content"
                    onMouseUp={handleTextSelection}
                    style={{
                      whiteSpace: 'pre-wrap',
                      fontSize: '16px',
                      lineHeight: '1.6',
                      wordBreak: 'break-word',
                      overflowWrap: 'break-word',
                      maxWidth: '100%',
                      width: '100%',
                      fontWeight: 'normal',
                      cursor: 'text'
                    }}
                  >
                    {structuredProposal ? (
                      // 渲染結構化提案數據
                      <>
                        {/* 提案標題 */}
                        {structuredProposal.proposal_title && (
                          <>
                            <div style={{
                              fontSize: '24px',
                              fontWeight: 'bold',
                              color: '#1890ff',
                              marginTop: '16px',
                              marginBottom: '8px'
                            }}>
                              Proposal
                            </div>
                            <div style={{ marginBottom: '16px' }}>
                              {structuredProposal.proposal_title}
                            </div>
                          </>
                        )}

                        {/* 研究需求 */}
                        {structuredProposal.need && (
                          <>
                            <div style={{
                              fontSize: '24px',
                              fontWeight: 'bold',
                              color: '#1890ff',
                              marginTop: '12px',
                              marginBottom: '6px'
                            }}>
                              Need
                            </div>
                            <div style={{ marginBottom: '16px' }}>
                              {structuredProposal.need}
                            </div>
                          </>
                        )}

                        {/* 解決方案 */}
                        {structuredProposal.solution && (
                          <>
                            <div style={{
                              fontSize: '24px',
                              fontWeight: 'bold',
                              color: '#1890ff',
                              marginTop: '12px',
                              marginBottom: '6px'
                            }}>
                              Solution
                            </div>
                            <div style={{ marginBottom: '16px' }}>
                              {structuredProposal.solution}
                            </div>
                          </>
                        )}

                        {/* 差異化 */}
                        {structuredProposal.differentiation && (
                          <>
                            <div style={{
                              fontSize: '24px',
                              fontWeight: 'bold',
                              color: '#1890ff',
                              marginTop: '12px',
                              marginBottom: '6px'
                            }}>
                              Differentiation
                            </div>
                            <div style={{ marginBottom: '16px' }}>
                              {structuredProposal.differentiation}
                            </div>
                          </>
                        )}

                        {/* 效益 */}
                        {structuredProposal.benefit && (
                          <>
                            <div style={{
                              fontSize: '24px',
                              fontWeight: 'bold',
                              color: '#1890ff',
                              marginTop: '12px',
                              marginBottom: '6px'
                            }}>
                              Benefit
                            </div>
                            <div style={{ marginBottom: '16px' }}>
                              {structuredProposal.benefit}
                            </div>
                          </>
                        )}

                        {/* 實驗概述 */}
                        {structuredProposal.experimental_overview && (
                          <>
                            <div style={{
                              fontSize: '24px',
                              fontWeight: 'bold',
                              color: '#1890ff',
                              marginTop: '12px',
                              marginBottom: '6px'
                            }}>
                              Experimental Overview
                            </div>
                            <div style={{ marginBottom: '16px' }}>
                              {structuredProposal.experimental_overview}
                            </div>
                          </>
                        )}
                      </>
                    ) : (
                      // 渲染傳統文本格式（作為 fallback）
                      proposal
                        .replace(/\*\*(.*?)\*\*/g, '$1') // 移除粗體標記
                        .replace(/\*(.*?)\*/g, '$1') // 移除斜體標記
                        .replace(/`(.*?)`/g, '$1') // 移除代碼標記
                        .replace(/^#+\s*(.*)$/gm, '$1') // 移除標題標記
                        .replace(/^\s*[-*+]\s+/gm, '- ') // 統一項目符號
                        .replace(/^\s*\d+\.\s+/gm, (match) => match.replace(/^\s*\d+\.\s+/, '')) // 移除編號
                        .replace(/\n\s*\n\s*\n/g, '\n\n') // 移除多餘空行
                        .replace(/\n\s*\*\*/g, '\n') // 移除粗體前的換行
                        .replace(/\*\*\s*\n/g, '\n') // 移除粗體後的換行
                        .split('\n')
                        .map((line, index) => {
                          if (line.match(/^(Revision Explanation:|Proposal:|Need:|Solution:|Differentiation:|Benefit:|Experimental overview:)/)) {
                            return (
                              <div key={index} style={{
                                fontSize: '24px',
                                fontWeight: 'bold',
                                color: '#1890ff',
                                marginTop: '16px',
                                marginBottom: '8px'
                              }}>
                                {line}
                              </div>
                            );
                          }
                          return <div key={index}>{line}</div>;
                        })
                    )}
                  </div>
                ),
              },
            ]}
          />

          {(experimentDetail || structuredExperiment) && (
            <>
              {/* 修訂說明卡片 - 僅在修訂實驗細節時顯示 */}
              {structuredExperiment?.revision_explanation && (
                <Collapse
                  defaultActiveKey={['revision']}
                  style={{ marginBottom: 16 }}
                  items={[
                    {
                      key: 'revision',
                      label: <span style={{ fontWeight: 700, fontSize: 27 }}>📝 Revision Explanation</span>,
                      children: (
                        <div style={{
                          whiteSpace: 'pre-wrap',
                          fontSize: '16px',
                          lineHeight: '1.6',
                          wordBreak: 'break-word',
                          overflowWrap: 'break-word',
                          maxWidth: '100%',
                          width: '100%',
                          fontWeight: 'normal'
                        }}>
                          {structuredExperiment.revision_explanation}
                        </div>
                      ),
                    },
                  ]}
                />
              )}

              {/* 實驗細節卡片 */}
              <Collapse
                defaultActiveKey={['experiment']}
                style={{ marginBottom: 16 }}
                items={[
                  {
                    key: 'experiment',
                    label: <span style={{ fontWeight: 700, fontSize: 27 }}>🔬 實驗步驟</span>,
                    children: (
                      <div
                        data-area="experiment"
                        data-testid="experiment-content"
                        onMouseUp={handleTextSelection}
                        style={{
                          whiteSpace: 'pre-wrap',
                          fontSize: '16px',
                          lineHeight: '1.6',
                          wordBreak: 'break-word',
                          overflowWrap: 'break-word',
                          maxWidth: '100%',
                          width: '100%',
                          fontWeight: 'normal',
                          cursor: 'text'
                        }}
                      >
                        {structuredExperiment ? (
                          // 渲染結構化實驗細節數據
                          <>
                            {/* 合成過程 */}
                            {structuredExperiment.synthesis_process && (
                              <>
                                <div style={{
                                  fontSize: '24px',
                                  fontWeight: 'bold',
                                  color: '#1890ff',
                                  marginTop: '12px',
                                  marginBottom: '6px'
                                }}>
                                  Synthesis Process
                                </div>
                                <div style={{ marginBottom: '16px' }}>
                                  {structuredExperiment.synthesis_process
                                    .replace(/^(SYNTHESIS PROCESS|Synthesis Process|合成過程)[:\s]*/i, '')
                                    .trim()}
                                </div>
                              </>
                            )}

                            {/* 材料和條件 */}
                            {structuredExperiment.materials_and_conditions && (
                              <>
                                <div style={{
                                  fontSize: '24px',
                                  fontWeight: 'bold',
                                  color: '#1890ff',
                                  marginTop: '12px',
                                  marginBottom: '6px'
                                }}>
                                  Materials and Conditions
                                </div>
                                <div style={{ marginBottom: '16px' }}>
                                  {structuredExperiment.materials_and_conditions
                                    .replace(/^(MATERIALS AND CONDITIONS|Materials and Conditions|材料和條件)[:\s]*/i, '')
                                    .trim()}
                                </div>
                              </>
                            )}

                            {/* 分析方法 */}
                            {structuredExperiment.analytical_methods && (
                              <>
                                <div style={{
                                  fontSize: '24px',
                                  fontWeight: 'bold',
                                  color: '#1890ff',
                                  marginTop: '12px',
                                  marginBottom: '6px'
                                }}>
                                  Analytical Methods
                                </div>
                                <div style={{ marginBottom: '16px' }}>
                                  {structuredExperiment.analytical_methods
                                    .replace(/^(ANALYTICAL METHODS|Analytical Methods|分析方法)[:\s]*/i, '')
                                    .trim()}
                                </div>
                              </>
                            )}

                            {/* 注意事項 */}
                            {structuredExperiment.precautions && (
                              <>
                                <div style={{
                                  fontSize: '24px',
                                  fontWeight: 'bold',
                                  color: '#1890ff',
                                  marginTop: '12px',
                                  marginBottom: '6px'
                                }}>
                                  Precautions
                                </div>
                                <div style={{ marginBottom: '16px' }}>
                                  {structuredExperiment.precautions
                                    .replace(/^(PRECAUTIONS|Precautions|注意事項)[:\s]*/i, '')
                                    .trim()}
                                </div>
                              </>
                            )}
                          </>
                        ) : (
                          // 渲染傳統文本格式（作為 fallback）
                          experimentDetail
                            .replace(/\*\*(.*?)\*\*/g, '$1') // 移除粗體標記
                            .replace(/\*(.*?)\*/g, '$1') // 移除斜體標記
                            .replace(/`(.*?)`/g, '$1') // 移除代碼標記
                            .replace(/^#{3,}\s*(.*)$/gm, '$1') // 只移除 ### 及以上的標題標記，保留 ##
                            .replace(/^\s*[-*+]\s+/gm, '- ') // 統一項目符號
                            .replace(/^\s*\d+\.\s+/gm, (match) => match.replace(/^\s*\d+\.\s+/, '')) // 移除編號
                            .replace(/\n\s*\n\s*\n/g, '\n\n') // 移除多餘空行
                            .replace(/\n\s*\*\*/g, '\n') // 移除粗體前的換行
                            .replace(/\*\*\s*\n/g, '\n') // 移除粗體後的換行
                            .split('\n')
                            .map((line, index) => {
                              // 檢查是否為實驗細節的主要標題行（與提案區域相同的樣式）
                              if (line.match(/^(##\s*)?(合成過程|材料和條件|分析方法|注意事項|Synthesis Process|Materials and Conditions|Analytical Methods|Precautions|實驗細節|Experimental Details)/)) {
                                return (
                                  <div key={index} style={{
                                    fontSize: '24px',
                                    fontWeight: 'bold',
                                    color: '#1890ff',
                                    marginTop: '16px',
                                    marginBottom: '8px'
                                  }}>
                                    {line.replace(/^##\s*/, '')}
                                  </div>
                                );
                              }
                              // 檢查是否為子標題行（保持原有的樣式）
                              if (line.match(/^(\d+\)\s*)?(前處理與配方計算|微波輔助骨架合成|活化|微波促進的後合成接枝|Pre-treatment and Formulation Calculation|Microwave-assisted Framework Synthesis|Activation|Microwave-promoted Post-synthesis Grafting|材料\(IUPAC 名稱以便辨識\)|Materials \(IUPAC names for identification\))/)) {
                                return (
                                  <div key={index} style={{
                                    fontSize: '20px',
                                    fontWeight: 'bold',
                                    color: '#262626',
                                    marginTop: '12px',
                                    marginBottom: '6px'
                                  }}>
                                    {line}
                                  </div>
                                );
                              }
                              return <div key={index} style={{ fontWeight: 'normal' }}>{line}</div>;
                            })
                        )}
                      </div>
                    ),
                  },
                ]}
              />
            </>
          )}

          <Collapse
            defaultActiveKey={['chemicals']}
            style={{ marginBottom: 16 }}
            items={[
              {
                key: 'chemicals',
                label: <span style={{ fontWeight: 700, fontSize: 27 }}>🧪 使用化學品</span>,
                children: (
                  <>
                    <List
                      dataSource={chemicals}
                      renderItem={(c, index) => {
                        console.log(`🔍 [CHEMICAL-SUMMARY] 渲染化學品 ${index}:`, c);
                        console.log(`🔍 [CHEMICAL-SUMMARY] 化學品 ${index} 的鍵:`, Object.keys(c));
                        console.log(`🔍 [CHEMICAL-SUMMARY] 化學品 ${index} 是否有 svg_structure:`, 'svg_structure' in c);
                        console.log(`🔍 [CHEMICAL-SUMMARY] 化學品 ${index} 是否有 png_structure:`, 'png_structure' in c);

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
                                    <div
                                      onMouseUp={handleTextSelection}
                                      style={{
                                        fontSize: '14px',
                                        lineHeight: '1.5',
                                        wordBreak: 'break-word',
                                        overflowWrap: 'break-word',
                                        cursor: 'text'
                                      }}
                                    >
                                      <div><strong>Formula:</strong> <code>{c.formula || '-'}</code></div>
                                      <div><strong>MW:</strong> <code>{c.weight || '-'}</code></div>
                                      <div><strong>Boiling Point:</strong> <code>{c.boiling_point_c || '-'}</code></div>
                                      <div><strong>Melting Point:</strong> <code>{c.melting_point_c || '-'}</code></div>
                                      <div><strong>CAS No.:</strong> <code>{c.cas || '-'}</code></div>
                                      <div><strong>SMILES:</strong> <code>{c.smiles || '-'}</code></div>
                                    </div>
                                  </div>

                                  {/* Safety Icons */}
                                  <div style={{ flex: '0 0 150px' }}>
                                    <Text strong style={{ fontSize: '14px', marginBottom: '8px', display: 'block' }}>
                                      Handling Safety
                                    </Text>
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                      {/* NFPA Diamond */}
                                      {c.safety_icons?.nfpa_image && (
                                        <img
                                          src={c.safety_icons.nfpa_image}
                                          alt="NFPA"
                                          style={{ width: '50px', height: '50px' }}
                                        />
                                      )}
                                      {/* GHS Icons */}
                                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', maxWidth: '120px' }}>
                                        {c.safety_icons?.ghs_icons?.map((icon, index) => (
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
                      grid={{ gutter: 16, column: 2 }}
                    />
                    {!!notFound.length && (
                      <>
                        <Divider />
                        <Paragraph style={{ color: '#ff4d4f', fontSize: '16px' }}>
                          ⚠️ Not Found: {notFound.join(', ')}
                        </Paragraph>
                      </>
                    )}
                  </>
                ),
              },
            ]}
          />

          {/* Action Buttons - 只在有結果時顯示 */}
          <Card style={{ marginBottom: 16 }}>
            <Space wrap>
              <Button
                size="large"
                onClick={onShowReviseInput}
                loading={loading}
                type={showReviseInput ? "primary" : "default"}
              >
                💡 Generate New Idea
              </Button>
              <Button size="large" onClick={onGenerateExperimentDetail} loading={loading}>
                ✅ Accept & Generate Experiment Detail
              </Button>
            </Space>

            {/* 修訂輸入框 - 點擊 Generate New Idea 後顯示 */}
            {showReviseInput && (
              <div style={{ marginTop: 16, padding: 16, backgroundColor: '#f5f5f5', borderRadius: 6 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <Text strong>Enter your revision idea:</Text>
                  <Button
                    type="text"
                    size="small"
                    onClick={() => {
                      setProposalState({ showReviseInput: false, reviseFeedback: '' });
                    }}
                  >
                    ✕ Close
                  </Button>
                </div>
                <Space>
                  <TextArea
                    placeholder="Your revision idea"
                    value={reviseFeedback}
                    onChange={(e) => setProposalState({ reviseFeedback: e.target.value })}
                    rows={isReviseInputFocused ? 6 : 2}
                    style={{ width: 800 }}
                    onFocus={() => setIsReviseInputFocused(true)}
                    onBlur={() => {
                      setIsReviseInputFocused(false);
                    }}
                    ref={reviseInputRef} // 將 ref 綁定到 TextArea
                  />
                  <Button
                    type="primary"
                    size="large"
                    onClick={onRevise}
                    loading={loading}
                    disabled={loading}
                  >
                    Revise it!
                  </Button>
                </Space>
              </div>
            )}
          </Card>

          {extractedMetalElement && extractedLinkerName ? (
            <Collapse
              defaultActiveKey={['property_prediction']}
              style={{ marginBottom: 16 }}
              items={[
                {
                  key: 'property_prediction',
                  label: <span style={{ fontWeight: 700, fontSize: 27 }}>💡 MOF 性質預測</span>,
                  children: (
                    <div style={{ padding: '8px 0' }}>
                      {translationLoading ? (
                        <div style={{ padding: '24px', textAlign: 'center' }}>
                          <Spin tip="正在自動對接 PORMAKE 資料庫代號..." size="large" />
                        </div>
                      ) : (
                        <div style={{ marginBottom: '24px' }}>
                          {/* 唯讀顯示自動擷取出的資訊 */}
                          <div style={{ display: 'flex', gap: '24px', flexWrap: 'wrap', marginBottom: '20px' }}>
                            {/* 金屬節點 */}
                            <div style={{ flex: '1 1 200px', backgroundColor: '#f9f9f9', padding: '16px', borderRadius: '6px', border: '1px solid #e8e8e8' }}>
                              <div style={{ fontWeight: 'bold', fontSize: '14px', color: '#595959', marginBottom: '8px' }}>金屬節點 (Node / Metal)</div>
                              <div style={{ fontSize: '15px', fontWeight: '500', marginBottom: '6px' }}>
                                金屬名稱: <Text strong style={{ color: '#1890ff' }}>{extractedMetalElement || '無'}</Text>
                              </div>
                              <div>
                                PORMAKE 代號: <Tag color="blue" style={{ fontSize: '13px', fontWeight: 'bold', padding: '2px 6px' }}>{resolvedNodeId || '未識別'}</Tag>
                              </div>
                            </div>

                            {/* 主要有機配體 */}
                            <div style={{ flex: '2 1 300px', backgroundColor: '#f9f9f9', padding: '16px', borderRadius: '6px', border: '1px solid #e8e8e8' }}>
                              <div style={{ fontWeight: 'bold', fontSize: '14px', color: '#595959', marginBottom: '8px' }}>有機配體1 (Main Linker / Organic)</div>
                              <div style={{ fontSize: '15px', fontWeight: '500', marginBottom: '6px' }}>
                                化學品名稱: <Text strong style={{ color: '#1890ff' }}>{extractedLinkerName || '無'}</Text>
                              </div>
                              <div style={{ marginBottom: '6px' }}>
                                PORMAKE 代號: <Tag color="green" style={{ fontSize: '13px', fontWeight: 'bold', padding: '2px 6px' }}>{resolvedLinkerId || '未識別'}</Tag>
                              </div>
                              <div style={{ fontSize: '12px', color: '#8c8c8c', wordBreak: 'break-all' }}>
                                SMILES: <code>{extractedLinkerSmiles || '無'}</code>
                              </div>
                            </div>

                            {/* 輔助有機配體 (如有) */}
                            {extractedLinkerSmiles2 && (
                              <div style={{ flex: '2 1 300px', backgroundColor: '#f9f9f9', padding: '16px', borderRadius: '6px', border: '1px solid #e8e8e8' }}>
                                <div style={{ fontWeight: 'bold', fontSize: '14px', color: '#595959', marginBottom: '8px' }}>有機配體2 (Auxiliary Linker / Organic)</div>
                                <div style={{ fontSize: '15px', fontWeight: '500', marginBottom: '6px' }}>
                                  化學品名稱: <Text strong style={{ color: '#1890ff' }}>{extractedLinkerName2 || '無'}</Text>
                                </div>
                                <div style={{ marginBottom: '6px' }}>
                                  PORMAKE 代號: <Tag color="purple" style={{ fontSize: '13px', fontWeight: 'bold', padding: '2px 6px' }}>{resolvedLinkerId2 || '已併入複合金屬節點'}</Tag>
                                </div>
                                <div style={{ fontSize: '12px', color: '#8c8c8c', wordBreak: 'break-all' }}>
                                  SMILES: <code>{extractedLinkerSmiles2 || '無'}</code>
                                </div>
                              </div>
                            )}
                          </div>

                          {pairingCandidates.length > 0 && (
                            <div style={{ marginBottom: 16 }}>
                              <Text strong>完整原子覆蓋的 PORMAKE 候選</Text>
                              <Select
                                style={{ width: '100%', marginTop: 8 }}
                                value={resolvedNodeId && resolvedLinkerId ? `${resolvedNodeId}:${resolvedLinkerId}` : undefined}
                                onChange={(value) => {
                                  const candidate = pairingCandidates.find(
                                    (item) => `${item.node_id}:${item.linker_id}` === value
                                  );
                                  setResolvedNodeId(candidate?.node_id || '');
                                  setResolvedLinkerId(candidate?.linker_id || '');
                                }}
                                options={pairingCandidates.map((candidate, index) => ({
                                  value: `${candidate.node_id}:${candidate.linker_id}`,
                                  label: `#${index + 1} ${candidate.node_id} + ${candidate.linker_id} · ${(candidate.confidence * 100).toFixed(1)}% · ${candidate.compatible_topologies.length} topologies`,
                                }))}
                              />
                              <Text type="secondary" style={{ display: 'block', marginTop: 6 }}>
                                系統自動選擇第一名；可切換其他 SBU/N/E 理論候選後再啟動篩選。
                              </Text>
                            </div>
                          )}

                          {pairingStatus && pairingStatus !== 'success' && (
                            <div style={{ marginBottom: 16, padding: 12, background: '#fffbe6', border: '1px solid #ffe58f', borderRadius: 4 }}>
                              <Text type="warning">{pairingMessage || '找不到可自動生成的 exact PORMAKE 候選。'}</Text>
                            </div>
                          )}

                          {/* 配對方法說明摘要 */}
                          <div style={{
                            width: '100%',
                            backgroundColor: '#fbfbfb',
                            padding: '14px 18px',
                            borderRadius: '6px',
                            border: '1px dashed #d9d9d9',
                            marginBottom: '16px',
                            fontSize: '13px',
                            lineHeight: '1.6',
                            color: '#595959'
                          }}>
                            <div style={{ fontWeight: 'bold', color: '#262626', marginBottom: '6px', fontSize: '14px' }}>
                              🔍 PORMAKE 資料庫自動配對機制說明
                            </div>
                            <ul style={{ paddingLeft: '18px', margin: 0, color: '#595959' }}>
                              <li>
                                <strong>多 SBU 候選</strong>：列舉 PORMAKE 中含指定金屬且能以已觀察配位 cap 解釋 linker 的節點，不將金屬元素強制對應到唯一 SBU。
                              </li>
                              <li>
                                <strong>完整圖匹配</strong>：比較元素、鍵級、配位端 cap 與 PORMAKE building block，只有 linker 重原子完整覆蓋的 <code>exact</code> 候選可生成 CIF。
                              </li>
                              <li>
                                <strong>幾何驗證</strong>：依候選配位數篩選 topology，PORMAKE 組裝後再以 connection-point RMSD 淘汰不相容結構。
                              </li>
                              <li>
                                <strong>MVP 限制</strong>：scaffold 近似不會自動剝除取代基或生成 CIF；需要完整 building block 才能進入 predictor。
                              </li>
                            </ul>
                          </div>

                          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', alignItems: 'flex-start' }}>
                            <Button
                              type="primary"
                              size="large"
                              onClick={onRunScreening}
                              loading={screeningLoading}
                              disabled={!resolvedNodeId || !resolvedLinkerId}
                            >
                              ⚡️ Start Prediction
                            </Button>

                            <div style={{ fontSize: '13px', color: '#595959', backgroundColor: '#f0f5ff', padding: '10px 16px', borderRadius: '4px', borderLeft: '4px solid #1890ff', width: '100%' }}>
                              💡 <span style={{ fontWeight: 'bold' }}>提示：</span>生成的CIF數目、性質預測器設定，將套用MOF功能分頁中的設定
                              <div style={{ marginTop: '4px', color: '#8c8c8c' }}>
                                • 當前設定最大生成 CIF 數：<Text strong>{localStorage.getItem('mof_max_results') || '10 (預設)'}</Text> 件
                                <span style={{ margin: '0 8px' }}>|</span>
                                當前設定性質預測模型：<Text strong>
                                  {(() => {
                                    const profileId = localStorage.getItem('mof_selected_profile_id') || 'co2-298k-015bar';
                                    const profileLabels = {
                                      'co2-298k-015bar': 'CO2 吸附性能預測 (298 K, 0.15 bar)',
                                      'co2-298k-1bar': 'CO2 吸附性能預測 (298 K, 1 bar)',
                                      'n2-298k-1bar': 'N2 吸附性能預測 (298 K, 1 bar)',
                                      'ch4-298k-5.8bar': 'CH4 吸附性能預測 (298 K, 5.8 bar)',
                                      'ch4-298k-65bar': 'CH4 吸附性能預測 (298 K, 65 bar)'
                                    };
                                    return profileLabels[profileId] || `${profileId} 模型`;
                                  })()}
                                </Text>
                              </div>
                            </div>
                          </div>
                        </div>
                      )}

                      {screeningLoading && (
                        <div style={{ marginTop: 16, padding: '12px 16px', backgroundColor: '#f0f9eb', borderRadius: 4, marginBottom: 16 }}>
                          <Text style={{ marginRight: 8, display: 'block', marginBottom: 8 }}>
                            {screeningStep === 'translating' && '正在對接化學描述與 PORMAKE 庫代碼 (10%)...'}
                            {screeningStep === 'assembling' && '正在使用 PORMAKE 異步拼接三維理論晶體結構 (30%)...'}
                            {screeningStep === 'predicting' && '正在使用 PMTransformer 預測氣體吸附性能 (60%)...'}
                          </Text>
                          <Progress percent={screeningProgress} status="active" strokeColor="#52c41a" />
                        </div>
                      )}

                      {screeningError && (
                        <div style={{ marginTop: 16, padding: '12px 16px', backgroundColor: '#fff2f0', border: '1px solid #ffccc7', borderRadius: 4, marginBottom: 16 }}>
                          <Text type="danger">⚠️ 篩選失敗: {screeningError}</Text>
                        </div>
                      )}

                      {screeningResults.length > 0 && (
                        <>
                          <Divider />
                          <Alert
                            type="warning"
                            showIcon
                            message="Illustrative Demo prediction"
                            description="Synthetic, non-experimental values only; not calibrated, measured, validated, or safety guidance."
                            style={{ marginBottom: 16 }}
                          />
                          <Table
                            dataSource={screeningResults}
                            rowKey={(record, idx) => `${record.topology}-${idx}`}
                            pagination={false}
                            columns={[
                              {
                                title: '金屬節點 (Node / Metal)',
                                dataIndex: 'node_id',
                                key: 'node_id',
                                render: (text) => <Text code>{text}</Text>
                              },
                              {
                                title: '有機配體 (Linker / Organic)',
                                dataIndex: 'linker_id',
                                key: 'linker_id',
                                render: (text) => <Text code>{text}</Text>
                              },
                              {
                                title: '拓撲結構 (Topology)',
                                dataIndex: 'topology',
                                key: 'topology',
                                render: (text) => <Tag color="blue">{text}</Tag>
                              },
                              {
                                title: '預測吸附量 (Uptake)',
                                dataIndex: 'uptake',
                                key: 'uptake',
                                render: (val, record) => <Text strong>{Number(val).toFixed(2)} {record.unit}</Text>
                              },
                              {
                                title: '操作',
                                key: 'actions',
                                render: (_, record) => (
                                  <Space size="middle">
                                    <Button
                                      type="link"
                                      size="small"
                                      loading={loadingCifId === record.artifact_id}
                                      onClick={() => onViewCifStructure(record.generator_run_id, record.artifact_id, record.topology, record.node_id, record.linker_id, record.filename)}
                                    >
                                      🔍 結構檢視
                                    </Button>
                                    <Button
                                      type="link"
                                      size="small"
                                      onClick={() => onViewXrd(record.generator_run_id, record.artifact_id, record.topology, record.node_id, record.linker_id)}
                                    >
                                      📈 XRD預測
                                    </Button>
                                  </Space>
                                )
                              }
                            ]}
                          />
                          <div style={{ marginTop: 16, padding: '12px 16px', backgroundColor: '#f9f9f9', borderLeft: '4px solid #1890ff', borderRadius: '0 4px 4px 0' }}>
                            <Text type="secondary" style={{ fontSize: '13px', display: 'block', lineHeight: '1.6' }}>
                              💡 <strong>系統備註：</strong>本提案系統所呈現之金屬鹽類、溶劑與溫度等文獻條件，旨在提供初步參考，並不保證在提案建議的反應條件下能直接產出此列表中的拓撲結構。真實合成受複雜熱力學與動力學控制，請使用者根據網格化學經驗，進一步優化與設計實驗條件以引導該拓撲生成。
                            </Text>
                          </div>
                        </>
                      )}
                    </div>
                  ),
                },
              ]}
            />
          ) : (
            <Card style={{ marginBottom: 16, backgroundColor: '#f0f5ff', border: '1px solid #d6e4ff', borderRadius: '8px' }}>
              <Text style={{ fontSize: '16px', color: '#1890ff', fontWeight: 500 }}>
                ℹ️ 本提案未涉及金屬有機框架 (MOF) 材料之設計，已自動略過性質預測。
              </Text>
            </Card>
          )}

          {!!citations.length && (
            <Collapse
              defaultActiveKey={['citations']}
              style={{ marginBottom: 16 }}
              items={[
                {
                  key: 'citations',
                  label: <span style={{ fontWeight: 700, fontSize: 27 }}>📚 Citations</span>,
                  children: (
                    <List
                      dataSource={citations}
                      renderItem={(c, i) => (
                        <List.Item>
                          <Text style={{
                            fontSize: '16px',
                            lineHeight: '1.6',
                            wordBreak: 'break-word',
                            overflowWrap: 'break-word',
                            maxWidth: '100%',
                            width: '100%'
                          }}>
                            [{i + 1}] <a
                              href={getDocumentUrl(c.source)}
                              target="_blank"
                              rel="noopener noreferrer"
                              style={{ color: '#1890ff', textDecoration: 'underline' }}
                            >
                              {c.title || c.source || 'Unknown Title'}
                            </a> | Page {c.page || ''} | Snippet: {c.snippet || ''}
                          </Text>
                        </List.Item>
                      )}
                    />
                  ),
                },
              ]}
            />
          )}
        </>
      )}
    </div>
  );
};

export default Proposal;

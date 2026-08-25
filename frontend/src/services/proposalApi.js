import { API_BASE, requestJson } from './apiClient'

export const generateProposal = ({ researchGoal, retrievalCount, mofLinkerMode }) =>
  requestJson('/proposal/generate', {
    method: 'POST',
    json: {
      research_goal: researchGoal,
      retrieval_count: retrievalCount,
      mof_linker_mode: mofLinkerMode || 'auto',
    },
  })

export const reviseProposal = ({ originalProposal, userFeedback, chunks, mofLinkerMode }) =>
  requestJson('/proposal/revise', {
    method: 'POST',
    json: {
      original_proposal: originalProposal,
      user_feedback: userFeedback,
      chunks,
      mof_linker_mode: mofLinkerMode || 'auto',
    },
  })

export const generateExperimentDetail = ({ proposal, chunks }) =>
  requestJson('/proposal/experiment-detail', {
    method: 'POST',
    json: { proposal, chunks },
  })

export const downloadProposalDocx = async ({
  proposal,
  chemicals,
  notFound,
  experimentDetail,
  citations,
}) => {
  const response = await fetch(`${API_BASE}/proposal/generate-docx`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      proposal,
      chemicals,
      not_found: notFound,
      experiment_detail: experimentDetail,
      citations,
    }),
  })

  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(`下載失敗: ${response.status} - ${errorText}`)
  }

  return response.blob()
}

export const translateProposalMof = ({ metalElement, linkerSmiles, linkerSmiles2 }) =>
  requestJson('/mof/proposal/translate', {
    method: 'POST',
    json: {
      metal_element: metalElement,
      linker_smiles: linkerSmiles,
      linker_smiles_2: linkerSmiles2,
    },
  })

export const runProposalScreening = ({ nodeId, linkerId, topology, maxResults }) =>
  requestJson('/mof/proposal/run-screening', {
    method: 'POST',
    json: {
      node_id: nodeId,
      linker_id: linkerId,
      topology,
      max_results: maxResults,
    },
  })

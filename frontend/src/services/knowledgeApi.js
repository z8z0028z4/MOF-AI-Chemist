import { requestJson } from './apiClient'

export const queryKnowledge = ({ question, retrievalCount, answerMode }) =>
  requestJson('/knowledge/query', {
    method: 'POST',
    json: {
      question,
      retrieval_count: retrievalCount,
      answer_mode: answerMode,
    },
  })

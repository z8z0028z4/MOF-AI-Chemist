import { requestJson } from './apiClient'

export const validateExternalPaperApi = () => requestJson('/external-paper/validate')

export const searchExternalPapers = ({ keywords, limit }) =>
  requestJson('/external-paper/search', {
    method: 'POST',
    json: { keywords, limit },
  })

export const downloadExternalPaper = ({ pmcid, title, pdfUrl }) =>
  requestJson('/external-paper/download', {
    method: 'POST',
    json: {
      pmcid,
      title,
      pdf_url: pdfUrl,
    },
  })

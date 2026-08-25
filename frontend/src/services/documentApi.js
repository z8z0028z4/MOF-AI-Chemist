import { API_BASE } from './apiClient'

export const getDocumentUrl = (filename) =>
  `${API_BASE}/documents/${encodeURIComponent(filename)}`

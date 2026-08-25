import { API_BASE, requestJson } from './apiClient'

const buildQueryString = (params) => {
  const query = new URLSearchParams()

  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      query.set(key, String(value))
    }
  })

  const queryString = query.toString()
  return queryString ? `?${queryString}` : ''
}

export const getPaperStats = () => requestJson('/paper/stats')

export const listPapers = ({ search, limit = 1000 } = {}) =>
  requestJson(`/paper/list${buildQueryString({ search, limit })}`)

export const searchPapers = ({ query, limit = 50 }) =>
  requestJson(`/paper/search${buildQueryString({ query, limit })}`)

export const getPaperDownloadUrl = (filename) =>
  `${API_BASE}/paper/download/${encodeURIComponent(filename)}`

export const getPaperViewUrl = (filename) =>
  `${API_BASE}/paper/view/${encodeURIComponent(filename)}`

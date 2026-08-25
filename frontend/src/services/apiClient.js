export const API_BASE = '/api/v1'

export async function requestJson(path, options = {}) {
  const requestOptions = { ...options }

  if (requestOptions.json !== undefined) {
    requestOptions.body = JSON.stringify(requestOptions.json)
    requestOptions.headers = {
      'Content-Type': 'application/json',
      ...requestOptions.headers,
    }
    delete requestOptions.json
  }

  const response = await fetch(`${API_BASE}${path}`, requestOptions)

  if (!response.ok) {
    const error = new Error(`API request failed: ${response.status}`)
    error.status = response.status
    error.response = response
    try {
      error.data = await response.clone().json()
    } catch {
      error.data = null
    }
    throw error
  }

  return response.json()
}

export function getApiErrorMessage(error, fallback) {
  return error?.data?.detail || fallback
}

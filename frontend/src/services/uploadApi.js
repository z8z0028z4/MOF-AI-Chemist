import { requestJson } from './apiClient'

export function getUploadStats() {
  return requestJson('/upload/stats')
}

export function refreshUploadStats() {
  return requestJson('/upload/refresh-stats', {
    method: 'POST',
    json: {},
  })
}

export function uploadFiles(files) {
  const formData = new FormData()
  files.forEach((file) => {
    formData.append('files', file)
  })

  return requestJson('/upload/files', {
    method: 'POST',
    body: formData,
  })
}

export function getUploadStatus(taskId) {
  return requestJson(`/upload/status/${encodeURIComponent(taskId)}`)
}

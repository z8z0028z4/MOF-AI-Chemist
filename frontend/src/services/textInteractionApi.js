import { requestJson } from './apiClient'

export const sendTextInteraction = (requestData) =>
  requestJson('/text-interaction', {
    method: 'POST',
    json: requestData,
  })

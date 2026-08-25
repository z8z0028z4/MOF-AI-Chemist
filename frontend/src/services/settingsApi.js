import { requestJson } from './apiClient'

export async function getConfigStatus() {
  try {
    return await requestJson('/settings/config-status')
  } catch (error) {
    if (error.status) {
      return null
    }
    throw error
  }
}

export function getModelSettings() {
  return requestJson('/settings/model')
}

export function updateModelSettings(llmModel, llmFallbackModel) {
  return requestJson('/settings/model', {
    method: 'POST',
    json: {
      llm_model: llmModel,
      llm_fallback_model: llmFallbackModel
    },
  })
}

export function getLlmParameters() {
  return requestJson('/settings/llm-parameters')
}

export function updateLlmParameters(parameters) {
  return requestJson('/settings/llm-parameters', {
    method: 'POST',
    json: parameters,
  })
}

export function getModelParametersInfo(modelName) {
  const query = modelName ? `?model_name=${encodeURIComponent(modelName)}` : ''
  return requestJson(`/settings/model-parameters-info${query}`)
}

export function getJsonSchemaParameters() {
  return requestJson('/settings/json-schema-parameters')
}

export function updateJsonSchemaParameters(parameters) {
  return requestJson('/settings/json-schema-parameters', {
    method: 'POST',
    json: parameters,
  })
}

export function getJsonSchemaParametersInfo() {
  return requestJson('/settings/json-schema-parameters-info')
}

export function getEnvStatus() {
  return requestJson('/settings/env-status')
}

export function getDevModeStatus() {
  return requestJson('/settings/dev-mode')
}

export function updateDevModeStatus(isDevMode) {
  return requestJson('/settings/dev-mode', {
    method: 'POST',
    json: { is_dev_mode: isDevMode },
  })
}

export function getDemoModeSettings() {
  return requestJson('/settings/demo-mode')
}

export function updateDemoModeSettings(settings) {
  return requestJson('/settings/demo-mode', {
    method: 'POST',
    json: settings,
  })
}

export function saveOpenAiApiKey(openaiApiKey) {
  return requestJson('/settings/api-keys/openai', {
    method: 'POST',
    json: { openai_api_key: openaiApiKey },
  })
}

export function saveGoogleApiKey(googleApiKey) {
  return requestJson('/settings/api-keys/google', {
    method: 'POST',
    json: { google_api_key: googleApiKey },
  })
}

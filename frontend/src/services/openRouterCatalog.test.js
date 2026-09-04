import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

import {
  canCommitCatalogRequest,
  commitCatalogResponse,
  enterOpenRouterCatalog,
  initializeCatalogModels,
  isValidCatalogResponse,
  isSuccessfulCatalogResponse,
  loadOpenRouterCatalogPage,

  mergeCatalogModels,
  mergeCatalogModelsPreservingSelection,
  normalizeCatalogVendor,
  replaceCatalogSelection,
  shouldLoadOpenRouterCatalog,
  shouldApplySettingsCatalogSnapshot,

  transitionToOpenRouterCatalog,
} from './openRouterCatalog.js'

const model = (value, label = value) => ({ value, label })

const firstPage = [model('other/first', 'Other first')]
const laterPage = [
  model('openai/later/vendor/complete-id', 'OpenAI later'),
  model('anthropic/later/vendor/complete-id', 'Anthropic later'),
  model('google/later/vendor/complete-id', 'Google later'),
  model('openai/later/vendor/complete-id', 'Duplicate OpenAI later'),
]

const merged = mergeCatalogModels(firstPage, laterPage)
assert.deepEqual(merged.map(({ value }) => value), [
  'openai/later/vendor/complete-id',
  'anthropic/later/vendor/complete-id',
  'google/later/vendor/complete-id',
  'other/first',
])
assert.equal(merged.length, 4)
assert.equal(merged[0].value, 'openai/later/vendor/complete-id')

const refreshedWithSelectedLaterModel = mergeCatalogModelsPreservingSelection(
  laterPage,
  [model('other/refreshed', 'Refreshed other')],
  'anthropic/later/vendor/complete-id',
)
assert.deepEqual(refreshedWithSelectedLaterModel.map(({ value }) => value), [
  'anthropic/later/vendor/complete-id',
  'other/refreshed',
])
assert.equal(mergeCatalogModelsPreservingSelection(laterPage, [], 'missing/model').length, 0)
const selectedBeforeProviderSwitch = [
  model('openrouter/later-page-model', 'Selected later-page model'),
  model('openrouter/another-model', 'Another model'),
]
const firstOpenRouterPage = [model('openai/first-page-model', 'First page model')]
const initializedAfterProviderSwitch = transitionToOpenRouterCatalog({
  previousProvider: null,
  selectedOpenRouterModel: selectedBeforeProviderSwitch[0],
  incomingModels: firstOpenRouterPage,
  keyConfigured: true,
})
assert.deepEqual(initializedAfterProviderSwitch, [
  model('openai/first-page-model', 'First page model'),
  model('openrouter/later-page-model', 'Selected later-page model'),
])
assert.equal(
  initializedAfterProviderSwitch.some(({ value }) => value === 'openrouter/later-page-model'),
  true,
)

// Exercise the same provider-effect boundary used by Settings: leave and
// re-enter OpenRouter, clear the old list, then merge the first page.
let lifecycle = {
  provider: 'openrouter',
  models: selectedBeforeProviderSwitch,
  selectedValue: 'openrouter/later-page-model',
}
const leavingOpenRouter = lifecycle
lifecycle = {
  provider: 'openai',
  models: [model('openai/default', 'OpenAI default')],
  selectedValue: 'openai/default',
}
const lifecycleEntry = enterOpenRouterCatalog({
  previousProvider: leavingOpenRouter.provider,
  currentModels: leavingOpenRouter.models,
  selectedValue: leavingOpenRouter.selectedValue,
  rememberedSelection: null,
  keyConfigured: true,
})
lifecycle = {
  provider: 'openrouter',
  models: lifecycleEntry.availableModels,
  selectedValue: leavingOpenRouter.selectedValue,
}
lifecycle.models = transitionToOpenRouterCatalog({
  previousProvider: lifecycleEntry.previousProvider,
  selectedOpenRouterModel: lifecycleEntry.selectedOpenRouterModel,
  incomingModels: firstOpenRouterPage,
  keyConfigured: lifecycleEntry.canLoad,
})
assert.equal(lifecycle.provider, 'openrouter')
assert.equal(lifecycle.models.some(({ value }) => value === 'openrouter/later-page-model'), true)
assert.equal(lifecycle.models.find(({ value }) => value === 'openrouter/later-page-model').label, 'Selected later-page model')
assert.equal(lifecycle.models.some(({ value }) => value === 'openai/default'), false)
assert.equal(lifecycle.models.some(({ value }) => value === lifecycle.selectedValue), true)

// Model-change boundary: a saved OpenAI option preserved during initialization
// must be removed from the live catalog when the user selects an Anthropic item.
const savedOpenAi = model('openai/saved', 'Saved OpenAI')
const selectedAnthropic = model('anthropic/page-1', 'Anthropic page 1')
let selectionBoundaryModels = mergeCatalogModels([savedOpenAi], [selectedAnthropic])
selectionBoundaryModels = replaceCatalogSelection(
  selectionBoundaryModels,
  savedOpenAi.value,
  selectedAnthropic.value,
)
assert.deepEqual(selectionBoundaryModels.map(({ value }) => value), [selectedAnthropic.value])
// The Settings surface receives one complete response. It must not model
// cursor continuation or merge a first page into local state.
const completeResponse = { models: [...firstPage, ...laterPage], stale: false, error: null }
assert.equal(isSuccessfulCatalogResponse(completeResponse), true)
assert.equal(completeResponse.models.length, 5)

// A complete response must be the options consumed by the Settings Select.
// The settings snapshot may resolve before or after the catalog request, but
// neither ordering may erase a committed initial load or refresh.
const initialCommit = commitCatalogResponse([], completeResponse)
assert.deepEqual(initialCommit.models, completeResponse.models)
assert.equal(initialCommit.state.error, null)
const refreshResponse = { models: [model('openai/refreshed', 'Refreshed OpenAI')], stale: false, error: null }
const refreshCommit = commitCatalogResponse(initialCommit.models, refreshResponse)
assert.deepEqual(refreshCommit.models, refreshResponse.models)
assert.equal(shouldApplySettingsCatalogSnapshot({ catalogCommitted: true, catalogLoading: false }), false)
assert.equal(shouldApplySettingsCatalogSnapshot({ catalogCommitted: false, catalogLoading: true }), false)
assert.equal(shouldApplySettingsCatalogSnapshot({ catalogCommitted: false, catalogLoading: false }), true)

// An OpenAI -> OpenRouter switch, including no-key fail-closed entry, must
// not retain the old provider's default or make it save-valid.
const providerBeforeSwitch = 'openai'
const openAiDefaults = [model('openai/default', 'OpenAI default')]
const noKeyEntry = enterOpenRouterCatalog({
  previousProvider: providerBeforeSwitch,
  currentModels: openAiDefaults,
  selectedValue: 'openai/default',
  rememberedSelection: null,
  keyConfigured: false,
})
assert.deepEqual(noKeyEntry.availableModels, [])
assert.equal(noKeyEntry.selectedOpenRouterModel, null)
const oldOpenAiValueSaveValid = noKeyEntry.availableModels.some(({ value }) => value === 'openai/default')
assert.equal(oldOpenAiValueSaveValid, false)
assert.equal(shouldLoadOpenRouterCatalog({
  provider: 'openrouter',
  keyConfigured: true,
  isLoading: false,
  existingModels: laterPage,
}), true)
assert.equal(shouldLoadOpenRouterCatalog({ provider: 'openai', keyConfigured: true, isLoading: false }), false)
// An in-flight response is discardable after either provider or key context
// changes, while the unchanged configured OpenRouter context remains valid.
assert.equal(canCommitCatalogRequest({
  requestGeneration: 4,
  currentGeneration: 4,
  requestProvider: 'openrouter',
  currentProvider: 'openrouter',
  requestKeyConfigured: true,
  currentKeyConfigured: true,
}), true)
assert.equal(canCommitCatalogRequest({
  requestGeneration: 4,
  currentGeneration: 5,
  requestProvider: 'openrouter',
  currentProvider: 'openrouter',
  requestKeyConfigured: true,
  currentKeyConfigured: true,
}), false)
assert.equal(canCommitCatalogRequest({
  requestGeneration: 4,
  currentGeneration: 5,
  requestProvider: 'openrouter',
  currentProvider: 'openai',
  requestKeyConfigured: true,
  currentKeyConfigured: false,
}), false)

const legacyModels = [
  model('openai/gpt-legacy', 'Legacy OpenAI'),
  model('anthropic/claude-legacy', 'Legacy Anthropic'),
  model('vendorless-model', 'Unknown model'),
  { value: 'google/gemini-explicit', label: 'Explicit OpenAI metadata', vendor: ' OpenAI ' },
]
assert.equal(normalizeCatalogVendor(legacyModels[0]), 'openai')
assert.equal(normalizeCatalogVendor(legacyModels[3]), 'openai')
assert.equal(normalizeCatalogVendor({ value: 'openai/derived', vendor: 'Mistral' }), 'other')
assert.equal(isValidCatalogResponse({ models: legacyModels }), true)
assert.equal(isValidCatalogResponse({ models: [{ value: 'openai/id' }] }), false)
assert.equal(isSuccessfulCatalogResponse({ models: legacyModels }), true)
assert.equal(isSuccessfulCatalogResponse({ models: legacyModels, stale: true }), false)
assert.equal(isSuccessfulCatalogResponse({ models: legacyModels, error: 'upstream unavailable' }), false)

// Exercise the request/commit/handler boundary used by Settings. The handler
// must receive the committed options rather than a discarded/null response.
const settingsSource = readFileSync(resolve(dirname(fileURLToPath(import.meta.url)), '../pages/Settings.jsx'), 'utf8')
assert.match(settingsSource, /loadOpenRouterCatalogPage\(/)
const renderedCatalogStates = []
const loadedInitial = await loadOpenRouterCatalogPage({
  fetchPage: async () => completeResponse,
  currentModels: [],
  onPage: (page) => renderedCatalogStates.push(page.models),
})
assert.deepEqual(loadedInitial.models, mergeCatalogModels([], completeResponse.models))
assert.deepEqual(renderedCatalogStates.at(-1), mergeCatalogModels([], completeResponse.models))
const loadedRefresh = await loadOpenRouterCatalogPage({
  refresh: true,
  fetchPage: async () => refreshResponse,
  currentModels: completeResponse.models,
  onPage: (page) => renderedCatalogStates.push(page.models),
})
assert.deepEqual(loadedRefresh.models, refreshResponse.models)
assert.deepEqual(renderedCatalogStates.at(-1), refreshResponse.models)

console.log('OpenRouter catalog dynamic dropdown: 14 passed')

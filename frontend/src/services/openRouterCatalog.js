const PRIORITY_VENDOR_RANK = {
  openai: 0,
  anthropic: 1,
  google: 2,
}

const PRIORITY_VENDORS = new Set(Object.keys(PRIORITY_VENDOR_RANK))

export const normalizeCatalogVendor = (item) => {
  const explicitVendor = typeof item?.vendor === 'string' ? item.vendor.trim().toLowerCase() : ''
  const modelValue = typeof item?.value === 'string' ? item.value : ''
  const namespace = modelValue.includes('/') ? modelValue.split('/', 1)[0].trim().toLowerCase() : ''
  const vendor = explicitVendor || namespace
  return PRIORITY_VENDORS.has(vendor) ? vendor : 'other'
}

export const shouldLoadOpenRouterCatalog = ({ provider, keyConfigured, isLoading }) => (
  ['openai', 'google', 'openrouter'].includes(provider) && keyConfigured && !isLoading
)

export const shouldApplySettingsCatalogSnapshot = ({ catalogCommitted, catalogLoading }) => (
  !catalogCommitted && !catalogLoading
)

export const commitCatalogResponse = (currentModels, response) => {
  if (!isValidCatalogResponse(response)) throw new Error('OpenRouter catalog response is invalid')
  return {
    models: response.models,
    state: { stale: Boolean(response.stale), error: response.error || null },
  }
}

export const canCommitCatalogRequest = ({
  requestGeneration,
  currentGeneration,
  requestProvider,
  currentProvider,
  requestKeyConfigured,
  currentKeyConfigured,
}) => (
  requestGeneration === currentGeneration
  && requestProvider === currentProvider
  && ['openai', 'google', 'openrouter'].includes(requestProvider)
  && requestKeyConfigured === currentKeyConfigured
  && currentKeyConfigured
)

const vendorRank = (item) => {
  return PRIORITY_VENDOR_RANK[normalizeCatalogVendor(item)] ?? 3
}

const compareCatalogModels = (left, right) => (
  vendorRank(left) - vendorRank(right)
  || left.label.localeCompare(right.label, undefined, { sensitivity: 'base' })
  || left.value.localeCompare(right.value)
)

export const mergeCatalogModels = (existingModels, incomingModels) => {
  const uniqueModels = new Map()
  for (const model of [...existingModels, ...incomingModels]) {
    if (!uniqueModels.has(model.value)) uniqueModels.set(model.value, model)
  }
  return [...uniqueModels.values()].sort(compareCatalogModels)
}

export const mergeCatalogModelsPreservingSelection = (existingModels, incomingModels, selectedValue) => {
  const selectedModel = existingModels.find((model) => model.value === selectedValue)
  return mergeCatalogModels(selectedModel ? [selectedModel] : [], incomingModels)
}

// Execute one bounded Settings request/commit operation.
export const loadOpenRouterCatalogPage = async ({
  refresh = false,
  cursor = null,
  fetchPage,
  currentModels,
  selectedModel = null,
  previousProvider = null,
  initialSelection = null,
  keyConfigured = true,
  isRequestValid = () => true,
  onPage = () => {},
}) => {
  const data = await fetchPage(refresh, cursor)
  if (!isRequestValid()) return null
  if (!isValidCatalogResponse(data)) throw new Error('OpenRouter catalog response is invalid')

  const incoming = data.models
  const initialModels = refresh || cursor === null
    ? (cursor === null
      ? transitionToOpenRouterCatalog({
        previousProvider,
        selectedOpenRouterModel: initialSelection,
        incomingModels: incoming,
        keyConfigured,
      })
      : mergeCatalogModelsPreservingSelection(
        selectedModel ? [selectedModel] : [], incoming, selectedModel?.value,
      ))
    : mergeCatalogModels(currentModels, incoming)
  const pageState = {
    models: initialModels,
    hasMore: Boolean(data.has_more) && Boolean(data.next_cursor),
    nextCursor: data.next_cursor || null,
  }
  onPage({ ...pageState, response: data })
  // The caller performs the final context check before applying the returned
  // snapshot. Do not re-check here between the callback and return: that
  // boundary can otherwise discard a page after its valid commit.
  return { ...data, models: pageState.models, has_more: pageState.hasMore, next_cursor: pageState.nextCursor }
}

export const selectedCatalogModel = (models, selectedValue) => (
  models.find((model) => model.value === selectedValue) || null
)

// Once the user chooses another loaded option, remove the one-off saved
// option that was injected only to keep an unavailable selection visible.
export const replaceCatalogSelection = (models, preservedSelectionValue, selectedValue) => {
  if (!preservedSelectionValue || preservedSelectionValue === selectedValue) return models
  return models.filter((model) => model.value !== preservedSelectionValue)
}

// This is the provider-effect boundary: clear options immediately, while
// retaining only a selection that belongs to the OpenRouter catalog.
export const enterOpenRouterCatalog = ({
  previousProvider,
  currentModels,
  selectedValue,
  rememberedSelection,
  keyConfigured,
}) => {
  const selectedOpenRouterModel = previousProvider === 'openrouter'
    ? selectedCatalogModel(currentModels, selectedValue)
    : rememberedSelection || null
  return {
    availableModels: [],
    selectedOpenRouterModel,
    previousProvider,
    canLoad: keyConfigured,
  }
}

export const initializeCatalogModels = (existingModels, incomingModels, selectedValue) => (
  mergeCatalogModelsPreservingSelection(existingModels, incomingModels, selectedValue)
)

export const transitionToOpenRouterCatalog = ({
  previousProvider,
  selectedOpenRouterModel,
  incomingModels,
  keyConfigured,
}) => {
  if (!keyConfigured) return []
  const canPreserveSelection = previousProvider === 'openrouter' || previousProvider == null
  const preservedSelection = canPreserveSelection && selectedOpenRouterModel
    ? [selectedOpenRouterModel]
    : []
  return initializeCatalogModels(
    preservedSelection,
    incomingModels,
    preservedSelection[0]?.value,
  )
}

export const isValidCatalogResponse = (data) => (
  Boolean(data)
  && typeof data === 'object'
  && Array.isArray(data.models)
  && data.models.every((item) => (
    item && typeof item === 'object'
    && typeof item.value === 'string'
    && item.value.length > 0
    && typeof item.label === 'string'
  ))
)

export const isSuccessfulCatalogResponse = (data) => (
  isValidCatalogResponse(data) && !data.stale && !data.error
)

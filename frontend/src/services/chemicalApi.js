import { requestJson } from './apiClient'

export const getChemicalDatabaseStats = () => requestJson('/chemical/database-stats')

export const listDatabaseChemicals = ({ limit = 1000 } = {}) =>
  requestJson(`/chemical/database-list?limit=${encodeURIComponent(limit)}`)

export const searchChemical = ({
  chemicalName,
  includeSafety = true,
  includeProperties = true,
  includeStructure = true,
  saveToDatabase = true,
}) =>
  requestJson('/chemical/search', {
    method: 'POST',
    json: {
      chemical_name: chemicalName,
      include_safety: includeSafety,
      include_properties: includeProperties,
      include_structure: includeStructure,
      save_to_database: saveToDatabase,
    },
  })

export const batchSearchChemicals = ({
  chemicalNames,
  includeSafety = true,
  includeProperties = true,
  includeStructure = true,
  saveToDatabase = true,
}) =>
  requestJson('/chemical/batch-search', {
    method: 'POST',
    json: {
      chemical_names: chemicalNames,
      include_safety: includeSafety,
      include_properties: includeProperties,
      include_structure: includeStructure,
      save_to_database: saveToDatabase,
    },
  })

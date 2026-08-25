import { requestJson } from './apiClient'

export function getMofPrivateSettingsStatus() {
  return requestJson('/mof/private-settings/status')
}

export function getToolsStatus() {
  return requestJson('/mof/tools/status')
}

export function installTool(tool) {
  return requestJson(`/mof/tools/${encodeURIComponent(tool)}/install`, {
    method: 'POST',
  })
}

export function getToolInstallStatus(tool) {
  return requestJson(`/mof/tools/${encodeURIComponent(tool)}/install-status`)
}

export function getCifGeneratorCatalog() {
  return requestJson('/mof/cif-generator/catalog')
}

export function getCifGeneratorTopologies(node_id, linker_id) {
  const params = new URLSearchParams()
  if (node_id) params.append('node_id', node_id)
  if (linker_id) params.append('linker_id', linker_id)
  const query = params.toString() ? `?${params.toString()}` : ''
  return requestJson(`/mof/cif-generator/topologies${query}`)
}

export function resolveCifGeneratorInputs(payload) {
  return requestJson('/mof/cif-generator/resolve', {
    method: 'POST',
    json: payload,
  })
}

export function createCifGeneratorJob(payload) {
  return requestJson('/mof/cif-generator/jobs', {
    method: 'POST',
    json: payload,
  })
}

export function getPropertyPredictorProfiles() {
  return requestJson('/mof/property-predictor/profiles')
}

export function createPropertyPredictorJob(formData) {
  return requestJson('/mof/property-predictor/jobs', {
    method: 'POST',
    body: formData,
  })
}

export function createPropertyPredictorUploadJob(payload) {
  return requestJson('/mof/property-predictor/upload-jobs', {
    method: 'POST',
    json: payload,
  })
}

export function getJobStatus(job_id) {
  return requestJson(`/mof/jobs/${encodeURIComponent(job_id)}`)
}

export function cancelJob(job_id) {
  return requestJson(`/mof/jobs/${encodeURIComponent(job_id)}/cancel`, {
    method: 'POST',
  })
}

export function listRuns() {
  return requestJson('/mof/runs')
}

export function getRunStatus(run_id) {
  return requestJson(`/mof/runs/${encodeURIComponent(run_id)}`)
}

export async function getRunArtifactText(run_id, artifact_id) {
  // Use fetch directly for text response
  const response = await fetch(`/api/v1/mof/runs/${encodeURIComponent(run_id)}/artifacts/${encodeURIComponent(artifact_id)}/text`)
  if (!response.ok) {
    throw new Error(`Failed to fetch artifact text: ${response.statusText}`)
  }
  return response.text()
}

export function browseCheckpoints(path) {
  const query = path ? `?path=${encodeURIComponent(path)}` : ''
  return requestJson(`/mof/property-predictor/browse-ckpts${query}`)
}

export function verifyCheckpoint(checkpointPath) {
  return requestJson('/mof/property-predictor/verify-ckpt', {
    method: 'POST',
    json: { checkpoint_path: checkpointPath },
  })
}

/**
 * Calculate theoretical XRD pattern from a CIF file.
 *
 * @param {object} options
 * @param {File|null} options.file - Uploaded CIF file object (takes priority)
 * @param {string|null} options.cifPath - Server-side CIF file path
 * @param {number} [options.wavelength=1.54184] - X-ray wavelength in Angstroms
 * @param {number} [options.maxTwoTheta=80.0] - Maximum 2-theta angle
 * @param {number} [options.fwhm=0.1] - Gaussian broadening FWHM
 * @returns {Promise<object>} XRD pattern result
 */
export async function calculateXrd({ file, cifPath, generatorRunId, artifactId, wavelength = 1.54184, maxTwoTheta = 80.0, fwhm = 0.1 }) {
  const formData = new FormData()
  if (file) {
    formData.append('file', file)
  } else if (cifPath) {
    formData.append('cif_path', cifPath)
  } else if (generatorRunId && artifactId) {
    formData.append('generator_run_id', generatorRunId)
    formData.append('artifact_id', artifactId)
  } else {
    throw new Error('Either file, cifPath, or both generatorRunId and artifactId must be provided')
  }
  formData.append('wavelength', String(wavelength))
  formData.append('max_two_theta', String(maxTwoTheta))
  formData.append('fwhm', String(fwhm))

  const response = await fetch('/api/v1/mof/xrd/calculate', {
    method: 'POST',
    body: formData,
  })
  if (!response.ok) {
    let detail = response.statusText
    try {
      const err = await response.json()
      detail = err.detail || detail
    } catch (_) {
      // Ignore error parsing failure and fallback to statusText
    }
    throw new Error(detail)
  }
  return response.json()
}

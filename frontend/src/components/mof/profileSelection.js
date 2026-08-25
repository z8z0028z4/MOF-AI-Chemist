export function resolveProfileSelection(profiles, defaultProfileId) {
  const validProfiles = Array.isArray(profiles) ? profiles.filter((profile) => profile?.id) : []
  const validIds = new Set(validProfiles.map((profile) => profile.id))

  if (defaultProfileId && validIds.has(defaultProfileId)) {
    return defaultProfileId
  }

  return validProfiles[0]?.id || null
}

export function createProfileRefreshGuard() {
  let generation = 0
  let active = true

  return {
    activate() {
      active = true
    },
    begin() {
      generation += 1
      return generation
    },
    isCurrent(token) {
      return active && token === generation
    },
    dispose() {
      active = false
      generation += 1
    },
  }
}
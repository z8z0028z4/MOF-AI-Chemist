import assert from 'node:assert/strict'
import { createProfileRefreshGuard, resolveProfileSelection } from './profileSelection.js'

const demoProfiles = [{ id: 'demo-canned-property-profile' }]
const realProfiles = [{ id: 'co2-298k-015bar' }, { id: 'n2-298k-1bar' }]

assert.equal(resolveProfileSelection(demoProfiles, 'demo-canned-property-profile'), 'demo-canned-property-profile')
assert.equal(resolveProfileSelection([], 'demo-canned-property-profile'), null)
assert.equal(resolveProfileSelection(realProfiles, 'demo-canned-property-profile'), 'co2-298k-015bar')
assert.equal(resolveProfileSelection(realProfiles, 'n2-298k-1bar'), 'n2-298k-1bar')
assert.equal(resolveProfileSelection([], undefined), null)

const deferred = () => {
  let resolve
  const promise = new Promise((res) => { resolve = res })
  return { promise, resolve }
}

const refreshGuard = createProfileRefreshGuard()
const firstResponse = deferred()
const secondResponse = deferred()
const committed = []
const refresh = async (response, token = refreshGuard.begin()) => {
  const result = await response.promise
  if (refreshGuard.isCurrent(token)) committed.push(result)
}
const firstRefresh = refresh(firstResponse)
const secondRefresh = refresh(secondResponse)
firstResponse.resolve('stale-demo-response')
secondResponse.resolve('current-real-response')
await Promise.all([firstRefresh, secondRefresh])
assert.deepEqual(committed, ['current-real-response'])

const unmountedGuard = createProfileRefreshGuard()
const lateResponse = deferred()
const lateToken = unmountedGuard.begin()
const lateCommitted = []
const lateRefresh = (async () => {
  const result = await lateResponse.promise
  if (unmountedGuard.isCurrent(lateToken)) lateCommitted.push(result)
})()
unmountedGuard.dispose()
lateResponse.resolve('late-response-after-unmount')
await lateRefresh
assert.deepEqual(lateCommitted, [])

console.log('profile selection transition tests: 7 passed')
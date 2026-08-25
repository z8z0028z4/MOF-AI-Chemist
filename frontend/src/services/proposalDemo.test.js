import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

import * as proposalDemo from './proposalDemo.js'

const {
  createDemoProposal,
  createDemoRevision,
  DEMO_EXPERIMENT_DETAIL,
  DEMO_PORMAKE_CANDIDATE,
  DEMO_SCREENING_RESULTS,
} = proposalDemo

const proposal = createDemoProposal('Validate the full workflow')
assert.equal(proposal.structured_proposal.mof_metal_element, 'Cu')
assert.equal(
  proposal.structured_proposal.mof_linker_name,
  'benzene-1,3,5-tricarboxylic acid',
)
assert.equal(proposal.chemicals.length, 5)
assert.deepEqual(proposal.chemicals.map(({ image_url }) => image_url), [
  '/demo_fixtures/pubchem_images/cid-18616.png',
  '/demo_fixtures/pubchem_images/cid-11138.png',
  '/demo_fixtures/pubchem_images/cid-3776.png',
  '/demo_fixtures/pubchem_images/cid-280.png',
  '/demo_fixtures/pubchem_images/cid-947.png',
])
assert.deepEqual(proposal.chemicals.map(({ cid, safety_icons }) => ({ cid, safety_icons })), [
  { cid: 18616, safety_icons: { nfpa_image: null, ghs_icons: ['/demo_fixtures/safety_images/ghs/ghs03.svg', '/demo_fixtures/safety_images/ghs/ghs05.svg', '/demo_fixtures/safety_images/ghs/ghs06.svg', '/demo_fixtures/safety_images/ghs/ghs07.svg', '/demo_fixtures/safety_images/ghs/ghs09.svg'] } },
  { cid: 11138, safety_icons: { nfpa_image: null, ghs_icons: ['/demo_fixtures/safety_images/ghs/ghs07.svg'] } },
  { cid: 3776, safety_icons: { nfpa_image: '/demo_fixtures/safety_images/nfpa/nfpa-cid-3776.svg', ghs_icons: ['/demo_fixtures/safety_images/ghs/ghs02.svg', '/demo_fixtures/safety_images/ghs/ghs05.svg', '/demo_fixtures/safety_images/ghs/ghs07.svg', '/demo_fixtures/safety_images/ghs/ghs08.svg', '/demo_fixtures/safety_images/ghs/ghs09.svg'] } },
  { cid: 280, safety_icons: { nfpa_image: null, ghs_icons: ['/demo_fixtures/safety_images/ghs/ghs04.svg', '/demo_fixtures/safety_images/ghs/ghs07.svg'] } },
  { cid: 947, safety_icons: { nfpa_image: '/demo_fixtures/safety_images/nfpa/nfpa-cid-947.svg', ghs_icons: ['/demo_fixtures/safety_images/ghs/ghs04.svg', '/demo_fixtures/safety_images/ghs/ghs08.svg'] } },
])

assert.equal(DEMO_PORMAKE_CANDIDATE.node_id, 'N409')
assert.equal(DEMO_PORMAKE_CANDIDATE.linker_id, 'N10')
assert.equal(DEMO_SCREENING_RESULTS[0].uptake, 1.2358)



const revision = createDemoRevision('Increase activation rigor')
assert.match(revision.proposal, /Increase activation rigor/)
assert.equal(revision.structured_proposal.mof_metal_element, 'Cu')
assert.equal(revision.chemicals.filter(({ image_url }) => image_url).length, 4)
assert.equal(revision.chemicals.find(({ cid }) => cid === 702).safety_icons.nfpa_image, '/demo_fixtures/safety_images/nfpa/nfpa-cid-702.svg')

assert.ok(DEMO_EXPERIMENT_DETAIL.structured_experiment.synthesis_process)

const proposalSource = readFileSync(new URL('../pages/Proposal.jsx', import.meta.url), 'utf8')
const proposalDemoSource = readFileSync(new URL('./proposalDemo.js', import.meta.url), 'utf8')
const smilesDrawerSource = readFileSync(new URL('../components/SmilesDrawer.jsx', import.meta.url), 'utf8')
const mofSource = readFileSync(new URL('../pages/MOF.jsx', import.meta.url), 'utf8')
const cifSource = readFileSync(new URL('../components/mof/CifGeneratorTab.jsx', import.meta.url), 'utf8')
const xrdSource = readFileSync(new URL('../components/mof/XrdCalculatorTab.jsx', import.meta.url), 'utf8')
const settingsSource = readFileSync(new URL('../pages/Settings.jsx', import.meta.url), 'utf8')

assert.match(proposalSource, /createCifGeneratorJob/)
assert.doesNotMatch(proposalSource, /batchSearchChemicals|chemicalApi/)
assert.match(proposalSource, /chemicals: data\.chemicals/)
assert.match(proposalSource, /imageUrl=\{c\.image_url\}/)
assert.match(proposalDemoSource, /\/demo_fixtures\/pubchem_images\/cid-18616\.png/)
assert.match(proposalDemoSource, /nfpa-cid-702\.svg/)
assert.doesNotMatch(proposalDemoSource, /https?:\/\//)
assert.doesNotMatch(proposalDemoSource, /pubchem\.ncbi\.nlm\.nih\.gov|fetch\(|axios/)
assert.match(smilesDrawerSource, /if \(imageUrl\)/)
assert.ok(smilesDrawerSource.indexOf('if (imageUrl)') > smilesDrawerSource.indexOf('if (pngStructure)'))
assert.match(proposalSource, /node_id:\s*'N409'/)
assert.match(proposalSource, /linker_id:\s*'N10'/)
assert.match(proposalSource, /max_results:\s*10/)
assert.match(proposalSource, /artifact_id:\s*`demo-cif-\$\{String\(index \+ 1\)\.padStart\(2, '0'\)\}`/)
assert.match(proposalSource, /generatorRunDetails\.status !== 'succeeded'/)
assert.match(proposalSource, /filename:\s*demoArtifacts\[index\]\.filename/)
assert.match(proposalSource, /artifactId,\s*filename:\s*artifactFilename/)
assert.match(mofSource, /artifactId:\s*location\.state\.artifactId/)
assert.match(cifSource, /envStatus\?\.version === 'demo-canned'/)
assert.match(cifSource, /const ready = isPormakeDemo \|\| envStatus\?\.ready === true/)
assert.match(cifSource, /Static\/canned synthetic ready/)
assert.match(xrdSource, /initialParams\.artifactId/)
assert.match(xrdSource, /art\.artifact_id === explicitArtifact/)

assert.equal((settingsSource.match(/<Switch\b/g) || []).length, 1)
assert.match(settingsSource, /checked=\{demoMode\.enabled\}/)
assert.match(settingsSource, /onChange=\{saveDemoMode\}/)
assert.match(settingsSource, /updateDemoModeSettings\(\{\s*enabled\s*\}\)/)
assert.match(
  settingsSource,
  /storeDemoMode\(\{\s*enabled:\s*saved\.enabled,\s*mock_proposal:\s*saved\.mock_proposal,\s*mock_property_prediction:\s*saved\.mock_property_prediction,\s*mock_generate_new_idea:\s*saved\.mock_generate_new_idea,\s*mock_experiment_detail:\s*saved\.mock_experiment_detail,\s*\}\)/,
)
assert.doesNotMatch(settingsSource, /storeDemoMode\(saved\)/)
assert.doesNotMatch(settingsSource, /Checkbox\.Group/)
assert.doesNotMatch(settingsSource, /enableFullDemo/)
assert.doesNotMatch(settingsSource, /全部開啟/)
assert.doesNotMatch(settingsSource, /User prompting proposal|Property Prediction|Generate New Idea|Accept & Generate Experiment Detail/)
console.log('proposalDemo fixtures: ok')

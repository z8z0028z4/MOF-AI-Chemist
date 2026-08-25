export const DEFAULT_DEMO_CONFIG = {
  enabled: false,
  mock_proposal: false,
  mock_property_prediction: false,
  mock_generate_new_idea: false,
  mock_experiment_detail: false,
}

export const DEMO_SCIENCE_DISCLAIMER = 'Illustrative Demo content only: non-experimental, not a validated synthesis procedure, and not safety instructions.'
export const DEMO_PREDICTION_DISCLAIMER = 'Synthetic illustrative prediction only: not calibrated, not an experimental measurement, and not a validated model result.'

export const readDemoConfig = () => {
  try {
    return {
      ...DEFAULT_DEMO_CONFIG,
      ...JSON.parse(localStorage.getItem('proposal_demo_config') || '{}'),
    }
  } catch {
    return { ...DEFAULT_DEMO_CONFIG }
  }
}

const BTC_SMILES = 'C1=C(C=C(C=C1C(=O)O)C(=O)O)C(=O)O'

const DEMO_PUBCHE_IMAGE_URLS = Object.freeze({
  18616: '/demo_fixtures/pubchem_images/cid-18616.png',
  11138: '/demo_fixtures/pubchem_images/cid-11138.png',
  3776: '/demo_fixtures/pubchem_images/cid-3776.png',
  280: '/demo_fixtures/pubchem_images/cid-280.png',
  947: '/demo_fixtures/pubchem_images/cid-947.png',
})

const getDemoPubChemImageUrl = (cid) => DEMO_PUBCHE_IMAGE_URLS[cid] || null

const DEMO_SAFETY_IMAGE_ROOT = '/demo_fixtures/safety_images'
// Real PubChem GHS/NFPA pictograms captured once into backend/demo_fixtures/safety_images
// via scripts/sync_demo_safety_images.py. NFPA 704 is only provided by PubChem for a subset
// of CIDs, so it is null where PubChem returns none (18616, 11138, 280).
const DEMO_SAFETY_ICON_URLS = Object.freeze({
  18616: {
    nfpa_image: null,
    ghs_icons: [
      `${DEMO_SAFETY_IMAGE_ROOT}/ghs/ghs03.svg`,
      `${DEMO_SAFETY_IMAGE_ROOT}/ghs/ghs05.svg`,
      `${DEMO_SAFETY_IMAGE_ROOT}/ghs/ghs06.svg`,
      `${DEMO_SAFETY_IMAGE_ROOT}/ghs/ghs07.svg`,
      `${DEMO_SAFETY_IMAGE_ROOT}/ghs/ghs09.svg`,
    ],
  },
  11138: {
    nfpa_image: null,
    ghs_icons: [`${DEMO_SAFETY_IMAGE_ROOT}/ghs/ghs07.svg`],
  },
  3776: {
    nfpa_image: `${DEMO_SAFETY_IMAGE_ROOT}/nfpa/nfpa-cid-3776.svg`,
    ghs_icons: [
      `${DEMO_SAFETY_IMAGE_ROOT}/ghs/ghs02.svg`,
      `${DEMO_SAFETY_IMAGE_ROOT}/ghs/ghs05.svg`,
      `${DEMO_SAFETY_IMAGE_ROOT}/ghs/ghs07.svg`,
      `${DEMO_SAFETY_IMAGE_ROOT}/ghs/ghs08.svg`,
      `${DEMO_SAFETY_IMAGE_ROOT}/ghs/ghs09.svg`,
    ],
  },
  280: {
    nfpa_image: null,
    ghs_icons: [
      `${DEMO_SAFETY_IMAGE_ROOT}/ghs/ghs04.svg`,
      `${DEMO_SAFETY_IMAGE_ROOT}/ghs/ghs07.svg`,
    ],
  },
  947: {
    nfpa_image: `${DEMO_SAFETY_IMAGE_ROOT}/nfpa/nfpa-cid-947.svg`,
    ghs_icons: [
      `${DEMO_SAFETY_IMAGE_ROOT}/ghs/ghs04.svg`,
      `${DEMO_SAFETY_IMAGE_ROOT}/ghs/ghs08.svg`,
    ],
  },
  702: {
    nfpa_image: `${DEMO_SAFETY_IMAGE_ROOT}/nfpa/nfpa-cid-702.svg`,
    ghs_icons: [
      `${DEMO_SAFETY_IMAGE_ROOT}/ghs/ghs02.svg`,
      `${DEMO_SAFETY_IMAGE_ROOT}/ghs/ghs07.svg`,
      `${DEMO_SAFETY_IMAGE_ROOT}/ghs/ghs08.svg`,
    ],
  },
})

const getDemoSafetyIcons = (cid) => DEMO_SAFETY_ICON_URLS[cid] || { ghs_icons: [], nfpa_image: null }

export const createDemoProposal = (researchGoal = '') => ({
  demo_disclaimer: DEMO_SCIENCE_DISCLAIMER,
  proposal: [
    'Proposal: Solvent-Free Synthesis of Porous Cu-BTC MOF (HKUST-1) for Sustainable CO2 Capture',
    '',
    `Research Goal: ${researchGoal || 'Develop a green, high-crystallinity Cu-BTC MOF via solvent-free grinding.'}`,
    '',
    '[Need & Background]',
    'Global climate change driven by rising greenhouse gas emissions, particularly carbon dioxide (CO2), necessitates the development of highly efficient carbon capture, utilization, and storage (CCUS) technologies. Metal-Organic Frameworks (MOFs), such as HKUST-1 (Cu-BTC), have emerged as promising candidates for CO2 adsorption due to their ultra-high specific surface area, tunable pore size, and rich density of unsaturated open metal sites that exhibit strong electrostatic interactions with CO2 molecules. However, conventional solvothermal methods for fabricating HKUST-1 require large amounts of hazardous, organic solvents (such as N,N-dimethylformamide or ethanol) and prolonged heating times. This massive solvent consumption generates toxic chemical waste, poses environmental hazards, and significantly increases production costs, hindering the sustainable scaling-up of MOF materials for commercial carbon capture applications. Therefore, there is an urgent need for a green, solvent-free synthesis method that eliminates organic liquid media during the reaction phase, drastically reduces energetic overhead, and preserves the structural integrity and gas adsorption capacity of the resulting MOF.',
    '',
    '[Solution]',
    'To address the environmental and scaling challenges of solvothermal MOF synthesis, we propose a solvent-free mechanochemical coordination approach combined with short-duration thermal treatment to prepare HKUST-1. The method involves dry-grinding solid precursors—specifically copper(II) nitrate trihydrate and benzene-1,3,5-tricarboxylic acid (BTC)—in an optimized 1.5:1 molar ratio for 15 minutes using a mortar and pestle. This mechanical force initiates the coordination between copper ions and carboxylate ligands in the solid state. The resulting solid mixture is subsequently heated in a sealed autoclave at 120 °C for only 3 hours to complete the crystal growth. Unreacted starting materials are then removed via a rapid centrifugal washing process with a minimal amount of methanol, yielding high-purity, dark-blue activated Cu-BTC. This process eliminates liquid organic solvents from the main reaction phase and reduces synthesis time from days to hours.',
    '',
    '[Differentiation]',
    'Unlike conventional hydrothermal and solvothermal approaches that rely on organic solvent mixtures to dissolve and assemble the network, this method performs the main coordination reaction in a completely solvent-free solid state, using mechanical energy to overcome the activation barrier. Compared to typical solvent-free methods that often result in amorphous or poorly crystalline products with low porosity, this combination of mechanochemical grinding and brief oven heating produces HKUST-1 with a relative crystallinity of up to 130% compared to commercial standards (e.g., Basolite C300). The reaction completes in just 3 hours at a moderate temperature of 120 °C, compared to conventional solvothermal processes that require 12 to 24 hours at higher temperatures, saving substantial energy and chemical resources.',
    '',
    '[Benefit]',
    'This approach significantly reduces the E-factor of MOF production by eliminating bulk reaction solvents, thereby preventing the generation of hazardous liquid waste streams. The high structural crystallinity translates into a highly developed microporous network (surface area ~1044 m2/g), ensuring an outstanding CO2 adsorption capacity of 1.7 mmol/g at 30 °C and 1 bar, which is comparable to or higher than solvothermally synthesized equivalents. The process utilizes easily manageable solid-state precursors, making it highly compatible with continuous green manufacturing techniques such as twin-screw extrusion, paving the way for low-cost, industrial-scale MOF production for carbon capture.',
    '',
    '[Experimental Overview]',
    'Synthesize the Cu-BTC framework by dry grinding copper(II) nitrate trihydrate and benzene-1,3,5-tricarboxylic acid (1.5:1 molar ratio) for 15 minutes, followed by conventional heating at 120 °C for 3 hours. Activate and purify the product by centrifugal washing with methanol (twice at 8,000 rpm for 10 minutes) and dry overnight at 80 °C under vacuum. Characterize the product using Powder X-ray Diffraction (PXRD) to verify phase purity and calculate relative crystallinity. Evaluate CO2 adsorption capacity at 30 °C and 1 bar, and conduct cyclic adsorption-desorption tests to assess regeneration performance.',
  ].join('\n'),
  chemicals: [
    {
      cid: 18616,
      name: 'copper dinitrate',
      formula: 'CuN2O6',
      weight: '187.56',
      smiles: '[N+](=O)([O-])[O-].[N+](=O)([O-])[O-].[Cu+2]',
      query_name: 'copper(II) nitrate',
      image_url: getDemoPubChemImageUrl(18616),
      safety_icons: getDemoSafetyIcons(18616),
    },
    {
      cid: 11138,
      name: 'benzene-1,3,5-tricarboxylic acid',
      formula: 'C9H6O6',
      weight: '210.14',
      smiles: BTC_SMILES,
      query_name: 'benzene-1,3,5-tricarboxylic acid',
      image_url: getDemoPubChemImageUrl(11138),
      safety_icons: getDemoSafetyIcons(11138),
    },
    {
      cid: 3776,
      name: 'methanol',
      formula: 'CH4O',
      weight: '32.04',
      smiles: 'CO',
      query_name: 'methanol',
      image_url: getDemoPubChemImageUrl(3776),
      safety_icons: getDemoSafetyIcons(3776),
    },
    {
      cid: 280,
      name: 'carbon dioxide',
      formula: 'CO2',
      weight: '44.01',
      smiles: 'C(=O)=O',
      query_name: 'carbon dioxide',
      image_url: getDemoPubChemImageUrl(280),
      safety_icons: getDemoSafetyIcons(280),
    },
    {
      cid: 947,
      name: 'nitrogen',
      formula: 'N2',
      weight: '28.01',
      smiles: 'N#N',
      query_name: 'nitrogen',
      image_url: getDemoPubChemImageUrl(947),
      safety_icons: getDemoSafetyIcons(947),
    },
  ],
  not_found: [],
  citations: [],
  chunks: [],
  structured_proposal: {
    proposal_title: 'Solvent-Free Synthesis of Porous Cu-BTC MOF (HKUST-1) for Sustainable CO2 Capture',
    need: 'Global climate change driven by rising greenhouse gas emissions, particularly carbon dioxide (CO2), necessitates the development of highly efficient carbon capture, utilization, and storage (CCUS) technologies. Metal-Organic Frameworks (MOFs), such as HKUST-1 (Cu-BTC), have emerged as promising candidates for CO2 adsorption due to their ultra-high specific surface area, tunable pore size, and rich density of open metal sites that exhibit strong electrostatic interactions with CO2 molecules. However, conventional solvothermal methods for fabricating HKUST-1 require large amounts of hazardous, organic solvents (such as N,N-dimethylformamide or ethanol) and prolonged heating times. This massive solvent consumption generates toxic chemical waste, poses environmental hazards, and significantly increases production costs, hindering the sustainable scaling-up of MOF materials for commercial carbon capture applications. Therefore, there is an urgent need for a green, solvent-free synthesis method that eliminates organic liquid media during the reaction phase, drastically reduces energetic overhead, and preserves the structural integrity and gas adsorption capacity of the resulting MOF.',
    solution: 'To address the environmental and scaling challenges of solvothermal MOF synthesis, we propose a solvent-free mechanochemical coordination approach combined with short-duration thermal treatment to prepare HKUST-1. The method involves dry-grinding solid precursors—specifically copper(II) nitrate trihydrate and benzene-1,3,5-tricarboxylic acid (BTC)—in an optimized 1.5:1 molar ratio for 15 minutes using a mortar and pestle. This mechanical force initiates coordination in the solid state. The resulting solid mixture is subsequently heated in a sealed autoclave at 120 °C for 3 hours. Unreacted starting materials are removed via centrifugal washing with methanol (twice at 8,000 rpm for 10 minutes), yielding activated dark-blue Cu-BTC crystals.',
    differentiation: 'Unlike conventional solvothermal methods that rely on bulk organic solvents to assemble the framework, this method performs the coordination reaction in a completely solvent-free solid state using mechanical force. Compared to other solid-state approaches that often produce amorphous material, this method yields HKUST-1 with a relative crystallinity of up to 130% compared to commercial standards (e.g. Basolite C300) in just 3 hours at 120 °C.',
    benefit: 'Significantly reduces the E-factor of MOF production by eliminating reaction solvent waste streams. The high crystallinity ensures a highly developed microporous network (surface area ~1044 m2/g) and an outstanding CO2 adsorption capacity of 1.7 mmol/g at 30 °C and 1 bar, comparable to or higher than solvothermally synthesized equivalents.',
    experimental_overview: 'Prepare a Cu-BTC framework using dry mechanochemical grinding followed by brief autoclave heating at 120 °C. Purify and activate the product using methanol wash under centrifugation, and evaluate carbon dioxide uptake at 30 °C.',
    materials_list: [
      'copper(II) nitrate',
      'benzene-1,3,5-tricarboxylic acid',
      'methanol',
      'carbon dioxide',
      'nitrogen',
    ],
    mof_metal_element: 'Cu',
    mof_linker_name: 'benzene-1,3,5-tricarboxylic acid',
    mof_linker_name_2: '',
    mof_linker_smiles: BTC_SMILES,
    mof_linker_smiles_2: '',
  },
})

export const DEMO_PORMAKE_CANDIDATE = {
  metal_id: 'N409',
  metal_element: 'Cu',
  organic_id: 'N10',
  organic_role: 'N',
  organic_coordination_number: 3,
  assembly_pattern: 'N(metal)-N(organic)',
  match_kind: 'exact',
  confidence: 0.98,
  covered_atom_fraction: 1,
  uncovered_elements: {},
  evidence: ['deterministic demo fixture'],
  warnings: [],
  port_modes: [],
  node_id: 'N409',
  linker_id: 'N10',
  auto_generatable: true,
  compatible_topologies: ['hbk', 'mfj', 'tfz', 'ffc', 'lil', 'iab', 'tfo', 'sty', 'tfn', 'maw'],
}

const DEMO_SCREENING_RESULTS_RAW = [
  {
    node_id: 'N409',
    linker_id: 'N10',
    topology: 'hbk',
    uptake: 1.2358,
    unit: 'mmol/g',
    artifact_id: 'pred-001',
    generator_run_id: '20260706T031121-f9b69a5819',
    is_demo: true,
  },
  {
    node_id: 'N409',
    linker_id: 'N10',
    topology: 'mfj',
    uptake: 1.2285,
    unit: 'mmol/g',
    artifact_id: 'pred-002',
    generator_run_id: '20260706T031121-f9b69a5819',
    is_demo: true,
  },
  {
    node_id: 'N409',
    linker_id: 'N10',
    topology: 'tfz',
    uptake: 1.0744,
    unit: 'mmol/g',
    artifact_id: 'pred-003',
    generator_run_id: '20260706T031121-f9b69a5819',
    is_demo: true,
  },
  {
    node_id: 'N409',
    linker_id: 'N10',
    topology: 'ffc',
    uptake: 1.3671,
    unit: 'mmol/g',
    artifact_id: 'pred-004',
    generator_run_id: '20260706T031121-f9b69a5819',
    is_demo: true,
  },
  {
    node_id: 'N409',
    linker_id: 'N10',
    topology: 'lil',
    uptake: 1.2001,
    unit: 'mmol/g',
    artifact_id: 'pred-005',
    generator_run_id: '20260706T031121-f9b69a5819',
    is_demo: true,
  },
  {
    node_id: 'N409',
    linker_id: 'N10',
    topology: 'iab',
    uptake: 1.4585,
    unit: 'mmol/g',
    artifact_id: 'pred-006',
    generator_run_id: '20260706T031121-f9b69a5819',
    is_demo: true,
  },
  {
    node_id: 'N409',
    linker_id: 'N10',
    topology: 'tfo',
    uptake: 1.1962,
    unit: 'mmol/g',
    artifact_id: 'pred-007',
    generator_run_id: '20260706T031121-f9b69a5819',
    is_demo: true,
  },
  {
    node_id: 'N409',
    linker_id: 'N10',
    topology: 'sty',
    uptake: 1.1571,
    unit: 'mmol/g',
    artifact_id: 'pred-008',
    generator_run_id: '20260706T031121-f9b69a5819',
    is_demo: true,
  },
  {
    node_id: 'N409',
    linker_id: 'N10',
    topology: 'tfn',
    uptake: 1.3873,
    unit: 'mmol/g',
    artifact_id: 'pred-009',
    generator_run_id: '20260706T031121-f9b69a5819',
    is_demo: true,
  },
  {
    node_id: 'N409',
    linker_id: 'N10',
    topology: 'maw',
    uptake: 1.2033,
    unit: 'mmol/g',
    artifact_id: 'pred-010',
    generator_run_id: '20260706T031121-f9b69a5819',
    is_demo: true,
  },
]

export const DEMO_SCREENING_RESULTS = DEMO_SCREENING_RESULTS_RAW.map((result) => ({
  ...result,
  demo_disclaimer: DEMO_PREDICTION_DISCLAIMER,
}))

export const createDemoRevision = (feedback = '') => {
  const base = createDemoProposal(feedback)
  return {
    ...base,
    proposal: [
      'Proposal: Solvent-Free Synthesis of Porous Cu-BTC MOF (HKUST-1) for Sustainable CO2 Capture',
      '',
      'Research Goal: We propose a modified green, solvent-free synthesis of Cu-BTC (HKUST-1) using ethanol as a less toxic alternative washing solvent to methanol.',
      '',
      `Demo Revision Request applied: ${feedback || 'suggest an alternative solvent for methanol, for a less toxic synthesis route.'}`,
      '',
      '[Need & Background]',
      'Global climate change driven by rising greenhouse gas emissions, particularly carbon dioxide (CO2), necessitates the development of highly efficient carbon capture, utilization, and storage (CCUS) technologies. Metal-Organic Frameworks (MOFs), such as HKUST-1 (Cu-BTC), have emerged as promising candidates for CO2 adsorption due to their ultra-high specific surface area, tunable pore size, and rich density of unsaturated open metal sites that exhibit strong electrostatic interactions with CO2 molecules. However, conventional solvothermal methods for fabricating HKUST-1 require large amounts of hazardous, organic solvents (such as N,N-dimethylformamide or ethanol) and prolonged heating times. This massive solvent consumption generates toxic chemical waste, poses environmental hazards, and significantly increases production costs, hindering the sustainable scaling-up of MOF materials for commercial carbon capture applications. Therefore, there is an urgent need for a green, solvent-free synthesis method that eliminates organic liquid media during the reaction phase, drastically reduces energetic overhead, and preserves the structural integrity and gas adsorption capacity of the resulting MOF.',
      '',
      '[Solution]',
      'To address the environmental and scaling challenges of solvothermal MOF synthesis, we propose a solvent-free mechanochemical coordination approach combined with short-duration thermal treatment to prepare HKUST-1. The method involves dry-grinding solid precursors—specifically copper(II) nitrate trihydrate and benzene-1,3,5-tricarboxylic acid (BTC)—in an optimized 1.5:1 molar ratio for 15 minutes using a mortar and pestle. This mechanical force initiates the coordination between copper ions and carboxylate ligands in the solid state. The resulting solid mixture is subsequently heated in a sealed autoclave at 120 °C for only 3 hours to complete the crystal growth. Unreacted starting materials are then removed via a rapid centrifugal washing process with a minimal amount of ethanol (with adjusted contact duration to compensate for ethyl diffusion constraints), yielding high-purity, dark-blue activated Cu-BTC. This process eliminates liquid organic solvents from the main reaction phase and reduces synthesis time from days to hours.',
      '',
      '[Differentiation]',
      'Unlike conventional hydrothermal and solvothermal approaches that rely on organic solvent mixtures to dissolve and assemble the network, this method performs the main coordination reaction in a completely solvent-free solid state, using mechanical energy to overcome the activation barrier. Compared to typical solvent-free methods that often result in amorphous or poorly crystalline products with low porosity, this combination of mechanochemical grinding and brief oven heating produces HKUST-1 with a relative crystallinity of up to 130% compared to commercial standards (e.g., Basolite C300). The reaction completes in just 3 hours at a moderate temperature of 120 °C, compared to conventional solvothermal processes that require 12 to 24 hours at higher temperatures, saving substantial energy and chemical resources, while utilizing low-toxicity ethanol instead of methanol for purification without compromising crystalline order.',
      '',
      '[Benefit]',
      'This approach significantly reduces the E-factor of MOF production by eliminating bulk reaction solvents and adopting green ethanol for purification, thereby preventing toxic liquid waste streams. The high structural crystallinity translates into a highly developed microporous network (surface area ~1044 m2/g), ensuring an outstanding CO2 adsorption capacity of 1.7 mmol/g at 30 °C and 1 bar, which is comparable to or higher than solvothermally synthesized equivalents. The process utilizes easily manageable solid-state precursors, making it highly compatible with continuous green manufacturing techniques such as twin-screw extrusion, paving the way for low-cost, industrial-scale MOF production for carbon capture.',
      '',
      '[Experimental Overview]',
      'Synthesize the Cu-BTC framework by dry grinding copper(II) nitrate trihydrate and benzene-1,3,5-tricarboxylic acid (1.5:1 molar ratio) for 15 minutes, followed by conventional heating at 120 °C for 3 hours. Activate and purify the product by centrifugal washing with ethanol (twice at 8,000 rpm for 10 minutes with optimized contact duration) and dry overnight at 80 °C under vacuum. Characterize the product using Powder X-ray Diffraction (PXRD) to verify phase purity and calculate relative crystallinity. Evaluate CO2 adsorption capacity at 30 °C and 1 bar, and conduct cyclic adsorption-desorption tests to assess regeneration performance.',
    ].join('\n'),
    chemicals: [
      {
        cid: 18616,
        name: 'copper dinitrate',
        formula: 'CuN2O6',
        weight: '187.56',
        smiles: '[N+](=O)([O-])[O-].[N+](=O)([O-])[O-].[Cu+2]',
        query_name: 'copper(II) nitrate',
        image_url: getDemoPubChemImageUrl(18616),
        safety_icons: getDemoSafetyIcons(18616),
      },
      {
        cid: 11138,
        name: 'benzene-1,3,5-tricarboxylic acid',
        formula: 'C9H6O6',
        weight: '210.14',
        smiles: BTC_SMILES,
        query_name: 'benzene-1,3,5-tricarboxylic acid',
        image_url: getDemoPubChemImageUrl(11138),
        safety_icons: getDemoSafetyIcons(11138),
      },
      {
        cid: 702,
        name: 'ethanol',
        formula: 'C2H6O',
        weight: '46.07',
        smiles: 'CCO',
        query_name: 'ethanol',
        safety_icons: getDemoSafetyIcons(702),
      },
      {
        cid: 280,
        name: 'carbon dioxide',
        formula: 'CO2',
        weight: '44.01',
        smiles: 'C(=O)=O',
        query_name: 'carbon dioxide',
        image_url: getDemoPubChemImageUrl(280),
        safety_icons: getDemoSafetyIcons(280),
      },
      {
        cid: 947,
        name: 'nitrogen',
        formula: 'N2',
        weight: '28.01',
        smiles: 'N#N',
        query_name: 'nitrogen',
        image_url: getDemoPubChemImageUrl(947),
        safety_icons: getDemoSafetyIcons(947),
      },
    ],
    structured_proposal: {
      ...base.structured_proposal,
      proposal_title: 'Ethanol-Washed Solvent-Free Synthesis of Porous Cu-BTC MOF (HKUST-1)',
      need: base.structured_proposal.need,
      solution: 'To address the environmental and scaling challenges of solvothermal MOF synthesis, we propose a solvent-free mechanochemical coordination approach combined with short-duration thermal treatment to prepare HKUST-1. The method involves dry-grinding solid precursors—specifically copper(II) nitrate trihydrate and benzene-1,3,5-tricarboxylic acid (BTC)—in an optimized 1.5:1 molar ratio for 15 minutes using a mortar and pestle. This mechanical force initiates coordination in the solid state. The resulting solid mixture is subsequently heated in a sealed autoclave at 120 °C for 3 hours. Unreacted starting materials are removed via centrifugal washing with ethanol (twice at 8,000 rpm for 10 minutes with optimized contact duration), yielding activated dark-blue Cu-BTC crystals.',
      differentiation: 'Unlike conventional solvothermal methods that rely on bulk organic solvents to assemble the framework, this method performs the coordination reaction in a completely solvent-free solid state using mechanical force. Compared to other solid-state approaches that often produce amorphous material, this method yields HKUST-1 with a relative crystallinity of up to 130% compared to commercial standards (e.g. Basolite C300) in just 3 hours at 120 °C, while utilizing low-toxicity ethanol instead of methanol for purification without compromising crystalline order.',
      benefit: 'Significantly reduces the E-factor of MOF production by eliminating reaction solvent waste streams and adopting green ethanol for purification, thereby preventing toxic liquid waste streams. The high crystallinity ensures a highly developed microporous network (surface area ~1044 m2/g) and an outstanding CO2 adsorption capacity of 1.7 mmol/g at 30 °C and 1 bar, comparable to or higher than solvothermally synthesized equivalents.',
      experimental_overview: 'Prepare a Cu-BTC framework using dry mechanochemical grinding followed by brief autoclave heating at 120 °C. Purify and activate the product using ethanol wash (twice at 8,000 rpm for 10 minutes with optimized contact duration) under centrifugation, and evaluate carbon dioxide uptake at 30 °C.',
      revision_explanation: 'Substituted methanol with ethanol as the washing agent to mitigate toxicity. Diffusion kinetics were optimized by adjusting agitation duration (24-30 h) and temperature (35-40 °C), maintaining framework integrity, a 130% relative crystallinity, and equivalent CO2 capture capacity.',
      materials_list: [
        'copper(II) nitrate',
        'benzene-1,3,5-tricarboxylic acid',
        'ethanol',
        'carbon dioxide',
        'nitrogen',
      ],
    },
  }
}

export const getDemoExperimentDetail = (isEthanol = false) => {
  const solventName = isEthanol ? 'ethanol' : 'methanol';
  const solventTitle = isEthanol ? 'Ethanol' : 'Methanol';
  const shakingTime = isEthanol ? '24–30 hours (or warm the washing bath slightly to 35–40 °C)' : '18 hours';
  const centrifugeTemp = isEthanol ? ' at 35–40 °C' : '';
  const precautionsSolvent = isEthanol
    ? 'Ethanol is volatile and highly flammable; keep away from open flames.'
    : 'Methanol is highly toxic and volatile; perform all operations involving methanol inside a well-ventilated fume hood. Avoid skin contact or inhalation.';
  const heavyMetalWaste = isEthanol
    ? 'Collect and dispose of all supernatant ethanol washing waste, which contains soluble copper residues, in the designated heavy metal organic liquid waste container.'
    : 'Collect and dispose of all supernatant methanol washing waste, which contains toxic copper and organic residues, in the designated chlorinated/non-chlorinated organic waste container according to local safety regulations.';

  const processStep5 = isEthanol
    ? '5. Purification & Washing (Green Solvent Option): Disperse the crude blue powder in 40 mL of analytical-grade ethanol (instead of methanol). To compensate for the slower diffusion of the larger ethyl group, extend the orbital shaking/agitation time from 18 hours to 24–30 hours (or warm the washing bath slightly to 35–40 °C). Perform centrifugation at 8,000 rpm for 10 minutes. Decant the supernatant liquid to remove unreacted starting materials. Repeat this centrifugation washing step twice.'
    : '5. Purification & Washing: Disperse the crude blue powder in 40 mL of analytical-grade methanol. Perform orbital shaking/agitation for 18 hours to dissolve and remove any unreacted copper precursors or organic ligands. Perform centrifugation at 8,000 rpm for 10 minutes. Decant the supernatant liquid. Repeat this centrifugation washing step twice.';

  const processStep6 = `6. Activation: Dry the washed product overnight (12 hours) in a vacuum drying oven at 80 °C. The activated final product appears as a deep dark-blue crystalline powder (Cu-BTC / HKUST-1).`;

  const synthesisProcessStructured = isEthanol
    ? '1. Precursor Preparation: Weigh out 3.62 g of copper(II) nitrate trihydrate and 2.10 g of BTC, matching an optimized molar ratio of 1.5:1.\n2. Solid-State Mechanochemical Grinding: Combine the solid reactants inside a clean agate mortar and grind vigorously for 15 minutes to initiate the solid-state coordination reaction.\n3. Thermal Crystallization: Transfer the ground solid mixture to a 100 mL Teflon-lined autoclave and heat at 120 °C under autogenous pressure for 3 hours.\n4. Cool-down: Allow the autoclave to cool down naturally to room temperature (approx. 2 hours) before opening.\n5. Purification & Washing: Disperse crude powder in 40 mL ethanol. To compensate for ethyl diffusion limits, extend shaking time to 24–30 hours (or warm bath to 35–40 °C). Centrifuge at 8,000 rpm for 10 minutes, decant, and repeat twice.\n6. Activation: Dry the washed product overnight in a vacuum oven at 80 °C to yield activated dark-blue Cu-BTC / HKUST-1.'
    : '1. Precursor Preparation: Weigh out 3.62 g of copper(II) nitrate trihydrate and 2.10 g of BTC, matching an optimized molar ratio of 1.5:1.\n2. Solid-State Mechanochemical Grinding: Combine the solid reactants inside a clean agate mortar and grind vigorously for 15 minutes to initiate the solid-state coordination reaction.\n3. Thermal Crystallization: Transfer the ground solid mixture to a 100 mL Teflon-lined autoclave and heat at 120 °C under autogenous pressure for 3 hours.\n4. Cool-down: Allow the autoclave to cool down naturally to room temperature (approx. 2 hours) before opening.\n5. Purification & Washing: Disperse crude powder in 40 mL methanol and shake for 18 hours. Centrifuge at 8,000 rpm for 10 minutes, decant, and repeat twice.\n6. Activation: Dry the washed product overnight in a vacuum oven at 80 °C to yield activated dark-blue Cu-BTC / HKUST-1.';

  const materialsAndConditionsStructured = isEthanol
    ? 'Precursors: Copper(II) nitrate trihydrate (99% purity) and benzene-1,3,5-tricarboxylic acid (98% purity) in a 1.5:1 molar ratio.\nReaction: Dry grinding for 15 minutes at room temperature, followed by thermal treatment in autoclave at 120 °C for 3 hours.\nWashing: Analytical-grade ethanol (two cycles of 40 mL, centrifuged at 8,000 rpm for 10 minutes each at 35–40 °C, with shaking for 24-30 hours).\nActivation: Vacuum drying at 80 °C for 12 hours.'
    : 'Precursors: Copper(II) nitrate trihydrate (99% purity) and benzene-1,3,5-tricarboxylic acid (98% purity) in a 1.5:1 molar ratio.\nReaction: Dry grinding for 15 minutes at room temperature, followed by thermal treatment in autoclave at 120 °C for 3 hours.\nWashing: Analytical-grade methanol (two cycles of 40 mL, centrifuged at 8,000 rpm for 10 minutes each, with shaking for 18 hours).\nActivation: Vacuum drying at 80 °C for 12 hours.';

  const analyticalMethodsStructured = 'Powder X-ray Diffraction (PXRD): Scan over 2-theta range of 5° to 40° at 1.2°/min using Cu-Ka radiation. Verify planes (200), (220), (222), (400), (420), and calculate relative crystallinity against Basolite C300.\nSEM/EDX: Analyze morphology and check for unreacted precursors via elemental composition (Cu, C, O).\nGas Adsorption: N2 isotherms at 77 K for BET surface area; CO2 uptake capacity at 30 °C and 1 bar via TGA after activation.';

  const precautionsStructured = isEthanol
    ? 'Wear standard laboratory PPE (lab coat, nitrile gloves, safety goggles).\nHandle solid reactants inside a certified fume hood to avoid dust inhalation.\nEthanol is volatile and flammable; keep away from open flames and heat sources.\nBalance centrifuge rotor carefully before running at 8,000 rpm.\nUse thermal gloves to retrieve autoclave from 120 °C oven, cool completely before opening.\nDispose of ethanol wash waste containing copper residues in designated heavy metal liquid containers.'
    : 'Wear standard laboratory PPE (lab coat, nitrile gloves, safety goggles).\nHandle solid reactants inside a certified fume hood to avoid dust inhalation.\nMethanol is highly toxic and volatile; perform all operations involving methanol inside a fume hood to prevent inhalation.\nBalance centrifuge rotor carefully before running at 8,000 rpm.\nUse thermal gloves to retrieve autoclave from 120 °C oven, cool completely before opening.\nDispose of methanol wash waste containing copper residues in chlorinated/non-chlorinated organic waste container.';

  return {
    experiment_detail: [
      'Synthesis Process',
      '1. Precursor Preparation: Weigh out 3.62 g of copper(II) nitrate trihydrate (99% purity) and 2.10 g of 1,3,5-benzenetricarboxylic acid (BTC, 98% purity), matching an optimized Cu:BTC molar ratio of 1.5:1.',
      '2. Solid-State Mechanochemical Grinding: Combine the solid reactants inside a clean agate mortar. Manually grind the mixture vigorously using a pestle for 15 minutes. Observe the physical coordination reaction as the light blue copper precursor and white ligand solids turn into a homogeneous blue paste/powder.',
      '3. Thermal Crystallization: Transfer the ground solid mixture quantitatively into a 100 mL stainless-steel Teflon-lined autoclave. Seal the autoclave tightly and heat the reaction at 120 °C under autogenous pressure for 3 hours in a conventional oven.',
      '4. Cool-down: Allow the autoclave to cool down naturally to room temperature (approximately 2 hours) before opening the reactor.',
      processStep5,
      processStep6,
      '',
      'Materials and Reaction Conditions',
      `- Precursors: Copper(II) nitrate trihydrate (Cu(NO3)2·3H2O, 99% purity, MW = 241.60 g/mol) and 1,3,5-benzenetricarboxylic acid (H3BTC, 98% purity, MW = 210.14 g/mol).`,
      `- Reaction Medium: Solvent-free dry mechanochemical co-grinding for 15 minutes at room temperature.`,
      `- Thermal Treatment: Heating in a sealed Teflon-lined stainless steel autoclave at 120 °C for 3 hours under autogenous pressure.`,
      `- Washing Solvent: Analytical-grade ${solventName} (99.8% purity) used for centrifugation washing (two cycles of 40 mL ${solventName}, centrifuged at 8,000 rpm for 10 minutes each${centrifugeTemp}).`,
      `- Activation & Drying: Vacuum drying at 80 °C for 12 hours.`,
      '',
      'Analytical Characterization Techniques',
      '1. Powder X-ray Diffraction (PXRD): Characterize the crystal structure and phase purity using a diffractometer with Cu-Ka radiation (lambda = 1.5418 Å). Scan the samples over a 2-theta range of 5° to 40° at a step scan speed of 1.2°/min. Verify the characteristic peaks of HKUST-1 at planes (200), (220), (222), (400), and (420). Calculate the relative percentage crystallinity against a commercial Basolite C300 reference standard using the plane (222) as intensity reference.',
      '2. SEM and EDX: Analyze the crystallite morphology and size distribution using a Scanning Electron Microscope operated at 15 kV. Coat samples with gold/platinum prior to imaging. Perform Energy-Dispersive X-ray Spectroscopy (EDX) to verify elemental compositions (Cu, C, O) and check for unreacted precursors.',
      '3. Gas Adsorption Measurements: Measure nitrogen (N2) adsorption-desorption isotherms at 77 K to compute the BET specific surface area and micropore volume. Determine carbon dioxide (CO2) adsorption capacities using a Thermogravimetric Analyzer (TGA) at 30 °C and 1 bar under pure CO2 flow (20 mL/min). Activate samples at 100 °C under N2 purge before the adsorption runs.',
      '',
      'Precautions & Safety Measures',
      '1. Personal Protective Equipment (PPE): Wear standard laboratory PPE including a lab coat, chemical-resistant nitrile gloves, and safety goggles at all times.',
      '2. Inhalation Hazard: Copper salts and organic ligands are fine powders. Perform weighing and mortar grinding inside a certified, ventilated fume hood to prevent chemical dust inhalation.',
      `3. Flammability & Centrifugation: ${precautionsSolvent}`,
      '4. Thermal Hazard: Use heat-resistant protective gloves when retrieving the autoclave from the 120 °C oven. Never open the autoclave until it has cooled completely to room temperature.',
      `5. Waste Disposal: ${heavyMetalWaste}`,
    ].join('\n'),
    structured_experiment: {
      synthesis_process: synthesisProcessStructured,
      materials_and_conditions: materialsAndConditionsStructured,
      analytical_methods: analyticalMethodsStructured,
      precautions: precautionsStructured,
    },
    citations: [],
  };
};

export const getDemoExperimentDetailByProposal = (proposalText = '') => {
  const isEthanol = /ethanol/i.test(proposalText);
  return getDemoExperimentDetail(isEthanol);
};

export const DEMO_EXPERIMENT_DETAIL = getDemoExperimentDetail(true);

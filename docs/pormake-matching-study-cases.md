# PORMAKE matching study cases

## Research question

For the MVP, proposal chemicals are treated as available ingredients, not as a
claim about the experimentally realized framework. A candidate may be generated
when the installed PORMAKE catalog can represent it and PORMAKE can assemble it.
Unused input ingredients are allowed. Geometry/RMSD validation is a later gate.

This study asks a narrower question: which common MOF composition patterns can
the current single-metal/single-linker matcher recover from the installed
PORMAKE catalog, and what X semantics explain the successes and failures?

## Cases and evidence

| Case | Reported framework ingredients | Topology | Source |
| --- | --- | --- | --- |
| HKUST-1 | Cu paddlewheel + BTC | tbo representation used by PORMAKE | [HKUST-1 overview](https://en.wikipedia.org/wiki/HKUST-1), [original Science DOI](https://doi.org/10.1126/science.283.5405.1148) |
| UiO-66 | Zr6 oxo cluster + BDC | fcu | [UiO MOFs](https://en.wikipedia.org/wiki/UiO_MOFs), [original JACS DOI](https://doi.org/10.1021/ja8057953) |
| UiO-66-NH2 | Zr6 oxo cluster + 2-aminoterephthalate | fcu | [PubChem framework record](https://pubchem.ncbi.nlm.nih.gov/compound/169449882) |
| MOF-5 | Zn4O + BDC | pcu representation used by PORMAKE | [MOF-5 overview](https://en.wikipedia.org/wiki/MOF-5), [original Nature paper](https://www.nature.com/articles/46248) |
| MIL-53(Al) | Al-OH chain + BDC | sra representation used by PORMAKE | [MIL-53 overview](https://en.wikipedia.org/wiki/MIL-53) |
| MOF-801 | Zr6 oxo cluster + fumarate | fcu | [MOF-801 structural description](https://www.mdpi.com/2304-6740/7/9/110) |
| ZIF-8 | Zn + 2-methylimidazolate | sod | [ZIF overview](https://en.wikipedia.org/wiki/Zeolitic_imidazolate_framework), [PubChem framework record](https://pubchem.ncbi.nlm.nih.gov/compound/87663345) |
| CALF-20 | Zn + oxalate + 1,2,4-triazolate | dmc in the literature | [CALF-20 review](https://pubs.rsc.org/en/content/articlehtml/2025/cc/d4cc05744a), [Science DOI](https://doi.org/10.1126/science.abi7281) |

The topology names in PORMAKE are abstract-net labels and need not be inferred
from chemical ingredients. The study uses a known topology only to validate an
identified pair, not to make the pair match.

## Installed-catalog results

| Case | Resolver result | Expected/observed PORMAKE pair | Assembly probe |
| --- | --- | --- | --- |
| HKUST-1 | exact | N409 + N10 | tbo succeeded, RMSD < 0.3 |
| UiO-66 | exact | N419 + E14 | fcu succeeded, RMSD 0.04343 |
| UiO-66-NH2 | exact | N419 + E72 | fcu succeeded, RMSD 0.04342 |
| MOF-5 | exact | N577 + E14 | pcu succeeded, RMSD 0.05773 |
| MIL-53(Al) | exact | N565 + E14 | sra succeeded, RMSD 0.12750 |
| MOF-801 | exact | N419 + E19 | fcu succeeded, RMSD 0.04337 |
| ZIF-8 | no match | no atom-complete 2-methylimidazolate E block found | not attempted |
| CALF-20 | no match | N73 + E37 is geometrically buildable but is not a chemically exact CALF-20 mapping | not accepted |

The executable discovery assertions are in
`tests/test_pormake_matching_study_cases.py`. The assembly probes use the real
PORMAKE worker and fixed named topologies.

## Matching modes observed

### 1. Split functional group

The organic E/N block contains a carbon skeleton with X at the port. The metal
N block contains the coordinating functional-group atoms around its X. Combining
the organic core and the observed metal cap reconstructs the supplied linker.

This is the current matcher's strongest mode and covers the carboxylate cases
above: BTC, BDC, amino-BDC, BPDC, fumarate, and DOBDC-like linkers when an exact
catalog block exists.

### 2. Direct donor

The complete donor ring remains in the organic block and X contributes no atom;
it only specifies the connection direction. ZIF linkers are representative.

The matcher now accepts a zero-atom port only when the opposite metal-node X is
bonded directly to a metal. This mirrors PORMAKE fusion without allowing an
unmatched nonmetal cap to be appended to the input linker. ZIF-8 remains
`no_match` because the installed catalog does not contain an atom-complete
2-methylimidazolate organic block, rather than because all direct-donor X ports
are categorically rejected.

### 3. Embedded auxiliary ligand

An input molecule may be represented inside the inorganic N block rather than
as a separate E block. Oxalate in a Zn-oxalate SBU is representative.

The current resolver accepts only one linker graph and does not compare
additional input components with nonmetal subgraphs embedded in an SBU.

### 4. Scaffold/decorated linker

A catalog core is contained in the input linker but unmatched decorations
remain. The matcher reports this relationship, but the MVP does not generate a
CIF because the catalog block would omit atoms.

## CALF-20 correction

The installed `N73` is a Zn/O/C composite node and `E37` is a two-connected
triazole-like block, so `N73 + E37 + dia` can be assembled geometrically.
However, graph inspection shows that E37 has the adjacent-atom pattern of a
1,2,3-triazole ring (including a C-C edge and two N-N edges). It is not
isomorphic to the 1,2,4-triazolate used in CALF-20. Therefore successful
PORMAKE assembly of N73/E37 is not sufficient evidence that the generated CIF
is CALF-20.

This is a useful negative case: topology/CN/RMSD validate geometry but cannot
repair an incorrect chemical graph mapping.

## Implemented MVP prefilter

Before any CIF worker is started, the production matcher now applies:

1. element-count, heavy-atom-count, bond-order, and cycle-rank signatures;
2. organic-core subgraph mapping;
3. `split_fragment` or metal-direct `zero_atom` virtual-fusion coverage;
4. exact heavy-atom coverage for auto-generatable candidates;
5. coordination-number topology filtering.

For representative inputs, the 314 organic catalog cores were reduced to:

| Input | Signature candidates |
| --- | ---: |
| BTC | 45 |
| BDC | 36 |
| amino-BDC | 47 |
| fumarate | 6 |
| 2-methylimidazole | 6 |

The PORMAKE worker then performs a local X-direction RMSD gate before cell
scaling and full CIF construction. Topologies with local RMSD at or above 0.3
are rejected without running the expensive builder.

## Implication for the MVP

The exact matcher is a conservative graph prefilter for split-functional-group
and catalog-supported zero-atom direct-metal ports. Its numeric `confidence` is
a rule score, not a calibrated chemical probability.

For a future broader enumerator, inputs should be treated as optional available
components:

1. enumerate PORMAKE N/E pairs containing the requested metal;
2. evaluate both split-cap and zero-atom direct-donor interpretations per X;
3. match additional molecules against embedded nonmetal SBU subgraphs;
4. allow unused input components;
5. retain candidates with explicit atom-coverage provenance;
6. run topology compatibility, PORMAKE assembly, RMSD, and CIF validation as
   separate downstream gates.

This broadens theoretical coverage without requiring the system to decide
whether a reagent is a precursor, modulator, linker, or spectator before
enumeration.

## Current resolver benchmark

Measured on the local WSL environment with the installed 867-fragment PORMAKE
catalog. The reusable command is:

```bash
.venv/bin/python -m experiments.pormake_pairing.benchmark --repeats 3
```

The benchmark contains ten exact positive cases, one scaffold-only case, and
three conservative no-match cases.

| Metric | Result |
| --- | ---: |
| Cases | 14 |
| Status classification | 14/14 |
| Positive exact cases | 10 |
| Recall@1 | 10/10 |
| Recall@5 | 10/10 |
| Recall@10 | 10/10 |
| Cold first query | 2.174 s |
| Warm median per query | 0.388 s |
| Warm mean per query | 0.384 s |
| Mean organic-signature reduction | 89.83% |

The fastest no-match was CALF-20 triazole at approximately 0.005 seconds after
only one organic signature candidate and zero pair evaluations. The heavier
positive cases were HKUST-1 and MOF-5 at about 1.2 seconds warm because they
retain many metal-node hypotheses and evaluate 7,020 and 8,096 graph mappings,
respectively. These are still graph operations; they do not generate CIFs.

Interpretation limits:

- The cases are curated regressions and over-represent chemistry already known
  to the matcher; the numbers are not an estimate of random-MOF recall.
- Top-1 ranking includes the product resolver's labelled common-SBU prior.
- The complete set of chemically valid PORMAKE alternatives is unknown, so
  candidate precision cannot yet be calculated.
- Conservative no-match correctness does not measure whether another external
  building-block database could represent the material.

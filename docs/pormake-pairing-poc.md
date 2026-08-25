# PORMAKE Pairing Proof of Concept

## Question

Given a metal element and a linker SMILES proposed by the AI chemist, can the
existing PORMAKE building-block database produce a chemically defensible set of
metal-node and organic `N`/`E` candidates without a hand-written
ligand-to-PORMAKE lookup table?

This proof of concept answers only that closed-world question. It does not
predict every coordination structure that the metal and linker could form in
the laboratory.

## Model

PORMAKE building blocks are treated as molecular graph fragments with `X`
attachment ports.

1. A metal building block is selected only when it contains the requested
   metal element.
2. Metal atoms and explicit hydrogens are removed from that block.
3. Every remaining connected component containing exactly one `X` is an
   observed metal-side cap. For carboxylate nodes this is typically
   `X-C(O)O`.
4. An organic building block is reduced to its heavy-atom core. Each `X`
   records a port on one core atom.
5. The organic core is searched as a bond-aware subgraph of the proposed
   linker.
6. Every port must lead to a linker branch that is graph-isomorphic to one of
   the selected metal node's observed caps.
7. All linker heavy atoms must be explained for an exact match. Small
   non-port substituents are allowed only as an explicitly labelled scaffold
   match.

This recovers BTC dynamically as a benzene core from `N10` plus three
carboxylate caps observed in a Cu node such as `N409`. No `BTC -> N10` table is
used.

## Result classes

- `exact`: every linker heavy atom is covered by the organic core and observed
  metal caps.
- `scaffold`: all coordination ports and their caps match, but small
  non-port decorations remain uncovered. This supports cases such as amino-BDC
  mapping to a BDC PORMAKE scaffold while making clear that a CIF built from
  the unmodified catalog entry would omit the amino group.
- `no_match`: the coordination branches do not match the selected metal's
  observed caps, coverage is incomplete, or only a low-confidence graph edit
  could make the structures agree.

Only `exact` candidates are suitable for later automatic CIF generation.
`scaffold` candidates are proposal hints until a custom decorated building
block is generated.

## Confidence

Confidence is evidence-based, not a synthesis-probability estimate.

- Exact graph cover starts at high confidence.
- Scaffold confidence is reduced in proportion to uncovered heavy atoms.
- Candidates are rejected when any port is unexplained.
- Bond order is enforced in organic cores.
- Metal caps are compared by element-labelled topology while allowing
  carboxylate resonance/protonation differences.

## Proof cases

The automated tests cover:

- Cu + BTC: exact `N409`/`N10`-shape reconstruction.
- Zr + BDC: exact metal-`E`-metal reconstruction.
- Zn + fumaric acid: exact ethene-core reconstruction.
- Zr + amino-BDC: scaffold fallback when an exact decorated fragment is absent
  from the isolated test library.
- Dicyanobenzene against a carboxylate-only test library: rejected.
- Invalid SMILES and wrong-metal candidates: rejected.

The standalone validator additionally runs these cases against the real
PORMAKE database and writes a JSON report. CIF generation and proposal-mode
integration remain out of scope until the real-database report demonstrates
adequate precision.

Run the complete real-database validation:

```bash
.venv/bin/python -m experiments.pormake_pairing.validate \
  --bb-dir /path/to/pormake/database/bbs
```

Run an arbitrary metal/linker query:

```bash
.venv/bin/python -m experiments.pormake_pairing.validate \
  --bb-dir /path/to/pormake/database/bbs \
  --metal Zr \
  --smiles 'Nc1cc(C(=O)O)ccc1C(=O)O' \
  --max-results 20
```

## Real-database result

Validation against the 867 building blocks in the PORMAKE checkout on
2026-06-29 produced:

- 867/867 files parsed without an error.
- 314/314 fragments classified as organic exposed a valid connected core and
  conservative single-neighbour `X` ports.
- 504/534 metal-containing `N` fragments exposed at least one conservative
  single-`X` cap. Metal-containing `E` fragments are intentionally excluded
  from the metal-node candidate pool.
- Cu/BTC recovered `N409 + N10` at rank 6 and also found lower-connectivity
  exact decompositions, demonstrating that the same chemical linker can have
  multiple PORMAKE coordination modes.
- Zr/BDC recovered `N419 + E14` at rank 6.
- Zn/fumarate recovered `N577 + E19`; 77 exact Zn-node candidates also showed
  that metal element plus linker graph cannot uniquely identify an SBU.
- Zr/amino-BDC recovered the exact decorated fragment `E72`, while also
  returning `E14` only as a lower-confidence scaffold whose catalog CIF would
  omit the amino group.
- Zr/BPDC and Cu/dicyanobenzene recovered graph-exact candidates, covering both
  carboxylate and nitrile cap chemistry.
- Benzene disulfonate and diphosphonate recovered exact S/O and P/O cap
  candidates.
- A methyl-BDC derivative not represented by an exact test entry fell back to
  an explicit `E14` scaffold result.
- Cu/4,4-bipyridine returned `no_match` rather than forcing an unsupported
  decomposition.

The measured conclusion is narrower than a general coordination predictor:
the algorithm is useful as a conservative **candidate generator** over the
existing PORMAKE graph grammar. It is not a unique resolver. Metal-node ties
require a later topology/3D assembly stage or additional SBU evidence from the
proposal/RAG context.

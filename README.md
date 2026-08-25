# MOF-AI-Chemist

MOF-AI-Chemist is an open-source AI research assistant for chemistry and materials science. It helps turn research questions into structured literature, chemical, proposal, and metal-organic framework (MOF) workflows.

The project bridges natural-language research goals with evidence-aware research exploration and computational materials workflows. Provider-backed paths can use configured external services or local project engines; the explicit Offline Demo mode uses deterministic fixtures instead, so readers can distinguish a click-through demonstration from real provider, network, or engine validation.

## Features

### Literature and knowledge

- Search local literature and Europe PMC results.
- Upload research documents for metadata extraction and text chunking.
- Query the knowledge base with citations and source context.

### AI-assisted research planning

- Draft structured research proposals.
- Extract chemical and material information from research content.
- Explain or revise selected text and organize experiment details.
- Produce export-oriented proposal and research outputs.

### Chemistry utilities

- Look up chemical properties and safety fields.
- Work with PubChem-shaped chemical records.
- Display SMILES and chemical structures for supported compounds.

### MOF workflow

- Interpret proposal content into candidate metals and linkers.
- Pair candidates through the PORMAKE integration boundary.
- Generate and view CIF structures.
- Connect property-prediction workflows at their integration boundary.
- Calculate and present X-ray diffraction (XRD) patterns.

### Provider and configuration layer

- React frontend and FastAPI backend boundaries keep UI, API, and research services separated.
- Configure model and provider settings for optional real-provider paths.
- Keep user-generated papers, uploads, indexes, parsed chemicals, and MOF runs under the private runtime-data root rather than in source control.

### Offline Demo mode

Offline Demo mode is one explicit user-facing feature: turn on the unified **Demo mode** switch in Settings to click through supported workflows with deterministic local fixtures. The supported Demo path does not require an API key or network connection, and it keeps demo behavior separate from production provider calls.

Demo fixtures are illustrative and non-experimental. They are not calibrated predictions, laboratory measurements, safety advice, or a validated synthesis procedure. Offline Demo mode is useful for reviewing UI and application/API handoffs; it does not replace real-provider, browser, Windows-packaging, or engine-real validation.

## Architecture

The maintained application is the React + FastAPI path:

```text
frontend/                 React + Vite + Ant Design
  src/pages/              Route-level screens
  src/components/         Reusable UI components
  src/contexts/           Shared frontend state
  src/services/           Frontend API/service helpers

backend/                  FastAPI application
  api/routes/             HTTP boundaries and request validation
  api/models/             Pydantic request/response schemas
  services/               Research workflows and external API orchestration
  services/analysis/      Scientific analysis routines
  core/                   Configuration, LLM, retrieval, and generation infrastructure
  workers/                MOF and analysis worker boundaries
```

## Quick start

Linux/WSL is the primary development path. Python 3.10–3.12 and Node.js 16 or newer are supported project targets. From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cd frontend
npm install
cd ..
```

Start the backend and Vite development server together:

```bash
./start_react.sh
```

The script starts the backend on port 8000 and prints the Vite frontend URL. It writes generated logs under `logs/`; use the URL printed by Vite rather than assuming a fixed frontend port. Backend API documentation is available at `http://localhost:8000/api/docs`, and the health endpoint is `http://localhost:8000/health`.

For backend-only development:

```bash
./run_backend.sh
```

Production provider paths may require credentials configured through the supported Settings/environment flow. Do not commit `.env` files, API keys, tokens, or generated user data. Offline Demo mode is the no-key path for supported click-through workflows.

## Verification

The repository uses layered tests. Default tests should use local fixtures or fakes; real provider and network checks are opt-in and marked `external`.

Backend import and safe test loop:

```bash
.venv/bin/python -c "import backend.main; print('backend.main import ok')"
.venv/bin/pytest -c tests/pytest.ini -m "not external" --tb=short -q
```

Focused Demo workflow checks:

```bash
.venv/bin/pytest -c tests/pytest.ini \
  tests/test_demo_cross_stage_handoffs.py \
  tests/test_unified_demo_smoke.py -q
```

Frontend checks:

```bash
cd frontend
npm run lint
npm run build
npm run test:proposal-demo
npm run test:mof
```

These commands provide local application, API, fixture, and static-build evidence. Browser click-through, Windows packaging, real provider compatibility, and engine-real MOF validation remain separate gates and should be reported with their own evidence.

## Project status

This is an active-development public snapshot. The main product workflows and the Offline Demo path are being stabilized, while provider compatibility, browser validation, Windows packaging, and real-engine MOF validation remain separate workstreams. The repository does not claim production readiness or validated laboratory use.

## Documentation and notices

- [Contributing guide](CONTRIBUTING.md) — development setup and workflow.
- [Demo mode specification](docs/demo-mode-spec.md) — the unified Demo switch and fixture-backed behavior.
- [Testing guide](tests/README_TESTING.md) — test layers, markers, and external-service policy.
- [Verification baseline](docs/verification-baseline.md) — public verification boundaries and evidence.
- [Third-party notices](THIRD_PARTY_NOTICES.md) — license and provenance information for bundled or derived assets.
- [MIT License](LICENSE).

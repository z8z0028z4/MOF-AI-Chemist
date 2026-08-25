# AI Research Assistant

A React + FastAPI research assistant for chemistry and materials-science workflows. Linux/WSL is the active development path; Windows launch and installer notes are retained as a future user/demo path and are not treated as verified release evidence.

## Current rough release candidate: Version A Demo

This checkout contains the rough Version A Demo candidate. The user-facing contract is deliberately small:

- Settings exposes one unified **Demo mode** switch.
- When the switch is ON, the Demo path covers Proposal, Property Prediction, Generate New Idea/Revision, and Experiment Detail.
- When the switch is OFF, those stages use their real paths.
- The persisted `mock_*` fields and `DEMO_MOCK_*` environment variables are internal/test-only compatibility surfaces, not additional user controls.
- Demo responses use explicit deterministic fixtures. The MOF path includes ten synthetic CIF fixtures and precomputed XRD patterns for offline application/API tests.

Application/API evidence is recorded in `tests/test_demo_cross_stage_handoffs.py` and `tests/test_unified_demo_smoke.py`. Those tests use local deterministic doubles and do not prove browser rendering, provider/network behavior, subprocess execution, engine-real results, Windows packaging, or a packaged CIF path.

### Open release gates

The following are intentionally still open for this rough candidate:

- Browser visual/user click-through, including the Settings switch and MOF CIF/XRD UI.
- Windows packaging and installer execution. This checkout has no verified `packaging/` release directory.
- Engine-real PMTransformer/PORMAKE execution and packaged-asset path verification.
- A separately scoped provider smoke for production model compatibility.

Do not describe the Demo as browser-validated, Windows-ready, engine-real, or production-ready until those gates have their own evidence.

### Known production-mode generation failure (documentation-only)

Some production structured-generation paths still reference Gemini preview model names such as `gemini-3-pro-preview` and `gemini-3-flash-preview`. A bounded audit recorded a provider `404 NOT_FOUND`/decommissioning failure for that path. This candidate documents the limitation only: it does not select a replacement model or change provider/generation code. Model repair requires a separately scoped opt-in provider smoke with credentials and independent review.

## Linux/WSL-first development

Use the repository root for the following commands. The current checked path uses Python 3.11 and Node.js 16 or newer.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cd frontend
npm install
cd ..
```

The root `requirements.txt` is the authoritative Python dependency source. Frontend dependencies are declared by `frontend/package.json` and its lockfile. No dependency or lockfile update is required for this Demo candidate; do not run an automatic dependency mutation such as `npm audit fix` as release preparation.

### Launch

Start the backend and Vite development server together:

```bash
./start_react.sh
```

The combined script requires `.venv`, starts the backend on port 8000, starts Vite, and writes generated logs under `logs/`. Use the frontend URL printed by Vite or recorded in `logs/frontend.log`; do not assume a fixed frontend port. Backend API documentation is available at:

```text
http://localhost:8000/api/docs
```

For backend-only development:

```bash
./run_backend.sh
```

Stop services started by the combined script with `Ctrl+C`. Do not kill unrelated Python or Node processes.

## Verification commands

The repository intends `not external` to be the safe backend loop. The current
rough candidate still has a test-isolation gap: the latest run emitted outbound
Gemini requests from existing real-path tests even though the tests were not
marked `external`. Treat this command as a regression loop, not as proof that
the checkout makes no provider calls.

```bash
.venv/bin/python -c "import backend.main; print('backend.main import ok')"
.venv/bin/pytest -c tests/pytest.ini -m "not external" --tb=short -q
```

Run the focused Version A Demo tests:

```bash
.venv/bin/pytest -c tests/pytest.ini \
  tests/test_demo_cross_stage_handoffs.py \
  tests/test_unified_demo_smoke.py -q
```

Run the frontend checks from `frontend/`:

```bash
npm run lint
npm run build
npm run test:proposal-demo
npm run test:mof
```

Latest local candidate check (2026-08-10): the backend import passed; the
focused Demo/fixture set passed 84 tests; the full `not external` selection
passed 327 tests, skipped 1, and retained 5 known path-drift failures in the
paper-download tests. Frontend lint passed. The first default-heap build hit
the Node heap limit; `NODE_OPTIONS=--max-old-space-size=4096 npm run build`
passed with existing Vite bundle warnings. The two frontend fixture checks
passed (proposal fixtures and six CIF-charge parser assertions).

These checks provide local application, API, static-build, and fixture
evidence. They do not substitute for the open browser, Windows, engine-real,
or external-provider gates above. Real-provider checks are opt-in and must be
marked `external`; never put API keys in source control.

## Product surfaces

The maintained application is the React + FastAPI path:

- Proposal drafting, revision, citations, and experiment-detail workflows.
- Literature search, knowledge queries, chemical lookup, and document upload.
- MOF CIF viewing/generation, property prediction, and XRD presentation.
- Settings for provider configuration and the unified Demo switch.

Demo fixtures are separate from production provider code. User-generated papers, uploads, vector indexes, parsed chemicals, MOF runs, and other runtime data belong under the configured `local_data/` root and must not be committed.

## Documentation map

- `AGENTS.md` — agent and repository contract.
- `CONTRIBUTING.md` — human development workflow.
- `tests/README_TESTING.md` — test markers and safe/external test policy.
- `docs/demo-mode-spec.md` — Version A behavior specification.
- `docs/demo-v1-windows-installer.md` and `docs/windows-demo-release-sop.md` — future Windows packaging/release planning; not proof of a working installer.

## License

This project is licensed under the MIT License; see `LICENSE`.

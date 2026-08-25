# Demo Mode Spec / Demo 模式規格

Status: approved Version A contract; application/API evidence complete; browser visual/user validation pending
Date: 2026-05-29
Last reviewed: 2026-08-10

This spec defines the click-through demo version requested before real LLM/provider work. Demo mode must show the full product workflow without requiring a real API key, paid provider, external network, or user-managed `.env`.

本規格定義「點下按鈕後所有功能都是套好的」展示版本。Demo mode 必須讓非技術使用者可完整點過主要功能，不需要真實 LLM API key、付費 provider、外部網路，或自行編輯 `.env`。

## Goals

- Provide a stable product demo for personal use and colleague sharing.
- Let a non-technical Windows user install one packaged application and click through core workflows.
- Require no API key, no `.env`, no provider account, and no external network for the demo flow.
- Preserve a clean separation between demo fixtures and production provider code.
- Make demo behavior testable without network and without secrets.
- Avoid masking production failures: demo mode is explicit, visible, and never silently used as fallback for production mode.

## Non-Goals

- Do not implement OpenRouter in this TODO; that belongs to the provider-layer TODO.
- Do not remove Streamlit in this TODO.
- Do not rewrite frontend architecture as part of demo mode.
- Do not hardcode private API keys or real user data into fixtures.
- Do not make demo responses random; all demo output must be deterministic.

## Activation and Settings control — Version A

Required current behavior:

- Settings exposes exactly one user-facing **Demo mode** switch.
- When the switch is ON, all four Demo stages are enabled: Proposal, Property Prediction, Generate New Idea/Revision, and Experiment Detail.
- When the switch is OFF, all four stages use their real paths.
- The Settings API write-through keeps `enabled` and the four persisted `mock_*` fields aligned when `enabled` is submitted; GET returns the stable five-field settings shape.
- `mock_proposal`, `mock_property_prediction`, `mock_generate_new_idea`, and `mock_experiment_detail` are internal compatibility/state fields, not independent Settings controls.
- `DEMO_MOCK_*` environment variables are test-only stage overrides. Mixed-stage behavior belongs to tests, not to the user-facing Settings surface.
- Settings may show a visible `Demo` tag or banner when the unified switch is active.

Rules:

- When the unified setting is ON, supported endpoints may return fixture-backed responses.
- When the unified setting is OFF, production paths must not silently use demo fixtures.
- If a production provider call fails, return a real error; do not fall back to demo data unless the request explicitly asks for demo behavior.

Windows packaging rule:

- A packaged Demo release must seed or enable the persisted Version A unified setting without asking the user to edit `.env` or set stage flags.
- The exact launcher/installer integration remains a separate, unverified release step; do not treat `DEMO_MODE=true` or four `DEMO_MOCK_*` assignments as the current user contract.
- Settings may show production API-key controls as optional "real use" controls, but the Demo path must not require a key.

## Verification status

- Application/API cross-stage evidence is complete: `tests/test_demo_cross_stage_handoffs.py` and `tests/test_unified_demo_smoke.py` passed five focused tests.
- Independent reviewer `t_336076ea` returned literal `APPROVE`; the historical pre-minimal-harness orchestration gate `t_b0a56989` also recorded `APPROVE`. The reviewer regression set passed 156 tests and strict marker collection selected 5 of 355.
- These checks do not prove browser rendering or a Windows installer run. Browser visual/user validation remains pending and is a release gate.

## User Flow

The expected demo path:

1. User opens the app.
2. App detects demo mode and does not redirect to Settings for missing API keys.
3. Dashboard displays prepared stats and recent activity.
4. User opens Proposal and clicks generate.
5. Proposal output appears with citations, chunks/sources, and chemical/safety references.
6. User highlights text and tries explanation/revision flows.
7. User opens Search and sees prepared local and online paper search results.
8. User opens Knowledge Query and asks a prepared or arbitrary question; demo returns deterministic answer with citations.
9. User opens Chemical and searches a supported compound; demo returns PubChem-like data and structure fields.
10. User opens Upload and simulates upload/progress/result without storing private files.
11. User opens Settings and sees one unified Demo switch plus where real API keys would be entered for production mode.
12. In the MOF workflow, the same unified Demo switch drives Proposal, Property Prediction, the ten Demo CIF/XRD results, Revision, and Experiment Detail without separate stage controls.

## Fixture Layout

Recommended backend fixture root:

```text
backend/demo_fixtures/
  dashboard.json
  proposal.json
  search_papers.json
  knowledge_query.json
  chemical_records.json
  upload_result.json
  text_interaction.json
```

Rules:

- Fixtures are backend-owned because API response shapes should stay close to backend schemas.
- Frontend may include tiny UI-only sample constants only when no backend endpoint exists yet.
- Fixtures must contain fake/synthetic research data or public-domain style examples, not copied private lab data.
- Fixtures should include stable IDs, timestamps, source IDs, and enough content to render realistic UI states.
- If a fixture represents an external provider response, name the source shape clearly, for example `pubchem_like_record`, not `pubchem_raw_response`.

## Backend Design

Add a small demo boundary instead of sprinkling fixture reads through route handlers.

Recommended modules:

```text
backend/core/demo_config.py
backend/services/demo_service.py
backend/demo_fixtures/*.json
```

Responsibilities:

- `demo_config.py`: resolve the persisted unified setting and test-only `DEMO_MOCK_*` stage overrides.
- `demo_service.py`: load typed fixture data and expose helper methods such as `get_demo_proposal()`.
- Route handlers: branch early at the API boundary on the named stage; the user-facing Settings control remains unified.

Example shape:

```python
if demo_config.is_stage_demo("proposal"):
    return demo_service.get_proposal_response(request)
```

Do not:

- Put demo conditionals inside low-level LLM/provider clients.
- Let demo fixtures mutate vector stores or user upload directories.
- Make fixture lookup depend on real provider models.

## API Coverage

Minimum demo-supported endpoints:

| Workflow | Current frontend surface | Demo behavior |
|---|---|---|
| Config/status | `App.jsx`, `Settings.jsx` | Report setup as demo-ready without requiring API key |
| Dashboard | `Dashboard.jsx` | Return prepared upload stats/activity |
| Proposal | `Proposal.jsx` | Return a complete structured proposal with source chunks |
| Text interaction | TextHighlight components | Return explanation/revision fixture responses |
| Search | `Search.jsx` | Return prepared local and online paper results |
| Knowledge | `KnowledgeQuery.jsx` | Return answer plus citations/source IDs |
| Chemical | `Chemical.jsx` | Return compound properties, safety fields, and structure fields |
| Upload | `Upload.jsx` | Simulate task ID, progress, and processed result |

If an endpoint is not demo-supported, it should return a clear `501`/unsupported response only in demo mode, not a confusing provider error.

## Frontend Design

Demo mode should feel like the actual app, not a landing page.

Frontend requirements:

- Do not force Settings redirect when backend reports demo-ready.
- Show a compact `Demo` indicator in the app chrome or Settings page.
- Buttons keep their normal labels and states.
- Loading/progress states should still appear briefly enough to demonstrate workflow, but tests must not depend on real timers when avoidable.
- Error states remain visible when demo fixture lookup fails.

Avoid:

- Marketing copy as the first screen.
- Separate demo-only pages that bypass the actual workflows.
- Hardcoded API keys in React state, source files, or localStorage.

## API Key And Secret Rules

- Personal API keys are never committed.
- Production API keys are entered through frontend Settings or environment variables, depending on the implemented product flow.
- Demo mode must not require `.env`.
- Settings may store key presence/status, but docs must warn against committing real keys.
- Tests must not read real `.env` unless marked `external`.

## Test Plan

Spec-first test order:

1. Unit tests for `demo_config`:
   - default false
   - parses true values
   - rejects accidental truthy strings only if the project chooses strict parsing
2. Unit tests for `demo_service`:
   - loads each fixture
   - validates required keys
   - returns deterministic data
3. API tests for demo branches:
   - config/status reports demo-ready
   - proposal route returns fixture response
   - search route returns fixture response
   - knowledge route returns fixture response
   - chemical route returns fixture response
   - upload status can progress deterministically
4. Frontend smoke:
   - app does not redirect to Settings in demo mode
   - each primary page renders demo data after user action
5. Application/API cross-stage smoke:
   - unified ON and unified OFF exercise the real FastAPI route chain and handoff fields
   - Proposal, Revision, Experiment Detail, generator, property, and XRD boundaries are covered
6. Browser/CDP smoke (still pending user-side evidence):
   - title and readyState are valid
   - visible text includes dashboard/proposal/search/knowledge/chemical/upload signals

Required markers:

- Fixture-backed tests: `unit`, `api`, or `integration`
- Real provider checks: `external`
- Browser/full-stack checks: `e2e`

## Acceptance Criteria

Demo mode is complete when:

- A Windows user can install and launch the packaged demo without Git, terminal commands, Node.js, pip, or a real API key.
- A user can complete the main demo flow without a real API key or network.
- Backend import smoke still passes.
- `pytest -c tests/pytest.ini --collect-only` passes.
- Demo-specific backend tests pass without network.
- `npm run build` passes.
- Browser smoke confirms the app renders demo surfaces; this remains an outstanding user-side gate and is not currently claimed as passed.
- Windows installer smoke (pending) must confirm the packaged launcher opens the app and demo mode is active.
- Documentation explains how to build the Windows installer and how a non-technical user launches the no-key demo.

## Implementation Order

1. Add `demo_config` and `demo_service` tests first.
2. Add minimal fixtures for each primary workflow.
3. Add backend demo branches endpoint by endpoint.
4. Update frontend demo readiness so Settings redirect does not block demo.
5. Seed/enable the Version A unified Demo setting in the Windows launcher/package without exposing per-stage controls.
6. Package demo fixtures and required static assets into the installer stage.
7. Add page-level demo smoke tests or manual CDP verification.
8. Verify the Windows installer/launcher path.
9. Update README/SOP only after commands are verified.

## Open Questions For Implementation

- Which exact proposal route should own demo proposal generation if current route contracts differ from frontend expectations?
- Should demo upload simulate progress entirely in frontend or through backend status polling fixtures?
- Resolved: Version A uses one unified Settings switch; per-stage fields are internal/test-only state and `DEMO_MOCK_*` overrides.
- Should chemical demo records be synthetic-only or include public facts for common compounds?

# AI Research Agent - Agent Working Contract

This file is the repo-local contract for Codex, Antigravity, and any other AI agent working in this repository.

本文件是本 repo 的 AI agent 工作契約。所有後續維修、測試、偵錯、文件整理與功能開發都以這份文件為優先依據。

## Product Direction

- Primary use: personal research tool shared with colleagues.
- Development environment: Linux/WSL first.
- End-user target: Windows-friendly demo/release for non-technical users.
- Current architecture: React + FastAPI is the mainline.
- Legacy Streamlit/app-era references are historical only unless explicitly restored.
- Near-term product goal: prepare a demo mode where the user can click through all major features with pre-baked results and no real LLM API key.

## Agent Mission

Agents are responsible for keeping this repository easy for agents and humans to maintain.

- Prefer small modular changes over broad rewrites.
- Preserve existing user-facing behavior unless a spec says otherwise.
- Update tests/specs before changing behavior.
- Do not silently depend on personal API keys, local-only paths, or external services.
- Do not introduce new dependencies without an explicit reason and user approval.
- Keep documentation and executable reality aligned.

## Mandatory Reading Order

Every new session and every new agent must read these files before making non-trivial changes:

1. `AGENTS.md` - this contract and the current architecture/testing rules.
2. `README.md` and the relevant public feature/spec documents under `docs/` - current user-facing behavior, setup, and release boundaries.
3. `CONTRIBUTING.md` - human developer setup and workflow.
4. `tests/README_TESTING.md` - test markers, mock/external API policy, and commands.
5. Relevant nearby code and tests for the target module.

Antigravity note:

- `.agent/rules/project_rules.md` exists for Antigravity compatibility.
- If `.agent/rules/project_rules.md` conflicts with this file, this `AGENTS.md` is the canonical source.
- Keep `.agent/rules/project_rules.md` as a pointer/summary, not a divergent second policy.

## Architecture Boundaries

Backend:

- `backend/main.py`: FastAPI app creation, middleware, startup, router registration.
- `backend/api/routes/`: HTTP request/response boundary only. Validate inputs, call services, return API responses.
- `backend/api/models/`: Pydantic request/response/data-transfer schemas.
- `backend/services/`: business logic, research workflows, document processing, external API orchestration.
- `backend/services/analysis/`: scientific data parsers and analysis routines.
- `backend/core/`: configuration, LLM abstractions, retrieval/vector infrastructure, shared generation utilities.
- `backend/utils/`: cross-cutting helpers, logging, exceptions, validators.

Frontend:

- `frontend/src/pages/`: route-level screens.
- `frontend/src/components/`: reusable UI components.
- `frontend/src/contexts/`: app-wide state providers.
- API calls should be centralized in service/hooks modules when added or refactored. Do not scatter endpoint construction across page components.
- Components should focus on rendering and interaction state, not backend data reshaping.

Demo mode:

- Demo behavior must be explicit, testable, and separated from production API calls.
- Demo mode must not require a real OpenAI, Gemini, OpenRouter, Europe PMC, or PubChem key.
- Demo fixtures should live in predictable fixture/data modules, not inline in UI components.

## TDD And Specs

Use spec-first development.

1. Write or update a short spec before changing behavior.
2. Write or update regression/unit tests from the spec.
3. Confirm the new/updated test fails for the old behavior when practical.
4. Implement the smallest change that passes the test.
5. Run the verification tier matching the risk.
6. Update docs when workflow, architecture, or user-visible behavior changes.

For bug fixes:

- First capture the bug as a failing test or explicit reproduction note.
- If an existing spec is wrong, update the spec before changing code.
- Do not patch around a failing test without deciding whether the test or code is authoritative.

For `backend/services/analysis/`:

- Add or update tests with representative raw/scientific input before changing parsers.
- Document expected units, accepted ranges, and malformed-input behavior.

## Test Strategy

Testing is layered. Unit tests passing does not prove the app works end-to-end; it proves the smallest logic units are protected.

Markers:

- `unit`: isolated logic, no network, no real API keys.
- `integration`: multiple backend modules connected together, but external services mocked or replaced with local fakes unless explicitly marked.
- `api`: FastAPI route/schema behavior.
- `e2e`: user-level workflow, browser or full-stack where available.
- `slow`: expensive or long-running tests.
- `external`: real network/API smoke tests. Never part of the default quick loop.

External API policy:

- Default unit tests must not call real external services.
- Use mocks/fakes for OpenAI, Gemini, OpenRouter, PubChem, Europe PMC, Chroma, filesystem-heavy paths, and browser automation unless the test is explicitly marked `external`.
- `external` tests may read real `.env` values and use real services, but must be opt-in.
- Add a minimal real-provider smoke test when a provider integration changes; do not rely only on mocks for provider compatibility.

Recommended verification tiers:

- Docs-only: inspect links/commands referenced by the changed docs.
- Backend unit change: targeted pytest plus `pytest -m "unit or fast"` when markers permit.
- Backend route/service change: targeted tests plus relevant `api` or `integration` tests.
- Frontend change: `npm run build`; run `npm run lint` when lint config is healthy.
- UI/demo change: browser smoke test through Chrome DevTools Protocol when available.
- Release/demo checkpoint: backend smoke, frontend build, browser smoke, and opt-in external provider smoke if keys are available.

Verification matrix:

| Change type | Minimum verification | Additional verification when risk rises |
|---|---|---|
| Docs-only | Link/path/command scan in changed docs | None unless commands were changed materially |
| Test/docs policy | `pytest --collect-only` after marker edits | Targeted pytest if tests were edited |
| Backend pure service | Targeted unit test | `pytest tests -m "unit or fast"` after marker cleanup |
| Backend route/schema | Targeted route/model tests | API/integration tests for affected endpoint |
| LLM/provider | Provider contract tests with fake provider | Opt-in `external` smoke for real provider |
| Frontend component/page | `npm run build` | `npm run lint`, browser/CDP smoke |
| Demo mode | Demo fixture tests | Browser/CDP smoke of click-through path |
| Packaging/Windows scripts | Read script and dry-run-safe checks | Manual Windows validation before release |

Current known limitation:

- Some existing tests and docs predate this contract. When touching a module, align nearby tests/docs with this contract instead of preserving stale claims.

## Build And Run SOP

Development on Linux/WSL:

```bash
./run_backend.sh
```

or:

```bash
./start_react.sh
```

The combined script starts backend and frontend and writes logs under `logs/`.

Frontend development:

```bash
cd frontend
npm install
npm run dev
npm run build
```

Backend development:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

API docs:

- Canonical docs URL: `http://localhost:8000/api/docs`
- Health check: `http://localhost:8000/health`

Ports:

- Backend default: `8000`.
- Frontend dev port is Vite-controlled. Prefer the URL printed by Vite/logs over hardcoding. Existing docs may mention `3000` or `5173`; verify the running server.

Windows use:

- Windows `.bat` scripts are for user-facing/demo convenience.
- Keep Linux/WSL scripts working for development.
- Do not remove Windows launch paths without an explicit migration plan.

## Secrets And Environment

- Never hardcode personal API keys, tokens, or private paths.
- `.env` can contain user-local secrets and must not be committed.
- A dummy `.env` placeholder may exist only to let the backend start and let users configure keys in the frontend Settings page.
- Dummy keys must be treated as invalid for real provider calls.
- Real provider tests must be opt-in and marked `external`.
- If demo mode exists, it must not need real secrets.

## User Data & Privacy Policy

This repository is developed collaboratively with AI agents. To prevent
accidental leakage of user-generated data or secrets, the following rules
are mechanically enforced by `scripts/security_preflight.sh` and the
pre-commit hook in `.pre-commit-config.yaml`. Agents must also follow them
by intent.

Runtime data root:

- All user-generated data — uploaded papers, vector indexes, parsed
  chemicals, MOF runs, proposal history, and any future workspace-scoped
  storage — MUST be written under `local_data/` via the runtime data root
  exposed by `backend/core/config.py`. Do not scatter user data across
  the repo or hardcode absolute paths.
- `local_data/` is already gitignored and must stay that way.

Never `git add` any of the following:

- `local_data/`, `user_data/`, `private_data/`
- `.env`, `.env.*` (any environment file)
- `*.pdf`, `*.cif`, `*.ckpt`, `*.pt`, `*.pth` outside the explicit
  synthetic allowlist under `tests/test_data/`
- `papers/`, `vector_index*`, `parsed_chemicals*`
- MOF run outputs generated outside `tests/test_data/`

Feature work that persists user data:

- Route through the runtime data root abstraction in
  `backend/core/config.py`. Do not invent new top-level directories.
- If a genuinely new storage location is required, place it under
  `local_data/` and update `.gitignore` in the same commit.

Commit hygiene:

- Never run `git add .` or `git add -A`. Always stage by explicit path.
- Before every commit, `scripts/security_preflight.sh` must exit 0.
  The pre-commit hook runs it automatically; do not bypass with
  `--no-verify` without user consent.

Test fixtures:

- Files under `tests/test_data/` may be committed ONLY if they are
  synthetic: no real user chemistry, no real paper PDFs, no real API
  keys, no personally identifiable data. When in doubt, treat the file
  as private and keep it under `local_data/`.

## Documentation Ownership

- `README.md`: user-facing overview, install, launch, demo usage.
- `CONTRIBUTING.md`: human developer workflow.
- `AGENTS.md`: AI-agent workflow and repository contract.
- `tests/README_TESTING.md`: current test taxonomy, commands, and marker rules.
- Public feature/spec documents under `docs/`: user-facing behavior, setup, and release notes. Keep local Agent handoff and dirty-worktree state out of the public tree.
- Old Streamlit or `research_agent/app` references should be removed or clearly marked legacy when encountered.

## Change Discipline

Before editing:

- Read the relevant files and nearby tests.
- Check for existing user changes. Do not revert unrelated dirty work.
- Identify the smallest module boundary that owns the change.
- Do not push to GitHub or any remote unless the user gives explicit verbal approval in the current conversation. Local commits are allowed when useful, but remote publication requires user confirmation each time.

During editing:

- Keep routes thin and services testable.
- Prefer Pydantic models for cross-boundary structured data.
- Avoid duplicating API endpoint strings in the frontend.
- Keep demo fixtures separate from production logic.

Before reporting completion:

- State changed files.
- State which verification ran and what it proved.
- State any verification not run and why.
- State remaining risks.

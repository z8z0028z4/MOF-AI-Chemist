# Contributing to AI Research Assistant

This project is maintained as a personal research assistant that can be shared with colleagues. Development happens primarily on Linux/WSL; Windows launch paths are preserved for demo and non-technical users.

本專案以個人研究與同事分享為主。開發以 Linux/WSL 為主，Windows 啟動流程保留給 demo 與非技術使用者。

## Current Architecture

The active architecture is React + FastAPI.

```text
frontend/                 React 18 + Vite + Ant Design
  src/pages/              Route-level screens
  src/components/         Reusable UI components
  src/contexts/           Shared frontend state

backend/                  FastAPI backend
  main.py                 App setup, middleware, startup, router registration
  api/routes/             Thin HTTP boundaries
  api/models/             Pydantic schemas
  services/               Business/research logic and external API orchestration
  services/analysis/      Scientific analysis parsers
  core/                   Config, LLM, retrieval, vector, generation infrastructure
  utils/                  Shared helpers, logging, exceptions, validators
```

Legacy Streamlit or `research_agent/app` references are historical only. Do not add new work to that path unless a migration task explicitly says so.

## Setup

### Linux/WSL Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cd frontend
npm install
cd ..
```

Run backend only:

```bash
./run_backend.sh
```

Run backend and frontend together:

```bash
./start_react.sh
```

Backend docs are served at:

```text
http://localhost:8000/api/docs
```

Frontend dev URL should come from Vite output or `logs/frontend.log`; do not assume one fixed port without checking.

### Windows Demo/User Path

Windows `.bat` scripts remain supported for non-technical users and demo builds. Keep them working when changing launch behavior, but prefer WSL/Linux for development and debugging.

## Development Rules

- Follow the repo-local [AGENTS.md](AGENTS.md) contract.
- Keep changes modular and scoped to the owning layer.
- Keep FastAPI routes thin: validate request, call services, return response.
- Put business/research logic in `backend/services/`.
- Use Pydantic models for structured data crossing API/service boundaries.
- Prefer frontend service/hooks modules for API calls instead of scattering endpoint strings in components.
- Keep demo-mode fixtures separate from production API logic.
- Never hardcode API keys, tokens, or personal paths.

## TDD Workflow

Use spec-first development:

1. Write or update a short spec for the intended behavior.
2. Write or update unit/regression tests from that spec.
3. Confirm the new test fails against the old behavior when practical.
4. Implement the smallest change that satisfies the spec.
5. Run the relevant verification tier.
6. Update docs when behavior, commands, or architecture changes.

For bug fixes, capture the bug as a failing test or explicit reproduction before patching.

For `backend/services/analysis/`, add representative raw/scientific input tests before changing parsers. Document units, accepted ranges, and malformed-input behavior.

## Test Strategy

Use a layered test strategy. Unit tests passing does not prove the whole app works; it proves the smallest logic units are protected.

Markers:

- `unit`: isolated logic, no network, no real API keys.
- `integration`: connected modules, external services mocked/faked unless explicitly marked.
- `api`: FastAPI route/schema behavior.
- `e2e`: user-level workflow.
- `slow`: long-running tests.
- `external`: real network/API smoke tests, opt-in only.

Default tests should not call real OpenAI, Gemini, OpenRouter, PubChem, Europe PMC, or other external services. Provider compatibility should be covered by a small opt-in `external` smoke test when integration code changes.

Recommended commands:

```bash
# All available Python tests
pytest tests -v

# Fast or unit-focused loop, when markers are available
pytest tests -m "unit or fast"

# Coverage report
pytest --cov=backend --cov-report=term-missing tests

# Frontend build verification
cd frontend
npm run build
```

Run `npm run lint` when touching frontend code and the lint config is healthy.

For UI/demo changes, use a browser smoke test through Chrome DevTools Protocol when available.

## Demo Mode Direction

The near-term product goal is a demo version where a user can click through major functions without providing a real LLM API key.

Demo mode must:

- Use explicit demo fixtures, not hidden production fallbacks.
- Avoid real provider calls by default.
- Exercise the same UI surfaces as production where practical.
- Be testable through unit/integration/browser smoke tests.
- Make it visually clear when data is demo data.

## Review Checklist

- [ ] Behavior has a spec or reproduction note.
- [ ] Tests match the spec and are in the right layer.
- [ ] Routes, services, models, and frontend components keep their boundaries.
- [ ] No API keys or secrets are hardcoded.
- [ ] Demo behavior is separated from production calls.
- [ ] Verification commands were run and reported.
- [ ] User-facing docs changed when commands or behavior changed.

## Commit Messages

When committing through Codex/OMX, follow the workspace Lore Commit Protocol from the higher-level instructions. If committing manually, include the intent, tested scope, and known gaps.

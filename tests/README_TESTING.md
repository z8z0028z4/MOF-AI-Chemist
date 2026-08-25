# Testing Guide / 測試指南

This guide describes the current testing direction for the React + FastAPI codebase.

本文件描述目前 React + FastAPI 架構下的測試策略。若其他舊文件提到不存在的測試檔或「全部真實 API、零 mock」，以本文件與 repo-local `AGENTS.md` 為準。

## Core Principle

Use a layered test strategy.

單元測試通過不代表整個 app 一定能實際運行；它代表小模組邏輯有保護。實際信心需要 unit、integration、API、browser smoke、external smoke 分層建立。

## Test Layers

| Layer | Marker | Purpose | External network/API |
|---|---|---|---|
| Unit | `unit` | Small functions/classes, schema transforms, pure service logic | Never |
| Integration | `integration` | Multiple backend modules working together | Mock/fake by default |
| API | `api` | FastAPI routes, request/response schemas, error responses | Mock/fake by default |
| E2E | `e2e` | User-level workflow or browser/full-stack path | Avoid unless explicitly needed |
| Slow | `slow` | Long-running local tests | Case by case |
| External | `external` | Real provider/network smoke tests | Allowed, opt-in only |

External provider examples: OpenAI, Gemini, OpenRouter, PubChem, Europe PMC, remote paper databases, and any paid/rate-limited service.

## External API Policy

Default tests must not call real external services or require real API keys.

Use this split:

1. Unit tests use mocks/fakes and local fixtures.
2. Integration/API tests use local fake providers or mocked external clients.
3. `external` smoke tests may use real `.env` keys and real services, but are never part of the default loop.

This avoids two failure modes:

- Mock-only confidence where production provider calls still fail.
- Slow/flaky/expensive default tests caused by network, rate limits, missing keys, or provider downtime.

## Current Test Files

Current files in this repository include:

```text
tests/
  conftest.py
  pytest.ini
  test_chemical_search.py
  test_core_env_manager.py
  test_core_modules.py
  test_core_settings_manager.py
  test_external_paper_search.py
  test_paper_search.py
  test_proposal_form_improvements.py
  test_services.py
```

Do not reference old planned files such as `test_api.py`, `test_e2e.py`, or `test_frontend_components.py` unless they are actually added.

## Running Tests

From the repository root (make sure to specify `-c tests/pytest.ini` so pytest registers the custom markers):

```bash
# Run safe default tests (excludes external network/API key dependent tests)
pytest -c tests/pytest.ini -m "not external"

# All Python tests (including external)
pytest -c tests/pytest.ini tests -v

# One file
pytest -c tests/pytest.ini tests/test_core_modules.py -v

# One test
pytest -c tests/pytest.ini tests/test_core_modules.py::TestConfigManagement::test_settings_loading -v

# Coverage
pytest -c tests/pytest.ini --cov=backend --cov-report=term-missing tests
```

Marker-focused commands, now that tests are consistently marked:

```bash
pytest -c tests/pytest.ini -m unit
pytest -c tests/pytest.ini -m "unit or fast"
pytest -c tests/pytest.ini -m integration
pytest -c tests/pytest.ini -m api
pytest -c tests/pytest.ini -m external
```

Frontend verification:

```bash
cd frontend
npm run build
npm run lint
```

`frontend/package.json` currently has build and lint scripts, but no dedicated frontend test script. Add a test framework only when a frontend change needs it.

## TDD Workflow

1. Write or update a spec.
2. Write or update the smallest failing test.
3. Implement the behavior.
4. Run the targeted test.
5. Run the matching verification tier.
6. Update docs when commands or behavior change.

For bug fixes:

- Capture the bug as a failing regression test or explicit reproduction note.
- If the current spec is wrong, correct the spec before changing code.

For demo mode:

- Write tests against explicit demo fixtures.
- Do not silently fall back to demo data inside production provider code.
- Browser smoke should confirm that demo paths render usable content without real API keys.

## Fixture And Mock Guidance

- Put reusable fakes in `conftest.py` or focused helper modules.
- Mock at the boundary closest to the external service, not deep inside pure logic.
- Prefer fake provider classes for LLM/provider layers so OpenRouter/OpenAI/Gemini behavior can share contract tests.
- Keep fixtures small, representative, and deterministic.
- Do not read the real `.env` in unit tests.

## Marking Rules

When adding or editing tests, mark intent explicitly:

```python
import pytest


@pytest.mark.unit
def test_parser_handles_empty_input():
    ...


@pytest.mark.external
def test_openrouter_structured_output_smoke():
    ...
```

If a test requires network, real API keys, a live browser, or a running backend/frontend, it must not masquerade as `unit`.

## Completion Standard

A change is not verified because one unit test passes. Report the verification tier:

- Targeted test: proves the immediate behavior.
- Unit/fast suite: reduces local regression risk.
- Integration/API: proves module boundaries still connect.
- Frontend build/lint: proves the UI bundle and static checks still pass.
- Browser/CDP smoke: proves a real page can load and render.
- External smoke: proves provider compatibility with real network/API behavior.

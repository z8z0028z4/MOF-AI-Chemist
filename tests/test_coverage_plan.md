# Test Coverage Plan / 測試覆蓋計劃

This is a living plan. It should describe real files and realistic targets, not aspirational claims.

本文件是動態計劃，只描述目前實際存在或明確待補的測試方向，不宣稱不存在的測試已完成。

## Current Baseline

Existing Python test files:

```text
tests/test_chemical_search.py
tests/test_core_env_manager.py
tests/test_core_modules.py
tests/test_core_settings_manager.py
tests/test_external_paper_search.py
tests/test_paper_search.py
tests/test_proposal_form_improvements.py
tests/test_services.py
```

Supporting files:

```text
tests/conftest.py
tests/pytest.ini
tests/README_TESTING.md
tests/run_tests.py
```

## Coverage Priorities

### P0: Agent-Safe Maintenance Baseline

- [ ] Mark existing tests with `unit`, `integration`, `api`, `slow`, or `external`.
- [ ] Ensure default test loop does not require real API keys or network.
- [ ] Add regression tests before changing behavior.
- [ ] Add provider contract tests for LLM abstraction before adding OpenRouter.
- [ ] Add demo-mode fixture tests before implementing demo behavior.

### P1: Backend Module Coverage

- [ ] `backend/api/routes/`: request validation, response shape, error handling.
- [ ] `backend/api/models/`: schema validation for demo and production payloads.
- [ ] `backend/services/`: business logic and external-service orchestration.
- [ ] `backend/services/analysis/`: representative scientific input, units, malformed input.
- [ ] `backend/core/`: LLM/provider abstraction, settings, env handling, retrieval contracts.

### P2: Frontend And Browser Confidence

- [ ] Add frontend test framework only when needed by a concrete UI change.
- [ ] Use `npm run build` as the minimum frontend static verification.
- [ ] Use Chrome DevTools Protocol smoke tests for demo/user-flow changes.
- [ ] Add Playwright or Vitest only with an explicit scope and maintenance plan.

### P3: External Provider Smoke

- [ ] Add opt-in `external` smoke tests for OpenRouter structured output.
- [ ] Keep OpenAI/Gemini provider smokes opt-in.
- [ ] Keep PubChem/Europe PMC smokes opt-in and rate-limit aware.
- [ ] Never run `external` tests in the default quick loop.

## Test Pyramid

| Layer | Target | Notes |
|---|---|---|
| Unit | Most tests | Fast, deterministic, no network, no real secrets |
| Integration/API | Important module seams | Mock/fake external providers by default |
| Browser/E2E | Key user/demo flows | Fewer tests, higher confidence, slower |
| External | Provider compatibility | Opt-in, small, real network/API |

## Commands

```bash
# All Python tests
pytest tests -v

# Targeted test
pytest tests/test_core_modules.py -v

# Coverage
pytest --cov=backend --cov-report=term-missing tests

# Frontend static verification
cd frontend
npm run build
```

Future marker commands after cleanup:

```bash
pytest tests -m unit
pytest tests -m "unit or fast"
pytest tests -m integration
pytest tests -m api
pytest tests -m external
```

## Definition Of Done For New Features

- Spec is written or updated.
- Unit/regression test exists for core behavior.
- Integration/API test exists when a route/service boundary changes.
- Frontend build passes when UI changes.
- Browser smoke passes when user workflow or demo behavior changes.
- External smoke is run only when provider compatibility is the claim.

## Known Cleanup Items

- Existing docs previously referenced planned files such as `test_api.py`, `test_e2e.py`, and `test_frontend_components.py`; those names should not be used as evidence until files are actually added.
- Some tests and docs predate the mock/external split. Align them opportunistically when touching nearby code.
- Coverage percentages should be reported from actual `pytest-cov` output, not manually claimed.

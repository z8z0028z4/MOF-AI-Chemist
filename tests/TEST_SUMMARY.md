# Test Status Summary / 測試現況摘要

This file summarizes the current testing posture. It intentionally avoids claiming 100% coverage or "zero mock" unless backed by current test output.

本文件描述目前測試現況，不再沿用舊文件中「所有功能 100% 覆蓋」或「零 mock」等未經目前測試輸出佐證的結論。

## Current Test Inventory

Existing test files:

```text
test_chemical_search.py
test_core_env_manager.py
test_core_modules.py
test_core_settings_manager.py
test_external_paper_search.py
test_paper_search.py
test_proposal_form_improvements.py
test_services.py
```

Configuration/support files:

```text
conftest.py
pytest.ini
run_tests.py
README_TESTING.md
test_coverage_plan.md
```

## Current Testing Direction

- Default tests should be deterministic and should not require real network access or real API keys.
- External provider compatibility should be tested through explicit opt-in `external` smoke tests.
- Demo-mode behavior should be covered with explicit demo fixtures.
- Provider layers should use contract tests so OpenAI, Gemini, and future OpenRouter support can be checked consistently.

## What Is Protected Today

Based on current file names and fixtures, the repository has coverage surfaces for:

- Core configuration/settings modules.
- Environment manager behavior.
- Service-layer behavior.
- Paper search behavior.
- Chemical search behavior.
- Proposal form improvements.
- Some external paper search behavior.

The exact pass/fail and coverage percentages must come from running pytest, not this document.

## Known Documentation Corrections

Older versions of this file referenced tests that are not currently present, including:

- `test_api.py`
- `test_e2e.py`
- `test_e2e_real.py`
- `test_frontend_components.py`
- `test_utils.py`
- `test_services_metadata.py`
- `test_services_additional.py`

Do not use those names as evidence of test coverage until files are actually added.

## Recommended Verification Commands

```bash
# All current Python tests
pytest tests -v

# Coverage snapshot
pytest --cov=backend --cov-report=term-missing tests

# Frontend static verification
cd frontend
npm run build
```

When markers are fully normalized:

```bash
pytest tests -m unit
pytest tests -m integration
pytest tests -m api
pytest tests -m external
```

## Next Cleanup Targets

- Normalize pytest markers across existing tests.
- Separate external/network tests from the default test loop.
- Add missing API route tests only where route behavior is actively changed.
- Add browser smoke tests when demo-mode UI work begins.
- Report actual coverage from `pytest-cov` before setting numeric gates.

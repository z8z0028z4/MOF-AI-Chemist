# Test Development Environment / 測試開發環境

This document is a lightweight orientation for test development. The canonical rules live in [README_TESTING.md](README_TESTING.md) and the repo-local [../AGENTS.md](../AGENTS.md).

本文件只提供測試開發環境導覽。實際測試規範以 [README_TESTING.md](README_TESTING.md) 與 [../AGENTS.md](../AGENTS.md) 為準。

## Environment

Backend tests:

```bash
source .venv/bin/activate
pytest tests -v
```

Coverage:

```bash
pytest --cov=backend --cov-report=term-missing tests
```

Frontend static verification:

```bash
cd frontend
npm run build
npm run lint
```

## Development Loop

1. Write or update the spec.
2. Add or update the smallest relevant test.
3. Run the targeted test.
4. Implement the code change.
5. Run the matching verification tier.
6. Record what was and was not verified.

## Test Pyramid

```text
Browser/E2E smoke     fewer, slower, proves user-visible flow
Integration/API       module seams and route contracts
Unit                  many, fast, deterministic
External smoke        opt-in only, real provider/network compatibility
```

## External Services

Default tests must not require:

- OpenAI/Gemini/OpenRouter keys
- PubChem or Europe PMC network availability
- browser sessions
- local private data paths

Use explicit `external` marker tests for real provider/network smoke checks.

## Current Known Cleanup

Some historical docs and tests were written before the current React + FastAPI maintenance contract. When touching tests, align them with:

- current file inventory
- pytest markers
- mock/fake by default
- opt-in external smoke
- demo fixtures separated from production provider code

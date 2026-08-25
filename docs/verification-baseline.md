# Verification Baseline / 驗證基準

Date: 2026-06-01

Status note: this is a historical pre-Demo baseline. Its recorded route smoke is general-app evidence, not proof of the current Demo UI click-through.

本文件記錄 demo mode 與 provider layer 開始前的已知驗證狀態。這是目前修復後的基準線，供後續 agent 接手。

## Environment

- Repo: `<repository-root>` (host path intentionally omitted)
- Python command: `.venv/bin/python`
- Pytest command: `.venv/bin/pytest -c tests/pytest.ini`
- Frontend package manager command used: `npm`
- Network availability during tests: restricted/offline from the agent sandbox.

## Results

| Check | Command | Result | Classification |
|---|---|---|---|
| Backend import smoke | `.venv/bin/python -c "import backend.main; print('backend.main import ok')"` | Pass | Usable baseline |
| Pytest collection | `.venv/bin/pytest -c tests/pytest.ini --collect-only` | Pass, 146 tests collected | Usable baseline |
| Safe collection | `.venv/bin/pytest -c tests/pytest.ini -m "not external" --collect-only` | Pass, 124 selected and 22 deselected | Usable baseline |
| Marker-focused local loop | `.venv/bin/pytest -c tests/pytest.ini -m "unit or fast"` | Pass, 18 passed, 128 deselected | Usable baseline |
| API contract slice | `.venv/bin/pytest -c tests/pytest.ini tests/test_api_contracts.py -q` | Pass, 7 passed | Usable baseline |
| Safe non-external suite | `timeout 120 .venv/bin/pytest -c tests/pytest.ini -m "not external" --tb=short -q` | Pass, 123 passed, 1 skipped, 22 deselected | Usable baseline |
| Frontend build | `npm run build` from `frontend/` | Pass | Usable baseline |
| Frontend lint | `npm run lint` from `frontend/` | Pass | Usable baseline |
| Browser/CDP smoke | Chrome CDP on `127.0.0.1:9222`, frontend tab `http://localhost:3000/upload` | Pass, route smoke for `/`, `/settings`, `/proposal`, `/search`, `/knowledge`, `/chemical` | Usable baseline |

## Current Notes

### TestClient sandbox behavior

FastAPI `TestClient` hangs inside the current Codex sandbox even for a minimal app. API suites should be run outside the sandbox with the exact command recorded above when verifying behavior.

### `unit or fast` is now a safe local smoke

The command now selects 18 deterministic local tests and passes.

The following tests previously loaded HuggingFace/SentenceTransformer embedding infrastructure while marked `fast`; they have been reclassified as `integration` + `slow`:

- `tests/test_core_modules.py::TestVectorStore::test_vectorstore_stats_real`
- `tests/test_core_modules.py::TestVectorStore::test_paper_vectorstore_loading_real`
- `tests/test_core_modules.py::TestVectorStore::test_experiment_vectorstore_loading_real`
- `tests/test_core_modules.py::TestRetrieval::test_real_document_search`

Observed failure:

- The tests try to reach `https://huggingface.co/BAAI/bge-base-en-v1.5/...`.
- The sandbox cannot resolve the host.
- The resulting error is `Cannot send a request, as the client has been closed`.

These tests are now marked `external`, so they are excluded from the safe default gate. Real vector-store validation still belongs in an opt-in integration smoke where HuggingFace/model cache and Chroma data are available.

### Repaired behavioral/API drift

The previous 17 `not external` failures were repaired or reclassified:

- Chemical-search route tests now match current response schemas and error messages.
- `GET /api/v1/chemical/database-search` compatibility is restored while preserving the POST endpoint.
- Retrieval code now supports current LangChain retrievers that expose `invoke()` and legacy retrievers that expose `get_relevant_documents()`.
- Real embedding/vectorstore/LLM/network tests are excluded from the safe gate via `external`.
- Added fake-backed route contract tests for settings config status, knowledge retrieval response shape, knowledge empty-result 404 behavior, proposal generation response shape, upload scheduling/status, and upload vector-stat response shape. These tests do not require real API keys, provider calls, HuggingFace downloads, or FastAPI `TestClient`.

## Frontend Notes

`npm run build` succeeds and produces `frontend/dist/`.

`npm run lint` now succeeds. `frontend/.eslintrc.cjs` is intentionally conservative: it ignores generated output and checks syntax plus React hook rules without forcing a broad style cleanup.

### Browser/CDP smoke

Recorded on 2026-06-01 using the WSL Chrome DevTools workflow:

- `/json/version` responded with Chrome `148.0.7778.181`.
- Runtime evaluation against `http://localhost:3000/upload` succeeded:
  - title: `AI Research Assistant`
  - readyState: `complete`
  - visible page text included sidebar navigation, upload page content, and vector statistics.
- Route smoke passed for:
  - `/`
  - `/settings`
  - `/proposal`
  - `/search`
  - `/knowledge`
  - `/chemical`
- No `pageerror`, navigation error, or console `error` was observed after fixing:
  - Proposal form duplicate `initialValue` warning.
  - Search `Tabs.TabPane` deprecation warning.
- Remaining console warnings are React Router v7 future-flag notices; they are not blocking runtime errors.

## Recommended Next Repair Order

1. Review the current worktree and stage only explicitly approved paths.
2. Run an opt-in `external` smoke only after API keys/model cache expectations are documented.
3. Start no-key canned demo mode implementation from `docs/demo-mode-spec.md`, or explicitly continue the Windows setup-key demo path as a separate scope.
4. After each repair, update this file with a new dated baseline.

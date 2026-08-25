# Frontend API Boundary / 前端 API 邊界

Status: Active page slices migrated; inactive Data Analyzer deferred
Date: 2026-06-01

This document records the frontend API service pattern introduced for TODO 5. The goal is to reduce page-level endpoint string duplication and make demo mode easier to support without scattering demo branches through UI components.

## Current Inventory

Direct API calls still exist in:

| Area | File | Current direct calls | Suggested service |
|---|---|---:|---|
| Data Analyzer | `frontend/src/pages/DataAnalyzer.jsx` | 2 | defer unless page is restored |

Initial service layer files:

- `frontend/src/services/apiClient.js`
- `frontend/src/services/settingsApi.js`

Initial migrated call:

- `frontend/src/App.jsx` now reads setup/config status through `getConfigStatus()`.

Migrated slices:

- `frontend/src/pages/Settings.jsx` now uses `settingsApi.js` for all `/settings/*` calls.
- `frontend/src/pages/Upload.jsx` and `frontend/src/pages/Dashboard.jsx` now use `uploadApi.js` for upload stats, refresh, file upload, and status polling.
- `frontend/src/pages/Search.jsx` now uses `paperApi.js` for local paper flows and `externalPaperApi.js` for Europe PMC validation, search, and download.
- `frontend/src/pages/Chemical.jsx` now uses `chemicalApi.js` for database stats, database list, and chemical search.
- `frontend/src/pages/KnowledgeQuery.jsx` now uses `knowledgeApi.js` for knowledge queries and `documentApi.js` for source document links.
- `frontend/src/pages/Proposal.jsx` now uses `proposalApi.js` for generate/revise/experiment-detail/DOCX calls and `documentApi.js` for source document links.
- `frontend/src/components/TextHighlight/TextHighlightProvider.jsx` now uses `textInteractionApi.js` for highlighted text interactions.

## Pattern

Use `apiClient.js` for shared API-base construction and response handling.

Use feature-specific service files for endpoint groups:

```text
frontend/src/services/
  apiClient.js
  settingsApi.js
  proposalApi.js
  searchApi.js
  chemicalApi.js
  uploadApi.js
  knowledgeApi.js
```

Page components should own:

- rendering
- UI state
- form state
- user interaction

Service modules should own:

- endpoint paths
- HTTP method/body construction
- common response parsing
- API-specific error normalization

## Migration Rules

- Move one page or endpoint group at a time.
- Preserve existing response shapes.
- Keep demo mode behind the same service boundary unless a route explicitly reports unsupported demo behavior.
- Run `npm run build` after each migration slice.
- Run `npm run lint` after each migration slice.

## First Slice Verification

Command:

```bash
cd frontend
npm run build
```

Result on 2026-05-29:

- Pass.
- Vite reports the existing large chunk warning.

Current lint status on 2026-06-01:

- `npm run lint` passes after adding `frontend/.eslintrc.cjs`.

## Next Slices

Recommended order:

1. Data Analyzer only if the page is restored to active navigation.

## Settings Slice Verification

Commands:

```bash
cd frontend
npm run lint
npm run build
```

Result on 2026-06-01:

- Pass.

## Search Slice Verification

Commands:

```bash
cd frontend
npm run lint
npm run build
```

Result on 2026-06-01:

- Pass.
- `Search.jsx` has no direct `axios`, `fetch`, or `/api/v1` endpoint construction after migration.

## Chemical Slice Verification

Commands:

```bash
cd frontend
npm run lint
npm run build
```

Result on 2026-06-01:

- Pass.
- `Chemical.jsx` has no direct `fetch`, `axios`, or `/api/v1` endpoint construction after migration.

## Proposal/Knowledge/TextHighlight Slice Verification

Commands:

```bash
cd frontend
npm run lint
npm run build
```

Result on 2026-06-01:

- Pass.
- `Proposal.jsx`, `KnowledgeQuery.jsx`, and `TextHighlightProvider.jsx` have no direct `fetch`, `axios`, or `/api/v1` endpoint construction after migration.

## Upload/Dashboard Slice Verification

Commands:

```bash
cd frontend
npm run lint
npm run build
```

Result on 2026-06-01:

- Pass.

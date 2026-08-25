# Demo v1 Windows Installer

Status: Version A app contract documented; Windows packaging and browser validation pending

This document defines the demo-v1 distribution target for non-developer users.

## User experience target

The user should only need to:

1. Run `AI-Research-Assistant-Demo-Setup-<version>.exe`.
2. Launch AI Research Assistant Demo from the desktop or Start Menu.
3. Click through Dashboard, Proposal, Search, Knowledge Query, Chemical, Upload, and text-highlight workflows using built-in deterministic demo data.

The user should not need Git, command prompts, `pip install`, `npm install`, source-code edits, `.env`, API keys, provider accounts, or network access for the demo flow.

Production/real-use API keys may be supported later from Settings, but that is not required for demo-v1 and must not block the demo path.

## Feature scope

Included in demo-v1:

- Dashboard
- Proposal
- Paper search
- Knowledge query
- Chemical lookup
- Upload
- Settings page with one unified Demo switch and optional production-key controls
- Text highlight interactions

The four `mock_*` fields are internal compatibility/test state only. They are not four independent Settings controls.

Hidden in demo-v1:

- Data Analyzer, because it is still pending and its route/config wiring is not ready for a simple demo.

## Maintainer build flow

From a Windows maintainer machine with Python, Node.js, npm, and optionally Inno Setup:

```powershell
.\packaging\windows\build_demo_release.ps1 -Version 0.1.0
```

The script builds `frontend/dist`, stages the backend and frontend under `release/demo-v1/stage`, creates a packaged launcher executable, prepares a local Python runtime from `packaging/windows/requirements-demo.txt`, pre-caches the default embedding model, and invokes Inno Setup when `iscc` is available.

For no-key demo-v1, the staged app must include:

- `backend/demo_fixtures/*`
- any fixture/static assets needed by demo responses
- launcher behavior that seeds/enables the Version A unified Demo setting
- no user-facing `DEMO_MOCK_*` stage switches; those variables remain test-only overrides
- no real API keys and no `.env`

If Inno Setup is not installed, the script falls back to Windows IExpress. If IExpress cannot produce an installer for the payload size, the script builds a PyInstaller-based installer stub that embeds the zipped staged app. If no installer compiler path succeeds, the staged app remains runnable from:

```text
release/demo-v1/stage/AI Research Assistant Demo.exe
```

## Installed layout

The installer uses a per-user install directory under Local AppData so the app can write user data without administrator permissions:

```text
%LOCALAPPDATA%\AI Research Assistant Demo\
  AI Research Assistant Demo.exe
  app\
    backend\
    frontend\dist\
    model_cache\
    local_data\
    uploads\
    temp_structures\
    settings.json
  runtime\venv\
  logs\
```

## Runtime behavior

The launcher starts:

- FastAPI backend on `127.0.0.1:8000`
- local frontend/static proxy on `127.0.0.1:3000`

The frontend proxy serves `frontend/dist` and forwards `/api/*` to the backend, so the installed app does not need Node.js or Vite. The packaged demo must start with the Version A unified setting enabled and must serve fixture-backed responses without provider calls. The exact launcher integration is still unverified. If model caches remain in the package, they are optional for later real-use mode and should not be required for the no-key demo path.

## Release checklist

- Build the installer from a clean checkout.
- Run the installed app on a Windows account without developer tools.
- Confirm the app does not ask for an API key.
- Confirm Settings reports demo mode active and setup ready.
- Confirm Settings presents one unified Demo switch; do not expect per-stage controls.
- Confirm Upload, Search, Knowledge Query, Proposal, and Chemical pages load.
- Confirm demo actions return deterministic fixture data without network.
- Confirm Data Analyzer is not visible in the sidebar.
- Confirm the installer artifact contains no `.env` and no real API keys.
- Record a separate browser visual/user pass; API/test evidence alone is not release proof.

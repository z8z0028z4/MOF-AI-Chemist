# Windows Demo / Release SOP

Status: planning SOP; Version A unified Demo contract documented; Windows/browser validation pending
Date: 2026-05-29

This document defines the intended Windows-friendly path for colleague demos after demo mode exists. It records the current scripts and packaging assets, plus the risks that must be handled before calling this a non-technical release.

## Target User

- Non-technical colleague on Windows.
- Should be able to launch the app without editing source files.
- Should not need to manually edit `.env` for demo mode.
- Demo mode is controlled by one unified Settings switch; per-stage mock fields are not user controls.
- Production mode may ask for API keys through the frontend Settings page.

## Current Windows Assets

Root scripts:

- `simple_setup.bat`
- `start_react.bat`
- `run_backend.bat`
- `restart_backend.bat`
- `install_frontend.bat`
- `install_all.bat`
- `dependency_manager.bat`

Mirrored scripts:

- `scripts/setup.bat`
- `scripts/start_react.bat`
- `scripts/run_backend.bat`
- `scripts/restart_backend.bat`
- `scripts/install_frontend.bat`
- `scripts/dependency_manager.bat`

Frontend script:

- `frontend/run_frontend.bat`

Packaging assets:

- `packaging/windows/build_demo_release.ps1`
- `packaging/windows/installer.iss`
- `packaging/windows/installer_stub.py`
- `packaging/windows/launcher.py`
- `packaging/windows/requirements-demo.txt`

## Current Script Behavior

- `simple_setup.bat`
  - Creates or reuses `C:\ai_research_venv`.
  - Writes `.venv_config`.
  - Installs backend dependencies.
  - Installs frontend dependencies.
  - Asks CPU/GPU installation choice.
- `start_react.bat`
  - Loads `.venv_config`.
  - Starts backend and frontend in separate Windows command windows.
  - Prints frontend `http://localhost:3000` and backend `http://localhost:8000`.
  - Prints API docs as `http://localhost:8000/api/docs`.
- `run_backend.bat`
  - Activates configured venv.
  - Runs `uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload`.
- `restart_backend.bat`
  - Loads `.venv_config`.
  - Runs `taskkill /f /im python.exe`.
  - Restarts backend.
  - Risk: this kills all Python processes for the user, not only this app.
- `install_frontend.bat`
  - Runs `npm install`.
  - Runs `npm audit fix`.
  - Risk: `npm audit fix` may mutate dependency files or introduce unplanned changes.

## Recommended Demo Flow

After demo mode is implemented:

1. User extracts or clones the project.
2. User runs `simple_setup.bat`.
3. User runs `start_react.bat`.
4. Browser opens or user visits `http://localhost:3000`.
5. App reports Demo mode is active with the unified switch ON.
6. User clicks through Dashboard, Proposal, Search, Knowledge, Chemical, Upload, and Settings.
7. User can optionally enter real API keys in Settings for production mode.

## Required Changes Before Non-Technical Release

1. Demo mode:
   - The packaged path must seed/enable the Version A unified Demo setting without `.env` keys.
   - `DEMO_MOCK_*` stage overrides remain test-only and must not become user-facing controls.
   - Settings redirect must not block demo.
2. Script safety:
   - Replace `taskkill /f /im python.exe` with app-specific process management.
   - Avoid automatic `npm audit fix` in normal install scripts.
   - Ensure scripts fail with clear messages when Python, Node, or npm are missing.
3. Packaging:
   - Verify `packaging/windows/build_demo_release.ps1`.
   - Verify `packaging/windows/launcher.py` starts backend/frontend correctly.
   - Verify installer does not bundle secrets.
4. Documentation:
   - Add a short Windows user README after commands are verified on Windows.
   - Keep WSL/Linux developer commands separate from Windows user commands.

## Verification Checklist

Run on a clean Windows machine or Windows VM:

- `simple_setup.bat` completes.
- `start_react.bat` starts both services.
- Frontend opens at `http://localhost:3000`.
- Backend health works at `http://localhost:8000/health`.
- API docs work at `http://localhost:8000/api/docs`.
- Demo path works without real API keys.
- Settings accepts real API keys without committing them.
- Closing the app does not kill unrelated Python processes.
- Re-running setup is idempotent or gives a safe choice.

## Release Rule

Do not publish a Windows demo/release bundle until:

- Demo mode implementation is complete.
- Baseline verification has been updated after implementation.
- Windows scripts are tested on Windows, not only WSL.
- The separate browser visual/user pass is recorded; API/application tests alone do not close this gate.
- No `.env`, API key, or private data is included.

# Portable Desktop App — Implementation Plan

**Goal:** Transform Jarvis from "local web app" to "portable desktop app" usable without opening a browser.

**Architecture:**
- Electron BackendManager spawns/checks backend FastAPI
- Electron main.js updated: loading screen → backend ready → load frontend
- Frontend dist loaded by Electron (portable mode) or Vite dev (dev mode)
- Setup Wizard guides first-run configuration
- Pending Actions queue for security
- Health/diagnostics endpoints

## Phase 1: Electron BackendManager + main.js rewrite
- `frontend/electron/backendManager.js` — check/start/stop backend
- `frontend/electron/main.js` — integrate BackendManager, loading screen, error handling

## Phase 2: Local setup + start scripts
- `scripts/setup_local_linux.sh`, `setup_local_windows.ps1`, `setup_local_macos.sh`
- `scripts/start_jarvis_linux.sh`, `start_jarvis_windows.ps1`, `start_jarvis_macos.sh`
- `scripts/check_environment.py` — JSON + human output

## Phase 3: Setup Wizard — backend API
- `backend/api/setup.py` — endpoints
- `backend/core/setup_state.py` — state management
- Pydantic models

## Phase 4: Setup Wizard — frontend
- `frontend/src/pages/SetupWizard.tsx` — 8-step wizard
- API client updates

## Phase 5: Health/Diagnostics — backend
- `GET /health/full` endpoint
- `GET /diagnostics`, `POST /diagnostics/export`
- Public config endpoint

## Phase 6: Pending Actions Queue — backend
- `backend/core/pending_actions.py`
- API: `GET /pending-actions`, `POST /pending-actions/{id}/approve|reject`
- Integration with permissions

## Phase 7: UI Polish
- Dashboard: health cards, next steps, pending badge
- Topbar: pending actions count
- Loading/error/empty states across pages
- Settings page: config status, setup wizard link

## Phase 8: Pending Actions — frontend
- `frontend/src/pages/PendingActions.tsx`
- Topbar badge

## Phase 9: Documentation
- README.md update
- docs/portable-desktop.md
- docs/setup-wizard.md
- docs/troubleshooting.md
- docs/architecture.md
- docs/security.md
- docs/roadmap.md update

## Phase 10: Tests + build + git

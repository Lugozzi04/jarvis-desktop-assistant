# Portable Desktop Mode

Jarvis Desktop Assistant can run as a **self-contained desktop application** — no browser needed. This document explains the portable mode, how it differs from dev mode and web mode, the architecture that makes it work, and how to set it up.

---

## Run Modes at a Glance

| Mode | What it does | Starts backend? | Browser? | How to launch |
|---|---|---|---|---|
| **Portable (desktop)** | Electron loads `dist/`, auto-manages backend | Yes — BackendManager | No | `bash scripts/start_jarvis_*.sh` |
| **Dev (desktop)** | Electron points at Vite dev server, HMR, DevTools | No — manual | No | `cd frontend && npm run desktop:dev` |
| **Web** | Browser opens Vite dev server directly | No — manual | Yes | `npm run dev` (frontend) + `uvicorn ...` (backend) |

---

## What Portable Mode Is

Portable mode turns Jarvis into a **zero-browser desktop app**. Electron loads the production-built frontend (`frontend/dist/`) and automatically discovers, starts, and health-checks the Python backend. You run a single shell script and a native window appears — the rest is handled for you.

Key characteristics:

- **Electron loads the built frontend** — the Vite production bundle in `frontend/dist/index.html` is loaded directly from disk via `mainWindow.loadFile()`. No Vite dev server runs.
- **BackendManager manages the backend** — Electron spawns `uvicorn` as a child process, waits for the `/health` endpoint to respond, and kills the backend when the app closes. The user never touches a terminal for the backend.
- **Loading screen** — a dark, frameless window with a spinner shows startup progress ("Starting services…", "Checking backend…", "Backend ready — loading Jarvis…").
- **Error screen with retry and diagnostics** — if the backend fails to start within 30 seconds, an error window appears with the failure reason, recent logs, a **Retry** button, a **Run Environment Check** button, a **Copy Diagnostics** button, and troubleshooting tips.
- **Zero browser requirement** — the entire flow happens inside native Electron windows.

---

## Architecture

```
┌──────────────────────────────────────────────────────┐
│  Electron main.js                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐  │
│  │ Loading Win  │  │  Error Win   │  │ Main Win   │  │
│  │ (spinner +   │  │ (retry +     │  │ (dist/ or  │  │
│  │  status)     │  │  diagnostics)│  │  Vite URL) │  │
│  └──────────────┘  └──────────────┘  └───────────┘  │
│                        │                            │
│              ┌─────────▼──────────┐                  │
│              │   BackendManager   │                  │
│              │  • checkHealth()   │                  │
│              │  • ensureRunning() │                  │
│              │  • start()/stop()  │                  │
│              │  • waitForReady()  │                  │
│              └─────────┬──────────┘                  │
│                        │ spawn/health-check          │
└────────────────────────┼─────────────────────────────┘
                         │ HTTP :8400
              ┌──────────▼──────────┐
              │  FastAPI Backend    │
              │  (uvicorn)          │
              │  /health  /api/*    │
              └──────────┬──────────┘
                         │
              ┌──────────▼──────────┐
              │  frontend/dist/     │
              │  (Vite build)       │
              │  React SPA          │
              └─────────────────────┘
```

### Component Details

**Electron `main.js`** (`frontend/electron/main.js`)

Entry point. Determines whether to run in dev mode (`NODE_ENV=development` or `--dev` flag) or portable mode. In dev mode it loads `http://localhost:5173` (Vite dev server) and opens DevTools detached. In portable mode it loads `frontend/dist/index.html` from disk. Orchestrates the startup sequence: loading window → BackendManager → main window.

**BackendManager** (`frontend/electron/backendManager.js`)

A Node.js class that manages the Python backend lifecycle:

- **`checkHealth()`** — HTTP GET to `http://127.0.0.1:8400/health`, returns online/offline status
- **`ensureRunning()`** — checks health first; if already running, leaves it alone. If not, **starts** the backend and polls `/health` every 1 second until ready or 30-second timeout
- **`start()`** — resolves the Python command (virtual env Python preferred, falls back to system Python), spawns `uvicorn backend.main:app --host 127.0.0.1 --port 8400`
- **`stop()`** — sends SIGTERM (or `taskkill` on Windows) to the backend process, but only if BackendManager started it. Does not touch a backend started by the user
- **`getLogs()`** — returns the last N log lines (stdout, stderr, and manager messages) for the error screen

**FastAPI Backend** (`backend/main.py`)

The Python FastAPI application. Listens on `127.0.0.1:8400`. Exposes REST endpoints for chat, commands, skills, settings, diagnostics, setup wizard, pending actions, voice, habits, and documents. Provides a `/health` endpoint that BackendManager polls.

**Frontend dist** (`frontend/dist/`)

The production build of the React/Vite/TypeScript frontend. Produced by `npm run build` (or automatically during setup). Loaded by Electron's `mainWindow.loadFile()`.

**Preload** (`frontend/electron/preload.js`)

A secure bridge that exposes a minimal API (`window.jarvisDesktop`) to the renderer: `platform`, `isElectron`, and `version`. Context isolation is enforced — the renderer has no direct access to Node.js or Electron internals.

---

## How to Use

### One-Time Setup

Run the setup script for your operating system. It installs all dependencies (Python venv, pip packages, Node modules), creates `.env` from `.env.example`, and builds the frontend.

**Linux:**

```bash
bash scripts/setup_local_linux.sh
```

**macOS:**

```bash
bash scripts/setup_local_macos.sh
```

**Windows (PowerShell):**

```powershell
.\scripts\setup_local_windows.ps1
```

The setup script performs these steps:

1. Checks for Python 3 and Node.js
2. Creates a `.venv` virtual environment (if missing)
3. Installs Python dependencies from `requirements.txt`
4. Installs frontend `npm` dependencies (including `electron` as an optional dependency)
5. Copies `.env.example` → `.env` (if `.env` doesn't exist)
6. Builds the frontend into `frontend/dist/`

> **Requirement:** Python 3.10+ is required. Node.js 18+ is strongly recommended.

### Launching Jarvis

**Linux:**

```bash
bash scripts/start_jarvis_linux.sh
```

**macOS:**

```bash
bash scripts/start_jarvis_macos.sh
```

**Windows (PowerShell):**

```powershell
.\scripts\start_jarvis_windows.ps1
```

The launch script:

1. Verifies `.venv`, `frontend/node_modules`, and `frontend/dist` exist
2. Auto-builds `frontend/dist` if missing (first-time launch)
3. Installs `electron` if not already present
4. Launches Electron in portable mode: `npx electron .` from the `frontend/` directory

All three launch scripts are nearly identical — the architecture allows the same script pattern across platforms because Electron abstracts OS differences.

### What Happens When You Launch

1. **Gathering window** (500×380, frameless, centered) — shows "⚡ JARVIS — Desktop Assistant" with a loading spinner
2. **BackendManager** checks if a backend is already running on port 8400
3. If not running: spawns `uvicorn` using the project's virtual environment Python (`.venv/bin/python` on Linux/macOS, `.venv\Scripts\python.exe` on Windows)
4. Polls `/health` every 1 second for up to 30 seconds
5. **On success:** loading window closes, main window opens (1280×860) with the built frontend
6. **On failure:** loading window closes, error window appears with logs, retry/diagnostics buttons
7. **On quit:** BackendManager stops the backend (SIGTERM → wait 2s → SIGKILL on Linux/macOS, `taskkill /f /t` on Windows) — but only if it started it

The frontend talks to the backend at `http://127.0.0.1:8400` exactly as it would in web mode.

---

## Package Scripts (Frontend Directory)

All scripts are run from `frontend/` (`cd frontend` first):

| Script | Description |
|---|---|
| `npm run desktop:dev` | **Dev desktop mode.** Starts Vite dev server + Electron. Uses `concurrently` to run both. Electron loads `http://localhost:5173` with DevTools open. Requires backend started separately. |
| `npm run dev` | **Web mode.** Starts only the Vite dev server at `http://localhost:5173`. Open in your browser. Backend must be started separately. |
| `npm run build` | TypeScript compile + Vite production build → `frontend/dist/`. Required for portable mode. |
| `npm run desktop:build` | `build` + `electron-builder`. Produces a platform-specific distributable (`.AppImage`/`.deb` on Linux, `.dmg`/`.app` on macOS, `.exe` on Windows). |

There is **no dedicated `desktop:portable` npm script** — portable mode is the default behavior when running `electron .` without the `--dev` flag. The `start_jarvis_*.sh` scripts simply run `npx electron .` which defaults to portable mode.

### How Mode Detection Works

```js
const isDev = process.env.NODE_ENV === 'development' || process.argv.includes('--dev');
```

- **Dev mode** (`npm run desktop:dev`): Vite sets `NODE_ENV=development` → Electron loads `http://localhost:5173`, opens DevTools
- **Portable mode** (default): no `--dev` flag, no dev env → Electron loads `frontend/dist/index.html`

---

## Error Handling & Diagnostics

If the backend fails to start, the error window provides:

- **Error message** — the reason BackendManager reports (e.g., "Could not find Python or venv", "Backend did not start within 30s")
- **Logs pane** — last 20 lines from BackendManager (stdout, stderr, and manager messages)
- **🔄 Retry** — kills the error window and restarts the entire startup sequence
- **🔍 Run Environment Check** — runs `scripts/check_environment.py` in a new window. This standalone script checks Python version, Node version, venv presence, frontend build, port availability, `.env` file, disk space, and more. Output can be copied to clipboard.
- **📋 Copy Diagnostics** — copies the error + logs to clipboard for pasting into a bug report
- **✕ Quit** — closes the app

The environment check (`scripts/check_environment.py`) is a **zero-dependency** diagnostic tool — it uses only stdlib modules so it can run even if the venv is broken. It supports `--json` and `--quiet` flags for scripting.

---

## Limitations

### No Installer Yet

There is no platform-native installer (`.msi`, `.pkg`, `.deb`). The app runs from the cloned repository directory. The `start_jarvis_*.sh` scripts assume the project is at a known location and the virtual environment is at `.venv` relative to the project root. Packaging via `electron-builder` (`npm run desktop:build`) exists but hasn't been fully tested for distribution.

### Python 3.10+ Required

The backend requires Python 3.10 or newer (uses modern type annotations and FastAPI features). The `check_environment.py` script will flag older versions. BackendManager's `_findSystemPython()` method filters out non-Python-3 interpreters.

### Electron Is an Optional Dependency

`electron` is listed in `optionalDependencies` in `frontend/package.json`. Running `npm install --no-optional` skips it. The launch scripts check for `node_modules/electron` and install it if missing, but this adds a delay on first launch and requires npm connectivity.

### Backend Port Is Fixed

The backend always binds to `127.0.0.1:8400`. There's no port-fallback or configuration option — if port 8400 is occupied, startup fails.

### No System Tray or Minimize-to-Tray

The app behaves as a normal window with no system tray integration. Closing the window quits the app on Linux and Windows; on macOS the app stays in the dock per platform convention.

### No Auto-Start on Login (from the App)

The app doesn't register itself for auto-start. Users can set this up manually (see `docs/startup.md` for systemd, LaunchAgent, Task Scheduler, and autostart `.desktop` instructions).

### Frontend Must Be Pre-Built for Portable Mode

Portable mode requires `frontend/dist/` to exist. The setup script builds it, and the launch script builds it on first launch if missing. After code changes, you must re-run `npm run build` (or re-run the setup script) before launching in portable mode again.

---

## Comparison: Portable vs Dev vs Web

| Feature | Portable | Dev (desktop) | Web |
|---|---|---|---|
| **Start command** | `bash scripts/start_jarvis_linux.sh` | `npm run desktop:dev` | `npm run dev` + `uvicorn ...` |
| **Backend management** | Automatic (BackendManager) | Manual | Manual |
| **Loading screen** | Yes | No | No |
| **Error recovery UI** | Yes (retry/diagnostics) | No (connection error in window) | No (browser error) |
| **Hot Module Replacement** | No (production build) | Yes (Vite HMR) | Yes (Vite HMR) |
| **DevTools** | No | Yes (detached) | Browser DevTools |
| **Browser required** | No | No | Yes |
| **Frontend loaded from** | `frontend/dist/index.html` (file) | `http://localhost:5173` (URL) | `http://localhost:5173` (URL) |
| **Native window chrome** | Yes | Yes | No (browser tabs/address bar) |
| **Use case** | Daily use, demos, non-technical users | Active development with live reload | Quick testing, no Electron installed |

---

## Troubleshooting Quick Reference

| Problem | Solution |
|---|---|
| "Could not find Python or venv" | Run the setup script: `bash scripts/setup_local_linux.sh` |
| Backend starts but times out | Check port 8400 is free; check `backend/` for Python import errors; run `python scripts/check_environment.py` |
| Electron window is blank/white | Run `cd frontend && npm run build` to regenerate `dist/` |
| ".venv not found" | Run the setup script, or create it manually: `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt` |
| Port 8400 already in use | Kill the existing process: `lsof -ti:8400 | xargs kill` (Linux/macOS) or `netstat -ano | findstr :8400` (Windows) |
| npm install fails (Electron) | Run `npm install electron --save-optional` explicitly; check Node.js version is 18+ |

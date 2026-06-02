# Troubleshooting Guide

This guide covers common problems and their fixes for the Jarvis Desktop Assistant. If you're stuck, start with the **Environment Check** — it diagnoses most issues in one shot.

---

## Quick Start: Environment Check

Run the built-in environment check script. It works with zero dependencies (stdlib only):

```bash
cd ~/jarvis-desktop-assistant
python scripts/check_environment.py
```

**Flags:**

| Flag | Behavior |
|---|---|
| *(none)* | Human-readable output with ✅/❌ icons |
| `--json` | JSON output (machine-readable) |
| `--quiet` | Only show errors |

The script checks:
- Python version (needs 3.10+)
- `.venv` existence
- Node.js and npm availability
- Port 8400 status
- Backend health
- Python requirements installed
- Frontend dist built, `node_modules` present, Electron config present
- Ollama reachable and models available

If the check finds issues, run the setup script for your platform:

```bash
# Linux
bash scripts/setup_local_linux.sh

# macOS
bash scripts/setup_local_macos.sh

# Windows (PowerShell)
.\scripts\setup_local_windows.ps1
```

---

## Backend Not Starting

The backend is a FastAPI app running on `http://127.0.0.1:8400` via uvicorn:

```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8400 --reload
```

### Symptom: Port 8400 Busy

**Check:**
```bash
# Linux / macOS
lsof -i :8400

# Windows
netstat -ano | findstr :8400
```

**Fix:**
- Kill the existing process: `kill -9 <PID>` (Linux/macOS) or `taskkill /PID <PID> /F` (Windows)
- Or change the port in `.env`: `JARVIS_UI_PORT=8401`, then update `UI_CORS_ORIGINS` to match

### Symptom: Python Not Found

**Check:**
```bash
python3 --version   # Should be 3.10 or higher
```

**Fix:**
- **Linux:** `sudo apt install python3 python3-venv python3-pip` (Debian/Ubuntu) or your distro's equivalent
- **macOS:** `brew install python@3.12`
- **Windows:** Download from [python.org](https://python.org) — check "Add Python to PATH"

### Symptom: `.venv` Missing

The virtual environment at `.venv/` is required for isolating Python dependencies.

**Check:**
```bash
ls -d .venv
```

**Fix:**
```bash
# Create and activate the venv
uv venv                    # recommended (uses uv)
# OR
python3 -m venv .venv      # standard library

# Activate it
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

# Install dependencies
uv pip install -r requirements.txt
# OR
pip install -r requirements.txt
```

### Symptom: Python Requirements Missing

**Check:**
```bash
pip list | grep -i fastapi
```

**Fix:**
```bash
source .venv/bin/activate
uv pip install -r requirements.txt
```

Key dependencies: `fastapi`, `uvicorn[standard]`, `sqlalchemy`, `pydantic`, `pydantic-settings`, `python-dotenv`, `httpx`, `loguru`.

### Symptom: `.env` File Missing or Misconfigured

The backend reads configuration from `.env` in the project root.

**Check:**
```bash
ls -la .env
```

**Fix:**
```bash
cp .env.example .env
# Edit .env with your preferred settings
```

See `.env.example` for all available options. At minimum, ensure `JARVIS_ENV` and `JARVIS_DATA_DIR` are set.

---

## npm Dependencies Missing

All frontend dependencies live under `frontend/node_modules/`.

### Symptom: `node_modules` Missing or Corrupted

**Check:**
```bash
ls frontend/node_modules/.package-lock.json
```

**Fix:**
```bash
cd frontend
npm install
```

> **Note:** `electron`, `electron-builder`, `concurrently`, and `wait-on` are `optionalDependencies`. If they fail to install (e.g., on a system without Electron toolchain), the web-only `npm run dev` / `npm run build` workflows still work.

### Symptom: Node.js / npm Not Found

**Check:**
```bash
node --version   # Should be 18+
npm --version    # Should be 9+
```

**Fix:**
- **Linux:** Use [nvm](https://github.com/nvm-sh/nvm) or `sudo apt install nodejs npm`
- **macOS:** `brew install node`
- **Windows:** Download from [nodejs.org](https://nodejs.org)

---

## Ollama Offline / Model Missing

Jarvis uses Ollama by default for local LLM inference.

### Symptom: Ollama Not Reachable

**Check:**
```bash
curl http://localhost:11434/api/tags
```

If this fails, Ollama is either not installed or not running.

**Fix:**

**Install Ollama:**
```bash
# Linux / macOS
curl -fsSL https://ollama.com/install.sh | sh

# Windows: download from https://ollama.com/download
```

**Start Ollama:**
```bash
# Start the Ollama service (Linux/macOS)
ollama serve

# On Linux, you can also run it as a systemd service
systemctl --user start ollama
```

### Symptom: Model Not Pulled

**Check:**
```bash
ollama list
```

**Fix:**
Pull the recommended model (qwen2.5:7b) or use the convenience script:

```bash
# Pull directly
ollama pull qwen2.5:7b

# Or use the project script (also pulls phi3:mini for routing)
bash scripts/pull_recommended_model.sh
```

Available model sizes:
- `qwen2.5:7b` — recommended (best balance)
- `llama3.2:3b` — lighter
- `llama3.1:8b` — heavier
- `phi3:mini` — used for intent routing

**Alternative:** Use an OpenAI-compatible API instead of Ollama:

```env
LLM_DEFAULT_PROVIDER=openai_compatible
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-your-key-here
LLM_DEFAULT_MODEL=gpt-4o-mini
```

---

## Voice Not Configured

Voice features (speech-to-text, text-to-speech) are **disabled by default**.

### Symptom: Voice Not Working

**Check:**
```bash
curl http://127.0.0.1:8400/api/voice/status
```

Returns `{"voice_enabled": false, "stt_provider": "mock", ...}`.

### Enabling Real STT (Speech-to-Text)

```bash
source .venv/bin/activate
pip install faster-whisper
```

Then set in `.env`:
```env
VOICE_ENABLED=true
STT_PROVIDER=faster_whisper
STT_MODEL=base
```

Model options: `tiny` (75 MB), `base` (150 MB), `small` (500 MB), `medium` (1.5 GB). The model auto-downloads on first use.

### TTS (Text-to-Speech)

Currently only the `mock` provider is available (logs text instead of speaking). Edge TTS integration is planned for a future release.

### Push-to-Talk

The frontend uses the browser's MediaRecorder API. Requires:
- `localhost` or HTTPS (browser security restriction)
- Microphone permissions granted in the browser / Electron

---

## Electron Blank Screen

When running in Electron desktop mode, a blank white screen typically means the frontend couldn't load.

### Symptom: Electron Opens but Shows Blank/White

**Causes and fixes:**

1. **Backend not running** — The Electron app needs the backend on `localhost:8400`. Start it first or use the dev launcher:
   ```bash
   bash scripts/dev_start_linux.sh
   ```

2. **Vite dev server not running (dev mode)** — Electron in dev mode loads `http://localhost:5173`. Start Vite:
   ```bash
   cd frontend && npm run dev
   ```

3. **Frontend dist not built (portable mode)** — In portable mode, Electron loads `frontend/dist/index.html`. Build it:
   ```bash
   cd frontend && npm run build
   ```

4. **Node.js integration issues** — The Electron app sets `contextIsolation: true` and `nodeIntegration: false` for security. If you're developing and need Node APIs, use the preload bridge at `frontend/electron/preload.js`.

5. **DevTools** — In dev mode, DevTools open detached. Check the Console tab for JavaScript errors:
   ```
   Ctrl+Shift+I  (Windows/Linux)
   Cmd+Opt+I    (macOS)
   ```

6. **Check Electron logs** — In dev mode, Electron logs to the terminal where it was launched. In portable mode, check:
   - Linux: `~/.config/jarvis-desktop/logs/`
   - macOS: `~/Library/Logs/jarvis-desktop/`
   - Windows: `%APPDATA%\jarvis-desktop\logs\`

---

## Frontend Build Fails

### Symptom: `npm run build` Fails

The frontend build runs `tsc -b && vite build`.

**Common causes:**

1. **TypeScript errors:**
   ```bash
   cd frontend
   npx tsc --noEmit   # Check types without emitting
   ```
   Fix type errors in `.ts` / `.tsx` files.

2. **Missing dependencies after update:**
   ```bash
   cd frontend
   rm -rf node_modules package-lock.json
   npm install
   npm run build
   ```

3. **Node version too old** — Requires Node 18+. Check with `node --version`.

4. **Vite config issue** — Check `frontend/vite.config.ts` for misconfiguration.

5. **Out of memory** — Large projects may need more heap:
   ```bash
   NODE_OPTIONS="--max-old-space-size=4096" npm run build
   ```

### Symptom: `electron-builder` Fails

If `desktop:build` fails during the Electron packaging phase:
```bash
cd frontend
npm run build              # Build frontend first (should succeed)
npx electron-builder --dir # Test packaging without full build
```

---

## Diagnostics Export

The backend exposes a diagnostics endpoint for troubleshooting.

### Get Diagnostics Summary

```bash
curl http://127.0.0.1:8400/api/diagnostics
```

Returns: version, Python/Node versions, OS info, public config (no secrets), skills loaded, LLM status (no API keys), backend status.

### Export Full Diagnostics (JSON)

```bash
curl -X POST http://127.0.0.1:8400/api/diagnostics/export
```

This returns a JSON payload you can save and share for debugging. No API keys or secrets are included.

### Get Recent Logs via API

```bash
curl "http://127.0.0.1:8400/api/diagnostics/logs?lines=200"
```

Returns the last N lines from `data/jarvis.log`.

### Full Health Check

```bash
curl http://127.0.0.1:8400/api/health/full
```

Returns comprehensive status: backend, LLM, documents, voice, automations, workflows, skills, pending actions, desktop, environment, warnings, errors, and recommended next steps.

---

## How to Get Logs

### Backend Logs (Python / FastAPI)

The backend uses **Loguru** with two sinks:

**Console output** (stderr):
Colored, compact format. Visible when running `uvicorn` directly or via the dev launcher.

**File logs:**
```
logs/jarvis_YYYY-MM-DD.log    # All logs at DEBUG level
logs/audit_YYYY-MM-DD.log     # Action-level audit trail
```

Log files rotate at 10 MB, retained for 30 days (general) / 90 days (audit), with gzip compression.

### View Logs in Real Time

```bash
# Follow all backend logs
tail -f logs/jarvis_$(date +%Y-%m-%d).log

# Follow audit trail only
tail -f logs/audit_$(date +%Y-%m-%d).log
```

### Electron Logs

When running in dev mode, Electron logs to the terminal. The BackendManager also captures backend process output — if the Electron app fails to start, the error window shows the last 20 log lines.

### systemd Logs (Linux, if using systemd)

```bash
journalctl --user -u jarvis-backend -f
```

---

## Common Fixes Cheat Sheet

| Problem | Quick Fix |
|---|---|
| Everything broken | Run `python scripts/check_environment.py` first |
| Port 8400 busy | `lsof -i :8400` → kill the PID, or change port in `.env` |
| `.venv` missing | `python3 -m venv .venv && source .venv/bin/activate` |
| Python deps missing | `uv pip install -r requirements.txt` |
| npm deps missing | `cd frontend && npm install` |
| Ollama offline | `ollama serve` → `ollama pull qwen2.5:7b` |
| Frontend build fails | `cd frontend && rm -rf node_modules && npm install && npm run build` |
| Blank Electron window | Ensure backend is running + `npm run build` (portable) or `npm run dev` (dev) |
| `.env` missing | `cp .env.example .env` |
| Voice not working | `pip install faster-whisper` + set `VOICE_ENABLED=true` in `.env` |
| API returns 500 | Check `logs/jarvis_*.log` for stack traces |
| Can't find `uv` | `curl -LsSf https://astral.sh/uv/install.sh | sh` |

---

## Still Stuck?

1. Run `python scripts/check_environment.py --json > diag.json` and review the output
2. Check `curl http://127.0.0.1:8400/api/health/full` for subsystem status
3. Review `logs/jarvis_$(date +%Y-%m-%d).log` for stack traces
4. Ensure Python 3.10+ and Node.js 18+ are installed
5. Verify Ollama is running: `curl http://localhost:11434/api/tags`

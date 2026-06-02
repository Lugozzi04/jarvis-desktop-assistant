# Jarvis Desktop Assistant — Local PC Test Plan (v0.3.0-rc1)

This is a step-by-step checklist for testing Jarvis on a fresh local PC (Linux, macOS, or Windows). Run every step, verify the expected result, and collect diagnostics if anything fails.

> **Time estimate**: 20–30 minutes for a full pass.

---

## Prerequisites

- Python 3.10+ and Node.js 18+ installed
- Git installed
- Ollama installed (optional but strongly recommended)
- A webcam/microphone (for voice tests)
- Port 8400 and 5173 free

---

## Phase 1: Clone & Setup

### Step 1 — Clone the repository

```bash
git clone https://github.com/Lugozzi04/jarvis-desktop-assistant
cd jarvis-desktop-assistant
```

**Expected**: No errors. `ls` shows `backend/`, `frontend/`, `scripts/`, `docs/`, `README.md`.

**Common error**: "Permission denied (publickey)" — check your SSH key or use HTTPS clone.

---

### Step 2 — Run the setup script

```bash
# Linux
bash scripts/setup_local_linux.sh

# macOS
bash scripts/setup_local_macos.sh

# Windows (PowerShell)
.\scripts\setup_local_windows.ps1
```

**Expected**: Output shows ✅ for: Python 3 check, venv creation, pip install, npm install, .env copy, frontend build.

**Common errors**:

| Error | Fix |
|---|---|
| "python3 not found" | `sudo apt install python3 python3-venv python3-pip` (Ubuntu/Debian) or equivalent |
| "node not found" | `curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh \| bash && nvm install 18` |
| "npm install failed" | `cd frontend && rm -rf node_modules package-lock.json && npm install` |
| "uv not found" | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| "Electron failed to install" | This is optional — web mode still works. Run `npm install electron --save-optional` separately. |

**If setup fails**: Run `python scripts/check_environment.py` and paste the output to Hermes.

---

### Step 3 — Run the environment check

```bash
python scripts/check_environment.py
```

**Expected**: All checks show ✅. No ❌ items.

**If anything fails**: Note which check failed, run `python scripts/check_environment.py --json > diag.json` and send `diag.json` to Hermes.

---

## Phase 2: Start Backend + Frontend

### Step 4 — Start the backend

Terminal 1:
```bash
source .venv/bin/activate
uvicorn backend.main:app --host 127.0.0.1 --port 8400 --reload
```

**Expected**: Output shows:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8400
```

**Common errors**:

| Error | Fix |
|---|---|
| "Address already in use" | `lsof -ti:8400 \| xargs kill -9` (Linux/macOS) or `netstat -ano \| findstr :8400` then `taskkill /PID <PID> /F` (Windows) |
| "No module named 'backend'" | Run from the project root, not inside `backend/` |
| ".env file not found" | `cp .env.example .env` |
| "ModuleNotFoundError: fastapi" | `source .venv/bin/activate && uv pip install -r requirements.txt` |

---

### Step 5 — Start the frontend

Terminal 2:
```bash
cd frontend
npm run dev
```

**Expected**: Output shows:
```
VITE vX.X.X  ready in XXX ms
➜  Local:   http://localhost:5173/
```

---

### Step 6 — Verify health endpoints

```bash
# Basic health
curl http://127.0.0.1:8400/health

# Full health
curl http://127.0.0.1:8400/api/health/full
```

**Expected for `/health`**: `{"status":"ok","version":"0.3.0"}`

**Expected for `/api/health/full`**: JSON with `backend.online: true`, all subsystem statuses populated.

---

## Phase 3: Desktop App (Optional — skip if web-only test)

### Step 7 — Start the desktop app (portable mode)

```bash
# Linux
bash scripts/start_jarvis_linux.sh

# macOS
bash scripts/start_jarvis_macos.sh

# Windows
.\scripts\start_jarvis_windows.ps1
```

**Expected**: macOS/Windows/Linux — a loading screen appears ("⚡ JARVIS — Desktop Assistant"), then the main window opens (1280×860).

**Common errors**:

| Error | Fix |
|---|---|
| "Could not find Python or venv" | Re-run the setup script |
| "Backend did not start within 30s" | Check port 8400 is free; check logs at `~/jarvis-desktop-assistant/logs/` |
| Blank/white window | Run `cd frontend && npm run build` to regenerate `dist/` |
| Electron not installed | `cd frontend && npm install electron --save-optional` |

**If desktop fails**: Click "📋 Copy Diagnostics" in the error window and send the output to Hermes. Or fall back to web mode (Steps 4-5).

---

## Phase 4: Setup Wizard

### Step 8 — Complete the Setup Wizard

Open http://localhost:5173 (or the desktop window). The Setup Wizard should appear automatically on first launch.

Walk through all 8 steps:

1. **Welcome** — read the intro, click **Next**
2. **System Check** — verify all checks pass, click **Next**
3. **LLM Setup** — select Ollama (if available) or Mock, click **Next**
4. **Documents Setup** — select Simple embeddings, click **Next**
5. **Voice Setup** — select Mock provider, click **Next**
6. **Integrations** — skip all (or configure if available), click **Next**
7. **Security** — read the risk levels, click **I Understand**, click **Next**
8. **Finish** — review summary, click **Finish**

**Expected**: Wizard transitions to the Dashboard with health cards showing system status.

**If wizard doesn't appear**: Click Settings → **Open Setup Wizard**.

**If wizard gets stuck**: Check `data/setup_state.json`. Reset with:
```bash
curl -X POST http://127.0.0.1:8400/api/setup/reset
```

**Send to Hermes if the wizard fails**: Screenshot of the stuck step + output of `curl http://127.0.0.1:8400/api/setup/status`.

---

## Phase 5: Feature Tests

### Step 9 — Chat (Basic LLM Conversation)

Navigate to **Chat** in the sidebar.

1. Type: "Hello! What can you do?"
2. Press Enter.

**Expected**: A response appears in the chat bubble. If LLM is configured (Ollama/OpenAI), response is an intelligent reply. If Mock, response is a placeholder.

**If no response**: Check `curl http://127.0.0.1:8400/api/health/full` → look at `llm.available`. Run the LLM test in Settings → LLM → Test Connection.

**Send to Hermes**: The `/api/health/full` output + any error from the browser DevTools console (F12).

---

### Step 10 — Slash Commands

In the Chat input, try each slash command:

| Command | Expected Result |
|---|---|
| `/help` | Lists available slash commands |
| `/skills` | Lists all loaded skills |
| `/open obs` | Opens OBS Studio (or shows not-installed message) |
| `/search best Python libraries 2026` | Returns web search results |
| `/system` | Shows CPU, RAM, disk stats |
| `/timer 10s test` | Creates a 10-second countdown timer |
| `/docs list` | Lists indexed documents (empty initially) |

**Expected**: Each command returns a response. `/timer` should show a countdown notification after the specified duration.

**If slash commands don't work**: Check `curl http://127.0.0.1:8400/api/skills` → verify skills are loaded. Check `logs/jarvis_*.log` for parser errors.

**Send to Hermes**: The non-working command text + the API response or error message.

---

### Step 11 — Documents (RAG / Document Memory)

Navigate to **Documents** page.

1. Click **Index File** → select a `.txt` or `.md` file from your computer.
2. Verify the file appears in the document list.
3. In the search box, type a keyword from the file → click **Search**.
4. In the ask box, type a question about the file content → click **Ask**.

**Expected**: 
- File is indexed with chunk count shown
- Search returns relevant chunks with scores
- Ask returns an answer if LLM is available; otherwise returns search results

**If indexing fails**: Check `curl http://127.0.0.1:8400/api/documents/status`. Ensure the file is a supported type.

**Send to Hermes**: `curl http://127.0.0.1:8400/api/documents/status` output + the file path that failed.

---

### Step 12 — Voice (Push-to-Talk)

Navigate to **Voice** page.

1. Check the Voice status card — shows STT and TTS providers.
2. Click **Start Recording** (push-to-talk) → speak a short phrase → click **Stop**.
3. Verify transcription appears.

**Expected**: With Mock provider, transcription returns a placeholder. The page shows STT/TTS status.

**If recording fails**: Ensure microphone permissions are granted in the browser / Electron. Voice requires `localhost` or HTTPS (works on localhost).

**Send to Hermes**: `curl http://127.0.0.1:8400/api/voice/status` output.

---

### Step 13 — OBS Skill

In Chat, try:
```
/open obs
/obs status
```

Alternatively, navigate to **Skills** → find `obs` → click actions.

**Expected**: 
- `/open obs`: Opens OBS if installed, or shows not-found message
- `/obs status`: Shows connection status (mock: "OBS WebSocket not configured")

**If OBS doesn't respond**: Check that the `obs` skill is loaded: `curl http://127.0.0.1:8400/api/skills | grep obs`.

**Send to Hermes**: The chat response text.

---

### Step 14 — Discord Skill

In Chat, try:
```
/open discord
/discord open_web
/discord open_server
```

**Expected**: 
- Opens Discord desktop app or web version
- `open_server` opens a Discord invite URL

**Send to Hermes**: The chat response text.

---

### Step 15 — Spotify Skill

In Chat, try:
```
/open spotify
/spotify search Bohemian Rhapsody
/spotify search_artist Queen
```

**Expected**: 
- Opens Spotify desktop app
- Search opens Spotify Web with the query

**Send to Hermes**: The chat response text.

---

### Step 16 — GitHub Skill

In Chat, try:
```
/github open_repo jarvis
/github issues jarvis
/github status
```

**Expected**: 
- `open_repo`: Opens the Jarvis GitHub repo in browser
- `issues`: Opens the issues page
- `status`: Runs `git status` in the project directory

**Send to Hermes**: The chat response text.

---

### Step 17 — Workflows

Navigate to **Workflows** page.

1. Verify the page loads with workflow list (seed workflows should be present).
2. Create a test workflow:
   - Click **+ New Workflow**
   - Name: "Test Workflow"
   - Add steps (e.g., `/system` + `/timer 5s test`)
   - Save
3. Click **Run** on the workflow.

**Expected**: Workflow runs all steps sequentially. Results appear on the page.

**If workflows page is empty**: Check `data/workflows.json` exists. The workflows engine may return placeholder — this is expected for M7 (placeholder).

**Send to Hermes**: What you see on the Workflows page + any console errors.

---

### Step 18 — Automations

Navigate to **Automations** page.

1. Verify the page shows 5 seed automations (daily-study-reminder, startup-llm-status, dev-session-manual, obs-live-workflow, hydration-reminder).
2. Click **Enable** on `startup-llm-status`.
3. Click **Run** on `daily-study-reminder`.
4. Check the Engine Status card shows "Running".

**Expected**: 
- Seed automations are listed
- `startup-llm-status` status changes to "Enabled"
- Manual run of `daily-study-reminder` shows success in logs
- Engine status card shows scheduler running, tick interval 15s

**If automations fail**: Check `curl http://127.0.0.1:8400/api/automations/engine/status`.

**Send to Hermes**: The automations page state + `curl http://127.0.0.1:8400/api/automations`.

---

### Step 19 — Pending Actions (Security Gate)

Navigate to **Pending Actions** page.

1. Verify the page shows "0 pending actions" if nothing is queued.
2. Trigger a dangerous action from Chat:
   - `/github clone https://github.com/some/repo` (may need confirmation depending on risk level)
3. Check that a pending action card appears with the action details, risk level, reason.
4. Click **Approve** → verify the action executes.
5. Or click **Reject** → verify the action is discarded.

**Expected**: 
- Pending actions queue works as a security gate
- The topbar shows a badge with pending count
- Actions auto-expire after 60 minutes

**If pending actions don't appear**: Check `curl http://127.0.0.1:8400/api/pending-actions`.

**Send to Hermes**: Screenshot of the Pending Actions page + `curl http://127.0.0.1:8400/api/pending-actions`.

---

## Phase 6: Diagnostics Export

### Step 20 — Export diagnostics

```bash
# Full diagnostics JSON
curl -s http://127.0.0.1:8400/api/diagnostics | python3 -m json.tool > diag_export.json

# Logs (last 100 lines)
curl -s "http://127.0.0.1:8400/api/diagnostics/logs?lines=100" | python3 -m json.tool > diag_logs.json

# Environment check
python scripts/check_environment.py --json > env_check.json
```

**Expected**: All three files are created. `diag_export.json` shows version, skills, LLM status, no secrets.

---

## Summary: What to Send to Hermes

If any step fails, collect and send:

1. **The step number** and expected vs actual behavior
2. **`diag_export.json`** — `curl -s http://127.0.0.1:8400/api/diagnostics > diag.json`
3. **`env_check.json`** — `python scripts/check_environment.py --json > env.json`
4. **Relevant logs** — `tail -50 logs/jarvis_$(date +%Y-%m-%d).log`
5. **The exact error message** from the terminal or browser console (F12 → Console tab)
6. **`data/setup_state.json`** (if wizard-related)
7. **OS and versions** — `python3 --version`, `node --version`, `uname -a`

---

## Quick Reference: Key Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /health` | Backend alive check |
| `GET /api/health/full` | Full subsystem status |
| `GET /api/diagnostics` | Diagnostics summary |
| `POST /api/diagnostics/export` | Export diagnostics JSON |
| `GET /api/diagnostics/logs?lines=100` | Recent log lines |
| `GET /api/setup/status` | Setup wizard state |
| `GET /api/skills` | Loaded skills list |
| `GET /api/voice/status` | Voice STT/TTS status |
| `GET /api/documents/status` | Document index status |
| `GET /api/automations` | Automation list |
| `GET /api/automations/engine/status` | Engine status |
| `GET /api/pending-actions` | Pending queue |
| `GET /api/habits/suggestions` | Habit suggestions |

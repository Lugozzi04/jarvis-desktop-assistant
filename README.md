# ⚡ JARVIS Desktop Assistant

Modular AI desktop assistant — control your PC, chat intelligently, execute commands, manage workflows, automations, voice, memory, and extensible skills/plugins.

**Status:** M1-M15 complete — Release Candidate 0.3.0-rc1. Portable desktop app with 19+ skills, LLM Gateway, RAG document memory, voice pipeline, workflow & automation engines, habit learning, and Electron desktop wrapper.

---

## 📊 Architecture

```
frontend/                    # React + Vite + TypeScript
│   ├── electron/            # Electron main process, preload, BackendManager
│   └── src/
│       ├── api.ts           # API client
│       ├── Layout.tsx        # Sidebar + Topbar (pending badge)
│       └── pages/           # 13 pages: Dashboard, Chat, Skills, Workflows,
│                            #   Automations, Logs, Settings, LLM Settings,
│                            #   SetupWizard, Documents, Voice, Habits, PendingActions

backend/
├── main.py                  # FastAPI app, health, CORS
├── api/
│   ├── chat.py              # POST /api/chat  — natural language input
│   ├── command.py           # POST /api/command — slash commands
│   ├── skills.py            # GET /api/skills, GET /api/skills/{name}
│   ├── settings.py          # GET /api/settings, LLM test, logs, config public
│   ├── setup.py             # Setup wizard (6 endpoints)
│   ├── diagnostics.py       # GET /api/diagnostics, export, logs, /api/health/full
│   ├── pending_actions.py   # GET/POST approve/reject/list security-gated actions
│   ├── documents.py         # Index, search, ask, status for RAG pipeline
│   ├── voice.py             # Transcribe, speak, command, status (STT+TTS)
│   ├── habits.py            # Event tracking, suggestions, analyze
│   └── apps_config.py       # App alias configuration
├── core/
│   ├── config.py            # Pydantic settings from .env
│   ├── schemas.py           # Intent, ActionResult, RiskLevel, LogEntry
│   ├── router.py            # Slash parser + rule-based NL router (IT+EN)
│   ├── registry.py          # Skill auto-discovery and execution
│   ├── permissions.py       # Risk-based permission guard
│   ├── assistant.py         # Orchestrator pipeline
│   ├── logger.py            # Loguru structured logging
│   ├── app_config.py        # Desktop app monitoring configuration
│   ├── pending_actions.py   # Thread-safe pending actions queue
│   ├── setup_state.py       # Wizard state management
│   └── process_monitor.py   # Process detection and monitoring
├── llm/
│   ├── gateway.py           # LLM Gateway — provider routing, JSON mode, intent routing
│   └── providers/
│       ├── base.py          # BaseLLMProvider abstract class
│       ├── ollama.py        # Ollama local provider
│       ├── openai_compatible.py  # OpenAI/DeepSeek/LM Studio compatible
│       └── mock.py          # Mock provider for tests
├── voice/
│   ├── gateway.py           # Voice gateway — STT/TTS provider routing
│   └── providers/
│       ├── base.py          # BaseSTTProvider / BaseTTSProvider
│       ├── mock_stt.py      # Mock STT (placeholder transcriptions)
│       ├── mock_tts.py      # Mock TTS (logs text)
│       └── faster_whisper.py # Faster-Whisper STT (code ready)
├── memory/
│   ├── extractors.py        # Text + PDF extraction (30+ formats)
│   ├── chunker.py           # Smart text chunking (1500 char, 200 overlap)
│   ├── embeddings.py        # Embedding providers (Simple, Mock, Ollama nomic-embed-text)
│   ├── vector_store.py      # SQLite vector store with cosine similarity
│   ├── indexer.py           # Pipeline orchestrator: extract → chunk → embed → store
│   ├── rag_engine.py        # RAG: embed query → search → LLM answer with citations
│   └── models.py            # Pydantic schemas for document memory
├── automation/
│   └── engine.py            # Trigger engine + background scheduler (15s tick)
├── workflows/
│   └── engine.py            # Multi-step workflow runner
├── skills/                   # 19 skills — auto-discovered
│   ├── base.py              # BaseSkill — every skill inherits from this
│   ├── chat/                # ChatSkill — uses LLM Gateway
│   ├── apps/                # AppSkill — open/close/list desktop apps
│   ├── browser/             # BrowserSkill — open URLs
│   ├── web_search/          # WebSearchSkill — DuckDuckGo search
│   ├── system/              # SystemSkill — CPU, RAM, disk stats
│   ├── timers/              # TimerSkill — countdown timers + notifications
│   ├── documents/           # DocumentsSkill — RAG over local files
│   ├── obs/                 # OBSSkill — OBS Studio control
│   ├── discord/             # DiscordSkill — Discord app/web/server
│   ├── spotify/             # SpotifySkill — open, search
│   ├── github/              # GitHubSkill — repos, issues, git commands
│   ├── voice/               # VoiceSkill — speech I/O (placeholder M9)
│   ├── workflows/           # WorkflowSkill — multi-step execution
│   ├── automations/         # AutomationsSkill — rule-based triggers
│   ├── habit_learning/      # HabitLearningSkill — pattern detection
│   ├── files/               # FileSkill — file management
│   ├── streaming/           # StreamingSkill — streaming setup
│   ├── study/               # StudySkill — study mode
│   └── dev/                 # DevSkill — development mode
├── db/                      # SQLAlchemy models (SQLite)
└── tests/                   # 101+ tests across all subsystems

scripts/
├── setup_local_linux.sh     # One-command Linux setup
├── setup_local_macos.sh     # One-command macOS setup
├── setup_local_windows.ps1  # One-command Windows setup
├── start_jarvis_linux.sh    # Portable desktop launcher (Linux)
├── start_jarvis_macos.sh    # Portable desktop launcher (macOS)
├── start_jarvis_windows.ps1 # Portable desktop launcher (Windows)
├── dev_start_linux.sh       # Dev mode launcher (Linux)
├── check_environment.py     # Zero-dependency diagnostic tool
└── pull_recommended_model.sh # Pulls qwen2.5:7b + phi3:mini

data/                        # Runtime data (gitignored)
├── setup_state.json         # Wizard progress
├── pending_actions.json     # Security gate queue
├── memory.db                # SQLite vector store
├── workflows.json           # Workflow definitions
├── automations.json         # Automation definitions
├── habit_events.json        # Habit learning events
└── jarvis.log               # Application logs
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- [Ollama](https://ollama.com) (optional, for local LLM)
- Node.js 18+ (for frontend and desktop app)

### One-Command Setup (All Platforms)

```bash
# Linux
bash scripts/setup_local_linux.sh

# macOS
bash scripts/setup_local_macos.sh

# Windows (PowerShell)
.\scripts\setup_local_windows.ps1
```

This installs all dependencies (Python venv, pip packages, npm modules), creates `.env`, and builds the frontend — all in one command.

### Portable Desktop Mode (Recommended for Daily Use)

```bash
# Linux
bash scripts/start_jarvis_linux.sh

# macOS
bash scripts/start_jarvis_macos.sh

# Windows
.\scripts\start_jarvis_windows.ps1
```

This launches Jarvis as a native desktop app — no browser needed. Electron manages the backend automatically (start, health-check, stop). See [docs/portable-desktop.md](docs/portable-desktop.md) for details.

### Dev Mode (Web + Backend)

```bash
# Terminal 1: Backend
source .venv/bin/activate
uvicorn backend.main:app --host 127.0.0.1 --port 8400 --reload

# Terminal 2: Frontend (web)
cd frontend && npm run dev
```

Open http://localhost:5173 in your browser.

### Dev Desktop Mode (HMR + Electron)

```bash
cd frontend
npm run desktop:dev
```

Starts Vite + Electron. HMR works — edits update instantly. Backend must be started separately.

### Test the API

```bash
# Health check
curl http://localhost:8400/health

# Full health (all subsystems)
curl http://localhost:8400/api/health/full

# Chat
curl -X POST http://localhost:8400/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "/open discord"}'

# List skills
curl http://localhost:8400/api/skills

# Run diagnostics
curl http://localhost:8400/api/diagnostics
```

### Environment Check

```bash
python scripts/check_environment.py
```

Zero-dependency diagnostic that checks Python, Node, venv, port, backend, frontend, Ollama, and more. Use `--json` for machine-readable output.

---

## 🤖 LLM Configuration

### Ollama (Local — free)

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model
ollama pull llama3.1:8b

# Set in .env
LLM_DEFAULT_PROVIDER=ollama
LLM_DEFAULT_MODEL=llama3.1:8b
OLLAMA_BASE_URL=http://localhost:11434
```

### OpenAI

```env
LLM_DEFAULT_PROVIDER=openai_compatible
LLM_DEFAULT_MODEL=gpt-4o-mini
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-...
```

### DeepSeek

```env
LLM_DEFAULT_PROVIDER=openai_compatible
LLM_DEFAULT_MODEL=deepseek-chat
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_API_KEY=sk-...
```

### LM Studio / LocalAI

```env
LLM_DEFAULT_PROVIDER=openai_compatible
LLM_DEFAULT_MODEL=local-model
LLM_BASE_URL=http://localhost:1234/v1
LLM_API_KEY=not-needed
```

Configure and test from the **LLM Settings page** in the UI (`/settings/llm`).

---

## 🧩 Adding a New Skill

Skills are **auto-discovered** — just create a folder with two files:

### 1. `backend/skills/myskill/manifest.json`

```json
{
  "name": "myskill",
  "display_name": "My Skill",
  "description": "What this skill does",
  "version": "0.1.0",
  "actions": [
    {
      "name": "do_something",
      "description": "Do something useful",
      "parameters": { "param1": "string" },
      "risk": "safe"
    }
  ]
}
```

### 2. `backend/skills/myskill/skill.py`

```python
from backend.skills.base import BaseSkill
from backend.core.schemas import ActionResult

class MySkill(BaseSkill):
    def execute(self, action, parameters):
        if action == "do_something":
            return self._result(action, success=True, result="Done!")
        return self._result(action, success=False, error="Unknown action")
```

**That's it.** Restart and your skill is automatically loaded.

---

## 🛡️ Security

Every action has a risk level:

| Risk | Behavior | Examples |
|---|---|---|
| `safe` | Auto-approved | Open app, URL, timer, system stats, chat |
| `confirmation` | User must confirm via UI | Close app, move/rename file, run script |
| `dangerous` | Strong confirmation required | Delete files, shutdown, shell commands |

---

## 📊 Current Status

### Core System
- ✅ FastAPI backend with 50+ API endpoints across 10 route modules
- ✅ 19 skills: auto-discovery, registry, permission guard
- ✅ Intent Router: slash commands + rule-based NL (Italian + English)
- ✅ LLM Gateway: Ollama + OpenAI-compatible + Mock providers, JSON mode
- ✅ Skill system with 6 functional + 4 specialized + 4 mode + 5 infrastructure skills

### User Interface
- ✅ React/Vite/TypeScript frontend with 13 pages + dark theme
- ✅ Dashboard with real-time health cards and subsystem status
- ✅ 8-step Setup Wizard with guided first-run configuration
- ✅ Electron desktop wrapper: portable mode, BackendManager, loading/error screens

### Advanced Features
- ✅ Document Memory (RAG): text+PDF extraction, chunking, embeddings, vector search, Q&A
- ✅ Workflow Engine: multi-step execution, seed workflows
- ✅ Automation Engine: time/interval/startup triggers, 5 seed automations, background scheduler
- ✅ Voice System: mock STT/TTS, push-to-talk UI, faster-whisper code ready
- ✅ Habit Learning: rule-based pattern detection, suggestions, accept/dismiss
- ✅ Pending Actions Queue: security gate for dangerous actions, approve/reject/expire

### Specialized Skills
- ✅ OBS Skill: open, status, recording (mock WebSocket)
- ✅ Discord Skill: open app/web/server
- ✅ Spotify Skill: open app, web search
- ✅ GitHub Skill: repos, issues, git status/clone/commit/push

### Operations
- ✅ Diagnostics: `/api/diagnostics`, export, logs, `/api/health/full`
- ✅ Environment check: `scripts/check_environment.py` (zero-dependency)
- ✅ Cross-platform setup scripts (Linux, macOS, Windows)
- ✅ Portable desktop launcher scripts (Linux, macOS, Windows)
- ✅ Startup/autostart templates: systemd, LaunchAgent, Task Scheduler, .desktop
- ✅ Logging: Loguru structured logging + audit trail
- ✅ Security: risk-based permissions (safe/confirmation/dangerous)
- ✅ 101+ tests passing
- ✅ Frontend builds without errors
- ✅ 16 documentation files covering all subsystems

### Documentation
- See `docs/` for: architecture, roadmap, portable-desktop, desktop-app, setup-wizard, voice-system, specialized-skills, automation-engine, habit-learning, document-memory, llm-strategy, startup, security, troubleshooting, development, local-pc-test-plan
- See `RELEASE_CANDIDATE.md` for v0.3.0-rc1 details

---

## 🗺️ Roadmap

| Milestone | Status | Description |
|---|---|---|
| M1 | ✅ | Project foundation — structure, FastAPI, SQLite, config |
| M2 | ✅ | Modular skill system — BaseSkill, Registry, Permissions |
| M3 | ✅ | Basic skills (6 functional) |
| M4 | ✅ | Command pipeline hardening |
| M5 | ✅ | LLM Gateway — Ollama + OpenAI-compatible + Mock providers |
| M6 | ✅ | Frontend React/Vite/TypeScript — 8 initial pages |
| M7 | ✅ | Workflow engine — multi-step automation |
| M8 | ✅ | Automation engine — triggers, conditions, background scheduler |
| M9 | ✅ | Voice system (STT + TTS providers, push-to-talk UI, faster-whisper code ready) |
| M10 | ✅ | Habit learning — event tracking, pattern analysis, suggestions |
| M11 | ✅ | RAG / Document memory — extraction, chunking, embeddings, vector search, Q&A |
| M12 | ✅ | Specialized skills (Discord, OBS, Spotify, GitHub) |
| M13 | ✅ | Electron desktop wrapper |
| M14 | ✅ | Startup / launcher scripts + systemd/LaunchAgent/Task Scheduler templates |
| M15 | ✅ | Portable desktop app — BackendManager, loading screen, diagnostics, setup wizard, pending actions |
| Future | 📋 | Edge TTS, wake word, OBS WebSocket, Discord bot, Spotify OAuth, streaming transcription, visual workflow builder, Tauri wrapper, installer, plugin marketplace, mobile companion |

### Current Focus: Release Candidate Testing

- 🟡 Fixing RC1 bugs
- 🟡 Edge TTS real provider (top priority for v0.3.1)
- 🟡 Wake word detection
- See `RELEASE_CANDIDATE.md` for full status

---

## 📄 License

MIT — see LICENSE file.

**Built with ❤️ for personal productivity and AI experimentation.**

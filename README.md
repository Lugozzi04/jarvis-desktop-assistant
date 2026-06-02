# ⚡ JARVIS Desktop Assistant

Modular AI desktop assistant — control your PC, chat intelligently, execute commands, manage workflows, automations, voice, memory, and extensible skills/plugins.

**Status:** M1-M5 complete, M6 (Frontend) complete — usable MVP with React UI and LLM Gateway.

---

## 📊 Architecture

```
frontend/                    # React + Vite + TypeScript
│   └── src/
│       ├── api.ts           # API client
│       ├── Layout.tsx        # Sidebar + Topbar
│       └── pages/           # Dashboard, Chat, Skills, Logs, Settings, LLM Settings

backend/
├── main.py                  # FastAPI app, health, CORS
├── api/
│   ├── chat.py              # POST /api/chat  — natural language input
│   ├── command.py           # POST /api/command — slash commands
│   ├── skills.py            # GET /api/skills, GET /api/skills/{name}
│   └── settings.py          # GET /api/settings, POST /api/settings/llm/test, GET /api/logs
├── core/
│   ├── config.py            # Pydantic settings from .env
│   ├── schemas.py           # Intent, ActionResult, RiskLevel, LogEntry
│   ├── router.py            # Slash parser + rule-based NL router
│   ├── registry.py          # Skill auto-discovery and execution
│   ├── permissions.py       # Risk-based permission guard
│   ├── assistant.py         # Orchestrator pipeline
│   └── logger.py            # Loguru structured logging
├── llm/
│   ├── gateway.py           # LLM Gateway — provider routing, JSON mode, intent routing
│   └── providers/
│       ├── base.py          # BaseLLMProvider abstract class
│       ├── ollama.py        # Ollama local provider
│       ├── openai_compatible.py  # OpenAI/DeepSeek/LM Studio compatible
│       └── mock.py          # Mock provider for tests
├── skills/
│   ├── base.py              # BaseSkill — every skill inherits from this
│   ├── chat/                # ChatSkill — uses LLM Gateway when available
│   ├── apps/                # AppSkill — open/close/list desktop apps
│   ├── browser/             # BrowserSkill — open URLs
│   ├── web_search/          # WebSearchSkill — DuckDuckGo search
│   ├── system/              # SystemSkill — CPU, RAM, disk stats
│   ├── timers/              # TimerSkill — countdown timers + notifications
│   └── ...                  # 8 placeholder skills for future milestones
├── db/                      # SQLAlchemy models (SQLite)
└── voice/                   # Voice pipeline (M9)
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- [Ollama](https://ollama.com) (optional, for local LLM)
- Node.js 18+ (for frontend)

### Backend Setup

```bash
# Clone
git clone https://github.com/Lugozzi04/jarvis-desktop-assistant
cd jarvis-desktop-assistant

# Create virtual environment
uv venv
source .venv/bin/activate

# Install dependencies
uv pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env — set LLM provider, model, API keys

# Run
uvicorn backend.main:app --host 127.0.0.1 --port 8400 --reload
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 in your browser.

### Test the API

```bash
# Health check
curl http://localhost:8400/health

# Chat
curl -X POST http://localhost:8400/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "/open discord"}'

# List skills
curl http://localhost:8400/api/skills

# Test LLM connection
curl -X POST http://localhost:8400/api/settings/llm/test \
  -H "Content-Type: application/json" \
  -d '{"provider": "ollama", "base_url": "http://localhost:11434", "model": "llama3.1:8b"}'
```

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

- ✅ FastAPI backend with all API endpoints
- ✅ 6 functional skills: apps, browser, chat, web_search, system, timers
- ✅ Skill system: auto-discovery, registry, permission guard
- ✅ Intent Router: slash commands + rule-based NL (Italian + English)
- ✅ LLM Gateway: Ollama + OpenAI-compatible + Mock providers
- ✅ LLM JSON mode + intent routing
- ✅ ChatSkill connected to real LLM Gateway
- ✅ React/Vite/TypeScript frontend with 8 pages
- ✅ Logs, health, LLM test API endpoints
- ✅ 42 passing tests (29 original + 12 LLM)
- ✅ Frontend builds without errors

---

## 🗺️ Roadmap

| Milestone | Status | Description |
|---|---|---|
| M1 | ✅ | Project foundation — structure, FastAPI, SQLite, config |
| M2 | ✅ | Modular skill system — BaseSkill, Registry, Permissions |
| M3 | ✅ | Basic skills (6 functional) |
| M4 | ✅ | Command pipeline hardening |
| M5 | ✅ | LLM Gateway — Ollama + OpenAI-compatible + Mock providers |
| M6 | ✅ | Frontend React/Vite/TypeScript — Dashboard, Chat, Skills, Settings, LLM Settings |
| M7 | 📋 | Workflow engine — multi-step automation |
| M8 | 📋 | Automation engine — triggers, conditions |
| M9 | 📋 | Voice system (STT + TTS) |
| M10 | 📋 | Habit learning |
| M11 | 📋 | RAG / document memory |
| M12 | 📋 | Specialized skills (Discord, OBS, Spotify, GitHub) |

---

## 📄 License

MIT — see LICENSE file.

**Built with ❤️ for personal productivity and AI experimentation.**

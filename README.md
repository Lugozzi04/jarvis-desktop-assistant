# 🤖 Jarvis Desktop Assistant

**Modular AI desktop assistant** — control your PC, chat intelligently, execute commands, manage workflows, automations, voice, memory, and extensible skills/plugins.

> ⚠️ **Alpha Stage** — Active development. Core architecture and basic skills are functional. Full LLM integration, voice, workflows, automations, and UI coming in upcoming milestones.

---

## 🎯 Vision

Jarvis is NOT a simple chatbot. It's a **modular desktop assistant framework** where:

- The **core** is small and stable — routing, permissions, logging, skill registry
- Every **capability** is a skill/plugin — independently developed and tested
- **No hardcoding** of app-specific logic in the core
- **Local-first** with optional cloud LLM
- **Secure by design** — risk-based permission system

---

## 🏗️ Architecture

```
User Input (text / voice / slash command / trigger)
    ↓
Input Normalizer
    ↓
Slash Command Parser (deterministic, no LLM)
    ↓
Intent Router (rules + optional LLM classifier)
    ↓
Planner (single action or multi-step workflow)
    ↓
Permission Guard (safe / confirmation / dangerous)
    ↓
Skill Registry → Skill Executor
    ↓
Logger / Audit Log
    ↓
Response Formatter → UI / voice
```

### Core Principles

1. **Core NEVER contains app-specific logic** (Spotify, Discord, OBS, etc.)
2. **Everything is a skill** — each with manifest, actions, risk levels
3. **Slash commands use zero LLM** — deterministic regex parsing
4. **LLM only when it adds value** — local-first, cloud optional
5. **Risk-based permissions** — safe (auto), confirmation (ask), dangerous (strong confirm)
6. **Every action is logged** — full audit trail

---

## 📁 Project Structure

```
jarvis-desktop-assistant/
├── README.md
├── pyproject.toml
├── .env.example
├── .gitignore
│
├── backend/
│   ├── main.py              # FastAPI entry point
│   ├── api/                  # REST API routers
│   │   ├── chat.py           # POST /api/chat
│   │   ├── command.py        # POST /api/command
│   │   ├── skills.py         # GET/POST /api/skills
│   │   └── settings.py       # GET/POST /api/settings
│   │
│   ├── core/                 # Stable core (never modified for specific skills)
│   │   ├── assistant.py      # Orchestrator — ties everything together
│   │   ├── config.py         # Pydantic settings
│   │   ├── errors.py         # Structured error types
│   │   ├── logger.py         # Loguru-based logging + audit
│   │   ├── permissions.py    # Risk-based permission guard
│   │   ├── registry.py       # Skill discovery & loading
│   │   ├── router.py         # Intent router (slash + rules + LLM)
│   │   └── schemas.py        # Pydantic models for all actions
│   │
│   ├── llm/                  # LLM Gateway (provider-agnostic)
│   │   ├── gateway.py
│   │   └── providers/
│   │
│   ├── skills/               # Modular skills (each in its own folder)
│   │   ├── base.py           # BaseSkill abstract class
│   │   ├── apps/             # Application launcher
│   │   ├── browser/          # URL opener & web search
│   │   ├── chat/             # Conversational AI
│   │   ├── web_search/       # Programmatic web search
│   │   ├── files/            # File management
│   │   ├── system/           # System monitoring
│   │   ├── timers/           # Timers & reminders
│   │   ├── workflows/        # Multi-step workflows
│   │   ├── automations/      # Trigger-based automations
│   │   ├── voice/            # STT & TTS
│   │   ├── dev/              # Developer tools
│   │   ├── study/            # Study mode
│   │   ├── streaming/        # Streaming mode
│   │   └── habit_learning/   # Pattern detection
│   │
│   ├── voice/                # Voice pipeline (STT, TTS, wake word)
│   ├── memory/               # User profile, habits, RAG
│   ├── db/                   # SQLAlchemy models (SQLite MVP)
│   └── utils/
│
├── frontend/                 # React + Vite desktop UI
│   ├── package.json
│   └── src/
│
├── docs/                     # Comprehensive documentation
│   ├── architecture.md
│   ├── plugin-system.md
│   ├── llm-strategy.md
│   ├── voice-system.md
│   ├── security.md
│   └── roadmap.md
│
└── tests/                    # Unit & integration tests
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
# Edit .env — set LLM provider, voice settings, etc.

# Run
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8400 --reload
```

### Frontend Setup (coming in M6)

```bash
cd frontend
npm install
npm run dev
```

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

# System stats
curl -X POST http://localhost:8400/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "/system stats"}'
```

---

## 🔌 Adding a New Skill

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
            return ActionResult(
                success=True, skill="myskill", action="do_something",
                risk="safe", result="Done!"
            )
        return ActionResult(success=False, error="Unknown action")
```

**That's it.** Restart the backend and your skill is automatically loaded.

---

## 🛡️ Security

Every action has a risk level:

| Risk | Behavior | Examples |
|---|---|---|
| `safe` | Auto-approved | Open app, URL, timer, system stats, chat |
| `confirmation` | User must confirm via UI | Close app, move/rename file, run script |
| `dangerous` | Strong confirmation required | Delete files, shutdown, shell commands |

---

## 📊 Current Status (M1-M2 Complete)

- ✅ Project structure + GitHub repo
- ✅ FastAPI backend with health/chat/command/skills/settings endpoints
- ✅ SQLite database with full schema (settings, skills, apps, workflows, automations, logs, habits)
- ✅ Skill system: BaseSkill, manifest loader, SkillRegistry
- ✅ 6 functional skills: apps, browser, chat, web_search, system, timers
- ✅ 8 placeholder skills: files, workflows, automations, voice, dev, study, streaming, habit_learning
- ✅ Intent Router: deterministic slash commands + rule-based natural language
- ✅ Permission Guard: risk-based (safe/confirmation/dangerous)
- ✅ Structured logging + audit trail
- ✅ Pydantic schemas for all actions/intents/results
- ✅ LLM Gateway skeleton (Ollama provider ready)
- ✅ Comprehensive documentation

---

## 🗺️ Roadmap

| Milestone | Status | Description |
|---|---|---|
| M1 | ✅ | Project foundation — structure, FastAPI, SQLite, config |
| M2 | ✅ | Modular skill system — BaseSkill, Registry, Permissions |
| M3 | 🚧 | Complete remaining basic skills |
| M4 | 🚧 | Command pipeline hardening, edge cases |
| M5 | 📋 | LLM Gateway full implementation |
| M6 | 📋 | UI MVP — React frontend with dashboard, chat, skills |
| M7 | 📋 | Workflow engine |
| M8 | 📋 | Automation engine |
| M9 | 📋 | Voice system (STT + TTS) |
| M10 | 📋 | Habit learning |
| M11 | 📋 | RAG / document memory |
| M12 | 📋 | Specialized skills (Discord, OBS, Spotify, GitHub) |

---

## 📄 License

MIT — see LICENSE file.

---

**Built with ❤️ for personal productivity and AI experimentation.**

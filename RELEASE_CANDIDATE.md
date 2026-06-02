# Jarvis Desktop Assistant — Release Candidate v0.3.0-rc1

**Release Date**: June 2026  
**Branch**: `main`  
**Commit**: HEAD  
**Status**: 🟡 Release Candidate — testing in progress  

---

## What Works (19 Features)

### Core System
| # | Feature | Status | Details |
|---|---|---|---|
| 1 | **FastAPI Backend** | ✅ | `/health`, `/api/health/full`, CORS, graceful shutdown |
| 2 | **Skill Registry** | ✅ | Auto-discovery of 19 skills, manifest validation, risk-based permissions |
| 3 | **Intent Router** | ✅ | Slash commands + rule-based NL routing (IT+EN) |
| 4 | **LLM Gateway** | ✅ | Ollama, OpenAI-compatible, Mock providers; JSON mode; fallback |
| 5 | **Configuration** | ✅ | Pydantic settings from `.env`, public config endpoint |

### User Interface
| # | Feature | Status | Details |
|---|---|---|---|
| 6 | **React/Vite/TS Frontend** | ✅ | 13 pages, dark theme, sidebar+topbar layout |
| 7 | **Dashboard** | ✅ | Real-time health cards, subsystem status, quick actions |
| 8 | **Setup Wizard** | ✅ | 8-step guided first-run configuration |
| 9 | **Desktop App (Electron)** | ✅ | Portable mode, BackendManager, loading/error screens, env check |

### User Features
| # | Feature | Status | Details |
|---|---|---|---|
| 10 | **Chat** | ✅ | NL conversation via LLM Gateway, conversation history |
| 11 | **Slash Commands** | ✅ | `/help`, `/skills`, `/open`, `/search`, `/system`, `/timer`, `/docs`, `/obs`, `/discord`, `/spotify`, `/github` |
| 12 | **Document Memory (RAG)** | ✅ | Text+PDF extraction, chunking, embeddings (Simple/Ollama), SQLite vector store, semantic search, RAG Q&A |
| 13 | **Voice (Base)** | ✅ | Mock STT/TTS, push-to-talk UI, faster-whisper code ready |
| 14 | **OBS Skill** | ✅ | Open, status, recording (mock) |
| 15 | **Discord Skill** | ✅ | Open, open_web, open_server |
| 16 | **Spotify Skill** | ✅ | Open, search, search_artist |
| 17 | **GitHub Skill** | ✅ | Open repo, issues, git status, clone/commit/push (confirmation) |
| 18 | **Workflows** | ✅ | Multi-step workflow engine, seed workflows, UI |
| 19 | **Automations** | ✅ | Trigger engine (time/interval/startup), 5 seed automations, background scheduler, UI |

### Security & Operations
| # | Feature | Status | Details |
|---|---|---|---|
| 20 | **Pending Actions Queue** | ✅ | Security gate for dangerous actions, approve/reject/expire, UI |
| 21 | **Habit Learning** | ✅ (lightweight) | Rule-based pattern detection, suggestions, accept/dismiss |
| 22 | **Diagnostics** | ✅ | `/api/diagnostics`, `/api/diagnostics/export`, `/api/diagnostics/logs`, env check script |
| 23 | **Logging** | ✅ | Loguru structured logging, audit trail, API log access |
| 24 | **Environment Check** | ✅ | `scripts/check_environment.py` — zero-dep diagnostic tool |

---

## What is Mock / Requires VPS-Only Setup

These features work but use mock/stub implementations. Real providers require setup that is impractical or infeasible on the target VPS:

| Feature | Mock behavior | Real setup required |
|---|---|---|
| **LLM (Speech)** | Mock provider returns deterministic placeholder text | Install Ollama + pull `qwen2.5:7b` (or any OpenAI-compatible key) |
| **Voice STT** | Mock returns placeholder transcription | `pip install faster-whisper` + set `VOICE_ENABLED=true` |
| **Voice TTS** | Mock logs text instead of speaking | `pip install edge-tts` (planned, not yet implemented) |
| **Document Embeddings** | Simple hash-based (works fine for <100 docs) | `ollama pull nomic-embed-text` for 768-dim real embeddings |
| **OBS WebSocket** | Mock status only (open/close works via desktop app) | Configure OBS WebSocket URL + password |
| **Discord Bot** | Opens desktop/web app only | Create Discord bot token for real message/status control |
| **Spotify API** | Opens desktop/web search only | Spotify OAuth for playback control |
| **GitHub API** | Basic repo open, git CLI for status | GitHub personal access token for issues/PR management |

> **Key insight**: On a local PC (not VPS), LLM via Ollama and Voice STT via faster-whisper work immediately after install. Only TTS and deep API integrations are genuinely pending.

---

## What Requires Local Setup

Steps needed after cloning on a fresh local PC:

| Requirement | Command | Time |
|---|---|---|
| Python 3.10+ | `sudo apt install python3 python3-venv` | 1 min |
| Node.js 18+ | `nvm install 18` or `brew install node` | 2 min |
| Ollama (optional) | `curl -fsSL https://ollama.com/install.sh \| sh` | 3 min |
| LLM Model (optional) | `ollama pull qwen2.5:7b` | 10-20 min (download) |
| Project setup | `bash scripts/setup_local_linux.sh` | 5 min |
| Faster-Whisper (optional) | `pip install faster-whisper` | 2 min |

---

## What is NOT Implemented Yet

| Feature | Priority | Planned |
|---|---|---|
| Real TTS (Edge TTS) | High | M9+ |
| Wake word detection ("Jarvis") | Medium | M9+ |
| OBS WebSocket full integration | Medium | M12+ |
| Discord bot token integration | Medium | M12+ |
| Spotify OAuth playback control | Medium | M12+ |
| GitHub PR management | Medium | M12+ |
| Streaming transcription | Low | M9+ |
| Voice activity detection | Low | M9+ |
| Visual workflow builder (drag-and-drop) | Low | M7+ |
| Real `app_opened` trigger (OS monitoring) | Low | M8+ |
| Mode system (study/streaming/dev) | Low | Future |
| Tauri desktop wrapper | Low | Future |
| ML-based habit patterns | Low | M10+ |
| OCR for scanned PDFs | Low | Future |
| ChromaDB / LanceDB vector store | Low | M11+ |
| Plugin marketplace | Low | Future |
| Mobile companion app | Low | Future |
| Multi-language UI | Low | Future |
| Full installer (.msi/.pkg/.deb) | Low | M15+ |

---

## Test & Build Status

### Backend Tests
```bash
cd jarvis-desktop-assistant
source .venv/bin/activate
python -m pytest tests/ -v
```
**Result**: ✅ 101+ tests passing (original 29 + 12 LLM + 38 automations + 22+ documents/other)

### Frontend Build
```bash
cd frontend
npm run build
```
**Result**: ✅ Builds without errors (TypeScript compilation + Vite bundle)

### Environment Check
```bash
python scripts/check_environment.py
```
**Result**: ✅ All checks pass on target system

### Desktop App (Electron)
```bash
bash scripts/start_jarvis_linux.sh
```
**Result**: ✅ BackendManager starts backend, loading screen shows, main window opens

---

## Known Limitations

| # | Limitation | Impact | Workaround |
|---|---|---|---|
| 1 | **No real TTS** | Jarvis doesn't speak aloud | Use mock TTS (text-only responses); Edge TTS planned |
| 2 | **No wake word** | Must click to talk | Push-to-talk button works |
| 3 | **SQLite vector store** | Slower search with >10K chunks | Use Ollama embeddings for better quality; external DB planned |
| 4 | **Frontend must be pre-built** for portable mode | Code changes need `npm run build` | Dev mode (`npm run desktop:dev`) has HMR |
| 5 | **Backend port 8400 is fixed** | Can't run 2 instances | Kill existing process or change port in `.env` |
| 6 | **No native installer** | Must run from cloned repo | Launch scripts handle deps automatically |
| 7 | **`app_opened` trigger is placeholder** | Automations can't react to real app launches | Use time/interval triggers |
| 8 | **Manual habit analysis** | Must click "Analyze" to get suggestions | Automatic analysis planned |
| 9 | **No system tray** | App lives as normal window | Minimize to taskbar/dock |
| 10 | **Confirmation actions can't be auto-triggered** | Automation engine skips them | Manually trigger confirmation actions |

---

## Next Priorities (v0.3.1 → v0.4.0)

| Priority | Item | Effort |
|---|---|---|
| 🔴 P0 | Edge TTS real provider | Small |
| 🔴 P0 | Fix any RC1 bugs found during testing | Variable |
| 🟡 P1 | Wake word detection (porcupine/openWakeWord) | Medium |
| 🟡 P1 | Automatic periodic habit analysis | Small |
| 🟡 P1 | OBS WebSocket real integration | Medium |
| 🟢 P2 | Streaming transcription | Medium |
| 🟢 P2 | Visual workflow builder | Large |
| 🟢 P2 | Full installer packaging | Medium |

---

## Changelog (v0.3.0-rc1)

### New Since v0.2.x (M1-M6 MVP)
- **M7**: Workflow engine with multi-step execution
- **M8**: Automation engine with time/interval/startup triggers, 5 seed automations
- **M9**: Voice system — STT/TTS providers, push-to-talk UI, faster-whisper code
- **M10**: Habit learning — event tracking, pattern analysis, suggestions
- **M11**: RAG/Document memory — text extraction, chunking, embeddings, vector store, search, Q&A
- **M12**: Specialized skills — OBS, Discord, Spotify, GitHub
- **M13**: Electron desktop wrapper — native window, dev + prod mode
- **M14**: Startup/launcher — dev scripts, systemd, LaunchAgent, Task Scheduler
- **M15**: Portable desktop app — BackendManager, loading screen, error recovery, diagnostics, setup wizard, pending actions, environment check

### Architecture Additions
- `backend/voice/` — STT/TTS provider system
- `backend/memory/` — RAG pipeline (extract, chunk, embed, store, search, ask)
- `backend/automation/` — trigger engine, scheduler, conditions
- `backend/workflows/` — workflow runner
- `frontend/electron/` — main.js, preload.js, BackendManager
- `scripts/` — setup, start, environment check (cross-platform)
- `data/` — `setup_state.json`, `pending_actions.json`, `memory.db`, `workflows.json`, `automations.json`, `habit_events.json`
- `docs/` — 16 documentation files covering all subsystems

### New API Endpoints (50+ total)
- Setup wizard (6 endpoints)
- Diagnostics (3 endpoints)
- Pending actions (6 endpoints)
- Documents (8 endpoints)
- Voice (4 endpoints)
- Habits (7 endpoints)
- Automations (10 endpoints)
- Health full
- Config public

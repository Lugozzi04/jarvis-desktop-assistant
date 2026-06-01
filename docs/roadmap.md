# Development Roadmap

## M1 — Project Foundation ✅
- [x] GitHub repo + project structure
- [x] FastAPI backend with health/chat endpoints
- [x] SQLite database with full schema
- [x] Pydantic settings from .env
- [x] Loguru logging + audit trail
- [x] Core Pydantic schemas (Intent, Action, Workflow, etc.)
- [x] Custom exception hierarchy

## M2 — Modular Skill System ✅
- [x] BaseSkill abstract class
- [x] Manifest loading and validation
- [x] SkillRegistry with auto-discovery
- [x] PermissionGuard (safe/confirmation/dangerous)
- [x] Intent Router (slash commands + rules)
- [x] Assistant Orchestrator pipeline

## M3 — Basic Skills (In Progress)
- [x] ChatSkill (questions, explanations)
- [x] AppSkill (open/close/list apps)
- [x] BrowserSkill (open URLs, web search in browser)
- [x] WebSearchSkill (DuckDuckGo search + summarization)
- [x] TimerSkill (countdown timers, reminders, desktop notifications)
- [x] SystemSkill (CPU, RAM, disk stats, screenshots)
- [ ] FileSkill (search, open, move, rename, delete)
- [ ] Complete remaining placeholder skills

## M4 — Command Pipeline Hardening
- [ ] Edge case handling for slash commands
- [ ] Parameter validation
- [ ] Error recovery and retry
- [ ] Confirmation flow end-to-end
- [ ] Unit tests for router and registry
- [ ] Integration tests for full pipeline

## M5 — LLM Gateway
- [ ] Ollama provider full implementation
- [ ] OpenAI provider
- [ ] Anthropic provider
- [ ] DeepSeek provider
- [ ] Custom OpenAI-compatible provider
- [ ] Task-based model routing
- [ ] JSON-mode output for intent parsing
- [ ] Graceful fallback when LLM unavailable
- [ ] Token counting and cost tracking

## M6 — UI MVP
- [ ] React + Vite frontend setup
- [ ] Dashboard page (status, active timers, quick actions)
- [ ] Chat page (text input, push-to-talk button, slash commands)
- [ ] Skills page (list, enable/disable, configure)
- [ ] Logs page (filterable audit trail)
- [ ] Settings page (LLM, voice, security, appearance)
- [ ] API client layer
- [ ] Dark theme

## M7 — Workflows
- [ ] Workflow schema (JSON or DB)
- [ ] Workflow runner (sequential + conditional steps)
- [ ] Workflow editor UI
- [ ] Built-in workflows: streaming, study, dev
- [ ] Workflow templates
- [ ] Workflow history and logs

## M8 — Automations
- [ ] Trigger engine (time, app events, system events)
- [ ] Condition evaluator
- [ ] Automation runner
- [ ] UI for creating/editing automations
- [ ] Enable/disable per automation
- [ ] Automation log

## M9 — Voice System
- [ ] Push-to-talk UI
- [ ] faster-whisper integration
- [ ] Edge TTS integration
- [ ] Voice settings page
- [ ] Microphone test
- [ ] Transcription preview + edit

## M10 — Habit Learning
- [ ] Event tracking (app opens, workflows, timers)
- [ ] Pattern detection (frequent combinations, time patterns)
- [ ] Suggestion generation
- [ ] Approve/reject UI
- [ ] Privacy controls
- [ ] Opt-in/opt-out

## M11 — RAG / Document Memory
- [ ] Document indexing (text extraction, chunking)
- [ ] Embeddings generation (local model)
- [ ] Vector store (ChromaDB or LanceDB)
- [ ] Semantic search
- [ ] Document Q&A

## M12 — Specialized Skills
- [ ] DiscordSkill (status, messages, channels)
- [ ] OBSSkill (scene switching, recording)
- [ ] SpotifySkill (play, pause, search)
- [ ] GitHubSkill (status, PRs, issues)
- [ ] DevSkill (project management, test running)

## Future
- [ ] Tauri desktop wrapper
- [ ] Wake word detection
- [ ] Multi-language support
- [ ] Plugin marketplace
- [ ] Mobile companion app

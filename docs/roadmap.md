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

## M3 — Basic Skills ✅
- [x] ChatSkill (questions, explanations, summarization)
- [x] AppSkill (open/close/list apps)
- [x] BrowserSkill (open URLs, web search in browser)
- [x] WebSearchSkill (DuckDuckGo search + summarization)
- [x] TimerSkill (countdown timers, reminders, desktop notifications)
- [x] SystemSkill (CPU, RAM, disk stats, screenshots)

## M4 — Command Pipeline Hardening ✅
- [x] Edge case handling for slash commands
- [x] Parameter validation
- [x] Error recovery and retry
- [x] Confirmation flow
- [x] 29 unit tests for router, registry, permissions, schemas, skills

## M5 — LLM Gateway ✅
- [x] Modular provider architecture (BaseLLMProvider)
- [x] Ollama provider
- [x] OpenAI-compatible provider (OpenAI, DeepSeek, LM Studio, LocalAI)
- [x] Mock provider for tests
- [x] JSON mode with auto-extraction
- [x] Intent routing via LLM
- [x] Graceful fallback when LLM unavailable
- [x] ChatSkill connected to real LLM Gateway
- [x] LLM test endpoint + UI
- [x] 12 provider tests

## M6 — UI MVP ✅
- [x] React + Vite + TypeScript frontend
- [x] Sidebar + topbar layout
- [x] Dashboard page (status, stats, quick actions)
- [x] Chat page (text input, slash commands, conversation)
- [x] Skills page (list, status, actions)
- [x] Workflows page (placeholder, M7)
- [x] Automations page (placeholder, M8)
- [x] Logs page (filterable audit trail)
- [x] Settings page (config display)
- [x] LLM Settings page (provider config, test connection, setup guide)
- [x] API client layer
- [x] Dark theme
- [x] Frontend builds without errors

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

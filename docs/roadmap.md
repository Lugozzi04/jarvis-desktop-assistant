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

## M8 — Automations ✅
- [x] Trigger engine (time, interval, startup, manual; app_opened placeholder)
- [x] Condition evaluator (always, time_after, time_before, day_of_week)
- [x] Automation runner with PermissionGuard integration
- [x] Background scheduler (15s tick, threading)
- [x] UI for listing, detail, run, enable/disable, delete
- [x] Create form with presets + JSON editor
- [x] Enable/disable per automation
- [x] Engine status card
- [x] 5 seed automations
- [x] 38 new tests (101 total)

## M9 — Voice System ✅ (base)
- [x] STT provider architecture (mock + faster-whisper ready)
- [x] TTS provider architecture (mock ready, edge-tts planned)
- [x] Push-to-talk UI (MediaRecorder + file upload)
- [x] Voice API endpoints (transcribe, speak, command, status)
- [x] Voice frontend page with setup guide
- [x] Faster-whisper provider (code ready, no model download on VPS)
- [x] docs/voice-system.md
- [ ] Edge TTS real provider
- [ ] Wake word detection
- [ ] Streaming transcription

## M10 — Habit Learning ✅ (lightweight)
- [x] HabitEvent tracking (skill_action, workflow_run, automation_run, app_opened, timer_created)
- [x] PatternAnalyzer (repeated actions, co-occurring, repeated workflows, app→workflow)
- [x] Suggestion generation (automation + workflow types)
- [x] Accept/dismiss suggestion with auto-creation
- [x] Frontend Habits page (pending/accepted/dismissed, analyze button)
- [x] Privacy controls (local only, clear events, no chat content)
- [x] API endpoints (events, suggestions, analyze, accept, dismiss, clear)
- [x] docs/habit-learning.md
- [ ] Automatic periodic analysis
- [ ] ML-based patterns

## M11 — RAG / Document Memory
- [ ] Document indexing (text extraction, chunking)
- [ ] Embeddings generation (local model)
- [ ] Vector store (ChromaDB or LanceDB)
- [ ] Semantic search
- [ ] Document Q&A

## M12 — Specialized Skills ✅ (base: M12A)
- [x] OBS Skill (open, status, recording placeholder)
- [x] Discord Skill (open, open_web, open_server)
- [x] Spotify Skill (open, search, search_artist)
- [x] GitHub Skill (open_repo, issues, git_status, clone/commit/push confirmation)
- [x] Slash commands for all 4 skills
- [x] NL rule-based routing for all 4 skills
- [x] docs/specialized-skills.md
- [ ] OBS WebSocket real integration
- [ ] Discord bot/oauth
- [ ] Spotify OAuth

## Future
- [ ] Tauri desktop wrapper
- [ ] Wake word detection
- [ ] Multi-language support
- [ ] Plugin marketplace
- [ ] Mobile companion app

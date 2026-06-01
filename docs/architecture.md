# JARVIS Architecture

## Overview

Jarvis Desktop Assistant follows a **modular monolith** architecture with a plugin-based skill system. The core is deliberately kept small and stable — it never contains application-specific logic.

## Layered Architecture

```
┌─────────────────────────────────────────┐
│              User Interface              │
│    (React + Vite → Tauri/Electron)      │
├─────────────────────────────────────────┤
│              REST API Layer              │
│     (FastAPI — chat, command, skills,   │
│      workflows, automations, settings)  │
├─────────────────────────────────────────┤
│            Assistant Orchestrator        │
│   (Pipeline: route → plan → permission  │
│    → execute → log → respond)           │
├─────────────────────────────────────────┤
│     Core Services (stateless)           │
│  ┌──────────┬──────────┬──────────┐     │
│  │  Router  │ Registry │ Permissions│    │
│  ├──────────┼──────────┼──────────┤     │
│  │  Logger  │  Config  │  Schemas │     │
│  └──────────┴──────────┴──────────┘     │
├─────────────────────────────────────────┤
│           Skill Layer (plugins)          │
│  apps │ browser │ chat │ web_search │    │
│  files │ system │ timers │ workflows │   │
│  voice │ dev │ study │ streaming │ ...   │
├─────────────────────────────────────────┤
│         Infrastructure Layer             │
│  ┌────────┬────────┬────────┬──────┐    │
│  │ SQLite │  LLM   │ Voice  │ RAG  │    │
│  │  (DB)  │Gateway │ Pipeline│Store │    │
│  └────────┴────────┴────────┴──────┘    │
└─────────────────────────────────────────┘
```

## Input Pipeline

1. **Input Normalizer** — accepts text, voice, slash commands, UI buttons, automation triggers
2. **Slash Command Parser** — deterministic regex, zero LLM cost
3. **Intent Router** — rules first, LLM classifier second (for complex intents)
4. **Planner** — resolves single actions or multi-step workflows
5. **Permission Guard** — checks risk level, requests confirmation if needed
6. **Skill Executor** — dispatches to the appropriate skill
7. **Logger** — writes structured audit log
8. **Response Formatter** — prepares output for UI or voice

## Design Decisions

### Why not microservices?
Jarvis is a desktop assistant running on a single machine. Microservices would add unnecessary complexity. The modular monolith with plugin-based skills gives the same isolation benefits without distributed system overhead.

### Why SQLite?
Zero-config, embedded, perfect for desktop apps. PostgreSQL is supported as an upgrade path for multi-user scenarios.

### Why FastAPI?
Async support for LLM calls, automatic OpenAPI docs, Pydantic validation, excellent performance.

### Why not LangChain?
Too heavy for our use case. Jarvis needs a thin LLM Gateway, not a full agent framework. Direct provider integration is simpler and more controllable.

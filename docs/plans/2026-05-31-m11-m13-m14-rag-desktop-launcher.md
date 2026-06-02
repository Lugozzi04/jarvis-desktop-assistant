# M11 + M13 + M14 Implementation Plan

> **Goal:** Add Document Memory/RAG, Desktop Wrapper, and Startup Launcher to Jarvis

**Architecture:** 
- M11: modular `backend/memory/` with extractors, chunker, embeddings (mock/simple/ollama), SQLite vector store, RAG engine. New `documents` skill + API + frontend page.
- M13: Electron desktop wrapper (simpler than Tauri for MVP, no Rust deps on VPS).
- M14: dev launcher scripts per OS + startup templates (systemd, .desktop, Task Scheduler, LaunchAgent).

**Tech Stack:** Python 3.11, FastAPI, SQLite, React/Vite/TS, Electron

---

## Task 1: Create backend/memory/ core module (models, extractors, chunker)
- `backend/memory/__init__.py`, `models.py`, `extractors.py`, `chunker.py`, `embeddings.py`, `vector_store.py`

## Task 2: Create DocumentIndexer + RAG Engine
- `backend/memory/indexer.py`, `backend/memory/rag_engine.py`

## Task 3: Documents skill + API router + main.py
- `backend/skills/documents/`, `backend/api/documents.py`, register in main.py

## Task 4: Router slash commands + NL patterns
- Update `backend/core/router.py`

## Task 5: Documents frontend page
- `frontend/src/pages/Documents.tsx`, api.ts, App.tsx, Layout.tsx

## Task 6: Habit events + tests
- Update habit engine, write tests

## Task 7: Electron desktop wrapper
- `frontend/electron/main.js`, package.json scripts

## Task 8: Dev launcher + startup templates
- `scripts/dev_start_*.sh`, `packaging/`

## Task 9: Documentation
- `docs/document-memory.md`, `docs/desktop-app.md`, `docs/startup.md`, roadmap

## Task 10: Verify, commit, push

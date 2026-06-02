"""JARVIS Desktop Assistant — FastAPI Application Entry Point.

This is the main backend server that exposes:
- REST API for the UI frontend
- Skill execution endpoints
- Workflow & automation management
- Voice endpoints
- Settings & logging

Start with: uvicorn backend.main:app --host 127.0.0.1 --port 8400 --reload
"""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.core.assistant import assistant
from backend.core.config import settings
from backend.core.logger import logger, setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    # Startup
    setup_logging()
    logger.info("🚀 JARVIS Desktop Assistant starting — env={}", settings.env)

    # Ensure backend is on path
    backend_dir = Path(__file__).resolve().parent.parent
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

    # Initialize subsystems
    try:
        assistant.initialize()
    except Exception as exc:
        logger.error("Failed to initialize subsystems: {}", exc)

    # Initialize LLM Gateway
    try:
        from backend.llm.gateway import llm_gateway
        llm_gateway.initialize_from_config()
        logger.info("LLM Gateway initialized")
    except Exception as exc:
        logger.warning("LLM Gateway initialization skipped: {}", exc)

    # Initialize Voice Gateway
    try:
        from backend.voice.gateway import voice_gateway
        voice_gateway.initialize()
        logger.info("Voice Gateway initialized")
    except Exception as exc:
        logger.warning("Voice Gateway initialization skipped: {}", exc)

    # Auto-detect apps on first run
    try:
        from backend.apps.config_store import app_config_store
        from backend.apps.detection import detect_apps
        existing = app_config_store.get_all()
        if not existing:
            logger.info("No apps configured — running auto-detection...")
            detected = detect_apps()
            app_config_store.import_from_detection(detected)
            logger.info("Auto-detected and imported {} apps", len(detected))
        else:
            logger.info("App config loaded: {} apps", len(existing))
    except Exception as exc:
        logger.warning("App auto-detection skipped: {}", exc)

    # Start Automation Engine scheduler
    try:
        from backend.automation.engine import automation_engine
        automation_engine.start_scheduler()
        logger.info("Automation Engine scheduler started")
    except Exception as exc:
        logger.warning("Automation Engine scheduler start skipped: {}", exc)

    yield

    # Stop Automation Engine scheduler
    try:
        from backend.automation.engine import automation_engine
        automation_engine.stop_scheduler()
    except Exception:
        pass

    # Shutdown
    logger.info("👋 JARVIS shutting down")


# ── App ──

app = FastAPI(
    title="Jarvis Desktop Assistant",
    description="Modular AI desktop assistant — control your PC, chat, execute commands, manage workflows and automations.",
    version="0.2.0",
    lifespan=lifespan,
)

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Root ──

@app.get("/")
def root():
    """Serve frontend if built, otherwise health JSON."""
    FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
    index_path = FRONTEND_DIST / "index.html"
    if index_path.exists():
        from fastapi.responses import FileResponse
        return FileResponse(index_path)
    return {
        "name": "Jarvis Desktop Assistant",
        "version": "0.3.0",
        "status": "running",
        "skills_loaded": len(_get_skills()),
    }


def _get_skills() -> list[str]:
    try:
        from backend.core.registry import skill_registry
        return skill_registry.skill_names
    except Exception:
        return []


@app.get("/health")
async def health():
    """Detailed health check with LLM status."""
    llm_status = {"provider": "none", "available": False, "model": ""}
    try:
        from backend.llm.gateway import llm_gateway
        llm_status = await llm_gateway.get_status()
    except Exception:
        pass

    return {
        "status": "ok",
        "version": "0.2.0",
        "env": settings.env,
        "skills": _get_skills(),
        "llm": llm_status,
    }


# ── Include API Routers ──

from backend.api.chat import router as chat_router
from backend.api.command import router as command_router
from backend.api.conversations import router as conversations_router
from backend.api.skills import router as skills_router
from backend.api.settings import router as settings_router
from backend.api.voice import router as voice_router
from backend.api.habits import router as habits_router
from backend.api.documents import router as documents_router
from backend.api.setup import router as setup_router
from backend.api.diagnostics import router as diagnostics_router
from backend.api.apps_config import router as apps_config_router
from backend.api.apps_wizard import router as apps_wizard_router
from backend.api.pending_actions import router as pending_actions_router
from backend.api.timers import router as timers_router

app.include_router(chat_router, prefix="/api")
app.include_router(command_router, prefix="/api")
app.include_router(conversations_router)
app.include_router(skills_router, prefix="/api")
app.include_router(settings_router, prefix="/api")
app.include_router(voice_router, prefix="/api")
app.include_router(habits_router, prefix="/api")
app.include_router(documents_router)
app.include_router(setup_router)
app.include_router(diagnostics_router)
app.include_router(pending_actions_router)
app.include_router(apps_config_router, prefix="/api")
app.include_router(timers_router, prefix="/api")
app.include_router(apps_wizard_router)


# ── Serve Frontend SPA (only if built) ──

FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"

if FRONTEND_DIST.is_dir():
    # Mount entire dist as SPA — StaticFiles with html=True handles:
    #   /          → index.html
    #   /chat      → index.html (SPA fallback)
    #   /assets/*  → actual files
    # Previously registered routes (/health, /api/*) remain active.
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend_spa")
    logger.info("🎨 Frontend SPA mounted from {}", FRONTEND_DIST)
else:
    logger.info("ℹ️  Frontend not built — API-only mode. Run 'npm run build' to enable UI.")

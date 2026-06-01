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

    yield

    # Shutdown
    logger.info("👋 JARVIS shutting down")


# ── App ──

app = FastAPI(
    title="Jarvis Desktop Assistant",
    description="Modular AI desktop assistant — control your PC, chat, execute commands, manage workflows and automations.",
    version="0.1.0",
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
    """Health check and basic info."""
    return {
        "name": "Jarvis Desktop Assistant",
        "version": "0.1.0",
        "status": "running",
        "skills_loaded": len(assistant._initialized and _get_skills() or []),
    }


def _get_skills() -> list[str]:
    try:
        from backend.core.registry import skill_registry
        return skill_registry.skill_names
    except Exception:
        return []


@app.get("/health")
def health():
    """Detailed health check."""
    return {
        "status": "ok",
        "version": "0.1.0",
        "env": settings.env,
        "skills": _get_skills(),
    }


# ── Include API Routers ──

from backend.api.chat import router as chat_router
from backend.api.command import router as command_router
from backend.api.skills import router as skills_router
from backend.api.settings import router as settings_router

app.include_router(chat_router, prefix="/api")
app.include_router(command_router, prefix="/api")
app.include_router(skills_router, prefix="/api")
app.include_router(settings_router, prefix="/api")

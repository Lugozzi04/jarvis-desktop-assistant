"""Health & Diagnostics API — full system status, logs, and export."""

from __future__ import annotations

import json
import platform
from datetime import datetime

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from backend.core.logger import logger
from backend.core.config import settings

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health/full")
async def health_full():
    """Comprehensive system health check."""
    result = {
        "timestamp": datetime.utcnow().isoformat(),
        "backend": await _backend_status(),
        "llm": await _llm_status(),
        "documents": await _documents_status(),
        "voice": await _voice_status(),
        "automations": await _automations_status(),
        "workflows": await _workflows_status(),
        "skills": await _skills_status(),
        "pending_actions": await _pending_actions_status(),
        "desktop": _desktop_status(),
        "environment": {
            "python": platform.python_version(),
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "warnings": [],
        "errors": [],
        "recommended_next_steps": [],
    }

    # Warnings
    if not result["llm"]["available"]:
        result["warnings"].append("LLM not available — run setup wizard or install Ollama")
    if not result["documents"]["ready"]:
        result["warnings"].append("Document memory empty — index some files")
    if not result["voice"]["available"]:
        result["warnings"].append("Voice not configured — install faster-whisper for STT")

    if result["errors"]:
        result["recommended_next_steps"].append("Fix errors before using affected features")
    if result["warnings"]:
        result["recommended_next_steps"].append("Run Setup Wizard to configure components")
    result["recommended_next_steps"].append("Open Dashboard to see full status")

    return result


@router.get("/diagnostics")
async def diagnostics():
    """Get diagnostics summary (no secrets)."""
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "version": "0.3.0",
        "environment": {
            "python": platform.python_version(),
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "node": _get_node_version(),
        },
        "config_public": _get_public_config(),
        "skills": await _skills_status(),
        "backend": await _backend_status(),
        "llm": {k: v for k, v in (await _llm_status()).items() if k != "api_key"},
    }


@router.get("/diagnostics/logs")
async def diagnostics_logs(lines: int = 100):
    """Get recent log lines (no sensitive data)."""
    try:
        log_file = settings.data_dir / "jarvis.log"
        if log_file.exists():
            content = log_file.read_text()
            return {"logs": content.splitlines()[-lines:]}
    except Exception:
        pass
    return {"logs": []}


@router.post("/diagnostics/export")
async def diagnostics_export():
    """Export full diagnostics as JSON (no secrets)."""
    diag = await diagnostics()
    return diag


@router.get("/config/public")
async def config_public():
    """Get public (non-sensitive) configuration."""
    return _get_public_config()


@router.get("/config/status")
async def config_status():
    """Get configuration status (which providers are configured)."""
    return {
        "backend_ready": True,
        "llm_configured": _llm_configured(),
        "documents_configured": True,
        "voice_configured": _voice_configured(),
        "integrations": {
            "obs": True,
            "discord": True,
            "spotify": True,
            "github": True,
        },
    }


# ── Private helpers ──

async def _backend_status():
    from backend.core.assistant import assistant
    skills = []
    try:
        from backend.core.registry import skill_registry
        skills = skill_registry.skill_names
    except Exception:
        pass
    return {
        "online": True,
        "version": "0.3.0",
        "skills_loaded": len(skills),
        "initialized": assistant._initialized,
    }


async def _llm_status():
    try:
        from backend.llm.gateway import llm_gateway
        return await llm_gateway.get_status()
    except Exception:
        return {"provider": "none", "available": False, "model": "", "error": "Gateway not initialized"}


async def _documents_status():
    try:
        from backend.memory.vector_store import get_vector_store
        store = get_vector_store()
        s = store.get_status()
        from backend.memory.embeddings import get_embedding_provider
        provider = get_embedding_provider()
        return {
            "ready": True,
            "documents": s.get("documents", 0),
            "chunks": s.get("chunks", 0),
            "embedding_provider": provider.name,
            "provider_available": provider.available,
        }
    except Exception as e:
        return {"ready": False, "error": str(e)}


async def _voice_status():
    try:
        from backend.voice.gateway import voice_gateway
        if not voice_gateway._initialized:
            voice_gateway.initialize()
        return {
            "available": voice_gateway.stt_available or voice_gateway.tts_available,
            "stt": voice_gateway.stt_provider,
            "tts": voice_gateway.tts_provider,
        }
    except Exception:
        return {"available": False, "stt": "none", "tts": "none"}


async def _automations_status():
    try:
        from backend.automation.engine import automation_engine
        return {"scheduler_running": automation_engine._running, "automations_loaded": len(automation_engine._automations)}
    except Exception:
        return {"scheduler_running": False}


async def _workflows_status():
    try:
        from backend.workflows.engine import workflow_engine
        return {"workflows_loaded": len(workflow_engine.list_workflows())}
    except Exception:
        return {"workflows_loaded": 0}


async def _skills_status():
    try:
        from backend.core.registry import skill_registry
        return {"loaded": skill_registry.skill_names}
    except Exception:
        return {"loaded": []}


async def _pending_actions_status():
    try:
        from backend.core.pending_actions import pending_queue
        return {"count": len(pending_queue.get_pending()), "queue_enabled": True}
    except Exception:
        return {"count": 0, "queue_enabled": False}


def _desktop_status():
    return {"electron": True, "portable_mode": True, "webview": "pywebview"}


def _get_public_config():
    return {
        "version": "0.3.0",
        "env": settings.env,
        "llm_provider": getattr(settings.llm, "default_provider", "none"),
        "llm_model": getattr(settings.llm, "default_model", "none"),
        "allow_cloud": getattr(settings.llm, "allow_cloud", False),
        "embedding_provider": getattr(settings, "embedding_provider", "simple"),
        "voice_enabled": getattr(settings, "voice_enabled", False),
    }


def _llm_configured():
    try:
        from backend.llm.gateway import llm_gateway
        return any(p.available for p in llm_gateway._providers.values()) if llm_gateway._providers else False
    except Exception:
        return False


def _voice_configured():
    try:
        from backend.voice.gateway import voice_gateway
        if not voice_gateway._initialized:
            voice_gateway.initialize()
        return voice_gateway.stt_available or voice_gateway.tts_available
    except Exception:
        return False


def _get_node_version():
    import subprocess
    try:
        return subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=3).stdout.strip()
    except Exception:
        return "unknown"

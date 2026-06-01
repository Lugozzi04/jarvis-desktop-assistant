"""Settings API — read and update configuration."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from backend.core.config import settings

router = APIRouter(tags=["settings"])


@router.get("/settings")
def get_settings():
    """Get current configuration (safe, no secrets)."""
    return {
        "env": settings.env,
        "log_level": settings.log_level,
        "ui_host": settings.ui_host,
        "ui_port": settings.ui_port,
        "llm": {
            "default_provider": settings.llm.default_provider,
            "default_model": settings.llm.default_model,
            "allow_cloud": settings.llm.allow_cloud,
        },
        "voice": {
            "enabled": settings.voice_enabled,
            "wake_word": settings.voice.wake_word,
        },
        "security": {
            "confirm_dangerous": settings.security.confirm_dangerous_actions,
            "auto_approve_safe": settings.security.auto_approve_safe,
        },
    }


@router.post("/settings")
def update_settings(updates: dict[str, Any]):
    """Update settings (placeholder — persistent settings in M2)."""
    # In the full implementation, this would write to DB
    return {"status": "received", "updates": updates, "note": "Settings persistence coming in M2"}

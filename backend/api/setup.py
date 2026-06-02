"""Setup Wizard API — first-run configuration and readiness endpoints."""

from __future__ import annotations

from fastapi import APIRouter
from backend.core.setup_state import setup_state

router = APIRouter(prefix="/api/setup", tags=["setup"])


@router.get("/status")
def get_setup_status():
    """Get current setup wizard status."""
    return setup_state.get_status().model_dump()


@router.post("/complete")
def complete_setup():
    """Mark setup wizard as completed."""
    setup_state.mark_completed()
    return {"status": "completed"}


@router.post("/reset")
def reset_setup():
    """Reset setup wizard — will show on next app start."""
    setup_state.reset()
    return {"status": "reset"}


@router.post("/component/{component}")
def mark_component_ready(component: str, ready: bool = True):
    """Mark a specific component as ready/not ready."""
    valid = ["llm", "documents", "voice", "security", "obs", "discord", "spotify", "github"]
    if component not in valid:
        return {"error": f"Invalid component. Valid: {valid}"}
    setup_state.mark_component(component, ready)
    return {"component": component, "ready": ready}


@router.get("/recommendations")
def get_recommendations():
    """Get setup recommendations (LLM model commands, etc.)."""
    return setup_state.get_recommendations()


@router.post("/refresh")
def refresh_status():
    """Force-refresh dynamic readiness fields."""
    # Getting status already refreshes
    return setup_state.get_status().model_dump()

"""Apps Config API — browse, configure, and detect desktop applications."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from backend.core.app_config import (
    AppConfigUpdate,
    get_app_config_store,
)

router = APIRouter(tags=["apps"])


# ── GET /apps/config ──

@router.get("/apps/config")
def get_apps_config():
    """Get all configured app definitions."""
    store = get_app_config_store()
    return {"apps": [cfg.model_dump() for cfg in store.get_all()]}


# ── GET /apps/config/{name} ──

@router.get("/apps/config/{name}")
def get_app_config(name: str):
    """Get a single app config by name."""
    store = get_app_config_store()
    cfg = store.get(name)
    if cfg is None:
        raise HTTPException(status_code=404, detail=f"App '{name}' not found")
    return cfg.model_dump()


# ── POST /apps/config ──

@router.post("/apps/config")
def create_or_update_app_config(payload: dict[str, Any]):
    """Create or update an app config.

    Body must contain at least 'name' and may include partial fields:
    path, aliases, type, enabled, notes.

    If an app with that name already exists, the provided fields are merged.
    """
    name = payload.get("name")
    if not name or not isinstance(name, str):
        raise HTTPException(status_code=400, detail="Field 'name' is required")

    # Validate the partial update shape
    update_fields = {k: v for k, v in payload.items() if k != "name"}
    try:
        AppConfigUpdate(**update_fields)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid config fields: {exc}")

    store = get_app_config_store()
    cfg = store.set(name, payload)
    return cfg.model_dump()


# ── DELETE /apps/config/{name} ──

@router.delete("/apps/config/{name}")
def delete_app_config(name: str):
    """Delete an app config."""
    store = get_app_config_store()
    if not store.delete(name):
        raise HTTPException(status_code=404, detail=f"App '{name}' not found")
    return {"status": "deleted", "name": name}


# ── GET /apps/detect ──

@router.get("/apps/detect")
def detect_apps():
    """Detect installed and running apps.

    On desktop: uses shutil.which() and psutil (when installed).
    On headless/VPS: returns mock placeholders.
    """
    store = get_app_config_store()
    results = store.detect()
    return {"apps": [r.model_dump() for r in results]}


# ── POST /apps/aliases ──

@router.post("/apps/aliases")
def set_app_aliases(payload: dict[str, Any]):
    """Set aliases for a specific app.

    Body: { "name": "vscode", "aliases": ["code", "Code-OSS"] }
    """
    name = payload.get("name")
    aliases = payload.get("aliases")

    if not name or not isinstance(name, str):
        raise HTTPException(status_code=400, detail="Field 'name' is required")
    if aliases is None or not isinstance(aliases, list):
        raise HTTPException(status_code=400, detail="Field 'aliases' (list of strings) is required")

    store = get_app_config_store()
    existing = store.get(name)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"App '{name}' not found")

    cfg = store.set(name, {"aliases": aliases})
    return cfg.model_dump()

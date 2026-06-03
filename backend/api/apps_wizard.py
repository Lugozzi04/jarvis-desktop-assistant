"""App Configuration & Detection API — unified router.

All app-related endpoints live here:
  GET  /api/apps          — list all configured apps
  POST /api/apps          — add custom app
  GET  /api/apps/detect   — scan system for apps
  POST /api/apps/import   — scan + import into config
  PUT  /api/apps/{name}   — update app (command, enabled, aliases)
  DELETE /api/apps/{name} — remove app
"""

from __future__ import annotations

import platform
import shutil
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.apps.config_store import app_config_store
from backend.apps.detection import detect_apps
from backend.core.logger import logger

router = APIRouter(prefix="/api/apps", tags=["apps"])


# ── Models ──

class AppConfigOut(BaseModel):
    name: str
    command: str = ""
    path: str = ""
    aliases: list[str] = []
    enabled: bool = True
    builtin: bool = False
    detected: bool = False


class AppUpdate(BaseModel):
    command: str | None = None
    enabled: bool | None = None
    aliases: list[str] | None = None


class AppCreate(BaseModel):
    name: str
    command: str
    aliases: list[str] | None = None


# ── Routes ──

@router.get("")
def list_apps():
    """List all configured apps."""
    apps = app_config_store.get_all()
    result = []
    for v in apps.values():
        result.append({
            "name": v.get("name", ""),
            "command": v.get("command", ""),
            "path": v.get("path", ""),
            "aliases": v.get("aliases", []),
            "enabled": v.get("enabled", True),
            "builtin": v.get("builtin", False),
            "detected": v.get("detected", False),
        })
    return {"apps": result, "total": len(result)}


@router.get("/detect")
def detect():
    """Scan system for installed applications."""
    logger.info("App detection requested — platform={}", platform.system())
    try:
        apps = detect_apps()
        return {"apps": apps, "total": len(apps)}
    except Exception as exc:
        logger.error("App detection failed: {}", exc)
        # Fallback: return built-in apps only
        fallback = [
            {"name": "Calculator", "command": "calc.exe", "path": "calc.exe", "category": "system", "aliases": ["calc", "calcolatrice"], "builtin": True, "detected": True},
            {"name": "Notepad", "command": "notepad.exe", "path": "notepad.exe", "category": "system", "aliases": ["notepad", "note"], "builtin": True, "detected": True},
            {"name": "Explorer", "command": "explorer.exe", "path": "explorer.exe", "category": "system", "aliases": ["explorer", "files"], "builtin": True, "detected": True},
            {"name": "Terminal", "command": "wt.exe", "path": "wt.exe", "category": "system", "aliases": ["terminal", "term"], "builtin": True, "detected": True},
            {"name": "Discord", "command": "discord", "path": "", "category": "desktop", "aliases": ["discord"], "builtin": False, "detected": False},
            {"name": "Spotify", "command": "spotify", "path": "", "category": "desktop", "aliases": ["spotify"], "builtin": False, "detected": False},
            {"name": "VS Code", "command": "code", "path": "", "category": "desktop", "aliases": ["vscode", "code"], "builtin": False, "detected": False},
            {"name": "OBS Studio", "command": "obs64.exe", "path": "", "category": "desktop", "aliases": ["obs"], "builtin": False, "detected": False},
        ]
        return {"apps": fallback, "total": len(fallback), "error": str(exc)}


@router.post("/import")
def import_apps():
    """Run detection and import new apps into config."""
    logger.info("App import requested")
    try:
        detected = detect_apps()
        imported = app_config_store.import_from_detection(detected)
        apps = app_config_store.get_all()
        result = []
        for v in apps.values():
            result.append({
                "name": v.get("name", ""),
                "command": v.get("command", ""),
                "path": v.get("path", ""),
                "aliases": v.get("aliases", []),
                "enabled": v.get("enabled", True),
                "builtin": v.get("builtin", False),
                "detected": v.get("detected", False),
            })
        return {"imported": imported, "total": len(detected), "apps": result}
    except Exception as exc:
        logger.error("App import failed: {}", exc)
        raise HTTPException(status_code=500, detail=f"Import failed: {exc}")


@router.put("/{name}")
def update_app(name: str, update: AppUpdate):
    """Update an app's configuration."""
    key = name.lower()
    app = app_config_store.get(key)
    if not app:
        raise HTTPException(status_code=404, detail=f"App '{name}' not found")

    if update.command is not None:
        app_config_store.update_command(name, update.command)
        app["command"] = update.command
        app["path"] = update.command
    if update.enabled is not None:
        app_config_store.set_enabled(name, update.enabled)
        app["enabled"] = update.enabled
    if update.aliases is not None:
        app["aliases"] = update.aliases
        app_config_store._save()

    return {"success": True, "app": app}


@router.post("")
def create_app(app: AppCreate):
    """Add a custom app."""
    config = app_config_store.add(
        name=app.name,
        command=app.command,
        aliases=app.aliases,
    )
    config["user_configured"] = True
    config["command_override"] = True
    app_config_store._save()
    return {"success": True, "app": config}


@router.delete("/{name}")
def delete_app(name: str):
    """Remove an app from config."""
    if app_config_store.remove(name):
        return {"success": True}
    raise HTTPException(status_code=404, detail=f"App '{name}' not found")

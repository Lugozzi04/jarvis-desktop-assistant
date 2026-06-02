"""App Configuration & Detection API."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from backend.apps.config_store import app_config_store
from backend.apps.detection import detect_apps
from backend.core.logger import logger

router = APIRouter(prefix="/api/apps", tags=["apps"])


class AppConfig(BaseModel):
    name: str
    command: str
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


class AppImportResult(BaseModel):
    imported: int
    total: int
    apps: list[AppConfig]


@router.get("/apps/detect")
def api_detect_apps():
    """Scan system for installed apps."""
    logger.info("App detection requested")
    apps = detect_apps()
    return {"apps": apps, "total": len(apps)}


@router.get("/apps")
def api_list_apps():
    """List all configured apps."""
    apps = app_config_store.get_all()
    return {"apps": [{"name": v["name"], **{k: v[k] for k in v if k != "name"}} for v in apps.values()], "total": len(apps)}


@router.post("/apps/import")
def api_import_apps() -> AppImportResult:
    """Run detection and import new apps into config."""
    detected = detect_apps()
    imported = app_config_store.import_from_detection(detected)
    apps = app_config_store.get_all()
    return AppImportResult(
        imported=imported,
        total=len(detected),
        apps=[
            AppConfig(
                name=v["name"],
                command=v.get("command", ""),
                path=v.get("path", ""),
                aliases=v.get("aliases", []),
                enabled=v.get("enabled", True),
                builtin=v.get("builtin", False),
                detected=v.get("detected", False),
            )
            for v in apps.values()
        ],
    )


@router.put("/apps/{name}")
def api_update_app(name: str, update: AppUpdate):
    """Update an app's configuration."""
    key = name.lower()
    app = app_config_store.get(key)
    if not app:
        return {"error": f"App '{name}' not found"}

    if update.command is not None:
        app_config_store.update_command(name, update.command)
    if update.enabled is not None:
        app_config_store.set_enabled(name, update.enabled)
    if update.aliases is not None:
        app["aliases"] = update.aliases
        app_config_store._save()

    return {"success": True, "app": app}


@router.post("/apps")
def api_create_app(app: AppCreate):
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


@router.delete("/apps/{name}")
def api_delete_app(name: str):
    """Remove an app from config."""
    if app_config_store.remove(name):
        return {"success": True}
    return {"error": f"App '{name}' not found"}

"""Settings API — read and update configuration, LLM status and setup."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from backend.core.config import settings
from backend.core.logger import logger

router = APIRouter(tags=["settings"])


class LLMTestRequest(BaseModel):
    provider: str = ""
    base_url: str = ""
    api_key: str = ""
    model: str = ""


class LanguageUpdate(BaseModel):
    language: str  # "it" or "en"


# ── Language storage ──

def _get_language_path() -> Path:
    return settings.data_path / "language.json"


def get_language() -> str:
    """Read language preference. Default: 'it' (Italian)."""
    try:
        p = _get_language_path()
        if p.exists():
            data = json.loads(p.read_text())
            return data.get("language", "it")
    except Exception:
        pass
    return "it"


def set_language(lang: str) -> str:
    """Save language preference. Returns the saved language."""
    lang = lang.lower()
    if lang not in ("it", "en"):
        lang = "it"
    try:
        p = _get_language_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"language": lang}))
    except Exception as exc:
        logger.error("Failed to save language: {}", exc)
    return lang


# ── API routes ──


@router.get("/settings")
def get_settings():
    """Get current configuration (safe, no secrets)."""
    return {
        "env": settings.env,
        "log_level": settings.log_level,
        "ui_host": settings.ui_host,
        "ui_port": settings.ui_port,
        "language": get_language(),
        "llm": {
            "default_provider": settings.llm.default_provider,
            "default_model": settings.llm.default_model,
            "allow_cloud": settings.llm.allow_cloud,
            "has_api_key": bool(settings.llm.api_key),
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
    """Update settings (placeholder — persistent settings coming)."""
    return {"status": "received", "updates": updates, "note": "Settings persistence coming soon"}


@router.put("/settings/language")
def update_language_api(data: LanguageUpdate):
    """Update language setting ('it' or 'en')."""
    lang = set_language(data.language)
    return {"language": lang, "success": True}


@router.post("/settings/llm/test")
async def test_llm_connection(request: LLMTestRequest):
    """Test an LLM provider connection with detailed diagnostics."""
    provider_name = request.provider or settings.llm.default_provider

    try:
        from backend.llm.gateway import llm_gateway

        # Configure temporarily if needed
        if request.provider and request.provider not in llm_gateway._providers:
            try:
                llm_gateway.configure(
                    provider_name=provider_name,
                    base_url=request.base_url or "",
                    api_key=request.api_key or "",
                    model=request.model or settings.llm.default_model,
                )
            except Exception as exc:
                return {
                    "success": False,
                    "provider": provider_name,
                    "error": f"Failed to configure provider: {exc}",
                }

        result = await llm_gateway.test_connection(provider_name)
        return result
    except Exception as exc:
        logger.error("LLM test failed: {}", exc)
        return {"success": False, "provider": provider_name, "error": str(exc)}


@router.get("/logs")
def get_logs(limit: int = 50):
    """Get recent audit logs from the database."""
    try:
        from backend.db.database import AuditLog, get_session_factory

        factory = get_session_factory()
        db = factory()
        try:
            rows = (
                db.query(AuditLog)
                .order_by(AuditLog.id.desc())
                .limit(limit)
                .all()
            )
            return {
                "logs": [
                    {
                        "id": r.id,
                        "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                        "input_raw": r.input_raw,
                        "intent_kind": r.intent_kind,
                        "skill": r.skill,
                        "action": r.action,
                        "risk": r.risk,
                        "result_success": r.result_success,
                        "result_summary": r.result_summary,
                        "error": r.error,
                        "duration_ms": r.duration_ms,
                    }
                    for r in rows
                ]
            }
        finally:
            db.close()
    except Exception as exc:
        logger.error("Failed to fetch logs: {}", exc)
        return {"logs": [], "error": str(exc)}


@router.get("/llm/status")
async def llm_status():
    """Get detailed LLM Gateway status.

    Returns:
        For Ollama: reachable, model_available, available_models,
        recommended_command, setup_required, error messages.
    """
    try:
        from backend.llm.gateway import llm_gateway
        return await llm_gateway.get_status()
    except Exception as exc:
        return {
            "provider": "none",
            "available": False,
            "ready": False,
            "error": str(exc),
        }


@router.get("/llm/recommended")
async def llm_recommended():
    """Get recommended model configuration."""
    try:
        from backend.llm.gateway import llm_gateway
        return await llm_gateway.get_recommended_models()
    except Exception as exc:
        return {"error": str(exc)}


@router.get("/llm/ollama-setup-guide")
async def ollama_setup_guide():
    """Get Ollama local setup guide."""
    try:
        from backend.llm.gateway import llm_gateway
        return await llm_gateway.get_ollama_setup_guide()
    except Exception as exc:
        return {"error": str(exc)}


@router.get("/workflows")
def list_workflows():
    """List workflows."""
    try:
        from backend.workflows.engine import workflow_engine
        return {"workflows": workflow_engine.list_all()}
    except Exception as exc:
        return {"workflows": [], "error": str(exc)}


@router.post("/workflows")
def create_workflow(data: dict[str, Any]):
    """Create a new workflow."""
    try:
        from backend.workflows.engine import workflow_engine
        return workflow_engine.create(data)
    except Exception as exc:
        return {"error": str(exc)}


@router.get("/workflows/{workflow_id}")
def get_workflow(workflow_id: str):
    """Get a workflow by ID."""
    try:
        from backend.workflows.engine import workflow_engine
        wf = workflow_engine.get(workflow_id)
        if wf is None:
            return {"error": "Workflow not found"}
        return wf
    except Exception as exc:
        return {"error": str(exc)}


@router.post("/workflows/{workflow_id}/run")
def run_workflow(workflow_id: str):
    """Execute a workflow."""
    try:
        from backend.workflows.engine import workflow_engine
        return workflow_engine.run(workflow_id)
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


@router.delete("/workflows/{workflow_id}")
def delete_workflow(workflow_id: str):
    """Delete a workflow."""
    try:
        from backend.workflows.engine import workflow_engine
        return workflow_engine.delete(workflow_id)
    except Exception as exc:
        return {"error": str(exc)}


@router.get("/automations")
def list_automations():
    """List all automations."""
    try:
        from backend.automation.engine import automation_engine
        return {"automations": automation_engine.list_all()}
    except Exception as exc:
        return {"automations": [], "error": str(exc)}


@router.post("/automations")
def create_automation(data: dict[str, Any]):
    """Create a new automation."""
    try:
        from backend.automation.engine import automation_engine
        return automation_engine.create(data)
    except Exception as exc:
        return {"error": str(exc)}


@router.get("/automations/{automation_id}")
def get_automation(automation_id: str):
    """Get an automation by ID."""
    try:
        from backend.automation.engine import automation_engine
        auto = automation_engine.get(automation_id)
        if auto is None:
            return {"error": "Automation not found"}
        return auto
    except Exception as exc:
        return {"error": str(exc)}


@router.put("/automations/{automation_id}")
def update_automation(automation_id: str, data: dict[str, Any]):
    """Update an automation."""
    try:
        from backend.automation.engine import automation_engine
        return automation_engine.update(automation_id, data)
    except Exception as exc:
        return {"error": str(exc)}


@router.delete("/automations/{automation_id}")
def delete_automation(automation_id: str):
    """Delete an automation."""
    try:
        from backend.automation.engine import automation_engine
        return automation_engine.delete(automation_id)
    except Exception as exc:
        return {"error": str(exc)}


@router.post("/automations/{automation_id}/enable")
def enable_automation(automation_id: str):
    """Enable an automation."""
    try:
        from backend.automation.engine import automation_engine
        return automation_engine.enable(automation_id)
    except Exception as exc:
        return {"error": str(exc)}


@router.post("/automations/{automation_id}/disable")
def disable_automation(automation_id: str):
    """Disable an automation."""
    try:
        from backend.automation.engine import automation_engine
        return automation_engine.disable(automation_id)
    except Exception as exc:
        return {"error": str(exc)}


@router.post("/automations/{automation_id}/run")
def run_automation(automation_id: str):
    """Execute an automation manually."""
    try:
        from backend.automation.engine import automation_engine
        return automation_engine.run(automation_id, triggered_by="manual")
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


@router.get("/automations/engine/status")
def automation_engine_status():
    """Get automation engine/scheduler status."""
    try:
        from backend.automation.engine import automation_engine
        return automation_engine.get_scheduler_status()
    except Exception as exc:
        return {"running": False, "error": str(exc)}


@router.post("/automations/reload")
def reload_automations():
    """Reload automations from storage."""
    try:
        from backend.automation.engine import automation_engine
        return automation_engine.reload()
    except Exception as exc:
        return {"error": str(exc)}

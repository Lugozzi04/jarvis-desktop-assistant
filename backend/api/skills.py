"""Skills API — list, inspect, and execute skills."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from backend.core.registry import skill_registry

router = APIRouter(tags=["skills"])


@router.get("/skills")
def list_skills():
    """List all registered skills with status and actions."""
    return {"skills": skill_registry.list_skills()}


@router.get("/skills/{skill_name}")
def get_skill(skill_name: str):
    """Get a single skill with its manifest and actions."""
    skill = skill_registry.get(skill_name)
    manifest = skill_registry.get_manifest(skill_name)
    return {
        "name": skill.name,
        "display_name": skill.display_name,
        "description": skill.description,
        "version": skill.version,
        "enabled": skill.enabled,
        "actions": manifest.get("actions", []),
    }


@router.post("/skills/{skill_name}/execute")
def execute_skill(skill_name: str, action: str, parameters: dict[str, Any] | None = None):
    """Execute a skill action directly."""
    params = parameters or {}
    result = skill_registry.execute(skill_name, action, params)
    return result.model_dump()

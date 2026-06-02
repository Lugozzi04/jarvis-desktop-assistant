"""Workflow Engine — models, storage, and execution."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class WorkflowStep(BaseModel):
    """A single step in a workflow."""

    order: int
    skill: str
    action: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    description: str = ""


class Workflow(BaseModel):
    """A complete workflow definition."""

    id: str
    name: str
    description: str = ""
    steps: list[WorkflowStep]
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class StepResult(BaseModel):
    """Result of a single workflow step execution."""

    order: int
    skill: str
    action: str
    status: str  # success, failed, skipped
    result: Any = None
    error: str | None = None
    duration_ms: float = 0.0


class WorkflowRunResult(BaseModel):
    """Result of running a complete workflow."""

    workflow_id: str
    workflow_name: str
    status: str  # success, partial, failed
    steps: list[StepResult]
    started_at: str
    finished_at: str
    total_duration_ms: float = 0.0


# ── Seed Workflows ──

SEED_WORKFLOWS: list[dict[str, Any]] = [
    {
        "id": "live-setup",
        "name": "Live Setup",
        "description": "Prepare streaming environment — open OBS, Twitch Dashboard, and Spotify",
        "steps": [
            {"order": 1, "skill": "apps", "action": "open", "parameters": {"app_name": "OBS"}, "description": "Open OBS Studio"},
            {"order": 2, "skill": "browser", "action": "open_url", "parameters": {"url": "https://dashboard.twitch.tv"}, "description": "Open Twitch Dashboard"},
            {"order": 3, "skill": "apps", "action": "open", "parameters": {"app_name": "Spotify"}, "description": "Open Spotify"},
            {"order": 4, "skill": "timers", "action": "create_timer", "parameters": {"duration": "10m", "message": "Check audio and bitrate"}, "description": "Quality check timer"},
        ],
    },
    {
        "id": "study-session",
        "name": "Study Session",
        "description": "Start a focused study session with timer and resources",
        "steps": [
            {"order": 1, "skill": "timers", "action": "create_timer", "parameters": {"duration": "50m", "message": "Focus session — no distractions!"}, "description": "50-minute focus timer"},
            {"order": 2, "skill": "system", "action": "get_stats", "parameters": {}, "description": "Check system resources"},
        ],
    },
    {
        "id": "dev-session",
        "name": "Dev Session",
        "description": "Start development environment — open VS Code, terminal, and local server",
        "steps": [
            {"order": 1, "skill": "apps", "action": "open", "parameters": {"app_name": "VS Code"}, "description": "Open VS Code"},
            {"order": 2, "skill": "browser", "action": "open_url", "parameters": {"url": "http://localhost:3000"}, "description": "Open local dev server"},
            {"order": 3, "skill": "system", "action": "get_stats", "parameters": {}, "description": "Check system resources"},
        ],
    },
]

"""Automation Engine — models for triggers, conditions, actions, and runs.

Follows the same Pydantic pattern as workflows/models.py.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


# ── Trigger ──

class TriggerConfig(BaseModel):
    """Configuration for a trigger."""

    time: str | None = None          # HH:MM format for 'time' trigger
    days: list[str] = Field(default_factory=list)  # ['mon','tue',...] for time trigger
    interval_minutes: int | None = None  # for 'interval' trigger
    app_name: str | None = None      # for 'app_opened' trigger
    mode_name: str | None = None     # for 'mode_is' trigger


class Trigger(BaseModel):
    """What causes the automation to run."""

    type: Literal["manual", "startup", "time", "interval", "app_opened", "mode_is"]
    config: TriggerConfig = Field(default_factory=TriggerConfig)


# ── Condition ──

class ConditionConfig(BaseModel):
    """Configuration for a condition."""

    time: str | None = None          # HH:MM for time_after/time_before
    days: list[str] = Field(default_factory=list)  # for day_of_week
    app_name: str | None = None      # for app_running
    mode_name: str | None = None     # for mode_is


class Condition(BaseModel):
    """A condition that must be met for the automation to run."""

    type: Literal["always", "time_after", "time_before", "day_of_week", "app_running", "mode_is"]
    config: ConditionConfig = Field(default_factory=ConditionConfig)
    operator: str = "equals"  # equals, not_equals, greater_than, less_than


# ── Action ──

class Action(BaseModel):
    """An action to execute when the automation triggers."""

    type: Literal["skill_action", "workflow", "notification", "chat_response"]
    skill: str | None = None
    action: str | None = None
    workflow_id: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    risk: str = "safe"


# ── Automation ──

class Automation(BaseModel):
    """A complete automation rule: when X, if Y, do Z."""

    id: str
    name: str
    description: str = ""
    enabled: bool = False
    trigger: Trigger
    conditions: list[Condition] = Field(default_factory=list)
    actions: list[Action]
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    last_run_at: str | None = None
    run_count: int = 0
    last_status: str | None = None


# ── Run Results ──

class ConditionResult(BaseModel):
    """Result of evaluating a single condition."""

    type: str
    status: str  # passed, failed, error
    message: str = ""
    error: str | None = None


class ActionResult(BaseModel):
    """Result of executing a single action."""

    index: int
    type: str
    status: str  # success, failed, skipped
    result: Any = None
    error: str | None = None


class AutomationRunResult(BaseModel):
    """Result of running a complete automation."""

    automation_id: str
    automation_name: str
    status: str  # success, partial, failed, skipped_requires_confirmation
    triggered_by: str  # manual, scheduler, startup, app_opened
    conditions: list[ConditionResult] = Field(default_factory=list)
    actions: list[ActionResult] = Field(default_factory=list)
    error: str | None = None
    started_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    finished_at: str | None = None
    total_duration_ms: float = 0.0


# ── Seed Automations ──

SEED_AUTOMATIONS: list[dict[str, Any]] = [
    {
        "id": "daily-study-reminder",
        "name": "Daily Study Reminder",
        "description": "Remind me to study every day at 18:00",
        "enabled": False,
        "trigger": {
            "type": "time",
            "config": {
                "time": "18:00",
                "days": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            },
        },
        "conditions": [],
        "actions": [
            {
                "type": "skill_action",
                "skill": "timers",
                "action": "create_reminder",
                "parameters": {"message": "📚 Time to study! Focus for at least 1 hour."},
                "risk": "safe",
            },
        ],
    },
    {
        "id": "startup-llm-status",
        "name": "Startup LLM Status Check",
        "description": "Check LLM status when Jarvis starts",
        "enabled": True,
        "trigger": {
            "type": "startup",
            "config": {},
        },
        "conditions": [],
        "actions": [
            {
                "type": "chat_response",
                "parameters": {
                    "message": "⚡ JARVIS started. Check LLM Settings to verify your provider is connected.",
                },
                "risk": "safe",
            },
        ],
    },
    {
        "id": "dev-session-manual",
        "name": "Dev Session Manual",
        "description": "Run Dev Session workflow manually from automations",
        "enabled": True,
        "trigger": {
            "type": "manual",
            "config": {},
        },
        "conditions": [],
        "actions": [
            {
                "type": "workflow",
                "workflow_id": "dev-session",
                "parameters": {},
                "risk": "safe",
            },
        ],
    },
    {
        "id": "obs-live-workflow",
        "name": "OBS Live Workflow",
        "description": "Run Live Setup workflow when OBS opens (after 18:00)",
        "enabled": False,
        "trigger": {
            "type": "app_opened",
            "config": {"app_name": "OBS"},
        },
        "conditions": [
            {
                "type": "time_after",
                "config": {"time": "18:00"},
            },
        ],
        "actions": [
            {
                "type": "workflow",
                "workflow_id": "live-setup",
                "parameters": {},
                "risk": "safe",
            },
        ],
    },
    {
        "id": "hydration-reminder",
        "name": "Hydration Reminder",
        "description": "Remind me to drink water every 30 minutes",
        "enabled": False,
        "trigger": {
            "type": "interval",
            "config": {"interval_minutes": 30},
        },
        "conditions": [],
        "actions": [
            {
                "type": "notification",
                "parameters": {"message": "💧 Drink some water! Stay hydrated."},
                "risk": "safe",
            },
        ],
    },
]

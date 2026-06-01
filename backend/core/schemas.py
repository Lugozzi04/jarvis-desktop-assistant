"""Core Pydantic schemas for JARVIS.

Every action, intent, skill call, and workflow step is represented
as a typed Pydantic model. No dicts — full validation everywhere.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


# ── Risk Levels ──

class RiskLevel(str, Enum):
    """Risk classification for every action."""

    safe = "safe"
    confirmation = "confirmation"
    dangerous = "dangerous"


# ── Intent Types ──

class IntentKind(str, Enum):
    """Classification of user intent."""

    skill = "skill"          # Direct skill action
    chat = "chat"            # General question / conversation
    workflow = "workflow"    # Execute a workflow
    automation = "automation"  # Manage automations
    settings = "settings"    # Read/change settings
    unknown = "unknown"      # Can't determine intent


class Intent(BaseModel):
    """Parsed user intent — the output of the Intent Router."""

    kind: IntentKind
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    skill: str | None = None
    action: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    workflow_name: str | None = None
    raw_input: str = ""
    needs_clarification: bool = False
    clarification_question: str = ""


# ── Action Schema ──

class SkillAction(BaseModel):
    """A single skill action to execute."""

    type: Literal["skill_action"] = "skill_action"
    skill: str
    action: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    risk: RiskLevel = RiskLevel.safe


class WorkflowStep(BaseModel):
    """A step inside a workflow."""

    order: int
    skill: str
    action: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    description: str = ""


class WorkflowAction(BaseModel):
    """A complete workflow to execute."""

    type: Literal["workflow"] = "workflow"
    name: str
    description: str = ""
    mode: str = "normal"
    steps: list[WorkflowStep]


class AutomationTrigger(BaseModel):
    """Trigger condition for automations."""

    type: str  # time, app_opened, app_closed, system_startup, timer_complete, etc.
    config: dict[str, Any] = Field(default_factory=dict)


class AutomationCondition(BaseModel):
    """Optional condition for automations."""

    type: str = "always"
    config: dict[str, Any] = Field(default_factory=dict)


class AutomationAction(BaseModel):
    """Single action inside an automation."""

    skill: str
    action: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class Automation(BaseModel):
    """Full automation definition."""

    name: str
    description: str = ""
    enabled: bool = True
    trigger: AutomationTrigger
    condition: AutomationCondition = Field(default_factory=AutomationCondition)
    actions: list[AutomationAction]
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ── Action Results ──

class ActionResult(BaseModel):
    """Result of executing an action."""

    success: bool
    skill: str
    action: str
    risk: RiskLevel
    result: Any = None
    error: str | None = None
    confirmation_required: bool = False
    confirmation_message: str = ""
    duration_ms: float = 0.0


# ── User Input ──

class UserInput(BaseModel):
    """Normalized user input."""

    raw: str
    source: Literal["text", "voice", "slash_command", "ui_button", "automation_trigger", "system_event"]
    session_id: str = "default"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ── Log Entry ──

class LogEntry(BaseModel):
    """Structured audit log entry."""

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    input_raw: str
    intent_kind: str
    skill: str | None = None
    action: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    risk: str = "safe"
    confirmation_required: bool = False
    confirmation_granted: bool | None = None
    result_success: bool | None = None
    result_summary: str = ""
    error: str | None = None
    duration_ms: float = 0.0


# ── LLM Gateway ──

class LLMRequest(BaseModel):
    """Request to the LLM Gateway."""

    task: str  # classify, chat, plan, summarize
    messages: list[dict[str, str]]
    prefer_local: bool = True
    require_json: bool = False
    json_schema: dict[str, Any] | None = None
    max_tokens: int = 1024


class LLMResponse(BaseModel):
    """Response from the LLM Gateway."""

    content: str
    model: str
    provider: str
    tokens_used: int = 0
    duration_ms: float = 0.0
    parsed_json: dict[str, Any] | None = None

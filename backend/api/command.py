"""Command API — direct slash command execution."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from backend.core.assistant import assistant
from backend.core.schemas import UserInput

router = APIRouter(tags=["command"])


class CommandRequest(BaseModel):
    command: str  # e.g., "/open discord", "/search best LLM"
    session_id: str = "default"


class CommandResponse(BaseModel):
    response: str
    intent: dict | None = None
    result: dict | None = None
    needs_confirmation: bool = False
    confirmation_message: str = ""
    duration_ms: float = 0.0


@router.post("/command", response_model=CommandResponse)
def execute_command(request: CommandRequest):
    """Execute a slash command."""
    user_input = UserInput(
        raw=request.command,
        source="slash_command",
        session_id=request.session_id,
    )
    result = assistant.process_input(user_input)
    return CommandResponse(
        response=result["response"],
        intent=result["intent"],
        result=result["result"],
        needs_confirmation=result["needs_confirmation"],
        confirmation_message=result["confirmation_message"],
        duration_ms=result["duration_ms"],
    )

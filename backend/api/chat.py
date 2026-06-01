"""Chat API — natural language and slash command input."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from backend.core.assistant import assistant
from backend.core.schemas import UserInput

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"
    source: str = "text"  # text, voice, slash_command


class ChatResponse(BaseModel):
    response: str
    intent: dict | None = None
    result: dict | None = None
    needs_confirmation: bool = False
    confirmation_message: str = ""
    duration_ms: float = 0.0


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """Process a chat message through the full JARVIS pipeline."""
    user_input = UserInput(
        raw=request.message,
        source=request.source,  # type: ignore[arg-type]
        session_id=request.session_id,
    )
    result = assistant.process_input(user_input)
    return ChatResponse(
        response=result["response"],
        intent=result["intent"],
        result=result["result"],
        needs_confirmation=result["needs_confirmation"],
        confirmation_message=result["confirmation_message"],
        duration_ms=result["duration_ms"],
    )

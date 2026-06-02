"""Chat API — natural language and slash command input with conversation history."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from backend.chat_store import conversation_store
from backend.core.assistant import assistant
from backend.core.schemas import UserInput
from backend.core.logger import logger

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
    """Process a chat message through the full JARVIS pipeline with history."""
    conv_id = request.session_id if request.session_id != "default" else None

    # Save user message
    if conv_id:
        conversation_store.add_message(conv_id, "user", request.message)

    # Process through assistant
    user_input = UserInput(
        raw=request.message,
        source=request.source,  # type: ignore[arg-type]
        session_id=request.session_id,
    )
    result = assistant.process_input(user_input)

    response_text = result["response"]

    # Enhance chat with LLM context from history
    if conv_id and not request.message.startswith("/"):
        response_text = _chat_with_context(conv_id, request.message, response_text)

    # Save assistant response
    if conv_id and response_text:
        conversation_store.add_message(conv_id, "assistant", response_text)

    return ChatResponse(
        response=response_text,
        intent=result["intent"],
        result=result["result"],
        needs_confirmation=result["needs_confirmation"],
        confirmation_message=result["confirmation_message"],
        duration_ms=result["duration_ms"],
    )


def _chat_with_context(conv_id: str, user_message: str, fallback: str) -> str:
    """Send message to Ollama with conversation history for context-aware chat."""
    try:
        import requests

        history = conversation_store.get_context_messages(conv_id, max_messages=20)

        # Build messages array with system prompt + history
        messages = [
            {
                "role": "system",
                "content": (
                    "You are JARVIS, a helpful desktop assistant running on Windows. "
                    "Respond in the user's language. Be concise and helpful. "
                    "You can help with opening apps, searching the web, setting timers, "
                    "and answering questions about the user's PC."
                ),
            }
        ]
        messages.extend(history)

        r = requests.post(
            "http://localhost:11434/api/chat",
            json={
                "model": "qwen2.5:7b",
                "messages": messages,
                "stream": False,
            },
            timeout=30,
        )
        if r.status_code == 200:
            return r.json().get("message", {}).get("content", fallback)
    except Exception:
        pass

    return fallback

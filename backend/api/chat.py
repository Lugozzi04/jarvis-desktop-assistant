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
    is_slash = request.message.strip().startswith("/")

    # Save user message
    if conv_id:
        conversation_store.add_message(conv_id, "user", request.message)

    # Process through assistant (routes intent, executes skills, web search)
    user_input = UserInput(
        raw=request.message,
        source=request.source,
        session_id=request.session_id,
    )
    result = assistant.process_input(user_input)

    response_text = result["response"]

    # For non-slash chat messages in a conversation, use LLM with full history
    if conv_id and not is_slash:
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
    """Send message to Ollama with FULL context: history + web search + language.

    This is the ONLY place that calls Ollama for chat messages.
    It combines:
      - Conversation history (last 20 messages)
      - Web search results (real-time data)
      - Language preference (Italian or English)
    """
    try:
        import requests

        # ── 1. Load conversation history ──
        history = conversation_store.get_context_messages(conv_id, max_messages=20)

        # ── 2. Web search for real-time context ──
        web_context = ""
        try:
            from backend.skills.web_search.search_provider import search_web, format_results
            results = search_web(user_message, max_results=5)
            if results:
                web_context = format_results(user_message, results)
        except Exception as exc:
            logger.debug("Web search in chat context failed: {}", exc)

        # ── 3. Language preference ──
        lang = "it"
        try:
            from backend.api.settings import get_language
            lang = get_language()
        except Exception:
            pass

        # ── 4. Build system prompt ──
        if lang == "it":
            system_content = (
                "Sei JARVIS, un assistente desktop italiano. Rispondi SEMPRE in italiano, "
                "in modo conciso e utile. Hai accesso allo storico della conversazione: "
                "usa il contesto dei messaggi precedenti per rispondere in modo coerente. "
                "Se ti vengono forniti risultati di ricerca web, usali per dare risposte "
                "accurate e aggiornate. Cita le fonti quando usi dati dal web."
            )
        else:
            system_content = (
                "You are JARVIS, a helpful desktop assistant. Respond concisely in English. "
                "You have access to the full conversation history — use previous messages "
                "as context for coherent, contextual responses. "
                "If web search results are provided, use them for accurate, up-to-date answers. "
                "Always cite sources when using web data."
            )

        # ── 5. Build user prompt with web context ──
        user_content = user_message
        if web_context:
            user_content = (
                f"Web search results for context:\n{web_context}\n\n"
                f"User question: {user_message}"
            )

        # ── 6. Assemble messages array ──
        messages = [{"role": "system", "content": system_content}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_content})

        logger.info(
            "Chat context: {} history msgs, web={} chars, lang={}",
            len(history), len(web_context), lang,
        )

        # ── 7. Single Ollama call ──
        r = requests.post(
            "http://localhost:11434/api/chat",
            json={
                "model": "qwen2.5:7b",
                "messages": messages,
                "stream": False,
            },
            timeout=45,
        )
        if r.status_code == 200:
            return r.json().get("message", {}).get("content", fallback)

    except Exception as exc:
        logger.warning("Chat context LLM call failed: {}", exc)

    return fallback

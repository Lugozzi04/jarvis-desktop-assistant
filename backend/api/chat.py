"""Chat API — natural language and slash command input with conversation history.

Uses Ollama's native TOOL CALLING for web search.
The model decides when to search — no forced external API calls.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel

from backend.chat_store import conversation_store
from backend.core.assistant import assistant
from backend.core.config import settings
from backend.core.schemas import UserInput
from backend.core.logger import logger

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"
    source: str = "text"


class ChatResponse(BaseModel):
    response: str
    intent: dict | None = None
    result: dict | None = None
    needs_confirmation: bool = False
    confirmation_message: str = ""
    duration_ms: float = 0.0


# ── Tools that Ollama can call ──

OLLAMA_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Cerca informazioni aggiornate sul web. Usa questo strumento quando "
                "hai bisogno di dati in tempo reale (prezzi, meteo, notizie, fatti recenti). "
                "NON usarlo per domande di cultura generale che già conosci."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "La query di ricerca (in italiano o inglese)",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Ottieni data e ora corrente.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


def _execute_tool(name: str, args: dict) -> str:
    """Execute a tool and return the result as a string."""
    if name == "web_search":
        query = args.get("query", "")
        if not query:
            return "Nessuna query fornita."
        try:
            from backend.skills.web_search.search_provider import search_web, format_results
            results = search_web(query, max_results=5)
            return format_results(query, results)
        except Exception as exc:
            logger.warning("Tool web_search failed: {}", exc)
            return f"Ricerca fallita: {exc}"

    elif name == "get_current_time":
        now = datetime.now(timezone.utc)
        it_now = now.strftime("%d/%m/%Y %H:%M:%S")
        return f"Data e ora correnti: {it_now} (UTC)"

    return f"Tool sconosciuto: {name}"


def _build_system_prompt(lang: str) -> str:
    """Build the system prompt with language and tool instructions."""
    if lang == "it":
        return (
            "Sei JARVIS, un assistente virtuale italiano che vive in un desktop Windows. "
            "PARLI ESCLUSIVAMENTE IN ITALIANO. Non usare mai altre lingue.\n\n"
            "HAI ACCESSO A QUESTI STRUMENTI:\n"
            "- web_search: cerca informazioni aggiornate su internet. Usalo per "
            "prezzi, meteo, notizie, eventi recenti. NON serve per domande di cultura generale.\n"
            "- get_current_time: ottieni data e ora attuale.\n\n"
            "REGOLE IMPORTANTI:\n"
            "- Usa gli strumenti SOLO quando necessario.\n"
            "- Per domande sulla conversazione in corso, usa lo storico.\n"
            "- Rispondi in modo conciso (3-5 frasi).\n"
            "- Se usi risultati di ricerca, cita le fonti (URL)."
        )
    else:
        return (
            "You are JARVIS, a helpful desktop assistant. "
            "Respond concisely in English.\n\n"
            "TOOLS AVAILABLE:\n"
            "- web_search: search the web for real-time info.\n"
            "- get_current_time: get current date and time.\n\n"
            "RULES:\n"
            "- Use tools ONLY when needed.\n"
            "- Use conversation history for context.\n"
            "- Cite sources when using web data."
        )


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """Process a chat message through the full JARVIS pipeline with history."""
    conv_id = request.session_id if request.session_id != "default" else None
    is_slash = request.message.strip().startswith("/")

    if conv_id:
        conversation_store.add_message(conv_id, "user", request.message)

    user_input = UserInput(
        raw=request.message,
        source=request.source,
        session_id=request.session_id,
    )
    result = assistant.process_input(user_input)
    response_text = result["response"]

    # For non-slash messages in a conversation, use LLM with tool calling
    if conv_id and not is_slash:
        response_text = _chat_with_tools(conv_id, request.message, response_text)

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


def _chat_with_tools(conv_id: str, user_message: str, fallback: str) -> str:
    """Single Ollama call with native TOOL CALLING.

    The model decides whether to use tools (web_search, get_current_time).
    If it requests a tool, we execute it and send results back.
    Max 3 tool-calling rounds to prevent loops.
    """
    try:
        import requests

        # ── 1. Language ──
        lang = "it"
        try:
            from backend.api.settings import get_language
            lang = get_language()
        except Exception:
            pass

        # ── 2. Conversation history ──
        history = conversation_store.get_context_messages(conv_id, max_messages=20)

        # ── 3. Build messages ──
        system_content = _build_system_prompt(lang)
        messages = [{"role": "system", "content": system_content}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        # ── 4. Ollama model ──
        model = getattr(settings.llm, 'chat_model', 'qwen2.5:7b') or 'qwen2.5:7b'
        ollama_url = (settings.llm.base_url or "http://localhost:11434").rstrip("/")

        logger.info("Chat with tools: model={}, history={} msgs, lang={}", model, len(history), lang)

        # ── 5. Tool-calling loop (max 3 rounds) ──
        for round_num in range(3):
            payload = {
                "model": model,
                "messages": messages,
                "stream": False,
                "tools": OLLAMA_TOOLS,
                "options": {"temperature": 0.5},
            }

            r = requests.post(f"{ollama_url}/api/chat", json=payload, timeout=60)
            if r.status_code != 200:
                logger.warning("Ollama returned {}", r.status_code)
                break

            data = r.json()
            msg = data.get("message", {})
            content = msg.get("content", "")
            tool_calls = msg.get("tool_calls", [])

            # No tool calls → model gave final answer
            if not tool_calls:
                if content and len(content.strip()) > 5:
                    return content
                break

            # Model wants to use tools
            logger.info("Tool call round {}: {} tools requested", round_num + 1, len(tool_calls))

            # Add assistant message with tool calls
            messages.append({
                "role": "assistant",
                "content": content or "",
                "tool_calls": tool_calls,
            })

            # Execute each tool and add results
            for tc in tool_calls:
                fn = tc.get("function", {})
                tool_name = fn.get("name", "")
                tool_args = fn.get("arguments", {})

                # Parse args if string
                if isinstance(tool_args, str):
                    try:
                        tool_args = json.loads(tool_args)
                    except json.JSONDecodeError:
                        tool_args = {}

                logger.info("Executing tool: {} args={}", tool_name, tool_args)
                tool_result = _execute_tool(tool_name, tool_args)

                messages.append({
                    "role": "tool",
                    "content": tool_result,
                })

        # ── 6. If we exhausted rounds, make a final call without tools ──
        try:
            r = requests.post(
                f"{ollama_url}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": False,
                    "options": {"temperature": 0.5},
                },
                timeout=60,
            )
            if r.status_code == 200:
                final = r.json().get("message", {}).get("content", "")
                if final.strip():
                    return final
        except Exception:
            pass

    except Exception as exc:
        logger.warning("Chat with tools failed: {}", exc)

    return fallback

"""ChatSkill — general-purpose conversational AI with tool calling.

Uses Ollama's native TOOL CALLING for web search.
The model decides when to search — no forced external API calls.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from backend.core.config import settings
from backend.core.logger import logger
from backend.core.schemas import ActionResult
from backend.skills.base import BaseSkill

# Same tools as chat.py
_OLLAMA_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for real-time information. Use for prices, weather, news, recent events.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query"}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Get current date and time.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


class ChatSkill(BaseSkill):
    """General-purpose chatbot skill with tool calling."""

    def execute(self, action: str, parameters: dict[str, Any]) -> ActionResult:
        question = parameters.get("question", parameters.get("text", ""))

        if action == "answer_question":
            return self._answer(question)
        elif action == "explain_concept":
            return self._explain(question)
        elif action == "summarize_text":
            return self._summarize(question)
        else:
            return self._result(action, success=False, error=f"Unknown action: {action}")

    def _answer(self, question: str) -> ActionResult:
        if not question:
            return self._result("answer_question", success=False, error="No question provided")

        response = _try_llm_with_tools(question)
        return self._result("answer_question", success=True, result=response)

    def _explain(self, question: str) -> ActionResult:
        if not question:
            return self._result("explain_concept", success=False, error="No question provided")

        prompt = f"Spiega il seguente concetto in italiano, in modo semplice e chiaro. Sii educativo ma conciso.\n\nConcetto: {question}"
        response = _try_llm_with_tools(prompt)
        return self._result("explain_concept", success=True, result=response)

    def _summarize(self, text: str) -> ActionResult:
        if not text:
            return self._result("summarize_text", success=False, error="No text provided")

        prompt = f"Riassumi il seguente testo in italiano, in 3-5 punti elenco. Sii conciso.\n\n{text}"
        response = _try_llm_with_tools(prompt)
        return self._result("summarize_text", success=True, result=response)


def _execute_tool(name: str, args: dict) -> str:
    """Execute a tool and return result."""
    if name == "web_search":
        query = args.get("query", "")
        if not query:
            return "No query provided."
        try:
            from backend.skills.web_search.search_provider import search_web, format_results
            results = search_web(query, max_results=5)
            return format_results(query, results)
        except Exception as exc:
            return f"Search failed: {exc}"
    elif name == "get_current_time":
        now = datetime.now(timezone.utc)
        return f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S')} UTC"
    return f"Unknown tool: {name}"


def _try_llm_with_tools(user_message: str) -> str:
    """Use Ollama with native tool calling. Model decides when to search."""
    import requests

    model = getattr(settings.llm, 'chat_model', 'qwen2.5:7b') or 'qwen2.5:7b'
    ollama_url = (settings.llm.base_url or "http://localhost:11434").rstrip("/")

    system_prompt = (
        "Sei JARVIS, un assistente italiano. "
        "Rispondi ESCLUSIVAMENTE in italiano. "
        "Hai accesso a web_search (per dati aggiornati) e get_current_time. "
        "Usa gli strumenti solo quando necessario. Sii conciso."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    try:
        for round_num in range(3):
            r = requests.post(
                f"{ollama_url}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": False,
                    "tools": _OLLAMA_TOOLS,
                    "options": {"temperature": 0.5},
                },
                timeout=45,
            )
            if r.status_code != 200:
                break

            data = r.json()
            msg = data.get("message", {})
            content = msg.get("content", "")
            tool_calls = msg.get("tool_calls", [])

            if not tool_calls:
                if content and len(content.strip()) > 5:
                    return content
                break

            messages.append({
                "role": "assistant",
                "content": content or "",
                "tool_calls": tool_calls,
            })

            for tc in tool_calls:
                fn = tc.get("function", {})
                tool_name = fn.get("name", "")
                tool_args = fn.get("arguments", {})
                if isinstance(tool_args, str):
                    try:
                        tool_args = json.loads(tool_args)
                    except json.JSONDecodeError:
                        tool_args = {}
                tool_result = _execute_tool(tool_name, tool_args)
                messages.append({"role": "tool", "content": tool_result})

        # Final call without tools
        r = requests.post(
            f"{ollama_url}/api/chat",
            json={
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {"temperature": 0.5},
            },
            timeout=45,
        )
        if r.status_code == 200:
            return r.json().get("message", {}).get("content", "")

    except Exception as exc:
        logger.warning("LLM with tools failed: {}", exc)

    return _fallback_response()


def _fallback_response() -> str:
    """Fallback when no LLM is available."""
    if not settings.llm.default_provider:
        return (
            "Sono in modalità offline — nessun LLM configurato. "
            "Installa Ollama e un modello per abilitare la chat intelligente.\n\n"
            "Prova i comandi slash:\n"
            "• /open <app> — Apri un'applicazione\n"
            "• /search <query> — Cerca sul web\n"
            "• /timer <durata> <messaggio> — Imposta un timer\n"
            "• /system stats — Statistiche di sistema"
        )
    return (
        f"Il provider LLM '{settings.llm.default_provider}' non è disponibile. "
        "Assicurati che Ollama sia in esecuzione."
    )

"""ChatSkill — general-purpose conversational AI.

Answers questions, explains concepts, summarizes text, and engages
in conversation. Uses the LLM Gateway when available.
"""

from __future__ import annotations

from typing import Any

from backend.core.config import settings
from backend.core.logger import logger
from backend.core.schemas import ActionResult
from backend.skills.base import BaseSkill


class ChatSkill(BaseSkill):
    """General-purpose chatbot skill."""

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

        response = _try_llm([
            {"role": "system", "content": "You are JARVIS, a helpful desktop assistant. Be concise and practical. Respond in the same language the user used."},
            {"role": "user", "content": question},
        ])
        return self._result("answer_question", success=True, result=response)

    def _explain(self, question: str) -> ActionResult:
        if not question:
            return self._result("explain_concept", success=False, error="No question provided")

        prompt = f"Explain the following concept in simple, clear terms. Be educational but concise.\n\nConcept: {question}"
        response = _try_llm([
            {"role": "system", "content": "You are a patient teacher. Explain concepts clearly in 2-3 paragraphs."},
            {"role": "user", "content": prompt},
        ])
        return self._result("explain_concept", success=True, result=response)

    def _summarize(self, text: str) -> ActionResult:
        if not text:
            return self._result("summarize_text", success=False, error="No text provided")

        response = _try_llm([
            {"role": "system", "content": "Summarize the following text in 3-5 bullet points. Be concise."},
            {"role": "user", "content": text},
        ])
        return self._result("summarize_text", success=True, result=response)


def _try_llm(messages: list[dict[str, str]]) -> str:
    """Try to use the LLM Gateway, fall back gracefully."""
    try:
        from backend.llm.gateway import llm_gateway
    except ImportError:
        return _fallback_response()

    import asyncio

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Running in async context — need a different approach
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, llm_gateway.generate(messages))
                return future.result(timeout=30)
        else:
            return asyncio.run(llm_gateway.generate(messages))
    except Exception as exc:
        logger.warning("LLM Gateway failed: {}", exc)
        return _fallback_response()


def _fallback_response() -> str:
    """Fallback when no LLM is available."""
    if not settings.llm.default_provider:
        return (
            "I'm in offline mode — no LLM configured. "
            "Set up Ollama or another provider in .env to enable smart chat.\n\n"
            "In the meantime, try slash commands:\n"
            "• /open <app> — Open an application\n"
            "• /search <query> — Search the web\n"
            "• /timer <duration> <message> — Set a timer\n"
            "• /system stats — Show system stats\n"
            "• /ask <question> — Ask a question"
        )
    return (
        f"LLM provider '{settings.llm.default_provider}' is configured but not available. "
        "Make sure the service is running.\n\n"
        "Try slash commands: /open, /search, /timer, /system stats"
    )

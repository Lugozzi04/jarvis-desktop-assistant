"""ChatSkill — general-purpose conversational AI.

Answers questions, explains concepts, summarizes text, and engages
in conversation. Uses the LLM Gateway when available.
"""

from __future__ import annotations

from typing import Any

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

        return self._result(
            "answer_question",
            success=True,
            result=f"💬 Chat mode active. Question received: \"{question[:100]}...\" "
                   f"(LLM Gateway coming in M5 — using offline mode for now)\n\n"
                   "Try slash commands: /search, /open, /timer, /system stats",
        )

    def _explain(self, question: str) -> ActionResult:
        return self._result(
            "explain_concept",
            success=True,
            result=f"📚 I'd explain \"{question[:80]}\" in detail once the LLM Gateway is connected. "
                   "Set up Ollama in .env to enable this feature.",
        )

    def _summarize(self, text: str) -> ActionResult:
        if not text:
            return self._result("summarize_text", success=False, error="No text provided")
        return self._result(
            "summarize_text",
            success=True,
            result=f"📝 Text received ({len(text)} chars). Summarization requires LLM Gateway (M5).",
        )

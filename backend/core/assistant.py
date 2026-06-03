"""Jarvis Assistant Orchestrator — the central brain.

This module ties together the entire execution pipeline:
  1. Receive user input (text, voice, slash command, trigger)
  2. Route to intent (IntentRouter)
  3. Check permissions (PermissionGuard)
  4. Execute skill (SkillRegistry)
  5. Log result (Logger)
  6. Format response

The orchestrator is a thin coordinator — it delegates everything
to modules, keeping the core small and stable.
"""

from __future__ import annotations

import time
from typing import Any

from backend.core.config import settings
from backend.core.errors import JarvisError
from backend.core.logger import audit_log, logger
from backend.core.permissions import permission_guard
from backend.core.registry import skill_registry
from backend.core.router import intent_router
from backend.core.schemas import (
    ActionResult,
    Intent,
    IntentKind,
    LogEntry,
    UserInput,
)


class AssistantOrchestrator:
    """Central orchestrator for the JARVIS desktop assistant."""

    def __init__(self) -> None:
        self._initialized = False
        logger.info("AssistantOrchestrator created")

    def initialize(self) -> None:
        """Initialize all subsystems."""
        if self._initialized:
            return

        logger.info("Initializing JARVIS subsystems...")

        # Initialize database
        from backend.db.database import init_db
        init_db(settings.database_url)
        logger.info("Database initialized — {}", settings.database_url)

        # Load skills
        skill_registry.discover_and_load()
        logger.info("Skills loaded: {}", skill_registry.skill_names)

        self._initialized = True
        logger.info("✅ JARVIS is ready")

    # ── Public API ──

    def process_input(self, user_input: UserInput) -> dict[str, Any]:
        """Process user input through the full pipeline.

        Args:
            user_input: Normalized UserInput object

        Returns:
            Dict with intent, action_result, response, and timing
        """
        t0 = time.monotonic()

        if not self._initialized:
            self.initialize()

        logger.info("Processing: [{}] {}", user_input.source, user_input.raw[:100])

        # ── Step 1: Route intent ──
        intent = intent_router.route(user_input.raw)

        # ── Step 2: Handle based on intent kind ──
        result: ActionResult | None = None
        response_text = ""
        needs_confirmation = False
        confirmation_message = ""

        if intent.kind == IntentKind.skill and intent.skill and intent.action:
            result, needs_confirmation, confirmation_message = self._execute_skill(
                intent.skill, intent.action, intent.parameters
            )
            if result and not needs_confirmation:
                response_text = self._format_result(result)
            elif needs_confirmation:
                response_text = confirmation_message

        elif intent.kind == IntentKind.workflow:
            response_text = self._execute_workflow(intent.workflow_name or "")

        elif intent.kind == IntentKind.chat:
            response_text = self._handle_chat(intent.parameters.get("question", ""))

        else:
            response_text = (
                "I'm not sure how to help with that. "
                "Try a slash command like /open, /search, /ask, /timer, or /workflow."
            )

        # ── Step 3: Log ──
        elapsed_ms = (time.monotonic() - t0) * 1000
        self._log_action(intent, result, elapsed_ms)

        return {
            "intent": {
                "kind": intent.kind.value,
                "skill": intent.skill,
                "action": intent.action,
                "confidence": intent.confidence,
            },
            "result": result.model_dump() if result else None,
            "response": response_text,
            "needs_confirmation": needs_confirmation,
            "confirmation_message": confirmation_message if needs_confirmation else "",
            "duration_ms": round(elapsed_ms, 1),
        }

    # ── Private: Skill Execution ──

    def _execute_skill(
        self,
        skill_name: str,
        action: str,
        parameters: dict[str, Any],
    ) -> tuple[ActionResult | None, bool, str]:
        """Execute a skill with permission checks."""
        # Check risk level
        try:
            risk = skill_registry.get_risk(skill_name, action)
        except JarvisError:
            risk = None

        # Permission check
        if risk:
            perm = permission_guard.check(risk, f"{skill_name}.{action}")
            if perm["needs_confirmation"]:
                if risk.value == "dangerous":
                    # Queue as pending action instead of blocking
                    from backend.core.pending_actions import pending_queue
                    reason = f"Action {skill_name}.{action} requires approval (risk: {risk.value})"
                    pending_queue.add(
                        skill=skill_name,
                        action=action,
                        parameters=parameters,
                        risk=risk.value,
                        reason=reason,
                        source="user",
                    )
                    logger.info("Dangerous action queued: {}.{} requires approval", skill_name, action)
                    from backend.core.schemas import ActionResult
                    return ActionResult(
                        success=False,
                        skill=skill_name,
                        action=action,
                        risk=risk.value,
                        result="⏳ This action requires approval. Check Pending Actions in the dashboard.",
                    ), False, ""
                else:
                    logger.info("Confirmation required for {}.{}", skill_name, action)
                    return None, True, perm["confirmation_message"]

        # Execute
        result = skill_registry.execute(skill_name, action, parameters)
        return result, False, ""

    def _execute_workflow(self, name: str) -> str:
        """Execute a named workflow using the Workflow Engine."""
        try:
            from backend.workflows.engine import workflow_engine
            result = workflow_engine.run(name)
            if result.get("status") == "error":
                return f"❌ {result.get('error', 'Workflow failed')}"

            status = result.get("status", "unknown")
            total_steps = len(result.get("steps", []))
            successful = sum(1 for s in result.get("steps", []) if s.get("status") == "success")
            failed = sum(1 for s in result.get("steps", []) if s.get("status") in ("failed", "skipped"))

            lines = [f"🔄 Workflow '{result.get('workflow_name', name)}' — {status.upper()} ({successful}/{total_steps} ok)"]
            for step in result.get("steps", []):
                icon = {"success": "✅", "failed": "❌", "skipped": "⏭️"}.get(step.get("status"), "❓")
                lines.append(f"  {icon} Step {step.get('order')}: {step.get('skill')}.{step.get('action')}")
                if step.get("error"):
                    lines.append(f"     ↳ {step['error']}")

            return "\n".join(lines)
        except Exception as exc:
            return f"❌ Workflow engine error: {exc}"

    def _handle_chat(self, question: str) -> str:
        """Handle a general chat question. Uses sync Ollama call first (no async issues on Windows)."""
        if not question:
            return "How can I help you?"

        # Detect if question needs real-time data (exchange rates, weather, etc.)
        web_context = self._try_web_search(question)

        # Build system prompt with web context if available
        system_prompt = (
            "You are JARVIS, a helpful desktop assistant. Respond concisely in the user's language. "
            "If web search results are provided below, use them to give accurate, up-to-date answers. "
            "Always cite sources when using web data."
        )
        user_prompt = question
        if web_context:
            user_prompt = f"Web search results for context:\n{web_context}\n\nUser question: {question}"

        # Direct sync call to Ollama (bypasses async event loop issues)
        try:
            import requests
            r = requests.post(
                "http://localhost:11434/api/chat",
                json={
                    "model": "qwen2.5:7b",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "stream": False,
                },
                timeout=30,
            )
            if r.status_code == 200:
                return r.json().get("message", {}).get("content", "")
        except Exception:
            pass

        # If web search gave results but Ollama is down, return web results directly
        if web_context:
            return f"🌐 Web search results:\n\n{web_context}\n\n_Install Ollama (ollama pull qwen2.5:7b) for AI-powered answers._"

        # Try ChatSkill via registry
        try:
            result = skill_registry.execute("chat", "answer_question", {"question": question})
            if result and result.success:
                return result.result or "I processed your request."
        except Exception:
            pass

        # Ultimate fallback
        return (
            "I'm in offline mode — no LLM provider is available. "
            "For smart chat, install Ollama and run: ollama pull qwen2.5:7b\n\n"
            "In the meantime, use slash commands:\n"
            "• /open notepad — Open Notepad\n"
            "• /search query — Search the web\n"
            "• /timer 5m test — Set a 5-minute timer\n"
            "• /system stats — Show system stats\n"
            "• /ask question — Ask a question via LLM"
        )

    def _try_web_search(self, question: str) -> str:
        """Try to get real-time web search results for the question.
        
        Returns formatted search results string, or empty string if not applicable/failed.
        Uses Google + SearXNG — NO DuckDuckGo.
        """
        from backend.core.logger import logger
        from backend.skills.web_search.search_provider import search_web, format_results
        
        # Always attempt a web search for chat questions — Ollama has no web access.
        # Skip only for clearly offline/local questions.
        skip_patterns = [
            "how are you", "what is your name", "who are you",
            "what can you do", "help", "hello", "hi ", "hey ",
        ]
        question_lower = question.lower().strip()
        if any(question_lower.startswith(p) for p in skip_patterns) and len(question_lower) < 30:
            return ""
        
        try:
            logger.info("Web search for: {}", question[:80])
            results = search_web(question, max_results=5)
            if results:
                return format_results(question, results)
        except Exception as exc:
            logger.debug("Web search unavailable: {}", exc)
        
        return ""

    def _format_result(self, result: ActionResult) -> str:
        """Format an ActionResult into a user-friendly message."""
        if result.success:
            if result.result:
                return f"✅ {result.result}"
            return f"✅ Done — {result.skill}.{result.action}"
        else:
            return f"❌ {result.error or 'Action failed'}"

    def _log_action(
        self,
        intent: Intent,
        result: ActionResult | None,
        elapsed_ms: float,
    ) -> None:
        """Write structured audit log."""
        audit_log(
            action=intent.action or "unknown",
            skill=intent.skill,
            parameters=intent.parameters,
            risk=result.risk.value if result else "safe",
            result="success" if (result and result.success) else "failure",
            duration_ms=elapsed_ms,
        )


# Singleton
assistant = AssistantOrchestrator()

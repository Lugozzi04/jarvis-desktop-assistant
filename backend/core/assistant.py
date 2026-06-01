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
                logger.info("Confirmation required for {}.{}", skill_name, action)
                return None, True, perm["confirmation_message"]

        # Execute
        result = skill_registry.execute(skill_name, action, parameters)
        return result, False, ""

    def _execute_workflow(self, name: str) -> str:
        """Execute a named workflow (placeholder — M7)."""
        return f"⚠️ Workflow '{name}' not yet implemented (coming in M7)"

    def _handle_chat(self, question: str) -> str:
        """Handle a general chat question (placeholder — M5 LLM Gateway)."""
        # For now, return a helpful fallback
        if not question:
            return "How can I help you?"

        # Check if LLM is configured
        if not settings.llm.default_provider:
            return (
                "I'm in offline mode — no LLM configured. "
                "Set up Ollama or another provider in .env to enable smart chat.\n\n"
                "In the meantime, try slash commands:\n"
                "• /open <app> — Open an application\n"
                "• /search <query> — Search the web\n"
                "• /timer <duration> <message> — Set a timer\n"
                "• /system stats — Show system stats"
            )

        return (
            "💬 Chat mode — LLM Gateway coming in M5. "
            "For now, use slash commands for actions."
        )

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

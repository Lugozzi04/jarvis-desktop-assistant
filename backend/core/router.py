"""Intent Router — deterministic slash command parser + natural language routing.

Slash commands are parsed WITHOUT an LLM (deterministic, fast).
Natural language can optionally be routed through a small LLM classifier.

Architecture:
  1. Check for slash commands → deterministic parse
  2. Check for common patterns → rule-based routing
  3. (Optional) LLM-based classification for complex intents
"""

from __future__ import annotations

import re
from typing import Any

from backend.core.logger import logger
from backend.core.schemas import Intent, IntentKind
from backend.core.registry import skill_registry

# ── Slash Command Patterns ──

SLASH_PATTERNS: list[tuple[re.Pattern, str, str, dict[str, Any] | None]] = [
    # /open <app|folder|url> <target>
    (
        re.compile(r"^/open\s+app\s+(.+)", re.IGNORECASE),
        "apps", "open",
        lambda m: {"app_name": m.group(1).strip()},
    ),
    (
        re.compile(r"^/open\s+folder\s+(.+)", re.IGNORECASE),
        "files", "open_folder",
        lambda m: {"path": m.group(1).strip()},
    ),
    (
        re.compile(r"^/open\s+url\s+(.+)", re.IGNORECASE),
        "browser", "open_url",
        lambda m: {"url": m.group(1).strip()},
    ),
    (
        re.compile(r"^/open\s+(.+)", re.IGNORECASE),
        "apps", "open",
        lambda m: {"app_name": m.group(1).strip()},
    ),

    # /search <query>
    (
        re.compile(r"^/search\s+(.+)", re.IGNORECASE),
        "web_search", "search_and_summarize",
        lambda m: {"query": m.group(1).strip()},
    ),

    # /ask <question>
    (
        re.compile(r"^/ask\s+(.+)", re.IGNORECASE),
        "chat", "answer_question",
        lambda m: {"question": m.group(1).strip()},
    ),

    # /timer <duration> <message>
    (
        re.compile(r"^/timer\s+(\S+)\s+(.+)", re.IGNORECASE),
        "timers", "create_timer",
        lambda m: {"duration": m.group(1).strip(), "message": m.group(2).strip()},
    ),

    # /remind <time> <message>
    (
        re.compile(r"^/remind\s+(\S+)\s+(.+)", re.IGNORECASE),
        "timers", "create_reminder",
        lambda m: {"when": m.group(1).strip(), "message": m.group(2).strip()},
    ),

    # /workflow <name>
    (
        re.compile(r"^/workflow\s+(.+)", re.IGNORECASE),
        "workflows", "run_workflow",
        lambda m: {"workflow_name": m.group(1).strip()},
    ),

    # /system <action>
    (
        re.compile(r"^/system\s+(.+)", re.IGNORECASE),
        "system", "run_action",
        lambda m: {"action": m.group(1).strip()},
    ),

    # /file <action> <path>
    (
        re.compile(r"^/file\s+search\s+(.+)", re.IGNORECASE),
        "files", "search_file",
        lambda m: {"query": m.group(1).strip()},
    ),
    (
        re.compile(r"^/file\s+open\s+(.+)", re.IGNORECASE),
        "files", "open_file",
        lambda m: {"path": m.group(1).strip()},
    ),

    # /dev <command>
    (
        re.compile(r"^/dev\s+(.+)", re.IGNORECASE),
        "dev", "run_command",
        lambda m: {"command": m.group(1).strip()},
    ),

    # /auto <list|create|disable> [name]
    (
        re.compile(r"^/auto\s+list", re.IGNORECASE),
        "automations", "list_automations",
        lambda m: {},
    ),
    (
        re.compile(r"^/auto\s+disable\s+(.+)", re.IGNORECASE),
        "automations", "disable_automation",
        lambda m: {"name": m.group(1).strip()},
    ),
]

# ── Rule-Based Pattern Routing ──

RULE_PATTERNS: list[tuple[re.Pattern, str, str]] = [
    (re.compile(r"\b(?:apri|open|launch|start|avvia)\s+(.+?)(?:\s+(?:app|application|programma))?$", re.IGNORECASE), "apps", "open"),
    (re.compile(r"\b(?:chiudi|close|kill|terminate)\s+(.+?)(?:\s+(?:app|application|programma))?$", re.IGNORECASE), "apps", "close"),
    (re.compile(r"\b(?:timer)\s+(?:di\s+)?(\d+)\s*(?:min(?:uti)?|m|sec(?:onds?)?|s)?\s*(.+)?", re.IGNORECASE), "timers", "create_timer"),
    (re.compile(r"\b(?:ricordami|remind)\s+(?:di\s+)?(.+)", re.IGNORECASE), "timers", "create_reminder"),
    (re.compile(r"\b(?:cerca|cercami|search|find)\s+(?:online\s+)?(.+)", re.IGNORECASE), "web_search", "search_and_summarize"),
    (re.compile(r"\b(?:spiega(?:mi)?|explain|cos[\'']?è|what\s+is)\s+(.+)", re.IGNORECASE), "chat", "explain_concept"),
    (re.compile(r"\b(?:modalità|mode)\s+(.+)", re.IGNORECASE), "workflows", "run_workflow"),
    (re.compile(r"\b(?:stat(?:us)?\s+(?:sistema|system|pc)|system\s+stats)\b", re.IGNORECASE), "system", "get_stats"),
]


class IntentRouter:
    """Routes user input to the appropriate skill/action.

    Pipeline:
      1. Slash commands → deterministic regex match
      2. Rule-based patterns → regex match on natural language
      3. LLM classification → (future) for complex intents
    """

    def route(self, text: str) -> Intent:
        """Route user input and return an Intent.

        Args:
            text: Raw user input

        Returns:
            Intent with kind, skill, action, parameters, and confidence
        """
        text = text.strip()
        if not text:
            return Intent(
                kind=IntentKind.unknown,
                confidence=0.0,
                raw_input=text,
            )

        logger.debug("Routing input: {}", text[:80])

        # ── Step 1: Slash commands ──
        if text.startswith("/"):
            result = self._parse_slash(text)
            if result:
                return result

        # ── Step 2: Rule-based patterns ──
        result = self._match_rules(text)
        if result:
            return result

        # ── Step 3: Fallback to chat ──
        logger.info("No specific pattern matched — routing to chat")
        return Intent(
            kind=IntentKind.chat,
            confidence=0.5,
            skill="chat",
            action="answer_question",
            parameters={"question": text},
            raw_input=text,
        )

    # ── Private ──

    def _parse_slash(self, text: str) -> Intent | None:
        """Try to parse text as a slash command."""
        for pattern, skill, action, extractor in SLASH_PATTERNS:
            if extractor is None:
                continue
            match = pattern.match(text)
            if match:
                try:
                    params = extractor(match)
                except Exception:
                    params = {}
                logger.info(
                    "Slash command matched: /{} → {}.{} params={}",
                    text.split()[0][1:] if text.split() else "?",
                    skill,
                    action,
                    params,
                )
                return Intent(
                    kind=IntentKind.skill,
                    confidence=0.99,
                    skill=skill,
                    action=action,
                    parameters=params,
                    raw_input=text,
                )
        return None

    def _match_rules(self, text: str) -> Intent | None:
        """Try to match natural-language patterns."""
        text_lower = text.lower()
        for pattern, skill, action in RULE_PATTERNS:
            match = pattern.search(text_lower)
            if match:
                params: dict[str, Any] = {}
                groups = match.groups()
                if groups:
                    # Use the first capture group as the primary parameter
                    param_names = {
                        ("apps", "open"): "app_name",
                        ("apps", "close"): "app_name",
                        ("timers", "create_timer"): "duration",
                        ("timers", "create_reminder"): "message",
                        ("web_search", "search_and_summarize"): "query",
                        ("chat", "explain_concept"): "question",
                        ("workflows", "run_workflow"): "workflow_name",
                    }
                    key = param_names.get((skill, action), "query")
                    params[key] = groups[0].strip()

                logger.info("Rule matched: {}.{} params={}", skill, action, params)
                return Intent(
                    kind=IntentKind.skill,
                    confidence=0.85,
                    skill=skill,
                    action=action,
                    parameters=params,
                    raw_input=text,
                )
        return None


# Singleton
intent_router = IntentRouter()

"""Intent Router — deterministic slash command parser + natural language routing.

Slash commands are parsed WITHOUT an LLM (deterministic, fast).
Natural language can optionally be routed through a small LLM classifier.
LLM routing is only attempted after rule-based routing fails.

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

    # /obs <action>
    (
        re.compile(r"^/obs\s+open", re.IGNORECASE),
        "obs", "open",
        lambda m: {},
    ),

    # /discord <action>
    (
        re.compile(r"^/discord\s+open", re.IGNORECASE),
        "discord", "open",
        lambda m: {},
    ),
    (
        re.compile(r"^/discord\s+web", re.IGNORECASE),
        "discord", "open_web",
        lambda m: {},
    ),

    # /spotify <action> <query>
    (
        re.compile(r"^/spotify\s+open", re.IGNORECASE),
        "spotify", "open",
        lambda m: {},
    ),
    (
        re.compile(r"^/spotify\s+search\s+(.+)", re.IGNORECASE),
        "spotify", "search",
        lambda m: {"query": m.group(1).strip()},
    ),

    # /github <action> <arg>
    (
        re.compile(r"^/github\s+status(?:\s+(.+))?", re.IGNORECASE),
        "github", "git_status",
        lambda m: {"path": m.group(1).strip() if m.group(1) else "."},
    ),
    (
        re.compile(r"^/github\s+open\s+(.+)", re.IGNORECASE),
        "github", "open_repo",
        lambda m: {"repo": m.group(1).strip()},
    ),
    (
        re.compile(r"^/github\s+clone\s+(.+)", re.IGNORECASE),
        "github", "clone_repo",
        lambda m: {"url": m.group(1).strip()},
    ),
    (
        re.compile(r"^/github\s+issues\s+(.+)", re.IGNORECASE),
        "github", "open_issues",
        lambda m: {"repo": m.group(1).strip()},
    ),

    # /docs list
    (
        re.compile(r"^/docs\s+list", re.IGNORECASE),
        "documents", "list_documents",
        lambda m: {},
    ),
    # /docs index <path>
    (
        re.compile(r"^/docs\s+index\s+(.+)", re.IGNORECASE),
        "documents", "index_file",
        lambda m: {"path": m.group(1).strip()},
    ),
    # /docs index-folder <path>
    (
        re.compile(r"^/docs\s+index-folder\s+(.+)", re.IGNORECASE),
        "documents", "index_folder",
        lambda m: {"folder_path": m.group(1).strip()},
    ),
    # /docs search <query>
    (
        re.compile(r"^/docs\s+search\s+(.+)", re.IGNORECASE),
        "documents", "search_documents",
        lambda m: {"query": m.group(1).strip()},
    ),
    # /docs ask <question>
    (
        re.compile(r"^/docs\s+ask\s+(.+)", re.IGNORECASE),
        "documents", "ask_documents",
        lambda m: {"question": m.group(1).strip()},
    ),
    # /docs clear
    (
        re.compile(r"^/docs\s+clear", re.IGNORECASE),
        "documents", "clear_index",
        lambda m: {},
    ),
]

# ── Rule-Based Pattern Routing ──

RULE_PATTERNS: list[tuple[re.Pattern, str, str]] = [
    (re.compile(r"\b(?:apri|open|launch|start|avvia)\s+(.+?)(?:\s+(?:app|application|programma))?$", re.IGNORECASE), "apps", "open"),
    (re.compile(r"\b(?:chiudi|close|kill|terminate)\s+(.+?)(?:\s+(?:app|application|programma))?$", re.IGNORECASE), "apps", "close"),
    (re.compile(r"\b(?:timer)\s+(?:di\s+)?(\d+)\s*(?:min(?:uti)?|m|sec(?:onds?)?|s)?\s*(.+)?", re.IGNORECASE), "timers", "create_timer"),
    (re.compile(r"\b(?:ricordami|remind)\s+(?:di\s+)?(.+)", re.IGNORECASE), "timers", "create_reminder"),
    (re.compile(r"\b(?:cerca|cercami|search|find)\s+(?:online\s+)?(.+)", re.IGNORECASE), "web_search", "search_and_summarize"),
    (re.compile(r"\b(?:spiega(?:mi)?|explain|cos[\'\"]?è|what\s+is)\s+(.+)", re.IGNORECASE), "chat", "explain_concept"),
    (re.compile(r"\b(?:modalità|mode)\s+(.+)", re.IGNORECASE), "workflows", "run_workflow"),
    (re.compile(r"\b(?:stat(?:us)?\s+(?:sistema|system|pc)|system\s+stats)\b", re.IGNORECASE), "system", "get_stats"),

    # ── Specialized skills ──
    (re.compile(r"\b(?:apri|open)\s+obs\b", re.IGNORECASE), "obs", "open"),
    (re.compile(r"\b(?:apri|open)\s+discord\b", re.IGNORECASE), "discord", "open"),
    (re.compile(r"\b(?:apri|open)\s+spotify\b", re.IGNORECASE), "spotify", "open"),
    (re.compile(r"\b(?:cerca|search|trova)\s+(?:su\s+)?spotify\s+(.+)", re.IGNORECASE), "spotify", "search"),
    (re.compile(r"\b(?:git\s+status|stato\s+git)\b", re.IGNORECASE), "github", "git_status"),
    (re.compile(r"\b(?:apri|open)\s+(?:repo|il\s+repo)\s+(.+)", re.IGNORECASE), "github", "open_repo"),
    (re.compile(r"\b(?:clona|clone)\s+(?:repo\s+)?(.+)", re.IGNORECASE), "github", "clone_repo"),

    # ── Document Memory ──
    (re.compile(r"\b(?:indicizza|index)\s+(?:questo\s+)?(?:file|il\s+file)\s+(.+)", re.IGNORECASE), "documents", "index_file"),
    (re.compile(r"\b(?:indicizza|index)\s+(?:questa\s+)?(?:cartella|la\s+cartella|folder)\s+(.+)", re.IGNORECASE), "documents", "index_folder"),
    (re.compile(r"\b(?:cerca|cercami|search|find)\s+(?:nei|nei miei|in)\s+(?:documenti|document|docs|appunti|notes)\s+(.+)", re.IGNORECASE), "documents", "search_documents"),
    (re.compile(r"\b(?:cosa|che\s+cosa|what|what do)\s+(?:dicono|dice|say|my)\s+(?:i\s+)?(?:miei\s+)?(?:documenti|document|docs|appunti|notes)\s+(?:su|about|riguardo\s+a)\s+(.+)", re.IGNORECASE), "documents", "ask_documents"),
    (re.compile(r"\b(?:chiedi|ask|domanda)\s+(?:ai|ai\s+miei)\s+(?:documenti|documents|appunti)\s+(.+)", re.IGNORECASE), "documents", "ask_documents"),
    (re.compile(r"\b(?:riassumi|summarize)\s+(?:i\s+)?(?:documenti|documents)\s+(?:su|about)\s+(.+)", re.IGNORECASE), "documents", "ask_documents"),
    (re.compile(r"\b(?:elenca|list|mostra|show)\s+(?:i\s+)?(?:miei\s+)?(?:documenti|documents|docs)", re.IGNORECASE), "documents", "list_documents"),
]


class IntentRouter:
    """Routes user input to the appropriate skill/action.

    Pipeline:
      1. Slash commands → deterministic regex match
      2. Rule-based patterns → regex match on natural language
      3. LLM classification → (only when available) for complex intents
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

        # ── Step 3: Try LLM routing (non-blocking, sync wrapper) ──
        llm_result = self._try_llm_route(text)
        if llm_result:
            return llm_result

        # ── Step 4: Fallback to chat ──
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
                    param_names = {
                        ("apps", "open"): "app_name",
                        ("apps", "close"): "app_name",
                        ("timers", "create_timer"): "duration",
                        ("timers", "create_reminder"): "message",
                        ("web_search", "search_and_summarize"): "query",
                        ("chat", "explain_concept"): "question",
                        ("workflows", "run_workflow"): "workflow_name",
                        ("documents", "index_file"): "path",
                        ("documents", "index_folder"): "folder_path",
                        ("documents", "search_documents"): "query",
                        ("documents", "ask_documents"): "question",
                        ("documents", "list_documents"): "query",
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

    def _try_llm_route(self, text: str) -> Intent | None:
        """Try LLM-based intent routing as a fallback.

        Only used when rule-based routing fails and LLM is available.
        Uses a sync wrapper around the async gateway call.
        """
        try:
            from backend.llm.gateway import llm_gateway
            import asyncio

            # Quick check: is there an available provider?
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        available = pool.submit(
                            asyncio.run, llm_gateway.is_available()
                        ).result(timeout=3)
                else:
                    available = asyncio.run(llm_gateway.is_available())
            except Exception:
                return None

            if not available:
                return None

            # Run LLM routing
            available_skills = skill_registry.skill_names
            try:
                if asyncio.get_event_loop().is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        result = pool.submit(
                            asyncio.run,
                            llm_gateway.route_intent(text, available_skills),
                        ).result(timeout=15)
                else:
                    result = asyncio.run(
                        llm_gateway.route_intent(text, available_skills)
                    )
            except Exception as exc:
                logger.warning("LLM routing failed: {}", exc)
                return None

            if result is None:
                return None

            kind = result.get("kind", "chat")
            confidence = float(result.get("confidence", 0.5))

            if kind == "clarification":
                return Intent(
                    kind=IntentKind.unknown,
                    confidence=confidence,
                    raw_input=text,
                    needs_clarification=True,
                    clarification_question=result.get("reply", "Can you clarify?"),
                )

            if kind == "skill":
                skill_name = result.get("skill", "")
                action_name = result.get("action", "")
                if skill_name and action_name:
                    params = result.get("parameters", {})
                    logger.info(
                        "LLM routed: {} → {}.{} confidence={}",
                        text[:60], skill_name, action_name, confidence,
                    )
                    return Intent(
                        kind=IntentKind.skill,
                        confidence=min(confidence, 0.8),  # Cap LLM confidence
                        skill=skill_name,
                        action=action_name,
                        parameters=params,
                        raw_input=text,
                    )

            # Default: chat
            return None

        except Exception as exc:
            logger.debug("LLM routing unavailable: {}", exc)
            return None


# Singleton
intent_router = IntentRouter()

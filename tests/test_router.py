"""Tests for the Intent Router — slash commands and natural language."""

import pytest
from backend.core.router import intent_router
from backend.core.schemas import IntentKind


class TestSlashCommands:
    def test_open_app(self):
        intent = intent_router.route("/open discord")
        assert intent.kind == IntentKind.skill
        assert intent.skill == "apps"
        assert intent.action == "open"
        assert intent.parameters["app_name"] == "discord"

    def test_open_url(self):
        intent = intent_router.route("/open url https://youtube.com")
        assert intent.kind == IntentKind.skill
        assert intent.skill == "browser"
        assert intent.action == "open_url"

    def test_search(self):
        intent = intent_router.route("/search best LLM 2026")
        assert intent.kind == IntentKind.skill
        assert intent.skill == "web_search"
        assert intent.action == "search_and_summarize"

    def test_timer(self):
        intent = intent_router.route("/timer 25m study session")
        assert intent.kind == IntentKind.skill
        assert intent.skill == "timers"
        assert intent.action == "create_timer"
        assert intent.parameters["duration"] == "25m"

    def test_system_stats(self):
        intent = intent_router.route("/system stats")
        assert intent.kind == IntentKind.skill
        assert intent.skill == "system"

    def test_workflow(self):
        intent = intent_router.route("/workflow live")
        assert intent.kind == IntentKind.skill
        assert intent.skill == "workflows"
        assert intent.action == "run_workflow"


class TestNaturalLanguage:
    def test_open_italian(self):
        intent = intent_router.route("apri Spotify")
        assert intent.skill == "apps"
        assert intent.action == "open"

    def test_explain(self):
        intent = intent_router.route("spiegami cos'è Docker")
        assert intent.skill == "chat"
        assert intent.action == "explain_concept"

    def test_search(self):
        intent = intent_router.route("cerca online migliori llm")
        assert intent.skill == "web_search"

    def test_fallback_chat(self):
        intent = intent_router.route("random nonsense text")
        assert intent.kind == IntentKind.chat

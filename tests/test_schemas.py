"""Tests for core Pydantic schemas."""

import pytest
from pydantic import ValidationError
from backend.core.schemas import (
    Intent,
    IntentKind,
    SkillAction,
    RiskLevel,
    ActionResult,
)


class TestSchemas:
    def test_intent_skill(self):
        intent = Intent(
            kind=IntentKind.skill,
            skill="apps",
            action="open",
            parameters={"app_name": "Discord"},
            raw_input="/open discord",
        )
        assert intent.skill == "apps"
        assert intent.action == "open"

    def test_skill_action(self):
        action = SkillAction(
            skill="apps",
            action="open",
            parameters={"app_name": "Discord"},
            risk=RiskLevel.safe,
        )
        assert action.type == "skill_action"
        assert action.risk == RiskLevel.safe

    def test_action_result_success(self):
        result = ActionResult(
            success=True,
            skill="apps",
            action="open",
            risk=RiskLevel.safe,
            result="Opened Discord",
        )
        assert result.success is True
        assert result.error is None

    def test_action_result_failure(self):
        result = ActionResult(
            success=False,
            skill="apps",
            action="open",
            risk=RiskLevel.safe,
            error="App not found",
        )
        assert result.success is False
        assert result.error == "App not found"

    def test_invalid_confidence(self):
        with pytest.raises(ValidationError):
            Intent(kind=IntentKind.skill, confidence=1.5)

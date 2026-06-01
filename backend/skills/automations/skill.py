"""AutomationSkill — trigger-based automations (coming in M8)."""
from backend.skills.base import BaseSkill
from backend.core.schemas import ActionResult
from typing import Any

class AutomationSkill(BaseSkill):
    def execute(self, action: str, parameters: dict[str, Any]) -> ActionResult:
        return self._result(action, success=False, error="AutomationSkill coming in M8")

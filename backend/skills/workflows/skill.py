"""WorkflowSkill — multi-step workflow execution (coming in M7)."""
from backend.skills.base import BaseSkill
from backend.core.schemas import ActionResult
from typing import Any

class WorkflowSkill(BaseSkill):
    def execute(self, action: str, parameters: dict[str, Any]) -> ActionResult:
        return self._result(action, success=False, error="WorkflowSkill coming in M7")

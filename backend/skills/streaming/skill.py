"""StreamingSkill — streaming mode setup (coming in M12)."""
from backend.skills.base import BaseSkill
from backend.core.schemas import ActionResult
from typing import Any

class StreamingSkill(BaseSkill):
    def execute(self, action: str, parameters: dict[str, Any]) -> ActionResult:
        return self._result(action, success=False, error="StreamingSkill coming in M12")

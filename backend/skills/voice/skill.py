"""VoiceSkill — speech-to-text and text-to-speech (coming in M9)."""
from backend.skills.base import BaseSkill
from backend.core.schemas import ActionResult
from typing import Any

class VoiceSkill(BaseSkill):
    def execute(self, action: str, parameters: dict[str, Any]) -> ActionResult:
        return self._result(action, success=False, error="VoiceSkill coming in M9")

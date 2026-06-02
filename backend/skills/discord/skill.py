from backend.skills.base import BaseSkill
from backend.core.schemas import ActionResult
from typing import Any

class DiscordSkill(BaseSkill):
    """Discord skill — open app or web."""
    def execute(self, action: str, parameters: dict[str, Any]) -> ActionResult:
        if action == "open":
            from backend.skills.apps.skill import AppSkill
            return AppSkill().execute("open", {"app_name": "Discord"})
        elif action == "open_web":
            from backend.skills.browser.skill import BrowserSkill
            return BrowserSkill().execute("open_url", {"url": "https://discord.com/app"})
        elif action == "open_server":
            url = parameters.get("url", "")
            if url:
                from backend.skills.browser.skill import BrowserSkill
                return BrowserSkill().execute("open_url", {"url": url})
            return self._result(action, False, error="Server URL required")
        return self._result(action, False, error=f"Unknown action: {action}")

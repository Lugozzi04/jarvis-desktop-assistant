from backend.skills.base import BaseSkill
from backend.core.schemas import ActionResult
from typing import Any
from urllib.parse import quote

class SpotifySkill(BaseSkill):
    """Spotify skill — open app or search."""
    def execute(self, action: str, parameters: dict[str, Any]) -> ActionResult:
        if action == "open":
            from backend.skills.apps.skill import AppSkill
            return AppSkill().execute("open", {"app_name": "Spotify"})
        elif action in ("search", "search_artist"):
            query = parameters.get("query", "")
            if not query:
                return self._result(action, False, error="Search query required")
            if action == "search_artist":
                url = f"https://open.spotify.com/search/{quote(query)}/artists"
            else:
                url = f"https://open.spotify.com/search/{quote(query)}"
            from backend.skills.browser.skill import BrowserSkill
            return BrowserSkill().execute("open_url", {"url": url})
        return self._result(action, False, error=f"Unknown action: {action}")

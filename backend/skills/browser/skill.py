"""BrowserSkill — open URLs and search the web in the default browser."""

from __future__ import annotations

import urllib.parse
import webbrowser
from typing import Any

from backend.core.schemas import ActionResult
from backend.skills.base import BaseSkill


class BrowserSkill(BaseSkill):
    """Open URLs and search the web."""

    def execute(self, action: str, parameters: dict[str, Any]) -> ActionResult:
        if action == "open_url":
            return self._open_url(parameters.get("url", ""))
        elif action == "search_web":
            return self._search_web(parameters.get("query", ""))
        else:
            return self._result(action, success=False, error=f"Unknown action: {action}")

    def _open_url(self, url: str) -> ActionResult:
        if not url:
            return self._result("open_url", success=False, error="No URL provided")

        # Add https:// if missing
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        try:
            webbrowser.open(url)
            return self._result("open_url", success=True, result=f"Opened {url}")
        except Exception as exc:
            return self._result("open_url", success=False, error=str(exc))

    def _search_web(self, query: str) -> ActionResult:
        if not query:
            return self._result("search_web", success=False, error="No search query provided")

        encoded = urllib.parse.quote_plus(query)
        url = f"https://www.google.com/search?q={encoded}"
        try:
            webbrowser.open(url)
            return self._result("search_web", success=True, result=f"Searched for: {query}")
        except Exception as exc:
            return self._result("search_web", success=False, error=str(exc))

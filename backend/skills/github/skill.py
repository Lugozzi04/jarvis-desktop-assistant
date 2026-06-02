from backend.skills.base import BaseSkill
from backend.core.schemas import ActionResult
from backend.core.logger import logger
from typing import Any
import subprocess, os

REPO_ALIASES = {
    "jarvis": "https://github.com/Lugozzi04/jarvis-desktop-assistant",
    "hermes": "https://github.com/nousresearch/hermes-agent",
}

class GitHubSkill(BaseSkill):
    """GitHub skill — repo operations and git commands."""
    def execute(self, action: str, parameters: dict[str, Any]) -> ActionResult:
        if action in ("open_repo", "open_issues"):
            repo = parameters.get("repo", "")
            if repo in REPO_ALIASES:
                repo = REPO_ALIASES[repo]
            if not repo:
                return self._result(action, False, error="Repo name or URL required")
            url = f"{repo}/issues" if action == "open_issues" else repo
            from backend.skills.browser.skill import BrowserSkill
            return BrowserSkill().execute("open_url", {"url": url})
        elif action == "git_status":
            path = parameters.get("path", os.getcwd())
            try:
                result = subprocess.run(["git", "-C", path, "status", "--short"], capture_output=True, text=True, timeout=10)
                output = result.stdout.strip() or "No changes"
                return self._result(action, True, result=f"Git status:\n{output}")
            except Exception as e:
                return self._result(action, False, error=str(e))
        elif action == "clone_repo":
            url = parameters.get("url", "")
            if not url:
                return self._result(action, False, error="Repo URL required")
            return self._result(action, True, result=f"Clone {url}: confirmation required. Run: git clone {url}")
        elif action in ("commit_all", "push"):
            return self._result(action, True, result=f"Git {action}: confirmation required. Use terminal or shell command.")
        return self._result(action, False, error=f"Unknown action: {action}")

"""AppSkill — launch and manage desktop applications.

Uses configurable aliases so the user can say:
  "open discord", "open vscode", "open obs"

Apps are configured via the settings UI or directly in the database.
On Linux, uses subprocess; on Windows, uses os.startfile.
"""

from __future__ import annotations

import os
import platform
import subprocess
import sys
from typing import Any

from backend.core.logger import logger
from backend.core.schemas import ActionResult
from backend.skills.base import BaseSkill


class AppSkill(BaseSkill):
    """Launch, close, and manage desktop applications."""

    # Built-in fallback apps (if no DB config)
    _DEFAULT_APPS: dict[str, dict[str, Any]] = {
        "discord": {"aliases": ["discord", "chat", "dc", "discordia"], "command": "discord"},
        "spotify": {"aliases": ["spotify", "music", "musica"], "command": "spotify"},
        "vscode": {"aliases": ["vscode", "code", "codice", "vs code", "visual studio"], "command": "code"},
        "obs": {"aliases": ["obs", "stream", "live", "streaming", "registrazione"], "command": "obs"},
        "terminal": {"aliases": ["terminal", "term", "shell", "cmd", "powershell", "prompt"], "command": "wt.exe"},
        "calculator": {"aliases": ["calculator", "calc", "calcolatrice"], "command": "calc.exe"},
        "files": {"aliases": ["files", "explorer", "file", "cartelle", "esplora file"], "command": "explorer.exe"},
        "browser": {"aliases": ["browser", "chrome", "firefox", "edge", "internet"], "command": "start https://google.com"},
        "settings": {"aliases": ["settings", "impostazioni", "config", "controllo"], "command": "start ms-settings:"},
        "notepad": {"aliases": ["notepad", "note", "blocco note", "editor", "appunti"], "command": "notepad.exe"},
    }

    def execute(self, action: str, parameters: dict[str, Any]) -> ActionResult:
        if action == "open":
            return self._open_app(parameters.get("app_name", ""))
        elif action == "close":
            return self._close_app(parameters.get("app_name", ""))
        elif action == "list":
            return self._list_apps()
        else:
            return self._result(action, success=False, error=f"Unknown action: {action}")

    def _open_app(self, app_name: str) -> ActionResult:
        if not app_name:
            return self._result("open", success=False, error="No app name provided")

        app_name_lower = app_name.lower().strip()

        # Resolve alias → app config
        app_config = self._resolve_app(app_name_lower)
        if app_config is None:
            available = ", ".join(self._DEFAULT_APPS.keys())
            return self._result(
                "open",
                success=False,
                error=f"Unknown app: '{app_name}'. Available: {available}",
            )

        command = app_config.get("command", app_name_lower)
        logger.info("Opening app: {} → {}", app_name, command)

        try:
            system = platform.system()
            if command.startswith("start "):
                # shell built-in — always use subprocess
                subprocess.Popen(command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif system == "Windows":
                # Try os.startfile first (handles .exe, .lnk, URLs), fall back to subprocess
                try:
                    os.startfile(command)
                except Exception:
                    subprocess.Popen(command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif system == "Darwin":
                subprocess.Popen(["open", "-a", command], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:  # Linux
                subprocess.Popen(
                    command.split() if " " in command else [command],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
            return self._result("open", success=True, result=f"Opened {app_name}")
        except FileNotFoundError:
            return self._result("open", success=False, error=f"App '{app_name}' not found (command: {command})")
        except Exception as exc:
            return self._result("open", success=False, error=str(exc))

    def _close_app(self, app_name: str) -> ActionResult:
        if not app_name:
            return self._result("close", success=False, error="No app name provided")

        app_name_lower = app_name.lower().strip()
        app_config = self._resolve_app(app_name_lower)
        command = app_config.get("command", app_name_lower) if app_config else app_name_lower

        try:
            system = platform.system()
            if system == "Windows":
                subprocess.run(["taskkill", "/IM", f"{command}.exe", "/F"], capture_output=True)
            else:
                subprocess.run(["pkill", "-f", command], capture_output=True)
            return self._result("close", success=True, result=f"Closed {app_name}")
        except Exception as exc:
            return self._result("close", success=False, error=str(exc))

    def _list_apps(self) -> ActionResult:
        apps = []
        for name, config in self._DEFAULT_APPS.items():
            apps.append(f"• {name} ({', '.join(config['aliases'][:3])})")
        return self._result("list", success=True, result="Configured apps:\n" + "\n".join(apps))

    def _resolve_app(self, name: str) -> dict[str, Any] | None:
        """Resolve an app name or alias to its config."""
        # Direct match
        if name in self._DEFAULT_APPS:
            return self._DEFAULT_APPS[name]

        # Alias match
        for app_name, config in self._DEFAULT_APPS.items():
            if name in config.get("aliases", []):
                return config

        return None

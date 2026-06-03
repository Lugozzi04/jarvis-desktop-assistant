"""AppSkill — launch and manage desktop applications.

Uses the AppConfigStore for user-configured apps (via Setup Wizard).
Falls back to built-in defaults when no config exists.
On Windows, launches via subprocess.Popen with full path when available,
or via 'start' for bare command names.
"""

from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path
from typing import Any

from backend.core.logger import logger
from backend.core.schemas import ActionResult
from backend.skills.base import BaseSkill


class AppSkill(BaseSkill):
    """Launch, close, and manage desktop applications."""

    # Built-in fallback apps (used only if config store is empty)
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

        # ── Security: sanitize input ──
        app_name = app_name.strip()
        dangerous_chars = ["../", "..\\", "|", ";", "&&", "||", "`", "$(", ">", "<", "\n", "\r"]
        for char in dangerous_chars:
            if char in app_name:
                return self._result("open", success=False, error="Invalid characters in app name.")

        if len(app_name) > 100:
            return self._result("open", success=False, error="App name too long")

        app_name_lower = app_name.lower()

        # 1️⃣ Try config store first (user-configured via Setup Wizard — has real paths)
        app_config = self._resolve_from_store(app_name_lower)
        if app_config and app_config.get("enabled", True):
            command = app_config.get("command", app_name_lower)
            return self._launch(app_name, command)

        # 2️⃣ Fall back to built-in defaults
        app_config = self._resolve_fallback(app_name_lower)
        if app_config:
            return self._launch(app_name, app_config.get("command", app_name_lower))

        # 3️⃣ Not found
        available = self._get_available_apps()
        return self._result("open", success=False, error=(
            f"Unknown app: '{app_name}'. Run the App Setup Wizard to detect installed apps!\n\n"
            f"Currently available: {', '.join(available[:10])}"
            + ("..." if len(available) > 10 else "")
        ))

    def _launch(self, name: str, command: str) -> ActionResult:
        """Launch an app using the best available method.

        On Windows:
        - Full paths (C:\\...\\app.exe) → subprocess.Popen directly
        - Bare names (discord, code) → try shutil.which first, then 'start'
        - 'start xxx' commands → shell=True as-is
        """
        logger.info("Opening app: {} → {}", name, command)

        try:
            system = platform.system()

            # Commands that start with 'start ' are shell built-ins
            if command.startswith("start "):
                subprocess.Popen(command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return self._result("open", success=True, result=f"Opened {name}")

            if system == "Windows":
                # Is it a full path to an executable?
                if "\\" in command or "/" in command:
                    path = Path(command)
                    if path.is_file():
                        # Direct launch of an .exe — no 'start' needed
                        subprocess.Popen(
                            [str(path)],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            cwd=str(path.parent),
                        )
                        return self._result("open", success=True, result=f"Opened {name}")
                    elif path.is_dir():
                        # It's a folder — open in Explorer
                        os.startfile(str(path))
                        return self._result("open", success=True, result=f"Opened {name} folder")
                    else:
                        # Path doesn't exist — try 'start' as fallback
                        subprocess.Popen(
                            f'start "" "{command}"',
                            shell=True,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                        )
                        return self._result("open", success=True, result=f"Opened {name}")

                # Bare name (e.g. "discord", "code") — resolve via PATH first
                import shutil
                resolved = shutil.which(command)
                if resolved:
                    subprocess.Popen(
                        [resolved],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    return self._result("open", success=True, result=f"Opened {name}")

                # Try .exe suffix
                if not command.lower().endswith(".exe"):
                    resolved = shutil.which(command + ".exe")
                    if resolved:
                        subprocess.Popen(
                            [resolved],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                        )
                        return self._result("open", success=True, result=f"Opened {name}")

                # Last resort: 'start' command
                subprocess.Popen(
                    f'start "" "{command}"',
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return self._result("open", success=True, result=f"Opened {name}")

            elif system == "Darwin":
                subprocess.Popen(["open", "-a", command], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return self._result("open", success=True, result=f"Opened {name}")

            else:  # Linux
                subprocess.Popen(
                    command.split() if " " in command else [command],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
                return self._result("open", success=True, result=f"Opened {name}")

        except FileNotFoundError:
            return self._result("open", success=False, error=f"App '{name}' not found. Run App Setup Wizard to configure the correct path.")
        except Exception as exc:
            logger.error("Launch failed for {}: {}", name, exc)
            return self._result("open", success=False, error=str(exc))

    def _close_app(self, app_name: str) -> ActionResult:
        if not app_name:
            return self._result("close", success=False, error="No app name provided")

        app_name_lower = app_name.lower().strip()
        app_config = self._resolve_from_store(app_name_lower) or self._resolve_fallback(app_name_lower)
        command = app_config.get("command", app_name_lower) if app_config else app_name_lower

        exe_name = command.split("\\")[-1] if "\\" in command else command
        if not exe_name.lower().endswith(".exe"):
            exe_name += ".exe"

        try:
            if platform.system() == "Windows":
                subprocess.run(["taskkill", "/IM", exe_name, "/F"], capture_output=True)
            else:
                subprocess.run(["pkill", "-f", command], capture_output=True)
            return self._result("close", success=True, result=f"Closed {app_name}")
        except Exception as exc:
            return self._result("close", success=False, error=str(exc))

    def _list_apps(self) -> ActionResult:
        apps = []
        try:
            from backend.apps.config_store import app_config_store
            enabled = app_config_store.get_enabled()
            for name, config in enabled.items():
                aliases = config.get("aliases", [name])[:3]
                apps.append(f"• {config.get('name', name)} ({', '.join(aliases)})")
        except Exception:
            pass

        if not apps:
            for name, config in self._DEFAULT_APPS.items():
                apps.append(f"• {name} ({', '.join(config['aliases'][:3])})")

        return self._result("list", success=True, result="Configured apps:\n" + "\n".join(apps))

    def _get_available_apps(self) -> list[str]:
        try:
            from backend.apps.config_store import app_config_store
            enabled = app_config_store.get_enabled()
            if enabled:
                return list(enabled.keys())
        except Exception:
            pass
        return list(self._DEFAULT_APPS.keys())

    def _resolve_from_store(self, name: str) -> dict[str, Any] | None:
        try:
            from backend.apps.config_store import app_config_store
            return app_config_store.resolve(name)
        except Exception:
            return None

    def _resolve_fallback(self, name: str) -> dict[str, Any] | None:
        if name in self._DEFAULT_APPS:
            return self._DEFAULT_APPS[name]
        for app_name, config in self._DEFAULT_APPS.items():
            if name in config.get("aliases", []):
                return config
        return None

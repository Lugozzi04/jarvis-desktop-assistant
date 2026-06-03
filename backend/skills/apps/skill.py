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

        if len(app_name) > 200:
            return self._result("open", success=False, error="App name too long")

        # ── Support multiple apps: /open discord, spotify ──
        # Split by comma, " and ", " e ", " y "
        import re
        parts = re.split(r'\s*,\s*|\s+and\s+|\s+e\s+|\s+y\s+', app_name)
        parts = [p.strip().lower() for p in parts if p.strip()]
        
        if len(parts) > 1:
            results = []
            for part in parts:
                r = self._open_single(part)
                results.append(r.result if r.success else f"❌ {r.error}")
            return self._result("open", success=True, result="\n".join(results))
        
        return self._open_single(app_name.lower().strip())

    def _open_single(self, app_name_lower: str) -> ActionResult:
        display_name = app_name_lower  # for error messages

        # 1️⃣ Try config store first (user-configured via Setup Wizard — has real paths)
        app_config = self._resolve_from_store(app_name_lower)
        if app_config and app_config.get("enabled", True):
            command = app_config.get("command", app_name_lower)
            display_name = app_config.get("name", app_name_lower)
            return self._launch(display_name, command)

        # 2️⃣ Fall back to built-in defaults
        app_config = self._resolve_fallback(app_name_lower)
        if app_config:
            return self._launch(display_name, app_config.get("command", app_name_lower))

        # 3️⃣ Not found
        available = self._get_available_apps()
        return self._result("open", success=False, error=(
            f"Unknown app: '{display_name}'. Run the App Setup Wizard to detect installed apps!\n\n"
            f"Currently available: {', '.join(available[:10])}"
            + ("..." if len(available) > 10 else "")
        ))

    def _launch(self, name: str, command: str) -> ActionResult:
        """Launch an app using the best available method.

        On Windows:
        - Full paths (C:\\...\\app.exe) → subprocess.Popen directly
        - Full folder paths → find .exe inside, launch that
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
                # Is it a full path?
                if "\\" in command or "/" in command:
                    path = Path(command)
                    if path.is_file():
                        # Direct launch of an .exe
                        subprocess.Popen(
                            [str(path)],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            cwd=str(path.parent),
                        )
                        return self._result("open", success=True, result=f"Opened {name}")
                    elif path.is_dir():
                        # It's a folder — search for matching .exe inside
                        exe_path = self._find_exe_in_folder(path, name)
                        if exe_path:
                            subprocess.Popen(
                                [str(exe_path)],
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL,
                                cwd=str(exe_path.parent),
                            )
                            return self._result("open", success=True, result=f"Opened {name}")
                        # No .exe found — open folder as fallback
                        os.startfile(str(path))
                        return self._result("open", success=True, result=f"Opened {name} folder")
                    else:
                        # Path doesn't exist — try 'start' as fallback (without quotes)
                        subprocess.Popen(
                            f'start "" {command}',
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

                # Last resort: 'start' command (without quotes — start resolves via App Paths registry)
                subprocess.Popen(
                    f'start "" {command}',
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

    def _find_exe_in_folder(self, folder: Path, app_name: str) -> Path | None:
        """Find the main executable in a folder. Searches folder + 1 level deep. Returns Path or None."""
        try:
            name_clean = app_name.lower().replace(" ", "").replace("-", "")

            # Collect all .exe files: folder root + 1 level deep
            all_exes = list(folder.glob("*.exe"))
            for sub in folder.iterdir():
                if sub.is_dir():
                    try:
                        all_exes.extend(sub.glob("*.exe"))
                    except PermissionError:
                        pass

            if not all_exes:
                return None

            candidates = sorted(all_exes)

            # Priority 1: exact name match (e.g., Spotify/Spotify.exe)
            for exe in candidates:
                stem = exe.stem.lower().replace(" ", "").replace("-", "")
                if stem == name_clean:
                    logger.info("Found exact exe match: {}", exe)
                    return exe

            # Priority 2: starts with name (e.g., Spotify/SpotifyLauncher.exe)
            for exe in candidates:
                stem = exe.stem.lower().replace(" ", "").replace("-", "")
                if stem.startswith(name_clean[:4]):
                    logger.info("Found prefix exe match: {}", exe)
                    return exe

            # Priority 3: name is in stem, skip uninstallers/updaters
            for exe in candidates:
                stem = exe.stem.lower().replace(" ", "").replace("-", "")
                if (name_clean[:3] in stem and
                    "uninstall" not in stem and
                    "update" not in stem and
                    "setup" not in stem and
                    "install" not in stem):
                    logger.info("Found fuzzy exe match: {}", exe)
                    return exe

            # Priority 4: largest .exe (usually the main app)
            largest = max(candidates, key=lambda p: p.stat().st_size)
            logger.info("Using largest exe: {} ({} bytes)", largest, largest.stat().st_size)
            return largest

        except Exception as exc:
            logger.warning("_find_exe_in_folder error: {}", exc)

        return None

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

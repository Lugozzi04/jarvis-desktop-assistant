"""App Configuration Store — persists user's selected apps and custom paths.

Stored in data/apps_config.json. The AppSkill loads from this at runtime.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.core.config import settings
from backend.core.logger import logger


class AppConfigStore:
    """Persistent store for user's app configuration."""

    def __init__(self):
        self._config_path = settings.data_path / "apps_config.json"
        self._apps: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        """Load config from disk."""
        try:
            if self._config_path.exists():
                data = json.loads(self._config_path.read_text())
                self._apps = data.get("apps", {})
                logger.info("App config loaded: {} apps", len(self._apps))
            else:
                self._apps = {}
        except Exception as exc:
            logger.warning("Failed to load app config: {}", exc)
            self._apps = {}

    def _save(self) -> None:
        """Persist config to disk."""
        try:
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            self._config_path.write_text(json.dumps({"apps": self._apps}, indent=2))
        except Exception as exc:
            logger.error("Failed to save app config: {}", exc)

    def get_all(self) -> dict[str, dict[str, Any]]:
        """Return all configured apps."""
        return dict(self._apps)

    def get(self, name: str) -> dict[str, Any] | None:
        """Get a specific app by name (case-insensitive)."""
        return self._apps.get(name.lower())

    def resolve(self, alias: str) -> dict[str, Any] | None:
        """Resolve an alias to an app config."""
        alias_lower = alias.lower().strip()

        # Direct name match
        if alias_lower in self._apps:
            return self._apps[alias_lower]

        # Alias match
        for app_name, config in self._apps.items():
            if alias_lower in config.get("aliases", []):
                return config

        return None

    def add(self, name: str, command: str, aliases: list[str] | None = None, path: str = "") -> dict[str, Any]:
        """Add or update an app."""
        key = name.lower()
        config = {
            "name": name,
            "command": command,
            "path": path or command,
            "aliases": aliases or [key],
            "enabled": True,
        }
        self._apps[key] = config
        self._save()
        return config

    def remove(self, name: str) -> bool:
        """Remove an app by name."""
        key = name.lower()
        if key in self._apps:
            del self._apps[key]
            self._save()
            return True
        return False

    def set_enabled(self, name: str, enabled: bool) -> bool:
        """Enable or disable an app."""
        key = name.lower()
        if key in self._apps:
            self._apps[key]["enabled"] = enabled
            self._save()
            return True
        return False

    def update_command(self, name: str, command: str) -> bool:
        """Update an app's executable command/path."""
        key = name.lower()
        if key in self._apps:
            self._apps[key]["command"] = command
            self._apps[key]["path"] = command
            self._save()
            return True
        return False

    def import_from_detection(self, detected_apps: list[dict[str, Any]]) -> int:
        """Import detected apps, merging with existing config (preserves user edits)."""
        imported = 0
        for app in detected_apps:
            key = app["name"].lower()

            # Skip if already configured
            if key in self._apps:
                # Update path if detected but keep user's command if set
                existing = self._apps[key]
                if app.get("detected") and app.get("path"):
                    if not existing.get("user_configured"):
                        existing["path"] = app["path"]
                        if not existing.get("command_override"):
                            existing["command"] = app["path"]
                continue

            # Import new app
            self._apps[key] = {
                "name": app["name"],
                "command": app.get("command", app["name"].lower()),
                "path": app.get("path", ""),
                "aliases": app.get("aliases", [key]),
                "enabled": app.get("builtin", False) or app.get("detected", False),
                "builtin": app.get("builtin", False),
                "detected": app.get("detected", False),
            }
            imported += 1

        if imported > 0:
            self._save()
            logger.info("Imported {} new apps from detection", imported)

        return imported

    def get_enabled(self) -> dict[str, dict[str, Any]]:
        """Return only enabled apps."""
        return {k: v for k, v in self._apps.items() if v.get("enabled", True)}


# Singleton
app_config_store = AppConfigStore()

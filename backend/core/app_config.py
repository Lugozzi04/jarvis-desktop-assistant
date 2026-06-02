"""App Configuration — model and JSON-persisted store for tracked desktop apps.

Each AppConfig represents a desktop application that JARVIS can interact with
(e.g. OBS, Discord, Spotify, VS Code, browser, terminal, GitHub).
The store persists configs to data/app_config.json.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from backend.core.logger import logger

# ── Constants ──

APP_TYPE = Literal["obs", "discord", "spotify", "vscode", "browser", "terminal", "github"]

DEFAULT_DATA_FILE = "data/app_config.json"

# ── Built-in defaults for common apps ──

_BUILTIN_APPS: list[dict] = [
    {"name": "obs", "aliases": ["obs", "obs64"], "type": "obs", "enabled": True, "notes": "OBS Studio"},
    {"name": "discord", "aliases": ["discord", "Discord"], "type": "discord", "enabled": True, "notes": "Discord chat app"},
    {"name": "spotify", "aliases": ["spotify", "Spotify"], "type": "spotify", "enabled": True, "notes": "Spotify music player"},
    {"name": "vscode", "aliases": ["code", "Code", "Code - Insiders"], "type": "vscode", "enabled": True, "notes": "Visual Studio Code"},
    {"name": "browser", "aliases": ["chrome", "firefox", "brave", "edge", "chromium"], "type": "browser", "enabled": True, "notes": "Web browser"},
    {"name": "terminal", "aliases": ["gnome-terminal", "konsole", "alacritty", "kitty", "wt", "WindowsTerminal", "Terminal"], "type": "terminal", "enabled": True, "notes": "Terminal emulator"},
    {"name": "github", "aliases": ["github"], "type": "github", "enabled": False, "notes": "GitHub integration (API-based, not a process)"},
]


# ── Model ──

class AppConfig(BaseModel):
    """Configuration for a single tracked desktop application."""

    name: str = Field(..., description="Unique app identifier (e.g. 'obs', 'discord')")
    path: str | None = Field(default=None, description="Optional filesystem path to the executable")
    aliases: list[str] = Field(default_factory=list, description="Alternative process names used for detection")
    type: APP_TYPE = Field(..., description="App category")
    enabled: bool = Field(default=True, description="Whether this app is actively tracked")
    notes: str = Field(default="", description="Human-readable notes about this app")


# ── AppConfigUpdate (partial update) ──

class AppConfigUpdate(BaseModel):
    """Partial update payload — all fields optional."""

    path: str | None = None
    aliases: list[str] | None = None
    type: APP_TYPE | None = None
    enabled: bool | None = None
    notes: str | None = None


# ── DetectedApp result ──

class DetectedApp(BaseModel):
    """Result from app detection."""

    name: str
    type: APP_TYPE
    found: bool
    path: str | None = None
    running: bool = False
    matched_alias: str | None = None


# ── Store ──

class AppConfigStore:
    """JSON-backed store for app configurations with detection support."""

    def __init__(self, data_path: str = DEFAULT_DATA_FILE) -> None:
        self._path = Path(data_path)
        self._configs: dict[str, AppConfig] = {}
        self._load()

    # ── Persistence ──

    def _resolve_path(self) -> Path:
        """Resolve the data file path, creating parent directories as needed."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        return self._path

    def _load(self) -> None:
        """Load configs from JSON, or seed with built-in defaults on first run."""
        path = self._resolve_path()
        if path.exists():
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(raw, list):
                    for item in raw:
                        try:
                            cfg = AppConfig(**item)
                            self._configs[cfg.name] = cfg
                        except Exception as exc:
                            logger.warning("Skipping invalid app config entry '{}': {}", item.get("name", "?"), exc)
                elif isinstance(raw, dict):
                    for key, item in raw.items():
                        try:
                            cfg = AppConfig(**{**item, "name": key})
                            self._configs[cfg.name] = cfg
                        except Exception as exc:
                            logger.warning("Skipping invalid app config entry '{}': {}", key, exc)
            except Exception as exc:
                logger.error("Failed to load app_config.json: {}", exc)
                self._seed_defaults()
        else:
            self._seed_defaults()

    def _save(self) -> None:
        """Persist current configs to JSON as a list."""
        path = self._resolve_path()
        data = [cfg.model_dump() for cfg in self._configs.values()]
        path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    def _seed_defaults(self) -> None:
        """Seed the store with built-in defaults."""
        for item in _BUILTIN_APPS:
            cfg = AppConfig(**item)
            self._configs[cfg.name] = cfg
        self._save()
        logger.info("Seeded {} built-in app configs", len(self._configs))

    # ── Access ──

    def get_all(self) -> list[AppConfig]:
        """Return all configured apps."""
        return list(self._configs.values())

    def get(self, name: str) -> AppConfig | None:
        """Get a single app config by name, or None."""
        return self._configs.get(name)

    def set(self, name: str, config: AppConfig | dict) -> AppConfig:
        """Create or update an app config. Accepts AppConfig or dict."""
        if isinstance(config, dict):
            # Merge with existing if partial dict
            existing = self._configs.get(name)
            if existing:
                merged = {**existing.model_dump(), **config}
                cfg = AppConfig(**merged)
            else:
                cfg = AppConfig(name=name, type="browser", **config)
        else:
            cfg = config
            if cfg.name != name:
                cfg = cfg.model_copy(update={"name": name})

        self._configs[name] = cfg
        self._save()
        return cfg

    def delete(self, name: str) -> bool:
        """Delete an app config. Returns True if it existed."""
        if name in self._configs:
            del self._configs[name]
            self._save()
            return True
        return False

    # ── Detection ──

    def _is_vps(self) -> bool:
        """Heuristic: are we on a headless VPS with no desktop environment?"""
        # No DISPLAY/WAYLAND_DISPLAY and not on macOS/Windows suggests headless VPS
        if sys.platform == "darwin":
            return False
        if sys.platform == "win32":
            return False
        return not bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))

    def detect(self) -> list[DetectedApp]:
        """Detect which configured apps are installed / running.

        On headless/VPS environments (no DISPLAY), returns mock placeholders.
        On desktop, uses shutil.which() for binary detection and psutil for
        running-process checks (when psutil is installed).
        """
        if self._is_vps():
            return self._detect_mock()

        results: list[DetectedApp] = []
        for cfg in self._configs.values():
            found = False
            matched = None
            running = False
            path = cfg.path

            # 1) Check explicit path
            if cfg.path:
                path_exists = Path(cfg.path).exists()
                if path_exists:
                    found = True
                    path = cfg.path

            # 2) Try aliases via shutil.which
            if not found and cfg.aliases:
                for alias in cfg.aliases:
                    resolved = shutil.which(alias)
                    if resolved:
                        found = True
                        matched = alias
                        if path is None:
                            path = resolved
                        break

            # 3) GitHub is API-based, never a local binary
            if cfg.type == "github":
                # GitHub is always "found" as an integration; check API key
                gh_token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
                found = bool(gh_token)
                path = None

            # 4) Check if running via psutil
            if found:
                try:
                    import psutil  # type: ignore[import-untyped]

                    aliases_lower = [a.lower() for a in (cfg.aliases or [])]
                    for proc in psutil.process_iter(["name"]):
                        try:
                            pname = (proc.info.get("name") or "").lower()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
                        if pname in aliases_lower or any(
                            alias.lower() in pname for alias in cfg.aliases
                        ):
                            running = True
                            break
                except ImportError:
                    pass  # psutil not installed; can't check running status

            results.append(
                DetectedApp(
                    name=cfg.name,
                    type=cfg.type,
                    found=found,
                    path=path,
                    running=running,
                    matched_alias=matched,
                )
            )

        return results

    def _detect_mock(self) -> list[DetectedApp]:
        """Return mock detection results for VPS/headless environments."""
        mock_status: dict[str, bool] = {
            "obs": False,
            "discord": False,
            "spotify": False,
            "vscode": False,
            "browser": False,
            "terminal": True,   # a terminal is always available on a VPS
            "github": bool(os.environ.get("GITHUB_TOKEN")),
        }
        results: list[DetectedApp] = []
        for cfg in self._configs.values():
            is_found = mock_status.get(cfg.name, False)
            results.append(
                DetectedApp(
                    name=cfg.name,
                    type=cfg.type,
                    found=is_found,
                    path=None,
                    running=is_found,
                    matched_alias=None,
                )
            )
        return results


# ── Singleton ──

_app_config_store: AppConfigStore | None = None


def get_app_config_store() -> AppConfigStore:
    """Return the singleton AppConfigStore, creating it on first call."""
    global _app_config_store
    if _app_config_store is None:
        _app_config_store = AppConfigStore()
    return _app_config_store

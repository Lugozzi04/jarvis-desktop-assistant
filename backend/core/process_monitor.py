"""Process Monitor — cross-platform app/process detection.

Uses psutil for real process monitoring with clean fallback when unavailable.
Provides process normalization, alias matching, and new-process detection.
"""

from __future__ import annotations

import re
from typing import Any

from backend.core.logger import logger

# ── App name → process name aliases ──
# Maps user-friendly names to patterns matched against running process names.
APP_ALIASES: dict[str, list[str]] = {
    "obs": ["obs64", "obs", "obs studio"],
    "discord": ["discord", "discord.exe", "discordcanary"],
    "spotify": ["spotify", "spotify.exe"],
    "code": ["code", "code.exe", "visual studio code", "vscode"],
    "vs code": ["code", "code.exe", "visual studio code", "vscode"],
    "vscode": ["code", "code.exe"],
    "chrome": ["chrome", "chrome.exe", "google chrome"],
    "firefox": ["firefox", "firefox.exe"],
    "terminal": ["terminal", "windows terminal", "wt.exe", "gnome-terminal", "konsole", "alacritty", "kitty", "iterm2"],
    "slack": ["slack", "slack.exe"],
    "zoom": ["zoom", "zoom.exe"],
    "telegram": ["telegram", "telegram.exe", "telegram desktop"],
}

# Inverse mapping for quick lookup
_ALIAS_LOOKUP: dict[str, str] = {}
for _app_name, _aliases in APP_ALIASES.items():
    for _alias in _aliases:
        _ALIAS_LOOKUP[_alias.lower()] = _app_name


def normalize_app_name(name: str) -> str:
    """Normalize an app name to its canonical form."""
    name_lower = name.lower().strip()
    # Direct match
    if name_lower in APP_ALIASES:
        return name_lower
    # Alias lookup
    if name_lower in _ALIAS_LOOKUP:
        return _ALIAS_LOOKUP[name_lower]
    return name_lower


def normalize_process_name(proc_name: str) -> str:
    """Normalize a process name: lowercase, strip extension, clean up."""
    name = proc_name.lower().strip()
    # Remove .exe
    if name.endswith(".exe"):
        name = name[:-4]
    # Remove common suffixes
    name = re.sub(r"[\s\-_]+(64|32|canary|beta|alpha)$", "", name)
    return name.strip()


def get_running_processes() -> list[dict[str, Any]]:
    """Get list of running processes. Returns [] with error log on failure.

    Returns:
        List of dicts with keys: name, pid, exe, cmdline
    """
    try:
        import psutil

        processes = []
        for proc in psutil.process_iter(["name", "pid", "exe", "cmdline"]):
            try:
                info = proc.info
                # Filter out None names
                if info.get("name"):
                    processes.append({
                        "name": info.get("name", ""),
                        "pid": info.get("pid", 0),
                        "exe": info.get("exe", ""),
                        "cmdline": " ".join(info.get("cmdline", []) or []),
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
                continue
        return processes
    except ImportError:
        logger.warning("psutil not available — process monitoring disabled")
        return []
    except Exception as exc:
        logger.error("Failed to list processes: {}", exc)
        return []


def is_app_running(app_name: str) -> bool:
    """Check if an app is currently running.

    Args:
        app_name: User-friendly app name (e.g., 'discord', 'OBS', 'Code')

    Returns:
        True if a matching process is found.
    """
    return match_app_to_process(app_name) is not None


def match_app_to_process(app_name: str) -> dict[str, Any] | None:
    """Find a process matching the given app name.

    Returns the first matching process dict, or None.
    """
    processes = get_running_processes()
    if not processes:
        return None

    normalized_app = normalize_app_name(app_name)
    aliases = APP_ALIASES.get(normalized_app, [normalized_app])

    for proc in processes:
        proc_norm = normalize_process_name(proc["name"])
        for alias in aliases:
            alias_norm = normalize_process_name(alias)
            if proc_norm == alias_norm or alias_norm in proc_norm or proc_norm in alias_norm:
                return proc

    return None


class ProcessMonitor:
    """Monitors processes for new-app detection.

    Maintains a snapshot of previously seen processes and detects new ones.
    Used by the AutomationEngine for `app_opened` triggers.
    """

    def __init__(self):
        self._previous_snapshot: set[str] = set()
        self._initialized = False

    def _init_snapshot(self) -> None:
        """Take initial snapshot of running processes."""
        if self._initialized:
            return
        processes = get_running_processes()
        self._previous_snapshot = {normalize_process_name(p["name"]) for p in processes}
        self._initialized = True
        logger.info("ProcessMonitor initialized — tracking {} processes", len(self._previous_snapshot))

    def detect_new_processes(self) -> list[str]:
        """Detect processes that weren't in the previous snapshot.

        Returns:
            List of normalized process names that are new.
        """
        self._init_snapshot()
        current = get_running_processes()
        current_names = {normalize_process_name(p["name"]) for p in current}

        new = current_names - self._previous_snapshot
        self._previous_snapshot = current_names
        return list(new)

    def is_app_newly_opened(self, app_name: str) -> bool:
        """Check if an app was opened since the last check.

        More precise than is_app_running — avoids false positives
        for apps that were already running.

        Args:
            app_name: User-friendly app name

        Returns:
            True if the app was detected as a new process.
        """
        self._init_snapshot()
        new = self.detect_new_processes()
        if not new:
            return False

        normalized_app = normalize_app_name(app_name)
        aliases = APP_ALIASES.get(normalized_app, [normalized_app])
        normalized_aliases = [normalize_process_name(a) for a in aliases]

        for proc_name in new:
            for alias in normalized_aliases:
                if alias in proc_name or proc_name in alias:
                    logger.info("Detected newly opened app: {} (matched: {})", app_name, proc_name)
                    return True

        return False

    def get_status(self) -> dict[str, Any]:
        """Get monitor status for health checks."""
        return {
            "available": _psutil_available(),
            "tracked_processes": len(self._previous_snapshot),
            "initialized": self._initialized,
            "aliases_configured": len(APP_ALIASES),
        }


def _psutil_available() -> bool:
    """Check if psutil is importable."""
    try:
        import psutil  # noqa: F401
        return True
    except ImportError:
        return False


# Singleton
process_monitor = ProcessMonitor()

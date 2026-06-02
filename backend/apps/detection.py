"""App Detection — scans Windows for installed applications.

Scans:
  - Start Menu (.lnk shortcuts)
  - PATH executables
  - Common install locations (Program Files, etc.)

Returns detected apps with name, path, and category.
"""

from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path
from typing import Any

from backend.core.logger import logger


# Well-known apps with their common executable names and search aliases
_KNOWN_APPS: dict[str, list[str]] = {
    "Discord": ["discord.exe", "Discord.exe", "Discord"],
    "Spotify": ["spotify.exe", "Spotify.exe", "Spotify"],
    "VS Code": ["code.exe", "Code.exe", "Visual Studio Code"],
    "OBS Studio": ["obs64.exe", "obs.exe", "OBS Studio", "OBS"],
    "Google Chrome": ["chrome.exe", "Google Chrome"],
    "Firefox": ["firefox.exe", "Firefox"],
    "Microsoft Edge": ["msedge.exe", "Microsoft Edge"],
    "Notepad++": ["notepad++.exe", "Notepad++"],
    "Telegram": ["telegram.exe", "Telegram Desktop", "Telegram"],
    "Slack": ["slack.exe", "Slack"],
    "Steam": ["steam.exe", "Steam"],
    "VLC": ["vlc.exe", "VLC media player", "VLC"],
    "7-Zip": ["7zFM.exe", "7-Zip File Manager", "7-Zip"],
    "WinRAR": ["winrar.exe", "WinRAR"],
    "Paint.NET": ["paintdotnet.exe", "Paint.NET"],
    "GIMP": ["gimp-2.10.exe", "gimp.exe", "GIMP"],
    "Blender": ["blender.exe", "Blender"],
    "Zoom": ["zoom.exe", "Zoom"],
    "Webex": ["webex.exe", "Cisco Webex", "Webex"],
    "Teams": ["teams.exe", "Microsoft Teams", "Teams"],
    "Outlook": ["outlook.exe", "Microsoft Outlook", "Outlook"],
    "Excel": ["excel.exe", "Microsoft Excel", "Excel"],
    "Word": ["winword.exe", "Microsoft Word", "Word"],
    "PowerPoint": ["powerpnt.exe", "Microsoft PowerPoint", "PowerPoint"],
}

# Built-in Windows apps (always available via aliases)
_BUILTIN_APPS: dict[str, str] = {
    "Terminal": "wt.exe",
    "Calculator": "calc.exe",
    "Notepad": "notepad.exe",
    "Explorer": "explorer.exe",
    "Settings": "start ms-settings:",
    "Task Manager": "taskmgr.exe",
    "Control Panel": "control.exe",
    "Paint": "mspaint.exe",
    "Snipping Tool": "snippingtool.exe",
    "Command Prompt": "cmd.exe",
    "PowerShell": "powershell.exe",
}


def _scan_start_menu() -> dict[str, str]:
    """Scan Start Menu for .lnk shortcuts."""
    found: dict[str, str] = {}
    start_menu_paths = [
        Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
        Path(os.environ.get("PROGRAMDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
    ]

    for base in start_menu_paths:
        if not base.exists():
            continue
        for lnk in base.rglob("*.lnk"):
            try:
                name = lnk.stem
                found[name.lower()] = str(lnk)
            except Exception:
                pass

    return found


def _search_path() -> dict[str, str]:
    """Search PATH for known executables."""
    found: dict[str, str] = {}
    path_dirs = os.environ.get("PATH", "").split(os.pathsep)

    for app_name, exe_names in _KNOWN_APPS.items():
        for exe in exe_names[:2]:  # Try first 2 executable names
            if not exe.lower().endswith(".exe"):
                continue
            for d in path_dirs:
                p = Path(d) / exe
                if p.exists():
                    found[app_name.lower()] = str(p)
                    break
            if app_name.lower() in found:
                break

    return found


def _search_common_dirs() -> dict[str, str]:
    """Search common install directories for known apps."""
    found: dict[str, str] = {}
    common_bases = []

    # Program Files
    for pf_var in ["ProgramFiles", "ProgramFiles(x86)", "ProgramW6432"]:
        pf = os.environ.get(pf_var)
        if pf:
            common_bases.append(Path(pf))

    # Local AppData
    local = os.environ.get("LOCALAPPDATA")
    if local:
        common_bases.append(Path(local))

    for base in common_bases:
        if not base.exists():
            continue

        for app_name, search_terms in _KNOWN_APPS.items():
            if app_name.lower() in found:
                continue

            for term in search_terms:
                candidate = base / term
                if candidate.exists():
                    found[app_name.lower()] = str(candidate)
                    break

                # Also check subdirectories (e.g., Program Files/Discord/Discord.exe)
                for subdir in base.iterdir():
                    if not subdir.is_dir():
                        continue
                    candidate = subdir / term
                    if candidate.exists():
                        found[app_name.lower()] = str(candidate)
                        break
                if app_name.lower() in found:
                    break

    return found


def detect_apps() -> list[dict[str, Any]]:
    """Scan the system for installed applications.

    Returns a list of detected apps with name, path, category, and aliases.
    """
    if platform.system() != "Windows":
        # On non-Windows, return built-in + basic detection
        apps: list[dict[str, Any]] = []
        for name, cmd in _BUILTIN_APPS.items():
            apps.append({
                "name": name,
                "command": cmd,
                "path": "",
                "category": "system",
                "aliases": [name.lower()],
                "builtin": True,
                "detected": True,
            })
        return apps

    logger.info("Scanning for installed applications...")

    # Collect from all sources
    start_menu = _scan_start_menu()
    path_found = _search_path()
    common_found = _search_common_dirs()

    logger.info(
        "App scan results — Start Menu: {} | PATH: {} | Common dirs: {}",
        len(start_menu), len(path_found), len(common_found),
    )

    apps: list[dict[str, Any]] = []

    # Built-in Windows apps (always available)
    for name, cmd in _BUILTIN_APPS.items():
        apps.append({
            "name": name,
            "command": cmd,
            "path": cmd,
            "category": "system",
            "aliases": [name.lower(), name.lower().replace(" ", "")],
            "builtin": True,
            "detected": True,
        })

    # Detected desktop apps
    all_detected = {**common_found, **path_found}  # path_found overwrites common_found

    for app_name, search_terms in _KNOWN_APPS.items():
        key = app_name.lower()
        path = all_detected.get(key, "")

        if path:
            aliases = [key.replace(" ", ""), key]
            # Add shorter aliases
            words = app_name.lower().split()
            if len(words) > 1:
                aliases.extend(words)
                aliases.append("".join(words))

            apps.append({
                "name": app_name,
                "command": path,
                "path": path,
                "category": "desktop",
                "aliases": list(dict.fromkeys(aliases)),  # dedupe, preserve order
                "builtin": False,
                "detected": True,
            })
        else:
            # App not detected — add placeholder
            apps.append({
                "name": app_name,
                "command": search_terms[0],
                "path": "",
                "category": "desktop",
                "aliases": [app_name.lower()],
                "builtin": False,
                "detected": False,
            })

    return apps

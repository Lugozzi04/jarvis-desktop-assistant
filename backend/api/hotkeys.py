"""Hotkey API — read and configure global shortcut keys."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["hotkeys"])


class HotkeyUpdate(BaseModel):
    modifiers: list[str]  # ["ctrl", "alt", "shift", "cmd"]
    key: str  # "space", "a", "f1", etc.


def _hotkey_path() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "data" / "hotkeys.json"


def _read_hotkeys() -> dict:
    p = _hotkey_path()
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            pass
    return {"modifiers": ["ctrl", "shift"], "key": "space"}


def _save_hotkeys(data: dict) -> None:
    p = _hotkey_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2))


@router.get("/hotkeys")
def get_hotkeys():
    """Get current hotkey configuration."""
    return _read_hotkeys()


@router.put("/hotkeys")
def update_hotkeys(req: HotkeyUpdate):
    """Update hotkey configuration."""
    data = {
        "modifiers": [m.lower() for m in req.modifiers if m.lower() in ("ctrl", "alt", "shift", "cmd")],
        "key": req.key.lower(),
    }
    _save_hotkeys(data)
    return {"success": True, "hotkey": data, "note": "Restart tray mode for changes to take effect."}

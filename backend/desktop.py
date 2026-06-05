"""Jarvis Desktop Launcher — opens a native window using pywebview.

No Electron, no npm, no browser. Uses the OS-native webview:
  - Windows 10/11: Edge WebView2 (pre-installed)
  - macOS: WKWebView
  - Linux: GTK WebKit (apt install python3-pyqt5.qtwebengine)

The FastAPI backend runs in a background thread. Global hotkey (Ctrl+Shift)
launches overlay even when running in windowed mode.
"""

from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
from pathlib import Path

import webview
import uvicorn

PROJECT_ROOT = Path(__file__).resolve().parent.parent

HOST = "127.0.0.1"
PORT = 8400
URL = f"http://{HOST}:{PORT}"


class BackendThread(threading.Thread):
    """Run the FastAPI backend in a daemon thread."""

    def __init__(self):
        super().__init__(daemon=True, name="jarvis-backend")
        self._server: uvicorn.Server | None = None

    def run(self):
        config = uvicorn.Config(
            "backend.main:app",
            host=HOST,
            port=PORT,
            log_level="info",
            reload=False,
        )
        self._server = uvicorn.Server(config)
        self._server.run()

    def stop(self):
        if self._server:
            self._server.should_exit = True


# ── Hotkey in windowed mode ──

def _load_hotkey_config() -> dict:
    p = PROJECT_ROOT / "data" / "hotkeys.json"
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            pass
    return {"modifiers": ["ctrl", "shift"], "key": ""}


class WindowHotkey(threading.Thread):
    """Global hotkey listener for windowed mode.
    Fires overlay via subprocess when chord is pressed."""

    def __init__(self):
        super().__init__(daemon=True, name="window-hotkey")
        self._active = True
        self._pressed: set[str] = set()
        self._fired = False

    def _launch_overlay(self):
        """Spawn overlay in a subprocess."""
        try:
            python = sys.executable
            script = PROJECT_ROOT / "backend" / "_win_overlay.py"
            # Regenerate the overlay script if needed
            if not script.exists():
                script.parent.mkdir(parents=True, exist_ok=True)
                script.write_text(
                    "# -*- coding: utf-8 -*-\n"
                    + '"""Auto-generated overlay launcher."""\n'
                    + f'import sys, time; sys.path.insert(0, r"{PROJECT_ROOT}")\n'
                    + "import webview, httpx\n"
                    + f'URL = "{URL}"\n'
                    + "for _ in range(20):\n"
                    + "  try: httpx.get(f'{URL}/health', timeout=1); break\n"
                    + "  except: time.sleep(0.5)\n"
                    + "window = webview.create_window(title='JARVIS', url=f'{URL}/overlay', "
                    + "width=700, height=500, min_size=(400,300), resizable=True, confirm_close=False, text_select=True)\n"
                    + "webview.start(gui=None, debug=False)\n",
                    encoding="utf-8",
                )
            subprocess.Popen(
                [python, str(script)],
                cwd=str(PROJECT_ROOT),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )
        except Exception:
            pass

    def run(self):
        try:
            from pynput import keyboard
            from pynput.keyboard import Key

            mapping = {
                Key.ctrl_l: "ctrl", Key.ctrl_r: "ctrl",
                Key.alt_l: "alt", Key.alt_r: "alt",
                Key.shift_l: "shift", Key.shift_r: "shift",
                Key.cmd_l: "cmd", Key.cmd_r: "cmd",
            }

            def on_press(key):
                cfg = _load_hotkey_config()
                needed = set(cfg.get("modifiers", ["ctrl", "shift"]))
                target_key = cfg.get("key", "")

                name = mapping.get(key)
                if name:
                    self._pressed.add(name)
                    # CHORD mode
                    if not target_key and not self._fired and needed.issubset(self._pressed):
                        self._fired = True
                        self._launch_overlay()
                elif target_key and hasattr(key, 'name') and key.name == target_key:
                    if needed.issubset(self._pressed):
                        self._launch_overlay()

            def on_release(key):
                name = mapping.get(key)
                if name:
                    self._pressed.discard(name)
                    cfg = _load_hotkey_config()
                    needed = set(cfg.get("modifiers", ["ctrl", "shift"]))
                    if not needed.issubset(self._pressed):
                        self._fired = False

            with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
                while self._active:
                    time.sleep(0.2)
                listener.stop()
        except ImportError:
            pass


def main():
    print("⚡ Starting Jarvis backend...")
    backend = BackendThread()
    backend.start()

    # Wait for backend to be ready
    import httpx
    for _ in range(30):
        try:
            r = httpx.get(f"{URL}/health", timeout=1)
            if r.status_code == 200:
                print(f"✅ Backend ready at {URL}")
                break
        except Exception:
            time.sleep(0.5)
    else:
        print("⚠️  Backend didn't start in time — continuing anyway")
        print(f"   Check {URL}/health manually")

    # Hotkey (Ctrl+Shift to open overlay even in windowed mode)
    hotkey = WindowHotkey()
    hotkey.start()
    print("⌨️  Ctrl+Shift — overlay quick analyze")

    print(f"🖥️  Opening Jarvis window ({URL})...")
    print("   Close the window to exit.")

    window = webview.create_window(
        title="Jarvis Desktop Assistant",
        url=URL,
        width=1100,
        height=750,
        min_size=(800, 500),
        resizable=True,
        fullscreen=False,
        confirm_close=True,
        text_select=True,
    )

    webview.start(gui=None, debug=False)

    print("👋 Window closed. Stopping backend...")
    hotkey._active = False
    backend.stop()
    print("✅ Jarvis exited.")


if __name__ == "__main__":
    sys.path.insert(0, str(PROJECT_ROOT))
    main()

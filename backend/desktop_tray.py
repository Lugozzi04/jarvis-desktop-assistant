"""Jarvis Desktop Tray — system tray + global hotkey + overlay launcher.

HOW TO USE:
    python -m backend.desktop_tray

Architecture:
    1. Start FastAPI backend in daemon thread
    2. Start pystray icon tray thread with right-click menu
    3. Start pynput global hotkey listener thread
    4. Keep main thread alive, serve webview windows on-demand via subprocess
"""

from __future__ import annotations

import json
import sys
import threading
import time
import subprocess
from pathlib import Path

import uvicorn

PROJECT_ROOT = Path(__file__).resolve().parent.parent
HOST = "127.0.0.1"
PORT = 8400
URL = f"http://{HOST}:{PORT}"


# ── Backend ──

class BackendThread(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True, name="jarvis-backend")

    def run(self):
        config = uvicorn.Config(
            "backend.main:app", host=HOST, port=PORT,
            log_level="warning", reload=False,
        )
        uvicorn.Server(config).run()


# ── Helpers ──

def _load_hotkey_config() -> dict:
    p = PROJECT_ROOT / "data" / "hotkeys.json"
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            pass
    return {"modifiers": ["alt"], "key": "space"}


def _hotkey_label() -> str:
    cfg = _load_hotkey_config()
    mods = " + ".join(m.upper() for m in cfg.get("modifiers", ["alt"]))
    key = cfg.get("key", "space").upper()
    return f"{mods} + {key}"


# ── Tray ──

class TrayIcon:
    """System tray icon with menu."""

    def __init__(self, on_main, on_overlay, on_quit):
        self._open_main = on_main
        self._open_overlay = on_overlay
        self._quit = on_quit
        self._icon = None

    def run(self):
        try:
            import pystray
            from PIL import Image, ImageDraw

            img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            d.ellipse([4, 4, 60, 60], fill=(99, 102, 241))
            d.rectangle([24, 12, 40, 52], fill=(255, 255, 255))
            d.rectangle([16, 28, 48, 36], fill=(255, 255, 255))

            menu = pystray.Menu(
                pystray.MenuItem("🖥️  Apri Jarvis", self._open_main),
                pystray.MenuItem(f"⚡ {_hotkey_label()} (Analizza)", self._open_overlay),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("❌ Esci", self._quit),
            )

            self._icon = pystray.Icon("jarvis", img, "JARVIS Desktop Assistant", menu)
            self._icon.run()
        except ImportError:
            print("⚠️  pystray not installed — tray disabled")
        except Exception as exc:
            print(f"⚠️  Tray error: {exc}")

    def stop(self):
        if self._icon:
            try:
                self._icon.stop()
            except Exception:
                pass


# ── Hotkey ──

class HotkeyListener:
    """Global hotkey listener."""

    def __init__(self, callback):
        self._callback = callback
        self._active = True
        self._pressed = set()

    def _on_press(self, key):
        if not self._active:
            return False
        try:
            from pynput.keyboard import Key
            mapping = {
                Key.ctrl_l: "ctrl", Key.ctrl_r: "ctrl",
                Key.alt_l: "alt", Key.alt_r: "alt",
                Key.shift_l: "shift", Key.shift_r: "shift",
                Key.cmd_l: "cmd", Key.cmd_r: "cmd",
            }
            name = mapping.get(key)
            if name:
                self._pressed.add(name)
            elif hasattr(key, 'name'):
                cfg = _load_hotkey_config()
                if key.name == cfg.get("key", "space"):
                    needed = set(cfg.get("modifiers", ["alt"]))
                    if needed.issubset(self._pressed):
                        threading.Thread(target=self._callback, daemon=True).start()
        except Exception:
            pass

    def _on_release(self, key):
        try:
            from pynput.keyboard import Key
            mapping = {
                Key.ctrl_l: "ctrl", Key.ctrl_r: "ctrl",
                Key.alt_l: "alt", Key.alt_r: "alt",
                Key.shift_l: "shift", Key.shift_r: "shift",
                Key.cmd_l: "cmd", Key.cmd_r: "cmd",
            }
            name = mapping.get(key)
            if name:
                self._pressed.discard(name)
        except Exception:
            pass

    def run(self):
        try:
            from pynput import keyboard
            print(f"⌨️  Hotkey active: {_hotkey_label()}")
            with keyboard.Listener(
                on_press=self._on_press,
                on_release=self._on_release,
            ) as listener:
                while self._active:
                    time.sleep(0.2)
                listener.stop()
        except ImportError:
            print("⚠️  pynput not installed — hotkey disabled")

    def stop(self):
        self._active = False


# ── Window Launchers ──

def launch_main_window():
    """Open Jarvis main window in a separate Python process (pywebview)."""
    script = PROJECT_ROOT / "backend" / "_win_main.py"
    # Create the window script if it doesn't exist
    if not script.exists():
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_text(f'''"""Auto-generated: Jarvis main window launcher."""
import sys, time
sys.path.insert(0, r"{PROJECT_ROOT}")

import webview
import httpx

URL = "{URL}"

# Wait for backend
for _ in range(20):
    try:
        httpx.get(f"{{URL}}/health", timeout=1)
        break
    except Exception:
        time.sleep(0.5)

window = webview.create_window(
    title="JARVIS Desktop Assistant",
    url=URL,
    width=1100, height=750,
    min_size=(800, 500),
    resizable=True,
    confirm_close=True,
    text_select=True,
)
webview.start(gui=None, debug=False)
print("Main window closed.")
''')

    venv_python = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    if not venv_python.exists():
        venv_python = sys.executable

    try:
        subprocess.Popen(
            [str(venv_python), str(script)],
            cwd=str(PROJECT_ROOT),
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        print("🖥️  Main window launched")
    except Exception as exc:
        print(f"⚠️  Failed to launch main window: {exc}")


def launch_overlay():
    """Open overlay window in a separate Python process (pywebview)."""
    script = PROJECT_ROOT / "backend" / "_win_overlay.py"
    if not script.exists():
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_text(f'''"""Auto-generated: Jarvis overlay launcher."""
import sys, time
sys.path.insert(0, r"{PROJECT_ROOT}")

import webview
import httpx

URL = "{URL}"

# Wait for backend
for _ in range(20):
    try:
        httpx.get(f"{{URL}}/health", timeout=1)
        break
    except Exception:
        time.sleep(0.5)

window = webview.create_window(
    title="JARVIS — {_hotkey_label()}",
    url=f"{{URL}}/overlay",
    width=700, height=500,
    frameless=True,
    easy_drag=True,
    on_top=True,
    resizable=True,
    min_size=(400, 300),
)
webview.start(gui=None, debug=False)
print("Overlay closed.")
''')

    venv_python = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    if not venv_python.exists():
        venv_python = sys.executable

    try:
        subprocess.Popen(
            [str(venv_python), str(script)],
            cwd=str(PROJECT_ROOT),
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        print("⚡ Overlay launched")
    except Exception as exc:
        print(f"⚠️  Failed to launch overlay: {exc}")


# ── Main ──

def main():
    print("⚡ JARVIS Desktop — System Tray Mode")
    print(f"   Backend: {URL}")
    print(f"   Hotkey:  {_hotkey_label()}")
    print("   Right-click tray icon → Apri Jarvis / Analizza / Esci")
    print()

    # 1. Backend
    backend = BackendThread()
    backend.start()

    import httpx
    for _ in range(30):
        try:
            if httpx.get(f"{URL}/health", timeout=1).status_code == 200:
                print("✅ Backend ready")
                break
        except Exception:
            time.sleep(0.5)
    else:
        print("⚠️  Backend didn't start — continuing")

    # 2. Quit handler
    def quit_all():
        print("👋 Shutting down...")
        hotkey.stop()
        tray.stop()
        sys.exit(0)

    # 3. Calls for menu
    def open_main():
        launch_main_window()

    def open_overlay():
        launch_overlay()

    # 4. Tray
    tray = TrayIcon(open_main, open_overlay, quit_all)
    tray_thread = threading.Thread(target=tray.run, daemon=True, name="tray")
    tray_thread.start()

    # 5. Hotkey
    hotkey = HotkeyListener(open_overlay)
    hotkey_thread = threading.Thread(target=hotkey.run, daemon=True, name="hotkey")
    hotkey_thread.start()

    # 6. Keep alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        quit_all()


if __name__ == "__main__":
    sys.path.insert(0, str(PROJECT_ROOT))
    main()

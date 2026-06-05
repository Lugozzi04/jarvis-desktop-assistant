"""Jarvis Desktop Tray — system tray application with global hotkey and overlay.

ARCHITECTURE:
  Main thread  → webview.start() (GUI event loop — BLOCKS)
  Tray thread  → pystray icon + menu
  Hotkey thread → pynput global listener

All windows are pre-created BEFORE webview.start(). The overlay is
hidden initially and shown/hidden when the hotkey fires or tray menu is used.
The main window opens on tray "Apri" click.

Hotkey is configurable via the Settings UI and stored in data/hotkeys.json.
"""

from __future__ import annotations

import json
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


# ── Hotkey Config ──

class HotkeyConfig:
    """Thread-safe hotkey configuration persisted to disk."""

    def __init__(self):
        self._path = Path(PROJECT_ROOT) / "data" / "hotkeys.json"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._data = self._load()

    def _load(self) -> dict:
        try:
            if self._path.exists():
                return json.loads(self._path.read_text())
        except Exception:
            pass
        return {"modifiers": ["alt"], "key": "space"}

    def save(self, modifiers: list[str], key: str) -> None:
        with self._lock:
            self._data = {"modifiers": modifiers, "key": key}
            try:
                self._path.write_text(json.dumps(self._data, indent=2))
            except Exception:
                pass

    def get(self) -> dict:
        with self._lock:
            return dict(self._data)

    def to_pynput_combo(self) -> set:
        """Convert config to pynput key set for matching."""
        d = self.get()
        combo = set()
        for m in d.get("modifiers", []):
            m = m.lower()
            if m == "ctrl": combo.add("ctrl")
            elif m == "alt": combo.add("alt")
            elif m == "shift": combo.add("shift")
            elif m == "cmd" or m == "win": combo.add("cmd")
        combo.add(d.get("key", "space").lower())
        return combo

    def combo_label(self) -> str:
        d = self.get()
        mods = "+".join(m.capitalize() for m in d.get("modifiers", []))
        key = d.get("key", "space").capitalize()
        return f"{mods}+{key}" if mods else key


hotkey_config = HotkeyConfig()


# ── Backend Thread ──

class BackendThread(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True, name="jarvis-backend")
        self._server: uvicorn.Server | None = None

    def run(self):
        config = uvicorn.Config(
            "backend.main:app", host=HOST, port=PORT,
            log_level="warning", reload=False,
        )
        self._server = uvicorn.Server(config)
        self._server.run()

    def stop(self):
        if self._server:
            self._server.should_exit = True


# ── Tray Icon Thread ──

class TrayThread(threading.Thread):
    """System tray icon with menu."""

    def __init__(self, on_show_main, on_show_overlay, on_quit):
        super().__init__(daemon=True, name="jarvis-tray")
        self._on_show_main = on_show_main
        self._on_show_overlay = on_show_overlay
        self._on_quit = on_quit

    def run(self):
        try:
            import pystray
            from PIL import Image, ImageDraw

            icon_img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
            draw = ImageDraw.Draw(icon_img)
            draw.ellipse([4, 4, 60, 60], fill=(99, 102, 241))
            draw.text((22, 18), "J", fill=(255, 255, 255))

            menu = pystray.Menu(
                pystray.MenuItem("🖥️  Apri Jarvis", lambda: self._on_show_main()),
                pystray.MenuItem(f"⚡ {hotkey_config.combo_label()} — Analizza Schermo", lambda: self._on_show_overlay()),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("❌ Esci", lambda: self._on_quit()),
            )

            self._tray = pystray.Icon("jarvis", icon_img, "JARVIS Desktop Assistant", menu)
            self._tray.run()
        except ImportError:
            print("⚠️  pystray non installato")
        except Exception as exc:
            print(f"⚠️  Tray error: {exc}")

    def stop(self):
        try:
            if hasattr(self, '_tray'):
                self._tray.stop()
        except Exception:
            pass


# ── Hotkey Listener Thread ──

class HotkeyListener(threading.Thread):
    """Global hotkey listener using pynput."""

    def __init__(self, callback):
        super().__init__(daemon=True, name="jarvis-hotkey")
        self._callback = callback
        self._running = True
        self._pressed = set()

    def run(self):
        try:
            from pynput import keyboard

            # Map key names to our config format
            KEY_MAP = {
                keyboard.Key.ctrl_l: "ctrl", keyboard.Key.ctrl_r: "ctrl",
                keyboard.Key.alt_l: "alt", keyboard.Key.alt_r: "alt",
                keyboard.Key.shift_l: "shift", keyboard.Key.shift_r: "shift",
                keyboard.Key.cmd_l: "cmd", keyboard.Key.cmd_r: "cmd",
                keyboard.Key.space: "space",
                keyboard.Key.enter: "enter",
                keyboard.Key.esc: "escape",
                keyboard.Key.tab: "tab",
            }

            def on_press(key):
                if not self._running:
                    return False
                try:
                    name = KEY_MAP.get(key, None)
                    if name is None and hasattr(key, 'name'):
                        name = key.name
                    elif name is None and hasattr(key, 'char') and key.char:
                        name = key.char.lower()
                    if name:
                        self._pressed.add(name)

                    # Check against configured hotkey
                    target = hotkey_config.to_pynput_combo()
                    if self._pressed == target:
                        self._pressed.clear()
                        self._callback()
                except Exception:
                    pass

            def on_release(key):
                try:
                    name = KEY_MAP.get(key, None)
                    if name is None and hasattr(key, 'name'):
                        name = key.name
                    elif name is None and hasattr(key, 'char') and key.char:
                        name = key.char.lower()
                    if name:
                        self._pressed.discard(name)
                except Exception:
                    pass

            with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
                while self._running:
                    time.sleep(0.1)
                listener.stop()

        except ImportError:
            print("⚠️  pynput non installato — hotkey disabilitato")
        except Exception as exc:
            print(f"⚠️  Hotkey error: {exc}")

    def stop(self):
        self._running = False


# ── Main ──

def main():
    print("⚡ JARVIS Desktop — System Tray Mode")
    print(f"   Backend: {URL}")
    print(f"   Hotkey: {hotkey_config.combo_label()}")

    # ── Start backend ──
    backend = BackendThread()
    backend.start()

    # Wait for backend
    import httpx
    for _ in range(30):
        try:
            r = httpx.get(f"{URL}/health", timeout=1)
            if r.status_code == 200:
                print("✅ Backend ready")
                break
        except Exception:
            time.sleep(0.5)
    else:
        print("⚠️  Backend didn't start")

    # ── Pre-create windows (MUST be before webview.start()) ──
    
    # Main window (hidden, shown on tray click)
    main_window = webview.create_window(
        title="JARVIS Desktop Assistant",
        url=URL,
        width=1100, height=750,
        min_size=(800, 500),
        resizable=True,
        confirm_close=True,
        text_select=True,
    )
    main_window.hide()

    # Overlay window for hotkey (always on top, frameless)
    overlay_url = f"{URL}/overlay"
    overlay_window = webview.create_window(
        title="JARVIS — Analisi Schermo",
        url=overlay_url,
        width=700, height=500,
        min_size=(400, 300),
        frameless=True,
        easy_drag=True,
        on_top=True,
        resizable=True,
    )
    overlay_window.hide()

    # Hook: when overlay is closed, just hide it (don't destroy)
    def _on_overlay_closing():
        overlay_window.hide()
        return False  # Don't prevent closing, just hide

    # Store reference for the hotkey callback
    windows = {"main": main_window, "overlay": overlay_window}
    
    try:
        overlay_window.events.closing += _on_overlay_closing
    except Exception:
        pass  # Non-fatal if event binding fails

    # ── Callbacks ──

    def show_main():
        """Show main Jarvis window (from tray)."""
        try:
            windows["main"].show()
        except Exception:
            pass

    def toggle_overlay():
        """Show/hide the overlay (from hotkey or tray)."""
        try:
            win = windows["overlay"]
            # Showing from a non-GUI thread needs evaluate_js or webview.windows
            # pywebview handles cross-thread window ops via its internal queue
            win.show()
        except Exception as exc:
            print(f"⚠️  Overlay show error: {exc}")

    def do_quit():
        print("👋 Shutting down...")
        hotkey_thread.stop()
        tray_thread.stop()
        backend.stop()
        # Closing all windows stops webview event loop
        for w in windows.values():
            try:
                w.destroy()
            except Exception:
                pass

    # ── Start tray + hotkey in threads ──

    tray_thread = TrayThread(show_main, toggle_overlay, do_quit)
    tray_thread.start()
    print("🔔 System tray attivo")

    hotkey_thread = HotkeyListener(toggle_overlay)
    hotkey_thread.start()
    print(f"⌨️  Hotkey globale: {hotkey_config.combo_label()}")

    # ── Start webview GUI (BLOCKS until all windows closed) ──

    print("🖥️  GUI avviata — clicca l'icona nella tray o premi la scorciatoia")
    webview.start(gui=None, debug=False)

    print("✅ Jarvis chiuso.")


if __name__ == "__main__":
    sys.path.insert(0, str(PROJECT_ROOT))
    main()

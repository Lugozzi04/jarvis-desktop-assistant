"""Jarvis Desktop Tray — system tray application with global hotkey and overlay.

Runs in the system tray at startup. Provides:
- System tray icon with right-click menu (Open, Settings, Quit)
- Global hotkey (Alt+Space) — opens overlay anywhere
- Screen capture + OCR + AI analysis via overlay
- Backend API in background thread
- Can also open the main UI window
"""

from __future__ import annotations

import json
import sys
import threading
import time
import webbrowser
from pathlib import Path

import webview
import uvicorn

PROJECT_ROOT = Path(__file__).resolve().parent.parent
HOST = "127.0.0.1"
PORT = 8400
URL = f"http://{HOST}:{PORT}"

# ── Backend Thread ──

class BackendThread(threading.Thread):
    """Run FastAPI backend in a daemon thread."""

    def __init__(self):
        super().__init__(daemon=True, name="jarvis-backend")
        self._server: uvicorn.Server | None = None

    def run(self):
        config = uvicorn.Config(
            "backend.main:app",
            host=HOST,
            port=PORT,
            log_level="warning",
            reload=False,
        )
        self._server = uvicorn.Server(config)
        self._server.run()

    def stop(self):
        if self._server:
            self._server.should_exit = True


# ── Global Hotkey Thread ──

class HotkeyThread(threading.Thread):
    """Listen for global Alt+Space hotkey."""

    def __init__(self, callback):
        super().__init__(daemon=True, name="jarvis-hotkey")
        self.callback = callback
        self._running = True

    def run(self):
        try:
            from pynput import keyboard

            alt_pressed = False

            def on_press(key):
                nonlocal alt_pressed
                try:
                    if key == keyboard.Key.alt_l or key == keyboard.Key.alt_r:
                        alt_pressed = True
                    elif key == keyboard.Key.space and alt_pressed:
                        self.callback()
                except AttributeError:
                    pass

            def on_release(key):
                nonlocal alt_pressed
                try:
                    if key == keyboard.Key.alt_l or key == keyboard.Key.alt_r:
                        alt_pressed = False
                except AttributeError:
                    pass

            with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
                while self._running:
                    time.sleep(0.1)
                listener.stop()
        except ImportError:
            print("⚠️  pynput not installed — global hotkey disabled")
        except Exception as exc:
            print(f"⚠️  Hotkey error: {exc}")

    def stop(self):
        self._running = False


# ── Overlay Window ──

def create_overlay(url: str) -> webview.Window | None:
    """Create a frameless overlay window for quick AI queries."""
    try:
        overlay = webview.create_window(
            title="JARVIS — Alt+Spazio",
            url=url,
            width=700,
            height=500,
            frameless=True,
            easy_drag=True,
            on_top=True,
            resizable=True,
            min_size=(400, 300),
        )
        return overlay
    except Exception as exc:
        print(f"⚠️  Failed to create overlay: {exc}")
        return None


# ── Tray Icon ──

def create_tray_icon(
    on_open_main: callable,
    on_open_overlay: callable,
    on_quit: callable,
) -> object | None:
    """Create a system tray icon with menu.

    Returns the tray icon object, or None if pystray is not available.
    """
    try:
        import pystray
        from PIL import Image, ImageDraw

        # Create a simple icon (purple circle with "J")
        icon_img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(icon_img)
        draw.ellipse([4, 4, 60, 60], fill=(99, 102, 241))  # Indigo
        draw.text((22, 18), "J", fill=(255, 255, 255))

        menu = pystray.Menu(
            pystray.MenuItem("Apri Jarvis", lambda: on_open_main()),
            pystray.MenuItem("Alt+Spazio (Analizza Schermo)", lambda: on_open_overlay()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Esci", lambda: on_quit()),
        )

        tray = pystray.Icon(
            "jarvis",
            icon_img,
            "JARVIS Desktop Assistant",
            menu,
        )
        return tray
    except ImportError:
        print("⚠️  pystray not installed — system tray disabled")
        return None
    except Exception as exc:
        print(f"⚠️  Failed to create tray icon: {exc}")
        return None


# ── Main ──

def main():
    """Start Jarvis in system tray mode."""
    print("⚡ JARVIS Desktop — System Tray Mode")
    print(f"   Backend: {URL}")
    print("   Hotkey: Alt+Spazio (analyze screen)")
    print("   Right-click tray icon for menu")

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
        print("⚠️  Backend didn't start — continuing anyway")

    # ── Overlay URL ──
    overlay_url = f"{URL}/overlay"

    # ── State ──
    main_window: webview.Window | None = None
    overlay_window: webview.Window | None = None

    def open_main():
        nonlocal main_window
        try:
            if main_window is None:
                main_window = webview.create_window(
                    title="JARVIS Desktop Assistant",
                    url=URL,
                    width=1100,
                    height=750,
                    min_size=(800, 500),
                    resizable=True,
                    confirm_close=True,
                    text_select=True,
                )
            webview.start(gui=None, debug=False)
        except Exception as exc:
            print(f"⚠️  Main window error: {exc}")

    def open_overlay():
        nonlocal overlay_window
        try:
            overlay = create_overlay(overlay_url)
            if overlay:
                overlay_window = overlay
                # The overlay runs in the same webview event loop
        except Exception as exc:
            print(f"⚠️  Overlay error: {exc}")

    def on_quit():
        print("👋 Shutting down...")
        if hotkey:
            hotkey.stop()
        backend.stop()
        sys.exit(0)

    # ── Start hotkey listener ──
    hotkey = HotkeyThread(open_overlay)
    hotkey.start()

    # ── Start tray icon ──
    tray = create_tray_icon(open_main, open_overlay, on_quit)

    if tray:
        # Run tray in separate thread
        tray_thread = threading.Thread(target=tray.run, daemon=True, name="jarvis-tray")
        tray_thread.start()
        print("🔔 System tray icon active")
    else:
        print("⚠️  No system tray — start.ps1 mode (windowed)")
        # Fallback: open main window directly
        open_main()

    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        on_quit()


if __name__ == "__main__":
    sys.path.insert(0, str(PROJECT_ROOT))
    main()

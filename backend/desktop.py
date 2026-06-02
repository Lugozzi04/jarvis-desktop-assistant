"""Jarvis Desktop Launcher — opens a native window using pywebview.

No Electron, no npm, no browser. Uses the OS-native webview:
  - Windows 10/11: Edge WebView2 (pre-installed)
  - macOS: WKWebView
  - Linux: GTK WebKit (apt install python3-pyqt5.qtwebengine)

The FastAPI backend runs in a background thread and shuts down
automatically when the window closes.
"""

from __future__ import annotations

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
    backend.stop()
    print("✅ Jarvis exited.")


if __name__ == "__main__":
    sys.path.insert(0, str(PROJECT_ROOT))
    main()

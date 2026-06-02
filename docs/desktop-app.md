# Jarvis Desktop App (Electron Wrapper)

The Electron desktop wrapper gives Jarvis a native window experience on Linux, macOS, and Windows — complete with its own window chrome, tray behavior (macOS), and isolated rendering.

The Electron layer is thin by design: it wraps the existing Vite/React frontend and leaves the Python backend (FastAPI on `localhost:8400`) untouched. The renderer talks to the backend over HTTP exactly as the browser version does.

---

## System Requirements

| Requirement | Minimum Version |
|---|---|
| Node.js | 18+ |
| npm | 9+ (bundled with Node) |
| Operating System | Linux, macOS (Intel/Apple Silicon), or Windows 10/11 |

Optional dependencies (installed automatically via `optionalDependencies`):

- **electron** `^35.0.0` — the desktop shell
- **electron-builder** `^25.0.0` — production packaging
- **concurrently** `^9.0.0` — runs Vite + Electron side-by-side
- **wait-on** `^8.0.0` — waits for Vite before launching Electron

> **Note:** The backend (Python/FastAPI) is a separate process and must be started independently. See [Limitations](#limitations).

---

## NPM Scripts

All scripts are run from the `frontend/` directory (`cd frontend` first).

### `npm run desktop:dev`

```bash
npm run desktop:dev
```

Full development mode — starts both Vite and Electron in one command. Under the hood it uses `concurrently` to run two processes:

1. `vite` — launches the Vite dev server on `http://localhost:5173`
2. `wait-on http://localhost:5173 && electron .` — waits for Vite to be ready, then opens the Electron window pointing at the dev server

Hot Module Replacement (HMR) works — edits to React components update instantly in the Electron window. DevTools open detached for debugging.

### `npm run electron:dev`

```bash
npm run electron:dev
```

Electron-only launch. Starts the Electron window immediately (no `wait-on`). Use this when you already have Vite running separately (e.g., via `npm run dev` in another terminal). If Vite isn't running, the Electron window will show a connection error.

### `npm run desktop:build`

```bash
npm run desktop:build
```

Production build pipeline. Two phases:

1. **`npm run build`** — TypeScript compilation (`tsc -b`) followed by `vite build`. Produces static assets in `frontend/dist/`.
2. **`electron-builder`** — packages the Electron app using `electron-builder`. Configuration is in the `"build"` key of `package.json` (or an `electron-builder.yml` file).

The output is a platform-specific distributable: `.dmg`/`.app` on macOS, `.AppImage`/`.deb`/`.snap` on Linux, `.exe`/NSIS installer on Windows.

---

## Architecture

### `electron/main.js` — Main Process

The main process is the entry point (`"main": "electron/main.js"` in `package.json`). It handles:

**Dev vs. Production Detection**

```js
const isDev = process.env.NODE_ENV !== 'production' || !app.isPackaged;
```

In dev: loads `http://localhost:5173` (the Vite dev server) and opens DevTools detached.
In production: loads `frontend/dist/index.html` from the filesystem (the Vite build output).

**BrowserWindow Configuration**

- Title: `Jarvis Desktop Assistant`
- Default size: 1280×860, minimum 900×600
- Dark background: `#0d1117` (matches the app's dark theme, avoids white flash)
- `contextIsolation: true` — renderer cannot access Node.js APIs directly
- `nodeIntegration: false` — no `require()` in the renderer
- Preload script bridges the gap (see below)

**External Link Handling**

```js
mainWindow.webContents.setWindowOpenHandler(({ url }) => {
  shell.openExternal(url);
  return { action: 'deny' };
});
```

All external URLs open in the system's default browser instead of within the Electron window.

**macOS Lifecycle**

- `window-all-closed` does NOT quit on macOS (`darwin`) — the app stays in the dock (standard macOS behavior)
- `activate` recreates the window if the dock icon is clicked with no windows open

### `electron/preload.js` — Security Bridge

```js
contextBridge.exposeInMainWorld('jarvisDesktop', {
  platform: process.platform,
  isElectron: true,
  version: '0.3.0',
});
```

The preload script exposes a minimal, read-only API object (`window.jarvisDesktop`) to the renderer. This lets the React frontend:

- Detect it's running inside Electron (`isElectron: true`)
- Adapt UI behavior per platform (`platform`: `darwin`, `linux`, or `win32`)
- Show version info

Because `contextIsolation` is on and `nodeIntegration` is off, the renderer has no access to Node.js, `fs`, `child_process`, or any Electron internals. The preload is the only bridge — nothing else leaks through.

---

## How It Works Per OS

### Linux

- Window frame uses the system's native window manager (GNOME, KDE, Xfce, etc.)
- `.desktop` file available at `packaging/linux/jarvis-desktop.desktop` for launcher integration
- Systemd service unit at `packaging/linux/jarvis-backend.service` for auto-starting the backend
- Dev start script: `scripts/dev_start_linux.sh`

### macOS

- Standard macOS window chrome with traffic-light buttons
- App stays in the dock after all windows close (standard macOS convention)
- Dock icon reactivates the window via the `activate` event handler
- Property list for bundling: `packaging/macos/com.jarvis.desktop.plist`
- Dev start script: `scripts/dev_start_macos.sh`

### Windows

- Native Windows title bar and window controls
- PowerShell start script: `packaging/windows/start_jarvis.ps1`
- Dev start script: `scripts/dev_start_windows.ps1`

In all cases the renderer is the same React app. Platform-specific differences are handled at the Electron main-process level (window behavior, lifecycle) and through `window.jarvisDesktop.platform` in the renderer.

---

## Limitations

### Backend Must Be Started Separately

The Electron app is a **frontend-only wrapper**. The Python backend (FastAPI on `localhost:8400`) is not bundled, managed, or spawned by Electron. You must start it independently before the app is functional:

```bash
# Example: start the backend manually
cd /path/to/jarvis-desktop-assistant
source .venv/bin/activate
uvicorn backend.main:app --host 127.0.0.1 --port 8400 --reload
```

The frontend detects backend availability at runtime — if the backend is down, API calls fail gracefully and the UI shows connection errors. There is no Electron-side process management or health-check logic for the backend.

### No System Tray (Yet)

There is currently no system tray icon or minimize-to-tray behavior. The window lives as a normal application window.

### No Auto-Start

The app does not register itself for auto-start on login. Users can manually configure this via their OS (Startup folder on Windows, Login Items on macOS, autostart on Linux).

### Dev-Only Dependencies

`electron`, `electron-builder`, `concurrently`, and `wait-on` are declared as `optionalDependencies`. This means `npm install --no-optional` (or environments where Electron can't build) will skip them without error — the web-only `npm run dev` / `npm run build` workflows are unaffected.

---

## Future Plans

### Tauri Alternative

We are evaluating [Tauri](https://tauri.app/) as a lighter-weight alternative to Electron. Key motivations:

- **Smaller bundle size** — Tauri apps are typically 5–10 MB vs 150+ MB for Electron
- **Lower memory usage** — Tauri uses the OS-native WebView instead of bundling Chromium
- **Rust backend** — opens the possibility of moving performance-critical or security-sensitive logic out of Python and into a Rust core

A Tauri migration would involve wrapping the existing React frontend in a Rust shell, similar to how Electron wraps it today. The Python backend would still run separately in the near term; longer-term, Rust could take over some backend responsibilities.

### Bundling the Backend

Currently the backend is a completely separate process. Plans to streamline this:

- **Electron `child_process`** — Electron could spawn `uvicorn` as a child process on app launch and kill it on quit. This adds complexity (managing Python venvs, port conflicts, cross-platform edge cases) but would make the app feel like a single unit.
- **Tauri sidecar** — Tauri has first-class support for sidecar processes. The Python backend could be bundled as a sidecar, automatically started and stopped with the app.
- **PyOxidizer / PyInstaller** — the backend could be packaged as a standalone binary and shipped alongside the desktop app.

Each approach has trade-offs in bundle size, startup time, and maintenance burden. The current priority is stabilizing the Electron wrapper; backend bundling will be revisited once the core desktop experience is solid.

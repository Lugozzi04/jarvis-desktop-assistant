// Jarvis Desktop Assistant — Electron main process (v2)
// Portable desktop mode: manages backend, shows loading screen, loads frontend.
// Dev mode: connects to Vite dev server at http://localhost:5173
// Portable mode: loads built frontend from dist/, starts/checks backend

const { app, BrowserWindow, shell, ipcMain, dialog } = require('electron');
const path = require('path');
const { BackendManager } = require('./backendManager');

const isDev = process.env.NODE_ENV === 'development' || process.argv.includes('--dev');
const DEV_URL = 'http://localhost:5173';
const BACKEND_PORT = 8400;
const BACKEND_HOST = '127.0.0.1';

let mainWindow = null;
let loadingWindow = null;
let backendManager = null;
let backendReady = false;

// ── Loading Window ──

function createLoadingWindow() {
  loadingWindow = new BrowserWindow({
    width: 500,
    height: 380,
    frame: false,
    transparent: false,
    resizable: false,
    backgroundColor: '#0d1117',
    center: true,
    show: false,
  });

  const html = `
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      background: #0d1117;
      color: #c9d1d9;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 100vh;
      padding: 30px;
      user-select: none;
      -webkit-app-region: drag;
    }
    .icon { font-size: 48px; margin-bottom: 16px; }
    .title { font-size: 20px; font-weight: 700; margin-bottom: 8px; }
    .subtitle { font-size: 13px; color: #8b949e; margin-bottom: 24px; }
    .spinner {
      width: 36px; height: 36px;
      border: 3px solid #30363d;
      border-top-color: #58a6ff;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
      margin-bottom: 16px;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
    .status { font-size: 13px; color: #8b949e; text-align: center; }
    .log { font-size: 11px; color: #6e7681; margin-top: 12px; max-height: 80px; overflow: hidden; text-align: center; }
  </style>
</head>
<body>
  <div class="icon">⚡</div>
  <div class="title">JARVIS</div>
  <div class="subtitle">Desktop Assistant</div>
  <div class="spinner"></div>
  <div class="status" id="status">Starting services...</div>
  <div class="log" id="log"></div>
  <script>
    const { ipcRenderer } = require('electron');
    ipcRenderer.on('loading-status', (_, msg) => {
      document.getElementById('status').textContent = msg;
    });
    ipcRenderer.on('loading-log', (_, msg) => {
      const el = document.getElementById('log');
      el.textContent = msg;
    });
  </script>
</body>
</html>`;

  loadingWindow.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(html)}`);
  loadingWindow.once('ready-to-show', () => {
    loadingWindow.show();
  });
}

function closeLoadingWindow() {
  if (loadingWindow && !loadingWindow.isDestroyed()) {
    loadingWindow.close();
    loadingWindow = null;
  }
}

function updateLoadingStatus(msg) {
  if (loadingWindow && !loadingWindow.isDestroyed()) {
    loadingWindow.webContents.send('loading-status', msg);
  }
}

function updateLoadingLog(msg) {
  if (loadingWindow && !loadingWindow.isDestroyed()) {
    loadingWindow.webContents.send('loading-log', msg);
  }
}

// ── Error Window ──

function showErrorWindow(errorMsg, logs) {
  closeLoadingWindow();

  const errorWin = new BrowserWindow({
    width: 600,
    height: 500,
    title: 'Jarvis — Startup Error',
    backgroundColor: '#0d1117',
    webPreferences: { nodeIntegration: true, contextIsolation: false },
  });

  const logsHtml = (logs || []).slice(-20).map(l => `<div class="log-line">${escapeHtml(l)}</div>`).join('');

  const html = `
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { background: #0d1117; color: #c9d1d9; font-family: -apple-system, BlinkMacSystemFont, sans-serif; padding: 24px; }
    h2 { color: #f85149; margin-bottom: 12px; }
    .error-box { background: #161b22; border: 1px solid #f85149; border-radius: 8px; padding: 16px; margin-bottom: 16px; font-size: 14px; }
    .actions { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 16px; }
    button { padding: 8px 16px; border-radius: 6px; border: 1px solid #30363d; background: #21262d; color: #c9d1d9; cursor: pointer; font-size: 13px; }
    button:hover { background: #30363d; }
    button.primary { background: #238636; border-color: #238636; color: #fff; }
    button.primary:hover { background: #2ea043; }
    .logs { background: #161b22; border-radius: 8px; padding: 12px; max-height: 200px; overflow-y: auto; font-family: monospace; font-size: 11px; color: #8b949e; }
    .log-line { padding: 2px 0; white-space: pre-wrap; word-break: break-all; }
    details { margin-top: 12px; }
    summary { cursor: pointer; color: #58a6ff; font-size: 13px; }
    .tip { font-size: 12px; color: #8b949e; margin-top: 12px; line-height: 1.6; }
  </style>
</head>
<body>
  <h2>⛔ Jarvis Could Not Start</h2>
  <div class="error-box">${escapeHtml(errorMsg)}</div>

  <div class="actions">
    <button class="primary" onclick="require('electron').ipcRenderer.send('retry-startup')">🔄 Retry</button>
    <button onclick="require('electron').ipcRenderer.send('run-check')">🔍 Run Environment Check</button>
    <button onclick="require('electron').ipcRenderer.send('copy-diagnostics')">📋 Copy Diagnostics</button>
    <button onclick="require('electron').ipcRenderer.send('quit-app')">✕ Quit</button>
  </div>

  <details>
    <summary>📋 Logs</summary>
    <div class="logs">${logsHtml || '<div class="log-line">No logs available.</div>'}</div>
  </details>

  <div class="tip">
    <strong>Troubleshooting:</strong>
    <br>• Run <code>scripts/setup_local_*.sh</code> to install dependencies
    <br>• Check that port ${BACKEND_PORT} is not in use
    <br>• Make sure Python 3.10+ and Node.js 18+ are installed
    <br>• Run <code>python scripts/check_environment.py</code> for detailed diagnostics
  </div>
</body>
</html>`;

  errorWin.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(html)}`);

  ipcMain.on('retry-startup', () => {
    if (errorWin && !errorWin.isDestroyed()) errorWin.close();
    startup();
  });
  ipcMain.on('run-check', async () => {
    if (errorWin && !errorWin.isDestroyed()) errorWin.close();
    await runEnvironmentCheck();
  });
  ipcMain.on('copy-diagnostics', () => {
    const diag = `Error: ${errorMsg}\n\nLogs:\n${(logs || []).join('\n')}`;
    require('electron').clipboard.writeText(diag);
    if (errorWin && !errorWin.isDestroyed()) {
      errorWin.webContents.executeJavaScript('alert("Diagnostics copied to clipboard.")');
    }
  });
  ipcMain.on('quit-app', () => app.quit());
}

function escapeHtml(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// ── Main Window ──

function createMainWindow() {
  const preloadPath = path.join(__dirname, 'preload.js');

  mainWindow = new BrowserWindow({
    title: 'Jarvis Desktop Assistant',
    width: 1280,
    height: 860,
    minWidth: 900,
    minHeight: 600,
    backgroundColor: '#0d1117',
    show: false,
    webPreferences: {
      preload: preloadPath,
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });

  if (isDev) {
    console.log(`[Jarvis] Dev mode — loading ${DEV_URL}`);
    mainWindow.loadURL(DEV_URL);
    mainWindow.webContents.openDevTools({ mode: 'detach' });
  } else {
    const distPath = path.join(__dirname, '..', 'dist', 'index.html');
    console.log(`[Jarvis] Portable mode — loading ${distPath}`);
    mainWindow.loadFile(distPath);
  }

  mainWindow.once('ready-to-show', () => {
    closeLoadingWindow();
    mainWindow.show();
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  // Pass backend status to renderer
  ipcMain.handle('get-backend-status', async () => {
    if (!backendManager) return { online: false };
    const health = await backendManager.checkHealth();
    return {
      online: health.online,
      managerStatus: backendManager.status,
      startedByManager: backendManager.startedByUs,
    };
  });
}

// ── Environment Check ──

async function runEnvironmentCheck() {
  // Create a window showing check results
  const checkWin = new BrowserWindow({
    width: 700,
    height: 550,
    title: 'Jarvis — Environment Check',
    backgroundColor: '#0d1117',
    webPreferences: { nodeIntegration: true, contextIsolation: false },
  });

  let output = 'Running environment check...';
  try {
    const checkScript = path.join(backendManager.projectDir, 'scripts', 'check_environment.py');
    const pythonCmd = backendManager._resolveCommand()?.command || 'python3';
    const { execSync } = require('child_process');

    try {
      output = execSync(`${pythonCmd} ${checkScript}`, {
        cwd: backendManager.projectDir,
        timeout: 15000,
        stdio: 'pipe',
      }).toString();
    } catch (e) {
      output = `Check failed:\n${e.stdout?.toString() || ''}\n${e.stderr?.toString() || e.message}`;
    }
  } catch (e) {
    output = `Could not run check: ${e.message}`;
  }

  const html = `
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>
    body { background: #0d1117; color: #c9d1d9; font-family: monospace; padding: 20px; white-space: pre-wrap; font-size: 13px; line-height: 1.5; }
    button { padding: 8px 16px; margin-top: 16px; border-radius: 6px; border: 1px solid #30363d; background: #21262d; color: #c9d1d9; cursor: pointer; }
    button:hover { background: #30363d; }
  </style>
</head>
<body>
  <h2>🔍 Environment Check</h2>
  <div>${escapeHtml(output)}</div>
  <button onclick="require('electron').clipboard.writeText(document.querySelector('div').textContent);alert('Copied!')">📋 Copy</button>
  <button onclick="window.close()">✕ Close</button>
</body>
</html>`;

  checkWin.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(html)}`);
}

// ── Startup Sequence ──

async function startup() {
  createLoadingWindow();
  updateLoadingStatus('Initializing...');

  const projectDir = path.join(__dirname, '..', '..');
  backendManager = new BackendManager(projectDir);

  updateLoadingStatus('Checking backend...');

  const result = await backendManager.ensureRunning();

  if (!result.success) {
    updateLoadingStatus('Backend failed to start');
    showErrorWindow(result.error, backendManager.getLogs());
    return;
  }

  backendReady = true;
  updateLoadingStatus('Backend ready — loading Jarvis...');
  createMainWindow();
}

// ── App Lifecycle ──

app.whenReady().then(startup);

app.on('window-all-closed', async () => {
  if (backendManager && backendManager.startedByUs) {
    await backendManager.stop();
  }
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', async () => {
  if (backendManager && backendManager.startedByUs) {
    await backendManager.stop();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    if (backendReady) {
      createMainWindow();
    } else {
      startup();
    }
  }
});

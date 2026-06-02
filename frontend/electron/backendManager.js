// Jarvis Backend Manager — manages the Python FastAPI backend lifecycle
// Handles: health checks, start, stop, restart, log collection
// Works cross-platform: Linux, macOS, Windows

const { spawn, execSync } = require('child_process');
const path = require('path');
const http = require('http');
const fs = require('fs');

const BACKEND_PORT = 8400;
const BACKEND_HOST = '127.0.0.1';
const HEALTH_URL = `http://${BACKEND_HOST}:${BACKEND_PORT}/health`;
const STARTUP_TIMEOUT_MS = 30000;
const HEALTH_CHECK_INTERVAL_MS = 1000;

class BackendManager {
  constructor(projectDir) {
    this.projectDir = projectDir || path.join(__dirname, '..', '..');
    this.process = null;
    this.startedByUs = false;
    this.logs = [];
    this.status = 'unknown'; // unknown | starting | running | stopped | error
    this.lastError = null;
  }

  // ── Public API ──

  async checkHealth() {
    return new Promise((resolve) => {
      const req = http.get(HEALTH_URL, { timeout: 3000 }, (res) => {
        let data = '';
        res.on('data', (chunk) => (data += chunk));
        res.on('end', () => {
          try {
            const json = JSON.parse(data);
            resolve({ online: true, status: json.status, version: json.version, data: json });
          } catch {
            resolve({ online: true, status: 'ok', version: 'unknown' });
          }
        });
      });
      req.on('error', () => resolve({ online: false, status: 'offline' }));
      req.on('timeout', () => { req.destroy(); resolve({ online: false, status: 'timeout' }); });
    });
  }

  async waitForReady(timeoutMs = STARTUP_TIMEOUT_MS) {
    const start = Date.now();
    while (Date.now() - start < timeoutMs) {
      const health = await this.checkHealth();
      if (health.online) {
        this.log(`Backend ready in ${Date.now() - start}ms (v${health.version})`);
        this.status = 'running';
        return true;
      }
      await this._sleep(HEALTH_CHECK_INTERVAL_MS);
    }
    const health = await this.checkHealth();
    if (health.online) {
      this.status = 'running';
      return true;
    }
    this.status = 'error';
    this.lastError = `Backend did not start within ${timeoutMs / 1000}s`;
    return false;
  }

  async ensureRunning() {
    this.log('Checking backend...');
    const health = await this.checkHealth();
    if (health.online) {
      this.log('Backend already running');
      this.status = 'running';
      this.startedByUs = false;
      return { success: true, alreadyRunning: true };
    }

    this.log('Starting backend...');
    const result = await this.start();
    if (!result.success) {
      return result;
    }

    this.startedByUs = true;
    const ready = await this.waitForReady();
    if (!ready) {
      return { success: false, error: this.lastError, logs: this.logs };
    }

    return { success: true, alreadyRunning: false };
  }

  async start() {
    if (this.process) {
      return { success: false, error: 'Backend is already starting or running' };
    }

    this.status = 'starting';
    this.logs = [];

    const cmd = this._resolveCommand();
    if (!cmd) {
      this.status = 'error';
      this.lastError = 'Could not find Python or venv. Run setup script first.';
      return { success: false, error: this.lastError };
    }

    this.log(`Command: ${cmd.command} ${cmd.args.join(' ')}`);
    this.log(`Project: ${this.projectDir}`);

    try {
      this.process = spawn(cmd.command, cmd.args, {
        cwd: this.projectDir,
        env: { ...process.env, ...cmd.env },
        stdio: ['ignore', 'pipe', 'pipe'],
        windowsHide: true,
      });

      this.process.stdout.on('data', (data) => {
        const lines = data.toString().trim().split('\n');
        lines.forEach((l) => {
          if (l) this.logs.push(`[out] ${l}`);
        });
      });

      this.process.stderr.on('data', (data) => {
        const lines = data.toString().trim().split('\n');
        lines.forEach((l) => {
          if (l) this.logs.push(`[err] ${l}`);
        });
      });

      this.process.on('error', (err) => {
        this.logs.push(`[error] ${err.message}`);
        this.lastError = err.message;
        this.status = 'error';
      });

      this.process.on('close', (code) => {
        this.logs.push(`[exit] Backend exited with code ${code}`);
        if (this.startedByUs) {
          this.status = 'stopped';
        }
        this.process = null;
      });

      return { success: true };
    } catch (err) {
      this.status = 'error';
      this.lastError = err.message;
      return { success: false, error: err.message };
    }
  }

  async stop() {
    if (!this.process || !this.startedByUs) {
      this.log('Backend was not started by us — not stopping');
      this.process = null;
      return;
    }

    this.log('Stopping backend...');
    try {
      if (process.platform === 'win32') {
        spawn('taskkill', ['/pid', this.process.pid.toString(), '/f', '/t']);
      } else {
        this.process.kill('SIGTERM');
        await this._sleep(2000);
        if (this.process) {
          this.process.kill('SIGKILL');
        }
      }
    } catch (err) {
      this.log(`Stop error: ${err.message}`);
    }

    this.process = null;
    this.status = 'stopped';
    this.startedByUs = false;
    this.log('Backend stopped');
  }

  getLogs(maxLines = 100) {
    return this.logs.slice(-maxLines);
  }

  log(msg) {
    const ts = new Date().toISOString().slice(11, 19);
    this.logs.push(`[${ts}] ${msg}`);
    console.log(`[BackendManager] ${msg}`);
  }

  // ── Private ──

  _resolveCommand() {
    const isWindows = process.platform === 'win32';

    // Detect venv
    const venvDir = isWindows
      ? path.join(this.projectDir, '.venv', 'Scripts')
      : path.join(this.projectDir, '.venv', 'bin');
    const pythonExe = isWindows ? 'python.exe' : 'python';
    const venvPython = path.join(venvDir, pythonExe);

    if (fs.existsSync(venvPython)) {
      this.log(`Using venv: ${venvPython}`);
      return {
        command: venvPython,
        args: ['-m', 'uvicorn', 'backend.main:app', '--host', BACKEND_HOST, '--port', String(BACKEND_PORT)],
        env: {
          VIRTUAL_ENV: path.join(this.projectDir, '.venv'),
          PATH: `${path.dirname(venvPython)}${path.delimiter}${process.env.PATH || ''}`,
        },
      };
    }

    // Fallback: system Python
    const systemPython = this._findSystemPython(isWindows);
    if (systemPython) {
      this.log(`Using system Python: ${systemPython}`);
      return {
        command: systemPython,
        args: ['-m', 'uvicorn', 'backend.main:app', '--host', BACKEND_HOST, '--port', String(BACKEND_PORT)],
        env: {},
      };
    }

    return null;
  }

  _findSystemPython(isWindows) {
    const candidates = isWindows
      ? ['python', 'python3', 'py']
      : ['python3', 'python'];

    for (const cmd of candidates) {
      try {
        const result = execSync(`${cmd} --version`, { stdio: 'pipe', timeout: 3000 });
        const version = result.toString().trim();
        if (version.includes('Python 3')) {
          return cmd;
        }
      } catch {
        // not found
      }
    }
    return null;
  }

  _sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
}

module.exports = { BackendManager };

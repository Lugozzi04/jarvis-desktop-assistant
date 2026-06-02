# Security Model

Jarvis Desktop Assistant is designed to be **local-first and security-conscious**. This document covers the security architecture: risk levels, the pending actions queue, permissions integration, secret handling, and a review checklist.

---

## Risk Levels

Every action in Jarvis is classified into one of three risk levels. This classification is enforced by the `PermissionGuard` before any action executes.

| Risk Level | Behavior | Examples |
|---|---|---|
| `safe` | **Auto-approved** — no user interaction needed | Open app, open URL, set timer, search, system stats, read file |
| `confirmation` | **User must confirm** via UI click | Close app, move/rename file, execute script, send message |
| `dangerous` | **Strong explicit confirmation** — user must type `CONFIRM EXECUTE` | Delete files, shutdown system, arbitrary shell commands, system modifications |

### How Risk Is Enforced

```python
from backend.core.permissions import permission_guard
from backend.core.schemas import RiskLevel

result = permission_guard.check(RiskLevel.dangerous, "Delete /home/user/important-file.txt")
# Returns:
# {
#   "allowed": True,
#   "needs_confirmation": True,
#   "confirmation_message": "🚨 DANGEROUS ACTION — REQUIRES EXPLICIT CONFIRMATION\n\nAction: Delete /home/user/important-file.txt\n\nTo proceed, type: CONFIRM EXECUTE",
#   "reason": "Dangerous action — strong confirmation required",
# }
```

Safe actions return `needs_confirmation: False` and proceed immediately.

### Configuring Risk Behavior

All security settings are in `.env`:

```env
SECURITY_CONFIRM_DANGEROUS_ACTIONS=true   # Enable/disable confirmation for confirmation-level actions
SECURITY_AUTO_APPROVE_SAFE=true           # Auto-approve safe actions
SECURITY_MAX_SHELL_TIMEOUT=30             # Max seconds for shell commands
```

In development, you can disable confirmations per risk level. **Never disable in production.**

---

## Pending Actions Queue

Dangerous actions are placed in the **Pending Actions Queue** — a security gate that requires explicit user approval before execution.

### How It Works

1. A skill registers an action with `risk: "dangerous"` or `risk: "confirmation"`
2. The `PermissionGuard` checks the risk level and sets `needs_confirmation: true`
3. The action is added to the `PendingActionsQueue` with status `pending`
4. The user sees the pending action in the UI and must click **Approve**
5. Upon approval, the status changes to `approved` and the action executes
6. If rejected, the action is discarded with status `rejected`
7. If unresolved for 60 minutes (configurable), the action **auto-expires** (auto-rejected)

### Pending Action Data Model

Each pending action stores:

| Field | Description |
|---|---|
| `id` | Unique ID (e.g., `pa_1717363200000`) |
| `skill` | Skill name (e.g., `filesystem`, `system`) |
| `action` | Action name (e.g., `delete`, `shutdown`) |
| `parameters` | Action parameters |
| `risk` | `confirmation` or `dangerous` |
| `reason` | Human-readable explanation |
| `source` | `user`, `automation`, or `workflow` |
| `status` | `pending`, `approved`, `rejected`, or `expired` |
| `timeout_minutes` | Auto-reject after this many minutes (default: 60) |

### API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/pending-actions` | List all pending actions |
| `GET` | `/api/pending-actions/count` | Get count of pending actions |
| `GET` | `/api/pending-actions/{id}` | Get a specific action |
| `POST` | `/api/pending-actions/{id}/approve?execute=true` | Approve (and optionally execute) |
| `POST` | `/api/pending-actions/{id}/reject` | Reject an action |
| `POST` | `/api/pending-actions/clear-resolved` | Clean up old resolved actions |

### Persistence

Pending actions are persisted to `data/pending_actions.json` so they survive restarts. Only actions with status `pending` are restored on startup — resolved actions are loaded but not re-queued.

---

## Permissions Integration

The `PermissionGuard` integrates with every execution path in Jarvis:

### 1. Assistant Pipeline

```
User Input → Intent Parser → Router → PermissionGuard.check() → Execute or Queue
```

If `needs_confirmation` is `true`, the action goes to the pending queue instead of executing immediately. The response to the user includes `confirmation_required: true` and a `confirmation_message`.

### 2. Workflow Engine

Workflows execute multiple steps. Before each step, the `PermissionGuard` checks risk. If any step requires confirmation, the entire workflow pauses and waits for user approval.

### 3. Automation Engine

Automations can trigger actions without direct user interaction. Actions from automations:
- Are always run through `PermissionGuard`
- Have `source: "automation"` for audit trail
- Safe automations (timers, reminders) auto-approve
- Dangerous automations require prior confirmation setup

### 4. Command Execution

Shell commands are classified as `dangerous` by default. They:
- Run through `PermissionGuard.check(RiskLevel.dangerous, ...)`
- Are subject to `SECURITY_MAX_SHELL_TIMEOUT` (default 30 seconds)
- Are sandboxed — no interactive prompts, no `sudo` without explicit approval
- Are logged to the audit trail

---

## No Secrets in Frontend

The frontend (React + Electron) is a **public-facing client**. It must never contain:

- API keys (`LLM_API_KEY`, OpenAI keys, etc.)
- Database credentials (`DATABASE_URL`)
- Internal service URLs beyond `localhost`
- Authentication tokens
- Any value from `.env` that is not explicitly public

### What the Frontend CAN Access

The backend exposes a **public config endpoint** that strips secrets:

```bash
curl http://127.0.0.1:8400/api/config/public
```

```json
{
  "version": "0.3.0",
  "env": "development",
  "llm_provider": "ollama",
  "llm_model": "qwen2.5:7b",
  "allow_cloud": false,
  "embedding_provider": "simple",
  "voice_enabled": false
}
```

No `LLM_API_KEY`, no `DATABASE_URL`, no secrets — ever.

### Diagnostics API Also Strips Secrets

```bash
curl http://127.0.0.1:8400/api/diagnostics
# llm_status excludes api_key
```

### Electron Security

The Electron wrapper enforces:
- `contextIsolation: true` — renderer cannot access Node.js APIs
- `nodeIntegration: false` — no `require()` in renderer
- Preload script exposes only a read-only `window.jarvisDesktop` object (platform, version, Electron detection)
- External links open in the system browser, not in the Electron window

---

## Local-Only by Default

Jarvis is designed to run **entirely on your machine**.

| Component | Default Behavior |
|---|---|
| LLM | Local via Ollama (`localhost:11434`). Cloud LLM is **opt-in** (`LLM_ALLOW_CLOUD=false` by default). |
| Voice | Local via Faster-Whisper. Audio never leaves the device. |
| Document Memory | Local indexing. Embeddings processed locally. |
| Database | SQLite stored in `data/` directory. |
| Backend API | Bound to `127.0.0.1:8400` — loopback only, not exposed to network. |
| Frontend | Served from `localhost:5173` (dev) or from local files (Electron). |

### CORS

The backend only allows CORS from configured origins:

```env
UI_CORS_ORIGINS=http://localhost:5173,http://localhost:8400
```

No wildcard origins in production.

### Binding to Network Interfaces

If you need to access Jarvis from another device on your network:
1. Change `UI_HOST` to `0.0.0.0` in `.env`
2. Add the remote origin to `UI_CORS_ORIGINS`
3. **Understand the security implications** — anyone on your network can access the API

**Not recommended** unless behind a firewall/VPN.

---

## API Key Storage (`.env` Only)

All secrets are stored in the `.env` file at the project root and loaded via `pydantic-settings`.

### .env File

```
JARVIS_ENV=development
LLM_API_KEY=sk-...          # LLM API key (if using cloud)
DATABASE_URL=sqlite:///...
```

### .env Security Rules

1. **`.env` is never committed to git** — it's in `.gitignore`
2. **`.env.example` is the template** — committed, but contains no real secrets
3. **Environment variables override `.env`** — useful in containers/CI
4. **The frontend never reads `.env`** — all config flows through the backend API

### How Secrets Flow

```
.env → pydantic-settings Settings() → backend.core.config.settings
                                         ↓
                                   Backend API (with secrets stripped)
                                         ↓
                                   Frontend (public config only)
```

### Checking for Leaked Secrets

Run before committing:
```bash
# Check no .env is staged
git diff --cached --name-only | grep -i .env

# Check no hardcoded secrets in code
grep -r "api_key\|API_KEY\|sk-\|password" --include="*.py" --include="*.ts" --include="*.tsx" \
  --exclude-dir=node_modules --exclude-dir=.venv --exclude=.env.example
```

---

## Audit Trail

Every action is logged with full context:

```
action=<name> skill=<name> risk=<level> params={...} result=<outcome> duration_ms=<ms>
```

Audit logs are written to `logs/audit_YYYY-MM-DD.log`, rotated at 10 MB, retained for 90 days.

The `PermissionsGuard.log_check()` method writes permission decisions to the audit log — every allow/deny is recorded.

---

## Principle of Least Privilege

- Jarvis runs with the user's permissions — **never as root/admin**
- Shell commands are sandboxed with timeouts and no destructive flags
- File operations outside user home directories require confirmation
- Network access is limited to configured providers only
- The Electron renderer has no Node.js or filesystem access

---

## Security Review Checklist

Use this checklist when making changes to the codebase, before merging PRs, or when deploying.

### Code Changes

- [ ] Are any new API keys or secrets hardcoded in source files?
- [ ] Does any new frontend code access `.env` or secrets?
- [ ] Are new API endpoints properly classified by risk level?
- [ ] Do new skills declare correct `risk` levels (`safe`, `confirmation`, `dangerous`)?
- [ ] Are all new shell/command executions routed through `PermissionGuard`?
- [ ] Are new file operations restricted to safe paths?
- [ ] Does new code use `audit_log()` for important actions?
- [ ] Are new dependencies reviewed for security issues?

### Configuration

- [ ] Is `.env` in `.gitignore`?
- [ ] Does `.env.example` exist and contain no real secrets?
- [ ] Are CORS origins restricted to localhost only?
- [ ] Is `LLM_ALLOW_CLOUD` set to `false` unless explicitly needed?
- [ ] Are security settings at their safe defaults?
  - `SECURITY_CONFIRM_DANGEROUS_ACTIONS=true`
  - `SECURITY_AUTO_APPROVE_SAFE=true`
  - `SECURITY_MAX_SHELL_TIMEOUT=30`

### Desktop App

- [ ] Is `contextIsolation: true` in Electron config?
- [ ] Is `nodeIntegration: false` in Electron config?
- [ ] Does the preload script expose only the minimum API surface?
- [ ] Are external links opened in the system browser, not in Electron?

### Before Release

- [ ] Run `python scripts/check_environment.py` — no unexpected issues
- [ ] Check `curl http://127.0.0.1:8400/api/config/public` — no secrets in response
- [ ] Check `curl -X POST http://127.0.0.1:8400/api/diagnostics/export` — no secrets
- [ ] Review audit logs for unexpected patterns
- [ ] Test a dangerous action — confirm it lands in the pending queue
- [ ] Test approval workflow — approve → execute → verify result
- [ ] Test rejection workflow — reject → verify not executed
- [ ] Test auto-expiry — leave a pending action > 60 minutes
- [ ] Verify voice processing stays local (no network calls for STT)
- [ ] Verify document indexing stays local

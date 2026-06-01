# Security Model

## Risk Levels

Every action in Jarvis is classified by risk:

| Level | Behavior | Examples |
|---|---|---|
| `safe` | Auto-approved, no confirmation | Open app, URL, timer, search, system stats |
| `confirmation` | User must confirm | Close app, move/rename file, execute script |
| `dangerous` | Strong explicit confirmation | Delete files, shutdown, arbitrary shell |

## Permission Guard

The PermissionGuard checks every action before execution:

```python
perm = permission_guard.check(risk, action_description)
# Returns: { allowed, needs_confirmation, confirmation_message }
```

Rules:
- Safe actions: always auto-approved
- Confirmation actions: user must click "Confirm" in UI
- Dangerous actions: user must type "CONFIRM EXECUTE"
- All checks are configurable via settings
- Confirmation can be disabled per-risk-level in dev mode

## Principle of Least Privilege

- Jarvis runs with user permissions, never root/admin
- Shell commands are sandboxed (timeout, no destructive flags)
- File operations outside user directories require confirmation
- Network access is limited to configured providers

## Audit Trail

Every action is logged with:
- Timestamp
- Original input
- Parsed intent
- Skill and action
- Parameters
- Risk level
- Confirmation status
- Result (success/failure)
- Error details
- Duration

Logs are stored in SQLite and rotated to compressed files.

## Privacy

- All data is local by default
- Cloud LLM is opt-in only
- Habit learning data never leaves the device
- Voice data is processed locally
- Document indexing is local-only

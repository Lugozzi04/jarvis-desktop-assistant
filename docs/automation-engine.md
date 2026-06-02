# Automation Engine (M8)

## What is an Automation?

An **automation** is a rule that says: **"When X happens, if Y is true, do Z."**

```
Trigger → Conditions → Actions
```

Contrast with **Workflows** (M7), which are sequences of actions executed step-by-step. Automations decide *when* to run workflows (or individual skill actions).

| Concept | Automation | Workflow |
|---|---|---|
| What it does | Decides WHEN to run | Defines WHAT to run |
| Trigger | Yes (time, event, manual) | No (always called explicitly) |
| Conditions | Yes | No |
| Actions | Skill action, workflow, notification, chat | Skill actions only (sequential) |
| Scheduling | Background scheduler | None |

---

## Anatomy of an Automation

```json
{
  "id": "daily-study-reminder",
  "name": "Daily Study Reminder",
  "description": "Remind me to study every day at 18:00",
  "enabled": false,
  "trigger": {
    "type": "time",
    "config": {
      "time": "18:00",
      "days": ["mon","tue","wed","thu","fri"]
    }
  },
  "conditions": [],
  "actions": [
    {
      "type": "skill_action",
      "skill": "timers",
      "action": "create_reminder",
      "parameters": { "message": "Time to study!" },
      "risk": "safe"
    }
  ]
}
```

---

## Triggers

| Type | Description | Config |
|---|---|---|
| `manual` | Run only when explicitly triggered via UI/API | `{}` |
| `startup` | Run once when Jarvis starts | `{}` |
| `time` | Run at a specific time of day | `time: "HH:MM"`, `days: ["mon",...]` |
| `interval` | Run every N minutes | `interval_minutes: 30` |
| `app_opened` | Run when a specific app opens (placeholder) | `app_name: "OBS"` |
| `mode_is` | Run when a mode is active (placeholder) | `mode_name: "study"` |

### How triggers are evaluated

- **Manual**: Always fires when `POST /automations/{id}/run` is called
- **Startup**: Fires once when the scheduler starts, then never again
- **Time**: Checked every 15 seconds; fires at the exact HH:MM on allowed days
- **Interval**: Fires when elapsed time since last run ≥ `interval_minutes`
- **App/opened / Mode/is**: Placeholder checks — always pass

---

## Conditions

Conditions are optional filters. If any condition fails, the automation is **skipped**.

| Type | Description | Config |
|---|---|---|
| `always` | Always passes | `{}` |
| `time_after` | Current time ≥ specified time | `time: "HH:MM"` |
| `time_before` | Current time ≤ specified time | `time: "HH:MM"` |
| `day_of_week` | Today is in the allowed days | `days: ["mon","wed","fri"]` |
| `app_running` | App is running (placeholder) | `app_name: "OBS"` |
| `mode_is` | Mode is active (placeholder) | `mode_name: "study"` |

---

## Actions

Actions are what the automation executes when triggered and conditions pass.

| Type | Description | Example |
|---|---|---|
| `skill_action` | Execute a single skill action | `skill: "timers"`, `action: "create_reminder"` |
| `workflow` | Run a workflow by ID | `workflow_id: "live-setup"` |
| `notification` | Log a notification message | `parameters: { message: "..." }` |
| `chat_response` | Log a chat-style message | `parameters: { message: "..." }` |

### Action execution chain

1. **Skill actions** → `SkillRegistry.execute(skill, action, params)`
2. **Workflows** → `WorkflowEngine.run(workflow_id)`
3. **Notifications** → Logged to the audit log
4. **Chat responses** → Logged to the audit log

---

## Security & Permissions

Every action has a `risk` level:

| Risk | Auto-triggered behavior | Manual trigger |
|---|---|---|
| `safe` | ✅ Runs automatically | ✅ Runs |
| `confirmation` | ❌ Skipped (`skipped_requires_confirmation`) | ✅ Runs |
| `dangerous` | ❌ Skipped (`skipped_requires_confirmation`) | ✅ Runs |

**Rule**: Automations triggered by the scheduler or startup will **never** execute confirmation or dangerous actions. The automation status will be `skipped_requires_confirmation` and the run will be logged.

---

## Scheduler

The scheduler is a **lightweight background thread** (no external dependencies).

- Tick interval: **15 seconds**
- Started when the FastAPI backend starts
- Stopped on backend shutdown
- Only evaluates `time` and `interval` triggers (manual/startup/app_opened/mode_is are not polled)

Status endpoint: `GET /api/automations/engine/status`

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/automations` | List all automations |
| `POST` | `/api/automations` | Create a new automation |
| `GET` | `/api/automations/{id}` | Get automation detail |
| `PUT` | `/api/automations/{id}` | Update automation |
| `DELETE` | `/api/automations/{id}` | Delete automation |
| `POST` | `/api/automations/{id}/enable` | Enable automation |
| `POST` | `/api/automations/{id}/disable` | Disable automation |
| `POST` | `/api/automations/{id}/run` | Execute automation manually |
| `GET` | `/api/automations/engine/status` | Scheduler status |
| `POST` | `/api/automations/reload` | Reload from storage |

---

## Seed Automations (5 defaults)

| ID | Name | Trigger | Enabled | Actions |
|---|---|---|---|---|
| `daily-study-reminder` | Daily Study Reminder | time 18:00 | ❌ | Notification |
| `startup-llm-status` | Startup LLM Status | startup | ✅ | Chat response |
| `dev-session-manual` | Dev Session Manual | manual | ✅ | Workflow: dev-session |
| `obs-live-workflow` | OBS Live Workflow | app_opened OBS | ❌ | Workflow: live-setup |
| `hydration-reminder` | Hydration Reminder | interval 30m | ❌ | Notification |

---

## Creating an Automation (Frontend)

1. Go to **Automations** page
2. Click **+ New**
3. Choose a **preset** or switch to **JSON Editor**
4. Paste/edit the JSON
5. Click **Create Automation**

### Example: Daily reminder at 9 AM

```json
{
  "name": "Morning Reminder",
  "description": "Check tasks every morning",
  "enabled": true,
  "trigger": {
    "type": "time",
    "config": { "time": "09:00", "days": ["mon","tue","wed","thu","fri"] }
  },
  "conditions": [],
  "actions": [
    { "type": "notification", "parameters": { "message": "🌅 Good morning! Check your tasks." }, "risk": "safe" }
  ]
}
```

### Example: Interval hydration reminder

```json
{
  "name": "Hydration Reminder",
  "description": "Drink water every 30 minutes",
  "enabled": true,
  "trigger": {
    "type": "interval",
    "config": { "interval_minutes": 30 }
  },
  "conditions": [],
  "actions": [
    { "type": "notification", "parameters": { "message": "💧 Drink water!" }, "risk": "safe" }
  ]
}
```

---

## Limitations (Current)

- `app_opened` trigger is a placeholder (no OS-level app monitoring yet)
- `mode_is` trigger and condition are placeholders (mode system not implemented)
- `app_running` condition is a placeholder
- JSON file-based storage (migratable to SQLite)
- No UI for editing individual automation fields (JSON editor only)
- Scheduler runs in-process (no persistent scheduling across restarts)

## Future (M8+)

- [ ] Real app_opened trigger via OS monitoring
- [ ] Mode system
- [ ] Visual automation builder (drag-and-drop)
- [ ] Automation templates/gallery
- [ ] SQLite storage migration
- [ ] Per-automation run history
- [ ] Conditional branching (if/else)

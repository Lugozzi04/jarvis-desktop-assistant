# Habit Learning (M10)

## What is Habit Learning?

JARVIS observes your usage patterns and suggests automations and workflows. It does NOT activate anything without your explicit approval.

## What is tracked

| Event | What | Privacy |
|---|---|---|
| `skill_action` | Skill name + action + timestamp | ✅ No message content |
| `workflow_run` | Workflow ID + timestamp | ✅ No step details |
| `automation_run` | Automation ID + timestamp | ✅ |
| `app_opened` | App name + timestamp | ✅ |
| `timer_created` | Duration + message | ✅ Message stored (for pattern detection) |
| `chat_command` | Slash command only | ✅ Not full chat content |

## What is NOT tracked

- Full chat messages
- File contents
- Web search queries (only action metadata)
- Personal documents
- Passwords or credentials

## How suggestions work

### 1. Repeated Actions
If you run the same skill/action at the same time of day 3+ times → suggests a time-based automation.

### 2. Co-occurring Actions
If you run multiple actions together within 30 minutes 3+ times → suggests a workflow combining them.

### 3. Repeated Workflows
If you run the same workflow manually 3+ times → suggests a shortcut automation.

### 4. App → Workflow
If you open an app and then run a workflow within 30 minutes 3+ times → suggests an app_opened automation.

## Suggestion lifecycle

```
Event tracked → Analysis (manual or automatic) → Suggestion generated
                                                      │
                                    ┌─────────────────┼──────────────────┐
                                    ▼                 ▼                  ▼
                                 Pending         Accepted           Dismissed
                                    │
                              User clicks "Accept"
                                    │
                              Creates automation/workflow (DISABLED by default)
```

## Privacy controls

- All data stored **locally** in `data/habit_events.json`
- Nothing sent externally
- Can be **disabled** via settings
- Events can be **cleared** at any time
- Max 1000 events retained

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/habits/events` | Recent events |
| GET | `/api/habits/suggestions` | All suggestions |
| POST | `/api/habits/analyze` | Run pattern analysis |
| POST | `/api/habits/suggestions/{id}/accept` | Accept → creates automation |
| POST | `/api/habits/suggestions/{id}/dismiss` | Dismiss suggestion |
| POST | `/api/habits/clear-events` | Clear all events |
| POST | `/api/habits/clear-suggestions` | Clear all suggestions |
| POST | `/api/habits/track` | Track a manual event |

## Current Limitations

- Rule-based only (no ML)
- Minimum 3 occurrences per pattern
- 30-minute co-occurrence window
- Manual analysis (no automatic background analysis yet)
- No cross-session pattern detection
- Simple confidence scoring

## Future (M10+)

- [ ] Automatic periodic analysis
- [ ] ML-based pattern detection
- [ ] Time decay for old patterns
- [ ] Custom pattern rules
- [ ] Export/import suggestions
- [ ] Integration with mode system

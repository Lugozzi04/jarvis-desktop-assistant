# Plugin / Skill System

## Overview

Every capability in Jarvis is a **skill** — an independent, auto-discovered plugin with its own manifest and Python module.

## Skill Structure

```
backend/skills/<skill_name>/
├── manifest.json    # Metadata, actions, parameters, risk levels
└── skill.py         # Python class inheriting BaseSkill
```

## Manifest Format

```json
{
  "name": "apps",
  "display_name": "Application Launcher",
  "description": "Open, close, and manage desktop applications.",
  "version": "0.1.0",
  "author": "Jarvis",
  "actions": [
    {
      "name": "open",
      "description": "Open a configured desktop application.",
      "parameters": {
        "app_name": "string"
      },
      "risk": "safe"
    }
  ]
}
```

## BaseSkill API

```python
class BaseSkill(ABC):
    name: str
    display_name: str
    description: str
    version: str
    actions: list[dict]

    def can_handle(self, skill_name: str, action: str) -> bool: ...
    
    @abstractmethod
    def execute(self, action: str, parameters: dict) -> ActionResult: ...
    
    def get_risk(self, action: str) -> RiskLevel: ...
```

## Auto-Discovery

At startup, `SkillRegistry.discover_and_load()`:
1. Scans `backend/skills/*/`
2. Reads `manifest.json` from each folder
3. Dynamically imports `skill.py`
4. Finds the `BaseSkill` subclass
5. Registers it with metadata from the manifest

**No configuration files, no manual registration.** Just create the folder and restart.

## Adding a New Skill

1. Create `backend/skills/<name>/manifest.json`
2. Create `backend/skills/<name>/skill.py` with a class inheriting `BaseSkill`
3. Implement `execute(action, parameters)` → `ActionResult`
4. Restart the backend

That's it. The skill is automatically loaded and available via API and chat.

## Skill Lifecycle

- **Discovery**: On startup, all valid skills are loaded
- **Execution**: `registry.execute(skill_name, action, params)` → `ActionResult`
- **Enable/Disable**: Via settings UI (coming in M6)
- **Hot Reload**: `registry.reload()` for development

## Best Practices

1. **One skill, one responsibility** — don't make mega-skills
2. **Idempotent actions** — opening an already-open app should be safe
3. **Graceful failure** — return `ActionResult(success=False, error=...)` instead of raising
4. **No core modifications** — if you need to change core code, you're doing it wrong
5. **Manifest truth** — the manifest is the contract; implement exactly what it declares

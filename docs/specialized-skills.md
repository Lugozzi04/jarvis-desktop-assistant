# Specialized Skills (M12A)

## Overview

M12A adds dedicated skills for popular applications. Each skill is modular, lives in `backend/skills/<name>/`, and requires **no core changes**.

All skills use a **fallback pattern**: if a native API (OBS WebSocket, Discord bot, Spotify API) is not configured, they fall back to `AppSkill` (open desktop app) or `BrowserSkill` (open web interface).

---

## OBS Skill

**ID:** `obs`

| Action | Risk | Description |
|---|---|---|
| `open` | safe | Opens OBS Studio via AppSkill |
| `check_status` | safe | Reports OBS connection status |
| `start_recording` | confirmation | Start recording (WebSocket required for real control) |
| `stop_recording` | confirmation | Stop recording (WebSocket required for real control) |

### Config (future)

```env
OBS_WS_URL=ws://localhost:4455
OBS_WS_PASSWORD=your_password
```

---

## Discord Skill

**ID:** `discord`

| Action | Risk | Description |
|---|---|---|
| `open` | safe | Opens Discord desktop app |
| `open_web` | safe | Opens Discord in browser |
| `open_server` | safe | Opens a specific Discord server URL |

### Config

```json
// In settings (future):
{"discord_servers": {"gaming": "https://discord.gg/..."}}
```

---

## Spotify Skill

**ID:** `spotify`

| Action | Risk | Description |
|---|---|---|
| `open` | safe | Opens Spotify desktop app |
| `search` | safe | Opens Spotify Web search for tracks/albums |
| `search_artist` | safe | Opens Spotify Web search for artists |

### How search works

Uses Spotify Web URLs — no API required:

```
https://open.spotify.com/search/{query}
https://open.spotify.com/search/{query}/artists
```

---

## GitHub Skill

**ID:** `github`

| Action | Risk | Description |
|---|---|---|
| `open_repo` | safe | Opens a GitHub repository in browser |
| `open_issues` | safe | Opens issues page for a repository |
| `git_status` | safe | Runs `git status` in current/configured directory |
| `clone_repo` | confirmation | Clone a repository (confirmation required) |
| `commit_all` | confirmation | Stage and commit all changes (confirmation required) |
| `push` | confirmation | Push to remote (confirmation required) |

### Repo aliases

```python
REPO_ALIASES = {
    "jarvis": "https://github.com/Lugozzi04/jarvis-desktop-assistant",
    "hermes": "https://github.com/nousresearch/hermes-agent",
}
```

---

## Security

| Risk Level | Behavior |
|---|---|
| `safe` | Runs automatically |
| `confirmation` | Requires user confirmation via UI |
| `dangerous` | Strong confirmation required |

Confirmation-requiring actions (`clone`, `commit`, `push`, `start_recording`) are never executed automatically by the Automation Engine. They can only be triggered manually.

---

## Adding a new specialized skill

1. Create `backend/skills/<name>/manifest.json` and `skill.py`
2. The SkillRegistry auto-discovers it on restart
3. Add slash commands and NL patterns to router
4. That's it — no core changes needed

---

## Future (M12+)

- [ ] OBS WebSocket real integration
- [ ] Discord bot token for message/status
- [ ] Spotify OAuth for playback control
- [ ] GitHub CLI (`gh`) integration
- [ ] Pull request management
- [ ] More app aliases in ProcessMonitor

# Setup Wizard

The Jarvis Desktop Assistant setup wizard walks you through first-run configuration in 8 guided steps. It appears automatically when you launch Jarvis for the first time, and you can re-open it at any time from Settings.

---

## Quick Reference

| Action | How |
|---|---|
| **Re-open wizard** | Settings → **Open Setup Wizard** |
| **Reset wizard** | `POST /api/setup/reset` |
| **Check status** | `GET /api/setup/status` |
| **Refresh components** | `POST /api/setup/refresh` |
| **State file location** | `data/setup_state.json` (inside the jarvis data directory) |
| **Mark component ready** | `POST /api/setup/component/{component}` |

---

## Wizard Walkthrough

### Step 1 — Welcome

The landing screen introduces Jarvis Desktop Assistant and explains what the wizard will configure:

- **LLM** — the AI model that powers Jarvis's responses
- **Documents** — semantic search and RAG over your files
- **Voice** — speech-to-text and text-to-speech
- **Integrations** — OBS, Discord, Spotify, GitHub
- **Security** — how dangerous actions are gated

Click **Next** to begin the system check.

---

### Step 2 — System Check

Jarvis verifies your environment is ready:

- Python 3.10+ installed and functional
- Backend server can start (FastAPI + Uvicorn)
- Write access to the data directory (where `setup_state.json`, vector stores, and logs live)
- Frontend build tooling available (Node.js / npm)
- Disk space for models and document indexes (recommended: 5+ GB free if using local LLM)

Any issues are surfaced with suggested fixes before you continue.

---

### Step 3 — LLM Setup

Jarvis needs a language model to respond to your requests.

#### Default / Recommended: Ollama + Qwen 2.5 7B

The wizard guides you to install Ollama and pull the recommended model:

```bash
# Install Ollama (if not already present)
curl -fsSL https://ollama.com/install.sh | sh

# Pull the recommended model (~4.7 GB download)
ollama pull qwen2.5:7b
```

Once the model is pulled, Jarvis detects it automatically. You can also pull additional models later and switch between them in Settings.

#### Alternative Providers

If you'd rather use a cloud provider or a different local model:

- **Ollama (other models)** — pull any model via `ollama pull <name>`; Jarvis scans running Ollama instances
- **OpenAI-compatible APIs** — point Jarvis at any OpenAI-compatible endpoint (LM Studio, vLLM, Groq, etc.)
- **Direct cloud** — configure an API key for OpenAI, Anthropic, or DeepSeek in Settings → LLM

The wizard shows a spinner while checking for available models. When an active provider is detected, the step is marked complete and you can proceed.

**Relevant API**: `GET /api/setup/recommendations` returns the recommended model and install commands.

---

### Step 4 — Documents Setup

Jarvis can index your documents and let you search them semantically or ask questions with RAG (Retrieval-Augmented Generation).

#### Default: Simple Embeddings

Out of the box, Jarvis uses a lightweight built-in embedding provider (**Simple**) that requires no external dependencies or downloads. This works well for getting started:

- No GPU needed
- No model downloads
- Instant availability

Choose this if you have a small document library or just want to try the feature.

#### Optional: Ollama Embeddings (nomic-embed-text)

For higher-quality semantic search, switch to Ollama's embedding model:

```bash
ollama pull nomic-embed-text
```

Then in the wizard, select **Ollama Embeddings** as your provider. Jarvis will use `nomic-embed-text` for chunking and retrieval, giving you better results for larger document collections.

After selecting a provider, you can optionally index a folder to populate the vector store immediately (or skip and do it later via the Documents panel).

**Relevant API**: `GET /api/documents/status` — check embedding provider and indexed document count.

---

### Step 5 — Voice Setup

Jarvis supports push-to-talk voice input and text-to-speech output.

#### Default: Mock Provider

The **Mock** voice provider is enabled by default and requires no setup. It provides:

- **STT (Speech-to-Text)**: Returns placeholder transcriptions. Useful for testing the voice pipeline end-to-end without installing model dependencies.
- **TTS (Text-to-Speech)**: No audio output (responses are text-only).

This is ideal if you primarily type your commands and don't need real voice I/O yet.

#### Optional: FasterWhisper (STT)

For real speech recognition, install FasterWhisper:

```bash
pip install faster-whisper
```

FasterWhisper runs locally on CPU or GPU with models from tiny to large-v3. The wizard will:

1. Detect if FasterWhisper is installed
2. Let you choose a model size (tiny/base/small/medium/large-v3)
3. Run a quick test transcription to confirm it works

#### Optional: EdgeTTS (TTS)

For text-to-speech output, Jarvis can use Microsoft Edge TTS (free, no API key):

```bash
pip install edge-tts
```

After installation, Jarvis will speak responses aloud. You can choose from multiple voices in Settings → Voice after setup.

**Relevant API**: `GET /voice/status` — check STT and TTS availability and active providers.

---

### Step 6 — Integrations

Connect Jarvis to your tools and services. Each integration is optional and can be configured now or later.

#### OBS Studio

- **Purpose**: Control OBS (start/stop streaming, switch scenes, adjust audio)
- **Requirements**: OBS installed with the WebSocket plugin enabled (OBS 28+ has it built-in)
- **Setup**: Enter your OBS WebSocket host (default: `localhost:4455`) and password
- **Test**: The wizard will attempt to connect and verify the connection

#### Discord

- **Purpose**: Send messages, manage channels, react to DMs
- **Requirements**: A Discord bot token with appropriate permissions
- **Setup**: Paste your bot token; wizard validates it by fetching bot user info
- **Test**: Sends a heartbeat check to confirm the token is valid

#### Spotify

- **Purpose**: Control playback, search tracks, manage playlists
- **Requirements**: Spotify Premium account + registered app (Client ID + Client Secret)
- **Setup**: Enter your Client ID and Secret; follow the OAuth redirect to authorize Jarvis
- **Test**: Wizard fetches your currently-playing track to confirm the connection

#### GitHub

- **Purpose**: Manage repos, issues, PRs, and gists
- **Requirements**: A GitHub personal access token (classic or fine-grained)
- **Scopes needed**: `repo` (private repos), `read:org`, `gist`
- **Setup**: Paste your token; wizard fetches your user profile to validate
- **Test**: Shows your GitHub username and rate limit status

**Relevant API**: `POST /api/setup/component/{obs|discord|spotify|github}` — mark individual integrations as configured.

---

### Step 7 — Security

Jarvis uses a layered security model to protect your system. This step explains the guardrails and lets you verify them.

#### Pending Actions Queue

Every **dangerous** or **confirmation-required** action goes through a pending actions queue:

1. Jarvis receives your request (e.g., "delete all files in ~/Downloads")
2. The action is placed in the **pending queue** with a risk label and reason
3. You review it in the Pending Actions panel and **approve** or **reject**
4. Only approved actions execute; rejected or expired actions are discarded
5. Actions auto-expire after 60 minutes if not reviewed

**Jarvis never executes dangerous actions automatically.** There is no "auto-approve dangerous" toggle.

#### Risk Levels

| Level | Behavior | Examples |
|---|---|---|
| `safe` | Auto-approved, no confirmation | Open apps, web searches, timers, system stats |
| `confirmation` | User must click **Confirm** | Close apps, move/rename files, execute known scripts |
| `dangerous` | User must explicitly approve via Pending Actions | Delete files, arbitrary shell, system shutdown, git force-push |

#### What the Wizard Confirms

- You understand the risk level system
- You know where to find pending actions (the Pending Actions icon in the sidebar)
- No auto-dangerous mode exists — this is a hard security invariant
- You can adjust confirmation behavior per-risk-level in advanced settings (dev mode only)

Once reviewed, click **I Understand** to mark security as reviewed.

**Relevant API**: `GET /api/pending-actions` — view the current pending actions queue.

---

### Step 8 — Finish

The final step shows a summary of your choices:

- **LLM**: provider and model name
- **Documents**: embedding provider and indexed document count (0 if skipped)
- **Voice**: STT and TTS providers
- **Integrations**: which services are connected
- **Security**: confirmed reviewed

Click **Finish** to complete the wizard. Jarvis transitions to the main interface and is ready for use.

If anything is incomplete, the summary highlights remaining recommendations (e.g., "Pull qwen2.5:7b", "Index documents to enable RAG").

---

## Re-opening the Setup Wizard

After the initial run, you can re-open the wizard at any time:

1. Open Jarvis Desktop Assistant
2. Click **Settings** (gear icon in the sidebar/top bar)
3. Select **Open Setup Wizard**

This launches the full 8-step wizard again, pre-populated with your current settings. You can step through to change providers, add integrations, or review security.

---

## Resetting the Setup State

To force the wizard to appear on next launch (as if Jarvis were never set up):

### Via API

```bash
curl -X POST http://localhost:8765/api/setup/reset
```

Response:

```json
{"status": "reset"}
```

This clears all setup state — `first_run` becomes `true` and all component readiness flags are cleared.

### Via File System

Delete the state file directly:

```bash
rm data/setup_state.json
```

Jarvis will regenerate it with defaults on the next status check.

### Programmatic Component Reset

Reset individual components without wiping everything:

```bash
curl -X POST http://localhost:8765/api/setup/component/llm?ready=false
curl -X POST http://localhost:8765/api/setup/component/voice?ready=false
curl -X POST http://localhost:8765/api/setup/component/github?ready=false
```

Valid component names: `llm`, `documents`, `voice`, `security`, `obs`, `discord`, `spotify`, `github`.

---

## Setup State File

The wizard state is persisted in:

```
data/setup_state.json
```

(Where `data/` is the configured `settings.data_dir`, typically `<project_root>/data/`.)

### Schema

```json
{
  "first_run": true,
  "completed": false,
  "completed_at": null,
  "llm_ready": false,
  "llm_provider": "none",
  "documents_ready": false,
  "documents_provider": "none",
  "voice_ready": false,
  "voice_provider": "none",
  "integrations_configured": {
    "obs": false,
    "discord": false,
    "spotify": false,
    "github": false
  },
  "security_reviewed": false,
  "desktop_ready": true,
  "recommended_next_steps": ["ollama_pull_model", "run_setup_wizard"]
}
```

Dynamic fields (`llm_ready`, `documents_ready`, `voice_ready`, `desktop_ready`, `recommended_next_steps`) are refreshed on every `GET /api/setup/status` call, so they reflect the live state of the system — not just what was set during the wizard.

---

## API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/api/setup/status` | GET | Full setup status with dynamic refresh |
| `/api/setup/complete` | POST | Mark wizard as completed |
| `/api/setup/reset` | POST | Full reset — wizard shows on next launch |
| `/api/setup/refresh` | POST | Force-refresh dynamic readiness fields |
| `/api/setup/recommendations` | GET | Get recommended next steps and commands |
| `/api/setup/component/{name}` | POST | Mark a single component ready/unready |

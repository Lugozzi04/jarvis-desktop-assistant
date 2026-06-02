# LLM Strategy for Jarvis Desktop Assistant

## Overview

Jarvis uses a **local-first, multi-tier** LLM strategy:

1. **Deterministic routing** for slash commands (no LLM)
2. **Rule-based NL patterns** for common phrases
3. **LLM intent routing** as fallback (only when available)
4. **LLM chat** for general conversation

The system is designed to work **offline** — if no LLM is available, slash commands and rule-based routing still work.

## Recommended Local Model

**Primary: `qwen2.5:7b`**

- Good balance of quality and performance
- ~4.7 GB download
- Excellent for structured JSON output
- Good for routing, chat, and planning
- Works well on consumer PCs with 16GB+ RAM

**Fallback Light: `llama3.2:3b`**

- ~2.0 GB download
- Works on machines with 8GB RAM
- Good for basic routing and chat
- Weaker at structured output

**Fallback Heavy: `llama3.1:8b`**

- ~4.9 GB download
- Better quality than qwen2.5:7b for some tasks
- Requires ~8GB RAM for the model alone

## Provider Architecture

```
User Input
    │
    ▼
┌─────────────────────────┐
│   Intent Router          │
│   1. Slash commands      │ → Deterministic (no LLM)
│   2. Rule patterns       │ → Regex match (no LLM)
│   3. LLM intent routing  │ → Only if available
│   4. Fallback to chat    │ → LLM or offline message
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│   LLM Gateway            │
│   ┌─────────────────┐   │
│   │ OllamaProvider   │   │ ← Local, free, private
│   │ OpenAICompat     │   │ ← Cloud: OpenAI, DeepSeek
│   │ MockProvider     │   │ ← Testing
│   └─────────────────┘   │
└─────────────────────────┘
```

## Setup on Local PC

### 1. Install Ollama

```bash
# Linux
curl -fsSL https://ollama.com/install.sh | sh

# macOS
brew install ollama

# Windows
# Download from https://ollama.com/download/windows
```

### 2. Pull the recommended model

```bash
ollama pull qwen2.5:7b
```

### 3. Configure .env

```env
LLM_DEFAULT_PROVIDER=ollama
LLM_DEFAULT_MODEL=qwen2.5:7b
LLM_BASE_URL=http://localhost:11434
LLM_ALLOW_CLOUD=false
```

### 4. Verify

```bash
# Check Ollama status
python scripts/check_ollama.py

# Or via the API
curl http://localhost:8400/api/llm/status
curl http://localhost:8400/api/settings/llm/test \
  -H "Content-Type: application/json" \
  -d '{"provider": "ollama"}'
```

## Alternative: Cloud Provider

### DeepSeek (Recommended Cloud)

```env
LLM_DEFAULT_PROVIDER=openai_compatible
LLM_DEFAULT_MODEL=deepseek-chat
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_API_KEY=sk-......LLM_ALLOW_CLOUD=true
```

### OpenAI

```env
LLM_DEFAULT_PROVIDER=openai_compatible
LLM_DEFAULT_MODEL=gpt-4o-mini
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-......LLM_ALLOW_CLOUD=true
```

## JSON Intent Routing

When rule-based routing fails to match user input, Jarvis can use the LLM to classify the intent:

```
User: "mi apri il programma per parlare con gli amici?"
  → Rule-based: no match
  → LLM routing: {"kind": "skill", "skill": "apps", "action": "open",
                   "parameters": {"app_name": "Discord"}, "confidence": 0.75}
  → Executes: apps.open("Discord")
```

The LLM prompt includes all available skills and actions for accurate routing.

## Important: No LLM Installation on Server

- **Ollama is NOT installed on the development server/VPS**
- **Models are NOT downloaded on the server**
- The server only runs the code and tests with MockProvider
- All LLM-dependent features degrade gracefully when offline
- Users install Ollama locally on their own PC

## Status API

`GET /api/llm/status` returns detailed Ollama diagnostics:

```json
{
  "provider": "ollama",
  "base_url": "http://localhost:11434",
  "model": "qwen2.5:7b",
  "reachable": false,
  "model_available": false,
  "available_models": [],
  "ready": false,
  "setup_required": true,
  "recommended_command": "ollama pull qwen2.5:7b",
  "error": "Ollama is not reachable at http://localhost:11434"
}
```

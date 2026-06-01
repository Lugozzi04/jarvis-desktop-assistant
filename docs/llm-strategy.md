# LLM Strategy

## Philosophy

**Use LLMs only when they add value.** Most desktop assistant operations (opening apps, setting timers, checking system stats) don't need an LLM at all.

## Task Classification

| Task Type | LLM Needed? | Strategy |
|---|---|---|
| Slash commands (`/open`, `/timer`) | ❌ No | Deterministic regex parser |
| Simple intents ("apri Spotify") | ❌ No | Rule-based pattern matching |
| Ambiguous intents | 🟡 Small | Local model (phi3:mini) for classification |
| Complex planning | 🟡 Medium | Local model (qwen2.5:7b) for multi-step plans |
| General chat | ✅ Yes | Full LLM (llama3.1:8b or cloud) |
| Web search summarization | ✅ Yes | Web results + LLM summarizer |

## Provider Architecture

```
LLM Gateway
├── Ollama (local, default)
├── OpenAI (cloud, optional)
├── Anthropic (cloud, optional)
├── DeepSeek (cloud, optional)
└── Custom OpenAI-compatible endpoint
```

## Local-First Design

1. All deterministic operations skip the LLM entirely
2. Intent classification uses a tiny local model (phi3:mini ~2GB)
3. Planning uses a medium local model (qwen2.5:7b ~4GB)
4. Cloud LLM is **opt-in only** — disabled by default
5. Sensitive data never leaves the machine

## JSON Output Mode

When the LLM is used for intent routing, it outputs structured JSON — never free text:

```json
{
  "kind": "action",
  "confidence": 0.93,
  "skill": "apps",
  "action": "open",
  "parameters": {"app_name": "Discord"},
  "needs_confirmation": false
}
```

This is validated against Pydantic schemas before execution.

## Fallback Strategy

If the LLM is unavailable:
- Slash commands still work (deterministic)
- Rule-based routing still works
- Chat returns a helpful message suggesting slash commands
- No crashes, no broken UX

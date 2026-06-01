# Voice System

## Architecture

```
Microphone → Wake Word (future) → STT → Intent Router → Action → TTS (optional)
```

## Modes

| Mode | Description | Status |
|---|---|---|
| Push-to-Talk | Hold button, speak, release | M9 target |
| Wake Word | "Jarvis" / "Daddy's home" | Future |
| Always Listening | Continuous (privacy indicator required) | Not planned for MVP |

## Speech-to-Text Providers

| Provider | Type | Quality | Speed | Notes |
|---|---|---|---|---|
| faster-whisper | Local | High | Fast | Recommended default |
| whisper.cpp | Local | High | Very Fast | C++ implementation |
| OpenAI Whisper API | Cloud | Highest | Fast | Requires API key |
| Vosk | Local | Medium | Very Fast | Good for simple commands |

## Text-to-Speech Providers

| Provider | Type | Quality | Notes |
|---|---|---|---|
| Edge TTS | Cloud-free | Good | Windows/Linux via edge-tts |
| Piper | Local | Good | Lightweight, multiple voices |
| Coqui TTS | Local | High | Heavier, better quality |
| System TTS | OS | Varies | Built-in, no dependencies |

## Privacy

- Push-to-talk only by default
- Wake word processed locally (no cloud)
- Always-listening requires explicit opt-in + visible indicator
- All voice data stays local unless cloud STT is explicitly enabled

## UX Requirements

- Microphone status indicator (on/off/muted)
- Push-to-talk button in UI
- Transcription preview (edit before sending)
- TTS toggle (on/off)
- Voice activity visualization

# Voice System (M9)

## Architecture

```
┌─────────────────────────────────────────────────┐
│                   Frontend                      │
│  ┌──────────────┐  ┌──────────────┐             │
│  │ Push-to-Talk  │  │ Upload Audio │             │
│  │ (MediaRecorder)│  │ (file input) │             │
│  └──────┬───────┘  └──────┬───────┘             │
│         │                 │                     │
└─────────┼─────────────────┼─────────────────────┘
          │                 │
          ▼                 ▼
┌─────────────────────────────────────────────────┐
│              API (FastAPI)                      │
│  POST /voice/transcribe                         │
│  POST /voice/command   (transcribe + route)     │
│  POST /voice/speak                              │
│  GET  /voice/status                             │
└───────────────────┬─────────────────────────────┘
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
┌──────────────────┐  ┌──────────────────┐
│   STT Provider   │  │   TTS Provider   │
│  ┌────────────┐  │  │  ┌────────────┐  │
│  │ Mock       │  │  │  │ Mock       │  │
│  ├────────────┤  │  │  ├────────────┤  │
│  │ FastWhisp. │  │  │  │ EdgeTTS    │  │
│  └────────────┘  │  │  └────────────┘  │
└──────────────────┘  └──────────────────┘
```

## Providers

### STT (Speech-to-Text)

| Provider | Status | Requires | Setup |
|---|---|---|---|
| `mock` | ✅ Default | Nothing | Works everywhere, returns deterministic text |
| `faster_whisper` | ✅ Ready | `pip install faster-whisper` | Model auto-downloads on first use (~150 MB for base) |

### TTS (Text-to-Speech)

| Provider | Status | Requires | Setup |
|---|---|---|---|
| `mock` | ✅ Default | Nothing | Logs text instead of speaking |
| `edge_tts` | 📋 Planned | `pip install edge-tts` | Uses Microsoft Edge TTS (free, no API key) |

## Local Setup (PC only, not VPS)

### Real STT with Faster-Whisper

```bash
pip install faster-whisper
```

```env
JARVIS_STT_PROVIDER=faster_whisper
JARVIS_STT_MODEL=base       # tiny (75MB), base (150MB), small (500MB), medium (1.5GB)
JARVIS_STT_DEVICE=cpu       # or cuda if GPU available
```

### Real TTS (coming in future)

Edge TTS will be the primary local TTS recommendation — free, no API key, good quality.

## API Endpoints

### GET /api/voice/status

```json
{
  "voice_enabled": false,
  "stt_provider": "mock",
  "stt_available": true,
  "tts_provider": "mock",
  "tts_available": true,
  "push_to_talk_enabled": true,
  "wake_word_enabled": false,
  "errors": []
}
```

### POST /api/voice/transcribe

Upload audio file (WAV, MP3, WebM, OGG, FLAC).

### POST /api/voice/command

Upload audio → transcribe → route to assistant pipeline → return transcription + response.

### POST /api/voice/speak

```json
{"text": "Ciao, sono Jarvis"}
```

## Privacy & Security

- **Audio is processed locally** when using Faster-Whisper
- **Nothing is sent externally** without user configuration
- **Mock provider** returns deterministic text — no real audio processing
- **Wake word** ("Jarvis") always-listening is NOT implemented
- **Push-to-talk** ensures intentional recording only

## Limitations (Current)

- No wake word / always-listening
- No real TTS provider (Edge TTS planned)
- Browser MediaRecorder requires HTTPS or localhost
- No streaming transcription (file-based only)

## TODO

- [ ] Edge TTS integration
- [ ] Wake word detection (porcupine or openWakeWord)
- [ ] Streaming transcription
- [ ] Voice activity detection
- [ ] Multi-language STT

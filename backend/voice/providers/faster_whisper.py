"""Faster-Whisper STT provider — local speech-to-text.

IMPORTANT: This code is ready but does NOT download models automatically.
The user must install faster-whisper and download a model locally.

Requirements (local PC only):
    pip install faster-whisper
    Model downloaded automatically by faster-whisper on first use.

Config (.env):
    JARVIS_STT_PROVIDER=faster_whisper
    JARVIS_STT_MODEL=base  # or tiny, small, medium, large-v3

Fallback: If faster-whisper or model is not available, the provider
reports an error with clear instructions.
"""

from __future__ import annotations

from typing import Any

from backend.core.config import settings
from backend.core.logger import logger
from backend.voice.providers.base import STTProvider, TranscriptionResult


class FasterWhisperProvider(STTProvider):
    """Faster-Whisper speech-to-text provider.

    Does NOT download models on import — only when first used.
    Reports clear errors if not installed.
    """

    name = "faster_whisper"

    def __init__(self, model_size: str = "base", device: str = "cpu"):
        self.model_size = model_size or getattr(settings, "stt_model", "base")
        self.device = device or getattr(settings, "stt_device", "cpu")
        self._model = None

    def _load_model(self) -> None:
        """Lazy-load the model. Call before first transcription."""
        if self._model is not None:
            return

        try:
            from faster_whisper import WhisperModel
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type="int8" if self.device == "cpu" else "float16",
            )
            logger.info(
                "Faster-Whisper loaded: model={} device={}",
                self.model_size, self.device,
            )
        except ImportError:
            raise RuntimeError(
                "faster-whisper is not installed. "
                "Install it on your local PC:\n"
                "  pip install faster-whisper\n\n"
                "Model will be downloaded automatically on first use (~150 MB for 'base')."
            )
        except Exception as exc:
            raise RuntimeError(f"Failed to load Faster-Whisper model: {exc}")

    async def transcribe_file(self, file_path: str) -> TranscriptionResult:
        """Transcribe an audio file using Faster-Whisper."""
        try:
            self._load_model()

            segments, info = self._model.transcribe(file_path, beam_size=5)
            text = " ".join([s.text for s in segments])

            return TranscriptionResult(
                text=text.strip(),
                language=info.language if info else "en",
                confidence=getattr(info, "avg_log_prob", None),
                duration=getattr(info, "duration", None),
                provider=self.name,
            )
        except RuntimeError as exc:
            logger.warning("Faster-Whisper error: {}", exc)
            return TranscriptionResult(
                text="",
                language="en",
                provider=self.name,
                error=str(exc),
            )
        except Exception as exc:
            logger.error("Faster-Whisper transcription failed: {}", exc)
            return TranscriptionResult(
                text="",
                language="en",
                provider=self.name,
                error=str(exc),
            )

    async def get_status(self) -> dict[str, Any]:
        try:
            from faster_whisper import WhisperModel
            self._load_model()
            return {
                "name": self.name,
                "available": True,
                "model": self.model_size,
                "device": self.device,
                "models_loaded": [self.model_size],
                "error": None,
                "setup_required": False,
            }
        except ImportError:
            return {
                "name": self.name,
                "available": False,
                "model": self.model_size,
                "device": self.device,
                "models_loaded": [],
                "error": "faster-whisper not installed. Run: pip install faster-whisper",
                "setup_required": True,
                "setup_command": "pip install faster-whisper",
            }
        except Exception as exc:
            return {
                "name": self.name,
                "available": False,
                "model": self.model_size,
                "device": self.device,
                "models_loaded": [],
                "error": str(exc),
                "setup_required": True,
            }

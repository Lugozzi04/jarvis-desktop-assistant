"""Edge TTS Provider — free, high-quality text-to-speech using Microsoft Edge.

Uses the edge-tts library (pip install edge-tts).
No API key required. Uses Microsoft's free Edge TTS service.
Supports many voices and languages.

Config (.env):
    VOICE_TTS_PROVIDER=edge
    VOICE_TTS_VOICE=it-IT-ElsaNeural  # Italian female voice
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from backend.core.config import settings
from backend.core.logger import logger
from backend.voice.providers.base import TTSProvider, SynthesisResult


class EdgeTTSProvider(TTSProvider):
    """Microsoft Edge TTS provider — free, no API key needed."""

    name = "edge"

    def __init__(self, voice: str = "it-IT-ElsaNeural"):
        self._voice = voice or getattr(settings.voice, "tts_voice", "it-IT-ElsaNeural") if settings.voice else "it-IT-ElsaNeural"
        self._available: bool | None = None

    async def _check_available(self) -> bool:
        """Lazy check if edge-tts is installed."""
        if self._available is not None:
            return self._available
        try:
            import edge_tts  # noqa: F401
            self._available = True
        except ImportError:
            self._available = False
            logger.warning("edge-tts not installed. Install: pip install edge-tts")
        return self._available

    async def get_status(self) -> dict[str, Any]:
        available = await self._check_available()
        return {
            "name": self.name,
            "available": available,
            "voice": self._voice,
            "error": None if available else "edge-tts not installed. Run: pip install edge-tts",
            "setup_required": not available,
            "setup_command": "pip install edge-tts",
        }

    async def synthesize(self, text: str, voice: str | None = None) -> SynthesisResult:
        """Convert text to speech and return audio file path."""
        if not await self._check_available():
            return SynthesisResult(
                success=False,
                provider=self.name,
                error="edge-tts not installed. Run: pip install edge-tts",
            )

        try:
            import edge_tts

            use_voice = voice or self._voice

            # Create temp file for output
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                output_path = f.name

            # Synthesize
            communicate = edge_tts.Communicate(text, use_voice)
            await communicate.save(output_path)

            # Clean up: read to bytes, then delete file
            audio_bytes = Path(output_path).read_bytes()
            Path(output_path).unlink(missing_ok=True)

            logger.info("Edge TTS: synthesized {} chars with voice {}", len(text), use_voice)
            return SynthesisResult(
                success=True,
                provider=self.name,
                audio_data=audio_bytes,
                format="mp3",
                voice=use_voice,
            )
        except Exception as exc:
            logger.error("Edge TTS synthesis failed: {}", exc)
            return SynthesisResult(
                success=False,
                provider=self.name,
                error=str(exc),
            )

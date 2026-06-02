"""Mock TTS provider — logs text instead of speaking."""

from __future__ import annotations

from typing import Any

from backend.core.logger import logger
from backend.voice.providers.base import TTSProvider, SynthesisResult


class MockTTSProvider(TTSProvider):
    """Mock text-to-speech provider for development and testing.

    Logs the text that would be spoken instead of generating audio.
    Does NOT use any TTS engine or models.
    """

    name = "mock"

    async def synthesize(self, text: str, voice: str | None = None) -> SynthesisResult:
        """Log the text and return success."""
        logger.info("Mock TTS would speak ({} chars): {}", len(text), text[:100])
        return SynthesisResult(
            success=True,
            provider=self.name,
        )

    async def get_status(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "available": True,
            "voices": [],
            "error": None,
            "note": "Mock provider — logs text instead of generating audio. No models required.",
        }

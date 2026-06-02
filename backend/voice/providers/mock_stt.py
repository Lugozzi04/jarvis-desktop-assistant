"""Mock STT provider — returns deterministic text for testing."""

from __future__ import annotations

from typing import Any

from backend.voice.providers.base import STTProvider, TranscriptionResult


class MockSTTProvider(STTProvider):
    """Mock speech-to-text provider for development and testing.

    Returns predetermined text based on filename or random patterns.
    Does NOT download or use any models.
    """

    name = "mock"

    def __init__(self, default_text: str = ""):
        self._default_text = default_text or "Hello, this is a mock transcription from JARVIS."

    async def transcribe_file(self, file_path: str) -> TranscriptionResult:
        """Return mock transcription."""
        # Try to extract a hint from the filename
        import os
        filename = os.path.basename(file_path).lower()
        text = self._default_text

        # Customize based on filename patterns
        if "hello" in filename or "ciao" in filename:
            text = "Ciao, sono Jarvis."
        elif "open" in filename:
            text = "open discord"
        elif "search" in filename:
            text = "search best coding practices"
        elif "timer" in filename:
            text = "timer 25 minutes study"
        elif "studio" in filename or "study" in filename:
            text = "study mode"

        return TranscriptionResult(
            text=text,
            language="en",
            confidence=1.0,
            provider=self.name,
        )

    async def get_status(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "available": True,
            "models_loaded": [],
            "error": None,
            "note": "Mock provider — returns deterministic transcriptions for testing",
        }

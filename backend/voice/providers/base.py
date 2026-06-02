"""Voice provider base classes and data models."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class TranscriptionResult(BaseModel):
    """Result of speech-to-text transcription."""

    text: str
    language: str = "en"
    confidence: float | None = None
    duration: float | None = None
    provider: str = ""
    error: str | None = None


class SynthesisResult(BaseModel):
    """Result of text-to-speech synthesis."""

    success: bool = True
    provider: str = ""
    audio_path: str | None = None
    audio_url: str | None = None
    error: str | None = None


class STTProvider(ABC):
    """Speech-to-text provider interface."""

    name: str = "base"

    @abstractmethod
    async def transcribe_file(self, file_path: str) -> TranscriptionResult:
        """Transcribe an audio file to text."""
        ...

    async def transcribe_bytes(self, audio_bytes: bytes, mime_type: str = "audio/wav") -> TranscriptionResult:
        """Transcribe audio bytes. Override for optimized implementations."""
        import tempfile
        import os

        suffix = _mime_to_suffix(mime_type)
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
            f.write(audio_bytes)
            tmp_path = f.name

        try:
            return await self.transcribe_file(tmp_path)
        finally:
            os.unlink(tmp_path)

    @abstractmethod
    async def get_status(self) -> dict[str, Any]:
        """Get provider status."""
        ...


class TTSProvider(ABC):
    """Text-to-speech provider interface."""

    name: str = "base"

    @abstractmethod
    async def synthesize(self, text: str, voice: str | None = None) -> SynthesisResult:
        """Convert text to speech audio."""
        ...

    async def speak(self, text: str, voice: str | None = None) -> SynthesisResult:
        """Convenience — same as synthesize for most providers."""
        return await self.synthesize(text, voice)

    @abstractmethod
    async def get_status(self) -> dict[str, Any]:
        """Get provider status."""
        ...


def _mime_to_suffix(mime_type: str) -> str:
    """Convert MIME type to file extension."""
    mapping = {
        "audio/wav": ".wav",
        "audio/wave": ".wav",
        "audio/mp3": ".mp3",
        "audio/mpeg": ".mp3",
        "audio/webm": ".webm",
        "audio/ogg": ".ogg",
        "audio/flac": ".flac",
    }
    return mapping.get(mime_type, ".wav")

"""Voice Gateway — manages STT/TTS providers and voice pipeline."""

from __future__ import annotations

from typing import Any

from backend.core.config import settings
from backend.core.logger import logger
from backend.voice.providers.base import STTProvider, TTSProvider, TranscriptionResult, SynthesisResult


class VoiceGateway:
    """Central voice gateway — manages STT and TTS providers."""

    def __init__(self):
        self._stt_provider: STTProvider | None = None
        self._tts_provider: TTSProvider | None = None
        self._initialized = False

    def initialize(self) -> None:
        """Initialize from config."""
        if self._initialized:
            return

        stt_provider_name = getattr(settings, "stt_provider", "mock")
        tts_provider_name = getattr(settings, "tts_provider", "mock")

        # STT
        if stt_provider_name == "faster_whisper":
            from backend.voice.providers.faster_whisper import FasterWhisperProvider
            self._stt_provider = FasterWhisperProvider()
        else:
            from backend.voice.providers.mock_stt import MockSTTProvider
            self._stt_provider = MockSTTProvider()

        # TTS
        if tts_provider_name in ("mock",):
            from backend.voice.providers.mock_tts import MockTTSProvider
            self._tts_provider = MockTTSProvider()
        else:
            from backend.voice.providers.mock_tts import MockTTSProvider
            self._tts_provider = MockTTSProvider()

        self._initialized = True
        logger.info(
            "Voice Gateway initialized — STT={} TTS={}",
            self._stt_provider.name, self._tts_provider.name,
        )

    async def get_status(self) -> dict[str, Any]:
        """Get overall voice system status."""
        if not self._initialized:
            self.initialize()

        stt_status = await self._stt_provider.get_status() if self._stt_provider else {"available": False}
        tts_status = await self._tts_provider.get_status() if self._tts_provider else {"available": False}

        return {
            "voice_enabled": getattr(settings, "voice_enabled", False),
            "stt_provider": self._stt_provider.name if self._stt_provider else "none",
            "stt_available": stt_status.get("available", False),
            "tts_provider": self._tts_provider.name if self._tts_provider else "none",
            "tts_available": tts_status.get("available", False),
            "push_to_talk_enabled": True,
            "wake_word_enabled": False,
            "stt_details": stt_status,
            "tts_details": tts_status,
            "errors": [],
        }

    async def transcribe_file(self, file_path: str) -> TranscriptionResult:
        """Transcribe an audio file."""
        if not self._initialized:
            self.initialize()
        if self._stt_provider is None:
            return TranscriptionResult(text="", provider="none", error="No STT provider configured")
        return await self._stt_provider.transcribe_file(file_path)

    async def transcribe_bytes(self, audio_bytes: bytes, mime_type: str = "audio/wav") -> TranscriptionResult:
        """Transcribe audio bytes."""
        if not self._initialized:
            self.initialize()
        if self._stt_provider is None:
            return TranscriptionResult(text="", provider="none", error="No STT provider configured")
        return await self._stt_provider.transcribe_bytes(audio_bytes, mime_type)

    async def synthesize(self, text: str, voice: str | None = None) -> SynthesisResult:
        """Convert text to speech."""
        if not self._initialized:
            self.initialize()
        if self._tts_provider is None:
            return SynthesisResult(success=False, provider="none", error="No TTS provider configured")
        return await self._tts_provider.synthesize(text, voice)

    async def process_voice_command(self, file_path: str) -> dict[str, Any]:
        """Full voice pipeline: transcribe → route to assistant → return result.

        Args:
            file_path: Path to audio file

        Returns:
            Dict with transcription and assistant response
        """
        # Step 1: Transcribe
        transcription = await self.transcribe_file(file_path)
        if transcription.error:
            return {
                "transcription": transcription.model_dump(),
                "response": None,
                "error": transcription.error,
            }

        # Step 2: Route to assistant
        try:
            from backend.core.assistant import assistant
            from backend.core.schemas import UserInput

            user_input = UserInput(
                raw=transcription.text,
                source="voice",
            )
            result = assistant.process_input(user_input)
            return {
                "transcription": transcription.model_dump(),
                "response": result,
            }
        except Exception as exc:
            logger.error("Voice command routing failed: {}", exc)
            return {
                "transcription": transcription.model_dump(),
                "response": None,
                "error": str(exc),
            }


# Singleton
voice_gateway = VoiceGateway()

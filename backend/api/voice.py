"""Voice API — STT, TTS, and voice command endpoints."""

from __future__ import annotations

from fastapi import APIRouter, UploadFile, File
from pydantic import BaseModel

from backend.core.logger import logger

router = APIRouter(tags=["voice"])


class SpeakRequest(BaseModel):
    text: str
    voice: str | None = None


@router.get("/voice/status")
async def voice_status():
    """Get detailed voice system status."""
    try:
        from backend.voice.gateway import voice_gateway
        voice_gateway.initialize()
        return await voice_gateway.get_status()
    except Exception as exc:
        return {
            "voice_enabled": False,
            "stt_available": False,
            "tts_available": False,
            "errors": [str(exc)],
        }


@router.post("/voice/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """Transcribe an uploaded audio file to text.

    Accepts: WAV, MP3, WebM, OGG, FLAC
    """
    try:
        from backend.voice.gateway import voice_gateway

        # Read the file
        content = await file.read()
        mime = file.content_type or "audio/wav"

        # Transcribe
        result = await voice_gateway.transcribe_bytes(content, mime)
        return result.model_dump()
    except Exception as exc:
        logger.error("Transcription failed: {}", exc)
        return {"text": "", "language": "en", "provider": "none", "error": str(exc)}


@router.post("/voice/speak")
async def speak_text(request: SpeakRequest):
    """Convert text to speech and return audio file URL."""
    try:
        from backend.voice.gateway import voice_gateway
        result = await voice_gateway.synthesize(request.text, request.voice)
        return result.model_dump()
    except Exception as exc:
        return {"success": False, "provider": "none", "error": str(exc)}


@router.get("/voice/speak-stream")
async def speak_text_stream(text: str, voice: str | None = None):
    """Convert text to speech and stream audio directly (for <audio> elements).

    Usage: <audio src="/api/voice/speak-stream?text=Hello+world" autoplay></audio>
    """
    try:
        from backend.voice.gateway import voice_gateway
        result = await voice_gateway.synthesize(text, voice)
        if result.success and result.audio_data:
            from fastapi.responses import Response
            return Response(
                content=result.audio_data,
                media_type="audio/mpeg",
                headers={"Content-Disposition": "inline"},
            )
        return {"success": False, "error": result.error or "TTS failed"}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@router.post("/voice/command")
async def voice_command(file: UploadFile = File(...)):
    """Full voice pipeline: transcribe → route to assistant.

    Upload an audio file and get transcription + assistant response.
    """
    try:
        from backend.voice.gateway import voice_gateway
        import tempfile
        import os

        # Save uploaded file temporarily
        suffix = ".wav"
        if file.content_type:
            from backend.voice.providers.base import _mime_to_suffix
            suffix = _mime_to_suffix(file.content_type)

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
            content = await file.read()
            f.write(content)
            tmp_path = f.name

        try:
            result = await voice_gateway.process_voice_command(tmp_path)
            return result
        finally:
            os.unlink(tmp_path)

    except Exception as exc:
        logger.error("Voice command failed: {}", exc)
        return {"error": str(exc)}

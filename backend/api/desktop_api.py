"""Desktop API — screen capture, OCR, and context analysis endpoints."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from backend.desktop_capture import capture_and_ocr, analyze_screen, capture_to_base64
from backend.core.logger import logger

router = APIRouter(tags=["desktop"])


class AnalyzeRequest(BaseModel):
    question: str
    model: str | None = None
    monitor: int = 1  # 1=primary, 2=second, 0=all


class AnalyzeResponse(BaseModel):
    success: bool
    response: str = ""
    ocr_text: str = ""
    model: str = ""
    error: str | None = None


@router.post("/desktop/screenshot")
def take_screenshot():
    """Capture the screen and return base64 image + OCR text."""
    result = capture_and_ocr()
    if not result["success"]:
        return {"success": False, "error": result.get("error", "Capture failed")}
    return {
        "success": True,
        "ocr_text": result["text"],
        "text_length": result["text_length"],
        "image_preview": result["image_base64"],
    }


@router.post("/desktop/analyze", response_model=AnalyzeResponse)
def analyze_desktop(req: AnalyzeRequest):
    """Capture screen, run OCR, and ask Ollama to analyze based on user's question.

    The full pipeline:
    1. Screenshot → OCR → Send to Ollama with user's question
    2. Returns AI analysis of what's on screen

    Parameters:
        monitor: 1=primary monitor, 2=secondary, 0=all monitors

    Example questions:
    - "Cosa significa questo errore?"
    - "Riassumi questa pagina"
    - "Traduci questo paragrafo"
    - "Cosa fa questo codice?"
    """
    logger.info("Desktop analyze: '{}' (monitor {})", req.question[:100], req.monitor)
    result = analyze_screen(req.question, req.model, req.monitor)
    return AnalyzeResponse(**result)


@router.get("/desktop/ocr")
def get_ocr_text():
    """Capture screen and return OCR text only (no AI analysis)."""
    result = capture_and_ocr()
    return {
        "success": result["success"],
        "text": result.get("text", ""),
        "text_length": result.get("text_length", 0),
        "error": result.get("error"),
    }


@router.get("/desktop/screenshot-b64")
def get_screenshot_b64():
    """Capture screen and return base64 image (for display)."""
    b64 = capture_to_base64()
    if not b64:
        return {"success": False, "error": "Capture failed"}
    # Return as data URI for direct use in <img> tags
    return {
        "success": True,
        "data_uri": f"data:image/png;base64,{b64[:200]}...",
    }

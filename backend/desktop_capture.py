"""Desktop Capture — screen capture, OCR, and context analysis.

Provides:
- Screen capture (primary monitor or all monitors)
- OCR (Tesseract) for text extraction
- AI analysis of screen content
"""

from __future__ import annotations

import io
import base64
from pathlib import Path
from typing import Any

from backend.core.logger import logger


def capture_screen(monitor: int = 1) -> bytes | None:
    """Capture the primary monitor as PNG bytes.

    Args:
        monitor: Monitor index (1 = primary). Use 0 for all monitors.

    Returns:
        PNG image bytes, or None if capture fails.
    """
    try:
        import mss
        import mss.tools

        with mss.mss() as sct:
            if monitor == 0:
                # All monitors
                img = sct.shot(output="raw")
                return mss.tools.to_png(img.rgb, img.size)
            else:
                monitor_idx = min(monitor, len(sct.monitors) - 1)
                monitor_data = sct.monitors[monitor_idx]
                screenshot = sct.grab(monitor_data)
                return mss.tools.to_png(screenshot.rgb, screenshot.size)
    except ImportError:
        logger.warning("mss not installed — screen capture unavailable")
    except Exception as exc:
        logger.error("Screen capture failed: {}", exc)

    return None


def capture_to_base64(monitor: int = 1) -> str:
    """Capture screen and return as base64-encoded PNG."""
    img_bytes = capture_screen(monitor)
    if img_bytes is None:
        return ""
    return base64.b64encode(img_bytes).decode("utf-8")


def _find_tesseract() -> str | None:
    """Find tesseract.exe on the system. Returns path or None."""
    import shutil

    # 1. Already in PATH
    path = shutil.which("tesseract")
    if path:
        return path

    # 2. Common Windows install paths
    candidates = [
        Path("C:/Program Files/Tesseract-OCR/tesseract.exe"),
        Path("C:/Program Files (x86)/Tesseract-OCR/tesseract.exe"),
        Path.home() / "AppData" / "Local" / "Tesseract-OCR" / "tesseract.exe",
        Path.home() / "AppData" / "Local" / "Programs" / "Tesseract-OCR" / "tesseract.exe",
    ]
    for p in candidates:
        if p.exists():
            return str(p)

    return None


def _configure_tesseract() -> bool:
    """Configure pytesseract with the correct tesseract path. Returns True if ready."""
    try:
        import pytesseract
    except ImportError:
        return False

    # Try to find and set the path FIRST (before get_tesseract_version)
    path = _find_tesseract()
    if path:
        pytesseract.pytesseract.tesseract_cmd = path
        logger.info("Tesseract found at: {}", path)
    else:
        logger.warning(
            "Tesseract-OCR not found. Install from: "
            "https://github.com/UB-Mannheim/tesseract/wiki\n"
            "During install, check 'Add to PATH' or select Italian language pack."
        )
        return False

    # Verify it works
    try:
        version = pytesseract.get_tesseract_version()
        logger.info("Tesseract version: {}", version)
        return True
    except Exception as exc:
        logger.warning("Tesseract found but not working: {}", exc)
        return False


def ocr_image(image_bytes: bytes, language: str = "ita+eng") -> str:
    """Run OCR on an image and return extracted text.

    Args:
        image_bytes: PNG/JPEG image bytes
        language: Tesseract language string (default: ita+eng for Italian + English)

    Returns:
        Extracted text, or empty string if OCR fails.
    """
    try:
        import pytesseract
        from PIL import Image

        if not _configure_tesseract():
            return ""

        img = Image.open(io.BytesIO(image_bytes))
        text = pytesseract.image_to_string(img, lang=language)
        return text.strip()
    except ImportError:
        logger.warning("pytesseract not installed — OCR unavailable")
    except Exception as exc:
        logger.warning("OCR failed — is Tesseract installed? Error: {}", exc)

    return ""


def capture_and_ocr(monitor: int = 1, language: str = "ita+eng") -> dict[str, Any]:
    """Capture screen, run OCR, and return results.

    Returns:
        Dict with 'image_base64', 'text', 'success'.
    """
    img_bytes = capture_screen(monitor)
    if img_bytes is None:
        return {"success": False, "error": "Screen capture failed."}

    image_b64 = base64.b64encode(img_bytes).decode("utf-8")
    text = ocr_image(img_bytes, language)

    return {
        "success": True,
        "image_base64": image_b64[:200] + "..." if len(image_b64) > 200 else image_b64,
        "text": text,
        "text_length": len(text),
    }


def analyze_screen(user_question: str, model: str | None = None) -> dict[str, Any]:
    """Capture screen, OCR, and ask Ollama to analyze it.

    This is the full pipeline:
    1. Capture screenshot
    2. Run OCR to extract text
    3. Send screenshot context + user question to Ollama
    4. Return the AI response

    Args:
        user_question: What the user wants to know (e.g., "Cosa significa questo errore?")
        model: Ollama model to use (falls back to configured default)

    Returns:
        Dict with 'response', 'ocr_text', 'image_base64', 'success'
    """
    from backend.core.config import settings

    # 1. Capture + OCR
    img_bytes = capture_screen(1)
    if img_bytes is None:
        return {"success": False, "error": "Screen capture failed.", "response": "Impossibile catturare lo schermo."}

    ocr_text = ocr_image(img_bytes)

    # 2. Build prompt for Ollama
    system_prompt = (
        "Sei JARVIS, un assistente desktop che AIUTA L'UTENTE IN TEMPO REALE. "
        "L'utente sta guardando il suo schermo e ti fa una domanda. "
        "Stai ricevendo il TESTO estratto via OCR da ciò che è visibile sullo schermo. "
        "Rispondi in ITALIANO, in modo CONCISO e UTILE (massimo 3-5 frasi). "
        "Se il testo OCR contiene un errore (es. errore di compilazione, eccezione, messaggio di sistema), "
        "SPIEGALO in modo chiaro e suggerisci come risolverlo. "
        "Se è una pagina web o un documento, riassumi o traduci come richiesto. "
        "Sii diretto e pratico."
    )

    if ocr_text:
        user_prompt = (
            f"L'utente chiede: \"{user_question}\"\n\n"
            f"TESTO VISIBILE SULLO SCHERMO (OCR):\n{ocr_text[:3000]}\n\n"
            f"Analizza il testo sullo schermo e rispondi alla domanda dell'utente."
        )
    else:
        user_prompt = (
            f"L'utente chiede: \"{user_question}\"\n\n"
            f"(Nessun testo rilevato sullo schermo)\n\n"
            f"Rispondi alla domanda dell'utente basandoti sulla tua conoscenza generale."
        )

    # 3. Call Ollama
    import requests

    ollama_url = (getattr(settings.llm, 'base_url', 'http://localhost:11434') or 'http://localhost:11434').rstrip('/')
    ollama_model = model or getattr(settings.llm, 'chat_model', 'qwen2.5:7b') or 'qwen2.5:7b'

    try:
        r = requests.post(
            f"{ollama_url}/api/chat",
            json={
                "model": ollama_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "stream": False,
                "options": {"temperature": 0.3},
            },
            timeout=60,
        )

        if r.status_code == 200:
            response_text = r.json().get("message", {}).get("content", "")
            return {
                "success": True,
                "response": response_text,
                "ocr_text": ocr_text[:500],
                "model": ollama_model,
            }
        else:
            return {
                "success": False,
                "error": f"Ollama returned {r.status_code}",
                "response": "Errore di connessione a Ollama. Assicurati che sia in esecuzione.",
                "ocr_text": ocr_text[:500],
            }
    except Exception as exc:
        logger.warning("Ollama call failed in analyze_screen: {}", exc)
        return {
            "success": False,
            "error": str(exc),
            "response": "Ollama non è raggiungibile. Avvia Ollama e riprova.",
            "ocr_text": ocr_text[:500],
        }

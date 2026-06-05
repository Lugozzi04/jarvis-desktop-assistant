"""Study API — upload, summarize, flashcards, quiz, spaced repetition."""

from __future__ import annotations

from fastapi import APIRouter, UploadFile, File, Form
from pydantic import BaseModel

from backend.study.engine import study_engine
from backend.core.logger import logger

router = APIRouter(tags=["study"])


# ── Request/Response Models ──

class TextUploadRequest(BaseModel):
    text: str
    title: str = ""


class GenerateRequest(BaseModel):
    count: int = 10


class ReviewRequest(BaseModel):
    card_id: str
    quality: int  # 0-5


class QuizGenerateRequest(BaseModel):
    count: int = 5


# ── Materials ──

@router.get("/study/materials")
def list_materials():
    """List all study materials."""
    return {"materials": study_engine.list_materials()}


@router.get("/study/materials/{material_id}")
def get_material(material_id: str):
    """Get a full study material with flashcards and quiz questions."""
    material = study_engine.get_material(material_id)
    if material is None:
        return {"error": "Material not found."}
    return material


@router.delete("/study/materials/{material_id}")
def delete_material(material_id: str):
    """Delete a study material."""
    success = study_engine.delete_material(material_id)
    if not success:
        return {"error": "Material not found."}
    return {"deleted": material_id}


@router.post("/study/materials/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    """Upload and process a PDF file."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        return {"error": "Only PDF files are supported."}

    try:
        content = await file.read()
    except Exception as exc:
        return {"error": f"Failed to read file: {exc}"}

    if len(content) == 0:
        return {"error": "Empty file."}

    logger.info("Study: received PDF '{}' ({} bytes)", file.filename, len(content))
    return study_engine.upload_pdf(content, file.filename)


@router.post("/study/materials/upload-text")
def upload_text(req: TextUploadRequest):
    """Create a study material from raw text."""
    return study_engine.upload_text(req.text, req.title)


# ── AI Processing ──

@router.post("/study/materials/{material_id}/summarize")
def generate_summary(material_id: str):
    """Generate an AI summary of the study material."""
    return study_engine.generate_summary(material_id)


@router.post("/study/materials/{material_id}/flashcards")
def generate_flashcards(material_id: str, req: GenerateRequest | None = None):
    """Generate flashcards for a study material."""
    count = req.count if req else 10
    return study_engine.generate_flashcards(material_id, count)


@router.post("/study/materials/{material_id}/quiz")
def generate_quiz(material_id: str, req: QuizGenerateRequest | None = None):
    """Generate multiple-choice quiz questions."""
    count = req.count if req else 5
    return study_engine.generate_quiz(material_id, count)


# ── Spaced Repetition ──

@router.post("/study/materials/{material_id}/review")
def review_flashcard(material_id: str, req: ReviewRequest):
    """Review a flashcard with SM-2 quality score (0-5)."""
    return study_engine.review_flashcard(material_id, req.card_id, req.quality)


@router.get("/study/materials/{material_id}/due")
def get_due_flashcards(material_id: str):
    """Get flashcards due for review."""
    return study_engine.get_due_flashcards(material_id)

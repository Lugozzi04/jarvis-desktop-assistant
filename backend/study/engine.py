"""Study Engine — PDF processing, flashcard generation, quiz, spaced repetition."""

from __future__ import annotations

import json
import random
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.core.config import settings
from backend.core.logger import logger


# ── Flashcard Model ──

class Flashcard:
    """A single flashcard with SM-2 spaced repetition data."""

    def __init__(
        self,
        front: str,
        back: str,
        card_id: str | None = None,
        easiness: float = 2.5,
        interval: int = 0,
        repetitions: int = 0,
        next_review: str | None = None,
        created_at: str | None = None,
    ):
        self.id = card_id or str(uuid.uuid4())[:8]
        self.front = front
        self.back = back
        self.easiness = easiness
        self.interval = interval
        self.repetitions = repetitions
        self.next_review = next_review or ""
        self.created_at = created_at or datetime.now(timezone.utc).isoformat()

    def review(self, quality: int) -> None:
        """SM-2 algorithm: update card after review. quality: 0-5."""
        quality = max(0, min(5, quality))

        if quality >= 3:
            if self.repetitions == 0:
                self.interval = 1
            elif self.repetitions == 1:
                self.interval = 6
            else:
                self.interval = int(round(self.interval * self.easiness))
            self.repetitions += 1
        else:
            self.repetitions = 0
            self.interval = 1

        self.easiness = max(1.3, self.easiness + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))

        # Next review: now + interval days
        from datetime import timedelta
        next_dt = datetime.now(timezone.utc) + timedelta(days=self.interval)
        self.next_review = next_dt.isoformat()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "front": self.front,
            "back": self.back,
            "easiness": self.easiness,
            "interval": self.interval,
            "repetitions": self.repetitions,
            "next_review": self.next_review,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Flashcard:
        return cls(
            front=d["front"],
            back=d["back"],
            card_id=d.get("id"),
            easiness=d.get("easiness", 2.5),
            interval=d.get("interval", 0),
            repetitions=d.get("repetitions", 0),
            next_review=d.get("next_review", ""),
            created_at=d.get("created_at", ""),
        )


# ── Quiz Question ──

class QuizQuestion:
    """A multiple-choice quiz question."""

    def __init__(
        self,
        question: str,
        options: list[str],
        correct_index: int,
        explanation: str = "",
    ):
        self.question = question
        self.options = options
        self.correct_index = correct_index
        self.explanation = explanation

    def to_dict(self) -> dict:
        return {
            "question": self.question,
            "options": self.options,
            "correct_index": self.correct_index,
            "explanation": self.explanation,
        }


# ── Study Material ──

class StudyMaterial:
    """A study material (uploaded PDF, text, or URL)."""

    def __init__(
        self,
        material_id: str | None = None,
        title: str = "",
        content: str = "",
        source: str = "",
        summary: str = "",
        flashcards: list[Flashcard] | None = None,
        quiz_questions: list[QuizQuestion] | None = None,
        created_at: str | None = None,
    ):
        self.id = material_id or str(uuid.uuid4())[:8]
        self.title = title
        self.content = content
        self.source = source
        self.summary = summary
        self.flashcards = flashcards or []
        self.quiz_questions = quiz_questions or []
        self.created_at = created_at or datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content[:500] + "..." if len(self.content) > 500 else self.content,
            "source": self.source,
            "summary": self.summary,
            "flashcard_count": len(self.flashcards),
            "quiz_question_count": len(self.quiz_questions),
            "created_at": self.created_at,
        }

    def to_full_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "source": self.source,
            "summary": self.summary,
            "flashcards": [f.to_dict() for f in self.flashcards],
            "quiz_questions": [q.to_dict() for q in self.quiz_questions],
            "created_at": self.created_at,
        }


# ── Study Engine ──

class StudyEngine:
    """Core study engine — processes materials, generates flashcards & quizzes."""

    def __init__(self):
        self._materials: dict[str, StudyMaterial] = {}
        self._data_dir = settings.data_path / "study"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._load()

    def _storage_path(self) -> Path:
        return self._data_dir / "study_data.json"

    def _load(self) -> None:
        """Load study data from disk."""
        p = self._storage_path()
        if not p.exists():
            return
        try:
            data = json.loads(p.read_text())
            for m in data.get("materials", []):
                mat = StudyMaterial(
                    material_id=m["id"],
                    title=m["title"],
                    content=m.get("content", ""),
                    source=m.get("source", ""),
                    summary=m.get("summary", ""),
                    flashcards=[Flashcard.from_dict(f) for f in m.get("flashcards", [])],
                    created_at=m.get("created_at", ""),
                )
                self._materials[mat.id] = mat
            logger.info("Study engine loaded: {} materials", len(self._materials))
        except Exception as exc:
            logger.warning("Failed to load study data: {}", exc)

    def _save(self) -> None:
        """Save study data to disk."""
        try:
            data = {
                "materials": [
                    m.to_full_dict() for m in self._materials.values()
                ]
            }
            self._storage_path().write_text(json.dumps(data, indent=2))
        except Exception as exc:
            logger.error("Failed to save study data: {}", exc)

    # ── Material Management ──

    def list_materials(self) -> list[dict]:
        """List all study materials."""
        return [m.to_dict() for m in self._materials.values()]

    def get_material(self, material_id: str) -> dict | None:
        """Get a full study material by ID."""
        mat = self._materials.get(material_id)
        if mat is None:
            return None
        return mat.to_full_dict()

    def delete_material(self, material_id: str) -> bool:
        """Delete a study material."""
        if material_id not in self._materials:
            return False
        del self._materials[material_id]
        self._save()
        return True

    def upload_pdf(self, file_content: bytes, filename: str) -> dict:
        """Process an uploaded PDF and extract text."""
        text = ""
        try:
            import fitz  # pymupdf
            doc = fitz.open(stream=file_content, filetype="pdf")
            pages = []
            for page in doc:
                pages.append(page.get_text())
            doc.close()
            text = "\n\n".join(pages)
            logger.info("PDF extracted: {} — {} chars, {} pages", filename, len(text), len(pages))
        except Exception as exc:
            logger.error("PDF extraction failed: {}", exc)
            return {"error": f"Failed to extract PDF: {exc}"}

        if not text.strip():
            return {"error": "PDF contained no extractable text."}

        title = filename.replace(".pdf", "").replace("_", " ").replace("-", " ")
        material = StudyMaterial(
            title=title,
            content=text,
            source=filename,
        )
        self._materials[material.id] = material
        self._save()

        return {
            "material": material.to_full_dict(),
            "char_count": len(text),
        }

    def upload_text(self, text: str, title: str) -> dict:
        """Create a study material from raw text."""
        if not text.strip():
            return {"error": "Text is empty."}

        material = StudyMaterial(
            title=title or "Untitled",
            content=text,
            source="text",
        )
        self._materials[material.id] = material
        self._save()

        return {
            "material": material.to_full_dict(),
            "char_count": len(text),
        }

    # ── AI Processing (via Ollama) ──

    def _call_ollama(self, system_prompt: str, user_prompt: str, language: str = "it") -> str:
        """Call Ollama for AI processing."""
        import requests

        ollama_url = (getattr(settings.llm, 'base_url', 'http://localhost:11434') or 'http://localhost:11434').rstrip('/')
        model = getattr(settings.llm, 'chat_model', 'qwen2.5:7b') or 'qwen2.5:7b'

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {"temperature": 0.3},
        }

        try:
            r = requests.post(f"{ollama_url}/api/chat", json=payload, timeout=120)
            if r.status_code == 200:
                return r.json().get("message", {}).get("content", "")
            logger.warning("Ollama returned {} for study engine", r.status_code)
        except Exception as exc:
            logger.warning("Ollama call failed in study engine: {}", exc)

        return ""

    def generate_summary(self, material_id: str) -> dict:
        """Generate an AI summary of the study material."""
        mat = self._materials.get(material_id)
        if mat is None:
            return {"error": "Material not found."}

        if not mat.content.strip():
            return {"error": "Material has no content."}

        # Truncate if too long
        content = mat.content[:8000]

        system_prompt = (
            "Sei un assistente di studio. Riassumi il seguente testo in italiano. "
            "Il riassunto deve essere: 5 punti chiave, chiaro, conciso, utile per studiare. "
            "Usa un formato a elenco puntato. Massimo 300 parole."
        )
        user_prompt = f"Testo da riassumere:\n\n{content}"

        summary = self._call_ollama(system_prompt, user_prompt)
        if summary:
            mat.summary = summary
            self._save()

        return {
            "material_id": material_id,
            "summary": summary or "Summary generation failed (Ollama may be offline).",
        }

    def generate_flashcards(self, material_id: str, count: int = 10) -> dict:
        """Generate flashcards from the study material using AI."""
        mat = self._materials.get(material_id)
        if mat is None:
            return {"error": "Material not found."}

        if not mat.content.strip():
            return {"error": "Material has no content."}

        content = mat.content[:8000]

        system_prompt = (
            "Sei un assistente di studio. Genera flashcard (domanda e risposta) dal testo fornito. "
            "Rispondi SOLO con un JSON valido in questo formato esatto:\n"
            f'{{"flashcards": [{{"front": "domanda", "back": "risposta"}}, ...]}}\n'
            f"Genera esattamente {count} flashcard. Le domande devono coprire i concetti chiave."
        )
        user_prompt = f"Testo:\n\n{content}"

        result = self._call_ollama(system_prompt, user_prompt)
        flashcards = []

        if result:
            try:
                # Extract JSON from response
                json_match = re.search(r'\{[\s\S]*\}', result)
                if json_match:
                    data = json.loads(json_match.group(0))
                    for item in data.get("flashcards", []):
                        fc = Flashcard(front=item["front"], back=item["back"])
                        flashcards.append(fc)
            except (json.JSONDecodeError, KeyError, IndexError) as exc:
                logger.warning("Failed to parse flashcards JSON: {}", exc)
                # Fallback: generate simple Q&A from text
                flashcards = self._fallback_flashcards(mat.content, count)

        if not flashcards:
            flashcards = self._fallback_flashcards(mat.content, count)

        mat.flashcards = flashcards
        self._save()

        return {
            "material_id": material_id,
            "flashcards": [f.to_dict() for f in flashcards],
            "count": len(flashcards),
        }

    def _fallback_flashcards(self, content: str, count: int = 10) -> list[Flashcard]:
        """Generate simple flashcards by extracting key sentences."""
        sentences = [s.strip() for s in re.split(r'[.!?]+', content) if len(s.strip()) > 30]
        if len(sentences) < 2:
            return [Flashcard(
                front="Qual è il contenuto principale del testo?",
                back=content[:200] + "..."
            )]

        flashcards = []
        # Take every Nth sentence as a card
        step = max(1, len(sentences) // min(count, len(sentences)))
        for i in range(0, len(sentences), step):
            if len(flashcards) >= count:
                break
            sentence = sentences[i][:300]
            # Create a question by removing a key term
            words = sentence.split()
            if len(words) > 5:
                key_word_idx = min(len(words) - 1, len(words) // 2)
                key_word = words[key_word_idx]
                question = " ".join(words[:key_word_idx]) + " _______ " + " ".join(words[key_word_idx + 1:])
                question = f"Completa: {question[:200]}"
                flashcards.append(Flashcard(front=question, back=sentence[:300]))
            else:
                flashcards.append(Flashcard(front="Spiega questo concetto:", back=sentence[:300]))

        return flashcards

    def generate_quiz(self, material_id: str, count: int = 5) -> dict:
        """Generate multiple-choice quiz questions from the material."""
        mat = self._materials.get(material_id)
        if mat is None:
            return {"error": "Material not found."}

        if not mat.content.strip():
            return {"error": "Material has no content."}

        content = mat.content[:8000]

        system_prompt = (
            "Sei un assistente di studio. Genera domande a scelta multipla dal testo. "
            "Rispondi SOLO con un JSON valido in questo formato esatto:\n"
            '{"questions": [{"question": "...", "options": ["A", "B", "C", "D"], '
            '"correct_index": 0, "explanation": "..."}]}\n'
            "correct_index è 0-based. Genera esattamente {} domande. "
            "Le domande devono testare la comprensione, non la memorizzazione."
        )

        user_prompt = f"Testo:\n\n{content}"

        result = self._call_ollama(system_prompt, user_prompt)
        questions = []

        if result:
            try:
                json_match = re.search(r'\{[\s\S]*\}', result)
                if json_match:
                    data = json.loads(json_match.group(0))
                    for item in data.get("questions", []):
                        q = QuizQuestion(
                            question=item["question"],
                            options=item["options"],
                            correct_index=item["correct_index"],
                            explanation=item.get("explanation", ""),
                        )
                        questions.append(q)
            except (json.JSONDecodeError, KeyError, IndexError) as exc:
                logger.warning("Failed to parse quiz JSON: {}", exc)

        if not questions:
            # Fallback: generate simple Q&A
            questions = self._fallback_quiz(mat.content, count)

        mat.quiz_questions = questions
        self._save()

        return {
            "material_id": material_id,
            "questions": [q.to_dict() for q in questions[:count]],
            "count": len(questions[:count]),
        }

    def _fallback_quiz(self, content: str, count: int = 5) -> list[QuizQuestion]:
        """Generate simple quiz questions from sentences."""
        sentences = [s.strip() for s in re.split(r'[.!?]+', content) if len(s.strip()) > 50]
        if not sentences:
            return [QuizQuestion(
                question="Qual è l'argomento principale del testo?",
                options=["Non definito", "Da determinare", "Vedi testo", "Nessuna delle precedenti"],
                correct_index=0,
                explanation="Il testo richiede ulteriore analisi.",
            )]

        questions = []
        for i, sentence in enumerate(sentences[:count * 2]):
            if len(questions) >= count:
                break
            words = sentence.split()
            if len(words) < 8:
                continue
            # Make a true statement and 3 false ones
            true_answer = sentence[:200]
            false_answers = []
            for j, other in enumerate(sentences):
                if j != i and len(false_answers) < 3:
                    false_answers.append(other[:200] if len(other) > 50 else "Informazione non corretta.")
            while len(false_answers) < 3:
                false_answers.append(f"Opzione alternativa {len(false_answers) + 1}")

            correct = 0  # True answer is at index 0
            options = [true_answer] + false_answers
            random.shuffle(options)
            correct = options.index(true_answer)

            questions.append(QuizQuestion(
                question=f"Quale affermazione è corretta riguardo al testo?",
                options=options,
                correct_index=correct,
                explanation="La risposta corretta è direttamente dal testo.",
            ))

        return questions

    def review_flashcard(self, material_id: str, card_id: str, quality: int) -> dict:
        """Review a flashcard with SM-2 quality score (0-5)."""
        mat = self._materials.get(material_id)
        if mat is None:
            return {"error": "Material not found."}

        for fc in mat.flashcards:
            if fc.id == card_id:
                fc.review(quality)
                self._save()
                return fc.to_dict()

        return {"error": "Flashcard not found."}

    def get_due_flashcards(self, material_id: str) -> dict:
        """Get flashcards that are due for review."""
        mat = self._materials.get(material_id)
        if mat is None:
            return {"error": "Material not found."}

        now = datetime.now(timezone.utc)
        due = []
        for fc in mat.flashcards:
            if not fc.next_review:
                due.append(fc)
            else:
                try:
                    review_dt = datetime.fromisoformat(fc.next_review)
                    if review_dt <= now:
                        due.append(fc)
                except (ValueError, TypeError):
                    due.append(fc)

        return {
            "material_id": material_id,
            "due_count": len(due),
            "total_count": len(mat.flashcards),
            "flashcards": [f.to_dict() for f in due],
        }


# ── Singleton ──

study_engine = StudyEngine()

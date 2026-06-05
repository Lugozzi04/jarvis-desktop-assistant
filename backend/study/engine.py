"""Study Engine — PDF processing, flashcard generation, quiz, spaced repetition.

COMPLETELY REWRITTEN — v2.0
- Multi-chunk processing for long documents (no more 8000-char limit)
- World-class AI prompts for summaries, flashcards, and quizzes
- Temperature tuning per task (creative summaries, precise JSON)
- Smart fallbacks that actually extract key information
- Model override support for better models
"""

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


# ═══════════════════════════════════════════════════════════════
# Data Models
# ═══════════════════════════════════════════════════════════════

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
        from datetime import timedelta
        next_dt = datetime.now(timezone.utc) + timedelta(days=self.interval)
        self.next_review = next_dt.isoformat()

    def to_dict(self) -> dict:
        return {
            "id": self.id, "front": self.front, "back": self.back,
            "easiness": self.easiness, "interval": self.interval,
            "repetitions": self.repetitions, "next_review": self.next_review,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Flashcard:
        return cls(
            front=d["front"], back=d["back"], card_id=d.get("id"),
            easiness=d.get("easiness", 2.5), interval=d.get("interval", 0),
            repetitions=d.get("repetitions", 0), next_review=d.get("next_review", ""),
            created_at=d.get("created_at", ""),
        )


class QuizQuestion:
    """A multiple-choice quiz question."""

    def __init__(self, question: str, options: list[str], correct_index: int, explanation: str = ""):
        self.question = question
        self.options = options
        self.correct_index = correct_index
        self.explanation = explanation

    def to_dict(self) -> dict:
        return {
            "question": self.question, "options": self.options,
            "correct_index": self.correct_index, "explanation": self.explanation,
        }


class StudyMaterial:
    """A study material (uploaded PDF, text, or URL)."""

    def __init__(
        self, material_id: str | None = None, title: str = "", content: str = "",
        source: str = "", summary: str = "",
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
            "id": self.id, "title": self.title,
            "content": self.content[:500] + "..." if len(self.content) > 500 else self.content,
            "source": self.source, "summary": self.summary,
            "flashcard_count": len(self.flashcards), "quiz_question_count": len(self.quiz_questions),
            "created_at": self.created_at,
        }

    def to_full_dict(self) -> dict:
        return {
            "id": self.id, "title": self.title, "content": self.content,
            "source": self.source, "summary": self.summary,
            "flashcards": [f.to_dict() for f in self.flashcards],
            "quiz_questions": [q.to_dict() for q in self.quiz_questions],
            "created_at": self.created_at,
        }


# ═══════════════════════════════════════════════════════════════
# Study Engine
# ═══════════════════════════════════════════════════════════════

class StudyEngine:
    """Core study engine — processes materials, generates flashcards & quizzes.

    v2.0: Multi-chunk processing, world-class prompts, temperature tuning.
    """

    def __init__(self):
        self._materials: dict[str, StudyMaterial] = {}
        self._data_dir = settings.data_path / "study"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._load()

    # ── Persistence ──

    def _storage_path(self) -> Path:
        return self._data_dir / "study_data.json"

    def _load(self) -> None:
        p = self._storage_path()
        if not p.exists():
            return
        try:
            data = json.loads(p.read_text())
            for m in data.get("materials", []):
                mat = StudyMaterial(
                    material_id=m["id"], title=m["title"],
                    content=m.get("content", ""), source=m.get("source", ""),
                    summary=m.get("summary", ""),
                    flashcards=[Flashcard.from_dict(f) for f in m.get("flashcards", [])],
                    created_at=m.get("created_at", ""),
                )
                self._materials[mat.id] = mat
            logger.info("Study engine loaded: {} materials", len(self._materials))
        except Exception as exc:
            logger.warning("Failed to load study data: {}", exc)

    def _save(self) -> None:
        try:
            data = {"materials": [m.to_full_dict() for m in self._materials.values()]}
            self._storage_path().write_text(json.dumps(data, indent=2))
        except Exception as exc:
            logger.error("Failed to save study data: {}", exc)

    # ── Material Management ──

    def list_materials(self) -> list[dict]:
        return [m.to_dict() for m in self._materials.values()]

    def get_material(self, material_id: str) -> dict | None:
        mat = self._materials.get(material_id)
        return mat.to_full_dict() if mat else None

    def delete_material(self, material_id: str) -> bool:
        if material_id not in self._materials:
            return False
        del self._materials[material_id]
        self._save()
        return True

    def upload_pdf(self, file_content: bytes, filename: str) -> dict:
        """Process an uploaded PDF and extract ALL text from ALL pages."""
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
        material = StudyMaterial(title=title, content=text, source=filename)
        self._materials[material.id] = material
        self._save()

        return {"material": material.to_full_dict(), "char_count": len(text)}

    def upload_text(self, text: str, title: str) -> dict:
        """Create a study material from raw text."""
        if not text.strip():
            return {"error": "Text is empty."}

        material = StudyMaterial(title=title or "Untitled", content=text, source="text")
        self._materials[material.id] = material
        self._save()

        return {"material": material.to_full_dict(), "char_count": len(text)}

    # ═══════════════════════════════════════════════════════════
    # AI Processing Core
    # ═══════════════════════════════════════════════════════════

    def _chunk_text(self, text: str, chunk_size: int = 6000, overlap: int = 500) -> list[str]:
        """Split text into overlapping chunks for processing long documents."""
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            # Try to break at a sentence boundary
            if end < len(text):
                # Look for sentence end within last 300 chars
                search_start = max(end - 300, start + chunk_size // 2)
                best = end
                for sep in ['.\n', '.\n\n', '. ', '.\n', '.\n\n', '. ', '!\n', '?\n', '.\n\n', '. \n']:
                    pos = text.rfind(sep, search_start, end)
                    if pos > search_start:
                        best = pos + 1
                        break
                end = best
            chunks.append(text[start:end].strip())
            start = end - overlap

        logger.info("Chunked text: {} chars → {} chunks", len(text), len(chunks))
        return chunks

    def _get_model(self, override_model: str | None = None) -> str:
        """Get the model to use, with optional override."""
        if override_model:
            return override_model
        # Use chat model from settings if configured, otherwise default
        return getattr(settings.llm, 'chat_model', None) or \
               getattr(settings.llm, 'default_model', None) or \
               'qwen2.5:7b'

    def _call_ollama(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        model_override: str | None = None,
        max_tokens: int = 2048,
    ) -> str:
        """Call Ollama for AI processing with configurable temperature and model."""
        import requests

        ollama_url = (getattr(settings.llm, 'base_url', 'http://localhost:11434') or 'http://localhost:11434').rstrip('/')
        model = self._get_model(model_override)

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        try:
            r = requests.post(f"{ollama_url}/api/chat", json=payload, timeout=180)
            if r.status_code == 200:
                result = r.json().get("message", {}).get("content", "")
                logger.info("Ollama response: {} chars, model={}, temp={}", len(result), model, temperature)
                return result
            logger.warning("Ollama returned {} for study engine", r.status_code)
        except Exception as exc:
            logger.warning("Ollama call failed in study engine: {}", exc)

        return ""

    # ═══════════════════════════════════════════════════════════
    # SUMMARIZE — Multi-stage, world-class quality
    # ═══════════════════════════════════════════════════════════

    def _summarize_chunk(self, text: str, chunk_num: int, total_chunks: int, model: str | None = None) -> str:
        """Summarize a single text chunk."""
        system_prompt = (
            "Sei un assistente di studio di livello universitario. Il tuo compito è "
            "estrarre i concetti PIÙ IMPORTANTI dal testo fornito.\n\n"
            "REGOLE:\n"
            "- Estrai SOLO le informazioni essenziali: definizioni, teorie, dati chiave, nomi importanti.\n"
            "- NON riassumere riga per riga — sintetizza concettualmente.\n"
            "- Mantieni la precisione accademica. Non inventare nulla.\n"
            "- Scrivi in italiano chiaro e formale.\n"
            "- Formato: elenco puntato con •, ogni punto 1-2 frasi.\n"
            "- Massimo 10 punti.\n"
            f"- Questa è la parte {chunk_num} di {total_chunks}."
        )

        user_prompt = f"Testo da analizzare (parte {chunk_num}/{total_chunks}):\n\n{text}"

        return self._call_ollama(system_prompt, user_prompt, temperature=0.5, model_override=model)

    def generate_summary(self, material_id: str, model_override: str | None = None) -> dict:
        """Generate an EXCELLENT structured summary — multi-stage for long texts."""
        mat = self._materials.get(material_id)
        if mat is None:
            return {"error": "Material not found."}
        if not mat.content.strip():
            return {"error": "Material has no content."}

        content = mat.content
        model = self._get_model(model_override)

        if len(content) <= 8000:
            # Single-stage summary for short texts
            system_prompt = (
                "Sei un assistente di studio universitario ECCELLENTE. "
                "Devi produrre un riassunto STRUTTURATO e COMPLETO del testo fornito.\n\n"
                "IL RIASSUNTO DEVE AVERE QUESTA STRUTTURA ESATTA:\n\n"
                "## 📋 Panoramica Generale\n"
                "2-3 frasi che catturano l'essenza del documento.\n\n"
                "## 🔑 Concetti Chiave (3-5)\n"
                "• [Concetto 1]: spiegazione in 1-2 frasi\n"
                "• [Concetto 2]: spiegazione in 1-2 frasi\n"
                "...\n\n"
                "## 📊 Punti Dettagliati (5-10)\n"
                "• [Punto 1]: spiegazione concreta con esempi se presenti\n"
                "• [Punto 2]: ...\n"
                "...\n\n"
                "## 📚 Glossario / Terminologia\n"
                "• **Termine**: definizione\n"
                "...\n\n"
                "REGOLE FONDAMENTALI:\n"
                "- NON tralasciare nessun concetto importante.\n"
                "- Usa un linguaggio CHIARO e PRECISO.\n"
                "- Se il testo contiene dati, numeri, date: INCLUDILI.\n"
                "- NON fare vaghi riassunti — sii SPECIFICO e CONCRETO.\n"
                "- Scrivi TUTTO in italiano.\n"
                "- Lunghezza: 400-800 parole."
            )

            user_prompt = f"Documento da riassumere:\n\n{content[:10000]}"
            summary = self._call_ollama(system_prompt, user_prompt, temperature=0.6, model_override=model_override, max_tokens=2048)
        else:
            # Multi-stage: summarize chunks, then synthesize
            chunks = self._chunk_text(content, chunk_size=6000, overlap=400)
            logger.info("Multi-stage summary: {} chunks for {} chars", len(chunks), len(content))

            # Stage 1: Summarize each chunk
            chunk_summaries = []
            for i, chunk in enumerate(chunks):
                logger.info("Summarizing chunk {}/{}...", i + 1, len(chunks))
                cs = self._summarize_chunk(chunk, i + 1, len(chunks), model_override)
                if cs:
                    chunk_summaries.append(cs)

            if not chunk_summaries:
                return {"material_id": material_id, "summary": "Summary generation failed — Ollama may be offline."}

            # Stage 2: Synthesize all chunk summaries into final summary
            combined = "\n\n---\n\n".join(chunk_summaries)
            system_prompt_synth = (
                "Sei un assistente di studio universitario ECCELLENTE. "
                "Hai ricevuto i riassunti parziali di diverse sezioni di un documento. "
                "Devi SINTETIZZARLI in un unico riassunto COERENTE e STRUTTURATO.\n\n"
                "STRUTTURA RICHIESTA:\n\n"
                "## 📋 Panoramica Generale\n"
                "3-4 frasi che catturano l'essenza COMPLESSIVA del documento.\n\n"
                "## 🔑 Concetti Fondamentali (5-8)\n"
                "• [Concetto]: spiegazione chiara\n...\n\n"
                "## 📊 Analisi Dettagliata (8-15 punti)\n"
                "• [Punto specifico con dettagli concreti]\n...\n\n"
                "## 📚 Glossario\n"
                "• **Termine**: definizione\n...\n\n"
                "## 💡 Implicazioni / Collegamenti\n"
                "2-3 frasi su come i concetti si collegano tra loro.\n\n"
                "REGOLE:\n"
                "- NON perdere informazioni importanti dai riassunti parziali.\n"
                "- Sii PRECISO e CONCRETO.\n"
                "- Lunghezza: 500-1000 parole.\n"
                "- Scrivi TUTTO in italiano."
            )

            user_prompt_synth = (
                f"Riassunti parziali di un documento di {len(content)} caratteri "
                f"(elaborato in {len(chunks)} sezioni):\n\n{combined}"
            )
            summary = self._call_ollama(system_prompt_synth, user_prompt_synth, temperature=0.6, model_override=model_override, max_tokens=3072)

        if summary:
            mat.summary = summary
            self._save()

        return {"material_id": material_id, "summary": summary or "Summary generation failed (Ollama may be offline)."}

    # ═══════════════════════════════════════════════════════════
    # FLASHCARDS — Multi-chunk, high quality
    # ═══════════════════════════════════════════════════════════

    def generate_flashcards(self, material_id: str, count: int = 20, model_override: str | None = None) -> dict:
        """Generate HIGH-QUALITY flashcards — processes all chunks, not just first 8000 chars."""
        mat = self._materials.get(material_id)
        if mat is None:
            return {"error": "Material not found."}
        if not mat.content.strip():
            return {"error": "Material has no content."}

        content = mat.content
        model = self._get_model(model_override)
        all_flashcards: list[Flashcard] = []

        # Determine chunk strategy
        if len(content) <= 8000:
            chunks = [content]
            cards_per_chunk = count
        else:
            chunks = self._chunk_text(content, chunk_size=6000, overlap=400)
            # Distribute card count across chunks
            cards_per_chunk = max(3, count // len(chunks))
            logger.info("Multi-chunk flashcards: {} chunks, {} cards/chunk", len(chunks), cards_per_chunk)

        for i, chunk in enumerate(chunks):
            logger.info("Generating flashcards for chunk {}/{}...", i + 1, len(chunks))

            prompt = (
                "Sei un assistente di studio che crea flashcard di ALTA QUALITÀ per l'apprendimento.\n\n"
                "Dal testo fornito, crea flashcard che coprano i concetti PIÙ IMPORTANTI.\n\n"
                "TIPI DI FLASHCARD DA CREARE:\n"
                "- **Definizioni**: 'Cos'è X?' → definizione precisa\n"
                "- **Concetti**: 'Spiega il concetto di Y' → spiegazione chiara\n"
                "- **Confronti**: 'Qual è la differenza tra A e B?' → confronto\n"
                "- **Applicazioni**: 'Come si applica Z nella pratica?' → esempio concreto\n"
                "- **Cause/Effetti**: 'Quali sono le cause di W?' → spiegazione\n\n"
                "REGOLE:\n"
                f"- Genera ESATTAMENTE {cards_per_chunk} flashcard.\n"
                "- Il 'front' deve essere una domanda CHIARA e SPECIFICA (non vaga).\n"
                "- Il 'back' deve essere una risposta COMPLETA (2-5 frasi).\n"
                "- NON generare flashcard banali o ovvie.\n"
                "- Copri i concetti CHIAVE del testo, non dettagli irrilevanti.\n"
                "- Scrivi TUTTO in italiano.\n\n"
                "Rispondi SOLO con un JSON valido in questo formato ESATTO:\n"
                '{"flashcards": [{"front": "domanda specifica", "back": "risposta dettagliata"}, ...]}'
            )

            result = self._call_ollama(prompt, f"Testo (parte {i+1}/{len(chunks)}):\n\n{chunk}", temperature=0.2, model_override=model_override)
            cards = self._parse_flashcards_json(result)
            if cards:
                all_flashcards.extend(cards)

        # If AI failed, use smart fallback
        if not all_flashcards:
            all_flashcards = self._smart_fallback_flashcards(mat.content, count)

        # Deduplicate by front text similarity
        all_flashcards = self._deduplicate_flashcards(all_flashcards)

        # Cap to requested count
        all_flashcards = all_flashcards[:count]

        mat.flashcards = all_flashcards
        self._save()

        return {
            "material_id": material_id,
            "flashcards": [f.to_dict() for f in all_flashcards],
            "count": len(all_flashcards),
        }

    def _parse_flashcards_json(self, result: str) -> list[Flashcard]:
        """Parse JSON flashcard response."""
        if not result:
            return []
        try:
            json_match = re.search(r'\{[\s\S]*\}', result)
            if json_match:
                data = json.loads(json_match.group(0))
                cards = []
                for item in data.get("flashcards", []):
                    cards.append(Flashcard(front=item["front"], back=item["back"]))
                return cards
        except (json.JSONDecodeError, KeyError, IndexError) as exc:
            logger.warning("Failed to parse flashcards JSON: {}", exc)
        return []

    def _deduplicate_flashcards(self, cards: list[Flashcard]) -> list[Flashcard]:
        """Remove near-duplicate flashcards."""
        seen = set()
        unique = []
        for card in cards:
            # Normalize front for comparison
            key = re.sub(r'\s+', ' ', card.front.lower().strip())[:80]
            if key not in seen:
                seen.add(key)
                unique.append(card)
        return unique

    def _smart_fallback_flashcards(self, content: str, count: int = 20) -> list[Flashcard]:
        """Intelligent fallback: extract key sentences by importance heuristics."""
        sentences = [s.strip() for s in re.split(r'[.!?\n]+', content) if len(s.strip()) > 40]
        if len(sentences) < 2:
            return [Flashcard(front="Qual è il contenuto principale?", back=content[:300])]

        # Score sentences by keyword density and position
        scored = []
        for i, s in enumerate(sentences):
            # Keywords: capitalized words, numbers, technical terms
            caps = len(re.findall(r'\b[A-ZÀ-Ü][a-zà-ü]+\b', s))
            nums = len(re.findall(r'\d+', s))
            length = len(s)
            # Position bonus: first 20% and last 10% of document are more important
            pos_bonus = 0
            if i < len(sentences) * 0.2:
                pos_bonus = 3
            elif i > len(sentences) * 0.9:
                pos_bonus = 1
            score = caps * 2 + nums + (length / 100) + pos_bonus
            scored.append((score, s))

        scored.sort(reverse=True, key=lambda x: x[0])

        flashcards = []
        for _, sentence in scored[:count]:
            words = sentence.split()
            if len(words) > 5:
                # Create cloze deletion
                key_idx = min(len(words) - 1, len(words) // 2)
                key_word = words[key_idx]
                front = " ".join(words[:key_idx]) + " _______ " + " ".join(words[key_idx + 1:])
                flashcards.append(Flashcard(
                    front=f"Completa: {front[:250]}",
                    back=sentence[:400]
                ))

        return flashcards

    # ═══════════════════════════════════════════════════════════
    # QUIZ — Multi-chunk, 20+ questions, diverse types
    # ═══════════════════════════════════════════════════════════

    def generate_quiz(self, material_id: str, count: int = 20, model_override: str | None = None) -> dict:
        """Generate RICH quiz questions — processes ALL chunks for comprehensive coverage."""
        mat = self._materials.get(material_id)
        if mat is None:
            return {"error": "Material not found."}
        if not mat.content.strip():
            return {"error": "Material has no content."}

        content = mat.content
        model = self._get_model(model_override)
        all_questions: list[QuizQuestion] = []

        # Determine chunk strategy
        if len(content) <= 8000:
            chunks = [content]
            q_per_chunk = count
        else:
            chunks = self._chunk_text(content, chunk_size=6000, overlap=400)
            q_per_chunk = max(3, count // len(chunks))
            logger.info("Multi-chunk quiz: {} chunks, {} questions/chunk", len(chunks), q_per_chunk)

        for i, chunk in enumerate(chunks):
            logger.info("Generating quiz questions for chunk {}/{}...", i + 1, len(chunks))

            prompt = (
                "Sei un assistente di studio universitario che crea QUIZ DI ALTA QUALITÀ.\n\n"
                "Dal testo fornito, crea domande a scelta multipla che TESTINO LA COMPRENSIONE PROFONDA.\n\n"
                "TIPI DI DOMANDE DA CREARE (distribuite equamente):\n"
                "1. **Fattuali**: 'Quale delle seguenti affermazioni è vera riguardo a X?'\n"
                "2. **Concettuali**: 'Qual è il principio fondamentale dietro Y?'\n"
                "3. **Applicative**: 'In quale scenario si applicherebbe Z?'\n"
                "4. **Comparative**: 'Qual è la principale differenza tra A e B?'\n"
                "5. **Inferenziali**: 'Cosa si può dedurre dal fatto che...?'\n\n"
                "REGOLE FONDAMENTALI:\n"
                f"- Genera ESATTAMENTE {q_per_chunk} domande.\n"
                "- Ogni domanda deve avere 4 opzioni (A, B, C, D).\n"
                "- SOLO UNA opzione deve essere corretta.\n"
                "- Le opzioni errate devono essere PLAUSIBILI (non ovviamente sbagliate).\n"
                "- Ogni domanda deve avere una 'explanation' che spiega PERCHÉ la risposta è corretta.\n"
                "- Le domande devono coprire CONCETTI DIVERSI (non tutte sullo stesso argomento).\n"
                "- Varia la DIFFICOLTÀ: 1 facile, 2 media, 1 difficile (per blocco di 4).\n"
                "- Scrivi TUTTO in italiano.\n\n"
                "Rispondi SOLO con un JSON valido in questo formato ESATTO:\n"
                '{"questions": [\n'
                '  {"question": "domanda?", "options": ["A", "B", "C", "D"],\n'
                '   "correct_index": 0, "explanation": "spiegazione dettagliata"},\n'
                '  ...\n'
                ']}\n'
                "correct_index è 0-based (0=A, 1=B, 2=C, 3=D)."
            )

            result = self._call_ollama(prompt, f"Testo (parte {i+1}/{len(chunks)}):\n\n{chunk}", temperature=0.3, model_override=model_override, max_tokens=3072)
            questions = self._parse_quiz_json(result)
            if questions:
                all_questions.extend(questions)

        # Fallback if AI completely failed
        if not all_questions:
            all_questions = self._smart_fallback_quiz(mat.content, count)

        # Deduplicate by question text
        seen = set()
        unique = []
        for q in all_questions:
            key = re.sub(r'\s+', ' ', q.question.lower().strip())[:80]
            if key not in seen:
                seen.add(key)
                unique.append(q)

        all_questions = unique[:count]

        mat.quiz_questions = all_questions
        self._save()

        return {
            "material_id": material_id,
            "questions": [q.to_dict() for q in all_questions],
            "count": len(all_questions),
        }

    def _parse_quiz_json(self, result: str) -> list[QuizQuestion]:
        """Parse JSON quiz response."""
        if not result:
            return []
        try:
            json_match = re.search(r'\{[\s\S]*\}', result)
            if json_match:
                data = json.loads(json_match.group(0))
                questions = []
                for item in data.get("questions", []):
                    q = QuizQuestion(
                        question=item["question"],
                        options=item["options"],
                        correct_index=item["correct_index"],
                        explanation=item.get("explanation", ""),
                    )
                    questions.append(q)
                return questions
        except (json.JSONDecodeError, KeyError, IndexError) as exc:
            logger.warning("Failed to parse quiz JSON: {}", exc)
        return []

    def _smart_fallback_quiz(self, content: str, count: int = 20) -> list[QuizQuestion]:
        """Intelligent quiz fallback — extract key facts and create questions."""
        sentences = [s.strip() for s in re.split(r'[.!?\n]+', content) if len(s.strip()) > 60]
        if not sentences:
            return [QuizQuestion(
                question="Qual è l'argomento principale del documento?",
                options=["Non determinabile", "Vedi il testo completo", "Analisi richiesta", "Nessuna delle precedenti"],
                correct_index=1,
                explanation="Senza il testo completo, non è possibile determinare l'argomento."
            )]

        # Use TF-IDF-like scoring to find important sentences
        # Count word frequency across all sentences
        word_freq: dict[str, int] = {}
        for s in sentences:
            for w in re.findall(r'\b[a-zà-üèéìòù]{4,}\b', s.lower()):
                word_freq[w] = word_freq.get(w, 0) + 1

        # Score sentences: important words × position bonus
        scored_sentences = []
        for i, s in enumerate(sentences):
            important_words = sum(1 for w in re.findall(r'\b[a-zà-üèéìòù]{4,}\b', s.lower()) if word_freq.get(w, 0) > 2)
            pos_bonus = 3 if i < len(sentences) * 0.15 else (1 if i > len(sentences) * 0.85 else 0)
            scored_sentences.append((important_words + pos_bonus, s))

        scored_sentences.sort(reverse=True, key=lambda x: x[0])
        top = [s for _, s in scored_sentences[:count * 2] if len(s) > 60]

        questions = []
        used = set()
        for truth in top:
            if len(questions) >= count:
                break
            # Pick 3 other sentences as wrong options
            distractors = [s for s in top if s != truth and s not in used][:3]
            while len(distractors) < 3:
                distractors.append(f"Opzione alternativa {len(distractors) + 1}")
            used.add(truth)

            options = [truth[:200]] + [d[:200] for d in distractors]
            random.shuffle(options)
            correct_idx = options.index(truth[:200])

            questions.append(QuizQuestion(
                question="Quale affermazione è corretta secondo il testo?",
                options=options,
                correct_index=correct_idx,
                explanation="Questa informazione è presente nel testo originale."
            ))

        return questions

    # ═══════════════════════════════════════════════════════════
    # Spaced Repetition
    # ═══════════════════════════════════════════════════════════

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


# Singleton
study_engine = StudyEngine()

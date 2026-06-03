"""Chat API — natural language and slash command input with conversation history."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from backend.chat_store import conversation_store
from backend.core.assistant import assistant
from backend.core.config import settings
from backend.core.schemas import UserInput
from backend.core.logger import logger

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"
    source: str = "text"


class ChatResponse(BaseModel):
    response: str
    intent: dict | None = None
    result: dict | None = None
    needs_confirmation: bool = False
    confirmation_message: str = ""
    duration_ms: float = 0.0


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """Process a chat message through the full JARVIS pipeline with history."""
    conv_id = request.session_id if request.session_id != "default" else None
    is_slash = request.message.strip().startswith("/")

    if conv_id:
        conversation_store.add_message(conv_id, "user", request.message)

    user_input = UserInput(
        raw=request.message,
        source=request.source,
        session_id=request.session_id,
    )
    result = assistant.process_input(user_input)
    response_text = result["response"]

    # For non-slash messages in a conversation, use LLM with full context
    if conv_id and not is_slash:
        response_text = _chat_with_context(conv_id, request.message, response_text)

    if conv_id and response_text:
        conversation_store.add_message(conv_id, "assistant", response_text)

    return ChatResponse(
        response=response_text,
        intent=result["intent"],
        result=result["result"],
        needs_confirmation=result["needs_confirmation"],
        confirmation_message=result["confirmation_message"],
        duration_ms=result["duration_ms"],
    )


def _chat_with_context(conv_id: str, user_message: str, fallback: str) -> str:
    """ONE call to Ollama with: history + web search + language.

    Tries models in order: mistral:7b → llama3.2:3b → qwen2.5:7b (fallback).
    Strong Italian system prompt prevents model from switching languages.
    """
    try:
        import requests

        # ── 1. Conversation history ──
        history = conversation_store.get_context_messages(conv_id, max_messages=20)

        # ── 2. Web search (Italian region, filtered) ──
        web_context = ""
        try:
            from backend.skills.web_search.search_provider import search_web, format_results
            results = search_web(user_message, max_results=5)
            if results:
                # Filter out non-Italian/non-English results
                filtered = _filter_results_by_language(results)
                if filtered:
                    web_context = format_results(user_message, filtered)
        except Exception as exc:
            logger.debug("Web search in chat failed: {}", exc)

        # ── 3. Language ──
        lang = "it"
        try:
            from backend.api.settings import get_language
            lang = get_language()
        except Exception:
            pass

        # ── 4. System prompt ──
        if lang == "it":
            system_content = (
                "Sei JARVIS, un assistente virtuale italiano. "
                "PARLI ESCLUSIVAMENTE IN ITALIANO. Non usare mai il cinese, "
                "l'inglese o qualsiasi altra lingua. "
                "Rispondi in modo conciso, preciso e utile. "
                "Usa la cronologia della conversazione per mantenere il contesto. "
                "Se ti vengono forniti risultati di ricerca web in italiano, usali "
                "per risposte accurate e aggiornate. "
                "Se i risultati di ricerca sono in altre lingue, IGNORALI e rispondi "
                "usando solo la tua conoscenza interna IN ITALIANO."
            )
        else:
            system_content = (
                "You are JARVIS, a helpful desktop assistant. Respond concisely in English. "
                "Use conversation history for context. "
                "If web search results are provided, use them for accurate answers. "
                "Always cite sources when using web data."
            )

        # ── 5. User prompt ──
        user_content = user_message
        if web_context:
            user_content = (
                f"RISULTATI RICERCA WEB (usa solo se in italiano):\n{web_context}\n\n"
                f"DOMANDA UTENTE: {user_message}"
            )

        # ── 6. Messages array ──
        messages = [{"role": "system", "content": system_content}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_content})

        logger.info(
            "Chat: {} history msgs, {} web chars, lang={}",
            len(history), len(web_context), lang,
        )

        # ── 7. Ollama call with model fallback ──
        ollama_url = settings.llm.base_url or "http://localhost:11434"
        models_to_try = [
            settings.llm.chat_model,       # configured: default mistral:7b
            "llama3.2:3b",                  # good fallback for Italian
            "qwen2.5:7b",                   # last resort
        ]

        for model in models_to_try:
            try:
                r = requests.post(
                    f"{ollama_url}/api/chat",
                    json={
                        "model": model,
                        "messages": messages,
                        "stream": False,
                        "options": {"temperature": 0.5},
                    },
                    timeout=45,
                )
                if r.status_code == 200:
                    content = r.json().get("message", {}).get("content", "")
                    if content and len(content.strip()) > 10:
                        logger.info("Chat response from model: {}", model)
                        return content
                else:
                    logger.debug("Model {} returned status {}", model, r.status_code)
            except Exception as exc:
                logger.debug("Model {} failed: {}", model, exc)
                continue

        # ── 8. All models failed → return web results or fallback ──
        if web_context:
            return (
                f"🌐 **Risultati ricerca web** (Ollama non disponibile):\n\n"
                f"{web_context}\n\n"
                f"_Installa Ollama e un modello italiano: `ollama pull mistral:7b`_"
            )

    except Exception as exc:
        logger.warning("Chat context failed: {}", exc)

    return fallback


def _filter_results_by_language(results: list[dict[str, str]]) -> list[dict[str, str]]:
    """Keep only results likely in Italian or English. Filter out Chinese, Japanese, etc."""
    # CJK Unicode ranges
    cjk_ranges = [
        (0x4E00, 0x9FFF),   # CJK Unified Ideographs
        (0x3400, 0x4DBF),   # CJK Unified Ideographs Extension A
        (0x3040, 0x309F),   # Hiragana
        (0x30A0, 0x30FF),   # Katakana
        (0xAC00, 0xD7AF),   # Hangul
    ]

    def has_cjk(text: str) -> bool:
        for ch in text:
            cp = ord(ch)
            for lo, hi in cjk_ranges:
                if lo <= cp <= hi:
                    return True
        return False

    filtered = []
    for r in results:
        text = (r.get("title", "") + " " + r.get("snippet", ""))
        if not has_cjk(text):
            filtered.append(r)

    # If filtering removed everything, return original (better than nothing)
    return filtered if filtered else results

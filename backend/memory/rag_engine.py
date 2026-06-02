"""RAG Engine — Question answering over indexed documents.

Pipeline:
  1. Receive question
  2. Generate query embedding
  3. Search top_k chunks
  4. Build context from chunks
  5. Send to LLM Gateway if available, else return search results
  6. Return answer with sources
"""

from __future__ import annotations

from backend.core.logger import logger
from backend.memory.embeddings import get_embedding_provider, EmbeddingProvider
from backend.memory.vector_store import get_vector_store, VectorStore
from backend.memory.models import SearchResult, RAGAnswer


RAG_PROMPT_TEMPLATE = """You are Jarvis, a desktop assistant. Answer the user's question using ONLY the provided document context below.

If the context contains the answer, provide it clearly with references to the source documents.
If the context does NOT contain enough information to answer, say so explicitly — do NOT make up information.
Always cite which documents you used.

--- DOCUMENT CONTEXT ---
{context}

--- QUESTION ---
{question}

Answer:"""


class RagEngine:
    """Retrieval-Augmented Generation engine for document Q&A."""

    def __init__(
        self,
        vector_store: VectorStore | None = None,
        embedding_provider: EmbeddingProvider | None = None,
    ):
        self.store = vector_store or get_vector_store()
        self.embedding_provider = embedding_provider or get_embedding_provider()

    async def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        """Search documents by semantic similarity. No LLM needed."""
        try:
            query_embedding = await self.embedding_provider.embed(query)
        except Exception as exc:
            logger.warning("Failed to generate query embedding: {}", exc)
            return []

        results = self.store.search(query_embedding, top_k=top_k)
        logger.info(
            "Document search: '{}' → {} results (provider={})",
            query[:60], len(results), self.embedding_provider.name,
        )
        return results

    async def ask(
        self,
        question: str,
        top_k: int = 5,
        max_context_chars: int = 6000,
    ) -> RAGAnswer:
        """Answer a question using RAG — search then LLM generation.

        If LLM is not available, returns search results with a fallback message.
        """
        # Step 1: Search for relevant chunks
        search_results = await self.search(question, top_k=top_k)

        if not search_results:
            return RAGAnswer(
                question=question,
                answer="No relevant documents found. Try indexing some documents first, or rephrase your question.",
                sources=[],
                provider=self.embedding_provider.name,
            )

        # Step 2: Build context from chunks
        context_parts = []
        total_chars = 0
        seen_ids = set()
        used_results = []

        for result in search_results:
            if result.chunk_id in seen_ids:
                continue
            chunk_text = result.text_preview
            if total_chars + len(chunk_text) > max_context_chars:
                chunk_text = chunk_text[:max_context_chars - total_chars]
            context_parts.append(
                f"[Source: {result.filename} (chunk {result.chunk_index})]\n{chunk_text}"
            )
            total_chars += len(chunk_text)
            seen_ids.add(result.chunk_id)
            used_results.append(result)
            if total_chars >= max_context_chars:
                break

        context = "\n\n---\n\n".join(context_parts)

        # Step 3: Try LLM generation
        prompt = RAG_PROMPT_TEMPLATE.format(context=context, question=question)

        try:
            from backend.llm.gateway import llm_gateway
            import asyncio

            available = False
            try:
                available = asyncio.run(llm_gateway.is_available()) if not asyncio.get_event_loop().is_running() else False
            except Exception:
                pass

            if available:
                try:
                    response = await llm_gateway.generate(prompt)
                    return RAGAnswer(
                        question=question,
                        answer=response,
                        sources=used_results,
                        provider=f"rag+{self.embedding_provider.name}",
                    )
                except Exception as exc:
                    logger.warning("LLM generation failed, falling back to search-only: {}", exc)
        except Exception:
            pass

        # Step 4: Fallback — return search results
        fallback_answer = self._build_fallback_answer(question, used_results)
        return RAGAnswer(
            question=question,
            answer=fallback_answer,
            sources=used_results,
            provider=self.embedding_provider.name,
            error="LLM not available — showing search results only",
        )

    def _build_fallback_answer(self, question: str, results: list[SearchResult]) -> str:
        """Build a fallback answer when LLM is not available."""
        if not results:
            return "No documents found."

        lines = [
            f"I found {len(results)} relevant document chunks for your question:",
            "",
        ]
        for i, r in enumerate(results, 1):
            lines.append(f"**{i}. {r.filename}** (chunk {r.chunk_index}, score: {r.score:.2f})")
            preview = r.text_preview[:200].replace("\n", " ")
            lines.append(f"> {preview}...")
            lines.append("")

        lines.append("---")
        lines.append("💡 *Tip: Set up an LLM (Ollama or OpenAI-compatible) to get AI-generated answers.*")
        return "\n".join(lines)


# ── Singleton ──

_rag_engine: RagEngine | None = None


def get_rag_engine() -> RagEngine:
    global _rag_engine
    if _rag_engine is None:
        _rag_engine = RagEngine()
    return _rag_engine

"""Document Memory Skill — Index, search, and ask about local documents."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.core.logger import logger
from backend.core.permissions import RiskLevel
from backend.skills.base import BaseSkill, ActionResult


class DocumentsSkill(BaseSkill):
    """Index and query local documents with semantic search."""

    def __init__(self):
        super().__init__("documents")

    def execute(self, action: str, params: dict[str, Any]) -> ActionResult:
        import asyncio

        actions: dict[str, Any] = {
            "index_file": self._index_file,
            "index_folder": self._index_folder,
            "search_documents": self._search_documents,
            "ask_documents": self._ask_documents,
            "list_documents": self._list_documents,
            "remove_document": self._remove_document,
            "clear_index": self._clear_index,
        }

        handler = actions.get(action)
        if handler is None:
            return ActionResult(
                success=False,
                skill="documents",
                action=action,
                result="",
                error=f"Unknown action: {action}",
            )

        try:
            result = asyncio.run(handler(params))
            return result
        except Exception as exc:
            logger.error("Documents skill error: {}", exc)
            return ActionResult(
                success=False,
                skill="documents",
                action=action,
                result="",
                error=str(exc),
            )

    async def _index_file(self, params: dict[str, Any]) -> ActionResult:
        from backend.memory.indexer import get_indexer

        path = params.get("path", "")
        if not path:
            return ActionResult(
                success=False, skill="documents", action="index_file",
                result="", error="Missing 'path' parameter",
            )

        indexer = get_indexer()
        doc = await indexer.index_file(path)

        if doc.status.value == "error":
            return ActionResult(
                success=False, skill="documents", action="index_file",
                result=f"Failed to index {doc.filename}: {doc.error}",
                error=doc.error,
            )

        return ActionResult(
            success=True, skill="documents", action="index_file",
            result=f"Indexed: {doc.filename} — {doc.chunk_count} chunks (provider: {indexer.embedding_provider.name})",
        )

    async def _index_folder(self, params: dict[str, Any]) -> ActionResult:
        from backend.memory.indexer import get_indexer

        folder_path = params.get("folder_path", "")
        recursive = params.get("recursive", True)

        if not folder_path:
            return ActionResult(
                success=False, skill="documents", action="index_folder",
                result="", error="Missing 'folder_path' parameter",
            )

        indexer = get_indexer()
        docs = await indexer.index_folder(folder_path, recursive=recursive)

        indexed = sum(1 for d in docs if d.status.value == "indexed")
        failed = sum(1 for d in docs if d.status.value == "error")

        return ActionResult(
            success=True, skill="documents", action="index_folder",
            result=f"Indexed {indexed} files from {folder_path} ({failed} failed). {len(docs)} total.",
        )

    async def _search_documents(self, params: dict[str, Any]) -> ActionResult:
        from backend.memory.rag_engine import get_rag_engine

        query = params.get("query", "")
        top_k = int(params.get("top_k", 5))

        if not query:
            return ActionResult(
                success=False, skill="documents", action="search_documents",
                result="", error="Missing 'query' parameter",
            )

        engine = get_rag_engine()
        results = await engine.search(query, top_k=top_k)

        if not results:
            return ActionResult(
                success=True, skill="documents", action="search_documents",
                result="No matching documents found.",
            )

        lines = [f"Found {len(results)} results:\n"]
        for i, r in enumerate(results, 1):
            lines.append(f"{i}. **{r.filename}** (chunk {r.chunk_index}, score: {r.score:.2f})")
            lines.append(f"   {r.text_preview[:150]}...\n")

        return ActionResult(
            success=True, skill="documents", action="search_documents",
            result="\n".join(lines),
        )

    async def _ask_documents(self, params: dict[str, Any]) -> ActionResult:
        from backend.memory.rag_engine import get_rag_engine

        question = params.get("question", "")
        top_k = int(params.get("top_k", 5))

        if not question:
            return ActionResult(
                success=False, skill="documents", action="ask_documents",
                result="", error="Missing 'question' parameter",
            )

        engine = get_rag_engine()
        rag_answer = await engine.ask(question, top_k=top_k)

        return ActionResult(
            success=True, skill="documents", action="ask_documents",
            result=rag_answer.answer,
        )

    async def _list_documents(self, params: dict[str, Any]) -> ActionResult:
        from backend.memory.vector_store import get_vector_store

        store = get_vector_store()
        docs = store.list_documents()

        if not docs:
            return ActionResult(
                success=True, skill="documents", action="list_documents",
                result="No documents indexed yet. Use /docs index <path> to add one.",
            )

        lines = [f"📚 {len(docs)} indexed documents:\n"]
        for doc in docs:
            status_icon = "✅" if doc.status.value == "indexed" else "❌"
            lines.append(
                f"{status_icon} **{doc.filename}** — {doc.chunk_count} chunks "
                f"({doc.file_type}, {doc.size_bytes:,} bytes)"
            )

        return ActionResult(
            success=True, skill="documents", action="list_documents",
            result="\n".join(lines),
        )

    async def _remove_document(self, params: dict[str, Any]) -> ActionResult:
        from backend.memory.vector_store import get_vector_store

        doc_id = params.get("document_id", "")
        if not doc_id:
            return ActionResult(
                success=False, skill="documents", action="remove_document",
                result="", error="Missing 'document_id' parameter",
            )

        store = get_vector_store()
        doc = store.get_document(doc_id)
        if not doc:
            return ActionResult(
                success=False, skill="documents", action="remove_document",
                result="", error=f"Document not found: {doc_id}",
            )

        store.delete_document(doc_id)
        return ActionResult(
            success=True, skill="documents", action="remove_document",
            result=f"Removed: {doc.filename}",
        )

    async def _clear_index(self, params: dict[str, Any]) -> ActionResult:
        from backend.memory.vector_store import get_vector_store

        store = get_vector_store()
        status = store.get_status()
        store.clear()

        return ActionResult(
            success=True, skill="documents", action="clear_index",
            result=f"Cleared all documents ({status['documents']} docs, {status['chunks']} chunks)",
        )

    @property
    def risk_level(self) -> RiskLevel:
        return RiskLevel.CONFIRMATION

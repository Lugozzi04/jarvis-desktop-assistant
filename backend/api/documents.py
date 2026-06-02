"""Documents API — REST endpoints for document memory and RAG."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.core.logger import logger
from backend.memory.indexer import get_indexer
from backend.memory.rag_engine import get_rag_engine
from backend.memory.vector_store import get_vector_store
from backend.memory.embeddings import get_embedding_provider
from backend.memory.models import (
    DocumentIndexRequest,
    DocumentIndexFolderRequest,
    DocumentSearchRequest,
    DocumentAskRequest,
    MemoryStatus,
)

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.get("")
def list_documents(status: str | None = None):
    """List all indexed documents."""
    store = get_vector_store()
    docs = store.list_documents(status=status)
    return {
        "documents": [d.model_dump() for d in docs],
        "count": len(docs),
    }


@router.get("/status")
def get_status():
    """Get document memory status."""
    store = get_vector_store()
    provider = get_embedding_provider()
    store_status = store.get_status()

    return MemoryStatus(
        documents=store_status["documents"],
        chunks=store_status["chunks"],
        embedding_provider=provider.name,
        ready=provider.available,
    )


@router.post("/index")
async def index_file(req: DocumentIndexRequest):
    """Index a single file."""
    indexer = get_indexer()
    doc = await indexer.index_file(req.path)

    if doc.status.value == "error":
        raise HTTPException(status_code=400, detail=doc.error or "Failed to index file")

    return {"document": doc.model_dump()}


@router.post("/index-folder")
async def index_folder(req: DocumentIndexFolderRequest):
    """Index all supported files in a folder."""
    indexer = get_indexer()
    docs = await indexer.index_folder(
        folder_path=req.folder_path,
        recursive=req.recursive,
        include_patterns=req.include_patterns if req.include_patterns != ["*.*"] else None,
        exclude_patterns=req.exclude_patterns,
    )

    indexed = sum(1 for d in docs if d.status.value == "indexed")
    failed = sum(1 for d in docs if d.status.value == "error")

    return {
        "documents": [d.model_dump() for d in docs],
        "total": len(docs),
        "indexed": indexed,
        "failed": failed,
    }


@router.get("/{document_id}")
def get_document(document_id: str):
    """Get a document by ID."""
    store = get_vector_store()
    doc = store.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    chunks = store.get_chunks_for_document(document_id)
    return {
        "document": doc.model_dump(),
        "chunks": [c.model_dump() for c in chunks],
    }


@router.delete("/{document_id}")
def delete_document(document_id: str):
    """Remove a document and its chunks from the index."""
    store = get_vector_store()
    doc = store.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    store.delete_document(document_id)
    logger.info("Deleted document: {} ({})", doc.filename, document_id)
    return {"deleted": document_id, "filename": doc.filename}


@router.post("/search")
async def search_documents(req: DocumentSearchRequest):
    """Search documents by semantic similarity."""
    engine = get_rag_engine()
    results = await engine.search(req.query, top_k=req.top_k)
    return {
        "query": req.query,
        "results": [r.model_dump() for r in results],
        "count": len(results),
    }


@router.post("/ask")
async def ask_documents(req: DocumentAskRequest):
    """Ask a question and get an answer based on your documents."""
    engine = get_rag_engine()
    answer = await engine.ask(req.question, top_k=req.top_k)
    return answer.model_dump()


@router.post("/clear")
def clear_index():
    """Clear all documents and chunks from the index. Confirmation required."""
    store = get_vector_store()
    status = store.get_status()
    store.clear()
    logger.info("Document index cleared: {} docs, {} chunks", status["documents"], status["chunks"])
    return {
        "cleared": True,
        "documents_removed": status["documents"],
        "chunks_removed": status["chunks"],
    }

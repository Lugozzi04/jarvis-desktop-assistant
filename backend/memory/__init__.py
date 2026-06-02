"""Document Memory — RAG module for Jarvis Desktop Assistant.

Architecture:
  memory/extractors.py — Text and PDF extraction
  memory/chunker.py   — Text chunking with overlap
  memory/embeddings.py — Embedding providers (mock, simple, ollama)
  memory/vector_store.py — SQLite-backed vector store with cosine similarity
  memory/indexer.py   — Document indexing pipeline
  memory/rag_engine.py — RAG query → search → answer pipeline
  memory/models.py     — Pydantic models
"""

from backend.memory.models import (
    Document,
    DocumentChunk,
    SearchResult,
    RAGAnswer,
    DocumentStatus,
)
from backend.memory.extractors import get_extractor, TextExtractor, PdfExtractor
from backend.memory.chunker import chunk_text, ChunkResult
from backend.memory.embeddings import get_embedding_provider, EmbeddingProvider
from backend.memory.vector_store import VectorStore, get_vector_store
from backend.memory.indexer import DocumentIndexer, get_indexer
from backend.memory.rag_engine import RagEngine, get_rag_engine

__all__ = [
    "Document",
    "DocumentChunk",
    "SearchResult",
    "RAGAnswer",
    "DocumentStatus",
    "get_extractor",
    "TextExtractor",
    "PdfExtractor",
    "chunk_text",
    "ChunkResult",
    "get_embedding_provider",
    "EmbeddingProvider",
    "VectorStore",
    "get_vector_store",
    "DocumentIndexer",
    "get_indexer",
    "RagEngine",
    "get_rag_engine",
]

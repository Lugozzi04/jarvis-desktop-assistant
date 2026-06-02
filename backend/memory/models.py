"""Document memory models — Pydantic schemas for documents, chunks, search, and RAG."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DocumentStatus(str, enum.Enum):
    pending = "pending"
    indexing = "indexing"
    indexed = "indexed"
    error = "error"


class Document(BaseModel):
    id: str = ""
    path: str
    filename: str
    file_type: str
    size_bytes: int = 0
    status: DocumentStatus = DocumentStatus.pending
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    chunk_count: int = 0
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    indexed_at: str | None = None


class DocumentChunk(BaseModel):
    id: str = ""
    document_id: str
    chunk_index: int
    text: str
    token_count: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchResult(BaseModel):
    document_id: str
    filename: str
    chunk_id: str
    chunk_index: int
    score: float
    text_preview: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class RAGAnswer(BaseModel):
    question: str
    answer: str
    sources: list[SearchResult] = Field(default_factory=list)
    provider: str = "none"
    error: str | None = None


class DocumentIndexRequest(BaseModel):
    path: str
    recursive: bool = False


class DocumentIndexFolderRequest(BaseModel):
    folder_path: str
    recursive: bool = True
    include_patterns: list[str] = Field(default_factory=lambda: ["*.*"])
    exclude_patterns: list[str] = Field(default_factory=lambda: [".git", "node_modules", ".venv", "__pycache__"])


class DocumentSearchRequest(BaseModel):
    query: str
    top_k: int = 5


class DocumentAskRequest(BaseModel):
    question: str
    top_k: int = 5


class MemoryStatus(BaseModel):
    documents: int = 0
    chunks: int = 0
    embedding_provider: str = "none"
    ready: bool = False
    error: str | None = None

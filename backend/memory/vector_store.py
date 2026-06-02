"""Vector Store — SQLite-backed with cosine similarity search.

Stores document chunks and their embeddings in SQLite.
Simple, zero-dependency, works offline. 
Ready to swap in ChromaDB or LanceDB later via the same interface.
"""

from __future__ import annotations

import json
import math
import sqlite3
import uuid
from pathlib import Path
from threading import Lock
from typing import Any

from backend.core.logger import logger
from backend.memory.models import Document, DocumentChunk, SearchResult, DocumentStatus


class VectorStore:
    """SQLite-backed vector store with cosine similarity."""

    def __init__(self, db_path: str = "data/memory.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_db(self):
        with self._lock:
            conn = self._get_conn()
            try:
                conn.executescript("""
                    CREATE TABLE IF NOT EXISTS documents (
                        id TEXT PRIMARY KEY,
                        path TEXT NOT NULL,
                        filename TEXT NOT NULL,
                        file_type TEXT NOT NULL DEFAULT '',
                        size_bytes INTEGER DEFAULT 0,
                        status TEXT DEFAULT 'pending',
                        error TEXT,
                        metadata_json TEXT DEFAULT '{}',
                        chunk_count INTEGER DEFAULT 0,
                        created_at TEXT DEFAULT (datetime('now')),
                        indexed_at TEXT
                    );

                    CREATE TABLE IF NOT EXISTS chunks (
                        id TEXT PRIMARY KEY,
                        document_id TEXT NOT NULL,
                        chunk_index INTEGER NOT NULL,
                        text TEXT NOT NULL,
                        token_count INTEGER DEFAULT 0,
                        embedding_json TEXT NOT NULL DEFAULT '[]',
                        metadata_json TEXT DEFAULT '{}',
                        FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
                    );

                    CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id);
                """)
                conn.commit()
            finally:
                conn.close()

    # ── Document operations ──

    def add_document(self, doc: Document) -> str:
        if not doc.id:
            doc.id = str(uuid.uuid4())
        with self._lock:
            conn = self._get_conn()
            try:
                conn.execute(
                    """INSERT OR REPLACE INTO documents 
                       (id, path, filename, file_type, size_bytes, status, error, 
                        metadata_json, chunk_count, created_at, indexed_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        doc.id, doc.path, doc.filename, doc.file_type,
                        doc.size_bytes, doc.status.value, doc.error,
                        json.dumps(doc.metadata), doc.chunk_count,
                        doc.created_at, doc.indexed_at,
                    ),
                )
                conn.commit()
                return doc.id
            finally:
                conn.close()

    def get_document(self, doc_id: str) -> Document | None:
        conn = self._get_conn()
        try:
            row = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
            if row is None:
                return None
            return Document(
                id=row["id"],
                path=row["path"],
                filename=row["filename"],
                file_type=row["file_type"],
                size_bytes=row["size_bytes"],
                status=DocumentStatus(row["status"]),
                error=row["error"],
                metadata=json.loads(row["metadata_json"]),
                chunk_count=row["chunk_count"],
                created_at=row["created_at"],
                indexed_at=row["indexed_at"],
            )
        finally:
            conn.close()

    def list_documents(self, status: str | None = None) -> list[Document]:
        conn = self._get_conn()
        try:
            if status:
                rows = conn.execute(
                    "SELECT * FROM documents WHERE status = ? ORDER BY indexed_at DESC",
                    (status,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM documents ORDER BY indexed_at DESC"
                ).fetchall()
            return [
                Document(
                    id=row["id"],
                    path=row["path"],
                    filename=row["filename"],
                    file_type=row["file_type"],
                    size_bytes=row["size_bytes"],
                    status=DocumentStatus(row["status"]),
                    error=row["error"],
                    metadata=json.loads(row["metadata_json"]),
                    chunk_count=row["chunk_count"],
                    created_at=row["created_at"],
                    indexed_at=row["indexed_at"],
                )
                for row in rows
            ]
        finally:
            conn.close()

    def delete_document(self, doc_id: str) -> bool:
        with self._lock:
            conn = self._get_conn()
            try:
                cursor = conn.execute("DELETE FROM chunks WHERE document_id = ?", (doc_id,))
                conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
                conn.commit()
                return cursor.rowcount > 0
            finally:
                conn.close()

    def update_document_status(self, doc_id: str, status: str, error: str | None = None):
        with self._lock:
            conn = self._get_conn()
            try:
                conn.execute(
                    "UPDATE documents SET status = ?, error = ? WHERE id = ?",
                    (status, error, doc_id),
                )
                conn.commit()
            finally:
                conn.close()

    # ── Chunk operations ──

    def add_chunks(self, chunks: list[DocumentChunk], embeddings: list[list[float]]):
        with self._lock:
            conn = self._get_conn()
            try:
                for chunk, emb in zip(chunks, embeddings):
                    if not chunk.id:
                        chunk.id = str(uuid.uuid4())
                    conn.execute(
                        """INSERT OR REPLACE INTO chunks
                           (id, document_id, chunk_index, text, token_count, 
                            embedding_json, metadata_json)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (
                            chunk.id, chunk.document_id, chunk.chunk_index,
                            chunk.text, chunk.token_count,
                            json.dumps(emb), json.dumps(chunk.metadata),
                        ),
                    )
                conn.commit()
            finally:
                conn.close()

    def get_chunks_for_document(self, doc_id: str) -> list[DocumentChunk]:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM chunks WHERE document_id = ? ORDER BY chunk_index",
                (doc_id,),
            ).fetchall()
            return [
                DocumentChunk(
                    id=row["id"],
                    document_id=row["document_id"],
                    chunk_index=row["chunk_index"],
                    text=row["text"],
                    token_count=row["token_count"],
                    metadata=json.loads(row["metadata_json"]),
                )
                for row in rows
            ]
        finally:
            conn.close()

    def delete_chunks(self, doc_id: str):
        with self._lock:
            conn = self._get_conn()
            try:
                conn.execute("DELETE FROM chunks WHERE document_id = ?", (doc_id,))
                conn.commit()
            finally:
                conn.close()

    # ── Search ──

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
    ) -> list[SearchResult]:
        """Search for most similar chunks using cosine similarity.

        Currently loads all chunks and computes in Python — fine for <10K chunks.
        Ready to swap in FAISS or ChromaDB for larger datasets.
        """
        conn = self._get_conn()
        try:
            chunks = conn.execute(
                """SELECT c.*, d.filename, d.path 
                   FROM chunks c 
                   JOIN documents d ON c.document_id = d.id"""
            ).fetchall()
        finally:
            conn.close()

        if not chunks:
            return []

        # Compute cosine similarity
        results: list[tuple[float, sqlite3.Row]] = []
        q_norm = math.sqrt(sum(v * v for v in query_embedding))
        if q_norm == 0:
            q_norm = 1
        q_vec = [v / q_norm for v in query_embedding]

        for row in chunks:
            emb = json.loads(row["embedding_json"])
            if not emb:
                continue
            d_norm = math.sqrt(sum(v * v for v in emb))
            if d_norm == 0:
                continue
            d_vec = [v / d_norm for v in emb]
            similarity = sum(a * b for a, b in zip(q_vec, d_vec))
            results.append((similarity, row))

        results.sort(key=lambda x: x[0], reverse=True)
        top = results[:top_k]

        return [
            SearchResult(
                document_id=row["document_id"],
                filename=row["filename"],
                chunk_id=row["id"],
                chunk_index=row["chunk_index"],
                score=round(score, 4),
                text_preview=row["text"][:300],
                metadata=json.loads(row["metadata_json"]),
            )
            for score, row in top
        ]

    # ── Status ──

    def get_status(self) -> dict[str, Any]:
        conn = self._get_conn()
        try:
            doc_count = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
            chunk_count = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
            return {
                "documents": doc_count,
                "chunks": chunk_count,
            }
        finally:
            conn.close()

    def clear(self):
        """Delete all documents and chunks."""
        with self._lock:
            conn = self._get_conn()
            try:
                conn.execute("DELETE FROM chunks")
                conn.execute("DELETE FROM documents")
                conn.commit()
                logger.info("Vector store cleared")
            finally:
                conn.close()


# ── Singleton ──

_vector_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store

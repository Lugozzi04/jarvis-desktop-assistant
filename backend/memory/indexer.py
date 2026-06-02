"""Document Indexer — pipeline to ingest documents into the vector store."""

from __future__ import annotations

import fnmatch
import os
from datetime import datetime
from pathlib import Path

from backend.core.logger import logger
from backend.memory.extractors import get_extractor
from backend.memory.chunker import chunk_text
from backend.memory.embeddings import get_embedding_provider, EmbeddingProvider
from backend.memory.vector_store import get_vector_store, VectorStore
from backend.memory.models import Document, DocumentChunk, DocumentStatus


class DocumentIndexer:
    """Orchestrates document indexing: extract → chunk → embed → store."""

    def __init__(self, vector_store: VectorStore | None = None):
        self.store = vector_store or get_vector_store()
        self._embedding_provider: EmbeddingProvider | None = None

    @property
    def embedding_provider(self) -> EmbeddingProvider:
        if self._embedding_provider is None:
            self._embedding_provider = get_embedding_provider()
        return self._embedding_provider

    async def index_file(self, file_path: str | Path) -> Document:
        """Index a single file. Returns the Document."""
        file_path = Path(file_path).resolve()

        if not file_path.exists():
            doc = Document(
                path=str(file_path),
                filename=file_path.name,
                file_type=file_path.suffix.lower(),
                status=DocumentStatus.error,
                error=f"File not found: {file_path}",
            )
            return doc

        doc = Document(
            path=str(file_path),
            filename=file_path.name,
            file_type=file_path.suffix.lower(),
            size_bytes=file_path.stat().st_size,
            status=DocumentStatus.indexing,
        )
        doc.id = self.store.add_document(doc)
        logger.info("Indexing document {}: {}", doc.id, doc.filename)

        try:
            # 1. Extract text
            extractor = get_extractor(str(file_path))
            extraction = extractor.extract(str(file_path))

            if not extraction.success or not extraction.text.strip():
                self.store.update_document_status(
                    doc.id, DocumentStatus.error.value,
                    extraction.error or "No text extracted",
                )
                doc.status = DocumentStatus.error
                doc.error = extraction.error or "No text extracted"
                return doc

            # 2. Chunk
            chunk_result = chunk_text(
                extraction.text,
                chunk_size=1500,
                overlap=200,
                metadata={
                    "filename": doc.filename,
                    "file_type": doc.file_type,
                    "path": str(file_path),
                    **extraction.metadata,
                },
            )

            if not chunk_result.chunks:
                self.store.update_document_status(
                    doc.id, DocumentStatus.error.value, "Text was empty after chunking"
                )
                doc.status = DocumentStatus.error
                doc.error = "Text was empty after chunking"
                return doc

            # 3. Embed
            embeddings = await self.embedding_provider.embed_batch(chunk_result.chunks)

            # 4. Store chunks
            doc_chunks = []
            for i, (chunk_text_content, embedding) in enumerate(zip(chunk_result.chunks, embeddings)):
                chunk = DocumentChunk(
                    document_id=doc.id,
                    chunk_index=i,
                    text=chunk_text_content,
                    token_count=len(chunk_text_content.split()),
                    metadata={
                        "filename": doc.filename,
                        "file_type": doc.file_type,
                        "path": str(file_path),
                        "chunk_of": len(chunk_result.chunks),
                    },
                )
                doc_chunks.append(chunk)

            self.store.delete_chunks(doc.id)  # remove old chunks if re-indexing
            self.store.add_chunks(doc_chunks, embeddings)

            # 5. Mark complete
            doc.status = DocumentStatus.indexed
            doc.chunk_count = len(doc_chunks)
            doc.indexed_at = datetime.utcnow().isoformat()
            doc.error = None
            self.store.update_document_status(doc.id, DocumentStatus.indexed.value)
            self.store.add_document(doc)  # update chunk count

            logger.info(
                "Document {} indexed: {} chunks, {} provider",
                doc.filename, doc.chunk_count, self.embedding_provider.name,
            )
            return doc

        except Exception as exc:
            logger.error("Failed to index document {}: {}", doc.filename, exc)
            self.store.update_document_status(doc.id, DocumentStatus.error.value, str(exc))
            doc.status = DocumentStatus.error
            doc.error = str(exc)
            return doc

    async def index_folder(
        self,
        folder_path: str | Path,
        recursive: bool = True,
        include_patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
    ) -> list[Document]:
        """Index all supported files in a folder. Returns list of Documents."""
        folder_path = Path(folder_path).resolve()

        if not folder_path.exists() or not folder_path.is_dir():
            logger.error("Folder not found: {}", folder_path)
            return []

        include_patterns = include_patterns or ["*.*"]
        exclude_patterns = exclude_patterns or [
            ".git", "node_modules", ".venv", "__pycache__",
            ".mypy_cache", ".pytest_cache", "dist", "build",
        ]

        docs: list[Document] = []

        for root, dirs, files in os.walk(str(folder_path)):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if not any(
                fnmatch.fnmatch(d, pat) for pat in exclude_patterns
            )]

            if not recursive and root != str(folder_path):
                break

            for file_name in files:
                file_path = Path(root) / file_name
                ext = file_path.suffix.lower()

                # Check include patterns
                if not any(fnmatch.fnmatch(file_name, pat) for pat in include_patterns):
                    continue

                # Check exclude patterns for files
                if any(fnmatch.fnmatch(file_name, pat) for pat in exclude_patterns):
                    continue

                # Check if extractor can handle
                extractor = get_extractor(str(file_path))
                if not extractor.can_handle(str(file_path)):
                    continue

                try:
                    doc = await self.index_file(file_path)
                    docs.append(doc)
                except Exception as exc:
                    logger.warning("Skipping {}: {}", file_path.name, exc)

        logger.info("Indexed {} documents from {}", len(docs), folder_path)
        return docs


# ── Singleton ──

_indexer: DocumentIndexer | None = None


def get_indexer() -> DocumentIndexer:
    global _indexer
    if _indexer is None:
        _indexer = DocumentIndexer()
    return _indexer

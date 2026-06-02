"""Text chunking with configurable size and overlap."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ChunkResult:
    chunks: list[str]
    metadata: dict


def chunk_text(
    text: str,
    chunk_size: int = 1500,
    overlap: int = 200,
    metadata: dict | None = None,
) -> ChunkResult:
    """Split text into overlapping chunks.

    Args:
        text: Input text to chunk.
        chunk_size: Maximum characters per chunk (default 1500).
        overlap: Characters of overlap between chunks (default 200).
        metadata: Optional metadata to attach.

    Returns:
        ChunkResult with chunk list and metadata.
    """
    if not text or not text.strip():
        return ChunkResult(chunks=[], metadata=metadata or {})

    text = text.strip()
    if len(text) <= chunk_size:
        return ChunkResult(chunks=[text], metadata=metadata or {"count": 1})

    chunks: list[str] = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))

        if end < len(text):
            # Try to break at a natural boundary (paragraph, then sentence, then word)
            chunk_text_raw = text[start:end]
            natural_break = _find_natural_break(chunk_text_raw)
            if natural_break is not None:
                end = start + natural_break

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end - overlap if end < len(text) else end
        if start >= len(text):
            break

    return ChunkResult(
        chunks=chunks,
        metadata={
            **(metadata or {}),
            "count": len(chunks),
            "chunk_size": chunk_size,
            "overlap": overlap,
        },
    )


def _find_natural_break(text: str) -> int | None:
    """Find a natural break point (paragraph, sentence, word) near the end of text.

    Returns the position to break at, or None if no good break found.
    """
    # Prefer paragraph breaks in the last 20% of the chunk
    window = max(1, int(len(text) * 0.2))
    search_region = text[-window:]

    # Try double newline (paragraph)
    for sep in ["\n\n", "\n", ". ", "! ", "? ", "; ", " "]:
        pos = search_region.rfind(sep)
        if pos > 0:
            return len(text) - window + pos + len(sep)

    return None

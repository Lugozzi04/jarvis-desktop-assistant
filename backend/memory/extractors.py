"""Document extractors — text and PDF extraction with modular providers."""

from __future__ import annotations

import json
import re
from pathlib import Path

from backend.core.logger import logger


class ExtractionResult:
    def __init__(self, text: str, metadata: dict | None = None, error: str | None = None):
        self.text = text
        self.metadata = metadata or {}
        self.error = error
        self.success = error is None


class BaseExtractor:
    """Base class for document extractors."""

    supported_extensions: list[str] = []
    name: str = "base"

    def can_handle(self, file_path: str | Path) -> bool:
        ext = Path(file_path).suffix.lower()
        return ext in self.supported_extensions

    def extract(self, file_path: str | Path) -> ExtractionResult:
        raise NotImplementedError


class TextExtractor(BaseExtractor):
    """Extract text from plain text files, code, markdown, JSON, CSV."""

    name = "text"
    supported_extensions = [
        ".txt", ".md", ".py", ".js", ".ts", ".tsx", ".jsx",
        ".html", ".css", ".json", ".csv", ".xml", ".yaml", ".yml",
        ".toml", ".ini", ".cfg", ".conf", ".env", ".sh", ".bash",
        ".ps1", ".bat", ".sql", ".rs", ".go", ".java", ".c", ".cpp",
        ".h", ".hpp", ".rb", ".php", ".swift", ".kt", ".scala",
        ".r", ".lua", ".vim", ".tex", ".rst", ".org",
    ]

    def extract(self, file_path: str | Path) -> ExtractionResult:
        file_path = Path(file_path)
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
            return ExtractionResult(
                text=content,
                metadata={"encoding": "utf-8", "lines": len(content.splitlines())},
            )
        except Exception as exc:
            return ExtractionResult(text="", error=str(exc))


class PdfExtractor(BaseExtractor):
    """Extract text from PDF files using pypdf. Falls back gracefully if missing."""

    name = "pdf"
    supported_extensions = [".pdf"]

    def __init__(self):
        self._available = False
        self._error = None
        try:
            import pypdf  # noqa: F401
            self._available = True
        except ImportError as e:
            self._error = str(e)

    def extract(self, file_path: str | Path) -> ExtractionResult:
        if not self._available:
            return ExtractionResult(
                text="",
                error=f"pypdf not installed ({self._error}). Install with: pip install pypdf",
            )

        file_path = Path(file_path)
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(file_path))
            text_parts = []
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            full_text = "\n\n".join(text_parts)
            return ExtractionResult(
                text=full_text,
                metadata={"pages": len(reader.pages)},
            )
        except Exception as exc:
            return ExtractionResult(text="", error=str(exc))


class UnsupportedExtractor(BaseExtractor):
    """Returns a controlled error for unsupported file types."""

    name = "unsupported"
    supported_extensions = []  # catch-all

    def can_handle(self, file_path: str | Path) -> bool:
        return True  # fallback

    def extract(self, file_path: str | Path) -> ExtractionResult:
        ext = Path(file_path).suffix.lower()
        return ExtractionResult(
            text="",
            error=f"Unsupported file type: {ext}. Supported: {', '.join(sorted(TextExtractor().supported_extensions + PdfExtractor().supported_extensions))}",
        )


# ── Extractor Registry ──

_extractors: list[BaseExtractor] = []


def _init_extractors():
    global _extractors
    if _extractors:
        return
    _extractors = [
        PdfExtractor(),
        TextExtractor(),
    ]
    _fallback = UnsupportedExtractor()


def get_extractor(file_path: str | Path) -> BaseExtractor:
    _init_extractors()
    for ext in _extractors:
        if ext.can_handle(file_path):
            if isinstance(ext, PdfExtractor) and not ext._available:
                # PdfExtractor can_handle but may not be available
                pass
            return ext
    return UnsupportedExtractor()

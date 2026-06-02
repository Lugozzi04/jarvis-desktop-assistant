"""Embedding providers — mock, simple (hash-based), and Ollama."""

from __future__ import annotations

import hashlib
import math
from abc import ABC, abstractmethod

from backend.core.config import settings
from backend.core.logger import logger


class EmbeddingProvider(ABC):
    """Abstract base for embedding providers."""

    name: str = "base"
    available: bool = False
    dimension: int = 0

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        ...

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts. Override for efficiency."""
        results = []
        for text in texts:
            results.append(await self.embed(text))
        return results


class MockEmbeddingProvider(EmbeddingProvider):
    """Deterministic mock embeddings for testing. Returns fixed-size random-like vectors."""

    name = "mock"
    available = True
    dimension = 384

    async def embed(self, text: str) -> list[float]:
        """Generate a deterministic mock embedding from text hash."""
        seed = int(hashlib.md5(text.encode()).hexdigest(), 16)
        # Generate a pseudo-random unit vector
        vec = []
        state = seed
        for i in range(self.dimension):
            state = (state * 1103515245 + 12345) & 0x7FFFFFFF
            vec.append((state % 1000) / 1000.0)
        # Normalize
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec


class SimpleEmbeddingProvider(EmbeddingProvider):
    """Lightweight hash-based embeddings. No model download needed.
    
    Uses character n-gram hashing + TF-like weighting.
    Works offline, good enough for small document sets.
    """

    name = "simple"
    available = True
    dimension = 256
    _ngram_sizes = (2, 3, 4)

    def _hash_ngram(self, ngram: str, seed: int = 0) -> int:
        h = hashlib.md5(f"{seed}:{ngram}".encode()).hexdigest()
        return int(h[:8], 16)

    async def embed(self, text: str) -> list[float]:
        """Generate a simple embedding from text using n-gram hashing."""
        vec = [0.0] * self.dimension
        text_lower = text.lower()

        for n in self._ngram_sizes:
            for i in range(len(text_lower) - n + 1):
                ngram = text_lower[i:i + n]
                idx = self._hash_ngram(ngram, seed=n) % self.dimension
                vec[idx] += 1.0

        # Normalize
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]

        return vec


class OllamaEmbeddingProvider(EmbeddingProvider):
    """Ollama embedding provider. Uses nomic-embed-text by default.
    
    Requires: ollama pull nomic-embed-text (run on local PC, not VPS).
    NOT installed on VPS — returns available=False with clear instructions.
    """

    name = "ollama"
    dimension = 768

    def __init__(self, base_url: str | None = None, model: str | None = None):
        self.base_url = (base_url or getattr(settings, "ollama_base_url", "http://localhost:11434")).rstrip("/")
        self.model = model or "nomic-embed-text"
        self.available = False
        self._error: str | None = None
        self._check_availability()

    def _check_availability(self):
        """Check if Ollama is reachable — non-blocking, sync for init."""
        try:
            import urllib.request
            req = urllib.request.Request(
                f"{self.base_url}/api/tags",
                headers={"User-Agent": "Jarvis/1.0"},
            )
            urllib.request.urlopen(req, timeout=2)
            self.available = True
            self._error = None
            logger.info("Ollama embedding provider available at {}", self.base_url)
        except Exception as e:
            self.available = False
            self._error = f"Ollama not reachable at {self.base_url}: {e}"
            logger.info("Ollama embedding provider not available: {}", self._error)

    async def embed(self, text: str) -> list[float]:
        """Generate embedding via Ollama API."""
        if not self.available:
            raise RuntimeError(
                f"Ollama not available. {self._error}\n"
                "Install Ollama on your local PC: curl -fsSL https://ollama.com/install.sh | sh\n"
                f"Then pull the model: ollama pull {self.model}"
            )

        import urllib.request
        import json as _json

        payload = _json.dumps({"model": self.model, "prompt": text}).encode()
        req = urllib.request.Request(
            f"{self.base_url}/api/embeddings",
            data=payload,
            headers={"Content-Type": "application/json", "User-Agent": "Jarvis/1.0"},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = _json.loads(resp.read().decode())
                embedding = data.get("embedding", [])
                return embedding
        except Exception as e:
            raise RuntimeError(f"Ollama embedding failed: {e}")


# ── Factory ──

_embedding_provider: EmbeddingProvider | None = None


def get_embedding_provider() -> EmbeddingProvider:
    """Get the configured embedding provider (singleton)."""
    global _embedding_provider
    if _embedding_provider is not None:
        return _embedding_provider

    provider_name = getattr(settings, "embedding_provider", "simple")
    logger.info("Initializing embedding provider: {}", provider_name)

    if provider_name == "ollama":
        _embedding_provider = OllamaEmbeddingProvider()
        if not _embedding_provider.available:
            logger.info("Ollama not available, falling back to simple embeddings")
            _embedding_provider = SimpleEmbeddingProvider()
    elif provider_name == "mock":
        _embedding_provider = MockEmbeddingProvider()
    else:
        _embedding_provider = SimpleEmbeddingProvider()

    logger.info(
        "Using embedding provider: {} (dim={}, available={})",
        _embedding_provider.name,
        _embedding_provider.dimension,
        _embedding_provider.available,
    )
    return _embedding_provider

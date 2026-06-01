"""LLM Gateway — modular provider system for JARVIS.

Currently a skeleton. Full implementation in M5.

Architecture:
  - Provider-agnostic interface (BaseLLMProvider)
  - Multiple backends: Ollama, OpenAI, Anthropic, DeepSeek, Custom
  - Task-based routing (classify vs chat vs plan vs summarize)
  - Local-first with optional cloud fallback
  - JSON-mode output for structured intent parsing
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from backend.core.config import settings
from backend.core.logger import logger


class BaseLLMProvider(ABC):
    """Abstract base for LLM providers."""

    name: str = "base"

    @abstractmethod
    async def generate(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> str:
        """Generate a completion from the LLM."""
        ...

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if the provider is reachable."""
        ...


class OllamaProvider(BaseLLMProvider):
    """Ollama local LLM provider."""

    name = "ollama"

    def __init__(self, base_url: str | None = None, model: str | None = None):
        self.base_url = base_url or settings.ollama.base_url
        self.model = model or settings.llm.default_model

    async def generate(self, messages, max_tokens=1024, temperature=0.7) -> str:
        import httpx
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": temperature,
                    },
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["message"]["content"]

    async def is_available(self) -> bool:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False


class LLMGateway:
    """Central LLM Gateway — routes tasks to appropriate providers.

    Strategy:
      - Slash commands → no LLM (deterministic)
      - Simple intent routing → rule-based or small local model
      - Complex chat → full LLM
      - Web search → search + LLM summarizer
    """

    def __init__(self):
        self._providers: dict[str, BaseLLMProvider] = {}

    def register_provider(self, provider: BaseLLMProvider) -> None:
        self._providers[provider.name] = provider
        logger.info("LLM provider registered: {}", provider.name)

    async def get_provider(self, prefer_local: bool = True) -> BaseLLMProvider | None:
        """Get the best available provider."""
        # Try Ollama first for local
        if "ollama" in self._providers:
            if await self._providers["ollama"].is_available():
                return self._providers["ollama"]

        # Fall back to any available provider
        for name, provider in self._providers.items():
            if await provider.is_available():
                return provider

        return None

    async def is_available(self) -> bool:
        provider = await self.get_provider()
        return provider is not None

    async def generate(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> str:
        """Generate a completion using the best available provider."""
        provider = await self.get_provider()
        if provider is None:
            return "No LLM provider available. Set up Ollama or configure an API key."

        try:
            return await provider.generate(messages, max_tokens, temperature)
        except Exception as exc:
            logger.error("LLM generation failed: {}", exc)
            return f"LLM error: {exc}"


# Singleton
llm_gateway = LLMGateway()

# Auto-register Ollama if configured
if settings.llm.default_provider == "ollama":
    try:
        llm_gateway.register_provider(OllamaProvider())
    except Exception as exc:
        logger.warning("Could not register Ollama: {}", exc)

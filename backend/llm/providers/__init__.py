"""LLM Provider base class and registry."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


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

    async def generate_json(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 1024,
        temperature: float = 0.3,
    ) -> dict[str, Any] | None:
        """Generate a JSON response. Override in subclasses for better parsing."""
        import json
        import re

        raw = await self.generate(messages, max_tokens, temperature)

        # Try direct parse
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        # Try to extract JSON from markdown code blocks
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # Try to find a JSON object anywhere
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        return None


def get_provider_class(name: str) -> type[BaseLLMProvider]:
    """Get a provider class by name."""
    if name == "ollama":
        from backend.llm.providers.ollama import OllamaProvider
        return OllamaProvider
    elif name in ("openai_compatible", "openai", "deepseek", "custom"):
        from backend.llm.providers.openai_compatible import OpenAICompatibleProvider
        return OpenAICompatibleProvider
    elif name == "mock":
        from backend.llm.providers.mock import MockProvider
        return MockProvider
    else:
        raise ValueError(f"Unknown provider: {name}")

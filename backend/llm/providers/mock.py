"""Mock LLM provider for testing — returns deterministic responses."""

from __future__ import annotations

from typing import Any

from backend.llm.providers import BaseLLMProvider


class MockProvider(BaseLLMProvider):
    """Returns deterministic mock responses. Used in tests."""

    name = "mock"

    def __init__(self, responses: list[str] | None = None):
        self._responses = responses or ["Mock response from JARVIS test provider."]
        self._idx = 0
        self._available = True

    def set_unavailable(self) -> None:
        self._available = False

    def set_available(self) -> None:
        self._available = True

    def add_response(self, text: str) -> None:
        self._responses.append(text)

    async def generate(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> str:
        if not self._available:
            raise RuntimeError("Mock provider is unavailable")
        resp = self._responses[self._idx % len(self._responses)]
        self._idx += 1
        return resp

    async def is_available(self) -> bool:
        return self._available

    async def generate_json(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 1024,
        temperature: float = 0.3,
    ) -> dict[str, Any] | None:
        import json
        raw = await self.generate(messages, max_tokens, temperature)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

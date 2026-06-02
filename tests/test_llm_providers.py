"""Tests for LLM Gateway providers."""

import pytest

from backend.llm.providers import BaseLLMProvider, get_provider_class
from backend.llm.providers.mock import MockProvider


class TestMockProvider:
    """Tests for the Mock LLM provider."""

    def test_generate_returns_response(self):
        provider = MockProvider(["Hello from mock"])
        import asyncio

        result = asyncio.run(provider.generate([{"role": "user", "content": "hi"}]))
        assert result == "Hello from mock"

    def test_is_available_by_default(self):
        provider = MockProvider()
        import asyncio

        assert asyncio.run(provider.is_available()) is True

    def test_set_unavailable(self):
        provider = MockProvider()
        provider.set_unavailable()
        import asyncio

        assert asyncio.run(provider.is_available()) is False

    def test_generate_fails_when_unavailable(self):
        provider = MockProvider()
        provider.set_unavailable()
        import asyncio

        with pytest.raises(RuntimeError, match="unavailable"):
            asyncio.run(provider.generate([{"role": "user", "content": "hi"}]))

    def test_multiple_responses_cycle(self):
        provider = MockProvider(["first", "second", "third"])
        import asyncio

        r1 = asyncio.run(provider.generate([]))
        r2 = asyncio.run(provider.generate([]))
        r3 = asyncio.run(provider.generate([]))
        assert r1 == "first"
        assert r2 == "second"
        assert r3 == "third"

    def test_generate_json_parses(self):
        provider = MockProvider(['{"key": "value"}'])
        import asyncio

        result = asyncio.run(provider.generate_json([]))
        assert result == {"key": "value"}

    def test_generate_json_fallback(self):
        provider = MockProvider(["not json at all"])
        import asyncio

        result = asyncio.run(provider.generate_json([]))
        assert result is None


class TestProviderRegistry:
    """Tests for provider class lookup."""

    def test_get_ollama_provider(self):
        cls = get_provider_class("ollama")
        assert cls.__name__ == "OllamaProvider"

    def test_get_openai_compatible(self):
        cls = get_provider_class("openai_compatible")
        assert cls.__name__ == "OpenAICompatibleProvider"

    def test_get_mock_provider(self):
        cls = get_provider_class("mock")
        assert cls.__name__ == "MockProvider"

    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            get_provider_class("nonexistent")


class TestBaseProvider:
    """Tests for the base provider class."""

    def test_base_is_abstract(self):
        with pytest.raises(TypeError):
            BaseLLMProvider()

    def test_get_provider_class_returns_subclass(self):
        cls = get_provider_class("mock")
        assert issubclass(cls, BaseLLMProvider)

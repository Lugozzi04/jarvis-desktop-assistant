"""LLM Gateway — modular provider system for JARVIS.

Architecture:
  - Provider-agnostic interface (BaseLLMProvider)
  - Multiple backends: Ollama, OpenAI-compatible, Mock
  - Task-based routing (classify vs chat vs plan vs summarize)
  - Local-first with optional cloud fallback
  - JSON-mode output for structured intent parsing
"""

from __future__ import annotations

from typing import Any

from backend.core.config import settings
from backend.core.logger import logger
from backend.llm.providers import BaseLLMProvider, get_provider_class


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
        self._primary: str = ""

    def register_provider(self, provider: BaseLLMProvider) -> None:
        self._providers[provider.name] = provider
        logger.info("LLM provider registered: {}", provider.name)

    def configure(
        self,
        provider_name: str,
        base_url: str = "",
        api_key: str = "",
        model: str = "",
        timeout: int = 60,
    ) -> None:
        """Configure and register a provider dynamically."""
        try:
            cls = get_provider_class(provider_name)
        except ValueError:
            logger.error("Unknown provider: {}", provider_name)
            raise

        if provider_name == "ollama":
            instance = cls(
                base_url=base_url or settings.ollama.base_url,
                model=model or settings.llm.default_model,
            )
        elif provider_name == "mock":
            instance = cls()
        else:
            instance = cls(
                base_url=base_url,
                api_key=api_key,
                model=model or settings.llm.default_model,
                timeout=timeout,
            )

        self.register_provider(instance)
        self._primary = provider_name

    def initialize_from_config(self) -> None:
        """Auto-configure from JARVIS settings."""
        provider_name = settings.llm.default_provider

        try:
            cls = get_provider_class(provider_name)
        except ValueError:
            logger.warning("Unknown provider: {} — LLM features disabled", provider_name)
            return

        if provider_name == "ollama":
            instance = cls(
                base_url=settings.ollama.base_url,
                model=settings.llm.default_model,
            )
        elif provider_name in ("openai_compatible", "openai", "deepseek", "custom"):
            api_key = getattr(settings, "llm_api_key", "") or ""
            base_url = getattr(settings, "llm_base_url", "https://api.openai.com/v1") or "https://api.openai.com/v1"
            timeout = getattr(settings, "llm_timeout", 60) or 60
            instance = cls(
                base_url=base_url,
                api_key=api_key,
                model=settings.llm.default_model,
                timeout=timeout,
            )
        elif provider_name == "mock":
            instance = cls()
        else:
            instance = cls()

        self.register_provider(instance)
        self._primary = provider_name
        logger.info("LLM Gateway initialized with provider: {}", provider_name)

    async def get_provider(self, prefer_local: bool = True) -> BaseLLMProvider | None:
        """Get the best available provider."""
        # Try primary first
        if self._primary and self._primary in self._providers:
            if await self._providers[self._primary].is_available():
                return self._providers[self._primary]

        # Try Ollama if local preferred
        if prefer_local and "ollama" in self._providers:
            if await self._providers["ollama"].is_available():
                return self._providers["ollama"]

        # Fall back to any available
        for name, provider in self._providers.items():
            if name == self._primary:
                continue
            if await provider.is_available():
                return provider

        return None

    async def get_status(self) -> dict[str, Any]:
        """Get LLM status for health checks."""
        provider = await self.get_provider(prefer_local=False)
        all_status = {}
        for name, p in self._providers.items():
            all_status[name] = {
                "configured": True,
            }

        return {
            "provider": self._primary or "none",
            "available": provider is not None,
            "model": settings.llm.default_model,
            "allow_cloud": settings.llm.allow_cloud,
            "providers": all_status,
        }

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

    async def generate_json(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 1024,
        temperature: float = 0.3,
    ) -> dict[str, Any] | None:
        """Generate a JSON response."""
        provider = await self.get_provider()
        if provider is None:
            return None

        try:
            return await provider.generate_json(messages, max_tokens, temperature)
        except Exception as exc:
            logger.error("LLM JSON generation failed: {}", exc)
            return None

    async def route_intent(
        self,
        user_input: str,
        available_skills: list[str],
    ) -> dict[str, Any] | None:
        """Use LLM to classify user intent and route to skill/action."""
        skills_list = ", ".join(available_skills)
        prompt = (
            "You are an intent router for a desktop assistant. "
            "Given user input, return a JSON object with: skill, action, parameters.\n"
            f"Available skills: {skills_list}\n"
            f"User input: {user_input}\n"
            'Return ONLY valid JSON: {"skill": "...", "action": "...", "parameters": {...}}'
        )

        return await self.generate_json([
            {"role": "system", "content": prompt}
        ])

    async def chat(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> str:
        """Chat completion — alias for generate."""
        return await self.generate(messages, max_tokens, temperature)

    async def test_connection(self, provider_name: str | None = None) -> dict[str, Any]:
        """Test a provider connection."""
        target = provider_name or self._primary
        if target not in self._providers:
            return {"success": False, "error": f"Provider '{target}' not configured"}

        provider = self._providers[target]
        try:
            available = await provider.is_available()
            if available:
                # Try a quick generation
                try:
                    result = await provider.generate(
                        [{"role": "user", "content": "Say 'hello' in one word."}],
                        max_tokens=10,
                    )
                    return {
                        "success": True,
                        "provider": target,
                        "available": True,
                        "test_response": result.strip(),
                    }
                except Exception as exc:
                    return {
                        "success": True,
                        "provider": target,
                        "available": True,
                        "test_response": f"Connected but generation failed: {exc}",
                    }
            else:
                return {
                    "success": False,
                    "provider": target,
                    "available": False,
                    "error": "Provider is not reachable",
                }
        except Exception as exc:
            return {
                "success": False,
                "provider": target,
                "available": False,
                "error": str(exc),
            }


# Singleton
llm_gateway = LLMGateway()

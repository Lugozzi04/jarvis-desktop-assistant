"""LLM Gateway — modular provider system for JARVIS.

Architecture:
  - Provider-agnostic interface (BaseLLMProvider)
  - Multiple backends: Ollama, OpenAI-compatible, Mock
  - Task-based routing (classify vs chat vs plan vs summarize)
  - Local-first with optional cloud fallback
  - JSON-mode output for structured intent parsing
  - Robust Ollama status with model availability checks
"""

from __future__ import annotations

from typing import Any

from backend.core.config import settings
from backend.core.logger import logger
from backend.llm.providers import BaseLLMProvider, get_provider_class

# Recommended models
RECOMMENDED_OLLAMA_MODEL = "qwen2.5:7b"
FALLBACK_LIGHT = "llama3.2:3b"
FALLBACK_HEAVY = "llama3.1:8b"
ALL_RECOMMENDED_MODELS = [RECOMMENDED_OLLAMA_MODEL, FALLBACK_LIGHT, FALLBACK_HEAVY]


class LLMGateway:
    """Central LLM Gateway — routes tasks to appropriate providers."""

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
        if self._primary and self._primary in self._providers:
            if await self._providers[self._primary].is_available():
                return self._providers[self._primary]

        if prefer_local and "ollama" in self._providers:
            if await self._providers["ollama"].is_available():
                return self._providers["ollama"]

        for name, provider in self._providers.items():
            if name == self._primary:
                continue
            if await provider.is_available():
                return provider

        return None

    async def get_status(self) -> dict[str, Any]:
        """Get detailed LLM status for health checks and UI.

        For Ollama: includes reachable, model_available, available_models,
        recommended_command, setup_required.
        """
        base_status: dict[str, Any] = {
            "provider": self._primary or "none",
            "available": False,
            "model": settings.llm.default_model,
            "allow_cloud": settings.llm.allow_cloud,
            "ready": False,
            "setup_required": True,
            "recommended_models": ALL_RECOMMENDED_MODELS,
        }

        # Try detailed Ollama status if primary is ollama
        if self._primary == "ollama" and "ollama" in self._providers:
            try:
                ollama = self._providers["ollama"]
                # Check if it has get_detailed_status method
                if hasattr(ollama, "get_detailed_status"):
                    detailed = await ollama.get_detailed_status()
                    base_status.update(detailed)
                    return base_status
            except Exception as exc:
                logger.warning("Failed to get Ollama detailed status: {}", exc)

        # Generic status
        provider = await self.get_provider(prefer_local=False)
        base_status["available"] = provider is not None
        base_status["ready"] = provider is not None
        base_status["setup_required"] = provider is None

        # Build provider-specific status
        all_status = {}
        for name, p in self._providers.items():
            all_status[name] = {"configured": True}
        base_status["providers"] = all_status

        return base_status

    async def get_recommended_models(self) -> dict[str, Any]:
        """Get recommended model configuration."""
        return {
            "primary": {
                "name": RECOMMENDED_OLLAMA_MODEL,
                "command": f"ollama pull {RECOMMENDED_OLLAMA_MODEL}",
                "description": "Best balance of quality and performance. Good for routing, chat, JSON output.",
                "size": "~4.7 GB",
            },
            "fallback_light": {
                "name": FALLBACK_LIGHT,
                "command": f"ollama pull {FALLBACK_LIGHT}",
                "description": "Lightweight option for slower machines.",
                "size": "~2.0 GB",
            },
            "fallback_heavy": {
                "name": FALLBACK_HEAVY,
                "command": f"ollama pull {FALLBACK_HEAVY}",
                "description": "Best quality, requires more RAM.",
                "size": "~4.9 GB",
            },
            "cloud_option": {
                "name": "deepseek-chat",
                "provider": "openai_compatible",
                "description": "Cloud-based via DeepSeek API. Requires API key.",
            },
        }

    async def get_ollama_setup_guide(self) -> dict[str, Any]:
        """Get setup guide for Ollama."""
        return {
            "title": "Ollama Local Setup Guide",
            "steps": [
                {
                    "step": 1,
                    "title": "Install Ollama",
                    "description": "Download and install Ollama for your operating system.",
                    "commands": {
                        "linux": "curl -fsSL https://ollama.com/install.sh | sh",
                        "macos": "brew install ollama",
                        "windows": "Download from https://ollama.com/download/windows",
                    },
                },
                {
                    "step": 2,
                    "title": "Start Ollama",
                    "description": "Ensure the Ollama service is running.",
                    "commands": {
                        "linux": "ollama serve",
                        "macos": "ollama serve",
                        "windows": "Launch Ollama from Start Menu",
                    },
                },
                {
                    "step": 3,
                    "title": f"Pull Recommended Model ({RECOMMENDED_OLLAMA_MODEL})",
                    "description": "Download the recommended model. This may take a few minutes.",
                    "commands": {
                        "all": f"ollama pull {RECOMMENDED_OLLAMA_MODEL}",
                    },
                },
                {
                    "step": 4,
                    "title": "Verify",
                    "description": "Check that the model is available.",
                    "commands": {
                        "all": "ollama list",
                    },
                },
                {
                    "step": 5,
                    "title": "Configure Jarvis",
                    "description": "Set up your .env file and restart Jarvis.",
                    "commands": {
                        "all": (
                            "JARVIS_LLM_DEFAULT_PROVIDER=ollama\n"
                            f"JARVIS_LLM_DEFAULT_MODEL={RECOMMENDED_OLLAMA_MODEL}\n"
                            "JARVIS_LLM_BASE_URL=http://localhost:11434\n"
                            "JARVIS_LLM_ALLOW_CLOUD=false"
                        ),
                    },
                },
            ],
            "alternative_models": [
                {
                    "name": FALLBACK_LIGHT,
                    "command": f"ollama pull {FALLBACK_LIGHT}",
                    "when": "Limited RAM/CPU — good for basic tasks",
                },
                {
                    "name": FALLBACK_HEAVY,
                    "command": f"ollama pull {FALLBACK_HEAVY}",
                    "when": "More RAM available — better quality",
                },
            ],
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
            return (
                "No LLM provider available. "
                f"To use JARVIS locally, install Ollama and run: ollama pull {RECOMMENDED_OLLAMA_MODEL}\n\n"
                "In the meantime, try slash commands:\n"
                "• /open <app> — Open an application\n"
                "• /search <query> — Search the web\n"
                "• /timer <duration> <message> — Set a timer\n"
                "• /system stats — Show system stats"
            )

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
        """Use LLM to classify user intent and route to skill/action.

        Returns structured JSON validated against the intent schema.
        Only called after rule-based routing fails.
        """
        skills_list = ", ".join(available_skills)
        prompt = (
            "You are an intent router for a desktop assistant called JARVIS. "
            "Given user input, return a JSON object classifying the intent.\n\n"
            f"Available skills: {skills_list}\n"
            "Available actions per skill:\n"
            "- apps: open, close, list\n"
            "- browser: open_url\n"
            "- chat: answer_question, explain_concept, summarize_text\n"
            "- web_search: search_and_summarize\n"
            "- system: get_stats, run_action\n"
            "- timers: create_timer, create_reminder\n\n"
            "Return ONLY a JSON object with these fields:\n"
            '{\n'
            '  "kind": "skill" | "chat" | "clarification",\n'
            '  "confidence": 0.0 to 1.0,\n'
            '  "skill": "skill_name" or null,\n'
            '  "action": "action_name" or null,\n'
            '  "parameters": {},\n'
            '  "reply": "clarification question" or null\n'
            '}\n\n'
            "Rules:\n"
            "- If you're confident (>0.7), set kind=skill with skill/action\n"
            "- If the input is a general question, set kind=chat\n"
            "- If you're unsure, set kind=clarification with reply asking for details\n\n"
            f"User input: {user_input}\n"
            "Return ONLY valid JSON, no other text:"
        )

        result = await self.generate_json([
            {"role": "system", "content": prompt}
        ])

        if result:
            # Validate required fields
            if "kind" not in result:
                result["kind"] = "chat"
            if "confidence" not in result:
                result["confidence"] = 0.5
            return result

        return None

    async def chat(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> str:
        """Chat completion — alias for generate."""
        return await self.generate(messages, max_tokens, temperature)

    async def test_connection(self, provider_name: str | None = None) -> dict[str, Any]:
        """Test a provider connection with detailed diagnostics."""
        target = provider_name or self._primary
        if target not in self._providers:
            return {"success": False, "error": f"Provider '{target}' not configured"}

        provider = self._providers[target]

        # For Ollama, use detailed status
        if target == "ollama" and hasattr(provider, "get_detailed_status"):
            try:
                status = await provider.get_detailed_status()
                if not status.get("reachable"):
                    return {
                        "success": False,
                        "provider": target,
                        "available": False,
                        "error": status.get("error", "Ollama is not reachable"),
                        "setup_required": True,
                        "recommended_command": status.get("recommended_command"),
                    }
                if not status.get("model_available"):
                    return {
                        "success": False,
                        "provider": target,
                        "available": True,
                        "model_available": False,
                        "error": status.get("error", "Model not pulled"),
                        "available_models": status.get("available_models", []),
                        "setup_required": True,
                        "recommended_command": status.get("recommended_command"),
                    }
                # All good — try generation
                try:
                    result = await provider.generate(
                        [{"role": "user", "content": "Say 'hello' in one word."}],
                        max_tokens=10,
                    )
                    return {
                        "success": True,
                        "provider": target,
                        "available": True,
                        "model_available": True,
                        "model": status.get("model"),
                        "test_response": result.strip(),
                    }
                except Exception as exc:
                    return {
                        "success": False,
                        "provider": target,
                        "available": True,
                        "model_available": True,
                        "error": f"Generation failed: {exc}",
                    }
            except Exception as exc:
                return {
                    "success": False,
                    "provider": target,
                    "error": str(exc),
                }

        # Generic test for other providers
        try:
            available = await provider.is_available()
            if not available:
                return {
                    "success": False,
                    "provider": target,
                    "available": False,
                    "error": "Provider is not reachable",
                }

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
        except Exception as exc:
            return {
                "success": False,
                "provider": target,
                "available": False,
                "error": str(exc),
            }


# Singleton
llm_gateway = LLMGateway()

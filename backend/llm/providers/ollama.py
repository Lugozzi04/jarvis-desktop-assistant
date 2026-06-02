"""Ollama local LLM provider with detailed status reporting.

Does NOT install Ollama or download models — only checks and reports.
"""

from __future__ import annotations

from typing import Any

from backend.llm.providers import BaseLLMProvider

# Recommended models for Jarvis
RECOMMENDED_MODEL = "qwen2.5:7b"
FALLBACK_LIGHT_MODEL = "llama3.2:3b"
FALLBACK_HEAVY_MODEL = "llama3.1:8b"
ALL_RECOMMENDED = [RECOMMENDED_MODEL, FALLBACK_LIGHT_MODEL, FALLBACK_HEAVY_MODEL]


class OllamaProvider(BaseLLMProvider):
    """Ollama local LLM provider.

    Checks Ollama availability, model presence, and provides detailed
    status for the frontend to guide local setup.
    """

    name = "ollama"

    def __init__(self, base_url: str = "http://localhost:11434", model: str = RECOMMENDED_MODEL):
        self.base_url = base_url.rstrip("/")
        self.model = model

    # ── Core LLM methods ──

    async def generate(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> str:
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
        """Quick check: is Ollama reachable?"""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False

    # ── Detailed status ──

    async def get_detailed_status(self) -> dict[str, Any]:
        """Get comprehensive Ollama status for UI display.

        Returns:
            Dict with:
              - provider: "ollama"
              - base_url: str
              - model: str (selected model name)
              - reachable: bool (is Ollama server responding?)
              - model_available: bool (is selected model pulled?)
              - available_models: list[str]
              - ready: bool (reachable AND model_available)
              - setup_required: bool
              - recommended_command: str | None
              - recommended_models: list[str]
              - error: str | None
        """
        result: dict[str, Any] = {
            "provider": "ollama",
            "base_url": self.base_url,
            "model": self.model,
            "reachable": False,
            "model_available": False,
            "available_models": [],
            "ready": False,
            "setup_required": True,
            "recommended_command": None,
            "recommended_models": ALL_RECOMMENDED,
            "error": None,
        }

        # Check reachability
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                if resp.status_code != 200:
                    result["error"] = f"Ollama returned HTTP {resp.status_code}"
                    return result

                result["reachable"] = True
                data = resp.json()
                models_data = data.get("models", [])
                available_models = [m.get("name", "") for m in models_data]
                result["available_models"] = available_models

                # Check if selected model exists
                is_pulled = self.model in available_models
                # Also check partial match (qwen2.5:7b matches qwen2.5:7b-instruct-q4_K_M etc.)
                if not is_pulled:
                    for am in available_models:
                        if am.startswith(self.model.split(":")[0]):
                            is_pulled = True
                            result["model"] = am  # Use the actually pulled variant
                            break

                result["model_available"] = is_pulled
                result["ready"] = is_pulled
                result["setup_required"] = not is_pulled

                if not is_pulled:
                    result["recommended_command"] = f"ollama pull {self.model}"
                    result["error"] = (
                        f"Model '{self.model}' not found. "
                        f"Run: ollama pull {self.model}"
                    )

        except Exception as exc:
            result["error"] = f"Ollama is not reachable at {self.base_url}: {exc}"

        return result

    async def list_models(self) -> list[str]:
        """List all models available in Ollama."""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                if resp.status_code != 200:
                    return []
                data = resp.json()
                return [m.get("name", "") for m in data.get("models", [])]
        except Exception:
            return []

    async def check_model_available(self, model_name: str | None = None) -> bool:
        """Check if a specific model is pulled."""
        target = model_name or self.model
        available = await self.list_models()
        # Exact match
        if target in available:
            return True
        # Partial match (base name before tag)
        base = target.split(":")[0]
        for am in available:
            if am.startswith(base):
                return True
        return False

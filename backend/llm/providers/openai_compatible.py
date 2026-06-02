"""OpenAI-compatible LLM provider.

Works with: OpenAI, DeepSeek, LM Studio, LocalAI, and any endpoint
that speaks the OpenAI Chat Completions API.
"""

from __future__ import annotations

from backend.llm.providers import BaseLLMProvider


class OpenAICompatibleProvider(BaseLLMProvider):
    """Provider for any OpenAI Chat Completions compatible endpoint."""

    name = "openai_compatible"

    def __init__(
        self,
        base_url: str = "https://api.openai.com/v1",
        api_key: str = "",
        model: str = "gpt-4o-mini",
        timeout: int = 60,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    async def generate(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ) -> str:
        import httpx

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json={
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    async def is_available(self) -> bool:
        if not self.api_key:
            return False
        try:
            import httpx

            headers = {"Authorization": f"Bearer {self.api_key}"}
            async with httpx.AsyncClient(timeout=5) as client:
                # Try models endpoint (works for most providers)
                resp = await client.get(
                    f"{self.base_url}/models",
                    headers=headers,
                )
                return resp.status_code == 200
        except Exception:
            return False

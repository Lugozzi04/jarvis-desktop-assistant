"""WebSearchSkill — Google + SearXNG web search (NO DuckDuckGo).

Supports: Google HTML scraping, SearXNG public instances.
Returns structured results for LLM summarization or direct display.
"""

from __future__ import annotations

from typing import Any

from backend.core.logger import logger
from backend.core.schemas import ActionResult
from backend.skills.base import BaseSkill
from backend.skills.web_search.search_provider import search_web, format_results


class WebSearchSkill(BaseSkill):
    """Programmatic web search via Google + SearXNG."""

    def execute(self, action: str, parameters: dict[str, Any]) -> ActionResult:
        query = parameters.get("query", "")
        if not query:
            return self._result(action, success=False, error="No search query provided")

        if action in ("search_and_summarize", "search"):
            return self._search(query)
        else:
            return self._result(action, success=False, error=f"Unknown action: {action}")

    def _search(self, query: str) -> ActionResult:
        """Execute a web search and optionally summarize with Ollama."""
        try:
            results = search_web(query, max_results=5)
            if not results:
                return self._result(
                    "search_and_summarize",
                    success=True,
                    result=f"🔍 No results found for: {query}",
                )
            
            formatted = format_results(query, results)
            
            # Try AI summarization via Ollama
            ai_summary = self._summarize_with_ollama(query, results)
            if ai_summary:
                output = f"🤖 **AI Summary**\n{ai_summary}\n\n{formatted}"
            else:
                output = formatted
            
            return self._result(
                "search_and_summarize",
                success=True,
                result=output,
            )
        except Exception as exc:
            logger.error("Web search failed: {}", exc)
            return self._result(
                "search_and_summarize",
                success=False,
                error=f"Search failed: {exc}",
            )

    def _summarize_with_ollama(self, query: str, results: list[dict[str, str]]) -> str:
        """Try to summarize search results using Ollama."""
        try:
            import requests
            
            # Build context from results
            ctx_parts = []
            for i, r in enumerate(results[:5], 1):
                ctx_parts.append(f"{i}. {r['title']}\n   {r.get('snippet', '')[:300]}")
            context = "\n\n".join(ctx_parts)
            
            prompt = (
                f"Search results for '{query}':\n\n{context}\n\n"
                f"Summarize the key findings in 3-5 concise bullet points. "
                f"Respond in the same language as the query. Be factual and cite sources."
            )
            
            r = requests.post(
                "http://localhost:11434/api/chat",
                json={
                    "model": "qwen2.5:7b",
                    "messages": [
                        {"role": "system", "content": "You are a helpful search assistant. Summarize web results concisely."},
                        {"role": "user", "content": prompt},
                    ],
                    "stream": False,
                },
                timeout=30,
            )
            if r.status_code == 200:
                content = r.json().get("message", {}).get("content", "")
                if content:
                    return content
        except Exception as exc:
            logger.debug("Ollama summarization unavailable: {}", exc)
        
        return ""

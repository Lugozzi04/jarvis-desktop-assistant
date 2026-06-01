"""WebSearchSkill — programmatic web search with result summarization.

Supports multiple providers (DuckDuckGo, custom APIs).
Returns structured results for the LLM to summarize or for direct display.
"""

from __future__ import annotations

from typing import Any

from backend.core.logger import logger
from backend.core.schemas import ActionResult
from backend.skills.base import BaseSkill


class WebSearchSkill(BaseSkill):
    """Programmatic web search."""

    def execute(self, action: str, parameters: dict[str, Any]) -> ActionResult:
        query = parameters.get("query", "")
        if not query:
            return self._result(action, success=False, error="No search query provided")

        if action in ("search_and_summarize", "search"):
            return self._search(query)
        else:
            return self._result(action, success=False, error=f"Unknown action: {action}")

    def _search(self, query: str) -> ActionResult:
        """Execute a web search using DuckDuckGo HTML scraping."""
        try:
            import httpx
        except ImportError:
            return self._result(
                "search_and_summarize",
                success=False,
                error="httpx not installed. Run: pip install httpx",
            )

        try:
            # DuckDuckGo HTML search (no API key needed)
            url = "https://html.duckduckgo.com/html/"
            resp = httpx.post(
                url,
                data={"q": query},
                headers={"User-Agent": "JarvisDesktopAssistant/0.1"},
                timeout=10,
            )
            resp.raise_for_status()

            # Basic HTML result extraction
            results = self._parse_results(resp.text, query)
            if not results:
                return self._result(
                    "search_and_summarize",
                    success=True,
                    result=f"🔍 No results found for: {query}",
                )

            # Format output
            lines = [f"🔍 Results for: {query}", ""]
            for i, r in enumerate(results[:5], 1):
                lines.append(f"{i}. **{r['title']}**")
                lines.append(f"   {r['snippet'][:200]}")
                lines.append(f"   {r['url']}")
                lines.append("")

            return self._result(
                "search_and_summarize",
                success=True,
                result="\n".join(lines),
            )

        except Exception as exc:
            logger.error("Web search failed: {}", exc)
            return self._result(
                "search_and_summarize",
                success=False,
                error=f"Search failed: {exc}",
            )

    def _parse_results(self, html: str, query: str) -> list[dict[str, str]]:
        """Parse DuckDuckGo HTML results."""
        import re

        results = []
        # Simple regex-based extraction (works for DuckDuckGo HTML)
        # Find result blocks
        blocks = re.split(r'<div class="result', html)
        for block in blocks[1:6]:  # Skip first (before first result), limit to 5
            title_match = re.search(r'<a[^>]*class="result__a"[^>]*>(.*?)</a>', block, re.DOTALL)
            url_match = re.search(r'<a[^>]*class="result__url"[^>]*href="([^"]*)"', block)
            snippet_match = re.search(r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>', block, re.DOTALL)

            title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip() if title_match else "Untitled"
            url_clean = url_match.group(1) if url_match else ""
            snippet = re.sub(r'<[^>]+>', '', snippet_match.group(1)).strip() if snippet_match else ""

            if title and url_clean:
                results.append({"title": title, "url": url_clean, "snippet": snippet})

        return results

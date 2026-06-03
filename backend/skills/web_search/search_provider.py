"""Web search provider — DuckDuckGo HTML/lite (via ddgs), NO api.duckduckgo.com.

Uses the `ddgs` Python library which queries DuckDuckGo's HTML/lite endpoint.
This is NOT the official JSON API — it's the same endpoint a browser uses.
No API key needed. Works reliably from any IP.

Priority:
  1. ddgs (DuckDuckGo HTML) — fast, reliable, no blocks
  2. Google HTML scraping — fallback, may trigger CAPTCHA
"""

from __future__ import annotations

import re
from typing import Any

import httpx
from backend.core.logger import logger

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)


def search_web(query: str, max_results: int = 5) -> list[dict[str, str]]:
    """Search the web. Returns list of {title, url, snippet}."""

    # ── 1. Primary: ddgs (DuckDuckGo HTML endpoint) ──
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            results = []
            for r in ddgs.text(query, max_results=max_results, region="it-it"):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                })
            if results:
                logger.info("ddgs returned {} results", len(results))
                return results
    except ImportError:
        logger.debug("ddgs not installed — falling back to Google")
    except Exception as exc:
        logger.warning("ddgs search failed: {}", exc)

    # ── 2. Fallback: Google HTML scraping ──
    try:
        results = _google_scrape(query, max_results)
        if results:
            logger.info("Google scrape returned {} results", len(results))
            return results
    except Exception as exc:
        logger.warning("Google scrape failed: {}", exc)

    return []


def _google_scrape(query: str, max_results: int) -> list[dict[str, str]]:
    """Scrape Google search results HTML."""
    from urllib.parse import quote_plus
    
    url = f"https://www.google.com/search?q={quote_plus(query)}&hl=en"

    with httpx.Client(timeout=10.0) as client:
        r = client.get(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )
        r.raise_for_status()
        html = r.text

    results = []
    blocks = re.split(r'<div class="[^"]*g[^"]*"[^>]*>', html)

    for block in blocks[1:]:
        if len(results) >= max_results:
            break

        url_match = re.search(r'href="/url\?q=([^"&]+)', block)
        title_match = re.search(r'<h3[^>]*>(.*?)</h3>', block, re.DOTALL)
        snippet_match = re.search(
            r'<div[^>]*class="[^"]*(?:BNeawe|VwiC3b|IsZvec)[^"]*"[^>]*>(.*?)</div>',
            block, re.DOTALL
        )
        if not snippet_match:
            snippet_match = re.search(
                r'<span[^>]*class="[^"]*aCOpRe[^"]*"[^>]*>(.*?)</span>',
                block, re.DOTALL
            )

        url_val = url_match.group(1) if url_match else ""
        title_val = _clean_html(title_match.group(1)) if title_match else ""
        snippet_val = _clean_html(snippet_match.group(1)) if snippet_match else ""

        if title_val and url_val and "google.com" not in url_val:
            results.append({
                "title": title_val,
                "url": url_val,
                "snippet": snippet_val[:300],
            })

    return results


def _clean_html(text: str) -> str:
    """Strip HTML tags and entities."""
    text = re.sub(r'<[^>]+>', '', text)
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " ")
    return text.strip()


def format_results(query: str, results: list[dict[str, str]]) -> str:
    """Format search results for display or LLM context."""
    if not results:
        return f"No results found for: {query}"

    lines = [f"🔍 Web results for: {query}", ""]
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. **{r['title']}**")
        if r.get("snippet"):
            lines.append(f"   {r['snippet'][:200]}")
        lines.append(f"   {r['url']}")
        lines.append("")

    return "\n".join(lines)

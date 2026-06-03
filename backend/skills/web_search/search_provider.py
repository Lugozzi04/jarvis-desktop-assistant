"""Web search provider — Google + SearXNG (NO DuckDuckGo).

Priority:
  1. SearXNG public instances (JSON API, aggregates Google/Bing/etc.)
  2. Direct Google HTML scraping (fallback)

No API keys needed. No DuckDuckGo.
"""

from __future__ import annotations

import re
import time
from typing import Any
from urllib.parse import quote_plus

import httpx
from backend.core.logger import logger

# ── SearXNG public instances ──
SEARX_INSTANCES = [
    "https://searx.be",
    "https://search.sapti.me",
    "https://searx.tiekoetter.com",
    "https://searx.fmac.xyz",
]

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)


def search_web(query: str, max_results: int = 5) -> list[dict[str, str]]:
    """Search the web. Returns list of {title, url, snippet}."""
    
    # ── 1. Try SearXNG ──
    for instance in SEARX_INSTANCES:
        try:
            results = _searx_search(instance, query, max_results)
            if results:
                logger.info("SearXNG returned {} results from {}", len(results), instance)
                return results
        except Exception as exc:
            logger.debug("SearXNG {} failed: {}", instance, exc)
            continue

    # ── 2. Fallback: Google HTML scraping ──
    try:
        results = _google_scrape(query, max_results)
        if results:
            logger.info("Google scrape returned {} results", len(results))
            return results
    except Exception as exc:
        logger.warning("Google scrape failed: {}", exc)

    return []


def _searx_search(instance: str, query: str, max_results: int) -> list[dict[str, str]]:
    """Query a SearXNG instance's JSON API."""
    url = f"{instance}/search"
    params = {
        "q": query,
        "format": "json",
        "categories": "general",
        "language": "auto",
    }
    
    with httpx.Client(timeout=8.0) as client:
        r = client.get(url, params=params, headers={"User-Agent": USER_AGENT})
        r.raise_for_status()
        data = r.json()
    
    results = []
    for item in data.get("results", [])[:max_results]:
        results.append({
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "snippet": _clean_html(item.get("content", "")),
        })
    return results


def _google_scrape(query: str, max_results: int) -> list[dict[str, str]]:
    """Scrape Google search results HTML."""
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
    # Extract results using regex patterns for Google's HTML structure
    # Pattern: <a href="/url?q=REAL_URL" ...><h3>TITLE</h3></a> ... snippet
    
    # Find all result blocks
    blocks = re.split(r'<div class="[^"]*g[^"]*"[^>]*>', html)
    
    for block in blocks[1:]:
        if len(results) >= max_results:
            break
            
        # Extract URL from href
        url_match = re.search(r'href="/url\?q=([^"&]+)', block)
        # Extract title from h3
        title_match = re.search(r'<h3[^>]*>(.*?)</h3>', block, re.DOTALL)
        # Extract snippet
        snippet_match = re.search(
            r'<div[^>]*class="[^"]*(?:BNeawe|VwiC3b|IsZvec)[^"]*"[^>]*>(.*?)</div>',
            block, re.DOTALL
        )
        # Fallback snippet pattern
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

"""Web search tools — Brave Search API.

Each tool is a (schema, handler) pair:
  - schema: JSON dict for Claude's tool_use format
  - handler: plain function that executes the tool
"""

from __future__ import annotations

import os

import httpx

# ── Brave Web Search ────────────────────────────────────────────────

BRAVE_SEARCH_SCHEMA = {
    "name": "brave_search",
    "description": (
        "Search the web using Brave Search API. "
        "Returns results with title, url, description. "
        "Use for finding industry news, research papers, and trends."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "count": {
                "type": "integer",
                "description": "Number of results (max 20)",
                "default": 10,
            },
        },
        "required": ["query"],
    },
}


def brave_search(query: str, count: int = 10) -> str:
    api_key = os.environ.get("BRAVE_API_KEY", "")
    if not api_key:
        return "Error: BRAVE_API_KEY not configured. Set it in .env"

    resp = httpx.get(
        "https://api.search.brave.com/res/v1/web/search",
        headers={
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": api_key,
        },
        params={"q": query, "count": min(count, 20), "freshness": "pw"},
    )
    resp.raise_for_status()

    results = []
    for item in resp.json().get("web", {}).get("results", []):
        results.append({
            "title": item.get("title"),
            "url": item.get("url"),
            "description": item.get("description"),
            "age": item.get("age"),
        })
    return str(results)


# ── Brave News Search ───────────────────────────────────────────────

BRAVE_NEWS_SCHEMA = {
    "name": "brave_news_search",
    "description": (
        "Search for recent news using Brave News API. "
        "Returns news articles from the past 24 hours, sorted by recency."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "News search query"},
            "count": {
                "type": "integer",
                "description": "Number of results (max 20)",
                "default": 10,
            },
        },
        "required": ["query"],
    },
}


def brave_news_search(query: str, count: int = 10) -> str:
    api_key = os.environ.get("BRAVE_API_KEY", "")
    if not api_key:
        return "Error: BRAVE_API_KEY not configured"

    resp = httpx.get(
        "https://api.search.brave.com/res/v1/news/search",
        headers={
            "Accept": "application/json",
            "X-Subscription-Token": api_key,
        },
        params={"q": query, "count": min(count, 20), "freshness": "pd"},
    )
    resp.raise_for_status()

    results = []
    for item in resp.json().get("results", []):
        results.append({
            "title": item.get("title"),
            "url": item.get("url"),
            "description": item.get("description"),
            "source": item.get("meta_url", {}).get("hostname"),
            "age": item.get("age"),
        })
    return str(results)


# ── Registry ────────────────────────────────────────────────────────

SEARCH_TOOLS = {
    "brave_search": (BRAVE_SEARCH_SCHEMA, brave_search),
    "brave_news_search": (BRAVE_NEWS_SCHEMA, brave_news_search),
}

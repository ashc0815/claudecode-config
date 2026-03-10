"""Web search tools wrapping Brave Search API for news discovery."""

from __future__ import annotations

import os

import httpx
from crewai.tools import BaseTool
from pydantic import Field


class BraveSearchTool(BaseTool):
    name: str = "brave_search"
    description: str = (
        "Search the web using Brave Search API. Input: 'query' (search string). "
        "Returns a list of results with title, url, and description. "
        "Use for finding industry news, research papers, and trends."
    )

    api_key: str = Field(default="")

    def model_post_init(self, __context: object) -> None:
        self.api_key = self.api_key or os.environ.get("BRAVE_API_KEY", "")

    def _run(self, query: str, count: int = 10) -> str:
        if not self.api_key:
            return "Error: BRAVE_API_KEY not configured. Set it in .env"

        resp = httpx.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers={
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": self.api_key,
            },
            params={
                "q": query,
                "count": min(count, 20),
                "freshness": "pw",  # Past week
            },
        )
        resp.raise_for_status()

        results = []
        for item in resp.json().get("web", {}).get("results", []):
            results.append(
                {
                    "title": item.get("title"),
                    "url": item.get("url"),
                    "description": item.get("description"),
                    "age": item.get("age"),
                }
            )
        return str(results)


class BraveNewsTool(BaseTool):
    name: str = "brave_news_search"
    description: str = (
        "Search for recent news using Brave News API. Input: 'query'. "
        "Returns news articles from the past 24 hours, sorted by recency."
    )

    api_key: str = Field(default="")

    def model_post_init(self, __context: object) -> None:
        self.api_key = self.api_key or os.environ.get("BRAVE_API_KEY", "")

    def _run(self, query: str, count: int = 10) -> str:
        if not self.api_key:
            return "Error: BRAVE_API_KEY not configured"

        resp = httpx.get(
            "https://api.search.brave.com/res/v1/news/search",
            headers={
                "Accept": "application/json",
                "X-Subscription-Token": self.api_key,
            },
            params={
                "q": query,
                "count": min(count, 20),
                "freshness": "pd",  # Past day
            },
        )
        resp.raise_for_status()

        results = []
        for item in resp.json().get("results", []):
            results.append(
                {
                    "title": item.get("title"),
                    "url": item.get("url"),
                    "description": item.get("description"),
                    "source": item.get("meta_url", {}).get("hostname"),
                    "age": item.get("age"),
                }
            )
        return str(results)

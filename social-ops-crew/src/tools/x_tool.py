"""X/Twitter API v2 tools for publishing threads and collecting metrics."""

from __future__ import annotations

import os
from typing import Any

import httpx
from crewai.tools import BaseTool
from pydantic import Field


class XBaseTool(BaseTool):
    """Base class with shared X API auth."""

    bearer_token: str = Field(default="")

    def model_post_init(self, __context: Any) -> None:
        self.bearer_token = self.bearer_token or os.environ.get("X_BEARER_TOKEN", "")

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.bearer_token}",
            "Content-Type": "application/json",
        }


class XPublishThreadTool(XBaseTool):
    name: str = "x_publish_thread"
    description: str = (
        "Publish a thread on X/Twitter. Input: 'tweets' (list of strings, "
        "each <= 280 chars). Posts them as a reply chain."
    )

    def _run(self, tweets: list[str]) -> str:
        # X API v2 uses OAuth 1.0a for posting — need user context tokens
        access_token = os.environ.get("X_ACCESS_TOKEN", "")
        access_secret = os.environ.get("X_ACCESS_SECRET", "")

        if not access_token:
            return "Error: X_ACCESS_TOKEN not configured"

        posted_ids = []
        reply_to = None

        for i, tweet_text in enumerate(tweets):
            if len(tweet_text) > 280:
                return f"Error: Tweet {i + 1} exceeds 280 chars ({len(tweet_text)})"

            payload: dict[str, Any] = {"text": tweet_text}
            if reply_to:
                payload["reply"] = {"in_reply_to_tweet_id": reply_to}

            resp = httpx.post(
                "https://api.x.com/2/tweets",
                headers=self._headers(),
                json=payload,
            )
            resp.raise_for_status()
            tweet_id = resp.json()["data"]["id"]
            posted_ids.append(tweet_id)
            reply_to = tweet_id

        return f"Thread published: {len(posted_ids)} tweets. First ID: {posted_ids[0]}"


class XSearchTool(XBaseTool):
    name: str = "x_search"
    description: str = (
        "Search recent tweets on X/Twitter. Input: 'query' (search string). "
        "Returns recent tweets matching the query."
    )

    def _run(self, query: str, max_results: int = 20) -> str:
        resp = httpx.get(
            "https://api.x.com/2/tweets/search/recent",
            headers=self._headers(),
            params={
                "query": query,
                "max_results": min(max_results, 100),
                "tweet.fields": "created_at,public_metrics,author_id",
            },
        )
        resp.raise_for_status()
        tweets = resp.json().get("data", [])
        results = []
        for t in tweets:
            results.append(
                {
                    "id": t["id"],
                    "text": t["text"],
                    "metrics": t.get("public_metrics", {}),
                    "created_at": t.get("created_at"),
                }
            )
        return str(results)


class XMetricsTool(XBaseTool):
    name: str = "x_metrics"
    description: str = "Get engagement metrics for a tweet. Input: 'tweet_id'."

    def _run(self, tweet_id: str) -> str:
        resp = httpx.get(
            f"https://api.x.com/2/tweets/{tweet_id}",
            headers=self._headers(),
            params={"tweet.fields": "public_metrics"},
        )
        resp.raise_for_status()
        return str(resp.json()["data"].get("public_metrics", {}))

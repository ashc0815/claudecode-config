"""X/Twitter API v2 tools — publish threads, search, metrics."""

from __future__ import annotations

import os
from typing import Any

import httpx


def _headers() -> dict:
    token = os.environ.get("X_BEARER_TOKEN", "")
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ── Handlers ────────────────────────────────────────────────────────

def x_publish_thread(tweets: list[str]) -> str:
    access_token = os.environ.get("X_ACCESS_TOKEN", "")
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

        resp = httpx.post("https://api.x.com/2/tweets", headers=_headers(), json=payload)
        resp.raise_for_status()
        tweet_id = resp.json()["data"]["id"]
        posted_ids.append(tweet_id)
        reply_to = tweet_id

    return f"Thread published: {len(posted_ids)} tweets. First ID: {posted_ids[0]}"


def x_search(query: str, max_results: int = 20) -> str:
    resp = httpx.get(
        "https://api.x.com/2/tweets/search/recent",
        headers=_headers(),
        params={
            "query": query,
            "max_results": min(max_results, 100),
            "tweet.fields": "created_at,public_metrics,author_id",
        },
    )
    resp.raise_for_status()
    results = []
    for t in resp.json().get("data", []):
        results.append({
            "id": t["id"],
            "text": t["text"],
            "metrics": t.get("public_metrics", {}),
            "created_at": t.get("created_at"),
        })
    return str(results)


def x_metrics(tweet_id: str) -> str:
    resp = httpx.get(
        f"https://api.x.com/2/tweets/{tweet_id}",
        headers=_headers(),
        params={"tweet.fields": "public_metrics"},
    )
    resp.raise_for_status()
    return str(resp.json()["data"].get("public_metrics", {}))


# ── Schemas ─────────────────────────────────────────────────────────

X_PUBLISH_THREAD_SCHEMA = {
    "name": "x_publish_thread",
    "description": "Publish a thread on X/Twitter. Posts tweets as a reply chain.",
    "input_schema": {
        "type": "object",
        "properties": {
            "tweets": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of tweet texts (each <= 280 chars)",
            },
        },
        "required": ["tweets"],
    },
}

X_SEARCH_SCHEMA = {
    "name": "x_search",
    "description": "Search recent tweets on X/Twitter.",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "max_results": {"type": "integer", "default": 20},
        },
        "required": ["query"],
    },
}

X_METRICS_SCHEMA = {
    "name": "x_metrics",
    "description": "Get engagement metrics for a tweet.",
    "input_schema": {
        "type": "object",
        "properties": {
            "tweet_id": {"type": "string", "description": "Tweet ID"},
        },
        "required": ["tweet_id"],
    },
}

# ── Registry ────────────────────────────────────────────────────────

X_TOOLS = {
    "x_publish_thread": (X_PUBLISH_THREAD_SCHEMA, x_publish_thread),
    "x_search": (X_SEARCH_SCHEMA, x_search),
    "x_metrics": (X_METRICS_SCHEMA, x_metrics),
}

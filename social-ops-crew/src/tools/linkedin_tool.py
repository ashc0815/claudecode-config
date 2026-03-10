"""LinkedIn API tools — publish, comment, feed, metrics."""

from __future__ import annotations

import os
import time

import httpx


def _headers() -> dict:
    token = os.environ.get("LINKEDIN_ACCESS_TOKEN", "")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }


def _get_user_id() -> str:
    resp = httpx.get("https://api.linkedin.com/v2/userinfo", headers=_headers())
    resp.raise_for_status()
    return resp.json()["sub"]


# ── Handlers ────────────────────────────────────────────────────────

def linkedin_publish(text: str, hashtags: list[str] | None = None) -> str:
    user_id = _get_user_id()
    if hashtags:
        text = text + "\n\n" + " ".join(hashtags)

    payload = {
        "author": f"urn:li:person:{user_id}",
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }

    resp = httpx.post("https://api.linkedin.com/v2/ugcPosts", headers=_headers(), json=payload)
    resp.raise_for_status()
    post_id = resp.headers.get("x-restli-id", resp.json().get("id", "unknown"))
    return f"Published successfully. Post ID: {post_id}"


def linkedin_comment(post_urn: str, comment_text: str) -> str:
    user_id = _get_user_id()
    payload = {"actor": f"urn:li:person:{user_id}", "message": {"text": comment_text}}
    resp = httpx.post(
        f"https://api.linkedin.com/v2/socialActions/{post_urn}/comments",
        headers=_headers(),
        json=payload,
    )
    resp.raise_for_status()
    return f"Comment posted successfully on {post_urn}"


def linkedin_feed(count: int = 50) -> str:
    resp = httpx.get(
        "https://api.linkedin.com/v2/feed",
        headers=_headers(),
        params={"count": min(count, 100), "sortBy": "RELEVANCE"},
    )
    resp.raise_for_status()
    posts = resp.json().get("elements", [])
    results = []
    for p in posts[:count]:
        results.append({
            "urn": p.get("id"),
            "author": p.get("author"),
            "text": (
                p.get("specificContent", {})
                .get("com.linkedin.ugc.ShareContent", {})
                .get("shareCommentary", {})
                .get("text", "")
            ),
            "created": p.get("created", {}).get("time"),
        })
    return str(results)


def linkedin_metrics(post_urn: str) -> str:
    resp = httpx.get(
        f"https://api.linkedin.com/v2/socialActions/{post_urn}",
        headers=_headers(),
    )
    resp.raise_for_status()
    data = resp.json()
    return str({
        "likes": data.get("likesSummary", {}).get("totalLikes", 0),
        "comments": data.get("commentsSummary", {}).get("totalFirstLevelComments", 0),
        "shares": data.get("sharesSummary", {}).get("totalShares", 0),
    })


# ── Rate limiter (used by pipeline, not by Claude) ──────────────────

class LinkedInRateLimiter:
    def __init__(self, max_per_hour: int = 5, min_interval_sec: int = 120):
        self.max_per_hour = max_per_hour
        self.min_interval_sec = min_interval_sec
        self._timestamps: list[float] = []

    def can_proceed(self) -> bool:
        now = time.time()
        self._timestamps = [t for t in self._timestamps if t > now - 3600]
        if len(self._timestamps) >= self.max_per_hour:
            return False
        if self._timestamps and (now - self._timestamps[-1]) < self.min_interval_sec:
            return False
        return True

    def record(self) -> None:
        self._timestamps.append(time.time())

    def wait_time(self) -> float:
        now = time.time()
        if self._timestamps and (now - self._timestamps[-1]) < self.min_interval_sec:
            return self.min_interval_sec - (now - self._timestamps[-1])
        return 0


# ── Schemas ─────────────────────────────────────────────────────────

LINKEDIN_PUBLISH_SCHEMA = {
    "name": "linkedin_publish",
    "description": "Publish a text post to LinkedIn.",
    "input_schema": {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Post content"},
            "hashtags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional hashtags",
            },
        },
        "required": ["text"],
    },
}

LINKEDIN_COMMENT_SCHEMA = {
    "name": "linkedin_comment",
    "description": "Post a comment on a LinkedIn post.",
    "input_schema": {
        "type": "object",
        "properties": {
            "post_urn": {"type": "string", "description": "The post URN to comment on"},
            "comment_text": {"type": "string", "description": "Your comment"},
        },
        "required": ["post_urn", "comment_text"],
    },
}

LINKEDIN_FEED_SCHEMA = {
    "name": "linkedin_feed",
    "description": "Fetch recent posts from LinkedIn feed with author, text, and URN.",
    "input_schema": {
        "type": "object",
        "properties": {
            "count": {
                "type": "integer",
                "description": "Number of posts (max 100)",
                "default": 50,
            },
        },
    },
}

LINKEDIN_METRICS_SCHEMA = {
    "name": "linkedin_metrics",
    "description": "Get engagement metrics (likes, comments, shares) for a LinkedIn post.",
    "input_schema": {
        "type": "object",
        "properties": {
            "post_urn": {"type": "string", "description": "The post URN"},
        },
        "required": ["post_urn"],
    },
}

# ── Registry ────────────────────────────────────────────────────────

LINKEDIN_TOOLS = {
    "linkedin_publish": (LINKEDIN_PUBLISH_SCHEMA, linkedin_publish),
    "linkedin_comment": (LINKEDIN_COMMENT_SCHEMA, linkedin_comment),
    "linkedin_feed": (LINKEDIN_FEED_SCHEMA, linkedin_feed),
    "linkedin_metrics": (LINKEDIN_METRICS_SCHEMA, linkedin_metrics),
}

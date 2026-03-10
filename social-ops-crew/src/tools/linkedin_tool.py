"""LinkedIn API tools for publishing, commenting, and analytics."""

from __future__ import annotations

import os
import time
from typing import Any

import httpx
from crewai.tools import BaseTool
from pydantic import Field


class LinkedInBaseTool(BaseTool):
    """Base class with shared LinkedIn API auth."""

    access_token: str = Field(default="")

    def model_post_init(self, __context: Any) -> None:
        self.access_token = self.access_token or os.environ.get("LINKEDIN_ACCESS_TOKEN", "")

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        }

    def _get_user_id(self) -> str:
        resp = httpx.get("https://api.linkedin.com/v2/userinfo", headers=self._headers())
        resp.raise_for_status()
        return resp.json()["sub"]


class LinkedInPublishTool(LinkedInBaseTool):
    name: str = "linkedin_publish"
    description: str = (
        "Publish a text post to LinkedIn. Input: JSON with 'text' (post content) "
        "and optional 'hashtags' (list of strings)."
    )

    def _run(self, text: str, hashtags: list[str] | None = None) -> str:
        user_id = self._get_user_id()

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

        resp = httpx.post(
            "https://api.linkedin.com/v2/ugcPosts",
            headers=self._headers(),
            json=payload,
        )
        resp.raise_for_status()
        post_id = resp.headers.get("x-restli-id", resp.json().get("id", "unknown"))
        return f"Published successfully. Post ID: {post_id}"


class LinkedInCommentTool(LinkedInBaseTool):
    name: str = "linkedin_comment"
    description: str = (
        "Post a comment on a LinkedIn post. Input: 'post_urn' (the post URN) "
        "and 'comment_text' (your comment)."
    )

    def _run(self, post_urn: str, comment_text: str) -> str:
        user_id = self._get_user_id()

        payload = {
            "actor": f"urn:li:person:{user_id}",
            "message": {"text": comment_text},
        }

        resp = httpx.post(
            f"https://api.linkedin.com/v2/socialActions/{post_urn}/comments",
            headers=self._headers(),
            json=payload,
        )
        resp.raise_for_status()
        return f"Comment posted successfully on {post_urn}"


class LinkedInFeedTool(LinkedInBaseTool):
    name: str = "linkedin_feed"
    description: str = (
        "Fetch recent posts from LinkedIn feed. Returns a list of posts "
        "with author, text, engagement metrics, and post URN."
    )

    def _run(self, count: int = 50) -> str:
        # LinkedIn Feed API — requires Marketing API access
        # Fallback: use search API for specific authors from watchlist
        resp = httpx.get(
            "https://api.linkedin.com/v2/feed",
            headers=self._headers(),
            params={"count": min(count, 100), "sortBy": "RELEVANCE"},
        )
        resp.raise_for_status()
        posts = resp.json().get("elements", [])
        results = []
        for p in posts[:count]:
            results.append(
                {
                    "urn": p.get("id"),
                    "author": p.get("author"),
                    "text": p.get("specificContent", {})
                    .get("com.linkedin.ugc.ShareContent", {})
                    .get("shareCommentary", {})
                    .get("text", ""),
                    "created": p.get("created", {}).get("time"),
                }
            )
        return str(results)


class LinkedInMetricsTool(LinkedInBaseTool):
    name: str = "linkedin_metrics"
    description: str = (
        "Get engagement metrics for a LinkedIn post. Input: 'post_urn'. "
        "Returns impressions, likes, comments, shares, saves."
    )

    def _run(self, post_urn: str) -> str:
        resp = httpx.get(
            f"https://api.linkedin.com/v2/socialActions/{post_urn}",
            headers=self._headers(),
        )
        resp.raise_for_status()
        data = resp.json()
        return str(
            {
                "likes": data.get("likesSummary", {}).get("totalLikes", 0),
                "comments": data.get("commentsSummary", {}).get("totalFirstLevelComments", 0),
                "shares": data.get("sharesSummary", {}).get("totalShares", 0),
            }
        )


class LinkedInRateLimiter:
    """Enforce rate limits for LinkedIn API calls (especially comments)."""

    def __init__(self, max_per_hour: int = 5, min_interval_sec: int = 120):
        self.max_per_hour = max_per_hour
        self.min_interval_sec = min_interval_sec
        self._timestamps: list[float] = []

    def can_proceed(self) -> bool:
        now = time.time()
        hour_ago = now - 3600
        self._timestamps = [t for t in self._timestamps if t > hour_ago]
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

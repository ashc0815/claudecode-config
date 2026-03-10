"""Agent definitions — system prompts + tool sets for each agent.

Each agent is a dict: {"system_prompt": str, "tools": dict, "temperature": float}
No classes, no framework — just data that feeds into runner.run_agent().
"""

from __future__ import annotations

from pathlib import Path

import yaml

from src.tools.data_tool import DATA_TOOLS
from src.tools.linkedin_tool import LINKEDIN_TOOLS
from src.tools.notification_tool import NOTIFICATION_TOOLS
from src.tools.search_tool import SEARCH_TOOLS
from src.tools.x_tool import X_TOOLS

_CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


def _load_yaml(name: str) -> dict:
    return yaml.safe_load((_CONFIG_DIR / name).read_text())


def _persona_context() -> str:
    """Load persona config as context string for content-generating agents."""
    persona = _load_yaml("persona.yaml")
    return (
        f"Your public persona: {persona['identity']['name']} — "
        f"{persona['identity']['tagline']}.\n"
        f"Voice: {persona['voice']['tone']}, {persona['voice']['style']}.\n"
        f"Perspective: {persona['voice']['perspective']}.\n"
        f"Do: {', '.join(persona['voice']['do'])}.\n"
        f"Don't: {', '.join(persona['voice']['dont'])}.\n"
        f"Primary expertise: {', '.join(persona['expertise_areas']['primary'])}."
    )


def _watchlist_context() -> str:
    """Load watchlist as context string for engager agent."""
    wl = _load_yaml("watchlist.yaml")
    lines = ["LinkedIn monitoring targets:"]
    for tier_key in ("tier_1", "tier_2"):
        targets = wl.get("linkedin", {}).get(tier_key, [])
        if isinstance(targets, list):
            for t in targets:
                if isinstance(t, dict):
                    lines.append(
                        f"  - [{tier_key}] {t['name']} "
                        f"({', '.join(t.get('topics', []))})"
                    )
    tags = wl.get("linkedin", {}).get("topic_tags", [])
    if tags:
        lines.append(f"  Topic tags: {', '.join(tags)}")
    return "\n".join(lines)


def _pick(registries: list[dict], names: list[str]) -> dict:
    """Pick specific tools from registries by name."""
    result = {}
    for reg in registries:
        for name in names:
            if name in reg:
                result[name] = reg[name]
    return result


# ── Agent Definitions ───────────────────────────────────────────────

def get_agents() -> dict[str, dict]:
    cfg = _load_yaml("agents.yaml")

    return {
        "scout": {
            "system_prompt": (
                f"Role: {cfg['scout']['role']}\n"
                f"Goal: {cfg['scout']['goal']}\n"
                f"Backstory: {cfg['scout']['backstory']}\n\n"
                "Instructions:\n"
                "1. Load the strategy config to get keyword priorities.\n"
                "2. Search for news using multiple queries from the keyword list.\n"
                "3. Score each result for relevance, timeliness, and platform fit.\n"
                "4. Save the top 10-15 candidates as YAML via save_scout_pool.\n"
                "5. Return a summary of what you found."
            ),
            "tools": _pick(
                [SEARCH_TOOLS, DATA_TOOLS],
                [
                    "brave_search",
                    "brave_news_search",
                    "save_scout_pool",
                    "load_strategy_config",
                ],
            ),
            "temperature": 0.3,
        },
        "planner": {
            "system_prompt": (
                f"Role: {cfg['planner']['role']}\n"
                f"Goal: {cfg['planner']['goal']}\n"
                f"Backstory: {cfg['planner']['backstory']}\n\n"
                "Instructions:\n"
                "1. Load today's scout pool and the strategy config.\n"
                "2. Select 2-3 best topics considering weekly mix, hook rotation, dedup.\n"
                "3. Assign time slots, platforms, and hook formulas.\n"
                "4. Save the plan via save_daily_plan.\n"
                "5. Send the plan for human approval via request_human_approval.\n"
                "6. Return the approved plan (or note rejections)."
            ),
            "tools": _pick(
                [DATA_TOOLS, NOTIFICATION_TOOLS],
                [
                    "load_scout_pool",
                    "load_strategy_config",
                    "save_daily_plan",
                    "telegram_notify",
                    "request_human_approval",
                ],
            ),
            "temperature": 0.3,
        },
        "creator": {
            "system_prompt": (
                f"Role: {cfg['creator']['role']}\n"
                f"Goal: {cfg['creator']['goal']}\n"
                f"Backstory: {cfg['creator']['backstory']}\n\n"
                f"{_persona_context()}\n\n"
                "Instructions:\n"
                "1. For each post in the daily plan, generate platform-native content.\n"
                "2. LinkedIn: text + hashtags + image prompt.\n"
                "3. X: thread format with tweet numbering (each <= 280 chars).\n"
                "4. Run an 8-point quality check on each piece.\n"
                "5. Save each content package via save_content_package.\n"
                "6. Return summaries of all generated content."
            ),
            "tools": _pick(
                [DATA_TOOLS, SEARCH_TOOLS],
                ["save_content_package", "brave_search"],
            ),
            "temperature": 0.7,
        },
        "publisher": {
            "system_prompt": (
                f"Role: {cfg['publisher']['role']}\n"
                f"Goal: {cfg['publisher']['goal']}\n"
                f"Backstory: {cfg['publisher']['backstory']}\n\n"
                "Instructions:\n"
                "1. Publish approved content to designated platforms.\n"
                "2. Use linkedin_publish for LinkedIn posts.\n"
                "3. Use x_publish_thread for X threads.\n"
                "4. Record post IDs and send confirmation via telegram_notify.\n"
                "5. Retry up to 2 times on failure.\n"
                "Safety: max 3 posts per day."
            ),
            "tools": _pick(
                [LINKEDIN_TOOLS, X_TOOLS, NOTIFICATION_TOOLS],
                ["linkedin_publish", "x_publish_thread", "telegram_notify"],
            ),
            "temperature": 0.1,
        },
        "engager": {
            "system_prompt": (
                f"Role: {cfg['engager']['role']}\n"
                f"Goal: {cfg['engager']['goal']}\n"
                f"Backstory: {cfg['engager']['backstory']}\n\n"
                f"{_persona_context()}\n\n"
                f"{_watchlist_context()}\n\n"
                "Instructions:\n"
                "1. Load strategy config for engagement limits.\n"
                "2. Fetch LinkedIn feed.\n"
                "3. Filter by watchlist targets and topic tags.\n"
                "4. Score posts (author influence, relevance, timeliness).\n"
                "5. For posts scoring > 7/10, generate a substantive comment:\n"
                "   - 30-150 words\n"
                "   - Must include: data point, personal observation, or smart question\n"
                "   - Must NOT include: self-promotion, generic praise\n"
                "6. Request approval for Tier 1/2 comments.\n"
                "7. Post approved comments and log activity.\n"
                "Rate limits: max 5/hour, 120s between comments."
            ),
            "tools": _pick(
                [LINKEDIN_TOOLS, DATA_TOOLS, NOTIFICATION_TOOLS],
                [
                    "linkedin_feed",
                    "linkedin_comment",
                    "load_strategy_config",
                    "save_engager_log",
                    "request_human_approval",
                ],
            ),
            "temperature": 0.5,
        },
        "analyst": {
            "system_prompt": (
                f"Role: {cfg['analyst']['role']}\n"
                f"Goal: {cfg['analyst']['goal']}\n"
                f"Backstory: {cfg['analyst']['backstory']}\n\n"
                "Instructions:\n"
                "1. Collect metrics for recently published posts.\n"
                "2. Calculate derived metrics: save_rate, engagement_rate, viral_coefficient.\n"
                "3. Save analytics data per post.\n"
                "4. Generate a daily report with best/worst performers.\n"
                "5. Send the report via telegram_notify.\n"
                "6. Return the full report."
            ),
            "tools": _pick(
                [LINKEDIN_TOOLS, X_TOOLS, DATA_TOOLS, NOTIFICATION_TOOLS],
                [
                    "linkedin_metrics",
                    "x_metrics",
                    "save_analytics",
                    "load_recent_analytics",
                    "telegram_notify",
                ],
            ),
            "temperature": 0.2,
        },
        "strategist": {
            "system_prompt": (
                f"Role: {cfg['strategist']['role']}\n"
                f"Goal: {cfg['strategist']['goal']}\n"
                f"Backstory: {cfg['strategist']['backstory']}\n\n"
                "Instructions:\n"
                "1. Load recent analytics (past 7 days).\n"
                "2. Load current strategy config.\n"
                "3. Analyze performance by hook formula, topic, platform, time.\n"
                "4. Recommend specific parameter changes with data justification.\n"
                "5. Present recommendations via request_human_approval.\n"
                "6. Return the strategy update proposal.\n"
                "Always present options — the human has final say."
            ),
            "tools": _pick(
                [DATA_TOOLS, NOTIFICATION_TOOLS],
                [
                    "load_recent_analytics",
                    "load_strategy_config",
                    "request_human_approval",
                    "telegram_notify",
                ],
            ),
            "temperature": 0.3,
        },
    }

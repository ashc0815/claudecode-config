"""Pipeline definitions — replaces CrewAI crews with plain function chains.

Each pipeline is a function that runs agents in sequence,
passing the output of one as input context to the next.
"""

from __future__ import annotations

from datetime import datetime

from src.agents.definitions import get_agents
from src.runner import run_agent


def _run(agent_name: str, task: str, context: str = "") -> str:
    """Run a named agent with optional context from a previous step."""
    agents = get_agents()
    agent = agents[agent_name]

    user_message = task
    if context:
        user_message = f"Context from previous step:\n{context}\n\n---\n\nYour task:\n{task}"

    print(f"\n{'=' * 60}")
    print(f"  Running: {agent_name}")
    print(f"{'=' * 60}\n")

    return run_agent(
        system_prompt=agent["system_prompt"],
        user_message=user_message,
        tools=agent["tools"],
        temperature=agent.get("temperature", 0.3),
        verbose=True,
    )


# ── Content Pipeline (daily) ────────────────────────────────────────

def run_content_pipeline() -> str:
    """Scout → Plan → Create → Publish. Returns final summary."""

    scout_result = _run(
        "scout",
        "Scan industry news for the past 12 hours. Find top 10-15 candidates "
        "in AI, fintech, and future-of-work. Score and save them.",
    )

    plan_result = _run(
        "planner",
        "Create today's publishing plan: select 2-3 topics, assign time slots "
        "and platforms, choose hook formulas. Get human approval.",
        context=scout_result,
    )

    if "rejected" in plan_result.lower():
        return f"Pipeline stopped: plan was rejected.\n\n{plan_result}"

    create_result = _run(
        "creator",
        "Generate publish-ready content for each post in the daily plan. "
        "Create platform-native formats (LinkedIn text, X thread). "
        "Run quality checks and save content packages.",
        context=plan_result,
    )

    publish_result = _run(
        "publisher",
        "Publish the approved content packages to their designated platforms. "
        "Record post IDs and send confirmation notifications.",
        context=create_result,
    )

    return publish_result


# ── Engager (hourly) ────────────────────────────────────────────────

def run_engager_cycle() -> str:
    """Single engagement cycle: scan feed → comment."""
    return _run(
        "engager",
        "Scan LinkedIn feed for high-value posts to comment on. "
        "Filter by watchlist and topic tags. Generate and post "
        "substantive comments on posts scoring > 7/10. "
        "Also reply to any new comments on your own posts.",
    )


# ── Analyst (daily) ─────────────────────────────────────────────────

def run_analyst() -> str:
    """Collect metrics + generate daily report."""
    return _run(
        "analyst",
        "Collect performance metrics for all posts published today. "
        "Calculate derived metrics (save_rate, engagement_rate). "
        "Generate a daily performance report and send it via notification.",
    )


# ── Strategist (weekly) ────────────────────────────────────────────

def run_strategy_review() -> str:
    """Weekly strategy review — requires human approval."""
    return _run(
        "strategist",
        "Analyze all daily reports from the past week. "
        "Recommend strategy parameter adjustments (keywords, hook weights, "
        "posting times). Present recommendations with data backing "
        "and get human approval before applying changes.",
    )

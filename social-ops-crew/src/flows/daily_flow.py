"""Daily flow — orchestrates the full day's operations.

Replaces CrewAI Flow with plain Python: run pipelines in sequence,
check day-of-week for weekly review.
"""

from __future__ import annotations

from datetime import datetime

from src.flows.crews import (
    run_analyst,
    run_content_pipeline,
    run_engager_cycle,
    run_strategy_review,
)


def run_daily_ops() -> str:
    """Full daily operations: content → engage → analyze (→ strategy on Sunday)."""
    date_str = datetime.now().strftime("%Y-%m-%d")

    print(f"\n{'#' * 60}")
    print(f"  Daily Operations — {date_str}")
    print(f"{'#' * 60}\n")

    # 1. Content pipeline
    content_result = run_content_pipeline()
    print(f"\n[Content] Done.\n")

    # 2. Engagement cycle
    engage_result = run_engager_cycle()
    print(f"\n[Engager] Done.\n")

    # 3. Analytics
    analyst_result = run_analyst()
    print(f"\n[Analyst] Done.\n")

    # 4. Weekly strategy review (Sunday only)
    strategy_result = ""
    if datetime.now().weekday() == 6:
        strategy_result = run_strategy_review()
        print(f"\n[Strategy] Done.\n")

    print(f"\n{'#' * 60}")
    print(f"  Daily Ops Complete — {date_str}")
    print(f"{'#' * 60}\n")

    return (
        f"Content: {content_result[:200]}...\n"
        f"Engager: {engage_result[:200]}...\n"
        f"Analyst: {analyst_result[:200]}...\n"
        + (f"Strategy: {strategy_result[:200]}...\n" if strategy_result else "")
    )

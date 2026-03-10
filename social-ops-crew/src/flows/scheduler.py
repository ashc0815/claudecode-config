"""Scheduler — runs the daily flow and hourly engager on schedule.

Uses the `schedule` library for simplicity. For production, consider:
- APScheduler for more robust scheduling
- Celery + Redis for distributed task queue
- GitHub Actions scheduled workflows for serverless
"""

from __future__ import annotations

import time
from datetime import datetime

import schedule

from src.flows.daily_flow import DailyOpsFlow, EngagerOnlyFlow


def run_daily_pipeline() -> None:
    """Run the full daily content pipeline."""
    print(f"[{datetime.now()}] Starting daily content pipeline...")
    flow = DailyOpsFlow()
    flow.kickoff()


def run_engager() -> None:
    """Run a single engager cycle."""
    now = datetime.now()
    # Only run during work hours (07:00-22:00 EST ≈ 12:00-03:00 UTC)
    hour_est = (now.hour - 5) % 24  # Rough EST conversion
    if 7 <= hour_est <= 22:
        print(f"[{now}] Starting engager cycle...")
        flow = EngagerOnlyFlow()
        flow.kickoff()
    else:
        print(f"[{now}] Outside engagement hours, skipping.")


def run_scheduler() -> None:
    """Start the scheduler loop.

    Schedule:
      - Daily pipeline at 06:00 UTC
      - Engager every hour
    """
    schedule.every().day.at("06:00").do(run_daily_pipeline)
    schedule.every().hour.do(run_engager)

    print("Scheduler started. Press Ctrl+C to stop.")
    print(f"  Daily pipeline: 06:00 UTC")
    print(f"  Engager: every hour (07:00-22:00 EST)")
    print()

    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    run_scheduler()

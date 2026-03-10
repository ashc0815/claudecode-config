"""Scheduler — runs daily flow and hourly engager on schedule."""

from __future__ import annotations

import time
from datetime import datetime

import schedule

from src.flows.crews import run_analyst, run_content_pipeline, run_engager_cycle


def _run_daily() -> None:
    print(f"[{datetime.now()}] Starting daily content pipeline...")
    try:
        run_content_pipeline()
    except Exception as e:
        print(f"[ERROR] Daily pipeline failed: {e}")


def _run_engager() -> None:
    now = datetime.now()
    hour_est = (now.hour - 5) % 24
    if 7 <= hour_est <= 22:
        print(f"[{now}] Starting engager cycle...")
        try:
            run_engager_cycle()
        except Exception as e:
            print(f"[ERROR] Engager cycle failed: {e}")
    else:
        print(f"[{now}] Outside engagement hours, skipping.")


def _run_analyst() -> None:
    print(f"[{datetime.now()}] Starting analytics collection...")
    try:
        run_analyst()
    except Exception as e:
        print(f"[ERROR] Analyst failed: {e}")


def run_scheduler() -> None:
    """Start the scheduler loop."""
    schedule.every().day.at("06:00").do(_run_daily)
    schedule.every().hour.do(_run_engager)
    schedule.every().day.at("16:00").do(_run_analyst)

    print("Scheduler started. Press Ctrl+C to stop.")
    print("  Daily pipeline: 06:00 UTC")
    print("  Engager: every hour (07:00-22:00 EST)")
    print("  Analyst: 16:00 UTC")
    print()

    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    run_scheduler()

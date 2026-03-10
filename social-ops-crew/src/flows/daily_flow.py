"""Daily Flow — orchestrates the full day's operations.

Schedule:
  06:00 UTC  Content Crew (scout → plan → create → publish)
  10:00-22:00 EST  Engager Crew (every hour)
  16:00 UTC  Analyst Crew (2h snapshot)
  Next day   Analyst Crew (24h + 48h snapshots)

This module uses CrewAI Flows for state management between crews.
"""

from __future__ import annotations

from datetime import datetime

from crewai.flow.flow import Flow, listen, router, start
from pydantic import BaseModel

from src.flows.crews import analyst_crew, content_crew, engager_crew, strategy_crew


class DailyState(BaseModel):
    """State passed between flow steps."""

    date: str = ""
    scout_result: str = ""
    plan_result: str = ""
    content_result: str = ""
    publish_result: str = ""
    engager_result: str = ""
    analyst_result: str = ""
    error: str = ""


class DailyOpsFlow(Flow[DailyState]):
    """Main daily operations flow.

    Usage:
        flow = DailyOpsFlow()
        flow.kickoff()
    """

    @start()
    def run_content_pipeline(self) -> str:
        """Morning: run the full content pipeline."""
        self.state.date = datetime.now().strftime("%Y-%m-%d")
        print(f"\n{'='*60}")
        print(f"  Daily Content Pipeline — {self.state.date}")
        print(f"{'='*60}\n")

        crew = content_crew()
        result = crew.kickoff()
        self.state.content_result = str(result)
        return str(result)

    @listen(run_content_pipeline)
    def run_engager(self) -> str:
        """After content is published, start engagement cycle."""
        print(f"\n{'='*60}")
        print(f"  Engager Cycle — {self.state.date}")
        print(f"{'='*60}\n")

        crew = engager_crew()
        result = crew.kickoff()
        self.state.engager_result = str(result)
        return str(result)

    @listen(run_engager)
    def run_analyst(self) -> str:
        """After engagement, collect early metrics."""
        print(f"\n{'='*60}")
        print(f"  Analytics Collection — {self.state.date}")
        print(f"{'='*60}\n")

        crew = analyst_crew()
        result = crew.kickoff()
        self.state.analyst_result = str(result)
        return str(result)

    @router(run_analyst)
    def check_weekly_review(self) -> str:
        """On Sundays, trigger weekly strategy review."""
        if datetime.now().weekday() == 6:  # Sunday
            return "weekly_review"
        return "done"

    @listen("weekly_review")
    def run_strategy_review(self) -> str:
        """Weekly strategy review — Sunday only."""
        print(f"\n{'='*60}")
        print(f"  Weekly Strategy Review — {self.state.date}")
        print(f"{'='*60}\n")

        crew = strategy_crew()
        result = crew.kickoff()
        return str(result)

    @listen("done")
    def finish(self) -> str:
        """Daily operations complete."""
        print(f"\n{'='*60}")
        print(f"  Daily Ops Complete — {self.state.date}")
        print(f"{'='*60}\n")
        return "Daily operations completed successfully."


class EngagerOnlyFlow(Flow[DailyState]):
    """Standalone engager flow — run hourly via scheduler."""

    @start()
    def engage(self) -> str:
        crew = engager_crew()
        result = crew.kickoff()
        return str(result)

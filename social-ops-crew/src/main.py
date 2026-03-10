"""Social Ops Crew — Entry point.

Usage:
  python -m src.main daily       # Full daily pipeline (scout → plan → create → publish → engage → analyze)
  python -m src.main engage      # Single engager cycle (scan LinkedIn feed → comment)
  python -m src.main analyze     # Collect metrics + generate daily report
  python -m src.main strategy    # Weekly strategy review (human approval required)
  python -m src.main scout       # Test news discovery only
  python -m src.main schedule    # Start continuous scheduler (daily + hourly)
"""

from __future__ import annotations

import sys

from dotenv import load_dotenv

load_dotenv()


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]

    if command == "daily":
        from src.flows.daily_flow import DailyOpsFlow

        flow = DailyOpsFlow()
        result = flow.kickoff()
        print(f"\nResult:\n{result}")

    elif command == "engage":
        from src.flows.daily_flow import EngagerOnlyFlow

        flow = EngagerOnlyFlow()
        result = flow.kickoff()
        print(f"\nResult:\n{result}")

    elif command == "analyze":
        from src.flows.crews import AnalystCrew

        result = AnalystCrew().crew().kickoff()
        print(f"\nResult:\n{result}")

    elif command == "strategy":
        from src.flows.crews import StrategyCrew

        result = StrategyCrew().crew().kickoff()
        print(f"\nResult:\n{result}")

    elif command == "scout":
        from crewai import Crew, Process

        from src.flows.crews import ContentCrew

        # Run only the scout agent with its task
        content = ContentCrew()
        scout_crew = Crew(
            agents=[content.scout()],
            tasks=[content.scan_news()],
            process=Process.sequential,
            verbose=True,
        )
        result = scout_crew.kickoff()
        print(f"\nResult:\n{result}")

    elif command == "schedule":
        from src.flows.scheduler import run_scheduler

        run_scheduler()

    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()

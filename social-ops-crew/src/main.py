"""Social Ops Crew — Entry point.

Usage:
  # Run full daily pipeline (interactive)
  python -m src.main daily

  # Run engager only (single cycle)
  python -m src.main engage

  # Run analyst only (collect + report)
  python -m src.main analyze

  # Run weekly strategy review
  python -m src.main strategy

  # Start scheduler (continuous operation)
  python -m src.main schedule

  # Run scout only (test news discovery)
  python -m src.main scout
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
        from src.flows.crews import analyst_crew

        crew = analyst_crew()
        result = crew.kickoff()
        print(f"\nResult:\n{result}")

    elif command == "strategy":
        from src.flows.crews import strategy_crew

        crew = strategy_crew()
        result = crew.kickoff()
        print(f"\nResult:\n{result}")

    elif command == "scout":
        from src.flows.crews import content_crew

        # Run only scout task by creating a minimal crew
        from src.agents.definitions import create_agents
        from src.tasks.definitions import create_tasks

        agents = create_agents()
        tasks = create_tasks(agents)
        from crewai import Crew, Process

        scout_only = Crew(
            agents=[agents["scout"]],
            tasks=[tasks["scan_news"]],
            process=Process.sequential,
            verbose=True,
        )
        result = scout_only.kickoff()
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

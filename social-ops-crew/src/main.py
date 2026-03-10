"""Social Ops — Entry point.

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
        from src.flows.daily_flow import run_daily_ops

        result = run_daily_ops()
        print(f"\nResult:\n{result}")

    elif command == "engage":
        from src.flows.crews import run_engager_cycle

        result = run_engager_cycle()
        print(f"\nResult:\n{result}")

    elif command == "analyze":
        from src.flows.crews import run_analyst

        result = run_analyst()
        print(f"\nResult:\n{result}")

    elif command == "strategy":
        from src.flows.crews import run_strategy_review

        result = run_strategy_review()
        print(f"\nResult:\n{result}")

    elif command == "scout":
        from src.agents.definitions import get_agents
        from src.runner import run_agent

        agent = get_agents()["scout"]
        result = run_agent(
            system_prompt=agent["system_prompt"],
            user_message=(
                "Scan industry news for the past 12 hours. "
                "Find top 10-15 candidates in AI, fintech, and future-of-work."
            ),
            tools=agent["tools"],
            temperature=agent["temperature"],
        )
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

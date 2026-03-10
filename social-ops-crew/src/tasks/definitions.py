"""Task definitions — maps YAML config to CrewAI Task instances."""

from __future__ import annotations

from crewai import Agent, Task

from src.config import load_tasks_config


def create_tasks(agents: dict[str, Agent]) -> dict[str, Task]:
    """Create all tasks from YAML config, linking to agent instances."""
    cfg = load_tasks_config()

    scan_news = Task(
        description=cfg["scan_news"]["description"],
        expected_output=cfg["scan_news"]["expected_output"],
        agent=agents["scout"],
    )

    plan_daily = Task(
        description=cfg["plan_daily_content"]["description"],
        expected_output=cfg["plan_daily_content"]["expected_output"],
        agent=agents["planner"],
        context=[scan_news],
    )

    create_content = Task(
        description=cfg["create_content"]["description"],
        expected_output=cfg["create_content"]["expected_output"],
        agent=agents["creator"],
        context=[plan_daily],
        human_input=True,  # Final content review before publishing
    )

    publish_content = Task(
        description=cfg["publish_content"]["description"],
        expected_output=cfg["publish_content"]["expected_output"],
        agent=agents["publisher"],
        context=[create_content],
    )

    scan_and_comment = Task(
        description=cfg["scan_and_comment"]["description"],
        expected_output=cfg["scan_and_comment"]["expected_output"],
        agent=agents["engager"],
    )

    collect_metrics = Task(
        description=cfg["collect_metrics"]["description"],
        expected_output=cfg["collect_metrics"]["expected_output"],
        agent=agents["analyst"],
    )

    daily_report = Task(
        description=cfg["generate_daily_report"]["description"],
        expected_output=cfg["generate_daily_report"]["expected_output"],
        agent=agents["analyst"],
        context=[collect_metrics],
    )

    weekly_review = Task(
        description=cfg["weekly_strategy_review"]["description"],
        expected_output=cfg["weekly_strategy_review"]["expected_output"],
        agent=agents["strategist"],
        human_input=True,  # Strategy changes always need human approval
    )

    return {
        "scan_news": scan_news,
        "plan_daily": plan_daily,
        "create_content": create_content,
        "publish_content": publish_content,
        "scan_and_comment": scan_and_comment,
        "collect_metrics": collect_metrics,
        "daily_report": daily_report,
        "weekly_review": weekly_review,
    }

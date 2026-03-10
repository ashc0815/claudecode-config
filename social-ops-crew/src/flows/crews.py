"""Crew definitions — 4 crews for different operational cycles.

Architecture:
  - Content Crew: daily content pipeline (scout → plan → create → publish)
  - Engager Crew: hourly LinkedIn commenting (independent of content)
  - Analyst Crew: data collection + daily report
  - Strategy Crew: weekly strategy review

Why separate crews instead of one big crew:
  1. Different schedules (hourly / daily / weekly)
  2. Independent failure domains (engager failing shouldn't block publishing)
  3. Can run in parallel (engager + content)
"""

from __future__ import annotations

from crewai import Crew, Process

from src.agents.definitions import create_agents
from src.tasks.definitions import create_tasks


def _build() -> tuple[dict, dict]:
    agents = create_agents()
    tasks = create_tasks(agents)
    return agents, tasks


def content_crew() -> Crew:
    """Daily content pipeline: scout → plan → create → publish."""
    agents, tasks = _build()
    return Crew(
        agents=[agents["scout"], agents["planner"], agents["creator"], agents["publisher"]],
        tasks=[
            tasks["scan_news"],
            tasks["plan_daily"],
            tasks["create_content"],
            tasks["publish_content"],
        ],
        process=Process.sequential,  # Each step depends on the previous
        verbose=True,
        memory=True,           # Enable CrewAI memory for cross-session learning
        planning=True,         # Enable planning mode for better task decomposition
        planning_llm="anthropic/claude-sonnet-4-6",
    )


def engager_crew() -> Crew:
    """Hourly LinkedIn engagement: scan feed → generate comments → post."""
    agents, tasks = _build()
    return Crew(
        agents=[agents["engager"]],
        tasks=[tasks["scan_and_comment"]],
        process=Process.sequential,
        verbose=True,
        memory=True,  # Remember what was already commented on
    )


def analyst_crew() -> Crew:
    """Data collection + daily report."""
    agents, tasks = _build()
    return Crew(
        agents=[agents["analyst"]],
        tasks=[
            tasks["collect_metrics"],
            tasks["daily_report"],
        ],
        process=Process.sequential,
        verbose=True,
    )


def strategy_crew() -> Crew:
    """Weekly strategy review — always requires human approval."""
    agents, tasks = _build()
    return Crew(
        agents=[agents["strategist"]],
        tasks=[tasks["weekly_review"]],
        process=Process.sequential,
        verbose=True,
    )

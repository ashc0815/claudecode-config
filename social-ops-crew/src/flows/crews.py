"""Crew definitions using CrewAI 1.10.x @CrewBase pattern.

Architecture: 4 independent crews for different operational cycles.
  - ContentCrew: daily content pipeline (scout → plan → create → publish)
  - EngagerCrew: hourly LinkedIn commenting (independent of content)
  - AnalystCrew: data collection + daily report
  - StrategyCrew: weekly strategy review

Why separate crews instead of one big crew:
  1. Different schedules (hourly / daily / weekly)
  2. Independent failure domains (engager failing shouldn't block publishing)
  3. Can run in parallel (engager + content)
"""

from __future__ import annotations

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import SerperDevTool, WebsiteSearchTool

from src.tools.data_tool import (
    LoadRecentAnalyticsTool,
    LoadScoutPoolTool,
    LoadStrategyConfigTool,
    SaveAnalyticsTool,
    SaveContentPackageTool,
    SaveDailyPlanTool,
    SaveEngagerLogTool,
    SaveScoutPoolTool,
)
from src.tools.linkedin_tool import (
    LinkedInCommentTool,
    LinkedInFeedTool,
    LinkedInMetricsTool,
    LinkedInPublishTool,
)
from src.tools.notification_tool import HumanApprovalTool, TelegramNotifyTool
from src.tools.search_tool import BraveNewsTool, BraveSearchTool
from src.tools.x_tool import XMetricsTool, XPublishThreadTool, XSearchTool

CLAUDE = "anthropic/claude-sonnet-4-6"

# Config paths relative to each @CrewBase class file location
_AGENTS_CONFIG = "../config/agents.yaml"
_TASKS_CONFIG = "../config/tasks.yaml"


# ─── Content Crew (Daily) ────────────────────────────────────────────

@CrewBase
class ContentCrew:
    """Daily content pipeline: scout → plan → create → publish."""

    agents_config = _AGENTS_CONFIG
    tasks_config = _TASKS_CONFIG

    @agent
    def scout(self) -> Agent:
        return Agent(
            config=self.agents_config["scout"],
            llm=CLAUDE,
            tools=[
                BraveSearchTool(),
                BraveNewsTool(),
                XSearchTool(),
                SerperDevTool(),
                SaveScoutPoolTool(),
                LoadStrategyConfigTool(),
            ],
            inject_date=True,
            verbose=True,
        )

    @agent
    def planner(self) -> Agent:
        return Agent(
            config=self.agents_config["planner"],
            llm=CLAUDE,
            tools=[
                LoadScoutPoolTool(),
                LoadStrategyConfigTool(),
                SaveDailyPlanTool(),
                TelegramNotifyTool(),
                HumanApprovalTool(),
            ],
            reasoning=True,
            verbose=True,
        )

    @agent
    def creator(self) -> Agent:
        return Agent(
            config=self.agents_config["creator"],
            llm=CLAUDE,
            tools=[WebsiteSearchTool(), SaveContentPackageTool()],
            verbose=True,
        )

    @agent
    def publisher(self) -> Agent:
        return Agent(
            config=self.agents_config["publisher"],
            llm=CLAUDE,
            tools=[
                LinkedInPublishTool(),
                XPublishThreadTool(),
                TelegramNotifyTool(),
            ],
            verbose=True,
        )

    @task
    def scan_news(self) -> Task:
        return Task(config=self.tasks_config["scan_news"])

    @task
    def plan_daily_content(self) -> Task:
        return Task(
            config=self.tasks_config["plan_daily_content"],
            context=[self.scan_news()],
        )

    @task
    def create_content(self) -> Task:
        return Task(
            config=self.tasks_config["create_content"],
            context=[self.plan_daily_content()],
            human_input=True,  # Final content review before publishing
        )

    @task
    def publish_content(self) -> Task:
        return Task(
            config=self.tasks_config["publish_content"],
            context=[self.create_content()],
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,   # Auto-collected from @agent methods
            tasks=self.tasks,     # Auto-collected from @task methods
            process=Process.sequential,
            verbose=True,
            memory=True,
            planning=True,
            planning_llm=CLAUDE,
        )


# ─── Engager Crew (Hourly) ───────────────────────────────────────────

@CrewBase
class EngagerCrew:
    """Hourly LinkedIn engagement: scan feed → generate comments → post."""

    agents_config = _AGENTS_CONFIG
    tasks_config = _TASKS_CONFIG

    @agent
    def engager(self) -> Agent:
        return Agent(
            config=self.agents_config["engager"],
            llm=CLAUDE,
            tools=[
                LinkedInFeedTool(),
                LinkedInCommentTool(),
                LoadStrategyConfigTool(),
                SaveEngagerLogTool(),
                HumanApprovalTool(),
            ],
            reasoning=True,
            inject_date=True,
            verbose=True,
        )

    @task
    def scan_and_comment(self) -> Task:
        return Task(config=self.tasks_config["scan_and_comment"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            memory=True,  # Remember what was already commented on
        )


# ─── Analyst Crew (Daily) ────────────────────────────────────────────

@CrewBase
class AnalystCrew:
    """Data collection + daily report."""

    agents_config = _AGENTS_CONFIG
    tasks_config = _TASKS_CONFIG

    @agent
    def analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["analyst"],
            llm=CLAUDE,
            tools=[
                LinkedInMetricsTool(),
                XMetricsTool(),
                SaveAnalyticsTool(),
                LoadRecentAnalyticsTool(),
                TelegramNotifyTool(),
            ],
            reasoning=True,
            verbose=True,
        )

    @task
    def collect_metrics(self) -> Task:
        return Task(config=self.tasks_config["collect_metrics"])

    @task
    def generate_daily_report(self) -> Task:
        return Task(
            config=self.tasks_config["generate_daily_report"],
            context=[self.collect_metrics()],
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )


# ─── Strategy Crew (Weekly) ──────────────────────────────────────────

@CrewBase
class StrategyCrew:
    """Weekly strategy review — always requires human approval."""

    agents_config = _AGENTS_CONFIG
    tasks_config = _TASKS_CONFIG

    @agent
    def strategist(self) -> Agent:
        return Agent(
            config=self.agents_config["strategist"],
            llm=CLAUDE,
            tools=[
                LoadRecentAnalyticsTool(),
                LoadStrategyConfigTool(),
                HumanApprovalTool(),
                TelegramNotifyTool(),
            ],
            reasoning=True,
            max_reasoning_attempts=5,
            verbose=True,
        )

    @task
    def weekly_strategy_review(self) -> Task:
        return Task(
            config=self.tasks_config["weekly_strategy_review"],
            human_input=True,  # Strategy changes always need human approval
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )

"""Agent factory — creates Agent instances from YAML config with appropriate tools.

Uses the latest CrewAI 1.10.x API patterns:
- LLM string format: "anthropic/claude-sonnet-4-6"
- reasoning=True for analytical agents
- inject_date=True for time-aware agents
"""

from __future__ import annotations

from crewai import Agent
from crewai_tools import SerperDevTool, WebsiteSearchTool

from src.config import load_agents_config
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

# Claude model strings (CrewAI 1.10.x format: "provider/model-id")
CLAUDE_CREATIVE = "anthropic/claude-sonnet-4-6"   # temp 0.7 for content generation
CLAUDE_ANALYTICAL = "anthropic/claude-sonnet-4-6"  # temp 0.3 for analysis


def create_agents() -> dict[str, Agent]:
    """Create all 7 agents from YAML config with appropriate tools."""
    cfg = load_agents_config()

    scout = Agent(
        role=cfg["scout"]["role"],
        goal=cfg["scout"]["goal"],
        backstory=cfg["scout"]["backstory"],
        llm=CLAUDE_CREATIVE,
        tools=[
            BraveSearchTool(),
            BraveNewsTool(),
            XSearchTool(),
            SerperDevTool(),
            SaveScoutPoolTool(),
            LoadStrategyConfigTool(),
        ],
        inject_date=True,  # Auto-inject current date for timeliness scoring
        verbose=True,
    )

    planner = Agent(
        role=cfg["planner"]["role"],
        goal=cfg["planner"]["goal"],
        backstory=cfg["planner"]["backstory"],
        llm=CLAUDE_ANALYTICAL,
        tools=[
            LoadScoutPoolTool(),
            LoadStrategyConfigTool(),
            SaveDailyPlanTool(),
            TelegramNotifyTool(),
            HumanApprovalTool(),
        ],
        reasoning=True,  # Enable strategic planning for topic selection
        max_reasoning_attempts=3,
        verbose=True,
    )

    creator = Agent(
        role=cfg["creator"]["role"],
        goal=cfg["creator"]["goal"],
        backstory=cfg["creator"]["backstory"],
        llm=CLAUDE_CREATIVE,
        tools=[
            WebsiteSearchTool(),
            SaveContentPackageTool(),
        ],
        verbose=True,
    )

    publisher = Agent(
        role=cfg["publisher"]["role"],
        goal=cfg["publisher"]["goal"],
        backstory=cfg["publisher"]["backstory"],
        llm=CLAUDE_ANALYTICAL,
        tools=[
            LinkedInPublishTool(),
            XPublishThreadTool(),
            TelegramNotifyTool(),
        ],
        verbose=True,
    )

    engager = Agent(
        role=cfg["engager"]["role"],
        goal=cfg["engager"]["goal"],
        backstory=cfg["engager"]["backstory"],
        llm=CLAUDE_CREATIVE,
        tools=[
            LinkedInFeedTool(),
            LinkedInCommentTool(),
            LoadStrategyConfigTool(),
            SaveEngagerLogTool(),
            HumanApprovalTool(),
        ],
        reasoning=True,  # Strategic comment targeting
        inject_date=True,
        verbose=True,
    )

    analyst = Agent(
        role=cfg["analyst"]["role"],
        goal=cfg["analyst"]["goal"],
        backstory=cfg["analyst"]["backstory"],
        llm=CLAUDE_ANALYTICAL,
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

    strategist = Agent(
        role=cfg["strategist"]["role"],
        goal=cfg["strategist"]["goal"],
        backstory=cfg["strategist"]["backstory"],
        llm=CLAUDE_ANALYTICAL,
        tools=[
            LoadRecentAnalyticsTool(),
            LoadStrategyConfigTool(),
            HumanApprovalTool(),
            TelegramNotifyTool(),
        ],
        reasoning=True,
        max_reasoning_attempts=5,  # More reasoning budget for strategy
        verbose=True,
    )

    return {
        "scout": scout,
        "planner": planner,
        "creator": creator,
        "publisher": publisher,
        "engager": engager,
        "analyst": analyst,
        "strategist": strategist,
    }

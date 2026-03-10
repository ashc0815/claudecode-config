"""Agent definitions — maps YAML config to CrewAI Agent instances."""

from __future__ import annotations

from crewai import Agent, LLM
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
from src.tools.x_tool import XMetricsTool, XPublishThreadTool, XSearchTool

# Claude as the backbone LLM
claude_llm = LLM(
    model="anthropic/claude-sonnet-4-6",
    temperature=0.7,
)

claude_analytical = LLM(
    model="anthropic/claude-sonnet-4-6",
    temperature=0.3,  # Lower temp for analytical tasks
)


def create_agents() -> dict[str, Agent]:
    """Create all 7 agents from YAML config with appropriate tools."""
    cfg = load_agents_config()

    scout = Agent(
        role=cfg["scout"]["role"],
        goal=cfg["scout"]["goal"],
        backstory=cfg["scout"]["backstory"],
        tools=[
            SerperDevTool(),         # Web search
            XSearchTool(),           # X/Twitter search
            SaveScoutPoolTool(),     # Persist results
            LoadStrategyConfigTool(),  # Read strategy keywords
        ],
        llm=claude_llm,
        verbose=True,
    )

    planner = Agent(
        role=cfg["planner"]["role"],
        goal=cfg["planner"]["goal"],
        backstory=cfg["planner"]["backstory"],
        tools=[
            LoadScoutPoolTool(),
            LoadStrategyConfigTool(),
            SaveDailyPlanTool(),
            TelegramNotifyTool(),
            HumanApprovalTool(),
        ],
        llm=claude_analytical,
        verbose=True,
    )

    creator = Agent(
        role=cfg["creator"]["role"],
        goal=cfg["creator"]["goal"],
        backstory=cfg["creator"]["backstory"],
        tools=[
            WebsiteSearchTool(),      # Deep research on sources
            SaveContentPackageTool(),
        ],
        llm=claude_llm,
        verbose=True,
    )

    publisher = Agent(
        role=cfg["publisher"]["role"],
        goal=cfg["publisher"]["goal"],
        backstory=cfg["publisher"]["backstory"],
        tools=[
            LinkedInPublishTool(),
            XPublishThreadTool(),
            TelegramNotifyTool(),
        ],
        llm=claude_analytical,
        verbose=True,
    )

    engager = Agent(
        role=cfg["engager"]["role"],
        goal=cfg["engager"]["goal"],
        backstory=cfg["engager"]["backstory"],
        tools=[
            LinkedInFeedTool(),
            LinkedInCommentTool(),
            LoadStrategyConfigTool(),
            SaveEngagerLogTool(),
            HumanApprovalTool(),      # For Tier 1 comments
        ],
        llm=claude_llm,
        verbose=True,
    )

    analyst = Agent(
        role=cfg["analyst"]["role"],
        goal=cfg["analyst"]["goal"],
        backstory=cfg["analyst"]["backstory"],
        tools=[
            LinkedInMetricsTool(),
            XMetricsTool(),
            SaveAnalyticsTool(),
            LoadRecentAnalyticsTool(),
            TelegramNotifyTool(),
        ],
        llm=claude_analytical,
        verbose=True,
    )

    strategist = Agent(
        role=cfg["strategist"]["role"],
        goal=cfg["strategist"]["goal"],
        backstory=cfg["strategist"]["backstory"],
        tools=[
            LoadRecentAnalyticsTool(),
            LoadStrategyConfigTool(),
            HumanApprovalTool(),
            TelegramNotifyTool(),
        ],
        llm=claude_analytical,
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

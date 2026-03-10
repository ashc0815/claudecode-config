"""Data persistence tools for reading/writing YAML data files."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import yaml
from crewai.tools import BaseTool

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


class SaveScoutPoolTool(BaseTool):
    name: str = "save_scout_pool"
    description: str = (
        "Save the scout's candidate stories to a daily YAML file. "
        "Input: 'candidates' (YAML-formatted string of candidate stories)."
    )

    def _run(self, candidates: str) -> str:
        date_str = datetime.now().strftime("%Y-%m-%d")
        path = DATA_DIR / "scout_pool" / f"{date_str}.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(candidates)
        return f"Scout pool saved: {path}"


class LoadScoutPoolTool(BaseTool):
    name: str = "load_scout_pool"
    description: str = "Load today's scout candidate pool. Returns YAML content."

    def _run(self) -> str:
        date_str = datetime.now().strftime("%Y-%m-%d")
        path = DATA_DIR / "scout_pool" / f"{date_str}.yaml"
        if not path.exists():
            return "No scout pool found for today."
        return path.read_text()


class SaveDailyPlanTool(BaseTool):
    name: str = "save_daily_plan"
    description: str = "Save the daily content plan. Input: 'plan' (YAML string)."

    def _run(self, plan: str) -> str:
        date_str = datetime.now().strftime("%Y-%m-%d")
        path = DATA_DIR / "daily_plans" / f"{date_str}.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(plan)
        return f"Daily plan saved: {path}"


class SaveContentPackageTool(BaseTool):
    name: str = "save_content_package"
    description: str = (
        "Save a content package for publishing. Input: 'post_id' (string) "
        "and 'content' (YAML string)."
    )

    def _run(self, post_id: str, content: str) -> str:
        path = DATA_DIR / "content_packages" / f"{post_id}.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return f"Content package saved: {path}"


class SaveAnalyticsTool(BaseTool):
    name: str = "save_analytics"
    description: str = (
        "Save analytics data for a post. Input: 'post_id' and 'metrics' (YAML string)."
    )

    def _run(self, post_id: str, metrics: str) -> str:
        path = DATA_DIR / "analytics" / f"{post_id}.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)

        # Merge with existing data if present
        existing = {}
        if path.exists():
            existing = yaml.safe_load(path.read_text()) or {}

        new_data = yaml.safe_load(metrics) or {}
        existing.update(new_data)

        path.write_text(yaml.dump(existing, default_flow_style=False))
        return f"Analytics saved: {path}"


class SaveEngagerLogTool(BaseTool):
    name: str = "save_engager_log"
    description: str = (
        "Log engager comment activity. Input: 'log_entry' (YAML string with "
        "comment details)."
    )

    def _run(self, log_entry: str) -> str:
        date_str = datetime.now().strftime("%Y-%m-%d")
        path = DATA_DIR / "engager" / f"comments-{date_str}.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)

        existing = []
        if path.exists():
            existing = yaml.safe_load(path.read_text()) or []

        new_entry = yaml.safe_load(log_entry)
        if isinstance(new_entry, list):
            existing.extend(new_entry)
        else:
            existing.append(new_entry)

        path.write_text(yaml.dump(existing, default_flow_style=False))
        return f"Engager log updated: {path}"


class LoadStrategyConfigTool(BaseTool):
    name: str = "load_strategy_config"
    description: str = "Load the current strategy configuration. Returns YAML content."

    def _run(self) -> str:
        path = Path(__file__).resolve().parent.parent / "config" / "strategy.yaml"
        return path.read_text()


class LoadRecentAnalyticsTool(BaseTool):
    name: str = "load_recent_analytics"
    description: str = (
        "Load analytics data for the past N days. Input: 'days' (int, default 7)."
    )

    def _run(self, days: int = 7) -> str:
        analytics_dir = DATA_DIR / "analytics"
        if not analytics_dir.exists():
            return "No analytics data found."

        files = sorted(analytics_dir.glob("*.yaml"))[-days * 3 :]  # ~3 posts/day max
        results = []
        for f in files:
            data = yaml.safe_load(f.read_text())
            if data:
                results.append({"file": f.name, **data})
        return yaml.dump(results, default_flow_style=False)

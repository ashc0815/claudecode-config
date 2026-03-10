"""Data persistence tools — read/write YAML data files."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import yaml

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


# ── Handlers ────────────────────────────────────────────────────────

def save_scout_pool(candidates: str) -> str:
    date_str = datetime.now().strftime("%Y-%m-%d")
    path = DATA_DIR / "scout_pool" / f"{date_str}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(candidates)
    return f"Scout pool saved: {path}"


def load_scout_pool() -> str:
    date_str = datetime.now().strftime("%Y-%m-%d")
    path = DATA_DIR / "scout_pool" / f"{date_str}.yaml"
    if not path.exists():
        return "No scout pool found for today."
    return path.read_text()


def save_daily_plan(plan: str) -> str:
    date_str = datetime.now().strftime("%Y-%m-%d")
    path = DATA_DIR / "daily_plans" / f"{date_str}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(plan)
    return f"Daily plan saved: {path}"


def save_content_package(post_id: str, content: str) -> str:
    path = DATA_DIR / "content_packages" / f"{post_id}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return f"Content package saved: {path}"


def save_analytics(post_id: str, metrics: str) -> str:
    path = DATA_DIR / "analytics" / f"{post_id}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)

    existing = {}
    if path.exists():
        existing = yaml.safe_load(path.read_text()) or {}

    new_data = yaml.safe_load(metrics) or {}
    existing.update(new_data)

    path.write_text(yaml.dump(existing, default_flow_style=False))
    return f"Analytics saved: {path}"


def save_engager_log(log_entry: str) -> str:
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


def load_strategy_config() -> str:
    path = Path(__file__).resolve().parent.parent / "config" / "strategy.yaml"
    return path.read_text()


def load_recent_analytics(days: int = 7) -> str:
    analytics_dir = DATA_DIR / "analytics"
    if not analytics_dir.exists():
        return "No analytics data found."

    files = sorted(analytics_dir.glob("*.yaml"))[-days * 3 :]
    results = []
    for f in files:
        data = yaml.safe_load(f.read_text())
        if data:
            results.append({"file": f.name, **data})
    return yaml.dump(results, default_flow_style=False)


# ── Schemas ─────────────────────────────────────────────────────────

SAVE_SCOUT_POOL_SCHEMA = {
    "name": "save_scout_pool",
    "description": "Save scout candidate stories to today's YAML file.",
    "input_schema": {
        "type": "object",
        "properties": {
            "candidates": {
                "type": "string",
                "description": "YAML-formatted string of candidate stories",
            },
        },
        "required": ["candidates"],
    },
}

LOAD_SCOUT_POOL_SCHEMA = {
    "name": "load_scout_pool",
    "description": "Load today's scout candidate pool. Returns YAML content.",
    "input_schema": {"type": "object", "properties": {}},
}

SAVE_DAILY_PLAN_SCHEMA = {
    "name": "save_daily_plan",
    "description": "Save the daily content plan.",
    "input_schema": {
        "type": "object",
        "properties": {
            "plan": {"type": "string", "description": "YAML-formatted daily plan"},
        },
        "required": ["plan"],
    },
}

SAVE_CONTENT_PACKAGE_SCHEMA = {
    "name": "save_content_package",
    "description": "Save a content package for publishing.",
    "input_schema": {
        "type": "object",
        "properties": {
            "post_id": {"type": "string", "description": "Post identifier"},
            "content": {"type": "string", "description": "YAML-formatted content package"},
        },
        "required": ["post_id", "content"],
    },
}

SAVE_ANALYTICS_SCHEMA = {
    "name": "save_analytics",
    "description": "Save analytics data for a post (merges with existing).",
    "input_schema": {
        "type": "object",
        "properties": {
            "post_id": {"type": "string"},
            "metrics": {"type": "string", "description": "YAML metrics data"},
        },
        "required": ["post_id", "metrics"],
    },
}

SAVE_ENGAGER_LOG_SCHEMA = {
    "name": "save_engager_log",
    "description": "Log engager comment activity.",
    "input_schema": {
        "type": "object",
        "properties": {
            "log_entry": {"type": "string", "description": "YAML log entry"},
        },
        "required": ["log_entry"],
    },
}

LOAD_STRATEGY_CONFIG_SCHEMA = {
    "name": "load_strategy_config",
    "description": "Load the current strategy configuration. Returns YAML.",
    "input_schema": {"type": "object", "properties": {}},
}

LOAD_RECENT_ANALYTICS_SCHEMA = {
    "name": "load_recent_analytics",
    "description": "Load analytics data for the past N days.",
    "input_schema": {
        "type": "object",
        "properties": {
            "days": {
                "type": "integer",
                "description": "Number of days to look back",
                "default": 7,
            },
        },
    },
}

# ── Registry ────────────────────────────────────────────────────────

DATA_TOOLS = {
    "save_scout_pool": (SAVE_SCOUT_POOL_SCHEMA, save_scout_pool),
    "load_scout_pool": (LOAD_SCOUT_POOL_SCHEMA, load_scout_pool),
    "save_daily_plan": (SAVE_DAILY_PLAN_SCHEMA, save_daily_plan),
    "save_content_package": (SAVE_CONTENT_PACKAGE_SCHEMA, save_content_package),
    "save_analytics": (SAVE_ANALYTICS_SCHEMA, save_analytics),
    "save_engager_log": (SAVE_ENGAGER_LOG_SCHEMA, save_engager_log),
    "load_strategy_config": (LOAD_STRATEGY_CONFIG_SCHEMA, load_strategy_config),
    "load_recent_analytics": (LOAD_RECENT_ANALYTICS_SCHEMA, load_recent_analytics),
}

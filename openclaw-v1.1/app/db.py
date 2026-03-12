"""Database helper — thin wrapper around Supabase client."""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from supabase import Client, create_client

from .config import settings

logger = logging.getLogger(__name__)

_client: Optional[Client] = None


def get_client() -> Client:
    global _client
    if _client is None:
        _client = create_client(settings.supabase_url, settings.supabase_service_key)
    return _client


# ── Audit Results ──


def insert_audit_result(data: dict) -> dict:
    return get_client().table("audit_results").insert(data).execute().data[0]


def get_audit_result(audit_id: str) -> Optional[dict]:
    resp = (
        get_client()
        .table("audit_results")
        .select("*")
        .eq("audit_id", audit_id)
        .execute()
    )
    return resp.data[0] if resp.data else None


def update_audit_status(audit_id: str, status: str) -> None:
    get_client().table("audit_results").update(
        {"status": status, "resolved_at": datetime.now(timezone.utc).isoformat()}
    ).eq("audit_id", audit_id).execute()


def get_results_by_status(status: str, limit: int = 50) -> list[dict]:
    return (
        get_client()
        .table("audit_results")
        .select("*")
        .eq("status", status)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
        .data
    )


# ── Feedback ──


def insert_feedback(data: dict) -> dict:
    return get_client().table("feedback").insert(data).execute().data[0]


def get_unconsumed_feedback() -> list[dict]:
    return (
        get_client()
        .table("feedback")
        .select("*, audit_results(risk_flags, prompt_version)")
        .eq("used_for_learning", False)
        .in_("action", ["confirmed", "false_positive"])
        .execute()
        .data
    )


def mark_feedback_consumed(feedback_ids: list[str], batch_id: str) -> None:
    get_client().table("feedback").update(
        {"used_for_learning": True, "learning_batch_id": batch_id}
    ).in_("id", feedback_ids).execute()


# ── Audit Log ──


def append_audit_log(
    event_type: str, actor: str, audit_id: Optional[str] = None, details: dict = None
) -> None:
    get_client().table("audit_log").insert(
        {
            "event_type": event_type,
            "actor": actor,
            "audit_id": audit_id,
            "details": details or {},
        }
    ).execute()


# ── Rule Params ──


def get_active_rule_params(rule_name: str) -> list[dict]:
    return (
        get_client()
        .table("rule_params")
        .select("*")
        .eq("rule_name", rule_name)
        .is_("effective_until", "null")
        .execute()
        .data
    )


def upsert_rule_param(
    rule_name: str,
    param_name: str,
    param_value: Any,
    source: str = "auto_tuned",
    previous_value: Any = None,
    reason: str = "",
) -> dict:
    # Expire the old version
    old = (
        get_client()
        .table("rule_params")
        .select("version")
        .eq("rule_name", rule_name)
        .eq("param_name", param_name)
        .is_("effective_until", "null")
        .execute()
        .data
    )
    new_version = 1
    if old:
        new_version = old[0]["version"] + 1
        get_client().table("rule_params").update(
            {"effective_until": datetime.now(timezone.utc).isoformat()}
        ).eq("rule_name", rule_name).eq("param_name", param_name).is_(
            "effective_until", "null"
        ).execute()

    return (
        get_client()
        .table("rule_params")
        .insert(
            {
                "rule_name": rule_name,
                "param_name": param_name,
                "param_value": json.dumps(param_value) if not isinstance(param_value, str) else param_value,
                "source": source,
                "previous_value": json.dumps(previous_value) if previous_value is not None else None,
                "adjustment_reason": reason,
                "version": new_version,
            }
        )
        .execute()
        .data[0]
    )


# ── Prompt Versions ──


def get_active_prompts() -> list[dict]:
    return (
        get_client()
        .table("prompt_versions")
        .select("*")
        .in_("status", ["active", "testing"])
        .order("created_at", desc=True)
        .execute()
        .data
    )


def increment_prompt_stats(version_tag: str, action: str) -> None:
    """Increment confirmed_count or false_positive_count for a prompt version."""
    prompt = (
        get_client()
        .table("prompt_versions")
        .select("total_uses, confirmed_count, false_positive_count")
        .eq("version_tag", version_tag)
        .execute()
        .data
    )
    if not prompt:
        return
    p = prompt[0]
    updates = {"total_uses": p["total_uses"] + 1}
    if action == "confirmed":
        updates["confirmed_count"] = p["confirmed_count"] + 1
    elif action == "false_positive":
        updates["false_positive_count"] = p["false_positive_count"] + 1

    total_fb = updates.get("confirmed_count", p["confirmed_count"]) + updates.get(
        "false_positive_count", p["false_positive_count"]
    )
    if total_fb > 0:
        updates["precision"] = updates.get("confirmed_count", p["confirmed_count"]) / total_fb

    get_client().table("prompt_versions").update(updates).eq(
        "version_tag", version_tag
    ).execute()


# ── Weekly Metrics ──


def insert_weekly_metrics(data: dict) -> dict:
    return get_client().table("weekly_metrics").insert(data).execute().data[0]


def get_recent_weekly_metrics(weeks: int = 4) -> list[dict]:
    return (
        get_client()
        .table("weekly_metrics")
        .select("*")
        .order("week_start", desc=True)
        .limit(weeks)
        .execute()
        .data
    )


# ── Aggregate Queries ──


def get_rule_feedback_stats(since_days: int = 7) -> dict[str, dict]:
    """Get per-rule feedback stats for the learning cycle."""
    feedbacks = (
        get_client()
        .table("feedback")
        .select("action, per_flag_feedback, free_text_note, audit_results(risk_flags)")
        .eq("used_for_learning", False)
        .in_("action", ["confirmed", "false_positive"])
        .execute()
        .data
    )

    rule_stats: dict[str, dict] = {}
    for fb in feedbacks:
        # Use per_flag_feedback if available
        if fb.get("per_flag_feedback"):
            for flag in fb["per_flag_feedback"]:
                rule = flag["rule"]
                if rule not in rule_stats:
                    rule_stats[rule] = {"agree": 0, "disagree": 0, "reasons": []}
                if flag["agree"]:
                    rule_stats[rule]["agree"] += 1
                else:
                    rule_stats[rule]["disagree"] += 1
                    if flag.get("note"):
                        rule_stats[rule]["reasons"].append(flag["note"])
        else:
            # Fallback: use overall action for all flags in the audit result
            risk_flags = (fb.get("audit_results") or {}).get("risk_flags", [])
            for flag in risk_flags:
                rule = flag.get("rule", "unknown")
                if rule not in rule_stats:
                    rule_stats[rule] = {"agree": 0, "disagree": 0, "reasons": []}
                if fb["action"] == "confirmed":
                    rule_stats[rule]["agree"] += 1
                else:
                    rule_stats[rule]["disagree"] += 1
                    if fb.get("free_text_note"):
                        rule_stats[rule]["reasons"].append(fb["free_text_note"])

    return rule_stats


def get_weekly_audit_counts(week_start: str) -> dict:
    """Get audit counts for a specific week."""
    results = (
        get_client()
        .table("audit_results")
        .select("risk_level")
        .gte("created_at", week_start)
        .execute()
        .data
    )
    counts = {"total": len(results), "pass": 0, "warn": 0, "fail": 0}
    for r in results:
        level = r["risk_level"]
        if level in counts:
            counts[level] += 1
    return counts

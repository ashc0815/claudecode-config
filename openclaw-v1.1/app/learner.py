"""Learning cycle — weekly auto-tuning of rules and prompt iteration.

This is the brain of V1.1 HITL: it consumes user feedback, analyzes
per-rule precision, and proposes weight adjustments. All changes require
admin approval via Feishu before taking effect (Human-in-the-Loop).
"""

import json
import logging
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

from . import db
from .config import settings
from .models import PendingAdjustment, WeeklyReportData, RulePerformance
from .notify import send_weekly_report, send_adjustment_proposal

logger = logging.getLogger(__name__)

# In-memory store for pending adjustments (in production, use a DB table)
_pending_adjustments: dict[str, dict] = {}


async def run_weekly_learning_cycle() -> dict:
    """Execute the weekly learning cycle.

    Called by a cron job or manual trigger every Sunday night.

    Steps:
        1. Collect unconsumed feedback
        2. Aggregate per-rule precision
        3. Generate adjustment proposals
        4. Send proposals to admin via Feishu
        5. Write weekly metrics snapshot
        6. Mark feedback as consumed

    Returns summary of the cycle.
    """
    batch_id = f"batch-{date.today().isoformat()}-{uuid.uuid4().hex[:6]}"
    logger.info("Starting weekly learning cycle: %s", batch_id)

    # Step 1: Collect feedback
    feedbacks = db.get_unconsumed_feedback()
    if len(feedbacks) < settings.learning_min_feedback_count:
        msg = f"Insufficient feedback ({len(feedbacks)}/{settings.learning_min_feedback_count}), skipping cycle"
        logger.info(msg)
        return {"status": "skipped", "reason": msg}

    # Step 2: Aggregate per-rule stats
    rule_stats = _aggregate_rule_stats(feedbacks)

    # Step 3: Generate adjustment proposals
    adjustments = _generate_adjustments(rule_stats)

    # Step 4: Send to admin for approval
    if adjustments:
        # Store pending adjustments
        for adj in adjustments:
            adj_id = f"adj-{uuid.uuid4().hex[:8]}"
            adj["adjustment_id"] = adj_id
            _pending_adjustments[adj_id] = adj

        await send_adjustment_proposal(adjustments)

    # Step 5: Write weekly metrics
    week_start = _get_week_start()
    metrics = _compute_weekly_metrics(feedbacks, rule_stats, week_start)
    db.insert_weekly_metrics(metrics)

    # Step 6: Send weekly report
    report_data = _build_report_data(metrics, rule_stats, adjustments)
    await send_weekly_report(report_data)

    # Step 7: Mark feedback consumed
    feedback_ids = [f["id"] for f in feedbacks]
    db.mark_feedback_consumed(feedback_ids, batch_id)

    # Audit log
    db.append_audit_log(
        event_type="learning_cycle",
        actor="learner_v1.1",
        details={
            "batch_id": batch_id,
            "feedback_count": len(feedbacks),
            "rules_analyzed": len(rule_stats),
            "adjustments_proposed": len(adjustments),
        },
    )

    return {
        "status": "completed",
        "batch_id": batch_id,
        "feedback_processed": len(feedbacks),
        "adjustments_proposed": len(adjustments),
        "metrics": metrics,
    }


def _aggregate_rule_stats(feedbacks: list[dict]) -> dict[str, dict]:
    """Aggregate feedback into per-rule precision stats."""
    rule_stats: dict[str, dict] = {}

    for fb in feedbacks:
        per_flag = fb.get("per_flag_feedback")
        if per_flag:
            for flag in per_flag:
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
            # Fallback: apply action to all flags in the audit
            audit_data = fb.get("audit_results", {})
            risk_flags = audit_data.get("risk_flags", []) if audit_data else []
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


def _generate_adjustments(rule_stats: dict[str, dict]) -> list[dict]:
    """Generate rule adjustment proposals based on precision analysis."""
    from .rules import RULES

    adjustments = []
    adjustment_count = 0

    for rule, stats in sorted(rule_stats.items(), key=lambda x: x[1]["agree"] / max(1, x[1]["agree"] + x[1]["disagree"])):
        total = stats["agree"] + stats["disagree"]
        if total < 5:
            continue  # Insufficient data

        precision = stats["agree"] / total

        if adjustment_count >= settings.max_weekly_rule_adjustments:
            break

        rule_def = RULES.get(rule, {})
        defaults = rule_def.get("defaults", {})
        min_weight = defaults.get("min_weight", 0.2)

        if precision < 0.4:
            # Low precision: reduce weight significantly
            new_weight = max(0.5, min_weight)
            adjustments.append({
                "rule": rule,
                "action": "reduce_weight",
                "current_weight": defaults.get("weight", 1.0),
                "new_weight": new_weight,
                "precision": round(precision, 2),
                "sample_size": total,
                "reason": f"精准率 {precision:.0%}（{stats['agree']}/{total}），建议降权至 {new_weight}",
                "user_reasons": stats["reasons"][:3],
            })
            adjustment_count += 1

        elif precision < 0.6:
            # Moderate precision: fine-tune
            new_weight = max(0.7, min_weight)
            adjustments.append({
                "rule": rule,
                "action": "fine_tune",
                "current_weight": defaults.get("weight", 1.0),
                "new_weight": new_weight,
                "precision": round(precision, 2),
                "sample_size": total,
                "reason": f"精准率 {precision:.0%}，建议微调权重至 {new_weight}",
                "user_reasons": stats["reasons"][:3],
            })
            adjustment_count += 1

    return adjustments


async def approve_adjustment(adjustment_id: str, approved: bool, admin_note: str = "") -> dict:
    """Process admin approval/rejection of a rule adjustment.

    This is the HITL gate: no rule changes without human approval.
    """
    adj = _pending_adjustments.get(adjustment_id)
    if not adj:
        raise ValueError(f"Adjustment {adjustment_id} not found or already processed")

    if approved:
        # Apply the adjustment
        db.upsert_rule_param(
            rule_name=adj["rule"],
            param_name="weight",
            param_value=adj["new_weight"],
            source="auto_tuned",
            previous_value=adj["current_weight"],
            reason=adj["reason"],
        )

        # Audit log
        db.append_audit_log(
            event_type="rule_update",
            actor="admin",
            details={
                "adjustment_id": adjustment_id,
                "rule": adj["rule"],
                "old_weight": adj["current_weight"],
                "new_weight": adj["new_weight"],
                "reason": adj["reason"],
                "admin_note": admin_note,
                "approved": True,
            },
        )
    else:
        db.append_audit_log(
            event_type="rule_update_rejected",
            actor="admin",
            details={
                "adjustment_id": adjustment_id,
                "rule": adj["rule"],
                "proposed_weight": adj["new_weight"],
                "admin_note": admin_note,
                "approved": False,
            },
        )

    # Remove from pending
    del _pending_adjustments[adjustment_id]

    return {
        "status": "applied" if approved else "rejected",
        "rule": adj["rule"],
        "new_weight": adj["new_weight"] if approved else None,
    }


def get_pending_adjustments() -> list[PendingAdjustment]:
    """Get list of pending adjustment proposals."""
    return [
        PendingAdjustment(
            adjustment_id=adj_id,
            rule=adj["rule"],
            proposed_action=f"reduce_weight_to_{adj['new_weight']}",
            reason=adj["reason"],
        )
        for adj_id, adj in _pending_adjustments.items()
    ]


def _get_week_start() -> date:
    """Get the Monday of the current week."""
    today = date.today()
    return today - timedelta(days=today.weekday())


def _compute_weekly_metrics(
    feedbacks: list[dict], rule_stats: dict, week_start: date
) -> dict:
    """Compute weekly metrics for the snapshot table."""
    week_start_str = week_start.isoformat()
    counts = db.get_weekly_audit_counts(week_start_str)

    confirmed = sum(1 for f in feedbacks if f["action"] == "confirmed")
    false_positives = sum(1 for f in feedbacks if f["action"] == "false_positive")
    total_fb = confirmed + false_positives
    precision = confirmed / total_fb if total_fb > 0 else 0

    # Flagged = warn + fail
    flagged = counts.get("warn", 0) + counts.get("fail", 0)
    feedback_rate = len(feedbacks) / flagged if flagged > 0 else 0

    # Average review time
    times = [f.get("time_spent_seconds", 0) for f in feedbacks if f.get("time_spent_seconds")]
    avg_review_time = sum(times) / len(times) if times else 0

    # Rule trigger distribution
    rule_triggers = {}
    fp_by_rule = {}
    for rule, stats in rule_stats.items():
        rule_triggers[rule] = stats["agree"] + stats["disagree"]
        fp_by_rule[rule] = stats["disagree"]

    return {
        "week_start": week_start_str,
        "total_audits": counts["total"],
        "pass_count": counts.get("pass", 0),
        "warn_count": counts.get("warn", 0),
        "fail_count": counts.get("fail", 0),
        "feedback_count": len(feedbacks),
        "confirmed_anomalies": confirmed,
        "false_positives": false_positives,
        "precision": round(precision, 3),
        "feedback_rate": round(feedback_rate, 3),
        "avg_review_time_seconds": round(avg_review_time, 1),
        "rule_trigger_distribution": rule_triggers,
        "false_positive_by_rule": fp_by_rule,
    }


def _build_report_data(
    metrics: dict, rule_stats: dict, adjustments: list[dict]
) -> WeeklyReportData:
    """Build structured report data for Feishu notification."""
    week_start = date.fromisoformat(metrics["week_start"])
    week_end = week_start + timedelta(days=6)

    rule_performances = []
    for rule, stats in sorted(
        rule_stats.items(),
        key=lambda x: x[1]["agree"] / max(1, x[1]["agree"] + x[1]["disagree"]),
        reverse=True,
    ):
        total = stats["agree"] + stats["disagree"]
        if total >= 3:
            rule_performances.append(
                RulePerformance(
                    rule=rule,
                    trigger_count=total,
                    precision=round(stats["agree"] / total, 2),
                )
            )

    pending = [
        PendingAdjustment(
            adjustment_id=adj.get("adjustment_id", ""),
            rule=adj["rule"],
            proposed_action=adj["action"],
            reason=adj["reason"],
        )
        for adj in adjustments
    ]

    total_fb = metrics.get("confirmed_anomalies", 0) + metrics.get("false_positives", 0)
    fp_rate = metrics.get("false_positives", 0) / total_fb if total_fb > 0 else 0

    return WeeklyReportData(
        week_start=week_start,
        week_end=week_end,
        total_audits=metrics.get("total_audits", 0),
        pass_count=metrics.get("pass_count", 0),
        warn_count=metrics.get("warn_count", 0),
        fail_count=metrics.get("fail_count", 0),
        precision=metrics.get("precision", 0),
        false_positive_rate=round(fp_rate, 3),
        feedback_rate=metrics.get("feedback_rate", 0),
        confirmed_anomalies=metrics.get("confirmed_anomalies", 0),
        rule_performances=rule_performances,
        adjustments=pending,
    )

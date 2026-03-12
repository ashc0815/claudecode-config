"""Feedback module — collect and process HITL feedback from Feishu interactions."""

import logging
from typing import Optional

from . import db
from .models import FeedbackRequest, FeedbackResponse, RuleImpact

logger = logging.getLogger(__name__)


async def record_feedback(req: FeedbackRequest) -> FeedbackResponse:
    """Record user feedback and return rule impact preview.

    This is the core HITL collection point: every time a finance user
    clicks [Confirm], [False Positive], or [Investigate] in Feishu,
    this function captures their judgment as structured training data.
    """
    # Verify audit exists
    audit = db.get_audit_result(req.audit_id)
    if not audit:
        raise ValueError(f"Audit {req.audit_id} not found")

    # Insert feedback record
    feedback_data = {
        "audit_id": req.audit_id,
        "action": req.action,
        "reviewer_id": req.reviewer_id,
        "reviewer_role": req.reviewer_role,
        "false_positive_reason": req.false_positive_reason,
        "corrected_risk_level": req.corrected_risk_level,
        "per_flag_feedback": (
            [f.model_dump() for f in req.per_flag_feedback]
            if req.per_flag_feedback
            else None
        ),
        "free_text_note": req.free_text_note,
        "time_spent_seconds": req.time_spent_seconds,
    }
    result = db.insert_feedback(feedback_data)

    # Update audit result status
    status_map = {
        "confirmed": "confirmed",
        "false_positive": "false_positive",
        "investigate": "investigating",
    }
    db.update_audit_status(req.audit_id, status_map[req.action])

    # Update prompt version stats
    prompt_version = audit.get("prompt_version", "v1.0")
    db.increment_prompt_stats(prompt_version, req.action)

    # Write audit log
    db.append_audit_log(
        event_type="feedback",
        actor=req.reviewer_id,
        audit_id=req.audit_id,
        details={
            "action": req.action,
            "false_positive_reason": req.false_positive_reason,
            "corrected_risk_level": req.corrected_risk_level,
        },
    )

    # Generate rule impact preview
    impact = _compute_rule_impact(audit.get("risk_flags", []))

    return FeedbackResponse(
        feedback_id=result["id"],
        rule_impact_preview=impact,
    )


def _compute_rule_impact(risk_flags: list[dict]) -> list[RuleImpact]:
    """Compute current precision and trend for each triggered rule."""
    impacts = []
    try:
        stats = db.get_rule_feedback_stats()
    except Exception:
        return impacts

    for flag in risk_flags:
        rule = flag.get("rule", "")
        if not rule or rule not in stats:
            continue

        s = stats[rule]
        total = s["agree"] + s["disagree"]
        if total < 3:
            continue

        precision = s["agree"] / total

        # Determine trend (simplified — in production, compare to last week)
        if precision >= 0.7:
            trend = "stable"
        elif precision >= 0.4:
            trend = "declining"
            note = f"精准率 {precision:.0%}，建议关注"
        else:
            trend = "declining"
            note = f"精准率仅 {precision:.0%}，下次调优将建议降权"

        impacts.append(
            RuleImpact(
                rule=rule,
                current_precision=round(precision, 2),
                trend=trend,
                note=note if precision < 0.7 else "",
            )
        )

    return impacts


def get_feedback_summary(audit_id: str) -> Optional[dict]:
    """Get feedback summary for a specific audit result."""
    try:
        feedbacks = (
            db.get_client()
            .table("feedback")
            .select("*")
            .eq("audit_id", audit_id)
            .order("created_at", desc=True)
            .execute()
            .data
        )
        if not feedbacks:
            return None

        latest = feedbacks[0]
        return {
            "total_feedbacks": len(feedbacks),
            "latest_action": latest["action"],
            "latest_reviewer": latest["reviewer_id"],
            "latest_at": latest["created_at"],
            "false_positive_reason": latest.get("false_positive_reason"),
            "free_text_note": latest.get("free_text_note"),
        }
    except Exception:
        return None

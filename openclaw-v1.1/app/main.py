"""OpenClaw V1.1 HITL — FastAPI application.

Core pipeline:
  Employee uploads voucher
    → OCR → Claude → Rules → Decision
    → PASS: auto-push to Concur → approval flow
    → WARN: Feishu notification → finance reviews → approve/reject
    → FAIL: reject back to employee

Post-audit (hourly cron):
  Concur approved data → pull back → cross-validate against original voucher

Endpoints:
  POST /upload              — Upload voucher for audit
  GET  /results             — Query audit results
  POST /feedback            — Submit HITL feedback (V1.1 enhanced)
  GET  /metrics             — System performance metrics
  POST /rules/approve       — Approve/reject rule adjustments
  POST /learning/run        — Manually trigger learning cycle
  POST /concur/push/{id}    — Manually push approved audit to Concur
  POST /concur/reconcile    — Trigger post-audit reconciliation
"""

import logging
import time
import uuid
from datetime import datetime, timezone

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile

from . import db
from .audit import analyze
from .config import settings
from .feedback import record_feedback
from .learner import (
    approve_adjustment,
    get_pending_adjustments,
    run_weekly_learning_cycle,
)
from .models import (
    AuditResult,
    FeedbackRequest,
    FeedbackResponse,
    MetricsResponse,
    RiskFlag,
    RuleApprovalRequest,
    RulePerformance,
    WeeklySnapshot,
)
from .concur import push_to_concur, reconcile_with_concur, pull_approved_reports
from .notify import send_audit_result
from .ocr import extract_text_from_base64
from .rules import evaluate, get_current_params_snapshot

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="OpenClaw V1.1 HITL",
    description="AI-powered expense audit with Human-in-the-Loop feedback",
    version="1.1.0",
)


# ── POST /upload ──


@app.post("/upload")
async def upload_voucher(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    """Upload a voucher image for AI audit.

    Pipeline: OCR → Claude Analysis → Rule Engine → Feishu Notification
    """
    start_time = time.time()
    audit_id = f"AUD-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:4]}"

    # Read file
    content = await file.read()
    import base64

    image_b64 = base64.b64encode(content).decode()
    mime_type = file.content_type or "image/jpeg"

    # Step 1: OCR
    try:
        ocr_result = await extract_text_from_base64(image_b64, mime_type)
    except Exception as e:
        logger.error("OCR failed for %s: %s", audit_id, e)
        raise HTTPException(status_code=500, detail=f"OCR processing failed: {e}")

    # Step 2: Claude analysis
    try:
        ai_result = await analyze(ocr_result["raw_text"])
    except Exception as e:
        logger.error("AI analysis failed for %s: %s", audit_id, e)
        raise HTTPException(status_code=500, detail=f"AI analysis failed: {e}")

    structured = ai_result["structured"]

    # Step 3: Rule engine
    expense_data = {
        "amount": structured.get("amount", 0),
        "invoice_date": structured.get("invoice_date", ""),
        "invoice_number": structured.get("invoice_number", ""),
        "vendor_name": structured.get("vendor_name", ""),
        "expense_type": structured.get("expense_type", ""),
        "ocr_amount": structured.get("amount", 0),
        "claimed_amount": structured.get("amount", 0),
    }
    rule_result = evaluate(expense_data)

    # Merge AI risk flags with rule-based flags
    all_flags = []
    seen_rules = set()

    for rf in rule_result["triggered_rules"]:
        all_flags.append(rf)
        seen_rules.add(rf["rule"])

    for rf in ai_result.get("risk_flags", []):
        if rf.get("rule") not in seen_rules:
            all_flags.append({
                "rule": rf.get("rule", "ai_detected"),
                "description": rf.get("detail", ""),
                "severity": rf.get("severity", "medium"),
                "weight": 1.0,
                "score": 15,
                "confidence": rf.get("confidence", 0.7),
            })

    # Final risk level (rules take precedence per "LLM Advises, Rules Decide")
    risk_level = rule_result["risk_level"]
    risk_score = rule_result["risk_score"]

    processing_time = int((time.time() - start_time) * 1000)

    # Step 4: Save to database
    audit_data = {
        "audit_id": audit_id,
        "document_url": f"upload://{file.filename}",
        "ocr_raw_text": ocr_result["raw_text"],
        "ocr_structured": structured,
        "ocr_confidence": ocr_result["confidence"],
        "risk_level": risk_level,
        "risk_score": risk_score,
        "risk_flags": all_flags,
        "ai_reasoning": ai_result.get("ai_reasoning", ""),
        "prompt_version": ai_result.get("prompt_version", "v1.0"),
        "rule_params_snapshot": get_current_params_snapshot(),
        "processing_time_ms": processing_time,
        "status": "pending_review" if risk_level != "pass" else "pass",
    }

    try:
        db.insert_audit_result(audit_data)
    except Exception as e:
        logger.error("DB insert failed for %s: %s", audit_id, e)
        raise HTTPException(status_code=500, detail="Failed to save audit result")

    # Audit log
    db.append_audit_log(
        event_type="audit",
        actor="system",
        audit_id=audit_id,
        details={
            "risk_level": risk_level,
            "risk_score": risk_score,
            "rules_triggered": len(rule_result["triggered_rules"]),
            "processing_time_ms": processing_time,
        },
    )

    # Step 5: Send Feishu notification (async, non-blocking)
    result_model = AuditResult(
        audit_id=audit_id,
        risk_level=risk_level,
        risk_score=risk_score,
        risk_flags=[RiskFlag(**f) for f in all_flags],
        ai_reasoning=ai_result.get("ai_reasoning", ""),
        prompt_version=ai_result.get("prompt_version", "v1.0"),
        processing_time_ms=processing_time,
        ocr_structured=structured,
    )

    if risk_level != "pass":
        # WARN / FAIL → notify finance via Feishu for human review
        background_tasks.add_task(send_audit_result, result_model)
    else:
        # PASS → auto-push to Concur approval flow
        concur_data = {**expense_data, "audit_id": audit_id, "risk_level": risk_level, "risk_score": risk_score}
        background_tasks.add_task(_push_pass_to_concur, concur_data, content)

    return {
        "audit_id": audit_id,
        "risk_level": risk_level,
        "risk_score": risk_score,
        "risk_flags": all_flags,
        "processing_time_ms": processing_time,
        "concur_status": "auto_pushing" if risk_level == "pass" else "pending_review",
    }


async def _push_pass_to_concur(expense_data: dict, image_bytes: bytes):
    """Background task: push PASS audit results to Concur."""
    try:
        result = await push_to_concur(
            expense_data=expense_data,
            image_bytes=image_bytes,
            auto_submit=True,  # PASS items auto-submit to approval flow
        )
        # Update audit record with Concur IDs
        db.get_client().table("audit_results").update({
            "concur_report_id": result.get("concur_report_id", ""),
            "concur_entry_id": result.get("concur_entry_id", ""),
            "concur_status": "submitted",
        }).eq("audit_id", expense_data["audit_id"]).execute()

        db.append_audit_log(
            event_type="concur_push",
            actor="system",
            audit_id=expense_data["audit_id"],
            details=result,
        )
    except Exception as e:
        logger.error("Failed to push %s to Concur: %s", expense_data.get("audit_id"), e)
        db.append_audit_log(
            event_type="concur_push_failed",
            actor="system",
            audit_id=expense_data.get("audit_id"),
            details={"error": str(e)},
        )


# ── GET /results ──


@app.get("/results")
async def get_results(
    status: str = "pending_review",
    limit: int = 50,
):
    """Query audit results by status."""
    results = db.get_results_by_status(status, limit)
    return {"results": results, "total": len(results)}


@app.get("/results/{audit_id}")
async def get_result_detail(audit_id: str):
    """Get a specific audit result."""
    result = db.get_audit_result(audit_id)
    if not result:
        raise HTTPException(status_code=404, detail="Audit result not found")
    return result


# ── POST /feedback (V1.1 enhanced) ──


@app.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(req: FeedbackRequest):
    """Submit HITL feedback for an audit result.

    This is the core V1.1 HITL endpoint. Each feedback:
    - Updates audit status (confirmed/false_positive/investigating)
    - Records structured per-rule feedback
    - Updates prompt version stats
    - Returns rule impact preview
    """
    try:
        return await record_feedback(req)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── GET /metrics (V1.1 new) ──


@app.get("/metrics", response_model=MetricsResponse)
async def get_metrics(period: str = "week"):
    """Get system performance metrics.

    Shows precision trends, rule performance, and pending adjustments.
    """
    # Get recent weekly metrics
    weeks = {"week": 1, "month": 4, "all": 52}.get(period, 1)
    recent = db.get_recent_weekly_metrics(weeks)

    if not recent:
        # No metrics yet — return empty
        return MetricsResponse(
            current_week=WeeklySnapshot(
                total_audits=0,
                precision=0,
                false_positive_rate=0,
                feedback_rate=0,
                avg_review_time_seconds=0,
                top_triggered_rules=[],
            ),
        )

    latest = recent[0]
    total_fb = latest.get("confirmed_anomalies", 0) + latest.get("false_positives", 0)

    # Build top rules
    trigger_dist = latest.get("rule_trigger_distribution", {})
    fp_dist = latest.get("false_positive_by_rule", {})
    top_rules = []
    for rule, count in sorted(trigger_dist.items(), key=lambda x: x[1], reverse=True)[:5]:
        fp = fp_dist.get(rule, 0)
        prec = (count - fp) / count if count > 0 else 0
        top_rules.append(RulePerformance(rule=rule, trigger_count=count, precision=round(prec, 2)))

    current = WeeklySnapshot(
        total_audits=latest.get("total_audits", 0),
        precision=latest.get("precision", 0),
        false_positive_rate=latest.get("false_positives", 0) / total_fb if total_fb > 0 else 0,
        feedback_rate=latest.get("feedback_rate", 0),
        avg_review_time_seconds=latest.get("avg_review_time_seconds", 0),
        top_triggered_rules=top_rules,
    )

    # Trend
    trend = {}
    if len(recent) > 1:
        trend["precision_trend"] = [m.get("precision", 0) for m in reversed(recent)]
        trend["fp_trend"] = [
            m.get("false_positives", 0) / max(1, m.get("confirmed_anomalies", 0) + m.get("false_positives", 0))
            for m in reversed(recent)
        ]

    pending = get_pending_adjustments()

    return MetricsResponse(
        current_week=current,
        trend=trend,
        pending_adjustments=pending,
    )


# ── POST /rules/approve (V1.1 new) ──


@app.post("/rules/approve")
async def approve_rule_adjustment(req: RuleApprovalRequest):
    """Approve or reject a rule adjustment proposal.

    This is the HITL gate: no automatic rule changes without human approval.
    """
    try:
        result = await approve_adjustment(req.adjustment_id, req.approved, req.admin_note or "")
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── POST /learning/run (V1.1 new, admin only) ──


@app.post("/learning/run")
async def trigger_learning_cycle():
    """Manually trigger the weekly learning cycle.

    In production, this runs as a cron job every Sunday 23:00.
    This endpoint allows manual triggering for testing.
    """
    result = await run_weekly_learning_cycle()
    return result


# ═══════════════════════════════════════════════
# Concur Integration Endpoints
# ═══════════════════════════════════════════════


@app.post("/concur/push/{audit_id}")
async def manual_push_to_concur(audit_id: str):
    """Manually push an approved WARN audit to Concur.

    Called after finance reviews a WARN item in Feishu and clicks [approve].
    Flow: WARN → finance reviews → approves → this endpoint → Concur.
    """
    audit = db.get_audit_result(audit_id)
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")

    if audit.get("concur_status") == "submitted":
        return {"status": "already_submitted", "audit_id": audit_id}

    expense_data = {
        **(audit.get("ocr_structured", {})),
        "audit_id": audit_id,
        "risk_level": audit.get("risk_level", ""),
        "risk_score": audit.get("risk_score", 0),
    }

    try:
        result = await push_to_concur(
            expense_data=expense_data,
            auto_submit=True,
        )

        db.get_client().table("audit_results").update({
            "concur_report_id": result.get("concur_report_id", ""),
            "concur_entry_id": result.get("concur_entry_id", ""),
            "concur_status": "submitted",
        }).eq("audit_id", audit_id).execute()

        db.append_audit_log(
            event_type="concur_push_manual",
            actor="finance",
            audit_id=audit_id,
            details=result,
        )

        return {**result, "audit_id": audit_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Concur push failed: {e}")


@app.post("/concur/reconcile")
async def trigger_reconciliation(modified_after: str = ""):
    """Trigger post-audit reconciliation: pull Concur approved data and cross-validate.

    In production, runs as hourly cron. This endpoint allows manual triggering.

    Checks for discrepancies:
    - Manager changed the amount after OpenClaw audit?
    - Report was rejected in Concur?
    - Date/vendor mismatch between original voucher and Concur entry?
    """
    try:
        reports = await pull_approved_reports(modified_after=modified_after)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to pull Concur data: {e}")

    results = []
    for report in reports:
        report_id = report.get("ID", "")

        # Find matching OpenClaw audit by Custom1 field
        try:
            entries = await pull_approved_reports()  # would use pull_report_entries in real code
        except Exception:
            continue

        # Look up our audits that were pushed to this report
        our_audits = (
            db.get_client()
            .table("audit_results")
            .select("audit_id")
            .eq("concur_report_id", report_id)
            .execute()
            .data
        )

        for audit in our_audits:
            try:
                recon = await reconcile_with_concur(audit["audit_id"], report_id)
                results.append(recon)
            except Exception as e:
                logger.error("Reconciliation failed for %s: %s", audit["audit_id"], e)

    return {
        "reconciled": len(results),
        "discrepancies_found": sum(1 for r in results if r.get("discrepancies")),
        "results": results,
    }


# ── Health check ──


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": "1.1.0",
        "features": [
            "hitl_feedback",
            "rule_auto_tuning",
            "prompt_versioning",
            "weekly_metrics",
            "concur_integration",
            "post_audit_reconciliation",
        ],
    }

"""Pydantic models for OpenClaw V1.1 HITL."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Request Models ──


class FlagFeedback(BaseModel):
    rule: str
    agree: bool
    note: str = ""


class FeedbackRequest(BaseModel):
    audit_id: str
    action: str = Field(pattern=r"^(confirmed|false_positive|investigate)$")
    reviewer_id: str
    reviewer_role: Optional[str] = None
    false_positive_reason: Optional[str] = None
    corrected_risk_level: Optional[str] = Field(
        default=None, pattern=r"^(none|low|medium|high)$"
    )
    per_flag_feedback: Optional[list[FlagFeedback]] = None
    free_text_note: Optional[str] = None
    time_spent_seconds: Optional[int] = None


class RuleApprovalRequest(BaseModel):
    adjustment_id: str
    approved: bool
    admin_note: Optional[str] = None


# ── Response Models ──


class RiskFlag(BaseModel):
    rule: str
    description: str = ""
    severity: str = "medium"
    weight: float = 1.0
    score: int = 0
    confidence: float = 0.7


class AuditResult(BaseModel):
    audit_id: str
    risk_level: str
    risk_score: int
    risk_flags: list[RiskFlag]
    ai_reasoning: str = ""
    prompt_version: str = "v1.0"
    processing_time_ms: int = 0
    ocr_structured: dict = {}


class RuleImpact(BaseModel):
    rule: str
    current_precision: float
    trend: str  # "improving" | "declining" | "stable"
    note: str = ""


class FeedbackResponse(BaseModel):
    status: str = "recorded"
    feedback_id: str
    rule_impact_preview: list[RuleImpact] = []


class RulePerformance(BaseModel):
    rule: str
    trigger_count: int
    precision: float


class WeeklySnapshot(BaseModel):
    total_audits: int
    precision: float
    false_positive_rate: float
    feedback_rate: float
    avg_review_time_seconds: float
    top_triggered_rules: list[RulePerformance]


class PendingAdjustment(BaseModel):
    adjustment_id: str
    rule: str
    proposed_action: str
    reason: str
    status: str = "awaiting_approval"


class MetricsResponse(BaseModel):
    current_week: WeeklySnapshot
    trend: dict = {}
    pending_adjustments: list[PendingAdjustment] = []


class WeeklyReportData(BaseModel):
    week_start: date
    week_end: date
    total_audits: int
    pass_count: int
    warn_count: int
    fail_count: int
    precision: float
    false_positive_rate: float
    feedback_rate: float
    confirmed_anomalies: int
    confirmed_amount: float = 0
    rule_performances: list[RulePerformance] = []
    adjustments: list[PendingAdjustment] = []

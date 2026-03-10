"""Investigation state and result models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FraudTypology(str, Enum):
    """Known fraud patterns."""

    STRUCTURING = "structuring"  # Splitting transactions to avoid thresholds
    ROUND_TRIPPING = "round_tripping"  # Circular fund flows
    RAPID_MOVEMENT = "rapid_movement"  # Quick in-and-out transfers
    LAYERING = "layering"  # Complex chains to obscure origin
    SMURFING = "smurfing"  # Multiple small deposits by different people
    VELOCITY_ABUSE = "velocity_abuse"  # Abnormal transaction frequency
    DORMANT_ACTIVATION = "dormant_activation"  # Sudden activity on dormant account
    UNKNOWN = "unknown"


class AnomalyFlag(BaseModel):
    """A single anomaly detected by the Pattern Detector."""

    typology: FraudTypology
    description: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[str]  # Transaction IDs or data points supporting this flag
    explanation: str  # Human-readable explanation for compliance


class EntityContext(BaseModel):
    """Enriched context about an entity (person or organization)."""

    entity_id: str
    entity_name: str | None = None
    account_age_days: int | None = None
    historical_transaction_count: int | None = None
    historical_avg_amount: float | None = None
    related_entities: list[str] = Field(default_factory=list)
    risk_notes: list[str] = Field(default_factory=list)
    news_mentions: list[str] = Field(default_factory=list)


class RiskAssessment(BaseModel):
    """Risk assessment output from the Risk Assessor agent."""

    overall_risk: RiskLevel
    risk_score: float = Field(ge=0.0, le=100.0)
    anomaly_flags: list[AnomalyFlag]
    mitigating_factors: list[str] = Field(default_factory=list)
    reasoning_chain: list[str]  # Step-by-step reasoning (for explainability)
    recommended_action: str  # e.g., "escalate", "monitor", "dismiss"


class InvestigationState(BaseModel):
    """Tracks the state of an investigation through the pipeline."""

    investigation_id: str
    created_at: datetime = Field(default_factory=datetime.now)
    status: str = "in_progress"  # in_progress | completed | needs_review

    # Stage outputs (populated as pipeline progresses)
    pattern_result: list[AnomalyFlag] | None = None
    entity_contexts: list[EntityContext] | None = None
    risk_assessment: RiskAssessment | None = None
    report_path: str | None = None

    # Verification
    verification_passed: bool | None = None
    verification_notes: str | None = None

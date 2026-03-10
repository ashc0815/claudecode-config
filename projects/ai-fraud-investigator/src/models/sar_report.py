"""SAR (Suspicious Activity Report) schema."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from .investigation import RiskLevel


class SAREvidence(BaseModel):
    """A single piece of evidence in the SAR report."""

    evidence_type: str  # "transaction", "pattern", "entity", "external"
    description: str
    source: str  # Where this evidence came from
    confidence: float = Field(ge=0.0, le=1.0)


class SARReport(BaseModel):
    """
    Suspicious Activity Report — the final output of the investigation.

    Modeled after FinCEN SAR format (simplified for demo).
    In production, this would conform to the BSA E-Filing XML schema.
    """

    report_id: str
    investigation_id: str
    generated_at: datetime = Field(default_factory=datetime.now)

    # Subject information
    subject_entities: list[str]  # Entity IDs involved
    subject_summary: str  # Brief description of the subject(s)

    # Suspicious activity details
    activity_start_date: datetime | None = None
    activity_end_date: datetime | None = None
    total_amount_involved: float
    currency: str = "USD"

    # Core findings
    risk_level: RiskLevel
    suspicious_activity_description: str  # Narrative description
    fraud_typologies_identified: list[str]
    evidence_chain: list[SAREvidence]
    reasoning_chain: list[str]  # Step-by-step logic (explainability)

    # Recommendations
    recommended_action: str
    additional_investigation_needed: bool = False
    additional_notes: str | None = None

    def to_narrative(self) -> str:
        """Generate a human-readable narrative for the SAR filing."""
        lines = [
            f"SAR Report #{self.report_id}",
            f"Investigation: {self.investigation_id}",
            f"Generated: {self.generated_at.strftime('%Y-%m-%d %H:%M')}",
            f"Risk Level: {self.risk_level.value.upper()}",
            "",
            "=" * 60,
            "SUBJECT SUMMARY",
            "=" * 60,
            self.subject_summary,
            "",
            "=" * 60,
            "SUSPICIOUS ACTIVITY DESCRIPTION",
            "=" * 60,
            self.suspicious_activity_description,
            "",
            f"Total Amount Involved: {self.currency} {self.total_amount_involved:,.2f}",
            f"Fraud Typologies: {', '.join(self.fraud_typologies_identified)}",
            "",
            "=" * 60,
            "EVIDENCE CHAIN",
            "=" * 60,
        ]
        for i, evidence in enumerate(self.evidence_chain, 1):
            lines.append(
                f"  [{i}] ({evidence.evidence_type}) {evidence.description}"
            )
            lines.append(f"      Source: {evidence.source}")
            lines.append(f"      Confidence: {evidence.confidence:.0%}")
            lines.append("")

        lines.extend([
            "=" * 60,
            "REASONING CHAIN",
            "=" * 60,
        ])
        for i, step in enumerate(self.reasoning_chain, 1):
            lines.append(f"  Step {i}: {step}")

        lines.extend([
            "",
            "=" * 60,
            f"RECOMMENDED ACTION: {self.recommended_action}",
            "=" * 60,
        ])

        return "\n".join(lines)

"""
Stage 3: Risk Assessor Agent

Synthesizes pattern detection and entity context into an explainable
risk assessment. Acts as an adversarial reviewer — challenges the
Pattern Detector's findings to reduce false positives.

Key design: Every risk score MUST come with a reasoning chain.
This is a regulatory requirement, not a nice-to-have.
"""

from __future__ import annotations

import json

from ..models.investigation import (
    AnomalyFlag,
    EntityContext,
    RiskAssessment,
    RiskLevel,
)
from ..utils.llm_client import LLMClient

SYSTEM_PROMPT = """You are a senior financial crime risk assessor. Your role is to:

1. REVIEW anomaly flags from the Pattern Detector — challenge weak evidence
2. CONSIDER entity context — does the context explain the anomaly innocently?
3. SYNTHESIZE a final risk assessment with an overall score and level
4. PRODUCE an explicit reasoning chain (step-by-step logic)

You must act as a critical reviewer. Not every flagged pattern is fraud.
Consider legitimate explanations before escalating.

Risk levels:
- LOW (0-25): Normal activity, minor anomalies with innocent explanations
- MEDIUM (26-50): Some suspicious indicators, worth monitoring
- HIGH (51-75): Multiple corroborating indicators, recommend investigation
- CRITICAL (76-100): Strong evidence of fraud, immediate escalation needed

Your response MUST include:
- overall_risk: one of [low, medium, high, critical]
- risk_score: 0-100
- anomaly_flags: refined list (you may remove weak flags or adjust confidence)
- mitigating_factors: legitimate explanations you considered
- reasoning_chain: numbered list of your reasoning steps
- recommended_action: one of [dismiss, monitor, investigate, escalate]

Respond in JSON format."""


class RiskAssessorAgent:
    """Produces explainable risk assessments."""

    def __init__(self):
        self.llm = LLMClient()

    def assess(
        self,
        anomaly_flags: list[AnomalyFlag],
        entity_contexts: list[EntityContext],
    ) -> RiskAssessment:
        """Generate a risk assessment from anomaly flags and entity context."""
        response = self.llm.query(
            system_prompt=SYSTEM_PROMPT,
            user_message=(
                f"Assess the risk based on these findings.\n\n"
                f"ANOMALY FLAGS:\n{self._format_flags(anomaly_flags)}\n\n"
                f"ENTITY CONTEXT:\n{self._format_entities(entity_contexts)}\n\n"
                "Provide your risk assessment with full reasoning chain."
            ),
        )

        return self._parse_response(response, anomaly_flags)

    def _format_flags(self, flags: list[AnomalyFlag]) -> str:
        return json.dumps(
            [
                {
                    "typology": f.typology.value,
                    "description": f.description,
                    "confidence": f.confidence,
                    "evidence": f.evidence,
                    "explanation": f.explanation,
                }
                for f in flags
            ],
            indent=2,
        )

    def _format_entities(self, entities: list[EntityContext]) -> str:
        return json.dumps(
            [
                {
                    "entity_id": e.entity_id,
                    "account_age_days": e.account_age_days,
                    "historical_avg_amount": e.historical_avg_amount,
                    "related_entities": e.related_entities,
                    "risk_notes": e.risk_notes,
                }
                for e in entities
            ],
            indent=2,
        )

    def _parse_response(
        self, response: str, original_flags: list[AnomalyFlag]
    ) -> RiskAssessment:
        """Parse LLM response into a RiskAssessment."""
        try:
            data = json.loads(response)
            return RiskAssessment(
                overall_risk=RiskLevel(data["overall_risk"]),
                risk_score=data["risk_score"],
                anomaly_flags=original_flags,  # Keep original flags for traceability
                mitigating_factors=data.get("mitigating_factors", []),
                reasoning_chain=data["reasoning_chain"],
                recommended_action=data["recommended_action"],
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            # Fallback: if parsing fails, return a conservative assessment
            return RiskAssessment(
                overall_risk=RiskLevel.MEDIUM,
                risk_score=50.0,
                anomaly_flags=original_flags,
                mitigating_factors=[],
                reasoning_chain=[f"Assessment parsing failed: {e}", "Defaulting to MEDIUM risk for manual review"],
                recommended_action="investigate",
            )

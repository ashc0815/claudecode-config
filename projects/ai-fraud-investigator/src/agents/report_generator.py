"""
Stage 4: Report Generator Agent

Generates SAR-format investigation reports with evidence chains.
Output is designed to be directly usable by compliance officers.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from ..models.investigation import InvestigationState, RiskAssessment
from ..models.sar_report import SAREvidence, SARReport
from ..models.transaction import TransactionBatch
from ..utils.llm_client import LLMClient

SYSTEM_PROMPT = """You are a compliance report writer specializing in Suspicious Activity Reports (SAR).

Given an investigation's findings, generate a clear, professional narrative that:
1. Summarizes the suspicious activity in plain language
2. References specific evidence (transaction IDs, amounts, dates)
3. Explains why this activity is suspicious (not just that it is)
4. Provides actionable recommendations

Your narrative should be suitable for filing with financial regulators.
Use formal but clear language. Avoid jargon where possible.

Respond with a JSON object containing:
- suspicious_activity_description: The main narrative (2-4 paragraphs)
- subject_summary: Brief description of subjects involved (1-2 sentences)
- additional_notes: Any caveats or suggestions for further investigation"""


class ReportGeneratorAgent:
    """Generates SAR reports from investigation results."""

    def __init__(self):
        self.llm = LLMClient()

    def generate(
        self,
        batch: TransactionBatch,
        state: InvestigationState,
    ) -> SARReport:
        """Generate a SAR report from investigation state."""
        assessment = state.risk_assessment

        # Build evidence chain from all stages
        evidence_chain = self._build_evidence_chain(state)

        # Generate narrative via LLM
        narrative = self._generate_narrative(batch, state)

        # Determine date range
        timestamps = [tx.timestamp for tx in batch.transactions]

        return SARReport(
            report_id=f"SAR-{uuid.uuid4().hex[:8].upper()}",
            investigation_id=state.investigation_id,
            subject_entities=list(batch.unique_entities),
            subject_summary=narrative.get("subject_summary", "See description"),
            activity_start_date=min(timestamps) if timestamps else None,
            activity_end_date=max(timestamps) if timestamps else None,
            total_amount_involved=batch.total_amount,
            risk_level=assessment.overall_risk,
            suspicious_activity_description=narrative.get(
                "suspicious_activity_description", ""
            ),
            fraud_typologies_identified=[
                f.typology.value for f in assessment.anomaly_flags
            ],
            evidence_chain=evidence_chain,
            reasoning_chain=assessment.reasoning_chain,
            recommended_action=assessment.recommended_action,
            additional_notes=narrative.get("additional_notes"),
        )

    def _build_evidence_chain(self, state: InvestigationState) -> list[SAREvidence]:
        """Compile evidence from all pipeline stages."""
        evidence = []

        # From pattern detection
        if state.pattern_result:
            for flag in state.pattern_result:
                evidence.append(
                    SAREvidence(
                        evidence_type="pattern",
                        description=f"[{flag.typology.value}] {flag.explanation}",
                        source="Pattern Detector Agent",
                        confidence=flag.confidence,
                    )
                )

        # From entity enrichment
        if state.entity_contexts:
            for entity in state.entity_contexts:
                for note in entity.risk_notes:
                    evidence.append(
                        SAREvidence(
                            evidence_type="entity",
                            description=f"Entity {entity.entity_id}: {note}",
                            source="Context Enricher Agent",
                            confidence=0.7,
                        )
                    )

        # From risk assessment
        if state.risk_assessment:
            evidence.append(
                SAREvidence(
                    evidence_type="assessment",
                    description=(
                        f"Overall risk: {state.risk_assessment.overall_risk.value} "
                        f"(score: {state.risk_assessment.risk_score})"
                    ),
                    source="Risk Assessor Agent",
                    confidence=state.risk_assessment.risk_score / 100,
                )
            )

        return evidence

    def _generate_narrative(
        self, batch: TransactionBatch, state: InvestigationState
    ) -> dict:
        """Use LLM to generate the narrative sections of the report."""
        import json

        assessment = state.risk_assessment

        response = self.llm.query(
            system_prompt=SYSTEM_PROMPT,
            user_message=(
                f"Generate a SAR narrative for this investigation.\n\n"
                f"Transaction count: {len(batch.transactions)}\n"
                f"Total amount: ${batch.total_amount:,.2f}\n"
                f"Entities involved: {len(batch.unique_entities)}\n"
                f"Risk level: {assessment.overall_risk.value}\n"
                f"Risk score: {assessment.risk_score}\n\n"
                f"Fraud typologies: {[f.typology.value for f in assessment.anomaly_flags]}\n"
                f"Reasoning chain: {assessment.reasoning_chain}\n"
                f"Mitigating factors: {assessment.mitigating_factors}"
            ),
        )

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {"suspicious_activity_description": response}

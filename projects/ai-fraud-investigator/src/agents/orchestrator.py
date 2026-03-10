"""
Orchestrator Agent — Main coordinator for the investigation pipeline.

Implements the Plan-Execute-Verify pattern:
1. PLAN: Determine which stages to run based on input
2. EXECUTE: Run each agent stage sequentially
3. VERIFY: Check stage output quality; retry or escalate on failure

Usage:
    python -m src.agents.orchestrator --input data/sample_transactions.csv
"""

from __future__ import annotations

import argparse
import sys
import uuid

from ..models.investigation import InvestigationState
from ..models.transaction import TransactionBatch
from ..utils.data_loader import load_sample_batch
from .context_enricher import ContextEnricherAgent
from .pattern_detector import PatternDetectorAgent
from .report_generator import ReportGeneratorAgent
from .risk_assessor import RiskAssessorAgent


class Orchestrator:
    """Coordinates the multi-agent investigation pipeline."""

    def __init__(self, max_retries: int = 2):
        self.max_retries = max_retries
        self.pattern_detector = PatternDetectorAgent()
        self.context_enricher = ContextEnricherAgent()
        self.risk_assessor = RiskAssessorAgent()
        self.report_generator = ReportGeneratorAgent()

    def investigate(self, batch: TransactionBatch) -> InvestigationState:
        """Run the full investigation pipeline on a transaction batch."""
        state = InvestigationState(
            investigation_id=f"INV-{uuid.uuid4().hex[:8].upper()}"
        )

        # Stage 1: Pattern Detection
        print(f"[Stage 1] Pattern Detection — analyzing {len(batch.transactions)} transactions...")
        state.pattern_result = self._run_with_retry(
            lambda: self.pattern_detector.analyze(batch),
            stage_name="Pattern Detection",
        )
        if not state.pattern_result:
            print("[Stage 1] No anomalies detected. Investigation complete.")
            state.status = "completed"
            return state
        print(f"[Stage 1] Found {len(state.pattern_result)} anomaly flags.")

        # Stage 2: Context Enrichment
        print("[Stage 2] Context Enrichment — profiling entities...")
        state.entity_contexts = self._run_with_retry(
            lambda: self.context_enricher.enrich(batch, state.pattern_result),
            stage_name="Context Enrichment",
        )
        print(f"[Stage 2] Enriched {len(state.entity_contexts or [])} entity profiles.")

        # Stage 3: Risk Assessment
        print("[Stage 3] Risk Assessment — synthesizing findings...")
        state.risk_assessment = self._run_with_retry(
            lambda: self.risk_assessor.assess(
                state.pattern_result, state.entity_contexts or []
            ),
            stage_name="Risk Assessment",
        )
        print(
            f"[Stage 3] Risk: {state.risk_assessment.overall_risk.value} "
            f"(score: {state.risk_assessment.risk_score})"
        )

        # Stage 4: Report Generation
        print("[Stage 4] Generating SAR report...")
        report = self._run_with_retry(
            lambda: self.report_generator.generate(batch, state),
            stage_name="Report Generation",
        )
        if report:
            print(f"[Stage 4] Report generated: {report.report_id}")
            print("\n" + report.to_narrative())

        # Verification
        state = self._verify(state)
        state.status = "completed"
        return state

    def _run_with_retry(self, fn, stage_name: str):
        """Execute a stage function with retry logic."""
        for attempt in range(self.max_retries + 1):
            try:
                result = fn()
                if result is not None:
                    return result
            except Exception as e:
                print(f"[{stage_name}] Attempt {attempt + 1} failed: {e}")
                if attempt == self.max_retries:
                    print(f"[{stage_name}] Max retries exceeded. Skipping.")
                    return None
        return None

    def _verify(self, state: InvestigationState) -> InvestigationState:
        """Verify investigation quality (Plan-Execute-Verify pattern)."""
        issues = []

        if state.risk_assessment:
            # Check: reasoning chain must not be empty
            if not state.risk_assessment.reasoning_chain:
                issues.append("Risk assessment has no reasoning chain")

            # Check: high/critical risk must have evidence
            if state.risk_assessment.overall_risk.value in ("high", "critical"):
                if not state.pattern_result:
                    issues.append("High risk but no anomaly flags")

        state.verification_passed = len(issues) == 0
        state.verification_notes = "; ".join(issues) if issues else "All checks passed"
        print(f"[Verify] {'PASSED' if state.verification_passed else 'FAILED'}: {state.verification_notes}")
        return state


def main():
    parser = argparse.ArgumentParser(description="AI Fraud Investigation Agent")
    parser.add_argument("--input", required=True, help="Path to transaction CSV file")
    parser.add_argument("--limit", type=int, default=100, help="Max transactions to analyze")
    args = parser.parse_args()

    batch = load_sample_batch(args.input, limit=args.limit)
    orchestrator = Orchestrator()
    orchestrator.investigate(batch)


if __name__ == "__main__":
    main()

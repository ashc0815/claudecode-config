"""
Stage 1: Pattern Detector Agent

Analyzes transactions against known fraud typologies and flags anomalies.
Each flag includes a confidence score and human-readable explanation
(required for regulatory compliance).
"""

from __future__ import annotations

import json

from ..models.investigation import AnomalyFlag, FraudTypology
from ..models.transaction import TransactionBatch
from ..utils.llm_client import LLMClient

SYSTEM_PROMPT = """You are a financial fraud detection specialist. Your job is to analyze
transaction data and identify suspicious patterns.

You know these fraud typologies:
- STRUCTURING: Splitting transactions to stay below reporting thresholds (e.g., multiple
  transfers just under $10,000)
- ROUND_TRIPPING: Funds flowing in a circle back to the originator through intermediaries
- RAPID_MOVEMENT: Funds received and immediately transferred out (pass-through behavior)
- LAYERING: Complex chains of transactions designed to obscure the origin of funds
- SMURFING: Multiple small deposits from different sources into one account
- VELOCITY_ABUSE: Abnormally high transaction frequency for the account profile
- DORMANT_ACTIVATION: Sudden high-value activity on a previously inactive account

For each suspicious pattern found, provide:
1. The typology name
2. A confidence score (0.0-1.0)
3. Specific transaction IDs as evidence
4. A clear, non-technical explanation suitable for a compliance officer

Respond in JSON format as a list of anomaly objects."""


class PatternDetectorAgent:
    """Detects fraud patterns in transaction data."""

    def __init__(self):
        self.llm = LLMClient()

    def analyze(self, batch: TransactionBatch) -> list[AnomalyFlag]:
        """Analyze a batch of transactions for suspicious patterns."""
        # Prepare transaction summary for the LLM
        tx_summary = self._prepare_summary(batch)

        response = self.llm.query(
            system_prompt=SYSTEM_PROMPT,
            user_message=f"Analyze these transactions for fraud patterns:\n\n{tx_summary}",
        )

        return self._parse_response(response)

    def _prepare_summary(self, batch: TransactionBatch) -> str:
        """Format transactions into a concise summary for LLM analysis."""
        lines = [
            f"Total transactions: {len(batch.transactions)}",
            f"Total amount: ${batch.total_amount:,.2f}",
            f"Unique entities: {len(batch.unique_entities)}",
            "",
            "Transaction details:",
        ]
        for tx in batch.transactions:
            lines.append(
                f"  {tx.transaction_id} | {tx.type.value} | "
                f"${tx.amount:,.2f} | {tx.sender_id} → {tx.receiver_id} | "
                f"{tx.timestamp.isoformat()}"
            )
        return "\n".join(lines)

    def _parse_response(self, response: str) -> list[AnomalyFlag]:
        """Parse LLM response into structured AnomalyFlag objects."""
        try:
            data = json.loads(response)
            flags = []
            for item in data:
                flag = AnomalyFlag(
                    typology=FraudTypology(item.get("typology", "unknown")),
                    description=item["description"],
                    confidence=item["confidence"],
                    evidence=item.get("evidence", []),
                    explanation=item["explanation"],
                )
                flags.append(flag)
            return flags
        except (json.JSONDecodeError, KeyError, ValueError):
            # If parsing fails, return empty — orchestrator will retry
            return []

"""
Stage 2: Context Enricher Agent

Enriches investigation with entity context: account history,
related entities, network connections, and external signals.
"""

from __future__ import annotations

import json

from ..models.investigation import AnomalyFlag, EntityContext
from ..models.transaction import TransactionBatch
from ..utils.llm_client import LLMClient

SYSTEM_PROMPT = """You are a financial intelligence analyst specializing in entity research
and network analysis. Given transaction data and initial anomaly flags, your job is to:

1. Profile each entity involved (account age, typical behavior, transaction history)
2. Identify relationships between entities (shared recipients, common patterns)
3. Flag any contextual risk factors (new account, unusual geography, etc.)
4. Note if entities appear in any known risk databases or news

For each entity, provide:
- entity_id: The account/entity identifier
- account_age_days: Estimated account age (null if unknown)
- historical_transaction_count: Typical transaction volume
- historical_avg_amount: Typical transaction size
- related_entities: List of entity IDs this entity frequently transacts with
- risk_notes: Any contextual risk factors identified
- news_mentions: Any relevant news or public information

Respond in JSON format as a list of entity context objects."""


class ContextEnricherAgent:
    """Enriches entities with contextual information."""

    def __init__(self):
        self.llm = LLMClient()

    def enrich(
        self,
        batch: TransactionBatch,
        anomaly_flags: list[AnomalyFlag],
    ) -> list[EntityContext]:
        """Enrich entity context based on transactions and detected anomalies."""
        # Focus on entities mentioned in anomaly flags first
        flagged_entities = set()
        for flag in anomaly_flags:
            for evidence_id in flag.evidence:
                for tx in batch.transactions:
                    if tx.transaction_id == evidence_id:
                        flagged_entities.add(tx.sender_id)
                        flagged_entities.add(tx.receiver_id)

        # Build entity profiles from transaction data
        entity_profiles = self._build_profiles(batch, flagged_entities)

        response = self.llm.query(
            system_prompt=SYSTEM_PROMPT,
            user_message=(
                f"Enrich these entity profiles with context.\n\n"
                f"Entity profiles from transaction data:\n{entity_profiles}\n\n"
                f"Anomaly flags detected:\n{self._format_flags(anomaly_flags)}"
            ),
        )

        return self._parse_response(response)

    def _build_profiles(
        self, batch: TransactionBatch, priority_entities: set[str]
    ) -> str:
        """Build basic entity profiles from transaction data."""
        profiles: dict[str, dict] = {}
        for tx in batch.transactions:
            for entity_id in [tx.sender_id, tx.receiver_id]:
                if entity_id not in profiles:
                    profiles[entity_id] = {
                        "entity_id": entity_id,
                        "transaction_count": 0,
                        "total_sent": 0.0,
                        "total_received": 0.0,
                        "counterparties": set(),
                        "is_priority": entity_id in priority_entities,
                    }
                profiles[entity_id]["transaction_count"] += 1
                if entity_id == tx.sender_id:
                    profiles[entity_id]["total_sent"] += tx.amount
                else:
                    profiles[entity_id]["total_received"] += tx.amount
                other = tx.receiver_id if entity_id == tx.sender_id else tx.sender_id
                profiles[entity_id]["counterparties"].add(other)

        # Convert sets to lists for serialization
        for p in profiles.values():
            p["counterparties"] = list(p["counterparties"])

        return json.dumps(list(profiles.values()), indent=2)

    def _format_flags(self, flags: list[AnomalyFlag]) -> str:
        return "\n".join(
            f"- [{f.typology.value}] {f.description} (confidence: {f.confidence})"
            for f in flags
        )

    def _parse_response(self, response: str) -> list[EntityContext]:
        """Parse LLM response into EntityContext objects."""
        try:
            data = json.loads(response)
            return [
                EntityContext(
                    entity_id=item["entity_id"],
                    entity_name=item.get("entity_name"),
                    account_age_days=item.get("account_age_days"),
                    historical_transaction_count=item.get("historical_transaction_count"),
                    historical_avg_amount=item.get("historical_avg_amount"),
                    related_entities=item.get("related_entities", []),
                    risk_notes=item.get("risk_notes", []),
                    news_mentions=item.get("news_mentions", []),
                )
                for item in data
            ]
        except (json.JSONDecodeError, KeyError, ValueError):
            return []

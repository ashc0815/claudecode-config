"""Transaction data models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class TransactionType(str, Enum):
    TRANSFER = "transfer"
    PAYMENT = "payment"
    CASH_OUT = "cash_out"
    CASH_IN = "cash_in"
    DEBIT = "debit"


class Transaction(BaseModel):
    """A single financial transaction."""

    transaction_id: str
    timestamp: datetime
    type: TransactionType
    amount: float = Field(ge=0)
    currency: str = "USD"
    sender_id: str
    sender_name: str | None = None
    receiver_id: str
    receiver_name: str | None = None
    sender_balance_before: float | None = None
    sender_balance_after: float | None = None
    receiver_balance_before: float | None = None
    receiver_balance_after: float | None = None
    memo: str | None = None
    is_flagged: bool = False


class TransactionBatch(BaseModel):
    """A batch of transactions to investigate."""

    transactions: list[Transaction]
    alert_reason: str | None = None
    source: str = "manual"

    @property
    def total_amount(self) -> float:
        return sum(t.amount for t in self.transactions)

    @property
    def unique_entities(self) -> set[str]:
        entities = set()
        for t in self.transactions:
            entities.add(t.sender_id)
            entities.add(t.receiver_id)
        return entities

"""Dataset loading and preprocessing utilities."""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from ..models.transaction import Transaction, TransactionBatch, TransactionType


# PaySim column mapping
PAYSIM_TYPE_MAP = {
    "TRANSFER": TransactionType.TRANSFER,
    "PAYMENT": TransactionType.PAYMENT,
    "CASH_OUT": TransactionType.CASH_OUT,
    "CASH_IN": TransactionType.CASH_IN,
    "DEBIT": TransactionType.DEBIT,
}


def load_paysim_csv(filepath: str, limit: int | None = None) -> pd.DataFrame:
    """Load PaySim dataset from CSV."""
    df = pd.read_csv(filepath, nrows=limit)
    return df


def paysim_to_transactions(df: pd.DataFrame) -> list[Transaction]:
    """Convert PaySim DataFrame rows to Transaction objects."""
    transactions = []
    for _, row in df.iterrows():
        tx = Transaction(
            transaction_id=f"TX-{row.name:08d}",
            timestamp=datetime(2025, 1, 1, row.get("step", 0) % 24),
            type=PAYSIM_TYPE_MAP.get(row["type"], TransactionType.TRANSFER),
            amount=row["amount"],
            sender_id=row["nameOrig"],
            receiver_id=row["nameDest"],
            sender_balance_before=row.get("oldbalanceOrg"),
            sender_balance_after=row.get("newbalanceOrig"),
            receiver_balance_before=row.get("oldbalanceDest"),
            receiver_balance_after=row.get("newbalanceDest"),
            is_flagged=bool(row.get("isFraud", 0)),
        )
        transactions.append(tx)
    return transactions


def load_sample_batch(filepath: str, limit: int = 100) -> TransactionBatch:
    """Load a sample batch of transactions for investigation."""
    df = load_paysim_csv(filepath, limit=limit)
    transactions = paysim_to_transactions(df)
    return TransactionBatch(
        transactions=transactions,
        alert_reason="Batch review — automated screening",
        source="paysim",
    )

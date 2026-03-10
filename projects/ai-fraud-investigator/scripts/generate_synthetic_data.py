"""
Generate synthetic transaction data with injected fraud patterns.

This script creates a small dataset for demo purposes without needing
the full PaySim dataset. Useful for quick testing and demos.

Usage: python scripts/generate_synthetic_data.py --output data/sample_transactions.csv
"""

from __future__ import annotations

import argparse
import csv
import random
from datetime import datetime, timedelta


def generate_normal_transactions(n: int = 200) -> list[dict]:
    """Generate normal-looking transactions."""
    entities = [f"C{i:04d}" for i in range(50)]
    merchants = [f"M{i:04d}" for i in range(20)]
    transactions = []

    base_time = datetime(2025, 1, 1)
    for i in range(n):
        sender = random.choice(entities)
        receiver = random.choice(merchants + entities)
        amount = round(random.lognormvariate(6, 1.5), 2)  # Log-normal distribution
        tx_type = random.choice(["TRANSFER", "PAYMENT", "CASH_OUT"])

        transactions.append({
            "step": i,
            "type": tx_type,
            "amount": min(amount, 50000),
            "nameOrig": sender,
            "oldbalanceOrg": round(random.uniform(1000, 100000), 2),
            "newbalanceOrig": 0,  # Simplified
            "nameDest": receiver,
            "oldbalanceDest": round(random.uniform(0, 50000), 2),
            "newbalanceDest": 0,
            "isFraud": 0,
            "isFlaggedFraud": 0,
        })

    return transactions


def inject_structuring(transactions: list[dict], count: int = 5) -> list[dict]:
    """Inject structuring pattern: multiple transactions just under $10k."""
    sender = "C_STRUCT_01"
    receivers = [f"M_STRUCT_{i:02d}" for i in range(count)]
    base_step = len(transactions)

    for i in range(count):
        transactions.append({
            "step": base_step + i,
            "type": "TRANSFER",
            "amount": round(random.uniform(9000, 9999), 2),
            "nameOrig": sender,
            "oldbalanceOrg": 100000,
            "newbalanceOrig": 0,
            "nameDest": receivers[i],
            "oldbalanceDest": 0,
            "newbalanceDest": 0,
            "isFraud": 1,
            "isFlaggedFraud": 0,
        })

    return transactions


def inject_round_tripping(transactions: list[dict]) -> list[dict]:
    """Inject round-tripping: A→B→C→A circular flow."""
    entities = ["C_ROUND_A", "C_ROUND_B", "C_ROUND_C"]
    amount = 25000
    base_step = len(transactions)

    for i, (sender, receiver) in enumerate(
        zip(entities, entities[1:] + entities[:1])
    ):
        transactions.append({
            "step": base_step + i,
            "type": "TRANSFER",
            "amount": round(amount * (1 - 0.01 * i), 2),  # Slight decrease
            "nameOrig": sender,
            "oldbalanceOrg": 50000,
            "newbalanceOrig": 0,
            "nameDest": receiver,
            "oldbalanceDest": 0,
            "newbalanceDest": 0,
            "isFraud": 1,
            "isFlaggedFraud": 0,
        })

    return transactions


def inject_rapid_movement(transactions: list[dict]) -> list[dict]:
    """Inject rapid fund movement: receive then immediately send out."""
    account = "C_RAPID_01"
    base_step = len(transactions)

    # Receive large amount
    transactions.append({
        "step": base_step,
        "type": "TRANSFER",
        "amount": 45000,
        "nameOrig": "C_EXT_SOURCE",
        "oldbalanceOrg": 100000,
        "newbalanceOrig": 55000,
        "nameDest": account,
        "oldbalanceDest": 100,
        "newbalanceDest": 45100,
        "isFraud": 1,
        "isFlaggedFraud": 0,
    })

    # Immediately send out
    transactions.append({
        "step": base_step + 1,
        "type": "TRANSFER",
        "amount": 44800,
        "nameOrig": account,
        "oldbalanceOrg": 45100,
        "newbalanceOrig": 300,
        "nameDest": "C_EXT_DEST",
        "oldbalanceDest": 0,
        "newbalanceDest": 44800,
        "isFraud": 1,
        "isFlaggedFraud": 0,
    })

    return transactions


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/sample_transactions.csv")
    parser.add_argument("--normal-count", type=int, default=200)
    args = parser.parse_args()

    random.seed(42)

    transactions = generate_normal_transactions(args.normal_count)
    transactions = inject_structuring(transactions)
    transactions = inject_round_tripping(transactions)
    transactions = inject_rapid_movement(transactions)

    random.shuffle(transactions)

    fieldnames = [
        "step", "type", "amount", "nameOrig", "oldbalanceOrg",
        "newbalanceOrig", "nameDest", "oldbalanceDest", "newbalanceDest",
        "isFraud", "isFlaggedFraud",
    ]

    with open(args.output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(transactions)

    fraud_count = sum(1 for t in transactions if t["isFraud"])
    print(f"Generated {len(transactions)} transactions ({fraud_count} fraudulent)")
    print(f"Saved to {args.output}")


if __name__ == "__main__":
    main()

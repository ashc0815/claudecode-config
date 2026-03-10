# Fraud Typologies Reference

This document describes the fraud patterns our system detects, designed as a reference for both the AI agents and human reviewers.

## 1. Structuring (Smurfing)

**What it is**: Breaking a large transaction into multiple smaller ones to avoid Currency Transaction Report (CTR) thresholds (typically $10,000 in the US).

**Detection signals**:
- Multiple transactions from the same sender, each just below $10,000
- Transactions clustered within a short time window (24-48 hours)
- Different recipient accounts but same beneficial owner

**Real-world example**: A customer makes 5 deposits of $9,500 each across different branches on the same day.

## 2. Round-Tripping (Circular Flows)

**What it is**: Funds moving in a circle through intermediaries and returning to the originator, often to create the appearance of legitimate business activity.

**Detection signals**:
- A→B→C→A flow pattern
- Similar amounts at each hop (minus small "fees")
- Transactions occur in rapid succession

**Real-world example**: Company A "pays" Company B for "consulting", B pays Company C for "supplies", C "invests" back into Company A.

## 3. Rapid Fund Movement (Pass-Through)

**What it is**: Account receives funds and immediately transfers them out, acting as a pass-through with no legitimate holding purpose.

**Detection signals**:
- Large inbound transfer followed by outbound transfer within minutes/hours
- Account balance returns to near-zero after each cycle
- No normal transaction history for the account

## 4. Layering

**What it is**: Creating complex chains of transactions through multiple accounts/entities to obscure the origin of funds.

**Detection signals**:
- Multiple intermediary accounts with little other activity
- Progressive amount changes at each layer
- Mixed transaction types (transfers, payments, cash-outs)

## 5. Velocity Abuse

**What it is**: Transaction frequency far exceeding the account's normal pattern.

**Detection signals**:
- Transaction count >3x historical average
- Sudden spike after period of low activity
- High-frequency small transactions (potential testing before large fraud)

## 6. Dormant Account Activation

**What it is**: A previously inactive account suddenly shows high-value activity.

**Detection signals**:
- No transactions for 90+ days, then large transfer
- Recent changes to account ownership or contact details
- First transaction is high-value outgoing transfer

---

## Regulatory Context

- **BSA/AML**: Bank Secrecy Act requires financial institutions to report suspicious activity
- **CTR Threshold**: $10,000 in the US (structuring specifically targets this)
- **SAR Filing**: Must be filed within 30 days of detecting suspicious activity
- **Explainability Requirement**: Regulators require clear documentation of why activity was flagged

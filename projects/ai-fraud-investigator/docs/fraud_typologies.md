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

## AI-Generated Fraud (Emerging Threats)

As generative AI tools become widely accessible, a new category of fraud leverages AI as an attack vector. Our system detects three key AI-assisted patterns:

### 7. Synthetic Identity Fraud

**What it is**: Using AI to fabricate composite identities — combining real and fake PII (SSN, address, phone) to create accounts that pass traditional KYC checks.

**Detection signals**:
- New account with rapid credit-building activity followed by a large cash-out (bust-out pattern)
- Multiple accounts share overlapping PII fragments (partial address, phone, or SSN overlap)
- Identity elements have no historical footprint in public records or credit bureaus
- Account behavior is suspiciously "textbook perfect" — legitimate patterns that are too clean to be natural

**Real-world example**: An attacker generates 20 synthetic identities, opens accounts, builds credit scores over 6 months with small regular payments, then maxes out all credit lines and disappears.

### 8. Deepfake Authorization Fraud

**What it is**: Using AI-generated voice clones or video deepfakes to impersonate authorized signers or executives and approve high-value transactions.

**Detection signals**:
- Voice/video-authorized transaction with amount 5x+ above account's historical average
- Authorization channel inconsistent with customer's established behavior patterns
- Multiple high-value voice/video authorizations in short succession
- Authorization metadata anomalies (unusual call duration, audio quality artifacts, atypical session timing)

**Real-world example**: An attacker clones a CFO's voice using publicly available earnings call recordings and calls the bank to authorize a $35M wire transfer to an overseas account.

### 9. AI-Assisted Social Engineering

**What it is**: Using LLMs to craft highly personalized phishing emails or messages that manipulate account holders into authorizing fraudulent transfers.

**Detection signals**:
- Sudden wire transfer to a new beneficiary immediately after account credential changes
- Transaction memo or notes contain urgency language typical of social engineering ("urgent", "confidential", "CEO request")
- Account shows login from new device/location shortly before the transaction
- Multiple unrelated victims sending funds to the same beneficiary within a short time window

**Real-world example**: An attacker uses an LLM to generate personalized emails mimicking a company's CEO, instructing 12 employees across different departments to wire funds to an "acquisition escrow account."

---

## Regulatory Context

- **BSA/AML**: Bank Secrecy Act requires financial institutions to report suspicious activity
- **CTR Threshold**: $10,000 in the US (structuring specifically targets this)
- **SAR Filing**: Must be filed within 30 days of detecting suspicious activity
- **Explainability Requirement**: Regulators require clear documentation of why activity was flagged

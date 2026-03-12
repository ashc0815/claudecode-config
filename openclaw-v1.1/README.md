# OpenClaw V1.1 — HITL (Human-in-the-Loop) Edition

> AI 做 90% 的苦活，人做 10% 的判断，人的每个判断反过来让 AI 更准。

AI-powered expense audit system with human feedback loops for continuous improvement.

## Architecture

```
Employee uploads voucher
    │
    ▼
┌─────────────────────────────────────────────┐
│  OpenClaw V1.1                              │
│                                             │
│  ocr.py ──► audit.py ──► rules.py           │
│  (Mistral)  (Claude)    (10 rules,          │
│                          dynamic weights)   │
│       │                                     │
│       ▼                                     │
│  notify.py ──► Feishu Interactive Card      │
│       │        [Confirm] [FP] [Investigate] │
│       │                                     │
│       ▼        ┌─ V1.1 HITL Loop ─┐        │
│  feedback.py ◄─┤ User clicks btn  │        │
│       │        └──────────────────┘        │
│       ▼                                     │
│  learner.py ──► Weekly auto-tuning          │
│                 (admin approval required)   │
└─────────────────────────────────────────────┘
```

## Files (7 Python files, ~2100 lines)

| File | Lines | Description |
|------|-------|-------------|
| `app/main.py` | ~250 | FastAPI, 5 endpoints + health check |
| `app/ocr.py` | ~80 | Mistral OCR API wrapper |
| `app/audit.py` | ~150 | Claude Sonnet analysis + prompt versioning |
| `app/rules.py` | ~350 | 10 parameterized rules with dynamic weights |
| `app/feedback.py` | ~130 | HITL feedback collection + impact preview |
| `app/learner.py` | ~300 | Weekly learning cycle + rule auto-tuning |
| `app/notify.py` | ~280 | Feishu interactive cards (audit, report, proposals) |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/upload` | Upload voucher image for audit |
| GET | `/results` | Query audit results by status |
| GET | `/results/{audit_id}` | Get specific audit result |
| POST | `/feedback` | Submit HITL feedback (V1.1 enhanced) |
| GET | `/metrics` | System performance metrics |
| POST | `/rules/approve` | Approve/reject rule adjustments |
| POST | `/learning/run` | Manually trigger learning cycle |
| GET | `/health` | Health check |

## Database (6 tables in Supabase)

| Table | Purpose |
|-------|---------|
| `audit_results` | OCR + AI + rule results per voucher |
| `feedback` | User feedback with per-rule annotations |
| `audit_log` | Immutable operation log |
| `rule_params` | Dynamic rule parameters (V1.1) |
| `prompt_versions` | Prompt A/B testing (V1.1) |
| `weekly_metrics` | Weekly performance snapshots (V1.1) |

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 3. Run database migration
# Execute migrations/001_init_schema.sql in Supabase SQL editor

# 4. Start server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## HITL Learning Cycle

```
Weekly (Sunday 23:00):
  1. Collect unconsumed feedback
  2. Compute per-rule precision
  3. Generate adjustment proposals (rules with precision < 40%)
  4. Send proposals to admin via Feishu
  5. Admin approves → rules updated
  6. Write weekly metrics snapshot
  7. Send weekly report to admin

Safety:
  - Max 3 rules adjusted per week
  - All adjustments require admin approval
  - Each rule has min_weight floor (can't be fully disabled)
  - All changes logged in immutable audit_log
```

## Key Metrics

| Metric | Target | Red Line |
|--------|--------|----------|
| Confirmed Anomaly Rate | ≥ 40% | < 20% |
| Precision (weekly) | Trending up | 2 weeks declining |
| False Positive Rate | ≤ 25% | > 40% → pause system |
| Feedback Coverage | ≥ 70% | < 50% → user disengagement |

## Cost

```
Supabase: Free tier
Railway: $5/month
Claude API: ~$30/month (1000 vouchers)
Mistral OCR: ~$10/month (1000 vouchers)
Total: ~$45/month
```

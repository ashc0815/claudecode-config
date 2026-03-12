# OpenClaw V1.1 — HITL (Human-in-the-Loop) Edition

> SAP Concur 智能审核增强层 — AI 做 90% 的苦活，人做 10% 的判断，每个判断让 AI 更准。

## Core Flow: Employee → OpenClaw → Concur → Post-Audit

```
                    ┌────────────────────────────────────────────────────────┐
 员工上传凭证 ──►   │  OpenClaw V1.1 (事前审核)                              │
                    │                                                        │
                    │  ocr.py ──► audit.py ──► rules.py ──► Decision         │
                    │  (Mistral)  (Claude)    (10 rules)                     │
                    │                            │                           │
                    │              ┌──────────────┼──────────────┐           │
                    │              ▼              ▼              ▼           │
                    │           PASS(70%)     WARN(25%)      FAIL(5%)       │
                    │              │              │              │           │
                    │              │              ▼              ▼           │
                    │              │       飞书通知财务      打回给员工       │
                    │              │       [确认][误报]                      │
                    │              │         │   │                           │
                    │              │    通过──┘   └──打回                    │
                    │              │     │                                   │
                    │              ▼     ▼                                   │
                    │         concur.py ──────────────────────────►┐         │
                    │         (push to Concur API)                 │         │
                    └─────────────────────────────────────────────┼─────────┘
                                                                  │
                    ┌─────────────────────────────────────────────┼─────────┐
                    │  SAP Concur (审批流)                         │         │
                    │                                              ▼         │
                    │  经理审批 → 财务审批 → 付款执行                         │
                    │         │                                              │
                    └─────────┼──────────────────────────────────────────────┘
                              │
                    ┌─────────▼──────────────────────────────────────────────┐
                    │  OpenClaw (事后审计, 每小时 cron)                        │
                    │                                                        │
                    │  concur.py ◄── 拉取 Concur 审批后数据                   │
                    │       │                                                │
                    │       ▼                                                │
                    │  交叉核对:                                              │
                    │  · 经理改了金额？(Concur ¥4,500 vs 原件 ¥4,999)        │
                    │  · 报销被驳回？                                         │
                    │  · 日期/供应商不一致？                                   │
                    │       │                                                │
                    │       ▼                                                │
                    │  异常 → 飞书告警 → 人工跟进                              │
                    └────────────────────────────────────────────────────────┘

                    ┌────────────────────────────────────────────────────────┐
                    │  HITL 学习循环 (每周日)                                  │
                    │                                                        │
                    │  财务反馈 → learner.py → 规则精准率分析                   │
                    │       → 低精准率规则降权建议 → 飞书通知管理员              │
                    │       → 管理员批准 → 规则更准 → 下周误报更少 🔄          │
                    └────────────────────────────────────────────────────────┘
```

## Files (8 Python files, ~2500 lines)

| File | Description |
|------|-------------|
| `app/main.py` | FastAPI, 8 endpoints + health check |
| `app/ocr.py` | Mistral OCR API wrapper |
| `app/audit.py` | Claude Sonnet analysis + prompt A/B testing |
| `app/rules.py` | 10 parameterized rules with dynamic weights |
| `app/concur.py` | SAP Concur API connector (OAuth2, push/pull/reconcile) |
| `app/feedback.py` | HITL feedback collection + rule impact preview |
| `app/learner.py` | Weekly learning cycle + rule auto-tuning |
| `app/notify.py` | Feishu interactive cards (audit result, weekly report, proposals) |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/upload` | Upload voucher → OCR → AI → Rules → Concur/Feishu |
| GET | `/results` | Query audit results by status |
| GET | `/results/{audit_id}` | Get specific audit result |
| POST | `/feedback` | Submit HITL feedback (per-rule annotations) |
| GET | `/metrics` | Precision trends, rule performance, pending adjustments |
| POST | `/rules/approve` | Approve/reject rule adjustment proposals |
| POST | `/learning/run` | Manually trigger weekly learning cycle |
| POST | `/concur/push/{audit_id}` | Push approved WARN item to Concur |
| POST | `/concur/reconcile` | Trigger post-audit cross-validation |
| GET | `/health` | Health check |

## Database (6 tables in Supabase)

| Table | Purpose |
|-------|---------|
| `audit_results` | OCR + AI + rules + Concur IDs per voucher |
| `feedback` | User feedback with per-rule annotations |
| `audit_log` | Immutable operation log (audit trail) |
| `rule_params` | Dynamic rule parameters (V1.1 HITL) |
| `prompt_versions` | Prompt A/B testing (V1.1 HITL) |
| `weekly_metrics` | Weekly performance snapshots (V1.1 HITL) |

## Quick Start

```bash
# 1. Install
pip install -r requirements.txt

# 2. Configure (fill in 5 services: Supabase, Anthropic, Mistral, Concur, Feishu)
cp .env.example .env

# 3. Database
# Paste migrations/001_init_schema.sql into Supabase SQL Editor and run

# 4. Start
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
# Open http://localhost:8000/docs for Swagger API docs
```

## External Services

| Service | Purpose | Cost |
|---------|---------|------|
| Supabase | PostgreSQL + Auth + Storage | Free |
| Anthropic API | Claude Sonnet for audit analysis | ~$30/mo |
| Mistral API | OCR text extraction | ~$10/mo |
| SAP Concur API | Expense report CRUD + approval flow | Per client license |
| Feishu | Notifications + HITL feedback UI | Free |

## Concur Integration Details

### Obtaining Concur API Credentials

1. Register app at [SAP Concur App Center](https://developer.concur.com)
2. Get `client_id` + `client_secret`
3. Complete OAuth2 flow to get `refresh_token`
4. Add to `.env`

### Data Flow

**Upstream (OpenClaw → Concur):**
- Create expense report
- Create expense entry (maps OCR fields to Concur fields)
- Upload receipt image
- Submit report into approval workflow
- Audit metadata stored in Custom1-4 fields

**Downstream (Concur → OpenClaw):**
- Hourly cron pulls approved/processed reports
- Cross-validates against original voucher
- Detects: amount changes, rejections, field mismatches
- Alerts finance via Feishu if discrepancies found

## Key Metrics

| Metric | Target | Red Line |
|--------|--------|----------|
| Confirmed Anomaly Rate | ≥ 40% | < 20% |
| Precision (weekly) | Trending up | 2 weeks declining |
| False Positive Rate | ≤ 25% | > 40% → pause |
| Feedback Coverage | ≥ 70% | < 50% |

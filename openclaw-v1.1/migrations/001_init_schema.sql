-- OpenClaw V1.1 HITL Database Schema
-- Run against Supabase PostgreSQL

-- ============================================
-- Table 1: audit_results
-- ============================================
CREATE TABLE IF NOT EXISTS audit_results (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  audit_id        TEXT UNIQUE NOT NULL,
  created_at      TIMESTAMPTZ DEFAULT NOW(),

  -- Document info
  document_url    TEXT NOT NULL,
  ocr_raw_text    TEXT,
  ocr_structured  JSONB NOT NULL DEFAULT '{}',
  ocr_confidence  FLOAT,

  -- Audit result
  risk_level      TEXT NOT NULL CHECK (risk_level IN ('pass', 'warn', 'fail')),
  risk_score      INTEGER CHECK (risk_score >= 0 AND risk_score <= 100),
  risk_flags      JSONB NOT NULL DEFAULT '[]',
  ai_reasoning    TEXT,

  -- V1.1 fields
  prompt_version  TEXT DEFAULT 'v1.0',
  rule_params_snapshot JSONB,
  processing_time_ms   INTEGER,

  -- Concur integration
  concur_report_id  TEXT,               -- Concur report ID after push
  concur_entry_id   TEXT,               -- Concur expense entry ID
  concur_status     TEXT DEFAULT 'not_pushed'
                    CHECK (concur_status IN ('not_pushed', 'submitted', 'approved', 'rejected', 'paid')),
  concur_synced_at  TIMESTAMPTZ,

  -- Status
  status          TEXT DEFAULT 'pending_review'
                  CHECK (status IN ('pending_review', 'confirmed', 'false_positive', 'investigating', 'pass')),
  resolved_at     TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_audit_results_status ON audit_results(status);
CREATE INDEX IF NOT EXISTS idx_audit_results_risk ON audit_results(risk_level);
CREATE INDEX IF NOT EXISTS idx_audit_results_created ON audit_results(created_at);

-- ============================================
-- Table 2: feedback (V1.1 expanded)
-- ============================================
CREATE TABLE IF NOT EXISTS feedback (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  audit_id              TEXT NOT NULL REFERENCES audit_results(audit_id),
  created_at            TIMESTAMPTZ DEFAULT NOW(),

  -- Core feedback
  action                TEXT NOT NULL CHECK (action IN ('confirmed', 'false_positive', 'investigate')),
  reviewer_id           TEXT NOT NULL,
  reviewer_role         TEXT,

  -- V1.1: Structured feedback
  false_positive_reason TEXT,
  corrected_risk_level  TEXT CHECK (corrected_risk_level IN ('none', 'low', 'medium', 'high')),
  per_flag_feedback     JSONB,
  free_text_note        TEXT,
  time_spent_seconds    INTEGER,

  -- V1.1: Learning markers
  used_for_learning     BOOLEAN DEFAULT FALSE,
  learning_batch_id     TEXT
);

CREATE INDEX IF NOT EXISTS idx_feedback_audit ON feedback(audit_id);
CREATE INDEX IF NOT EXISTS idx_feedback_action ON feedback(action);
CREATE INDEX IF NOT EXISTS idx_feedback_learning ON feedback(used_for_learning) WHERE used_for_learning = FALSE;

-- ============================================
-- Table 3: audit_log (immutable)
-- ============================================
CREATE TABLE IF NOT EXISTS audit_log (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at  TIMESTAMPTZ DEFAULT NOW(),
  event_type  TEXT NOT NULL,
  actor       TEXT NOT NULL,
  audit_id    TEXT,
  details     JSONB NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_audit_log_event ON audit_log(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_log_audit ON audit_log(audit_id);

-- Revoke UPDATE/DELETE on audit_log for application role
-- (uncomment when deploying)
-- REVOKE UPDATE, DELETE ON audit_log FROM anon, authenticated;

-- ============================================
-- Table 4: rule_params (V1.1 new)
-- ============================================
CREATE TABLE IF NOT EXISTS rule_params (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  rule_name         TEXT NOT NULL,
  param_name        TEXT NOT NULL,
  param_value       JSONB NOT NULL,

  source            TEXT NOT NULL CHECK (source IN ('manual', 'auto_tuned', 'default')),
  previous_value    JSONB,
  adjustment_reason TEXT,

  version           INTEGER DEFAULT 1,
  effective_from    TIMESTAMPTZ DEFAULT NOW(),
  effective_until   TIMESTAMPTZ,
  created_by        TEXT DEFAULT 'system',

  UNIQUE(rule_name, param_name, version)
);

CREATE INDEX IF NOT EXISTS idx_rule_params_active
  ON rule_params(rule_name, effective_until)
  WHERE effective_until IS NULL;

-- ============================================
-- Table 5: prompt_versions (V1.1 new)
-- ============================================
CREATE TABLE IF NOT EXISTS prompt_versions (
  id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  version_tag          TEXT UNIQUE NOT NULL,
  prompt_text          TEXT NOT NULL,
  created_at           TIMESTAMPTZ DEFAULT NOW(),

  total_uses           INTEGER DEFAULT 0,
  confirmed_count      INTEGER DEFAULT 0,
  false_positive_count INTEGER DEFAULT 0,
  precision            FLOAT,

  status               TEXT DEFAULT 'active' CHECK (status IN ('active', 'testing', 'retired')),
  traffic_pct          INTEGER DEFAULT 100 CHECK (traffic_pct >= 0 AND traffic_pct <= 100),
  notes                TEXT
);

-- ============================================
-- Table 6: weekly_metrics (V1.1 new)
-- ============================================
CREATE TABLE IF NOT EXISTS weekly_metrics (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  week_start      DATE NOT NULL UNIQUE,
  created_at      TIMESTAMPTZ DEFAULT NOW(),

  total_audits    INTEGER DEFAULT 0,
  pass_count      INTEGER DEFAULT 0,
  warn_count      INTEGER DEFAULT 0,
  fail_count      INTEGER DEFAULT 0,

  feedback_count          INTEGER DEFAULT 0,
  confirmed_anomalies     INTEGER DEFAULT 0,
  false_positives         INTEGER DEFAULT 0,
  precision               FLOAT,
  feedback_rate            FLOAT,

  avg_review_time_seconds  FLOAT,
  avg_processing_time_ms   FLOAT,

  rule_trigger_distribution JSONB DEFAULT '{}',
  false_positive_by_rule    JSONB DEFAULT '{}',
  prompt_version_used       TEXT
);

-- ============================================
-- Seed: Default prompt version
-- ============================================
INSERT INTO prompt_versions (version_tag, prompt_text, status, traffic_pct, notes)
VALUES (
  'v1.0',
  '你是一个专业的财务审计助手。请分析以下凭证的 OCR 提取结果，识别潜在的财务风险。

输入：OCR 提取的凭证文字内容
输出：严格按照以下 JSON 格式返回

{
  "vendor_name": "供应商名称",
  "amount": 数字金额,
  "currency": "CNY",
  "invoice_number": "发票号",
  "invoice_date": "YYYY-MM-DD",
  "expense_type": "费用类型",
  "items": [{"description": "项目描述", "amount": 金额}],
  "risk_flags": [
    {
      "rule": "规则标识符",
      "severity": "critical/high/medium/low",
      "confidence": 0.0-1.0,
      "detail": "具体发现描述"
    }
  ],
  "ai_reasoning": "综合分析说明",
  "citations": ["引用凭证中的具体文字"]
}

重点关注：
1. 金额是否接近常见审批阈值（如 ¥5,000 / ¥10,000 / ¥50,000）
2. 发票日期是否为周末或节假日
3. 金额是否为整数（无零头可能是虚构）
4. 供应商信息是否完整
5. 是否有明显的费用类型不匹配',
  'active',
  100,
  'Initial production prompt for V1.0'
)
ON CONFLICT (version_tag) DO NOTHING;

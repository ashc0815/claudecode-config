-- Fin-Wellness Local-First Schema (SQLite)
-- All data stays on device. No cloud dependency.

-- ============================================
-- Accounts (银行卡、投资账户、信用卡、贷款)
-- ============================================
CREATE TABLE IF NOT EXISTS accounts (
  id            TEXT PRIMARY KEY,
  name          TEXT NOT NULL,
  account_type  TEXT NOT NULL CHECK (account_type IN ('cash', 'savings', 'credit_card', 'investment', 'loan', 'other')),
  balance       REAL DEFAULT 0.0,
  currency      TEXT DEFAULT 'CNY',
  institution   TEXT DEFAULT '',
  is_asset      INTEGER DEFAULT 1,  -- 1=asset, 0=liability
  notes         TEXT DEFAULT '',
  created_at    TEXT DEFAULT (datetime('now')),
  updated_at    TEXT DEFAULT (datetime('now'))
);

-- ============================================
-- Transactions (每一笔收支)
-- ============================================
CREATE TABLE IF NOT EXISTS transactions (
  id                    TEXT PRIMARY KEY,
  date                  TEXT NOT NULL,  -- YYYY-MM-DD
  amount                REAL NOT NULL,
  tx_type               TEXT NOT NULL CHECK (tx_type IN ('expense', 'income', 'transfer')),
  category              TEXT DEFAULT '',
  subcategory           TEXT DEFAULT '',
  description           TEXT DEFAULT '',
  account_id            TEXT REFERENCES accounts(id),
  counterparty          TEXT DEFAULT '',
  source                TEXT DEFAULT '',  -- alipay_csv, wechat_csv, manual, ocr
  tags                  TEXT DEFAULT '[]',  -- JSON array
  ai_category_confidence REAL DEFAULT 0.0,
  created_at            TEXT DEFAULT (datetime('now')),
  import_batch_id       TEXT DEFAULT ''  -- 同一次导入的标记
);

CREATE INDEX IF NOT EXISTS idx_tx_date ON transactions(date);
CREATE INDEX IF NOT EXISTS idx_tx_category ON transactions(category);
CREATE INDEX IF NOT EXISTS idx_tx_type ON transactions(tx_type);

-- ============================================
-- Assets (投资持仓：基金、股票等)
-- ============================================
CREATE TABLE IF NOT EXISTS assets (
  id              TEXT PRIMARY KEY,
  name            TEXT NOT NULL,
  asset_type      TEXT DEFAULT '',  -- fund, stock, bond, crypto, real_estate
  ticker          TEXT DEFAULT '',  -- 基金/股票代码
  shares          REAL DEFAULT 0.0,
  cost_basis      REAL DEFAULT 0.0,
  current_value   REAL DEFAULT 0.0,
  last_updated    TEXT,
  account_id      TEXT REFERENCES accounts(id),
  created_at      TEXT DEFAULT (datetime('now'))
);

-- ============================================
-- Categories (分类规则 — 用户可自定义)
-- ============================================
CREATE TABLE IF NOT EXISTS categories (
  id          TEXT PRIMARY KEY,
  name        TEXT NOT NULL UNIQUE,  -- e.g. "餐饮.外卖"
  parent      TEXT DEFAULT '',       -- "餐饮"
  keywords    TEXT DEFAULT '[]',     -- JSON: ["美团", "饿了么", "肯德基"]
  is_system   INTEGER DEFAULT 0,    -- 系统预设 vs 用户自定义
  icon        TEXT DEFAULT ''
);

-- ============================================
-- Goals (长期财务目标)
-- ============================================
CREATE TABLE IF NOT EXISTS goals (
  id              TEXT PRIMARY KEY,
  title           TEXT NOT NULL,
  target_amount   REAL,
  current_amount  REAL DEFAULT 0.0,
  deadline        TEXT,  -- YYYY-MM-DD
  status          TEXT DEFAULT 'active' CHECK (status IN ('active', 'completed', 'paused', 'abandoned')),
  created_at      TEXT DEFAULT (datetime('now')),
  updated_at      TEXT DEFAULT (datetime('now'))
);

-- ============================================
-- Commitments (微行动承诺 — 核心循环)
-- ============================================
CREATE TABLE IF NOT EXISTS commitments (
  id                TEXT PRIMARY KEY,
  goal_id           TEXT REFERENCES goals(id),
  action            TEXT NOT NULL,           -- "周二/周四带饭"
  category          TEXT DEFAULT '',         -- 关联消费分类
  expected_saving   REAL DEFAULT 0.0,
  start_date        TEXT NOT NULL,
  end_date          TEXT,
  status            TEXT DEFAULT 'active' CHECK (status IN ('active', 'achieved', 'missed', 'adjusted')),
  follow_up_result  TEXT DEFAULT '',
  actual_saving     REAL DEFAULT 0.0,
  created_at        TEXT DEFAULT (datetime('now'))
);

-- ============================================
-- User Profile (用户画像 — 记忆层长期)
-- ============================================
CREATE TABLE IF NOT EXISTS user_profile (
  key    TEXT PRIMARY KEY,
  value  TEXT NOT NULL,
  updated_at TEXT DEFAULT (datetime('now'))
);

-- ============================================
-- Memory: Mid-term (消费习惯画像)
-- ============================================
CREATE TABLE IF NOT EXISTS habit_profile (
  id            TEXT PRIMARY KEY,
  category      TEXT NOT NULL,
  metric        TEXT NOT NULL,       -- 'monthly_avg', 'weekly_pattern', 'trend'
  value         TEXT NOT NULL,       -- JSON
  period        TEXT DEFAULT '',     -- "2026-Q1", "2026-03"
  updated_at    TEXT DEFAULT (datetime('now'))
);

-- ============================================
-- Weekly Snapshots (周报快照)
-- ============================================
CREATE TABLE IF NOT EXISTS weekly_snapshots (
  id              TEXT PRIMARY KEY,
  week_start      TEXT NOT NULL,
  week_end        TEXT NOT NULL,
  total_income    REAL DEFAULT 0.0,
  total_expense   REAL DEFAULT 0.0,
  net_worth       REAL DEFAULT 0.0,
  data            TEXT DEFAULT '{}',  -- Full JSON snapshot
  created_at      TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_weekly_start ON weekly_snapshots(week_start);

-- ============================================
-- Conversation History (对话历史 — 记忆层短期)
-- ============================================
CREATE TABLE IF NOT EXISTS conversations (
  id          TEXT PRIMARY KEY,
  role        TEXT NOT NULL,  -- 'user' or 'assistant'
  content     TEXT NOT NULL,
  tool_calls  TEXT DEFAULT '[]',  -- JSON: tools the AI called
  created_at  TEXT DEFAULT (datetime('now'))
);

-- ============================================
-- Seed: Default categories (系统预设分类)
-- ============================================
INSERT OR IGNORE INTO categories (id, name, parent, keywords, is_system) VALUES
  ('cat_food',      '餐饮',       '',     '[]', 1),
  ('cat_food_out',  '餐饮.外卖',  '餐饮', '["美团","饿了么","星巴克","瑞幸"]', 1),
  ('cat_food_dine', '餐饮.堂食',  '餐饮', '["海底捞","必胜客","肯德基","麦当劳"]', 1),
  ('cat_food_groc', '餐饮.买菜',  '餐饮', '["盒马","叮咚买菜","美团买菜","山姆"]', 1),
  ('cat_transport', '交通',       '',     '[]', 1),
  ('cat_trans_taxi','交通.打车',   '交通', '["滴滴","高德打车","花小猪","T3出行"]', 1),
  ('cat_trans_pub', '交通.公共',   '交通', '["地铁","公交","北京一卡通"]', 1),
  ('cat_shopping',  '购物',       '',     '["淘宝","京东","拼多多","天猫"]', 1),
  ('cat_housing',   '住房',       '',     '["房租","物业","水电","燃气"]', 1),
  ('cat_entertain', '娱乐',       '',     '["电影","游戏","视频会员","音乐会员"]', 1),
  ('cat_health',    '医疗健康',   '',     '["药店","医院","体检"]', 1),
  ('cat_education', '教育',       '',     '["课程","书","培训"]', 1),
  ('cat_salary',    '工资',       '',     '["工资","薪水"]', 1),
  ('cat_invest',    '投资收益',   '',     '["分红","利息","基金收益"]', 1),
  ('cat_transfer',  '转账',       '',     '["转账","还款"]', 1);

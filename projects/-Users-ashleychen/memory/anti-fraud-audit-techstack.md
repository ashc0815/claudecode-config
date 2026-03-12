# AI Anti-Fraud 审计助手 — 4 周 MVP 落地方案

> 产品定位：帮 SME「看清每一笔账」的智能审计空间
> 目标用户：Finance Controller / CFO（团队小、预算有限、无内审部门）
> 现有技术栈：飞书 + Salesforce
> 约束：4 周上线 MVP，上线后持续迭代

---

## 核心原则：砍到只剩刀刃

MVP 只做一件事做透：**上传凭证 → AI 全量扫描 → 标出有问题的那几笔**。
动态风险画像、图谱分析、Salesforce 同步——全部 V2 再说。

---

## 4 周 Sprint 计划

### Week 1：骨架搭建

**目标：凭证上传 → OCR 提取 → 结构化数据入库**

| 任务 | 技术选型 | 交付物 |
|---|---|---|
| 项目初始化 | Next.js 15 + FastAPI + PostgreSQL + Docker Compose | 一键 `docker compose up` 跑通 |
| 凭证上传 | Next.js 页面 + S3-compatible 存储（Cloudflare R2，免费 10GB） | 拖拽上传发票/收据/银行流水 |
| OCR + 字段提取 | Mistral OCR API → Claude Sonnet 4.6 Structured Output | JSON: {供应商, 金额, 日期, 税号, 行项目...} |
| 数据模型 | PostgreSQL: vouchers, line_items, scan_results | Schema + Alembic migration |

```
技术栈：
├── 前端: Next.js 15 + shadcn/ui + TailwindCSS
├── 后端: Python FastAPI（async）
├── DB: PostgreSQL（Supabase 免费 tier 或 Docker 自建）
├── 文件: Cloudflare R2（S3 兼容，免费额度够 MVP）
├── OCR: Mistral OCR API（$1/1000 页）
└── LLM: Claude Sonnet 4.6（字段提取 + 审计推理）
```

### Week 2：AI 审计引擎

**目标：每笔交易给出风险标记 + 置信度 + 可解释理由**

| 任务 | 实现方式 | 说明 |
|---|---|---|
| 规则引擎 | Python 硬编码 10 条高频审计规则 | 不用框架，if/else 足够 |
| Claude 审计推理 | Prompt Engineering + Structured Output | 每笔交易出: risk_level / confidence / reason / audit_note |
| 批量处理 | FastAPI Background Tasks + Redis Queue (可选) | 100 张凭证并发扫描 |
| 结果页面 | Next.js 表格：按风险等级排序，红/黄/绿标记 | 一眼看到哪些有问题 |

**10 条 MVP 审计规则（硬编码即可）：**
```python
RULES = [
    "金额为整数且 > 5000（虚假发票常见特征）",
    "周末/节假日开具的发票",
    "同一供应商同日多笔接近审批阈值的拆单",
    "税号格式校验不通过",
    "金额与行项目合计不一致",
    "供应商名称模糊匹配到黑名单",
    "连续编号发票（批量伪造特征）",
    "开票日期晚于付款日期",
    "同一报销人短期内高频提交",
    "金额显著偏离同类历史均值（>2σ）",
]
```

### Week 3：飞书集成 + 通知闭环

**目标：审计结果自动推飞书，CFO 可一键处理**

| 任务 | 实现方式 | 说明 |
|---|---|---|
| 飞书机器人通知 | 飞书 OpenAPI Webhook | 高风险凭证即时推送到审计群 |
| 飞书多维表格同步 | 飞书 Bitable API | 审计结果自动写入，CFO 手机可查 |
| 消息卡片交互 | 飞书 Interactive Card | "查看详情 / 标记已处理 / 升级调查" 按钮 |
| 简易审批流 | 飞书审批 API（如果时间够） | 高风险项需 CFO 确认后才能放行——可 V1.1 |

### Week 4：打磨 + 试用 + 修 Bug

**目标：5 个真实客户跑通完整流程**

| 任务 | 说明 |
|---|---|
| Dashboard 打磨 | 审计概览页：扫描总数 / 异常率 / Top 风险供应商 |
| 错误处理 | OCR 识别失败的 fallback（人工标注入口） |
| 权限 | 简单的 API Key 认证（别搞 OAuth，MVP 够了） |
| 部署 | Railway / Fly.io 一键部署（或客户自己的服务器 Docker） |
| 客户试用 | 拿真实凭证跑，收集反馈，记录 V2 需求 |

---

## 最终技术栈（精简版）

```
┌─────────────────────────────────────────────┐
│                   前端                        │
│  Next.js 15 + shadcn/ui + TailwindCSS        │
│  · 凭证上传页                                 │
│  · 审计结果表格（红/黄/绿）                     │
│  · 概览 Dashboard                             │
└──────────────────┬──────────────────────────┘
                   │ REST API
┌──────────────────┴──────────────────────────┐
│                   后端                        │
│  Python FastAPI                               │
│  · /upload    → 存文件 + 触发 OCR 管线         │
│  · /scan      → 规则引擎 + Claude 审计         │
│  · /results   → 查询审计结果                   │
│  · /webhook   → 飞书通知推送                   │
└──────┬───────────┬──────────┬────────────────┘
       │           │          │
  Mistral OCR   Claude    飞书 API
  (文档提取)    Sonnet 4.6  (通知+表格)
               (审计推理)
       │           │          │
┌──────┴───────────┴──────────┴────────────────┐
│                   数据层                       │
│  PostgreSQL          Cloudflare R2            │
│  (交易+审计结果)      (原始凭证文件)            │
└─────────────────────────────────────────────┘
```

### 成本估算（MVP 阶段月均）

| 项目 | 费用 |
|---|---|
| Claude Sonnet 4.6 API | ~$50-100（1000 笔/月） |
| Mistral OCR API | ~$10（1000 页/月） |
| Supabase PostgreSQL | $0（免费 tier） |
| Cloudflare R2 | $0（10GB 免费） |
| Railway 部署 | ~$5-20 |
| 飞书 API | $0（100 万次/月免费） |
| **合计** | **~$65-130/月** |

---

## 明确不做（V2+ 再考虑）

| 功能 | 为什么不做 | 什么时候做 |
|---|---|---|
| 动态风险画像 | 需要 3 个月以上历史数据才有意义 | V2：积累数据后 |
| 图谱分析（Neo4j） | 过早优化；MVP 阶段供应商数量有限 | V3：客户量起来后 |
| Salesforce 同步 | 增加集成复杂度，不影响核心价值验证 | V2：PMF 确认后 |
| 像素级伪造检测 | Arya.ai 集成成本高；先用规则+LLM 覆盖 80% | V2：有真实伪造案例后 |
| 多租户/SaaS | MVP 先服务单客户 | V3：商业化阶段 |
| OAuth / SSO | API Key 够用 | V2 |
| 移动端 | 飞书消息卡片已覆盖移动场景 | 不急 |

---

## V1 → V2 迭代路线（上线后）

```
V1（Week 4 上线）
  全量 OCR 扫描 + 10 条规则 + Claude 审计 + 飞书通知
    │
V1.1（上线后 2 周）
  基于客户反馈补规则 + 飞书审批流 + 批量导入
    │
V1.2（上线后 1 月）
  历史数据分析 → 简单统计基线（均值±2σ）→ 偏差预警
    │
V2（上线后 2-3 月）
  独立 Dashboard + Salesforce 供应商同步 + 多租户
    │
V3（上线后 4-6 月）
  Neo4j 图谱 + LSTM 动态基线 + 伪造检测 + SaaS 商业化
```

---

*Updated: 2026-03-12 | 4-Week MVP Plan | Ashley Chen — Product Thinking × AI in Finance*

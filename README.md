# AI Anti-fraud — SAP Concur 智能审核增强层

> AI-powered expense audit & compliance system for multinational enterprises in China

---

## What is AI Anti-fraud?

AI Anti-fraud 是 SAP Concur 的**前置智能审核层**，面向在华跨国企业（医药、零售等）。

**核心定位**：员工报销的第一个 contact point — 审核通过后才进入 Concur 审批流。

```
员工 ──► AI Anti-fraud（OCR + 规则校验 + AI 审核）──► Concur（审批流）
              ↑                                        │
              └──── 拉取结构化数据做事后审计 ◄───────────┘
```

### Why AI Anti-fraud?

| Concur 能做的 | AI Anti-fraud 做的（Concur 做不了的） |
|---|---|
| 等级不同 → 限额不同 | 非出差晚9点后打车才可报销 |
| 基础金额审批 | 一个员工只能报 2 个手机号 |
| 标准审批流转 | 同日同供应商多笔 = 拆单检测 |
| 结构化数据审批 | 凭证原件 OCR + AI 核对 |
| 5% 抽查 | **100% 全量凭证审核** |

---

## Docs

| # | Document | Description |
|---|---|---|
| 01 | [Product Design](docs/01-product-design.md) | Concur 增强层产品设计：功能模块、规则引擎、MVP 路线 |
| 02 | [Product Architecture](docs/02-product-architecture.md) | 产品架构全景图、AI 分层设计、面试叙事框架 |
| 03 | [Integrated Flow Diagram](docs/03-integrated-flow-diagram.md) | 端到端集成流程图：员工→AI anti-fraud→Concur→事后审计 |
| 04 | [Tech Stack & GitHub References](docs/04-tech-stack-references.md) | 技术栈选型 + 20+ 开源项目参考 + 可复用组件 |
| 05 | [Anti-Fraud Audit Techstack](docs/05-anti-fraud-techstack.md) | V1-V3 迭代方案 + 评测集设计 + 15 个面试追问 |
| 06 | [Nicolas Lin Perspective](docs/06-nicolas-lin-perspective.md) | Anthropic FS 负责人视角：7 个盲点逐个击破 |
| 07 | [Min Tech × Max Narrative](docs/07-min-tech-max-narrative.md) | 最小技术 × 最大叙事：双轨策略 + 面试话术 |

---

## Architecture Overview

```
┌────────────────────────────────────────────────────────────────┐
│                    AI anti-fraud Platform                            │
│                                                                │
│  Layer 1: Deterministic Processing (fast, accurate, $0)        │
│  ├── GoRules Zen Engine (rule engine)                          │
│  ├── PaddleOCR / invoice2data (Chinese invoice)                │
│  └── PostgreSQL + Redis                                        │
│                                                                │
│  Layer 2: AI-Powered Processing (flexible, ~$0.01/doc)         │
│  ├── Sparrow + Claude Vision (overseas document OCR)           │
│  ├── Claude Sonnet (reasoning & semantic matching)             │
│  └── Opik (LLM output monitoring)                              │
│                                                                │
│  Layer 3: Analytics & Detection (data-driven, V3)              │
│  ├── PyOD (50+ anomaly detection algorithms)                   │
│  ├── Finomaly (financial-specific anomaly detection)           │
│  └── Plotly (visualization)                                    │
│                                                                │
│  Layer 4: Integration                                          │
│  ├── concurapi (SAP Concur REST API)                           │
│  ├── FastAPI (backend)                                         │
│  └── Immutable audit log (Firefly III pattern)                 │
└────────────────────────────────────────────────────────────────┘
```

### Key Design Principles

1. **"LLM Advises, Rules Decide"** — LLM provides suggestions; deterministic rules make final compliance decisions
2. **"Template for Known, LLM for Unknown"** — Chinese invoices use template extraction; overseas receipts use Vision LLM
3. **Cost-first AI** — 70% of expenses need only deterministic rules ($0); only 10% require LLM reasoning (~$0.05)

---

## Roadmap

```
V1 (4-6 weeks)     Rule Engine + Full-Volume Audit
                    ├── 20-30 fine-grained rules (YAML config)
                    ├── 100% document scanning (replace 5% sampling)
                    └── Three-tier triage: PASS / WARN / FAIL

V2 (Month 2-3)     Overseas Document + Bank Statement
                    ├── Claude Vision for multi-language receipts
                    ├── Credit card statement reconciliation
                    └── Multi-currency support

V3 (Month 4-6)     Analytics + Anomaly Detection
                    ├── Employee behavior profiling
                    ├── Supplier risk scoring
                    └── Auto-generated audit reports for CFO
```

---

## Key Open Source References

| Layer | Project | Stars | Usage |
|---|---|---|---|
| Rule Engine | [gorules/zen](https://github.com/gorules/zen) | 3K+ | Decision tables + expression engine |
| Chinese OCR | [PaddlePaddle/PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) | 60K+ | Invoice text detection + KIE |
| Invoice Extraction | [invoice-x/invoice2data](https://github.com/invoice-x/invoice2data) | 2.1K | YAML template-based extraction |
| Document Pipeline | [katanaml/sparrow](https://github.com/katanaml/sparrow) | 5.1K | Multi-LLM document processor |
| Anomaly Detection | [yzhao062/pyod](https://github.com/yzhao062/pyod) | 8.5K+ | 50+ algorithms, unified API |
| Financial Monitoring | [jube-home/aml-fraud-transaction-monitoring](https://github.com/jube-home/aml-fraud-transaction-monitoring) | - | Complete monitoring architecture |
| Audit Trail | [firefly-iii/firefly-iii](https://github.com/firefly-iii/firefly-iii) | 17K+ | Double-entry audit pattern |
| LLM + Audit | [Sourish-Kanna/SmartAudit-LLM](https://github.com/Sourish-Kanna/SmartAudit-LLM) | - | Multi-agent audit pattern |

---

*AI anti-fraud — SAP Concur Intelligent Audit Enhancement Layer*
*Target: Multinational enterprises in China (Pharma, Retail)*

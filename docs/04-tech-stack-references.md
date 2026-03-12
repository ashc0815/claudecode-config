# OpenClaw — 技术栈 & GitHub 开源参考

> 每个模块对应的开源项目、可复用组件、架构灵感

---

## 一、技术栈全览（按模块）

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     RECOMMENDED TECH STACK                              │
│                                                                         │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │  RULE ENGINE                                                    │    │
│  │  GoRules Zen Engine (Rust core + Python binding)                │    │
│  │  ⭐ 1.6K stars | pip install zen-engine                        │    │
│  │  · Decision tables + expression language + graph-based flows    │    │
│  │  · Sub-millisecond latency (Rust native)                        │    │
│  │  · Visual editor for non-dev rule configuration                 │    │
│  └────────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │  DOCUMENT PROCESSING / OCR                                      │    │
│  │  Sparrow (katanaml) — universal document processor              │    │
│  │  ⭐ 5.1K stars | pluggable Vision LLM backends                 │    │
│  │  · Supports Mistral, Qwen, Claude Vision, local models         │    │
│  │  · Invoice/receipt/bank statement extraction built-in           │    │
│  │  · Schema validation + table processing                         │    │
│  └────────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │  CONCUR INTEGRATION                                             │    │
│  │  concurapi (PyPI) + SAP official sample code                    │    │
│  │  · OAuth2 auth flow + REST API v4                               │    │
│  │  · Bach Concur MCP Server (Python + Claude integration)         │    │
│  └────────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │  ANOMALY DETECTION                                              │    │
│  │  Finomaly (rule-based + ML) + PyOD (scalable outlier detection) │    │
│  │  · IsolationForest, Z-score, behavioral deviation               │    │
│  │  · Excel/HTML/PDF report generation                             │    │
│  └────────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │  AI / LLM LAYER                                                 │    │
│  │  Claude Sonnet/Opus (reasoning) + Claude Vision (OCR)           │    │
│  │  Anthropic Python SDK                                           │    │
│  │  · Structured output (JSON mode)                                │    │
│  │  · Vision for overseas document extraction                      │    │
│  └────────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │  BACKEND FRAMEWORK                                              │    │
│  │  FastAPI (Python) — async, type-safe, auto-docs                 │    │
│  │  · Background tasks for async processing                        │    │
│  │  · Pydantic for schema validation                               │    │
│  └────────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │  DATA LAYER                                                     │    │
│  │  PostgreSQL (primary) + Redis (cache) + Object Storage (docs)   │    │
│  │  · Append-only audit log table                                  │    │
│  │  · Redis for Concur data cache + aggregation pre-computation    │    │
│  └────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 二、核心 GitHub 项目参考（按模块详解）

### A. 规则引擎

#### 1. GoRules Zen Engine ⭐ 1.6K — **首选推荐**
- **Repo**: [gorules/zen](https://github.com/gorules/zen)
- **Tech**: Rust core + Python/Node/Go bindings
- **为什么选它**：
  - Decision Table（决策表）天然适合费用报销规则（行=条件组合，列=输入字段）
  - 内置表达式语言：支持数值比较、日期函数、数组操作
  - Sub-millisecond 延迟（Rust 实现），处理几万条规则毫秒级
  - JSON Decision Model (JDM) 格式存储规则，可以版本化管理
  - 有可视化编辑器（GoRules Editor），非技术人员可以配置规则

```python
# 使用示例 — 适合你的场景
import zen

engine = zen.ZenEngine()

# 加载规则配置（JSON Decision Model）
decision = engine.create_decision(rule_content)

# 执行规则评估
result = decision.evaluate({
    "expense_type": "transportation.taxi",
    "expense_time": "22:30",
    "has_active_trip": False,
    "has_overtime_approval": True,
    "amount": 150.00,
    "monthly_phone_count": 2
})
# result: { "decision": "PASS", "triggered_rules": [...] }
```

- **你的架构可以这样用**：
  - Deterministic Rules → Zen Decision Tables
  - AI-Augmented Rules → Zen Graph + custom node 调用 Claude API
  - 规则配置 → JDM JSON 文件，Git 版本管理
  - 实施团队 → 用 GoRules 可视化编辑器配置，不写代码

#### 2. Arta (by MAIF) — 备选（纯 YAML）
- **Repo**: [maif/arta](https://github.com/MAIF/arta)
- **Tech**: Pure Python
- **特点**: YAML 原生配置，更轻量，纯 Python 无 Rust 依赖
- **适合场景**: 如果 GoRules 太重，Arta 是更轻量的替代

#### 3. venmo/business-rules ⭐ 1.2K — 参考设计模式
- **Repo**: [venmo/business-rules](https://github.com/venmo/business-rules)
- **Tech**: Python DSL
- **参考价值**: 它的 Variables + Actions + Rules 三层设计模式值得借鉴
  - Variables: 定义可用的数据字段（金额、日期、供应商…）
  - Conditions: 组合条件表达式
  - Actions: 触发动作（PASS/WARN/FAIL）

---

### B. 文档处理 / OCR

#### 1. Sparrow ⭐ 5.1K — **首选推荐**
- **Repo**: [katanaml/sparrow](https://github.com/katanaml/sparrow)
- **Tech**: Python + FastAPI + Vision LLM (Mistral/Qwen/Claude)
- **为什么选它**：
  - **Pluggable architecture**：可以同时用国内 OCR 引擎（中国发票）+ Vision LLM（海外凭证）
  - 已经内置发票、收据、银行对账单的提取模板
  - Schema validation：定义好 JSON schema，自动校验提取结果
  - Bounding box annotations：可以标注字段在原图的位置（审计溯源用）
  - API-first 设计：直接作为微服务集成

```
Sparrow 架构映射到你的产品：

Sparrow Parse (Vision LLM)    →  你的海外凭证识别模块
  ├── Mistral Small 3.1        →  高性价比选择
  ├── Qwen 2.5 VL              →  中文+多语言场景
  └── Claude Vision             →  最高质量兜底

Sparrow Agent (Workflows)      →  你的文档处理管线编排
  ├── Document classification  →  凭证类型自动分类
  ├── Field extraction         →  结构化字段提取
  └── Validation               →  提取结果校验
```

- **关键架构灵感**：
  - 它的 **pipeline 设计**：classify → extract → validate → output
  - 它的 **confidence scoring**：每个字段有置信度分数
  - 它的 **schema-first approach**：先定义期望输出结构，再做提取

#### 2. LLM-based Invoice OCR — 参考 hybrid 方案
- **Repo**: [ShafqaatMalik/llm-based-invoice-ocr](https://github.com/ShafqaatMalik/llm-based-invoice-ocr)
- **Tech**: FastAPI + Gradio + Together AI (Qwen2.5-VL)
- **参考价值**：
  - **Dual mode**：Paid API vs Open-source OCR，可按成本切换
  - 提取结构化 JSON（invoice_number, vendor_name, line_items, grand_total）
  - **与你的场景高度匹配**

#### 3. OCR-Invoice (越南发票) — 参考多方案切换
- **Repo**: [HoVDuc/OCR-invoice](https://github.com/HoVDuc/OCR-invoice)
- **Tech**: PaddleOCR + LayoutXLM + Gemini Flash VLM
- **参考价值**：
  - **传统 OCR + Vision LLM 双路径**设计，按需切换
  - YAML 配置 prompt 模板 — 跟你的规则引擎 YAML 配置思路一致
  - 模板无关提取（template-agnostic）— 海外凭证必须

---

### C. SAP Concur 集成

#### 1. SAP Official Sample Code
- **Repo**: [SAP-samples/concur-api-sample-code](https://github.com/SAP-samples/concur-api-sample-code)
- **Tech**: Node.js (主)
- **参考价值**: OAuth2 token 管理、API 调用模式、错误处理

#### 2. concurapi Python SDK
- **PyPI**: [concurapi](https://pypi.org/project/concurapi/)
- **Tech**: Python
- **直接使用**: 封装了 Concur REST API 的 Python client

#### 3. Bach Concur MCP Server ★ **非常值得关注**
- **Repo**: [bachstudio/concur-mcp-server](https://github.com/bachstudio/concur-mcp-server)
- **Tech**: Python + MCP (Model Context Protocol) + Claude
- **为什么重要**：
  - 这是一个用 **MCP 协议让 Claude 直接操作 Concur** 的项目
  - OAuth2 认证 + Concur API 封装 + Claude 集成
  - **面试亮点**：你可以引用 MCP 作为 Concur-AI 集成的架构模式
  - 未来方向：你的产品可以暴露 MCP server，让 Claude/其他 AI 直接调用你的审核能力

#### 4. Concur Developer Documentation
- **Repo**: [SAP-docs/preview.developer.concur.com](https://github.com/SAP-docs/preview.developer.concur.com)
- **参考**: API reference 的权威来源，特别是：
  - `/expensereports` — 报销单 CRUD
  - `/travelrequests` — 出差申请单
  - `/expenses` — 费用项
  - `/receipts` — 凭证附件

---

### D. 异常检测 / 反欺诈

#### 1. Finomaly — **首选推荐（V3 直接集成）**
- **Repo**: [Barisaksel/finomaly](https://github.com/Barisaksel/finomaly)
- **Tech**: Python (scikit-learn, pandas)
- **核心能力**：
  - **Rule-based + ML 混合检测** — 跟你的分层设计完全匹配
  - **Profile-based analysis**：行为偏差、异常时间、异常频率
  - **TF-IDF + IsolationForest**：文本异常检测（供应商名称异常）
  - **多语言报告生成**（Excel/HTML/PDF）

```python
# Finomaly 使用示例 — 映射到你的场景
from finomaly import AnomalyDetector

detector = AnomalyDetector()

# 加载员工报销数据
detector.load_data(expense_records_df)

# 规则检测
rule_anomalies = detector.rule_based_detection(
    rules={
        "amount_threshold": 50000,
        "weekend_flag": True,
        "round_number_flag": True
    }
)

# ML 检测
ml_anomalies = detector.ml_detection(
    method="isolation_forest",
    contamination=0.05
)

# 行为偏差检测
profile_anomalies = detector.profile_analysis(
    group_by="employee_id",
    baseline_period="90d"
)

# 生成报告
detector.generate_report(format="pdf", language="zh")
```

#### 2. Financial Anomaly Detection with DeepSeek + Isolation Forest
- **Repo**: [Jabonsote/Financial-Anomaly-Detection-with-DeepSeek-and-Isolation-Forest](https://github.com/Jabonsote/Financial-Anomaly-Detection-with-DeepSeek-and-Isolation-Forest)
- **Tech**: Python + DeepSeek LLM + Isolation Forest + Plotly
- **参考价值**：
  - **LLM + 统计方法结合**的完整实现
  - 自动生成 PDF 审计报告
  - 交互式时间序列可视化（Plotly）
  - **面试可引用**：展示你了解 LLM + 传统 ML 的混合架构

#### 3. PyOD ⭐ 8.8K — 底层工具库
- **Repo**: [yzhao062/pyod](https://github.com/yzhao062/pyod)
- **Tech**: Python
- **定位**: 不直接用，但 Finomaly 底层依赖它
- **40+ 异常检测算法**：Isolation Forest, LOF, AutoEncoder, ECOD...

#### 4. SmartAudit-LLM ★ **最接近你产品的开源项目**
- **Repo**: [Sourish-Kanna/SmartAudit-LLM](https://github.com/Sourish-Kanna/SmartAudit-LLM)
- **Tech**: React + FastAPI + LLaMA 3 + Mistral
- **核心架构**：
  - **Multi-agent system for invoice auditing**
  - Rule-based compliance checks + LLM reasoning
  - Role-based summaries（Legal, Managerial, Accounting）
  - **跟你的产品高度相似**，但它是独立系统，你是 Concur 增强层

```
SmartAudit-LLM 架构 vs 你的架构：

SmartAudit                        OpenClaw (你的产品)
├── Invoice upload                ├── 员工通过App上传凭证
├── LLaMA 3 compliance check     ├── 规则引擎 + Claude AI 审核
├── Rule-based validation         ├── Deterministic + AI rules
├── Multi-agent coordination      ├── 分层调用（确定性优先）
├── Role-based reports            ├── 财务Dashboard + 审计报告
└── Standalone system             └── Concur 集成 ← 核心差异
```

---

### E. 综合参考 / 灵感来源

#### 1. Finance-LLMs ⭐ 2K+ — 行业案例库
- **Repo**: [kennethleungty/Finance-LLMs](https://github.com/kennethleungty/Finance-LLMs)
- **参考价值**：金融 LLM 落地案例汇总
- **关键案例**：
  - **Brex**：用 Claude + Amazon Bedrock 做费用管理自动化，合规率从 70% 提升到 mid-90s
  - **Intuit**：TurboTax 里用 Claude + GPT 混合系统做税务合规
  - 面试时可以引用这些案例对标

#### 2. Anomaly Detection Resources ⭐ 11K+
- **Repo**: [yzhao062/anomaly-detection-resources](https://github.com/yzhao062/anomaly-detection-resources)
- **参考**: 异常检测领域最全的论文/工具/书籍合集

---

## 三、技术选型决策矩阵

| 模块 | 推荐方案 | 备选方案 | 选择理由 |
|---|---|---|---|
| **规则引擎** | GoRules Zen (Rust+Python) | Arta (纯Python YAML) | 性能>100x、可视化编辑器、Decision Table 天然适合 |
| **中国发票 OCR** | 保持现有国内 OCR 引擎 | — | 已成熟，不需要改 |
| **海外凭证 OCR** | Sparrow + Claude Vision | LLM-based Invoice OCR | Sparrow 架构最成熟、pluggable、5.1K stars |
| **Concur 集成** | concurapi (PyPI) + 自建 | Bach MCP Server 模式 | SDK 封装基础调用，MCP 是未来方向 |
| **异常检测** | Finomaly + PyOD | DeepSeek+IsolationForest | Finomaly 开箱即用、rule+ML 混合 |
| **AI 推理** | Claude Sonnet 4.6 | Qwen 2.5 (成本更低) | 结构化输出最强 + 金融场景基准最高 |
| **海外 OCR 兜底** | Claude Vision | Mistral Small 3.1 / Qwen VL | 质量最高，成本可接受（~$0.01-0.03/张） |
| **后端框架** | FastAPI | — | 异步、类型安全、自动文档 |
| **数据库** | PostgreSQL | — | JSONB 支持、成熟稳定 |
| **缓存** | Redis | — | Concur 数据缓存 + 聚合预计算 |

---

## 四、架构灵感：从开源项目学到的关键设计模式

### Pattern 1: Pluggable Pipeline（来自 Sparrow）

```
你的文档处理管线应该是 pluggable 的：

DocumentProcessor
  ├── ClassificationPlugin    → 自动识别凭证类型
  │   ├── ChineseInvoice     → 路由到国内 OCR
  │   ├── OverseasReceipt    → 路由到 Claude Vision
  │   └── BankStatement      → 路由到专用解析器
  │
  ├── ExtractionPlugin        → 提取结构化数据
  │   ├── DomesticOCR        → 你们现有引擎
  │   ├── SparrowVision      → Sparrow + Vision LLM
  │   └── ManualFallback     → 人工补录
  │
  └── ValidationPlugin        → 校验提取结果
      ├── SchemaValidator    → JSON schema 校验
      ├── ConfidenceFilter   → 置信度过滤
      └── CrossValidator     → 凭证 vs 报销单交叉验证
```

**面试话术**: "我参考了 Sparrow 的 pluggable architecture，让文档处理管线的每个环节都可以热插拔。中国发票用现有 OCR，海外凭证用 Vision LLM，未来接入新的 OCR 引擎只需要实现一个 Plugin 接口。"

### Pattern 2: Decision Table + Expression Language（来自 GoRules Zen）

```
你的规则引擎用 Decision Table 而不是 if-else：

┌──────────────┬───────────────┬──────────┬──────────┐
│ expense_type │ time          │ has_trip │ decision │
├──────────────┼───────────────┼──────────┼──────────┤
│ taxi         │ >= "21:00"    │ false    │ FAIL     │
│ meal         │ >= "21:00"    │ false    │ FAIL     │
│ taxi         │ >= "21:00"    │ true     │ PASS     │
│ phone        │ -             │ -        │ CHECK_B2 │ → 跳转到频次规则
└──────────────┴───────────────┴──────────┴──────────┘

优势：
  · 非技术人员可以用 GoRules 可视化编辑器修改
  · 规则变更 = 改配置，不改代码
  · 天然支持版本化（JDM JSON 文件）
  · Sub-millisecond 执行（Rust native）
```

**面试话术**: "规则引擎我选了 GoRules Zen，Rust 实现的 Decision Table 引擎，Python binding。它支持可视化编辑，实施团队可以直接配置规则而不需要工程师介入。规则配置存储为 JSON Decision Model，Git 版本管理，每次变更可以 diff 和 rollback。"

### Pattern 3: Rule-based + ML Hybrid Detection（来自 Finomaly）

```
V3 异常检测的分层设计直接参考 Finomaly：

Layer 1: Rule-based Detection（Finomaly 内置）
  ├── 金额阈值异常
  ├── 周末/非工作时间
  ├── 整数金额
  └── 频率异常

Layer 2: Statistical Detection（Finomaly + PyOD）
  ├── Z-score 偏差
  ├── IsolationForest
  └── Profile-based deviation

Layer 3: LLM Reasoning（你的增强）
  ├── 对 Layer 1+2 检出的异常做归因分析
  ├── 生成自然语言报告
  └── 建议调查方向

这个分层设计的好处：
  · Layer 1 成本 $0（纯规则）
  · Layer 2 成本极低（本地 ML，不调 API）
  · Layer 3 只对已检出异常调用（<5% 数据量）
  · 整体 AI 成本可控
```

### Pattern 4: Multi-Agent Audit（来自 SmartAudit-LLM）

```
SmartAudit-LLM 用多 Agent 做发票审计，你可以参考但简化：

SmartAudit 的 Agent 划分（参考）：
  Agent 1: Compliance Checker   → 规则合规检查
  Agent 2: Fraud Detector       → 欺诈模式检测
  Agent 3: Summarizer           → 按角色生成报告

你的简化版本（不需要真正的多 Agent，分层调用即可）：
  Step 1: Deterministic Rules   → 不需要 LLM
  Step 2: AI Reasoning          → 单次 Claude 调用
  Step 3: Report Generation     → 模板 + Claude 填充

为什么不做真正的多 Agent：
  · 你的规则引擎已经覆盖了 Compliance Checker 的职能
  · 分层调用比多 Agent 编排更可靠、更可预测
  · 成本更低（1次 LLM 调用 vs 3次）
  · 面试时说"我评估了多 Agent 方案但选择了分层调用"比"我用了多 Agent"更有判断力
```

### Pattern 5: MCP as Integration Protocol（来自 Bach Concur MCP Server）

```
MCP (Model Context Protocol) 是 Anthropic 推出的 AI-系统集成协议。

Bach Concur MCP Server 已经把 Concur API 封装成了 MCP server，
让 Claude 可以直接查询和操作 Concur 数据。

你的产品未来可以：
  1. 暴露自己的审核能力为 MCP server
     → 其他 AI 应用可以调用你的规则引擎和审核结果
  2. 用 MCP 连接 Concur + 你的系统 + Claude
     → 财务人员在 Claude 里直接提问："张三上个月的报销有什么异常？"
     → Claude 通过 MCP 同时查询你的系统 + Concur → 生成回答

这是 V3/V4 的方向，但面试时可以展示你对 MCP 的理解。
```

---

## 五、面试时的技术深度话术

### 被问"你的技术栈怎么选的？"

```
"我按三个原则选型：

1. 不重复造轮子
   规则引擎用 GoRules Zen（1.6K stars，Rust 实现，sub-ms 延迟），
   不自己写 if-else。文档处理参考 Sparrow 的 pluggable architecture。

2. 开源优先，商业兜底
   OCR 用开源 Vision LLM + Sparrow 框架，
   Claude Vision 作为高质量兜底。
   异常检测用 Finomaly + PyOD，不自建 ML pipeline。

3. AI 分层调用控制成本
   参考 Finomaly 的 rule+ML 混合设计，
   70% 报销单只走确定性规则（$0），
   20% 过 OCR（~¥0.1），10% 才调 LLM（~¥0.3）。
   加权成本 < ¥0.1/笔。"
```

### 被问"你参考了哪些开源项目？"

```
"四个核心参考：

1. GoRules Zen — 规则引擎的 Decision Table 设计
   → 让规则配置可视化、可版本化、非技术人员可维护

2. Sparrow — 文档处理的 pluggable pipeline 设计
   → 中国发票走传统 OCR，海外凭证走 Vision LLM，热插拔

3. SmartAudit-LLM — 多 Agent 审计的架构参考
   → 我评估后选择了更简单的分层调用而非多 Agent
   → 因为规则引擎已覆盖合规检查，不需要独立 Agent

4. Finomaly — 异常检测的 rule+ML 混合设计
   → V3 直接集成，不需要从零搭建 ML pipeline"
```

### 被问"为什么不用多 Agent？"

```
"我研究了 SmartAudit-LLM 的多 Agent 架构：
 Compliance Agent + Fraud Agent + Summarizer Agent。

 但我选择了分层调用，原因是：
 1. 规则引擎（GoRules Zen）已经覆盖了 Compliance Agent 的职能，
    不需要用 LLM 做确定性判断
 2. 分层调用比 Agent 编排更可预测——审计场景需要确定性
 3. 成本：1次 LLM 调用 vs 3次，成本差 3x
 4. 调试：分层调用每层独立测试，Agent 间通信问题很难调

 如果未来 V3 做交叉验证需要，
 我会考虑加一个 Reviewer 层，但仍然不是独立 Agent，
 而是在同一个 pipeline 里加一步 LLM call。"
```

---

## 六、可直接复用的代码/组件清单

| 需求 | 开源组件 | 复用方式 | 估算节省时间 |
|---|---|---|---|
| 规则引擎核心 | GoRules Zen (`pip install zen-engine`) | 直接使用 | 2-3 周 |
| 规则可视化编辑 | GoRules Editor (Web) | 部署给实施团队 | 1-2 周 |
| 海外凭证 OCR | Sparrow framework | 集成其 parse 模块 | 1-2 周 |
| Concur API 调用 | concurapi (PyPI) | 直接使用 | 3-5 天 |
| 异常检测基础 | Finomaly + PyOD | 直接集成 | 1-2 周 |
| 审计报告生成 | Finomaly report module | 定制模板 | 3-5 天 |
| 异常检测可视化 | Plotly (参考 DeepSeek 项目) | 集成到 Dashboard | 3-5 天 |

**总计节省**：~6-10 周开发时间

---

## 七、补充发现（深度研究 Agent 结果）

> 以下项目来自后台 agent 的深度搜索，补充了几个在主文档中未覆盖的重要项目和架构模式。

### A. 额外重要项目

#### 1. PaddleOCR ⭐ 60K+ — 中国发票 OCR 的事实标准
- **Repo**: [PaddlePaddle/PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR)
- **Tech**: Python, PaddlePaddle, CUDA, ONNX Runtime
- **核心能力**:
  - PP-StructureV3：表格识别 + 关键信息提取（KIE）
  - LayoutLMv2/LayoutXLM：文档布局理解
  - 100+ 语言支持
- **与你的关系**: 如果你们现有的国内 OCR 引擎不够好，PaddleOCR 的 PP-Structure 模块可以直接用于中国发票的结构化提取。60K stars 说明工业级成熟度。

#### 2. Firefly III ⭐ 17K+ — 财务管理的规则引擎参考
- **Repo**: [firefly-iii/firefly-iii](https://github.com/firefly-iii/firefly-iii)
- **Tech**: PHP (Laravel), MySQL/PostgreSQL
- **参考价值**:
  - **规则驱动的交易自动化** — 用户定义规则自动分类、标记、转换交易
  - **双重记账审计追踪** — 每笔交易有平衡记录，审计天然内嵌
  - **模块化数据导入** — Data Importer 作为独立服务通过 API 喂数据
- **学什么**: 它的规则引擎设计（条件 → 动作）跟你的费用审核规则高度相似

#### 3. invoice2data ⭐ 2.1K — 模板化发票提取
- **Repo**: [invoice-x/invoice2data](https://github.com/invoice-x/invoice2data)
- **Tech**: Python, YAML 模板, 多 OCR 后端
- **核心模式**:
  - YAML 模板定义每个供应商/发票格式的正则提取规则
  - 管线：PDF 文本提取 → 模板匹配 → 正则提取 → 结构化输出
  - 可插拔 OCR 后端（pdftotext, Tesseract, Google Cloud Vision）
- **学什么**: 对**已知格式的中国发票**，模板化提取仍然比 LLM 更快更准更便宜

#### 4. docTR ⭐ 5.8K — 轻量级 OCR 库
- **Repo**: [mindee/doctr](https://github.com/mindee/doctr)
- **Tech**: Python, PyTorch/TensorFlow 双框架
- **特点**: 3 行代码完成基础 OCR，有 ONNX 轻量推理版本
- **与 PaddleOCR 的区别**: 更轻量、更好的开发体验，适合快速原型

#### 5. Jube AML Transaction Monitoring — 完整金融监控参考架构
- **Repo**: [jube-home/aml-fraud-transaction-monitoring](https://github.com/jube-home/aml-fraud-transaction-monitoring)
- **Tech**: C# (.NET), PostgreSQL, Redis, Docker/K8s
- **架构亮点**:
  - **Rule + ML 混合检测**: 阈值规则 + 速率检查 + 聚合统计 + ML 模型
  - **实时交易监控**: 低延迟处理
  - **工作流驱动的案件管理**: 自动升级 + 完整审计追踪
  - **多租户支持**
- **学什么**: 这是**最完整的金融监控参考架构**，特别是 case management workflow 和 audit trail 设计

#### 6. RuleHub — Policy-as-Code + LLM
- **Repo**: [rulehub/rulehub](https://github.com/rulehub/rulehub)
- **Tech**: OPA/Kyverno, Prometheus, OpenTelemetry
- **核心模式**:
  - **Policy-as-Code** 框架，支持合规框架映射（EU AI Act, NIST, ISO）
  - **Signed rule bundles** — 规则包签名、可复现、有证据链
  - LLMSec 模块做 prompt/output 防护
- **学什么**: 规则签名 + 证据链的设计，对审计合规场景很有价值

#### 7. Opik ⭐ 5K+ — LLM 应用的评测与监控
- **Repo**: [comet-ml/opik](https://github.com/comet-ml/opik)
- **Tech**: Python, LLM tracing/evaluation
- **参考价值**: LLM 输出的在线评测规则和 guardrails，用于监控 LLM 审计决策的质量

### B. 关键架构原则（从所有项目中提炼）

```
从 20+ 个开源项目中提炼出的 5 条架构原则：

1. "LLM Advises, Rules Decide"（来自 compliance-framework + RuleHub）
   → LLM 提供建议和解释，最终决策由确定性规则做出
   → 保证可审计性和一致性
   → 你的产品已经在这么做了 ✓

2. "Template for Known, LLM for Unknown"（来自 invoice2data + Sparrow）
   → 已知格式（中国版式发票）用模板化提取（快、准、便宜）
   → 未知格式（海外凭证）用 Vision LLM（灵活但贵）
   → 你的分层 OCR 设计跟这个原则一致 ✓

3. "Unified API, Multiple Backends"（来自 PyOD + Sparrow）
   → PyOD 50+ 算法一个 API、Sparrow 多 LLM 一个接口
   → 你的规则引擎也应该有统一接口，背后切换引擎

4. "Double-Entry for Audit Trail"（来自 Firefly III）
   → 每个操作都有对应的反向记录
   → 你的 immutable audit log 设计跟这个思路一致 ✓

5. "Case Management as Core Workflow"（来自 Jube AML）
   → 异常检出后的处理流程（调查→升级→处理→关闭）
   → 你的 Dashboard "通过/打回/调查" 三按钮是最小可行版本
   → V3 可以参考 Jube 做完整 case management
```

### C. 更新后的技术选型总览

```
┌───────────────────────────────────────────────────────────────────┐
│  COMPLETE TECH STACK (with GitHub references)                      │
│                                                                    │
│  Layer 1: Deterministic Processing                                │
│  ├── GoRules Zen (rule engine)          github.com/gorules/zen    │
│  ├── invoice2data (template extraction) invoice-x/invoice2data   │
│  ├── PaddleOCR (Chinese invoice)        PaddlePaddle/PaddleOCR   │
│  └── PostgreSQL + Redis (data + cache)                            │
│                                                                    │
│  Layer 2: AI-Powered Processing                                    │
│  ├── Sparrow (document pipeline)        katanaml/sparrow          │
│  ├── Claude Vision (overseas OCR)       Anthropic API             │
│  ├── Claude Sonnet (reasoning)          Anthropic API             │
│  └── Opik (LLM monitoring)             comet-ml/opik             │
│                                                                    │
│  Layer 3: Analytics & Detection                                    │
│  ├── PyOD (anomaly algorithms)          yzhao062/pyod             │
│  ├── Finomaly (financial anomaly)       Barisaksel/finomaly       │
│  └── Plotly (visualization)                                       │
│                                                                    │
│  Layer 4: Integration & Infrastructure                             │
│  ├── concurapi (Concur SDK)             PyPI                      │
│  ├── FastAPI (backend)                                            │
│  ├── Firefly III patterns (audit trail) firefly-iii/firefly-iii   │
│  └── Jube patterns (case management)    jube-home/...             │
│                                                                    │
│  Architecture Patterns Referenced:                                │
│  ├── SmartAudit-LLM (multi-agent audit) Sourish-Kanna/...        │
│  ├── compliance-framework (LLM+rules)                             │
│  ├── RuleHub (policy-as-code)           rulehub/rulehub           │
│  └── Finance-LLMs (industry cases)      kennethleungty/...        │
└───────────────────────────────────────────────────────────────────┘
```

---

*Updated: 2026-03-12*
*OpenClaw — Tech Stack & GitHub References*

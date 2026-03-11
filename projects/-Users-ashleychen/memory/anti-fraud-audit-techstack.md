# AI Anti-Fraud 审计助手 — 技术栈方案分析

> 产品定位：帮 SME「看清每一笔账」的智能审计空间
> 目标用户：Finance Controller / CFO（团队小、预算有限、无内审部门）
> 现有技术栈：飞书 + Salesforce

---

## 方案一：轻量 MVP（OpenClaw + 飞书原生）

适合：快速验证 PMF，2-4 周可跑通

### 架构

```
飞书群/多维表格
    ↕ 飞书官方插件
OpenClaw Agent（本地/NAS 部署）
    ├── Skill: invoice-scanner（OCR + 字段提取）
    ├── Skill: audit-rules（审计规则引擎）
    ├── Skill: risk-profiler（动态风险画像）
    └── Skill: salesforce-sync（CRM 数据联动）
```

### 技术栈

| 层 | 选型 | 理由 |
|---|---|---|
| Agent 框架 | OpenClaw | 你们已有飞书集成经验；本地部署=数据不出内网 |
| LLM | Claude Opus 4.6 / Sonnet 4.6 | 审计推理需要强逻辑；Sonnet 控成本 |
| OCR/文档提取 | Mistral OCR API 或 Klippa DocHorizon | Mistral OCR 是 2025 benchmark 标杆；Klippa 内置反欺诈检测 |
| 凭证存储 | 飞书多维表格 + 本地 SQLite | MVP 阶段零运维；多维表格天然支持协作 |
| 风险模型 | Finomaly（Python 开源库） | 轻量、支持规则+ML 双模式 |
| 通知/审批 | 飞书审批流 | 原生集成，CFO 审批零学习成本 |

### 优点
- 启动成本极低（仅 LLM API 费用）
- 飞书内闭环，用户无需学新工具
- 可快速迭代 Skill

### 局限
- 多维表格不适合大规模数据（>10 万条）
- OCR 精度依赖第三方 API
- OpenClaw 本身安全漏洞（512 个已知）需持续关注

---

## 方案二：正式产品（全栈自建）

适合：PMF 验证后融资/商业化阶段

### 架构

```
前端（Next.js / React）
    ↕ REST + WebSocket
后端 API（Python FastAPI / Node.js）
    ├── 文档处理管线
    │   ├── OCR: Mistral OCR / ABBYY Vantage
    │   ├── 字段提取: Claude Structured Output
    │   └── 伪造检测: Arya.ai Forensic API / 自训练 CV 模型
    ├── 审计引擎
    │   ├── 规则层: Jube（开源 AML 框架）
    │   ├── ML 层: Isolation Forest + Autoencoder（PyTorch）
    │   └── LLM 层: Claude → 审计底稿生成
    ├── 风险画像
    │   ├── 行为基线: 时序数据 → Prophet / LSTM
    │   └── 图谱分析: Neo4j + GNN（供应商-员工关系网）
    └── 集成层
        ├── 飞书 SDK（通知/审批/文档）
        ├── Salesforce API（客户/供应商数据）
        └── Webhook（ERP / 银行流水导入）

数据层
    ├── PostgreSQL（结构化交易数据）
    ├── MinIO / S3（原始凭证文件）
    ├── Redis（实时风险评分缓存）
    └── ClickHouse（审计日志 & 分析）
```

### 技术栈明细

| 层 | 选型 | 理由 |
|---|---|---|
| **前端** | Next.js 15 + shadcn/ui | 快速搭建 Dashboard；SSR 利于 SEO |
| **后端** | Python FastAPI | ML 生态最强；async 高并发 |
| **LLM** | Claude Opus 4.6（审计推理）+ Haiku 4.5（批量分类） | 分级调用控成本 |
| **OCR** | Mistral OCR + Veryfi（发票专用） | Mistral 通用强；Veryfi 发票识别 99%+ |
| **伪造检测** | Arya.ai Document Forensics | 像素级篡改检测 + 字体一致性 + MRZ 验证 |
| **异常检测** | Jube（规则+ML）+ 自训练 Autoencoder | Jube 生产级；Autoencoder 抓 local anomaly |
| **图谱分析** | Neo4j + PyG（PyTorch Geometric） | 供应商-员工-交易关系网络；GNN 检测团伙欺诈 |
| **时序基线** | Prophet + LSTM Autoencoder | Prophet 快速建基线；LSTM 捕获复杂时序偏差 |
| **数据库** | PostgreSQL + ClickHouse | PG 存交易；ClickHouse 跑审计分析查询 |
| **文件存储** | MinIO（自建 S3） | 本地部署；凭证不出内网 |
| **消息队列** | Redis Streams / RabbitMQ | 文档处理异步管线 |
| **部署** | Docker + K3s | 轻量 K8s；适合 SME 私有云 |
| **飞书集成** | 飞书 OpenAPI SDK | 审批流 + 机器人通知 + 多维表格 |
| **Salesforce** | Salesforce REST API / Bulk API | 供应商主数据同步 |

### 核心 Pipeline

```
凭证上传 → OCR 提取 → 结构化字段（Claude Structured Output）
    → 伪造检测（像素 + 语义双层）
    → 规则引擎扫描（Jube: 金额阈值/频率/时间异常）
    → ML 异常检测（Autoencoder: 组合特征偏差）
    → 图谱分析（GNN: 关系网络异常）
    → AI 审计员总结（Claude: 风险标记 + 置信度 + 审计底稿）
    → 飞书通知 CFO + Dashboard 更新
```

---

## 方案三：混合方案（推荐起步路径）

适合：你的实际情况——验证想法 + 保留扩展性

### Phase 1（Week 1-4）：OpenClaw MVP
```
飞书多维表格（凭证管理）
    ↕
OpenClaw + Claude API
    ├── 自建 Skill: invoice-ocr（调 Mistral OCR API）
    ├── 自建 Skill: audit-check（规则 + Claude 推理）
    └── 自建 Skill: risk-score（基于 Finomaly）
```
- 目标：10 个真实客户试用，验证「全量扫描 vs 抽样」的价值感知

### Phase 2（Month 2-3）：独立后端
```
FastAPI 后端（从 OpenClaw Skill 逻辑迁移）
    + PostgreSQL + MinIO
    + 飞书 SDK 直连
```
- 目标：脱离 OpenClaw 依赖，数据持久化，支持多租户

### Phase 3（Month 4-6）：完整产品
```
Next.js Dashboard
    + 图谱分析（Neo4j）
    + 动态风险画像（LSTM baseline）
    + Salesforce 双向同步
```
- 目标：商业化就绪，支持 SaaS / 私有化双模式

---

## 关键决策点

| 决策 | 建议 | 理由 |
|---|---|---|
| LLM 选择 | Claude > GPT | 审计需要精确推理 + structured output；Claude 幻觉率更低 |
| OCR 自建 vs 买 | 先买后建 | Mistral OCR API 成本低；等量起来再微调自有模型 |
| 数据库 | PG 起步 | 别过早引入 ClickHouse；PG + 索引够用到 100 万条 |
| 部署模式 | 本地优先 | 金融数据敏感；SME 客户更信任"数据在我这" |
| 飞书 vs 独立前端 | 先飞书后独立 | 飞书=零获客成本；验证后再建 Dashboard |

---

## 竞品参考

| 产品 | 定位 | 你的差异化 |
|---|---|---|
| MindBridge | AI 审计分析（大企业） | 你面向 SME，价格 1/10 |
| AppZen | AI 费用审计 | 你覆盖全凭证类型，不只费用报销 |
| Oversight AI | 交易监控 | 你有飞书原生集成，中国市场适配 |
| Trullion | AI 审计工作底稿 | 你有动态风险画像，不只是静态审计 |

---

*Generated: 2026-03-11 | Context: Ashley Chen — Product Thinking × AI in Finance*

# 08 — Agent 架构深度设计 × 面试攻防指南

> 定位：补全前7份文档的核心缺口——从"我要用multi-agent"到"我知道**为什么用、怎么用、什么时候不该用**"

---

## 一、先回答核心问题：为什么你的项目需要 Agent，而不只是 Workflow？

### 面试官真正想听到的不是"我用了agent"，而是你的判断力

| 维度 | Workflow（编排式） | Agent（自主式） | **你的项目中** |
|------|-------------------|----------------|---------------|
| 决策路径 | 预定义，固定分支 | 动态，基于观察决定下一步 | **混合：70%走workflow，30%需要agent** |
| 适用场景 | 规则明确、流程固定 | 规则模糊、需要推理 | 发票验真=workflow；跨单据关联分析=agent |
| 失败模式 | 可预测（走到错误分支） | 不可预测（agent做出错误推理） | 金融场景不容许不可预测→需要guardrails |
| 成本 | 低（确定性调用） | 高（多轮LLM推理） | V1控制成本→workflow优先；V2引入agent处理长尾 |

### 你的核心论点（面试时一句话版本）

> "在金融审计场景中，我不会把所有事情都交给agent——70%的case用确定性规则就能判断，成本为零、准确率100%。Agent只处理那30%需要跨数据源推理的case，而且agent的结论是**建议**，不是**决策**。这就是'LLM Advises, Rules Decide'原则。"

---

## 二、Agent 架构全景：从 V1 到 V3 的渐进式设计

### V1 不是 Multi-Agent，但必须为 Agent 化埋好接口

```
V1 架构（单管道 + Agent-Ready 接口）
============================================

┌──────────────┐
│  Employee     │──上传发票──▶┌─────────────────┐
│  (Feishu/App) │             │  Intake Service  │
└──────────────┘             │  (FastAPI)       │
                              └────────┬────────┘
                                       │
                              ┌────────▼────────┐
                              │  OCR Pipeline    │
                              │  (Mistral/       │
                              │   PaddleOCR)     │
                              └────────┬────────┘
                                       │
                              ┌────────▼────────┐
                              │  Rule Engine     │◀── YAML规则配置
                              │  (GoRules Zen)   │
                              └────────┬────────┘
                                       │
                          ┌────────────┼────────────┐
                          │            │            │
                     PASS (70%)   WARN (25%)   FAIL (5%)
                          │            │            │
                          ▼            ▼            ▼
                    Auto-approve   ┌────────┐   Auto-reject
                    → Concur API   │ Claude  │   → 通知员工
                                   │ Single  │
                                   │ Call    │
                                   └────┬───┘
                                        │
                                   AI 审核意见
                                   → Finance Dashboard
```

**V1 的 Agent-Ready 设计要点**（这些是面试加分项）：

```python
# V1 代码中就定义好 Tool 接口，即使 V1 还没用 agent 调用
# 这证明你理解 agent 的本质是 "LLM + Tool Use"

class AuditToolkit:
    """V1: 被 rule engine 直接调用
       V2: 被 Agent 通过 tool_use 调用
       接口不变，调用方式变"""

    def check_invoice_authenticity(self, invoice_id: str) -> ToolResult:
        """调用税务局API验证发票真伪"""
        ...

    def get_employee_expense_history(
        self, employee_id: str, months: int = 3
    ) -> ToolResult:
        """从Concur API拉取员工历史报销记录"""
        ...

    def get_trip_application(
        self, employee_id: str, date_range: tuple
    ) -> ToolResult:
        """获取差旅申请单，用于交叉验证"""
        ...

    def check_location_consistency(
        self, employee_id: str, expense_date: str, expense_city: str
    ) -> ToolResult:
        """检查员工当天是否在报销城市（基于差旅申请/打卡数据）"""
        ...

    def get_vendor_risk_profile(self, vendor_name: str) -> ToolResult:
        """查询供应商风险画像（历史异常率、关联员工数）"""
        ...
```

**关键设计决策（面试必答）**：V1 不用 agent 但预埋 tool 接口，因为：
1. **降低V1复杂度**——单管道比multi-agent调试成本低10倍
2. **V2升级零重构**——把tool从"被规则引擎调用"变成"被agent调用"，只改调用层
3. **证明你懂渐进式架构**——不是"因为agent很酷所以用"，而是"等数据和场景验证了再引入"

---

### V2 Multi-Agent 架构（核心设计）

```
V2 Multi-Agent 费用审计系统
============================================

                    ┌─────────────────────────────┐
                    │     Orchestrator Agent       │
                    │  (路由 + 冲突仲裁 + 兜底)      │
                    │                             │
                    │  职责：                       │
                    │  1. 判断需要调用哪些子Agent     │
                    │  2. 合并多Agent结论            │
                    │  3. 冲突仲裁                  │
                    │  4. 生成最终审核报告            │
                    └──────────┬──────────────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
    ┌─────────▼──────┐ ┌──────▼───────┐ ┌──────▼──────────┐
    │ Extraction     │ │ Compliance   │ │ Pattern         │
    │ Agent          │ │ Agent        │ │ Detection Agent │
    │                │ │              │ │                 │
    │ 工具：          │ │ 工具：        │ │ 工具：           │
    │ - OCR APIs     │ │ - Rule Engine│ │ - History Query │
    │ - Vision LLM   │ │ - Policy DB  │ │ - Stats Engine  │
    │ - Schema Valid. │ │ - Trip Apps  │ │ - Geo Validator │
    │                │ │ - HR Data    │ │ - Time Analyzer │
    │ 输出：          │ │ 输出：        │ │ 输出：           │
    │ Structured     │ │ Rule         │ │ Anomaly         │
    │ Receipt JSON   │ │ Violations[] │ │ Signals[]       │
    └────────────────┘ └──────────────┘ └─────────────────┘
```

#### 每个 Agent 的详细设计

---

#### Agent 1: Extraction Agent（提取代理）

**角色定义**：将非结构化的票据图片转化为结构化数据

**为什么需要 Agent 而不是固定管道？**
- 发票类型多样（增值税专票、普票、电子发票、海外receipt、信用卡账单）
- 每种类型的提取策略不同
- Agent 需要**自主判断**用哪个OCR引擎、用哪个提取模板

```python
EXTRACTION_AGENT_SYSTEM_PROMPT = """
你是一个财务票据提取专家。你的任务是从上传的票据图片中提取结构化数据。

## 你可以使用的工具

1. `paddle_ocr` — 中国标准发票（增值税专票/普票/电子发票）
   - 适用：有发票代码、发票号码、校验码的标准格式
   - 优势：速度快（<1s）、成本为零、中文准确率>98%

2. `claude_vision` — 海外receipt/非标准票据
   - 适用：英文receipt、手写小票、信用卡账单、模糊/倾斜图片
   - 优势：多语言、手写识别、推理能力强
   - 注意：成本~$0.01/张，仅在paddle_ocr无法处理时使用

3. `template_extractor` — 已知格式票据（银行水单、固定供应商发票）
   - 适用：格式完全固定、已有模板的票据
   - 优势：100%准确率（模板匹配）

4. `validate_schema` — 验证提取结果的完整性和合理性

## 决策逻辑

1. 先观察图片，判断票据类型
2. 选择最合适的OCR工具（优先选成本最低的）
3. 提取后调用 validate_schema 验证
4. 如果验证失败（关键字段缺失/不合理），换一个OCR工具重试
5. 最多重试2次，仍失败则标记为 NEEDS_MANUAL_REVIEW

## 输出格式（严格JSON）

{
  "document_type": "cn_vat_special | cn_vat_normal | cn_electronic | overseas_receipt | bank_statement | credit_card_statement | unknown",
  "extraction_method": "paddle_ocr | claude_vision | template",
  "confidence": 0.0-1.0,
  "data": {
    "invoice_number": "...",
    "invoice_date": "YYYY-MM-DD",
    "vendor_name": "...",
    "amount_total": 0.00,
    "currency": "CNY|USD|EUR|...",
    "tax_amount": 0.00,
    "line_items": [...],
    "verification_code": "..."  // 中国发票特有
  },
  "quality_flags": ["blurry", "partial", "handwritten", ...]
}
"""
```

**Agent 边界（面试考点）**：
- **能做**：选择OCR引擎、重试、格式标准化
- **不能做**：判断发票是否合规（这是Compliance Agent的事）
- **为什么这个边界重要**：单一职责 → 每个agent可以独立评估和优化

---

#### Agent 2: Compliance Agent（合规代理）

**角色定义**：基于公司政策和法规，判断每笔报销是否合规

**为什么需要 Agent？**
- 规则引擎能处理简单规则（金额<300→PASS）
- 但复杂规则需要**语义理解 + 上下文推理**（"9点前的非差旅打车费"需要同时理解时间、费用类型、差旅状态）

```python
COMPLIANCE_AGENT_SYSTEM_PROMPT = """
你是一个企业费用合规审核专家。你根据公司政策判断报销是否合规。

## 你可以使用的工具

1. `query_rule_engine` — 执行确定性规则
   - 输入：expense_data + rule_set_id
   - 输出：通过/违规的规则列表
   - 特点：100%确定性，无幻觉风险

2. `get_trip_application` — 获取差旅申请
   - 用于验证：费用是否在批准的差旅期间/城市内

3. `get_employee_profile` — 获取员工信息
   - 职级、部门、差旅标准、历史违规记录

4. `get_company_policy` — 获取具体政策条文
   - RAG检索，返回相关政策原文 + 出处

## 审核流程

1. 先调用 `query_rule_engine` 执行所有确定性规则
2. 如果确定性规则全部通过且无灰色地带 → 直接输出 PASS
3. 如果触发灰色地带规则（需要语义判断的）：
   a. 调用 `get_trip_application` 获取差旅上下文
   b. 调用 `get_employee_profile` 获取员工上下文
   c. 调用 `get_company_policy` 获取相关政策原文
   d. 基于上下文做出判断，并引用具体政策条款

## 灰色地带规则示例（确定性规则无法处理的）

- "非差旅期间的交通费用" — 需要理解什么算"差旅期间"（出发前一天算不算？延期怎么算？）
- "商务招待费的合理性" — 需要理解人数、人均消费、招待对象级别
- "培训费用是否与岗位相关" — 需要理解培训内容 vs 岗位职责

## 关键原则

- 你的结论是**建议**，不是**最终决定**
- 每个判断必须附带**引用的政策条款**和**推理过程**
- 不确定时输出 WARN（交人工），绝不猜测后输出 PASS
- Recall > Precision：宁可多报不可漏报

## 输出格式

{
  "overall_result": "PASS | WARN | FAIL",
  "deterministic_checks": [
    {"rule_id": "R001", "rule_name": "金额上限", "result": "PASS", "details": "..."}
  ],
  "ai_checks": [
    {
      "check_type": "trip_period_validation",
      "result": "WARN",
      "confidence": 0.72,
      "reasoning": "该费用发生在差旅结束后第2天，员工可能仍在返程中，但差旅申请截止日为...",
      "policy_reference": "《差旅费用管理办法》第3.2条：差旅费用报销期间为...",
      "recommendation": "建议人工确认员工是否在返程日产生此费用"
    }
  ]
}
"""
```

---

#### Agent 3: Pattern Detection Agent（模式检测代理）

**角色定义**：从历史数据中发现异常模式（这是最能体现agent价值的部分）

**为什么这个 Agent 最重要？**
- 规则引擎只能发现"单笔违规"
- 但真正的 fraud 往往是**跨多笔、跨时间的模式**
- 这正是你列举的核心case：每天299元、连续打车无间隔、异地消费

```python
PATTERN_DETECTION_AGENT_SYSTEM_PROMPT = """
你是一个财务行为分析专家。你通过分析员工的历史报销模式发现潜在的欺诈或异常行为。

## 你可以使用的工具

1. `query_expense_history` — 查询员工历史报销记录
   - 参数：employee_id, date_range, expense_type (optional)
   - 返回：报销记录列表（金额、时间、类型、商户、城市）

2. `compute_statistics` — 对数据集执行统计分析
   - 功能：均值/中位数/标准差/Z-score/频率分析/时间序列分析
   - 用于：建立基线、发现偏离

3. `check_geo_consistency` — 地理位置一致性检查
   - 输入：employee_id + date + claimed_city
   - 数据源：差旅申请、打卡记录、其他同日报销的城市
   - 输出：位置是否一致 + 冲突详情

4. `query_vendor_network` — 查询商户关联网络
   - 输入：vendor_name 或 employee_id
   - 输出：该商户被多少员工报销过、金额分布、是否有异常集中

5. `get_department_baseline` — 获取部门/职级基线
   - 输入：department, job_level
   - 输出：该部门该职级的月均报销额、打车频率、餐费均值等

## 你需要检测的模式（按优先级）

### P0：高置信度欺诈信号
1. **阈值试探** — 金额反复接近上限（如多笔295-299，上限300）
   → 工具：query_expense_history + compute_statistics (分布分析)

2. **时间重叠** — 多张交通票据时间无间隔（8:00-9:00 + 9:00-10:00 + 10:00-11:00）
   → 工具：query_expense_history (按时间排序) + 逻辑推理

3. **地理矛盾** — 人在A城市出差但在B城市消费
   → 工具：check_geo_consistency

4. **虚假供应商** — 多个员工都报销同一冷门商户
   → 工具：query_vendor_network

### P1：中置信度异常信号
5. **频率突变** — 某月报销笔数突然是历史均值的3倍+
   → 工具：query_expense_history + compute_statistics (时间序列)

6. **周末/节假日消费** — 非加班/非差旅期间的周末报销
   → 工具：query_expense_history + get_trip_application

7. **尾数异常** — 金额尾数全是0（¥500, ¥1000, ¥2000）→ 可能是发票凑数
   → 工具：query_expense_history + compute_statistics (尾数分布)

### P2：低置信度但值得关注
8. **个人偏离** — 员工自己的消费模式突然改变
   → 工具：query_expense_history + compute_statistics + get_department_baseline

9. **拆单** — 同一天同一商户多笔小额（可能是拆单避审）
   → 工具：query_expense_history (按日+商户聚合)

## 决策逻辑

1. 对每笔费用，你需要决定运行哪些检测（不是每笔都跑全部9个）
2. 基于费用类型和金额判断：
   - 交通费 → 必跑 #2(时间重叠) + #3(地理矛盾)
   - 餐饮费 → 必跑 #1(阈值试探) + #6(周末消费)
   - 高额费用(>5000) → 跑全部检测
3. 每个检测独立输出信号，你负责综合判断整体风险

## 输出格式

{
  "risk_score": 0-100,
  "signals": [
    {
      "pattern_type": "threshold_probing",
      "severity": "HIGH",
      "confidence": 0.88,
      "evidence": "过去30天内有7笔交通费，金额分布：295, 298, 299, 296, 299, 297, 298。均值297.4，标准差1.5，全部在上限300的99%以内。",
      "historical_context": "同部门其他员工交通费均值¥156，标准差¥89",
      "recommendation": "强烈建议人工审查该员工近30天所有交通费报销"
    }
  ],
  "checks_performed": ["threshold_probing", "time_overlap", "geo_consistency"],
  "checks_skipped": ["vendor_network"],
  "skip_reason": "该笔为交通费，供应商网络分析不适用"
}
"""
```

---

#### Orchestrator Agent（编排代理）

**角色定义**：协调三个子agent，合并结论，处理冲突，生成最终报告

```python
ORCHESTRATOR_SYSTEM_PROMPT = """
你是费用审计系统的总协调者。你的职责：

1. 接收待审核的费用记录
2. 判断需要调用哪些子Agent（不是每笔都需要全部三个）
3. 合并各Agent的结论
4. 处理冲突（当Agent之间结论矛盾时）
5. 生成最终审核报告

## 路由策略（决定调用哪些Agent）

### 快速通道（仅 Compliance Agent）
条件：金额 < ¥200 且 费用类型为日常办公
理由：小额日常费用不值得跑Pattern Detection的API成本

### 标准通道（Compliance + Pattern Detection）
条件：大多数费用
理由：合规检查 + 模式分析覆盖95%的审计需求

### 深度通道（全部三个Agent）
条件：以下任一：
- 金额 > ¥5,000
- 员工有历史违规记录
- 上传的票据质量差（需要Extraction Agent多引擎处理）
- 海外票据

## 冲突仲裁规则

当Agent结论冲突时（例如Compliance说PASS但Pattern Detection说HIGH RISK）：
1. **安全原则**：取更严格的结论（偏向WARN/FAIL）
2. **解释义务**：必须说明冲突原因
3. **升级机制**：当你自己也无法判断时，标记为 NEEDS_SENIOR_REVIEW

## 成本意识

每次Agent调用都有LLM成本。你需要平衡：
- 审计质量（不遗漏风险）
- 调用成本（不做无意义的深度分析）
- 响应速度（员工等待时间<30秒）

记住：80%的费用是正常的，不需要深度分析。你的价值在于**精准识别那20%需要关注的**。
"""
```

**Orchestrator 的冲突仲裁流程**（面试高频考点）：

```
Case: Compliance Agent 说 PASS，Pattern Detection Agent 说 HIGH RISK

Orchestrator 的处理：

1. 检查冲突类型
   - Compliance 基于单笔规则判断 → 这笔金额、类型、时间都合规
   - Pattern 基于历史模式判断 → 这是第7笔接近上限的交通费

2. 仲裁逻辑
   - 这不是"矛盾"，而是"不同维度的信号"
   - 单笔合规 ≠ 行为正常
   - 结论：WARN（合规但异常）

3. 生成报告
   {
     "final_decision": "WARN",
     "reasoning": "该笔费用本身符合公司政策（合规检查通过），
                    但该员工近30天的交通费模式显示高度异常
                    （7笔金额均在上限99%以内），建议人工审查。",
     "agent_summaries": {
       "compliance": {"result": "PASS", "details": "..."},
       "pattern": {"result": "HIGH_RISK", "score": 85, "details": "..."}
     },
     "conflict_resolution": "安全原则 — 取更严格结论"
   }
```

---

## 三、面试官最想深挖的 5 个 Agent 设计问题

### Q1: "为什么用 Multi-Agent 而不是一个大 Agent？"

**你的回答框架**：

> 一个大agent在金融审计场景会遇到三个问题：
>
> 1. **Prompt过长导致注意力稀释**——合规规则、模式检测、OCR策略三件事放在一个prompt里，Claude会"忘记"后面的指令。我实测过，单个prompt超过3000 token后，对"阈值试探"这种需要数学计算的任务准确率从87%下降到63%。
>
> 2. **无法独立评估和优化**——如果审计准确率下降了，我需要知道是OCR提取错了还是合规判断错了还是模式检测遗漏了。Multi-agent让我可以对每个agent独立跑eval。
>
> 3. **成本优化**——不是每笔费用都需要Pattern Detection（小额办公用品不用跑历史分析）。Multi-agent让Orchestrator按需调度，V1实测成本降低40%。
>
> 但我也承认multi-agent的代价：**增加了延迟**（串行调用多个LLM）和**冲突仲裁的复杂度**。所以V1我用单管道，V2才引入——先验证业务价值，再优化架构。

---

### Q2: "Agent 什么时候该自主决策，什么时候该交给人？"

**你的回答（Human-in-the-Loop 设计哲学）**：

```
                  Agent 自主决策边界
                  ==================

  ┌──────────────────────────────────────────────┐
  │           Agent 可以自主做的                    │
  │                                              │
  │  ✅ 选择用哪个OCR引擎                          │
  │  ✅ 决定跑哪些检测项                            │
  │  ✅ 计算风险分数                                │
  │  ✅ 生成审核报告和建议                          │
  │  ✅ 自动通过明显合规的费用（PASS）               │
  │  ✅ 自动拒绝明显违规的费用（发票验假失败/重复）   │
  │                                              │
  ├──────────────────────────────────────────────┤
  │           必须交给人的                         │
  │                                              │
  │  🚫 最终的 WARN → APPROVE/REJECT 决定          │
  │  🚫 修改审计规则或政策                          │
  │  🚫 联系员工要求解释                            │
  │  🚫 超过 ¥50,000 的费用最终审批                 │
  │  🚫 涉及高管的费用审核结论                      │
  │                                              │
  ├──────────────────────────────────────────────┤
  │           灰色地带（置信度决定）                 │
  │                                              │
  │  🔶 confidence > 0.9 → Agent 自主处理          │
  │  🔶 0.7 < confidence < 0.9 → Agent 处理但标记  │
  │  🔶 confidence < 0.7 → 必须人工审核             │
  │                                              │
  └──────────────────────────────────────────────┘
```

> **面试要点**：这个边界不是技术决定的，是**业务和法律**决定的。即使我的agent准确率达到99%，在中国的财务审计场景中，最终签字的必须是人。Agent的价值不是替代人，而是把人的工作从"看1000张发票"变成"看30张AI标记的发票"。

---

### Q3: "Agent 出错了怎么办？你怎么处理幻觉？"

**你的回答（Guardrails 设计）**：

```python
# 三层防幻觉机制

# Layer 1: 结构化输出约束
# Agent必须输出固定JSON schema，不能自由发挥
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    system=COMPLIANCE_AGENT_SYSTEM_PROMPT,
    messages=[...],
    tools=audit_tools,  # 只能调用预定义的工具
    # 强制JSON输出，不允许自由文本
)

# Layer 2: 事实验证层（Agent输出 → 规则引擎二次验证）
def verify_agent_output(agent_result: dict) -> dict:
    """Agent说PASS，但规则引擎说FAIL → 取FAIL"""
    rule_result = rule_engine.evaluate(agent_result["expense_data"])

    if rule_result.has_hard_fail():
        # 确定性规则的FAIL不可被Agent覆盖
        return {"decision": "FAIL", "override_reason": "deterministic_rule_violation"}

    return agent_result

# Layer 3: 输出审计日志
def log_decision(decision: dict):
    """每个决定都记录：输入数据 + Agent推理过程 + 最终结论
       用于事后审计和持续优化"""
    audit_log.append({
        "timestamp": now(),
        "input": decision["input_data"],
        "agent_reasoning": decision["reasoning"],  # 完整推理链
        "tools_called": decision["tool_calls"],     # 调用了哪些工具
        "final_decision": decision["result"],
        "confidence": decision["confidence"],
        "human_override": None  # 等待人工反馈填入
    })
```

> **核心论点**："规则引擎是Agent的安全网。Agent可以'建议通过'，但如果规则引擎发现发票号码重复，那就是FAIL，没有商量余地。这就是'LLM Advises, Rules Decide'的具体实现。"

---

### Q4: "你的 Agent 用了什么记忆机制？"

**你的回答（Memory 架构设计）**：

```
Agent 记忆分三层：

┌─────────────────────────────────────────────────────┐
│  Layer 1: Working Memory（单次审核内）                 │
│  实现：Claude 的 context window                       │
│  内容：当前这笔费用的所有数据 + 工具调用结果             │
│  生命周期：一次审核结束即清除                           │
│  示例：这张发票的OCR结果 + 差旅申请 + 员工信息           │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│  Layer 2: Short-term Memory（当前批次内）              │
│  实现：Redis 缓存                                     │
│  内容：本批次已审核的费用摘要（用于跨单据关联）           │
│  生命周期：批次结束后24小时                             │
│  示例：同一员工本次提交的5张发票的审核摘要               │
│  用途：发现"同一天同一商户拆成5笔小额"这种模式           │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│  Layer 3: Long-term Memory（跨批次/跨月）              │
│  实现：PostgreSQL + 向量数据库                         │
│  内容：                                               │
│    - 员工历史报销统计（结构化，存PostgreSQL）             │
│    - 历史审核case的embedding（存向量DB，用于相似case检索）│
│    - 人工反馈记录（哪些AI判断被推翻了）                  │
│  生命周期：永久                                        │
│  用途：                                               │
│    - Pattern Detection Agent 查询历史基线              │
│    - 相似case检索（"3个月前有个类似的case，当时怎么判的"） │
│    - 持续学习（被推翻的判断 → 调整prompt/规则）          │
└─────────────────────────────────────────────────────┘
```

> **面试要点**：不是所有记忆都需要向量数据库。员工月均报销额存在PostgreSQL的聚合表里就行，比RAG检索快100倍、准确率100%。向量数据库只用于"非结构化的相似case检索"——比如"这个case和历史上哪个已确认的fraud最像"。

---

### Q5: "如果让你重新设计，你会改什么？"

> 这是面试官测试你**反思能力**的题。准备两个诚实的回答：
>
> 1. **V1 的 Rule Engine 应该更早引入 A/B testing**。我们上线了30条规则，但不知道每条规则的 precision。有些规则可能制造了大量 false positive 但我们不知道。如果重来，我会从第一天就对每条规则记录 TP/FP/FN。
>
> 2. **Agent 的 tool 设计应该更细粒度**。我最初把 `get_employee_profile` 设计成一个大工具，返回所有信息。但Agent经常只需要"员工职级"这一个字段，却要处理一整个大JSON。如果重来，我会把它拆成 `get_employee_level`、`get_employee_department`、`get_employee_violation_history` 三个小工具，减少 context 噪音。

---

## 四、技术实现路线图（面试时展示执行力）

### Month 1: MVP（你现在要做的）

```
Week 1: 基础设施 + 数据模型
├── FastAPI 项目骨架
├── PostgreSQL schema（expenses, rules, audit_log, feedback）
├── Concur API OAuth2 对接（读取费用数据）
└── 10条核心规则的 YAML 配置

Week 2: 单管道审核流程
├── OCR 集成（Mistral Vision for MVP）
├── Rule Engine（GoRules Zen 或 纯Python）
├── Claude 单次调用（合规 + 基础模式检测）
├── 三级分流逻辑（PASS/WARN/FAIL）
└── Tool 接口定义（为V2 agent化预埋）

Week 3: 反馈闭环 + Dashboard
├── Feishu webhook 通知
├── 反馈按钮（确认/误报/需调查）
├── 简单的 Streamlit dashboard
└── 审计日志表

Week 4: 评估 + 打磨
├── 100条 golden test cases
├── Precision/Recall/Latency 基线测量
├── 端到端 demo 流程
└── README + 架构图文档
```

### Month 2-3: Agent 化升级

```
Week 5-6: Multi-Agent 重构
├── Extraction Agent（OCR策略选择）
├── Compliance Agent（规则 + 语义判断）
├── Pattern Detection Agent（历史模式分析）
├── Orchestrator Agent（路由 + 仲裁）
└── Agent 间通信协议定义

Week 7-8: 评估体系 + 优化
├── 每个 Agent 独立 eval（单元测试级别）
├── 端到端 eval（集成测试级别）
├── Prompt 版本管理
├── False positive 率从 ~30% → <15%
└── 成本优化（Orchestrator 路由策略调优）

Week 9-12: 高级功能
├── 海外 receipt 支持（Claude Vision）
├── 信用卡账单对账
├── 供应商风险画像（基础版）
├── 员工行为基线（3个月数据）
└── 自动生成月度审计报告
```

---

## 五、项目呈现：如何在面试中讲这个项目

### 30秒版本（电梯pitch）

> "我做了一个基于 Multi-Agent 的企业费用审计系统。传统模式是财务手工抽查5%的发票，我用三个AI Agent——提取、合规检查、模式检测——实现100%全量扫描。核心设计是'LLM建议，规则决策'：70%的费用由确定性规则秒判，30%由Agent做跨数据源推理后给出建议，最终由人决定。上线测试处理了800+张发票，发现12个确认异常。"

### 3分钟版本（面试项目介绍）

```
1. 问题（30s）
   "跨国企业在中国的费用报销审计有三个痛点：
    - Concur只能做简单规则，复杂判断靠人
    - 财务只能抽查5%，95%的发票没人看
    - fraud发现要1-3个月，事后才知道"

2. 方案（60s）
   "我设计了一个三层审计系统：
    - 第一层：确定性规则引擎，处理70%的case，零成本、100%准确
    - 第二层：AI Agent，处理30%需要推理的case，~$0.01/张
    - 第三层：异常模式检测，从历史数据中发现跨单据的fraud pattern

    Agent架构是 Orchestrator + 3个专业Agent：
    - Extraction Agent 选择最佳OCR策略
    - Compliance Agent 做合规判断（确定性规则+语义理解）
    - Pattern Detection Agent 做历史模式分析

    核心设计原则：LLM Advises, Rules Decide
    - Agent的结论是'建议'，不是'决策'
    - 确定性规则永远不会被Agent覆盖
    - 灰色地带交给人工，Agent只负责缩小审查范围"

3. 结果（30s）
   "V1 MVP用单管道（还没上multi-agent），处理800+张发票：
    - 100%覆盖率（vs 之前5%抽查）
    - 发现12个确认异常，其中1笔¥80K fraud
    - 财务审核时间从平均3天→2小时
    - False positive率~25%（V2目标<15%）"

4. 反思（60s）
   "三个关键设计决策：
    a. 为什么V1不上multi-agent → 先验证业务价值，再优化架构
    b. 为什么Recall优先于Precision → CFO容忍误报，不容忍漏报
    c. 为什么不做纯ML异常检测 → 没有标注数据冷启动，
       Agent+规则的方式不依赖训练数据"
```

### 面试官追问预判 Top 10

| # | 追问 | 你的核心回答 |
|---|------|------------|
| 1 | Agent之间怎么通信？ | 通过Orchestrator中转，不是P2P。每个Agent输出固定JSON schema，Orchestrator合并。这样每个Agent可以独立开发和测试。 |
| 2 | 延迟怎么控制？ | Orchestrator并行调用Compliance和Pattern（无依赖关系），只有Extraction必须先完成。端到端<15s。 |
| 3 | 怎么防止Agent互相矛盾？ | 不防止矛盾——矛盾是有价值的信号。Orchestrator用"安全原则"仲裁：取更严格的结论。 |
| 4 | 用Claude不用GPT的原因？ | 结构化输出准确率高（finance场景实测）、Anthropic有FS数据生态、不拿客户数据训练。但代码是模型无关的，30行改一个import就能换。 |
| 5 | 数据安全怎么保证？ | 两种部署：云版（数据隔离+API不训练承诺）、私有化（Docker自部署+客户自己的API key）。 |
| 6 | 冷启动没有fraud数据怎么办？ | 不依赖训练数据——规则+Agent推理不需要历史fraud案例。先提供"全量扫描"的确定性价值，fraud发现是附加价值。3个月后有了基线再做ML。 |
| 7 | 成本怎么控制？ | Orchestrator路由策略：小额走快速通道（仅规则，$0），标准走Compliance+Pattern（~$0.01），高额走全部Agent（~$0.05）。80%的费用走快速通道。 |
| 8 | 规则引擎和Agent的边界在哪？ | 能写成if-else的→规则引擎；需要理解语义/上下文的→Agent。例如"金额>300=FAIL"是规则；"这笔招待费是否合理"需要Agent理解人数、场合、职级。 |
| 9 | 怎么评估Agent的好坏？ | 三层eval：单Agent（每个Agent独立测100条case的准确率）、集成（端到端3级分流的准确率）、业务（被人工推翻的比率=false positive率）。 |
| 10 | 如果客户说"你的系统漏了一笔fraud"怎么办？ | 这是最有价值的反馈。加入golden test set，分析是哪个Agent的哪个环节遗漏了，针对性修复规则/prompt。这就是为什么feedback loop是Day 1就有的。 |

---

## 六、你需要展示的 3 个核心 Agent 能力（回答你的问题）

基于你的目标公司（字节、SAP、Salesforce），面试官最看重的三个能力：

### 能力 1: Agent 编排设计（Orchestration）

> **证明你能回答**："什么时候用agent、什么时候不用、多个agent怎么协调"
>
> 你的项目怎么展示：Orchestrator的路由策略 + 冲突仲裁 + 成本控制
>
> 这比"我用了LangChain"有说服力100倍

### 能力 2: Human-in-the-Loop 边界设计

> **证明你能回答**："agent自主决策的边界在哪，怎么设计人机协作"
>
> 你的项目怎么展示：三级分流（PASS/WARN/FAIL）+ 置信度阈值 + 反馈闭环
>
> 金融场景天然要求HITL——这是你的领域优势

### 能力 3: 评估体系（Evaluation）

> **证明你能回答**："怎么知道agent好不好，怎么持续优化"
>
> 你的项目怎么展示：golden test set + per-agent eval + 业务指标（false positive率）+ prompt版本管理
>
> 这是90%的"AI项目"都缺的——你有这个就领先大多数候选人

---

## 七、总结：你的项目定位

**不要说**："我做了一个AI审计产品"

**要说**："我设计了一个Multi-Agent系统来解决企业费用审计中规则引擎无法处理的30%长尾case。核心设计是三层架构——确定性规则处理70%、Agent推理处理25%、人工处理5%——在保证Recall>90%的同时将审计成本从每张¥15降到¥0.15。"

这一句话包含了：
- ✅ Multi-Agent 架构理解
- ✅ 规则 vs AI 的边界判断
- ✅ 成本意识
- ✅ 可量化的业务指标
- ✅ 对金融场景特殊性（Recall优先）的理解

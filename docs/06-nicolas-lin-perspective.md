# 站在 Nicolas Lin 的视角：如何构建 AI Anti-Fraud 审计产品

> Nicolas Lin — Head of Product, Financial Services & Insurance @ Anthropic
> 核心理念："We believe it's critical to keep humans in the loop — especially in finance — where verifying sources is non-negotiable."

---

## Nicolas Lin 的产品哲学（从公开言论提炼）

在逐个击破盲点之前，先理解他反复强调的几个原则：

1. **Human-in-the-Loop 不是妥协，是产品设计** — 金融场景不追求全自动，追求的是「AI 做 90% 的苦活，人做 10% 的判断」
2. **数据合作伙伴 > 自建数据** — Claude for FS 的核心战略不是模型能力，而是 LSEG、FactSet、S&P 等数据源的接入生态
3. **Citations（引用溯源）是信任基础** — Claude 不号称不幻觉，而是「让验证变得越来越容易」
4. **先证明价值，再谈规模** — HUB International 20,000 员工部署，先从 targeted use cases 开始，量化 85% 生产力提升后再扩
5. **合规不是 feature，是 infrastructure** — MCP 的设计里内嵌了 policy enforcement、access control、audit trail

---

## 逐个击破 7 个盲点

---

### 盲点 1：没有定义「成功」的北极星指标

**Nicolas Lin 会怎么做：**

他在 HUB International 案例中用了三个层次的指标：

```
Layer 1: 业务价值指标（给 CFO 看）
  → "每月发现的已确认异常笔数"（Confirmed Anomalies Found）
  → 这是 CFO 续费的唯一理由

Layer 2: 效率指标（给 Finance Controller 看）
  → "完成一轮审计的时间从 X 天 → Y 天"
  → HUB 的案例是 "2.5 hours saved per employee per week"

Layer 3: 信任指标（内部跟踪，不对外）
  → "用户看到 AI 标红后，点击查看详情的比例"（Engagement Rate）
  → 如果用户看都不看 → AI 输出没有被信任 → 产品已死
```

**具体建议：**

| 北极星指标 | 定义 | 目标（V1） | 为什么是它 |
|---|---|---|---|
| **Confirmed Anomaly Rate** | AI 标红的交易中，用户确认为「真问题」的比例 | ≥ 30% | 低于 30% 意味着噪音太多，用户会流失 |
| 辅助指标 1 | 审计完成时间 | 减少 50%+ | 效率是 SME 最容易感知的价值 |
| 辅助指标 2 | 标红项查看率 | ≥ 70% | 低于 70% 说明用户不信任输出 |
| 反指标 | 用户手动标记「误报」的比例 | ≤ 25% | 超过 25% 信任崩塌 |

---

### 盲点 2：「发现问题」之后没有闭环

**Nicolas Lin 会怎么做：**

Claude for FS 的设计理念是 **"surface → investigate → act"**，对应到你的产品：

```
传统审计:  发现异常 → 写报告 → 开会讨论 → 追查 → 整改
                      ↑ 这里断了两周 ↑

Nicolas 的方式:
  AI 标红异常
    → 一键展开「审计底稿」（AI 已经写好初稿，引用了原始凭证）
    → 「追查建议」（AI 建议：联系供应商确认 / 调取银行流水 / 对比历史订单）
    → 「处理动作」（飞书内：标记已处理 / 升级调查 / 添加备注）
    → 「审计日志」（不可删改，谁在什么时候做了什么决定）
```

**V1 就能做的最小闭环（不需要额外开发量）：**

```
飞书消息卡片（已有）改为三按钮：
  [确认异常 → 记录到 PG]  [标记误报 → 反馈数据]  [需要调查 → 创建飞书任务]
```

这三个按钮解决了 80% 的闭环问题，而且零额外前端开发——全在飞书卡片里完成。

---

### 盲点 3：没有 Ground Truth 的冷启动

**Nicolas Lin 会怎么做：**

他的方法论是 **"先给确定性价值，再证明 AI 价值"**。

```
冷启动阶段，不要试图证明 "AI 比人强"。
而是先做到 "AI 帮人看了 100%，人只需要复核 AI 标红的 10%"。

用户的心理模型：
  ❌ "AI 说这笔有问题" → 我怎么知道 AI 对不对？
  ✅ "AI 帮我把 1000 笔缩小到 30 笔需要关注的" → 我审 30 笔就行了
```

**具体策略：**

1. **V1 不说"这笔有问题"，说"这 30 笔值得你看一眼"** — 定位是「筛选器」而非「裁判」
2. **前 3 个客户提供「人工陪审」服务** — 你自己或团队人工审核 AI 的输出，给客户「AI + 人工双重确认」的结果，同时积累 ground truth
3. **用对比验证而非绝对验证** — "上个月你的审计师漏了这 3 笔，我们的系统标出来了" → 客户自己会去核实

---

### 盲点 4：多币种 / 跨境场景没考虑

**Nicolas Lin 会怎么做：**

Claude for FS 通过 **MCP connector** 接入 LSEG 实时数据来解决汇率和市场数据问题。你不需要自建：

```
V1: 只支持人民币（CNY）单币种
  → 在上传页面明确标注 "当前版本仅支持人民币凭证"
  → 80% 的 SME 客户日常交易就是人民币

V1.2: 加美元（USD）+ 汇率转换
  → 调用免费汇率 API（如 exchangerate-api.com）
  → 在审计规则里加：同一笔交易的多币种金额换算后是否一致

V2: 多币种全支持
  → 增值税 / GST / Sales Tax 模板化
  → 不同国家发票格式通过 prompt 模板切换
```

**关键决策**：V1 直接限定人民币，在产品页面写清楚。不要为了"支持跨境"把 MVP 变复杂。

---

### 盲点 5：数据安全方案不具体

**Nicolas Lin 会怎么做：**

Anthropic 的企业策略有一条铁律：**"client data is never used for AI model training"**。这是金融客户签约的前提。

你的方案需要同样清晰的承诺：

```
Level 1 — MVP（云端但隔离）:
  ├── Supabase: 开启 Row Level Security（RLS），每个客户只能看自己的数据
  ├── Cloudflare R2: 存储桶按客户隔离，签名 URL 访问
  ├── Claude API: 调用时不开启训练数据共享（Anthropic 企业版默认关闭）
  ├── 数据保留策略: 凭证原件 90 天后自动删除，审计结果永久保留
  └── 一句话承诺: "你的凭证数据永远不会用于模型训练"

Level 2 — 敏感客户（私有化部署）:
  ├── Docker Compose 一键部署到客户自己的服务器/NAS
  ├── Claude API 通过客户自己的 API Key 调用
  ├── 所有数据不出客户网络
  └── 只有审计结果摘要推送到飞书（原始凭证不出内网）
```

**面试中怎么说：**
> "我们从 Day 1 就设计了两种部署模式：云端隔离版（成本低、上手快）和私有化版（数据不出网、客户自己控制密钥）。SME 先用云端版验证价值，涉及敏感数据时可一键迁移到私有化。这跟 Anthropic 自己的 Claude Enterprise 策略一致——先让客户用起来，再解决最严格的合规需求。"

---

### 盲点 6：没有竞品 AI 能力对比

**Nicolas Lin 会怎么做：**

他在 Claude for FS 的 launch 中用了 **Vals AI Finance Agent Benchmark** 来做能力背书。你也需要一个可量化的对比：

```
不要泛泛说 "我们面向 SME"。而是：

"在我们的 100 张凭证测试集上：
  - Claude Sonnet + 我们的审计 prompt: Precision 78%, Recall 92%
  - 直接用 GPT-4o: Precision 65%, Recall 81%
  - 纯规则引擎（无 LLM）: Precision 85%, Recall 55%
  - MindBridge (从官方白皮书): Precision ~90%, Recall ~88% (但年费 $50K+）"
```

**竞品不是你的敌人，是你的定价锚点：**

| 竞品 | 定价 | 能力 | 你的定位 |
|---|---|---|---|
| MindBridge | $50K+/年 | Precision ~90% | "我们 Recall 更高（92% vs 88%），价格 1/50" |
| AppZen | $30K+/年 | 只做费用报销 | "我们覆盖全凭证类型" |
| 人工审计 | $200-500/小时 | Precision 高但 Recall 低（只抽 5%） | "我们 100% 覆盖，$130/月" |

---

### 盲点 7：Prompt 没有被当作核心资产管理

**Nicolas Lin 会怎么做：**

Claude for FS 的 pre-built Agent Skills（DCF、Comp Analysis 等）本质上就是 **prompt 产品化**。每个 Skill 都经过：

```
1. 版本管理（像代码一样）
2. 评测集验证（每次改动跑回归）
3. A/B 测试（新版 vs 旧版，比较指标）
4. 灰度发布（先给 10% 用户，观察指标再全量）
```

**你应该这样管理 prompt：**

```
prompts/
├── v1.0/
│   ├── extraction_invoice.txt       # 发票字段提取 prompt
│   ├── extraction_receipt.txt       # 收据字段提取 prompt
│   ├── audit_reasoning.txt          # 审计推理 prompt
│   ├── risk_summary.txt             # 风险摘要生成 prompt
│   └── CHANGELOG.md                 # 每次改动记录原因和效果
├── v1.1/
│   ├── extraction_invoice.txt       # 改了什么、为什么改、golden set 指标变化
│   └── ...
└── eval/
    ├── run_eval.py                  # 一键跑评测
    ├── compare_versions.py          # 对比两个版本的指标差异
    └── results/
        ├── v1.0_results.json
        └── v1.1_results.json
```

**关键规则：**
- **永远不改 production prompt 不跑回归** — 跟 "不跑测试不上线" 一样
- **每个 prompt 有 owner** — 审计推理的 prompt 由了解审计逻辑的人维护，不是随便一个工程师
- **Prompt 变更需要 review** — 像 code review 一样，PR + approval

---

## Nicolas Lin 视角下的额外 5 个问题（你还没想到的）

---

### Q1: "你的产品是 Tool 还是 Platform？这决定你的商业模式。"

```
Tool = 客户用你来做一件事（扫描凭证）
  → 按次/按量收费
  → 天花板低，容易被替代

Platform = 客户在你上面构建审计流程
  → 按席位/按企业收费
  → 客户的审计规则、历史数据、行为基线都沉淀在你这里 → 迁移成本高

Nicolas 的答案: 从 Tool 切入，但数据沉淀让你变成 Platform。
  V1: Tool（扫描 → 标红 → 通知）
  V2: 审计规则可自定义 → 客户开始沉淀自己的规则
  V3: 历史数据 + 行为基线 → 客户离不开你了
```

### Q2: "你的 moat 不是 AI，是 workflow embedding。"

```
Nicolas 在 Claude for FS 的策略:
  不是 "Claude 比 GPT 聪明" → 而是 "Claude 已经接入了 LSEG/FactSet/S&P 的数据"
  不是 "我们的模型更准" → 而是 "客户的分析师已经习惯在 Claude 里跑 DCF"

映射到你的产品:
  你的壁垒不是 "Precision 78%" → 而是:
    - CFO 已经习惯在飞书群里看审计推送
    - 审计规则已经按这个企业的业务定制过了
    - 3 个月的历史数据基线已经建好了
    - 所有审计记录都在你的系统里（迁移 = 丢审计底稿）
```

### Q3: "LLM 的不确定性不是 bug，是 feature——如果你这样框定它。"

```
大部分 AI 产品的错误: 把 LLM 输出当作"答案"呈现
Nicolas 的做法: 把 LLM 输出当作"建议"呈现，附带 citations

你的产品应该这样:
  ❌ "这笔交易存在欺诈风险（高）"
  ✅ "这笔交易触发了 2 条规则，AI 审计建议关注以下 3 点：
      1. 金额 ¥49,900 接近 ¥50,000 审批阈值 [规则: 拆单检测]
      2. 供应商「XX公司」近 30 天内第 4 次出现 [规则: 高频供应商]
      3. 发票开具日为周日 [规则: 非工作日]
      置信度: 82% | 建议: 人工复核 | 类似历史案例: 3 笔"

区别:
  前者 → 用户要么信要么不信 → 没有中间地带
  后者 → 用户可以逐条验证 → 信任逐步建立 → 即使 AI 错了，用户也能看出为什么错了
```

### Q4: "你考虑过内部欺诈者会反向利用你的系统吗？"

```
场景: 你的审计助手会暴露审计规则（"金额 > 5000 的整数会被标红"）
  → 聪明的内部欺诈者会学习：把 ¥50,000 拆成 ¥49,999.50 + ¥0.50
  → 你的规则被「博弈」了

Nicolas 的思维: 在 Anthropic 的安全框架里，有专门的 Safeguards 团队做对抗性测试

你的应对:
  1. 不要在用户界面展示触发了"哪条规则" → 只展示风险等级和审计建议
  2. 规则权重随机化 → 不是固定阈值，而是动态调整
  3. V2 的 Reviewer Agent 专门做"如果我是欺诈者，我会怎么绕过这些规则"的对抗性检查
```

### Q5: "你的定价应该跟客户省了多少钱挂钩，而不是你花了多少成本。"

```
成本定价: $130/月 → 客户觉得"AI 工具就值这个价"
价值定价: "帮你避免了一笔 ¥50,000 的欺诈 = 你付我们 ¥5,000"

但 V1 还不能做价值定价（因为你还没证明能真的抓到欺诈）

正确的路径:
  V1: 免费 / ¥499/月（低门槛获客，积累案例）
  V1.1: 收集到 "我们帮客户 A 发现了 ¥200,000 的虚假报销" 的案例
  V2: ¥2,999/月 或 按节省金额的 5% 抽成（有案例背书了）
  V3: 按企业规模阶梯定价（¥999-9,999/月）
```

---

## 总结：Nicolas Lin 的方法论映射到你的产品

```
Anthropic 做 Claude for FS 的路径:
  ① 选准 use case（投研分析，不是全金融）
  ② 接数据源（LSEG/FactSet/S&P = 你的飞书/财务系统）
  ③ Citations + Human-in-the-Loop（不号称完美，让验证变容易）
  ④ 先 targeted use cases，量化 ROI（85% 生产力提升 / 2.5 小时/周）
  ⑤ 用案例说话，再扩规模（HUB 20,000 人，NBIM 20% 效率提升）

你做 Anti-Fraud 审计的路径（映射）:
  ① 选准 use case → 全量凭证扫描（不是全审计流程）
  ② 接数据源 → 飞书 + 财务系统（不自建数据）
  ③ 展示 AI 判断依据 → 每条标红都有可追溯的规则/证据
  ④ 先 5 个客户，量化 "审计时间减少 X%" + "发现 Y 笔此前漏检的异常"
  ⑤ 用案例获客 → "某制造业 SME 用我们发现了 ¥30 万虚假报销"
```

---

*Generated: 2026-03-12 | Nicolas Lin Perspective Analysis*
*Ashley Chen — Product Thinking × AI in Finance*

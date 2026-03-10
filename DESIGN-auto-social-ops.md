# Multi-Agent 社交媒体自动运营系统设计

## 目标

从现有的「手动触发 → 单次生成」pipeline，演进为「自动发现 → 自动发布 → 自动反馈 → 自动调整」的全闭环运营系统。

---

## 现有架构 vs 目标架构

```
现有（手动触发，单次执行）:

  用户 → /content-agent [topic] → 生成脚本 → 手动发布 → 手动看数据 → 手动调整

目标（自动闭环，持续运行）:

  ┌─────────────────────────────────────────────────────────┐
  │                    Daily Loop (自动)                      │
  │                                                         │
  │  新闻监控 → 选题排期 → 内容生成 → 人工审批 → 自动发布   │
  │      ↑                                          │       │
  │      └──── 数据回收 ← 效果分析 ←────────────────┘       │
  │                  │                                       │
  │            策略调整（周级）                                │
  └─────────────────────────────────────────────────────────┘
```

---

## 系统架构：6 个 Agent + 1 个调度器

```
                    ┌──────────────────────┐
                    │   Scheduler Agent    │
                    │   (每日调度中心)       │
                    └──────┬───────────────┘
                           │
          ┌────────────────┼────────────────────┐
          │                │                    │
          ▼                ▼                    ▼
    ┌──────────┐    ┌──────────┐         ┌──────────┐
    │  Scout   │    │ Creator  │         │ Analyst  │
    │  Agent   │    │  Agent   │         │  Agent   │
    │ (新闻发现) │    │ (内容生成) │         │ (数据分析) │
    └────┬─────┘    └────┬─────┘         └────┬─────┘
         │               │                    │
         ▼               ▼                    ▼
    ┌──────────┐    ┌──────────┐         ┌──────────┐
    │ Planner  │    │Publisher │         │ Strategist│
    │  Agent   │    │  Agent   │         │  Agent   │
    │ (选题排期) │    │ (自动发布) │         │ (策略调整) │
    └──────────┘    └──────────┘         └──────────┘
```

---

## Agent 详细设计

### Agent 1: Scout Agent（新闻发现）

**职责：** 每日自动扫描相关新闻和热点，生成候选素材池

**运行频率：** 每天 2 次（早 8 点 + 晚 6 点 UTC）

**数据源：**
| 来源 | 方法 | 频率 |
|------|------|------|
| 行业新闻 | WebSearch: "AI finance" + "fintech" + 关键词列表 | 每次 5-8 个 query |
| X/Twitter | X API v2 search: 监控 KOL 列表 + 话题标签 | 实时/批量 |
| LinkedIn | LinkedIn API: 监控行业 influencer 动态 | 每日 |
| Reddit | Reddit API: r/finance, r/artificial, r/fintech | 每日 |
| 小红书 | 爬虫/RSS: 金融+AI 相关话题 | 每日 |
| arXiv/论文 | arXiv API: cs.AI + q-fin 分类 | 每周 |

**输出：** 候选素材清单（每天 10-15 条）

```yaml
# scout-output.yaml 示例
date: 2026-03-10
candidates:
  - id: scout-20260310-001
    source: "Financial Times"
    url: "https://..."
    title: "JPMorgan deploys AI agents for trade settlement"
    relevance_score: 9/10
    timeliness: "breaking (< 6h)"
    angle_potential:
      - "AI agent 在金融后台的真实落地"
      - "从 copilot 到 agent 的转变"
      - "skill repricing: settlement 岗位的未来"
    platform_fit:
      linkedin: high  # 行业深度
      x: medium       # 需要简化
      xiaohongshu: low # 太专业
    tier: 1
```

**关键设计：**
- 维护一个 **关键词列表**（存在 memory 中，Strategist Agent 可以调整）
- 维护一个 **KOL 监控列表**（竞品 + 灵感来源）
- **去重逻辑：** 与 content-memory 中已发布话题做相似度检查，避免重复

---

### Agent 2: Planner Agent（选题排期）

**职责：** 从 Scout 的候选池中选题，安排发布计划

**运行频率：** 每天 1 次（Scout 之后）

**选题决策模型：**

```
Score = (Relevance × 0.3) + (Timeliness × 0.25) + (Angle_Uniqueness × 0.25) + (Platform_Fit × 0.2)

过滤规则：
- content-memory 中 30 天内有相似话题 → 降权 50%
- Strategist 标记的「高优先话题方向」→ 加权 30%
- 连续 2 天同一 hook formula → 强制切换
```

**输出：** 每日发布计划

```yaml
# daily-plan.yaml
date: 2026-03-10
posts:
  - slot: "morning"  # 早上发布
    time: "08:30 EST"
    mode: "--fast"
    topic: "JPMorgan AI agents for trade settlement"
    source_id: scout-20260310-001
    platform: linkedin
    hook_formula: "data-shock"
    reason: "breaking news + 高行业相关性"

  - slot: "afternoon"
    time: "14:00 EST"
    mode: "--deep"
    topic: "从 Copilot 到 Agent: 金融后台自动化的三个阶段"
    source_id: scout-20260310-001  # 同一新闻的深度延伸
    platform: [linkedin, x]
    hook_formula: "counter-intuitive"
    reason: "anchor post for the week"

  - slot: "evening-cn"
    time: "20:00 CST"
    mode: "--fast"
    topic: "摸鱼时间：JPMorgan用AI agent替代了什么岗位"
    platform: xiaohongshu
    hook_formula: "identity-mirror"
    reason: "小红书热度窗口"
```

**人工审批节点（关键）：**
```
Planner 输出计划 → 推送到用户（Slack/邮件/Telegram）→ 等待确认
  - 用户回复 "ok" → 进入 Creator Agent
  - 用户回复 "skip 2" → 跳过第 2 条
  - 用户回复 "swap topic" → 从候选池选替代
  - 30 分钟无回复 → 自动执行（如果用户设置了 auto-approve）
```

---

### Agent 3: Creator Agent（内容生成）

**职责：** 基于排期计划生成内容（复用现有 pipeline）

**核心逻辑：** 直接调用现有 skill chain

```
--deep mode:
  brave-research → script-analyzer → blindspot-detector → kobo-optimizer

--fast mode:
  script-analyzer → kobo-optimizer
```

**新增能力：**

1. **Batch 模式：** 一次处理当天所有排期内容，而不是逐条触发
2. **Platform-native 格式化：**
   - LinkedIn: 生成纯文本 + 推荐配图关键词
   - X: 生成 thread 格式（含 tweet 编号和字数校验）
   - 小红书: 生成中文脚本 + 封面文案 + 标签

**输出：** 可发布的内容包

```yaml
# content-package.yaml
post_id: "post-20260310-001"
topic: "JPMorgan AI agents for trade settlement"
created_at: "2026-03-10T07:45:00Z"

linkedin:
  text: |
    JPMorgan just quietly deployed AI agents
    that settle trades in 12 seconds.

    That used to take a human analyst 4 hours.

    [PAUSE]

    But here's what nobody's talking about...
    ...
  hashtags: ["#AIinFinance", "#FutureOfWork", "#FinTech"]
  image_prompt: "futuristic trading floor with AI overlay"
  estimated_read_time: "75 seconds"

x_thread:
  tweets:
    - "JPMorgan's AI agents now settle trades in 12 seconds. It used to take 4 hours. Here's why this matters more than you think 🧵"
    - "1/ The obvious story: AI makes things faster..."
    # ...

xiaohongshu: null  # 不适合此话题

quality_scores:
  hook: 8/10
  authenticity: 7/10
  actionability: 8/10
  reflection_checks: 7/8

status: "pending_review"  # 等待人工最终确认
```

---

### Agent 4: Publisher Agent（自动发布）

**职责：** 将审批通过的内容发布到各平台

**API 集成：**

| 平台 | API | 关键功能 |
|------|-----|---------|
| LinkedIn | LinkedIn Marketing API (OAuth 2.0) | 发帖、发图文、获取互动数据 |
| X/Twitter | X API v2 (OAuth 2.0) | 发 tweet、thread、获取 metrics |
| 小红书 | 小红书开放平台 / 第三方工具 | 发帖（可能需要半自动） |

**发布流程：**

```
1. 检查 content-package 状态 = "approved"
2. 按排期时间发布
3. 发布成功 → 记录 post_id（平台返回的）到 content-memory
4. 发布失败 → 重试 2 次 → 失败则通知用户
5. 发布后立即记录 auto-log（现有 content-memory Layer 1）
```

**发布时间优化：**
```
LinkedIn:  周二-周四 08:00-09:00 EST (B2B 高峰)
X:         周一-周五 12:00-13:00 EST (午休刷推)
小红书:     每天 20:00-22:00 CST (晚间高峰)
```

**安全设计：**
- 每天最多发布 3 条（硬限制，防止异常情况刷屏）
- 首次运行 7 天内强制人工审批每一条
- 敏感词检测（金融监管相关词汇自动触发人工审核）

---

### Agent 5: Analyst Agent（数据分析）

**职责：** 自动回收发布数据，生成每日/每周 performance report

**运行频率：**
- 发布后 2h: 首次数据快照（early signal）
- 发布后 24h: 标准数据回收
- 发布后 48h: 最终数据更新
- 每周日: 周报汇总

**回收的数据：**

```yaml
# analytics-20260310-001.yaml
post_id: "post-20260310-001"
platform: "linkedin"

metrics_2h:
  impressions: 340
  likes: 12
  comments: 3
  saves: 8
  shares: 2
  click_through: 15

metrics_24h:
  impressions: 2100
  likes: 47
  comments: 12
  saves: 31
  shares: 8
  click_through: 89

metrics_48h:
  impressions: 3200
  likes: 62
  comments: 18
  saves: 45
  shares: 11
  click_through: 112

derived:
  save_rate: 1.4%          # saves / impressions
  engagement_rate: 4.2%     # (likes+comments+saves+shares) / impressions
  comment_quality: "high"   # 有实质讨论 vs 纯表情
  viral_coefficient: 0.34   # shares / impressions (传播力)
  early_signal_accuracy: 0.82  # 2h数据与48h数据的相关性
```

**Daily Report（自动生成，推送到用户）：**

```
📊 Daily Performance — 2026-03-10

Posts published: 2 (LinkedIn: 2, X: 1)

Best performer:
  "JPMorgan AI agents" (LinkedIn)
  → 3200 impressions | 45 saves (1.4% save rate) | 18 comments
  → Hook: Data Shock | Anchor: Industry News

Underperformer:
  "从 Copilot 到 Agent" (X Thread)
  → 800 impressions | 5 RTs
  → Likely cause: too long for X format, thread >5 tweets

7-day rolling averages:
  LinkedIn save rate: 1.1% (↑ from 0.8% last week)
  X engagement: 2.3% (↓ from 2.8%)

Action items for Strategist Agent:
  - X thread format needs tightening (see underperformer)
  - Data Shock hooks outperforming Counter-Intuitive 2:1 this week
```

---

### Agent 6: Strategist Agent（策略调整）

**职责：** 基于 Analyst 的数据，调整 Scout 和 Planner 的行为参数

**运行频率：** 每周 1 次（周日晚）+ 异常触发

**调整的参数：**

```yaml
# strategy-config.yaml（Strategist 可修改，其他 Agent 读取）

content_strategy:
  # Scout Agent 参数
  keywords_priority:
    - "AI agents finance"       # weight: 1.2 (上周效果好)
    - "LLM trading"             # weight: 0.8 (上周效果一般)
    - "AI regulation banking"   # weight: 1.0 (新增)

  kol_watchlist:
    - "@AlliKMiller"
    - "@ChrisSkinner"
    - "@jimmarous"
    # Strategist 可以增删

  # Planner Agent 参数
  weekly_mix:
    deep_posts: 1-2
    fast_posts: 2-3
    total_max: 5

  hook_formula_weights:
    data_shock: 1.3        # 本周表现最好
    counter_intuitive: 0.9  # 略降
    problem_solution: 1.0
    identity_mirror: 1.1   # 小红书效果好

  platform_priority:
    linkedin: 1     # 始终第一
    x: 2
    xiaohongshu: 3

  # 发布时间（Analyst 数据驱动调整）
  best_times:
    linkedin: "08:15 EST"   # 从 08:30 微调
    x: "12:30 EST"
    xiaohongshu: "21:00 CST"

  # 质量阈值
  min_hook_score: 7         # 低于此分不发布
  min_save_rate_target: 1.0%  # 低于此的话题方向降权
```

**策略调整逻辑（周度）：**

```
1. 读取本周所有 Analyst 报告
2. 计算各维度表现：
   - 按 hook_formula 分组 → 更新权重
   - 按 anchor_type 分组 → 更新 Scout 优先级
   - 按 platform 分组 → 更新发布时间和频率
   - 按 topic_category 分组 → 更新关键词权重
3. 生成 Strategy Update（推送给用户）:
   - 本周最佳内容模式
   - 本周最差内容模式
   - 参数调整建议（人工确认后生效）
4. 更新 strategy-config.yaml
```

**异常触发：**
- 连续 3 条 post 的 save_rate < 0.5% → 立即触发策略检查
- 某条 post engagement_rate > 5% → 标记为「爆款」，分析原因并更新策略

---

## 整体运行时序（一天）

```
06:00 UTC  Scout Agent 第一轮扫描
           ├── WebSearch × 8 queries
           ├── X API: 过去 12h KOL 动态
           ├── Reddit API: 热帖
           └── 输出: 候选素材池 (10-15 条)

07:00 UTC  Planner Agent
           ├── 读取候选池
           ├── 读取 strategy-config.yaml
           ├── 读取 content-memory (去重)
           ├── 生成当日排期 (2-3 条)
           └── 推送排期给用户审批

07:30 UTC  用户审批
           └── 确认 / 修改 / 跳过

08:00 UTC  Creator Agent (batch)
           ├── Post 1: --fast (晨间快评)
           ├── Post 2: --deep (深度分析)
           └── 生成 content-packages

09:00 UTC  Publisher Agent
           └── 发布 Post 1 → LinkedIn (08:30 EST)

14:00 UTC  Publisher Agent
           └── 发布 Post 2 → LinkedIn + X (09:00 EST / 14:00 UTC)

16:00 UTC  Analyst Agent (2h 快照)
           └── 回收 Post 1 early metrics

18:00 UTC  Scout Agent 第二轮扫描
           └── 补充下午的新素材 → 更新候选池

次日 09:00  Analyst Agent (24h 数据)
           └── 回收前一天所有 post 的标准数据

次日+1 09:00  Analyst Agent (48h 最终数据)
              └── 最终数据 → 写入 content-memory

每周日 22:00  Strategist Agent
              ├── 读取本周所有 Analyst 报告
              ├── 计算各维度表现趋势
              ├── 生成策略调整建议
              └── 更新 strategy-config.yaml（人工确认后）
```

---

## 人工介入点（Human-in-the-Loop）

全自动不等于零人工。以下节点 **必须** 保留人工审批：

| 节点 | 原因 | 自动化条件 |
|------|------|-----------|
| 每日排期确认 | 防止不合适的话题被发布 | 运行 30 天 + 用户显式开启 auto-approve |
| 内容最终审核 | 防止错误数据/不当表述 | 仅 --fast 模式可跳过（已有 quality gate） |
| 策略参数调整 | 防止数据漂移导致方向偏离 | 永不全自动 — 策略由人控制 |
| 敏感话题拦截 | 金融监管、争议话题 | 永不全自动 |

**渐进式放权：**
```
Week 1-2:  每条内容人工审批（建立信任）
Week 3-4:  --fast 模式自动发布，--deep 仍需审批
Month 2+:  全部自动发布，但敏感话题仍拦截
始终保持: 策略调整需人工确认
```

---

## 技术实现建议

### 方案 A: Claude Code Skills + Cron（最小可行方案）

```
调度: cron job / GitHub Actions scheduled workflow
Agent: 每个 Agent 是一个 Claude Code skill
状态: YAML 文件存在 repo 中
API: 直接调用 X API / LinkedIn API
通知: Telegram Bot / Slack Webhook
```

**优点：** 基于现有架构，改动最小
**缺点：** cron 调度不够灵活，跨 Agent 状态管理需要自己处理

### 方案 B: Claude Agent SDK + Task Queue（推荐）

```
调度: Claude Agent SDK 的 agent loop
Agent: 每个 Agent 是一个 SDK agent (Python)
状态: SQLite / Postgres（结构化存储）
API: 通过 MCP servers 接入各平台
通知: MCP server for Slack/Telegram
```

**优点：** 原生 agent 调度，MCP 生态丰富，状态管理更可靠
**缺点：** 需要部署 Python 服务

### 方案 C: 混合方案（实用主义）

```
Phase 1: 用现有 Skills 实现 Scout + Planner + Creator（手动触发）
Phase 2: 加入 Publisher Agent（API 集成，最难的部分先跑通）
Phase 3: 加入 Analyst Agent（数据回收自动化）
Phase 4: 加入 Strategist Agent + 全流程调度
```

**推荐 Phase 1 先落地的原因：**
- Scout + Planner 是现有 pipeline 缺失的最大功能
- 不需要任何外部 API（纯 WebSearch）
- 立刻提升效率：从「想话题」变成「选话题」

---

## 数据流与存储设计

```
~/.claude/
├── skills/
│   ├── scout-agent/SKILL.md          # 新增
│   ├── planner-agent/SKILL.md        # 新增
│   ├── publisher-agent/SKILL.md      # 新增
│   ├── analyst-agent/SKILL.md        # 新增
│   ├── strategist-agent/SKILL.md     # 新增
│   ├── content-agent/SKILL.md        # 改造：读取 daily-plan
│   ├── brave-research/SKILL.md       # 不变
│   ├── script-analyzer/SKILL.md      # 不变
│   ├── blindspot-detector/SKILL.md   # 不变
│   ├── kobo-optimizer/SKILL.md       # 不变
│   └── content-memory/SKILL.md       # 扩展：接收 Analyst 数据
│
├── data/                              # 新增：运营数据目录
│   ├── scout-pool/                    # 每日候选素材
│   │   └── 2026-03-10.yaml
│   ├── daily-plans/                   # 每日排期
│   │   └── 2026-03-10.yaml
│   ├── content-packages/              # 待发布内容包
│   │   └── post-20260310-001.yaml
│   ├── analytics/                     # 发布数据
│   │   └── post-20260310-001.yaml
│   └── strategy-config.yaml           # 策略参数（唯一）
│
└── projects/-Users-ashleychen/memory/
    ├── MEMORY.md                      # 不变
    └── content-sessions.md            # 扩展：Analyst 自动写入
```

---

## 与现有架构的关系

```
现有 Skills（保留，作为 Creator Agent 的内部调用）:
  brave-research → script-analyzer → blindspot-detector → kobo-optimizer → content-memory

新增 Agents（包裹在现有 pipeline 外层）:
  Scout → Planner → [Creator = 现有 pipeline] → Publisher → Analyst → Strategist
                                                                        │
                                                                        ▼
                                                              更新 Scout + Planner 参数
```

核心原则：**新系统包裹旧系统，不替换旧系统。** 所有现有 skills 保持原样，新 Agent 在外层编排。

---

## 实施优先级

| Phase | 内容 | 工作量 | 价值 |
|-------|------|--------|------|
| **Phase 1** | Scout Agent + Planner Agent | 2-3 天 | 高：解决「每天想话题」的痛点 |
| **Phase 2** | Analyst Agent（数据回收） | 2-3 天 | 高：闭合反馈循环 |
| **Phase 3** | Publisher Agent（API 集成） | 3-5 天 | 中：省去手动复制粘贴 |
| **Phase 4** | Strategist Agent（策略自动调整）| 2-3 天 | 中：需要 Phase 2 的数据积累 |
| **Phase 5** | 全流程调度 + 渐进式放权 | 3-5 天 | 高：真正的自动化 |

**建议从 Phase 1 开始** — Scout + Planner 不需要任何 API key，可以立刻开始用。

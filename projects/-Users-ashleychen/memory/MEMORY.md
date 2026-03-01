# Memory

## Content Creation Agent Workflow
Built a 口播 video content agent workflow using Claude Code Skills.

### Custom Skills Created (in ~/.claude/skills/)
- `script-analyzer` — Analyzes viral content patterns, hook formulas, benchmark account styles
- `blindspot-detector` — Devil's advocate: counterarguments, missing data, differentiation gaps
- `kobo-optimizer` — Final script optimizer: LinkedIn (60-90s), X Thread (5-7 tweets), 小红书 (Chinese)

### Workflow Order (v2 — Manus-inspired architecture)

**Single entry point (recommended):**
```
/content-agent [topic]   → runs full pipeline with Plan-Execute-Verify
```

**Manual stage-by-stage (still available):**
```
/brave-research [topic]      → Stage 0: gather real data + source verification
/script-analyzer [topic]     → Stage 1: viral pattern analysis + self-verify
/blindspot-detector [topic]  → Stage 2: adversarial stress test + verdict gate
/kobo-optimizer [draft]      → Stage 3: Draft→Critique→Revise→Freeze
/content-memory log          → Stage 4: log session for learning
```

### Architecture Patterns Applied (2026)
- Manus Plan-Execute-Verify: each stage has explicit pass/fail gate, loops back on failure
- Reflection Loop (Draft→Critique→Revise→Freeze): built into kobo-optimizer
- Orchestrator + Subagent: content-agent coordinates all skills, manages state
- Memory-Augmented: content-memory persists learnings across sessions
- Verification Gates: blindspot-detector issues PROCEED/REVISE/NEEDS RESEARCH verdict

### User Positioning
- Core angle: product thinking applied to AI in Finance
- Primary platform: LinkedIn (English)
- Secondary: X/Twitter
- Auxiliary: 小红书 (Chinese)
- Target audience: English-speaking finance professionals + AI practitioners

### Key Notes
- LinkedIn AI content gets ~30% less reach — inject personal voice aggressively
- LinkedIn algorithm: saves > likes > comments for reach
- 小红书: authenticity > production quality

---

## 对话记录摘要（2026-02-28）

### 测试选题：AI如何改变finance analyst的日常工作

**Script Analyzer 结论：**
- 最佳 Hook 公式：Data Shock（JPMorgan 具体数据开场）
- 备选 Hook 中最强：个人故事版（"4小时→40分钟"，需有真实经历支撑）
- 对标账号：Ronit Ghose（复杂概念简单化）+ Jim Marous（数字金融转型）
- 核心差异化角度：**技能重定价**（skill repricing）——AI 不只是加速旧工作流，而是改变了哪些技能有价值
- 整体爆款潜力：8/10

**Blindspot Detector 结论（5个关键盲点）：**
1. JPMorgan "12秒" 数据未经核实，需找真实来源或改为有引用的统计
2. 缺少个人故事锚点——必须加入一个具体的亲身经历才能与他人区分
3. 选题范围太宽（IB/FP&A/资管都涵盖），需明确聚焦或显式说明
4. "产品思维"术语需翻译成金融语言（如"把技能当投资组合来管理"）
5. 小红书版本需本地化：换成国内机构（中金/华泰），用"金融民工"语气

**下一步：** 用户需提供个人故事后，运行 `/kobo-optimizer` 生成最终三平台脚本

### 用户偏好
- 希望对话内容保存在 memory 中，方便跨会话延续

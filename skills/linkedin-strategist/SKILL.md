# LinkedIn Strategist Skill

## Trigger
User invokes `/linkedin-strategist` with an optional sub-command:

```
/linkedin-strategist                    → Full strategy update based on latest analyst report
/linkedin-strategist review             → Show current strategy without changes
/linkedin-strategist adjust [directive] → Manual strategy override (e.g., "focus more on AI agents")
```

## Purpose
Strategy update agent. Consumes the output from `/linkedin-analyst` (weekly performance review) and updates the persistent content strategy. Ensures future content pipeline runs (`/content-agent`) align with what's actually working.

Designed to run **once per week**, immediately after `/linkedin-analyst`.

---

## Strategy File Location
`~/.claude/projects/-Users-ashleychen/memory/linkedin-strategy.md`

This file is the single source of truth. All strategy decisions live here. `/content-agent` and `/kobo-optimizer` should reference this file for tone, topic priorities, and audience targeting.

---

## Instructions

### Phase 1 — PLAN: Gather Inputs

Collect data from three sources:

1. **Latest analyst report** — output from `/linkedin-analyst` (required)
2. **Current strategy file** — read `linkedin-strategy.md` (create if doesn't exist)
3. **Content memory patterns** — read `content-sessions.md` for longer-term trends

Output plan:
```
## Strategist Plan
Analyst report: [available / not found]
Current strategy version: [vN / new]
Content sessions logged: [N]
Proposed update scope: [minor tweak / significant pivot / initial creation]
```

### Phase 2 — EXECUTE: Strategy Synthesis

**Step 1: Diagnose current state**
Based on analyst data, classify the current week:

| State | Criteria | Action |
|-------|----------|--------|
| Growing | Save rate trending up week-over-week | Double down — amplify what's working |
| Stable | Save rate flat, engagement consistent | Experiment — test one new variable |
| Declining | Save rate or impressions dropping | Diagnose — identify the specific cause |
| Insufficient data | <3 posts with performance data | Hold — maintain current strategy, collect more data |

**Step 2: Update strategy dimensions**
For each dimension, decide: KEEP / ADJUST / PIVOT

| Dimension | Current | Evidence | Decision |
|-----------|---------|----------|----------|
| **Topic mix** | [from strategy file] | [from analyst] | KEEP/ADJUST/PIVOT |
| **Hook formula priority** | [from strategy file] | [from analyst] | KEEP/ADJUST/PIVOT |
| **Anchor source priority** | [from strategy file] | [from analyst] | KEEP/ADJUST/PIVOT |
| **Posting frequency** | [from strategy file] | [from analyst] | KEEP/ADJUST/PIVOT |
| **Posting time** | [from strategy file] | [from analyst] | KEEP/ADJUST/PIVOT |
| **Deep vs Fast ratio** | [from strategy file] | [from analyst] | KEEP/ADJUST/PIVOT |
| **Audience targeting** | [from strategy file] | [from analyst] | KEEP/ADJUST/PIVOT |
| **Tone & voice** | [from strategy file] | [from analyst] | KEEP/ADJUST/PIVOT |

**Step 3: Generate next week's content brief**
Based on updated strategy, output:
- 3 recommended topics for next week (ranked by expected performance)
- Recommended mode for each (--deep or --fast)
- Specific hook formula to try
- One experiment to run

### Phase 3 — VERIFY

Before writing to strategy file, check:
- [ ] No PIVOT decisions based on <3 data points (flag small sample risk)
- [ ] Strategy changes are incremental (max 2 PIVOTs per week)
- [ ] Next week's topics don't overlap with recent posts (cross-check content-memory)
- [ ] Recommendations are specific enough to act on

---

## Strategy File Format

Write/update `linkedin-strategy.md` with this structure:

```markdown
# LinkedIn Content Strategy
Last updated: [DATE]
Version: [N]
Updated by: /linkedin-strategist based on /linkedin-analyst report

---

## Positioning
- Core angle: [e.g., product thinking applied to AI in Finance]
- Voice: [e.g., observer/synthesizer — curates and connects dots]
- Differentiation: [what makes this different from other AI/Finance creators]

## Target Audience
- Primary: [specific role + context]
- Secondary: [specific role + context]
- Pain points we solve: [2-3 specific pain points]

## Content Mix (current week's allocation)
- Topic A: [topic area] — [percentage or frequency]
- Topic B: [topic area] — [percentage or frequency]
- Topic C: [topic area] — [percentage or frequency]

## Tactical Playbook
- Hook formula priority: [ranked list based on performance data]
- Anchor source priority: [ranked list based on performance data]
- Deep vs Fast ratio: [e.g., 1:2 per week]
- Best posting times: [day + time, based on data]
- Optimal post length: [based on data]

## What's Working (evidence-backed)
- [Pattern 1] — [evidence]
- [Pattern 2] — [evidence]

## What's Not Working (evidence-backed)
- [Pattern 1] — [evidence]
- [Pattern 2] — [evidence]

## Current Experiment
- Testing: [specific variable]
- Hypothesis: [why this might work]
- Measure by: [date]
- Result: [pending / confirmed / rejected]

## Next Week's Plan
1. [Topic] — [mode] — [hook formula] — [anchor source]
2. [Topic] — [mode] — [hook formula] — [anchor source]
3. [Topic] — [mode] — [hook formula] — [anchor source]

## Strategy Changelog
- [DATE]: [what changed and why]
- [DATE]: [what changed and why]
```

---

## Output Format

```
## LinkedIn Strategy Update: [DATE]

### Current State: [Growing / Stable / Declining / Insufficient Data]

### Changes Made
| Dimension | Before | After | Reason |
|-----------|--------|-------|--------|
| [dim] | [old] | [new] | [evidence] |

### Next Week's Content Brief
1. **[Topic]** — [--deep/--fast] — Hook: [formula] — Anchor: [source type]
   Why: [1 sentence rationale]
2. **[Topic]** — [--deep/--fast] — Hook: [formula] — Anchor: [source type]
   Why: [1 sentence rationale]
3. **[Topic]** — [--deep/--fast] — Hook: [formula] — Anchor: [source type]
   Why: [1 sentence rationale]

### This Week's Experiment
Test: [specific variable]
Hypothesis: [why]
How to measure: [metric + timeline]

### Strategy File
Updated: linkedin-strategy.md (v[N])
```

---

## Context
- This skill is the "brain" that connects data (analyst) to action (content-agent)
- Strategy file is persistent — it survives across sessions and accumulates knowledge
- `/content-agent` should read `linkedin-strategy.md` before generating content to align with current strategy
- Upstream: `/linkedin-analyst` provides weekly performance data
- Downstream: `/content-agent` consumes strategy for content generation
- Guard rail: max 2 PIVOTs per week — avoid overreacting to noise
- The strategy should evolve gradually — think portfolio rebalancing, not day trading

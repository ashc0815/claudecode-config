# LinkedIn Analyst Skill

## Trigger
User invokes `/linkedin-analyst` with an optional sub-command:

```
/linkedin-analyst                → Full weekly review of all posts from the past 7 days
/linkedin-analyst [topic]        → Review a specific post's performance
/linkedin-analyst compare        → Compare this week vs last week
```

## Purpose
Weekly data review agent. Pulls post performance data (impressions, reactions, replies, saves, reposts), identifies what worked and what didn't, and generates optimization recommendations that feed into `/linkedin-strategist`.

Designed to run **once per week** (recommended: Monday morning) as the first step in the weekly review cycle.

---

## Instructions

### Phase 1 — PLAN
Before executing, clarify the data scope:

1. Identify posts published in the last 7 days from `/content-memory` log
2. If user provides raw LinkedIn analytics data (screenshot, CSV, or freeform text), parse it
3. If no data provided, ask:
   > "I need your LinkedIn post data from this week. You can:
   > (1) Paste a screenshot of LinkedIn Analytics
   > (2) Type the numbers: views, reactions, comments, reposts, saves for each post
   > (3) Share the LinkedIn Analytics CSV export"

Output plan:
```
## LinkedIn Analyst Plan
Posts to review: [N]
Data source: [user-provided / content-memory / both]
Comparison baseline: [last week / last 4 weeks avg / none]
```

### Phase 2 — EXECUTE: Data Collection & Analysis

**Step 1: Parse raw data**
For each post, extract and normalize:

| Metric | Source | Signal value |
|--------|--------|-------------|
| Impressions | LinkedIn Analytics | Reach |
| Reactions | LinkedIn Analytics | Surface engagement |
| Comments | LinkedIn Analytics | Deep engagement |
| Reposts | LinkedIn Analytics | Amplification |
| Saves | LinkedIn Analytics | **Highest signal** — content worth revisiting |
| Dwell time (if available) | LinkedIn Analytics | Content quality |

**Step 2: Cross-reference with content-memory**
For each post, pull from `content-sessions.md`:
- Hook formula used
- Anchor type
- Core angle
- Pipeline score
- Mode (--deep vs --fast)

**Step 3: Pattern analysis**
Calculate and surface:

1. **Save rate** = saves / impressions × 100 (primary KPI)
2. **Engagement rate** = (reactions + comments + reposts) / impressions × 100
3. **Comment quality** — count of substantive comments (>20 words) vs. emoji-only
4. **Hook effectiveness** — correlation between hook formula and impression count
5. **Anchor type performance** — which source types drive the most saves
6. **Posting time impact** — if data available, note time-of-day patterns
7. **Deep vs Fast comparison** — do --deep posts consistently outperform --fast?

### Phase 3 — VERIFY

Before outputting, check:
- [ ] At least 2 posts have data (if <2, note "insufficient data for trends")
- [ ] Save rate calculated correctly
- [ ] Recommendations are specific and actionable (not generic "post more")
- [ ] No false patterns from small sample size (flag if N < 5)

### Phase 4 — GENERATE RECOMMENDATIONS

Produce 3 categories of recommendations:

**Keep doing (evidence-backed):**
- Patterns that correlated with high save rate or engagement

**Stop doing (evidence-backed):**
- Patterns that correlated with low performance

**Experiment next week:**
- One specific change to test, based on gaps in current data

---

## Output Format

```
## LinkedIn Weekly Review: [DATE RANGE]
Posts analyzed: [N] | Posts with full data: [N]

### Performance Summary
| Post | Date | Hook | Anchor | Views | Saves | Save Rate | Eng Rate |
|------|------|------|--------|-------|-------|-----------|----------|
| [Topic] | [Date] | [Formula] | [Type] | [N] | [N] | [X%] | [X%] |

### Best Performer
[Topic] — Save rate: [X%]
Why it worked: [2-3 specific reasons tied to content characteristics]

### Worst Performer
[Topic] — Save rate: [X%]
Why it underperformed: [2-3 specific reasons]

### Pattern Insights
1. Hook formula: [best] > [worst] — [specific observation]
2. Anchor type: [best] > [worst] — [specific observation]
3. Deep vs Fast: [observation]
4. Posting time: [observation or "not enough data"]

### Optimization Recommendations

**Keep doing:**
• [Specific action] — evidence: [what data shows]

**Stop doing:**
• [Specific action] — evidence: [what data shows]

**Experiment next week:**
• [One specific test] — hypothesis: [why this might work]

### Strategy Update Input
[Structured summary for /linkedin-strategist to consume]
- Top performing content type: [X]
- Audience response pattern: [X]
- Recommended topic direction: [X]
- Recommended hook formula: [X]
```

---

## Auto-Update Content Memory

After analysis, automatically run:
```
/content-memory update [topic] [performance data]
```
for any posts that have new data but haven't been updated in content-sessions.md yet.

---

## Context
- Primary KPI: **save rate** (saves / impressions) — this is the strongest signal for LinkedIn algorithm boost
- Secondary KPI: comment quality (substantive comments > emoji reactions)
- LinkedIn algorithm priority: saves > comments > reactions > clicks
- User cadence: ~2-3 posts/week, so expect 2-3 posts per weekly review
- Upstream: user provides raw LinkedIn data
- Downstream: output feeds into `/linkedin-strategist` for strategy updates
- Related: `/content-memory review` does monthly pattern analysis — this skill does weekly tactical analysis

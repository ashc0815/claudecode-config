---
name: brave-research
description: Real-time web research with source verification. Use before script-analyzer to gather data, or after blindspot-detector to fill evidence gaps. Activates on "search for", "research", "look up", "find data on", "最新数据", "搜索", "查一下".
---

# Brave Research

Real-time web research with built-in source verification. Returns a structured research brief with quality-assessed sources — not just a list of links.

## Instructions

### SCAN Mode — Auto-Topic Discovery (for `--morning` pipeline)

When called with `SCAN` mode (by linkedin-orchestrator `--morning`), the goal is NOT to research a specific topic — it's to **find today's best topic** from fresh AI + Finance news.

**Step 1: Morning news sweep**
Run 3-5 WebSearch queries to surface today's freshest AI + Finance stories:
- `"AI finance" OR "AI banking" OR "AI analyst" latest news [current month] [current year]`
- `"AI agent" OR "LLM" finance OR Wall Street [current week]`
- `site:linkedin.com "AI" "finance" trending [current week]` (catch viral LinkedIn takes)
- `Goldman Sachs OR JPMorgan OR BlackRock AI announcement [current month]`
- Optional: `AI 金融 最新 [current month]` (for 小红书 angle)

**Step 2: Candidate ranking**
From the results, pick the top 3 candidates. Score each on:

| Criteria | Weight | What to look for |
|----------|--------|-----------------|
| Freshness | 30% | Published in last 48 hours beats last week |
| Controversy potential | 25% | Does this have a non-obvious take? Could people disagree? |
| Data availability | 20% | Is there a specific stat or announcement to anchor on? |
| Audience pain match | 15% | Does this connect to a real pain point from linkedin-strategy.md? |
| Differentiation | 10% | Has this NOT been covered by benchmark accounts yet? |

**Step 3: Auto-select + verify**
- Pick the #1 ranked candidate
- Cross-check against `content-sessions.md` via `/content-memory topic-check` — if similar topic was done in the last 2 weeks, pick #2
- WebFetch the source article to extract the specific data point or quote for anchoring
- Output the selected topic with its anchor

**SCAN Output Format:**
```
## Morning Scan: [DATE]
Queries run: [N]
Stories found: [N]

### Selected Topic
Topic: [One-line topic]
Anchor: [Specific news item, stat, or quote — with source URL]
Anchor type: [News / Company announcement / Report / Viral post]
Why this one: [1 sentence — freshness + controversy + data]
Mode recommendation: [--deep if rich data, --fast if reactive take]

### Runners-up
2. [Topic] — [why not picked: too similar to recent post / less data / less controversial]
3. [Topic] — [why not picked]
```

The selected topic and anchor are passed directly to the content-agent autopilot pipeline. No user input needed.

---

### Phase 1 — PLAN
Before searching, decompose the research need into:
1. What specific claim needs evidence? (not "research AI in finance" — "find a stat on AI productivity gains for finance analysts, published 2024-2026")
2. What source type would be most credible for this claim?
3. What would make a source too weak to use? (older than 18 months, no methodology, vendor-published only)

### Phase 2 — EXECUTE

Run searches in priority order:

**Tier 1 sources (highest credibility):**
- McKinsey Global Institute, Deloitte Insights, PwC, Accenture Research
- Bloomberg, Financial Times, Wall Street Journal
- LinkedIn Workforce Reports, World Economic Forum
- Official company announcements (JPMorgan, Goldman Sachs, BlackRock, Citadel)

**Tier 2 sources (good credibility):**
- Harvard Business Review, MIT Sloan Management Review
- Industry associations (CFA Institute, GARP)
- Reputable fintech media (The Banker, American Banker, Finextra)

**Tier 3 sources (use with caution):**
- Vendor whitepapers (flag as potentially biased)
- Individual blog posts (flag as opinion, not data)
- Social media posts (flag as anecdotal)

For each search query:
1. Use WebSearch to find candidate sources
2. Use WebFetch on the 2-3 most promising results to extract actual content
3. Note publication date, author/organization, and methodology if available

### Phase 3 — VERIFY: Source Quality Check

For each piece of evidence found, assess:

| Check | Criteria |
|-------|----------|
| Recency | Published within 18 months (for AI topics) |
| Credibility | Tier 1 or Tier 2 source |
| Specificity | Contains actual numbers, not just directional claims |
| Relevance | Directly supports the claim being made |
| Independence | Not published by a vendor selling the solution |

**Verification Gate:**
- If ≥2 Tier 1/2 sources found with specific data → STRONG EVIDENCE, proceed
- If only Tier 3 sources found → WEAK EVIDENCE, flag and suggest alternative search angles
- If no relevant sources found → NO EVIDENCE, recommend reframing the claim or dropping it

### Autopilot Decision Rules (when called from --autopilot pipeline)
When running inside an autopilot pipeline, do NOT stop to ask the user. Instead:

| Situation | Auto-Decision |
|-----------|---------------|
| STRONG EVIDENCE | Proceed. Pass top 2 data points downstream. |
| WEAK EVIDENCE | Auto-run 1 retry with narrower query. If still weak, proceed with caveat: tag output as "data-light" and recommend observer framing to kobo-optimizer. |
| NO EVIDENCE | Do NOT ask user. Auto-narrow the topic to the most specific sub-angle that has adjacent data. If still nothing after 1 retry, proceed with "no-data" flag — kobo-optimizer will use counter-intuitive claim formula instead of data shock. |
| Conflicting sources | Pick the higher-tier source. Note the conflict in output for blindspot-detector to address. |
| All sources >18 months old | Use the most recent one with a recency caveat. Never block the pipeline for stale data alone. |

**Quality floor (non-negotiable even in autopilot):**
- Never fabricate or extrapolate statistics
- Never cite a source without verifying it exists via WebFetch
- Always tag evidence tier in output so downstream skills can calibrate

### Phase 4 — REFLECT
After gathering evidence, ask: does this data strengthen or complicate the original claim?
- If it strengthens: note the best quote/stat to use
- If it complicates: flag the nuance — this is valuable for blindspot-detector
- If it contradicts: this is a critical blindspot — must be addressed in the script

## Output Format

```
## Research Brief: [QUERY]
Date: [today] | Research scope: [date range searched]

### Evidence Found

#### STRONG (use in script)
- [Stat/finding] — [Source name, publication date] — [URL]
  Quality: Tier [1/2] | Recency: [date] | Specificity: [High/Medium]

#### MODERATE (use with caveat)
- [Stat/finding] — [Source name, publication date] — [URL]
  Quality: Tier [2/3] | Caveat: [What to note when citing]

#### WEAK (do not use)
- [Stat/finding] — [Source name] — Why weak: [reason]

### Recommended Data Points for Script
1. [Best stat to use — exact quote or paraphrase]
   → Cite as: "[Source], [Year]"
2. [Best case study or example]
   → Use as: [How to reference it in the script]
3. [Counterargument found in research]
   → Address by: [How to handle it]

### Evidence Verdict
Status: [STRONG EVIDENCE / WEAK EVIDENCE / NO EVIDENCE]
Gaps remaining: [What still needs a source]

### If gaps remain, try:
/brave-research "[alternative query 1]"
/brave-research "[alternative query 2]"
```

## Workflow Integration

```
/brave-research [topic]           → before script-analyzer (gather data first)
/script-analyzer [topic]          → analyze with data in hand
/blindspot-detector [topic]       → identify remaining gaps
/brave-research [specific gap]    → fill evidence gaps (targeted)
/kobo-optimizer [draft]           → write final script
```

## Notes
- For 小红书 content: search in Chinese for domestic context (中金, 华泰, 招商, 国泰君安, A股)
- AI moves fast — data older than 18 months may be outdated for this topic area
- Vendor-published stats (e.g., "our AI saves 40% of analyst time") need independent corroboration

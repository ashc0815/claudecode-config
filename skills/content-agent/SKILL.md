# Content Agent Skill (Orchestrator)

## Trigger
User invokes `/content-agent` followed by a topic and optional mode flag.

```
/content-agent --deep [topic]    → Full 5-stage pipeline (anchor post, ~1x/week)
/content-agent --fast [topic]    → Fast 2-stage pipeline (reactive post, ~1-2x/week)
/content-agent [topic]           → Defaults to --deep
```

## Purpose
Orchestrator that runs the complete Plan → Execute → Verify pipeline across all content skills. Supports two production modes to match a 2-3 posts/week cadence without burning out on process overhead.

---

## MODE SELECTION

### When to use `--deep`
- You have a topic you've been thinking about for a few days
- There's a specific data point or case study you want to build around
- This is your "anchor" post for the week — the one you want to perform
- You have at least a rough personal observation or experiment result to anchor it

### When to use `--fast`
- You just saw a news item, report, or LinkedIn post that triggered a reaction
- You ran an AI experiment and want to share the observation while it's fresh
- You have a contrarian take that doesn't need heavy research to support
- You want to publish within the hour

**Rule of thumb:** 1 deep post + 1-2 fast posts per week. Fast posts are often more authentic and get more engagement precisely because they're reactive and unpolished.

---

## `--deep` MODE: Full 5-Stage Pipeline

### PLAN PHASE
Before executing, output a visible plan and wait for confirmation:

```
## Content Pipeline Plan: [TOPIC] [--deep]

Stage 1: Research      → /brave-research
Stage 2: Analysis      → /script-analyzer
Stage 3: Stress Test   → /blindspot-detector
Stage 4: Script        → /kobo-optimizer
Stage 5: Memory Log    → /content-memory

Content anchor detected: [Source type if mentioned in input, or "not specified"]
```

If the user mentioned a source (news article, YouTube video, X thread, Reddit post, conversation), extract it and pass it as the anchor to kobo-optimizer. If not mentioned, note "not specified" — kobo-optimizer will use observer framing.

Ask: "Ready to run? Any stage to skip?"
Wait for confirmation.

### EXECUTE + VERIFY: Stage-by-Stage

**STAGE 1: Research**
Execute: `/brave-research` on the topic.
Verify:
- ≥2 Tier 1/2 sources found? → if no, run one targeted retry
- Data <18 months old? → if no, flag recency gap
- ≥1 specific statistic? → if no, mark as "data-light"

Gate: PASS if ≥1 credible source. FAIL if nothing relevant found.
On FAIL: "Limited data on this topic. Options: (1) narrow the angle, (2) proceed as observer framing with no data claim."

---

**STAGE 2: Analysis**
Execute: `/script-analyzer` with topic + research brief.
Verify: PROCEED / PROCEED WITH GAPS / TOPIC TOO VAGUE

Gate: PASS if PROCEED or PROCEED WITH GAPS.
On TOPIC TOO VAGUE: Stop. Suggest 3 narrower angles, ask user to pick.

---

**STAGE 3: Stress Test**
Execute: `/blindspot-detector` with topic + script-analyzer output.
Verify: PROCEED / REVISE / NEEDS RESEARCH

On REVISE: Show top 3 fixes. If fix requires personal story, ask:
> "I need a personal anchor for this script. Do you have a specific moment — an experiment, an observation, a before/after — I can use? Even one sentence is enough."
> If no: auto-downgrade to observer framing (see Downgrade Rules below).

On NEEDS RESEARCH: Run targeted `/brave-research` on specific gaps, re-run blindspot (max 1 retry).

Gate: PASS if PROCEED. FAIL if NEEDS RESEARCH after retry.
On FAIL: Surface unresolved gaps, ask user how to proceed.

---

**STAGE 4: Script Generation**
Execute: `/kobo-optimizer` with topic + all previous outputs.
Verify: reflection checks X/8, all platform gates passed.

Gate: PASS when quality gate passes (kobo-optimizer handles internal retries).

---

**STAGE 5: Memory Log**
Execute: `/content-memory log` automatically.
No user action needed.

---

## `--fast` MODE: 2-Stage Reactive Pipeline

No plan confirmation needed — just run.

### STAGE 1: Analysis
Execute: `/script-analyzer` on the topic.
No research stage — proceed directly with whatever data the user has mentioned.
If topic is TOO VAGUE: suggest 2 sharper angles, ask user to pick. Then continue.

### STAGE 2: Script Generation
Execute: `/kobo-optimizer` with script-analyzer output.
Reflection loop still runs internally — quality gate still applies.
LinkedIn version is the only required output. X and 小红书 are generated only if time allows.

### Fast Mode Output Header
Always prepend the output with:

```
⚡ FAST MODE — Unverified
This script skipped brave-research and blindspot-detector.
Known risks: [list 1-2 likely gaps based on topic]
Recommend: Review before publishing, especially any data claims.
```

---

## DOWNGRADE RULES (Auto-handling when blocked)

When a stage is blocked and user has set preference to auto-downgrade:

| Blocker | Auto-downgrade action |
|---------|----------------------|
| No personal story available | Switch to observer framing: "I've been watching..." / "I noticed that..." — first person but no fabricated experience |
| No data found | Lead with the observation, skip the data hook, use counter-intuitive claim formula instead |
| Topic too vague after 1 retry | Narrow to the most specific sub-angle automatically, note the narrowing in output |
| NEEDS RESEARCH after retry | Proceed with REVISE verdict, flag the unresolved gaps in the output header |

Downgrade is always noted in the output — never silent.

---

## LOOP MANAGEMENT
Maximum loops per stage: 2
If a stage fails twice: surface the specific blocker to the user, do not loop again.

## STATE PASSING
Maintain a running context block between stages:

```
## Pipeline State
Mode: [--deep / --fast]
Topic: [topic]
Research: [key stats / "data-light" / "skipped"]
Core claim: [from script-analyzer]
Audience: [specific role]
Personal story: [present / observer framing / missing]
Critical gaps: [from blindspot-detector / "skipped"]
Verdict: [PROCEED / REVISE / NEEDS RESEARCH / "fast mode"]
North star: [key insight to protect]
```

---

## OUTPUT FORMAT

**Deep mode progress log:**
```
## Content Agent: [TOPIC] [--deep]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[STAGE 1: Research]   → PASS — [key stat found]
[STAGE 2: Analysis]   → PROCEED — [core claim]
[STAGE 3: Stress Test]→ REVISE → auto-downgraded: [what changed]
[STAGE 4: Script]     → PASS — 7/8 checks, 1 revision
[STAGE 5: Memory]     → Logged ✓
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[Final scripts]
```

**Fast mode output:**
```
## Content Agent: [TOPIC] [--fast]
⚡ FAST MODE — Unverified
Known risks: [1-2 gaps]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[STAGE 1: Analysis]   → PROCEED — [core claim]
[STAGE 2: Script]     → PASS — [X/8 checks]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[LinkedIn script — primary output]
[X + 小红书 — if generated]
```

---

## Context
- Weekly cadence: 1 deep post + 1-2 fast posts
- Platform priority: LinkedIn first, always
- User background: observer/synthesizer — content anchors come from industry news, YouTube/podcasts (AI founders), X threads, Reddit discussions, and conversation insights
- Auto-downgrade is on: never block on missing personal story, use observer framing instead
- Individual skills remain available standalone for manual use

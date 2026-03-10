# LinkedIn Orchestrator Skill

## Trigger
User invokes `/linkedin-orchestrator` with a mode flag:

```
/linkedin-orchestrator --daily                    → Daily routine (post + engage)
/linkedin-orchestrator --weekly                   → Weekly review cycle (analyze + strategize)
/linkedin-orchestrator --full                     → Full cycle (weekly review + daily routine)
/linkedin-orchestrator --daily --autopilot [topic] → Daily routine, zero interruptions
/linkedin-orchestrator --full --autopilot [topic]  → Full cycle, zero interruptions
/linkedin-orchestrator --morning                  → ★ Fully autonomous: find topic + write post + generate engagement
/linkedin-orchestrator status                     → Show current state of all systems
```

## Purpose
Meta-orchestrator that coordinates the entire LinkedIn multi-agent system. Manages the interplay between content creation, performance analysis, strategy updates, and community engagement. Think of it as the "operating system" that ensures all agents work together coherently.

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────┐
│              /linkedin-orchestrator                    │
│         (this skill — coordination layer)              │
└──────┬──────────────┬──────────────┬─────────────────┘
       │              │              │
  ┌────▼────┐   ┌─────▼─────┐  ┌────▼──────┐
  │ WEEKLY  │   │   DAILY   │  │   DAILY   │
  │ REVIEW  │   │  CONTENT  │  │  ENGAGE   │
  │ CYCLE   │   │  PIPELINE │  │  ROUTINE  │
  └────┬────┘   └─────┬─────┘  └────┬──────┘
       │              │              │
  ┌────▼────┐   ┌─────▼─────┐  ┌────▼──────┐
  │/linkedin│   │ /content  │  │/linkedin  │
  │-analyst │   │  -agent   │  │ -engager  │
  └────┬────┘   └───────────┘  └───────────┘
       │
  ┌────▼────────┐
  │ /linkedin   │
  │ -strategist │
  └─────────────┘
```

**Data flow:**
- `/linkedin-analyst` reads from: content-memory, user-provided LinkedIn data
- `/linkedin-strategist` reads from: analyst output, linkedin-strategy.md, content-sessions.md
- `/content-agent` reads from: linkedin-strategy.md (for alignment)
- `/linkedin-engager` reads from: linkedin-creators.md, linkedin-strategy.md

---

## Instructions

### `--morning` MODE: Fully Autonomous Daily Run

**This is the "I just say go" mode.** User provides NOTHING — the agent finds today's topic, writes the post, generates engagement comments, and presents a single go/no-go decision.

#### How to use
```
/linkedin-orchestrator --morning
```
That's it. No topic, no flags, no input. Just run this every morning.

#### Execution Flow
```
STEP 0: Read context
  → Read linkedin-strategy.md (current topic priorities + what's working)
  → Read content-sessions.md (recent posts — avoid repetition)
  → Read linkedin-creators.md (for engagement targets)

STEP 1: Find today's topic
  → Run /brave-research in SCAN mode (morning news sweep)
  → Auto-select the best topic based on freshness + controversy + data + strategy alignment
  → Auto-check against content-memory to avoid repeats

STEP 2: Write the post
  → Run /content-agent --autopilot [auto-selected topic]
  → Full pipeline: research → analyze → stress test → script
  → All decisions handled automatically by each skill's autopilot rules

STEP 3: Generate engagement
  → Auto-select 3-5 creators from linkedin-creators.md (rotation-aware)
  → Generate template comments based on each creator's focus area
  → Flag as "template — customize after reading their actual post"

STEP 4: Present for approval
  → Single output block with everything the user needs
```

#### Output Format
```
## ☀ Morning Brief: [DATE]
Topic source: [What triggered this topic — news headline, report, announcement]
Strategy alignment: [Which strategy priority this serves]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### Your LinkedIn Post
[Final LinkedIn script — ready to copy-paste]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### Engagement Queue (post these ~1h after publishing)

**1. [Creator Name]** — likely topic: [their focus area]
> [Template comment — customize after reading their actual post]

**2. [Creator Name]** — likely topic: [their focus area]
> [Template comment]

**3. [Creator Name]** — likely topic: [their focus area]
> [Template comment]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### Autopilot Decision Trail
- Topic selection: [why this topic was chosen over alternatives]
- Research: [evidence quality — strong/data-light/no-data]
- Analysis: [any auto-narrowing or auto-fixes applied]
- Stress test: [any auto-downgrades — observer framing, etc.]
- Script: [reflection score X/8, any revisions made]

### Runners-up (if you don't like today's topic)
2. [Alternative topic] — [one-line reason]
3. [Alternative topic] — [one-line reason]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### Your Call
- **"go"** → I'll log to content-memory, you publish
- **"用第2个"** or **"switch to [topic]"** → I'll re-run the pipeline on that topic
- **"adjust [what]"** → I'll revise just that part (e.g., "adjust hook", "more data", "shorter")
- **"skip today"** → Nothing posted, no log
```

#### Morning Mode Guardrails
- **Topic must be <48h old.** If no fresh news found, fall back to linkedin-strategy.md's planned topics for the week.
- **Never pick the same topic angle as a post from the last 14 days.** Always cross-check content-memory.
- **Strategy alignment is weighted.** If linkedin-strategy.md says "focus on AI agents this week", prefer topics in that direction.
- **Mode auto-selection:** If the topic has rich data (Tier 1/2 sources), use --deep pipeline. If it's a reactive hot take, use --fast. The agent decides — user doesn't need to.
- **Runners-up are always shown.** User can switch to an alternative without re-running the scan.

---

### `--autopilot` FLAG: Zero-Interruption Mode

When `--autopilot` is combined with any mode, the orchestrator runs the entire pipeline without asking for user input. Every intermediate decision is handled automatically by each skill's built-in autopilot rules.

**`--daily --autopilot [topic]`:**
1. Auto-check `linkedin-strategy.md` for today's planned topic (use provided [topic] if given, else pick from weekly plan)
2. Run `/content-agent --autopilot [topic]` — full pipeline, no interruptions
3. Output the final script + engagement comments in one block
4. Present a single decision point:
```
## Ready to Publish

### Your Post
[Final LinkedIn script]

### Engagement Comments (post ~1 hour after publishing)
[3-5 generated comments for target creators]

### Autopilot Decision Trail
[Summary of all auto-decisions made during the pipeline]

### Your Call
- "go" → I'll log everything to content-memory
- "adjust [what]" → I'll revise just that part
- "redo" → I'll re-run the full pipeline in step-by-step mode
```

**`--full --autopilot [topic]`:**
1. Run weekly review: `/linkedin-analyst` + `/linkedin-strategist` (auto-process available data)
2. Pick today's topic from freshly generated plan (or use provided [topic])
3. Run daily autopilot pipeline (as above)
4. Output everything in one block: strategy update + final script + engagement comments

**`--weekly` with `--autopilot`:**
- Requires user to provide LinkedIn Analytics data (this is the one input that can't be auto-generated)
- Once data is provided, runs analyst → strategist → weekly plan generation without further interruptions
- If no data is provided, auto-generate plan based on content-memory data only, flagged as "data-light review"

**Autopilot engagement generation:**
When generating engagement comments in autopilot mode:
- Auto-select 3-5 creators from `linkedin-creators.md` based on rotation schedule
- Since we can't fetch their actual posts, generate **template comments** based on each creator's known focus area
- Flag these as "template — customize after reading their actual post"
- The user reviews and personalizes before posting

---

### `--weekly` MODE: Weekly Review Cycle

**Run every Monday (recommended)**

#### PLAN
```
## Weekly Review Cycle Plan
Date: [DATE]
Week number: [N]

Step 1: /linkedin-analyst          → Analyze last 7 days of post performance
Step 2: /linkedin-strategist       → Update strategy based on analyst findings
Step 3: Generate next week's plan  → 3 posts with topics, modes, and schedules

Data needed from user:
- LinkedIn Analytics data for posts from [date] to [date]
- Any qualitative observations (what felt good/bad this week)
```

Ask: "Ready to run the weekly review? Please share your LinkedIn Analytics data."
Wait for user to provide data.

#### EXECUTE

**Step 1: Run Analyst**
Execute `/linkedin-analyst` with user's data.
Wait for completion. Capture output.

Gate: Analyst must produce at least a Performance Summary. If data is insufficient, note it and proceed with available data.

**Step 2: Run Strategist**
Execute `/linkedin-strategist` with analyst output.
Wait for completion. Verify `linkedin-strategy.md` was updated.

Gate: Strategy file must be updated. If strategist has no changes, that's valid — log "strategy unchanged."

**Step 3: Generate Weekly Plan**
Based on updated strategy, output a concrete plan:

```
## Next Week's Content Plan

### Monday
- Post: [Topic] — [--deep/--fast] — [hook formula]
- Engage: /linkedin-engager after posting

### Wednesday
- Post: [Topic] — [--deep/--fast] — [hook formula]
- Engage: /linkedin-engager after posting

### Friday
- Post: [Topic] — [--deep/--fast] — [hook formula]
- Engage: /linkedin-engager after posting

### Experiment This Week
- Testing: [variable]
- Hypothesis: [why]
- Measure: [how]
```

---

### `--daily` MODE: Daily Routine

**Run each posting day**

#### PLAN
```
## Daily Routine Plan: [DATE] [DAY]
Today's scheduled post: [topic from weekly plan, or user-specified]
Post mode: [--deep / --fast]
Engagement window: 1 hour after posting
```

#### EXECUTE

**Step 1: Content Creation**
Execute `/content-agent [topic]` with the mode from the weekly plan.
Wait for completion.

**Step 2: Post Reminder**
After script is ready, output:
```
## Post Ready
Script generated. After you publish on LinkedIn:
1. Note the exact posting time
2. Set a reminder for 1 hour from now
3. Come back and run the engagement step, or type: "engage"
```

**Step 3: Engagement (1 hour after posting)**
When user returns or says "engage":
Execute `/linkedin-engager`
Output generated comments for user to manually post.

---

### `--full` MODE: Full Cycle

Runs `--weekly` first, then immediately starts `--daily` for today's post.

Sequence:
1. Weekly review (analyst → strategist)
2. Pick today's topic from the freshly generated weekly plan
3. Run content pipeline
4. Queue engagement for 1 hour after posting

---

### `status` MODE: System Status

Read all state files and report:

```
## LinkedIn System Status

### Strategy
File: linkedin-strategy.md
Last updated: [date]
Version: [N]
Current state: [Growing / Stable / Declining / Unknown]

### Content Memory
File: content-sessions.md
Total posts logged: [N]
Posts with performance data: [N]
Last entry: [date]

### Creator Watch List
File: linkedin-creators.md
Creators tracked: [N]
Last engagement: [date]

### This Week
Posts planned: [N]
Posts published: [N]
Posts remaining: [N]
Weekly review: [done / pending]

### Health Check
- [ ] Strategy file exists and is <7 days old
- [ ] Content memory has recent entries
- [ ] Creator watch list has ≥5 creators
- [ ] Last weekly review was within 7 days
```

---

## Shared State Files

| File | Location | Owner | Readers |
|------|----------|-------|---------|
| `content-sessions.md` | memory/ | content-memory | analyst, strategist |
| `linkedin-strategy.md` | memory/ | strategist | content-agent, engager |
| `linkedin-creators.md` | memory/ | engager | orchestrator |
| `MEMORY.md` | memory/ | user/system | all skills |

---

## Output Format

```
## LinkedIn Orchestrator: [MODE] — [DATE]

### Pipeline Status
[Stage 1: name]  → [DONE / RUNNING / PENDING / SKIPPED]
[Stage 2: name]  → [DONE / RUNNING / PENDING / SKIPPED]
[Stage 3: name]  → [DONE / RUNNING / PENDING / SKIPPED]

### Summary
[2-3 sentences on what was accomplished]

### Next Action
[What the user should do next — e.g., "publish the post, then return in 1 hour for engagement"]
```

---

## Scheduling Reference

| Task | Frequency | Trigger | Skills Involved |
|------|-----------|---------|-----------------|
| Content creation | 2-3x/week | `/linkedin-orchestrator --daily` | content-agent pipeline |
| Post engagement | Daily (after posting) | `/linkedin-engager` or `--daily` step 3 | linkedin-engager |
| Performance review | Weekly (Monday) | `/linkedin-orchestrator --weekly` | linkedin-analyst |
| Strategy update | Weekly (after review) | Auto-triggered by `--weekly` | linkedin-strategist |
| Memory review | Monthly (~every 10 posts) | `/content-memory review` | content-memory |

---

## Context
- This is the top-level entry point — users should primarily interact through this skill
- Individual skills remain available standalone for manual use or debugging
- The orchestrator never modifies content directly — it delegates to specialized skills
- All engagement comments are generated but must be posted manually by the user
- Strategy changes are incremental by design — no sudden pivots based on one week's data
- Upstream: user triggers with mode flag
- Downstream: delegates to all other skills in the system

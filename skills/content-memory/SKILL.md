# Content Memory Skill

## Trigger
User invokes `/content-memory` with a sub-command:

```
/content-memory update [topic] [data]   → update performance data after publishing
/content-memory review                  → surface patterns from past sessions
/content-memory topic-check [topic]     → check if a similar topic has been done
```

The `/content-memory log` step runs automatically inside `/content-agent` — no manual trigger needed.

## Purpose
Learning layer. Records what worked and what didn't across sessions. Designed for a 2-3 posts/week cadence: logging is automatic and zero-cost, manual updates take under 2 minutes, monthly reviews surface actionable patterns.

## Memory File Location
`~/.claude/projects/-Users-ashleychen/memory/content-sessions.md`

---

## Layer 1 — Auto-Log (runs inside content-agent, no user action)

When `/content-agent` completes Stage 4, automatically append to `content-sessions.md`:

```markdown
---
## [DATE] | [TOPIC]
Mode: [--deep / --fast]
Hook formula: [Data Shock / Counter-Intuitive / Problem-Solution / Identity Mirror]
Anchor type: [News / YouTube-Podcast / X-thread / Reddit / Conversation / Observer]
Anchor detail: [One sentence — e.g., "Reddit thread on r/finance asking if analysts are worried about AI"]
Core angle: [One sentence — the product thinking differentiation]
Pipeline score: Hook X/10 | Authenticity X/10 | Actionability X/10
Blindspot gaps: [Number] — [brief description or "none"]
Status: drafted | [ ] published | [ ] performance updated
```

This is the only thing that happens automatically. Everything else is user-triggered.

---

## Layer 2 — Performance Update (user runs after publishing, ~2 min)

### `/content-memory update [topic] [data]`

User provides data in any format — structured or freeform. Examples:

```
/content-memory update "AI finance analyst" LinkedIn: 1200 views 47 saves 12 comments. Hook felt too long.
/content-memory update "AI finance analyst" 好的数据，saves很高，但评论区没人互动
/content-memory update "AI finance analyst" flopped, barely 200 views, think the topic was too broad
```

Claude reads the existing log entry for that topic and appends:

```markdown
Performance (48h):
- LinkedIn: [views] views / [saves] saves / [comments] comments
- X: [impressions] impressions / [RTs] RTs (or "not published")
- 小红书: [views] views / [saves] saves (or "not published")
Feeling: [user's freeform note, verbatim]
```

If the user only gives partial data (e.g., just LinkedIn), log what's available and leave the rest blank. Never ask for more than what was provided.

---

## Layer 3 — Monthly Review (user runs every ~10 posts)

### `/content-memory review`

Read all entries in `content-sessions.md`. Analyze only two categories of data:

**Category A: Content characteristics**
- Hook formula used
- Anchor type (News / YouTube / X / Reddit / Conversation / Observer)
- Core angle

**Category B: Real feedback**
- Platform performance numbers (where available)
- User's freeform feeling notes

Synthesize into a review. Do not surface pipeline metrics (blindspot gap counts, reflection loop rates, etc.) — these are process noise, not signal.

Output format:

```
## Content Memory Review
Posts logged: [N] | Posts with performance data: [N]
Period: [date range]

### What's driving saves (your best signal)
- Hook formula: [best performer] — avg saves rate [X per 1k views or "not enough data"]
- Anchor type: [best performer] — [observation]
- Angle type: [pattern if visible]

### What's not working
- [Pattern from low-performing posts or negative feeling notes]
- [Recurring issue]

### Your own words (feeling notes pattern)
[Synthesize the freeform notes — what do you keep saying after posts go live?]

### Next 10 posts: do more of this
1. [Specific recommendation]
2. [Specific recommendation]

### Next 10 posts: do less of this
1. [Specific recommendation]

### Topics covered (avoid repetition)
- [Topic] — [date] — [one-word performance: strong/ok/weak]
```

If fewer than 5 posts have performance data, note: "Not enough data for reliable patterns yet. Keep logging."

---

## `/content-memory topic-check [topic]`

Before starting a new pipeline, check for overlap:
- Search `content-sessions.md` for similar topics or angles
- If found: show what angle was used and how it performed
- Suggest what's NOT been covered yet

Output:
```
## Topic Check: [TOPIC]

Similar posts found: [N]
- [Date]: "[Angle used]" — Performance: [strong/ok/weak]

Uncovered angles:
- [What hasn't been done yet]

Repetition risk: [Low / Medium / High]
```

If nothing similar found: "No overlap detected. Good to go."

---

## File Management Rules

- Always append, never overwrite
- One entry per content session
- Performance data is added in-place to the existing entry (not as a new entry)
- Every 10 sessions: `/content-memory review` should be run to extract durable patterns
- If a post was never published, mark status as "unpublished" and skip performance tracking

## Context
- Logging is automatic — user only touches this skill to update performance data and run reviews
- The freeform "feeling" note after publishing is the most valuable signal — more useful than raw numbers
- Goal: after 20-30 posts, the review should tell you exactly what type of content to make more of
- Upstream: auto-called by `/content-agent` Stage 5
- Manual update: run after each post goes live (within 48h)

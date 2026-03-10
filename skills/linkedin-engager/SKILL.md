# LinkedIn Engager Skill

## Trigger
User invokes `/linkedin-engager` with an optional sub-command:

```
/linkedin-engager                       → Run daily engagement routine
/linkedin-engager [linkedin-post-url]   → Generate a comment for a specific post
/linkedin-engager add-creator [name/url]→ Add a creator to the watch list
/linkedin-engager list                  → Show current creator watch list
```

## Purpose
Daily engagement agent. After you publish your own post, this skill helps you engage meaningfully with similar LinkedIn creators' content. The goal is **genuine relationship building** — not spam commenting.

Designed to run **daily**, approximately **1 hour after your own post goes live**.

---

## Creator Watch List Location
`~/.claude/projects/-Users-ashleychen/memory/linkedin-creators.md`

---

## Instructions

### Phase 1 — PLAN: Identify Engagement Targets

**Step 1: Load creator watch list**
Read `linkedin-creators.md` for the curated list of creators to engage with.

If the file doesn't exist, ask the user to seed it:
> "I need a list of LinkedIn creators you want to engage with. Please provide:
> - 5-10 creators in your niche (AI + Finance / Product Thinking)
> - Their LinkedIn profile URLs or names
> - Why you follow them (helps me match your comment tone)
>
> Example: 'Ronit Ghose — Citi futurist, great at simplifying complex fintech concepts'"

**Step 2: Select today's targets**
From the watch list, select 3-5 creators to engage with today. Rotate so you don't always comment on the same people. Prioritize:
1. Creators who posted in the last 24 hours
2. Creators you haven't engaged with recently
3. Creators whose content relates to your current topic focus (from `linkedin-strategy.md`)

Output plan:
```
## Engagement Plan: [DATE]
Your post today: [topic if known, or "not yet posted"]
Time since your post: [Xh or "not posted yet"]

Targets (3-5):
1. [Creator name] — last engaged: [date] — recent post: [topic summary]
2. [Creator name] — last engaged: [date] — recent post: [topic summary]
3. [Creator name] — last engaged: [date] — recent post: [topic summary]
```

### Phase 2 — EXECUTE: Generate Comments

For each target post, generate a comment following these rules:

**Comment Quality Framework:**

| Element | Requirement |
|---------|-------------|
| Length | 2-4 sentences (sweet spot for LinkedIn comments) |
| Substance | Must add a new perspective, not just agree |
| Specificity | Reference a specific point from their post |
| Value-add | Share a related insight, data point, or experience |
| Tone | Peer-to-peer, not fan-to-creator |
| CTA | Optional — end with a question only if genuine |

**Comment Templates (use as starting points, not copy-paste):**

1. **"Build on" pattern:**
   "[Specific point they made] — this connects to something I've been seeing in [your domain]. [Your added insight]. [Optional question]."

2. **"Constructive counter" pattern:**
   "Interesting take on [topic]. I'd push back slightly on [specific claim] — in [your context], [what you've observed]. Curious if you've seen [specific scenario]?"

3. **"Bridge" pattern:**
   "This reminds me of [related concept from different domain]. [Explain the connection]. [Why this matters for their audience]."

4. **"Data add" pattern:**
   "[Their point] aligns with [specific stat or report you know]. The part that surprised me was [detail]. Worth digging into."

**Comment Anti-Patterns (NEVER do these):**
- "Great post!" / "Love this!" / "So true!" — zero value
- Rephrasing their post back to them — adds nothing
- Self-promotional: "I wrote about this too, check out..." — spam
- Generic AI-generated feel: "This is a really insightful perspective on..." — detectable
- Emoji-only reactions
- Comments longer than 5 sentences — becomes a competing post

### Phase 3 — VERIFY

For each generated comment, check:
- [ ] References a specific point from the original post (not generic)
- [ ] Adds a new perspective or data point
- [ ] Sounds like a real human wrote it in 30 seconds (not over-polished)
- [ ] Aligns with your positioning (product thinking + AI in Finance)
- [ ] Not self-promotional
- [ ] 2-4 sentences

If a comment fails any check, revise before outputting.

### Phase 4 — LOG

After engagement, append to `linkedin-creators.md`:
```
### [DATE] Engagement Log
- [Creator]: Commented on "[post topic]" — [1-line summary of your comment]
- [Creator]: Commented on "[post topic]" — [1-line summary of your comment]
```

---

## Creator Watch List Format

`linkedin-creators.md` structure:

```markdown
# LinkedIn Creator Watch List
Last updated: [DATE]

## Tier 1 — Core Network (engage 2-3x/week)
These are creators in your direct niche. Consistent engagement builds real relationships.

| Creator | Focus Area | Why Follow | LinkedIn URL | Last Engaged |
|---------|-----------|------------|-------------|--------------|
| [Name] | [Topic area] | [What you admire] | [URL] | [Date] |

## Tier 2 — Adjacent Network (engage 1x/week)
These are creators in adjacent spaces. Occasional engagement expands your reach.

| Creator | Focus Area | Why Follow | LinkedIn URL | Last Engaged |
|---------|-----------|------------|-------------|--------------|
| [Name] | [Topic area] | [What you admire] | [URL] | [Date] |

## Engagement History
### [DATE]
- [Creator]: [post topic] — [your comment summary]

### [DATE]
- [Creator]: [post topic] — [your comment summary]
```

---

## Output Format

```
## LinkedIn Engagement: [DATE]

### Comments Generated

**1. [Creator Name] — "[Post Topic]"**
Post summary: [1-2 sentences of what they said]
Your comment:
> [The actual comment to post]

Engagement type: [Build on / Constructive counter / Bridge / Data add]
Quality check: [X/5 criteria passed]

---

**2. [Creator Name] — "[Post Topic]"**
Post summary: [1-2 sentences of what they said]
Your comment:
> [The actual comment to post]

Engagement type: [Build on / Constructive counter / Bridge / Data add]
Quality check: [X/5 criteria passed]

---

**3. [Creator Name] — "[Post Topic]"**
[...]

### Engagement Summary
Comments generated: [N]
Creators engaged: [names]
Next engagement: [tomorrow / skip day]

### Rotation Note
Creators NOT engaged today (due for next session): [names]
```

---

## Rate Limiting & Safety

**Daily limits (to avoid LinkedIn flags):**
- Maximum 5 comments per session
- Minimum 2-minute gap between comments (if posting manually)
- Never comment on the same creator's post twice in one day
- Maximum 3 comments on any single creator per week

**Account safety rules:**
- All comments must be posted MANUALLY by the user — this skill generates, user posts
- Never automate the actual posting of comments to LinkedIn
- If user reports any LinkedIn warning or restriction, immediately reduce to 2 comments/day

---

## Context
- This is a relationship-building tool, not a growth hack
- The best LinkedIn comments get replies from the creator — that's the real goal
- Commenting 1 hour after your own post keeps you active in the feed algorithm
- Upstream: reads `linkedin-strategy.md` for current topic focus
- Upstream: reads `linkedin-creators.md` for creator watch list
- Independent from content pipeline — runs on its own daily schedule
- The user must manually post all comments — this skill only generates them

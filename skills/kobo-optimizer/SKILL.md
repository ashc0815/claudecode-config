# 口播 Optimizer Skill (kobo-optimizer)

## Trigger
User invokes `/kobo-optimizer` followed by a draft script, topic + blindspot report, or topic + context.

## Purpose
Final script generation with a built-in reflection loop: Draft → Self-Critique → Revise → Quality Gate → Freeze. Outputs ready-to-record scripts for LinkedIn, X Thread, and 小红书. Does not output until the quality gate passes.

## Instructions

### Phase 1 — PLAN
Before writing, extract from the input:
1. The north star insight (from blindspot-detector's reflection, or derive it)
2. The content anchor — identify which type applies (see Anchor Types below)
3. The platform priority order
4. Any hard constraints (word count, specific data points to include, tone notes)

### Anchor Types
The user's content comes from 5 source types. Each maps to a different opening voice:

| Source | Anchor format | Opening voice |
|--------|--------------|---------------|
| Industry news / report | "I read that [X happened]. Here's what nobody's talking about..." | Curator with a take |
| YouTube / podcast (founder/CEO) | "I was listening to [person] talk about [X]. One thing stuck with me..." | Synthesizer |
| X thread / post | "Saw a thread by [handle] on [topic]. The part that surprised me..." | Amplifier with commentary |
| Reddit comment / discussion | "Someone on Reddit asked [question]. The top answer was wrong. Here's why..." | Contrarian |
| Conversation insight | "I was talking to someone in [role] and they said something that stopped me..." | Connector |

**Anchor selection rule:** Pick the source type that makes the opening feel most specific and least generic. "I read a McKinsey report" is weaker than "McKinsey buried a stat on page 34 that nobody's quoting."

If no anchor source is provided at all, use observer framing as default:
> "I've been watching [trend] for a while. Here's what I think most people are missing..."
Never stop and wait — always proceed with the best available anchor.

### Phase 2 — EXECUTE: DRAFT

Write three platform versions simultaneously:

**LinkedIn Version (60-90 seconds, ~150-225 words)**
Structure: Hook → Story → Insight → CTA
- Hook: ≤15 words, uses the strongest formula from script-analyzer
- Story: Names the specific situation, tool, and moment — no generics
- Insight: Frames the "product thinking" angle as a system or tradeoff
- CTA: Drives saves (primary) or comments (secondary)
- Mark natural pauses with [PAUSE]
- Inject 2 humanization markers: personal observation, specific detail, or "I noticed..."

**LinkedIn Format Rules (learned from user feedback):**
- Short sentences — optimized for mobile reading, not desktop paragraphs
- Use deliberate line breaks and white space to create "thinking pauses"
- Use bullet points (•) for lists of 3+ items — increases dwell time
- Tone: "insider insight" not "industry report" — write like a practitioner, not an analyst
- Emotional tension: open with pain point resonance before moving to diagnosis
- CTA: end with a discussion-inviting question that signals the author has a POV, not just curiosity
- Avoid: dense paragraph blocks, report-style prose, passive voice
- The hook must create a gap (curiosity or contradiction) in the first 2 lines — LinkedIn shows ~2 lines before "see more"

**X Thread Version (5-7 tweets)**
- Tweet 1: Standalone hook — works without context, stops the scroll
- Tweets 2-5: One concrete point per tweet, building tension
- Tweet 6: The actionable takeaway in one sentence
- Tweet 7: CTA
- Each tweet ≤280 characters, no filler words

**小红书 Version (Chinese, 30-90 seconds)**
- Language: Simplified Chinese, conversational 普通话
- Structure: 痛点开场 → 我的经历/发现 → 实用建议 → 互动CTA
- Tone: Authentic confession, not thought leadership
- Reference Chinese context: 券商/投行/咨询 not Western firms
- Use 金融民工 register if appropriate

### Phase 3 — REFLECT: Self-Critique

After drafting, run the critic pass. Do NOT show the draft yet. Evaluate against:

| Criterion | Check |
|-----------|-------|
| Hook ≤15 words | Yes/No |
| Hook stops scroll (honest self-test) | Yes/No |
| Anchor is specific (names source, person, or moment — not generic) | Yes/No |
| No generic AI hype phrases | Yes/No |
| At least 1 verifiable data point or named tool | Yes/No |
| Product thinking angle is genuine (not just labeled) | Yes/No |
| LinkedIn sounds human, not AI-generated | Yes/No |
| Three platform versions are distinct (not just translated) | Yes/No |

**Reflection rules:**
- If 7-8 checks pass → proceed to Quality Gate
- If 5-6 checks pass → revise the failing elements, then re-check (max 1 revision loop)
- If <5 checks pass → do not output. Identify the root cause and ask user for the missing input (usually: personal story or specific data point)

### Autopilot Decision Rules (when called from --autopilot pipeline)
When running inside an autopilot pipeline, do NOT stop to ask the user. Instead:

| Situation | Auto-Decision |
|-----------|---------------|
| 7-8 checks pass | Proceed to Quality Gate. |
| 5-6 checks pass | Auto-revise failing elements (max 1 loop), then proceed. |
| <5 checks pass | Do NOT ask user. Auto-diagnose root cause and apply: |
| | - Missing personal story → use observer framing anchor ("I've been watching...", "I noticed...") |
| | - Missing data point → use the best available from brave-research output, even if Tier 3 (with caveat tag). If no data at all, use counter-intuitive claim formula. |
| | - Hook too generic → inject the most specific element available: named company, specific number, or concrete role title |
| | - Sounds AI-generated → add 1-2 conversational markers: "here's the thing", "and honestly", sentence fragments, rhetorical pauses |
| | After auto-fix, re-run critic. If still <5, output with a "NEEDS USER REVIEW" flag in the header. |

**Autopilot anchor selection:**
If no anchor source was provided by the user, auto-select in this priority:
1. Best data point from brave-research → "Curator with a take" opening
2. Trend observation from script-analyzer → "Observer" opening
3. Counterargument from blindspot-detector → "Contrarian" opening
Never use a generic opening. Always pick the most specific available anchor.

**Quality floor (non-negotiable even in autopilot):**
- Hook must be ≤15 words with at least 1 concrete noun — no exceptions
- LinkedIn version must have at least 1 "I noticed..." or personal observation marker
- Never output a script that sounds like a report — if tone check fails, rewrite the first 2 sentences in conversational voice
- All three platform versions must be distinct — not translations of each other

### Phase 4 — REVISE
Apply the critic's feedback. Focus only on the failing checks — do not rewrite what's working.

### Phase 5 — QUALITY GATE: Freeze

Final verification before output:

**LinkedIn gate:**
- [ ] Hook is ≤15 words
- [ ] Contains a named tool, company, or specific number
- [ ] Has at least one "I noticed..." or personal observation
- [ ] CTA drives saves or comments (not just "follow me")

**X gate:**
- [ ] Tweet 1 works as a standalone post
- [ ] Each tweet is ≤280 characters
- [ ] Thread has a clear narrative arc (not just a list)

**小红书 gate:**
- [ ] Written in Chinese
- [ ] Opens with a pain point, not a claim
- [ ] References Chinese professional context

If all gates pass → FREEZE and output.
If any gate fails → fix only the failing element, then output.

## Output Format

```
## 口播 Optimizer Output: [TOPIC]

### PLAN
North star insight: [One sentence]
Content anchor: [Source type + specific detail — e.g., "Reddit thread on r/finance, top comment said X"]
Platform priority: [1st / 2nd / 3rd]

---

### LINKEDIN VERSION (60-90 sec)
[Full spoken script with [PAUSE] markers]

Hook strength: X/10
Humanization elements: [What makes this sound human]
Key insight (one sentence): [Summary]

---

### X THREAD VERSION
Tweet 1: [Hook]
Tweet 2: [Point 1]
Tweet 3: [Point 2]
Tweet 4: [Point 3]
Tweet 5: [Point 4]
Tweet 6: [Actionable takeaway]
Tweet 7: [CTA]

---

### 小红书 VERSION
[Full Chinese spoken script]

---

### REFLECTION LOG
Critic checks passed: X/8
Revisions made: [What was changed and why]

### OPTIMIZATION NOTES
- Hook alternatives: [2 backups]
- Best posting time: LinkedIn [day/time] | X [day/time] | 小红书 [day/time]
- Hashtags: LinkedIn [3-5] | X [2-3] | 小红书 [3-5]
- Thumbnail text: [Short phrase for video cover]

### FINAL SCORE
Hook: X/10
Authenticity: X/10
Actionability: X/10
Product Thinking Angle: X/10
Platform Fit: X/10
```

## Context
- This is the final output stage — script must be ready to record without further editing
- Core positioning: product thinking applied to AI in Finance
- User is an observer/synthesizer — content anchors come from news, YouTube/podcasts, X threads, Reddit, and conversation insights, not direct finance industry experience
- LinkedIn AI content gets ~30% less reach — specific source references and named reactions make it sound human
- Upstream: receives PROCEED verdict from `/blindspot-detector`
- Downstream: output logged to `/content-memory` after publishing

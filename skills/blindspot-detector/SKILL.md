# Blindspot Detector Skill

## Trigger
User invokes `/blindspot-detector` followed by a topic, draft script, or Script Analyzer report.

## Purpose
Adversarial challenge layer. Surface blind spots, missing evidence, weak arguments, and differentiation gaps. Outputs a structured verdict — PROCEED, REVISE, or NEEDS RESEARCH — that gates entry into script writing.

## Instructions

### Phase 1 — PLAN
Read the input and identify:
1. What is the central claim being made?
2. What evidence is currently cited (if any)?
3. What audience assumptions are embedded?

This determines which blindspot categories to prioritize.

### Phase 2 — EXECUTE (5 adversarial checks)

**Check 1: Counterargument Stress Test**
Play three adversarial roles simultaneously:
- The skeptical senior finance professional: "I've heard this before. Prove it."
- The AI skeptic: "LLMs hallucinate on financial data. This is dangerous advice."
- The failed adopter: "I tried this at my firm. Here's why it didn't work."

For each counterargument, assign severity:
- CRITICAL: If left unaddressed, this kills credibility
- MODERATE: Weakens the argument but doesn't kill it
- MINOR: Worth acknowledging but not blocking

**Check 2: Evidence Gap Audit**
Flag every claim that lacks a source:
- Specific statistics → need publication + year
- "Most companies" / "many analysts" → need quantification
- Named company examples → need verifiable source
- Tool recommendations → need real use case, not hypothetical

For each gap, specify: what type of source would fix it (McKinsey report, company announcement, LinkedIn data, etc.)

**Check 3: Audience Assumption Pressure Test**
Challenge three assumptions:
- Is this pain point real or assumed? (Would a finance analyst actually feel this?)
- Is the content level right? (Too basic = condescending; too technical = alienating)
- Is "product thinking" genuinely applied, or just mentioned as a label?

**Check 4: Differentiation Pressure Test**
Check saturation:
- Has this exact angle been covered by Allie K. Miller, Andrew Ng, Jim Marous, or Chris Skinner?
- If yes: what's the delta — what does this version add that theirs doesn't?
- Is there a "only I can say this" element? If not, the content is replaceable.

**Check 5: Platform Fit Check**

LinkedIn:
- Does it have a save-worthy insight? (Not just interesting — worth bookmarking)
- Does it sound human? (AI-generated content gets ~30% less reach)
- Is it free of overt self-promotion?

X/Twitter:
- Can the core insight fit in one punchy tweet?
- Is the hook scroll-stopping in a fast feed?

小红书:
- Does it connect to Chinese workplace context (not just translated Western content)?
- Is the tone authentic, not polished?

### Phase 3 — VERIFY (Verdict Gate)

Count critical gaps:

| Severity | Count | Action |
|----------|-------|--------|
| 0 CRITICAL, ≤2 MODERATE | — | PROCEED to kobo-optimizer |
| 1-2 CRITICAL | — | REVISE: fix critical gaps first, then proceed |
| 3+ CRITICAL | — | NEEDS RESEARCH: run `/brave-research` on specific gaps, then re-run blindspot-detector |

The verdict is non-negotiable in manual mode — do not proceed to script writing if verdict is NEEDS RESEARCH.

### Autopilot Decision Rules (when called from --autopilot pipeline)
When running inside an autopilot pipeline, do NOT stop to ask the user. Instead:

| Verdict | Auto-Decision |
|---------|---------------|
| PROCEED | Pass through immediately with north star reflection. |
| REVISE (1-2 CRITICAL) | Auto-apply the top 3 fixes using these rules: |
| | - "Needs personal story" → switch to observer framing ("I've been watching...", "I noticed...") — never fabricate experience |
| | - "Needs data" → if brave-research tagged "data-light", accept and use counter-intuitive claim formula instead |
| | - "Differentiation weak" → sharpen the product thinking angle: reframe as a system, tradeoff, or value chain insight |
| | - "Audience assumption wrong" → narrow to the most specific pain point that IS validated |
| | After auto-fixes, do NOT re-run blindspot-detector. Proceed with fixes applied. |
| NEEDS RESEARCH (3+ CRITICAL) | Auto-run ONE targeted `/brave-research` on the single most critical gap. Then auto-downgrade remaining gaps: observer framing for missing stories, "data-light" tag for missing stats. Proceed — do NOT loop more than once. |

**Auto-downgrade priority (when multiple gaps exist):**
1. Fix the gap with the highest credibility impact first
2. Downgrade remaining gaps to observer framing
3. Flag all downgrades in the output header so the user sees them in the final review

**Quality floor (non-negotiable even in autopilot):**
- Never proceed with a claim that contradicts found evidence — either address the contradiction or drop the claim
- Never suppress a CRITICAL counterargument — it must be addressed in the script, even if briefly
- The north star reflection is always generated — it's the single most important input for kobo-optimizer

### Phase 4 — REFLECT
After issuing the verdict, add one reflection:
- What is the single most important thing that would make this content 2x better?
- This becomes the "north star" for the kobo-optimizer stage.

## Output Format

```
## Blindspot Report: [TOPIC]

### PLAN
Central claim: [One sentence]
Evidence currently available: [List or "None"]
Key audience assumptions: [List]

### Check 1: Counterarguments
CRITICAL:
- [Counterargument] → How to address: [Specific response]

MODERATE:
- [Counterargument] → How to address: [Specific response]

MINOR:
- [Counterargument] → Acknowledge as: [Nuance to add]

### Check 2: Evidence Gaps
- [ ] CRITICAL: [Claim] → Need: [Source type]
- [ ] MODERATE: [Claim] → Need: [Source type]
- [ ] MINOR: [Claim] → Need: [Source type]

### Check 3: Audience Assumptions
Pain point reality: [Real / Assumed / Partially real]
Content level: [Too basic / Right / Too technical]
Product thinking applied: [Genuine / Superficial / Missing]
Adjustments needed: [Specific fixes]

### Check 4: Differentiation
Covered by: [Benchmark accounts + what they said]
Your delta: [What this version adds]
"Only you can say this" element: [Present / Missing — if missing, suggest what it could be]

### Check 5: Platform Fit
- LinkedIn: [Pass / Fail + specific issue]
- X: [Pass / Fail + specific issue]
- 小红书: [Pass / Fail + specific issue]

### VERDICT
Critical gaps: X | Moderate gaps: X | Minor gaps: X
Decision: [PROCEED / REVISE / NEEDS RESEARCH]

If REVISE — Top 3 fixes before writing:
1. [Most important]
2. [Second]
3. [Third]

If NEEDS RESEARCH — Run:
/brave-research "[specific query 1]"
/brave-research "[specific query 2]"

### REFLECTION
North star for script writing: [The single most important thing to get right]
```

## Context
- Goal: Make content bulletproof, not kill good ideas
- Finance professionals are skeptical by training — intellectual honesty earns more trust than oversimplification
- The user's edge is "product thinking in AI/Finance" — always verify this is genuinely present
- Upstream: receives output from `/script-analyzer`
- Downstream: PROCEED verdict unlocks `/kobo-optimizer`

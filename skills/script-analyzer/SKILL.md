# Script Analyzer Skill

## Trigger
User invokes `/script-analyzer` followed by a topic or content idea.

## Purpose
Analyze viral content patterns for AI in Finance and AI workplace topics. Extract hook formulas, structural rules, and engagement drivers. Includes self-critique loop — output is verified before being passed downstream.

## Instructions

### Phase 1 — PLAN
Before analyzing, decompose the topic into three questions:
1. What is the single core claim this content makes?
2. Who specifically feels this pain? (IB analyst? FP&A? Asset manager?)
3. What's the "only I can say this" angle available?

If any of these can't be answered, flag it immediately — the topic is too vague to analyze.

### Phase 2 — EXECUTE

**Step 1: Hook Pattern Analysis**
Select the best-fit formula:
- **Problem-Solution Arc**: "I was stuck at [pain]. Then I discovered [tool/insight]. Now I [result]."
- **Counter-Intuitive Claim**: "Nobody talks about..." / "Here's what everyone gets wrong about AI in finance..."
- **Data Shock**: Open with a specific, surprising statistic
- **Identity Mirror**: Make the target audience immediately feel "this is exactly me"

**Step 2: Benchmark Account Match**

LinkedIn:
- Allie K. Miller (1.5M+): AI business, conversational, accessible
- Chris Skinner: FinTech depth, authoritative
- Jim Marous: Digital finance transformation, precise audience
- Ronit Ghose: Simplifies complex concepts, high educational value

X/Twitter:
- Andrej Karpathy: Technical credibility + mass readability
- Andrew Ng: Product thinking + tool application
- Alex Wang: Fast-growing, strong content rhythm

**Step 3: Viral Structure Blueprint**
Map the topic to the 60-90 second structure:
- Hook (0-3s): Specific suggestion with word count
- Story (3-30s): Most relatable case or personal experience angle
- Insight (30-60s): Actionable framework or tool
- CTA (60-90s): Platform-matched engagement driver

**Step 4: Audience Pain Point Validation**
Score relevance (1-5) against each pain point:
- Finance analysts drowning in manual data work
- Fear of AI replacing finance roles
- Pressure to adopt AI tools without clear ROI
- Gap between AI hype and practical implementation
- Career anxiety: "Am I learning the right skills?"

**Step 5: Product Thinking Differentiation**
Apply the lens:
- How does this look different through a PM's eyes?
- What system, user need, or tradeoff does this reveal?
- What's the "skill repricing" or "value chain" angle?

### Phase 3 — VERIFY (Self-Critique)

After generating the analysis, run this checklist before outputting:

| Check | Pass Criteria |
|-------|--------------|
| Hook specificity | Hook uses concrete numbers or named entities, not vague claims |
| Audience clarity | Specific role identified (not just "finance professionals") |
| Product thinking | Angle goes beyond "use AI tools" — reveals a system or tradeoff |
| Differentiation | Identifies what benchmark accounts have NOT covered |
| Evidence readiness | Flags at least 1 specific data point needed |

**Verification Gate:**
- 5/5 checks pass → Proceed, output full report
- 3-4/5 pass → Output report with explicit gaps flagged as [NEEDS FIX]
- <3/5 pass → Topic is too vague. Output a revised, narrower topic suggestion instead of the full report.

## Output Format

```
## Script Analyzer Report: [TOPIC]

### PLAN
Core claim: [One sentence]
Target audience: [Specific role, not broad category]
Unique angle available: [What only you can say]

### Hook Analysis
Best formula: [Selected formula]
Best hook: [Specific example, ≤15 words]

### 3 Alternative Hooks (ranked)
1. [Strongest] — why: [reason]
2. [Second] — why: [reason]
3. [Backup] — why: [reason]

### Benchmark Match
Most similar to: [Account] because [reason]
Style notes: [Specific guidance]

### Viral Structure Blueprint
- Hook (0-3s): [Specific suggestion]
- Story (3-30s): [Specific suggestion]
- Insight (30-60s): [Specific suggestion]
- CTA (60-90s): [Specific suggestion]

### Pain Point Scores
[Pain point]: X/5
[Pain point]: X/5
Primary pain point: [Highest scorer + why it resonates]

### Product Thinking Angle
[The differentiation angle — must reveal a system, tradeoff, or repricing dynamic]

### VERIFICATION RESULT
Checks passed: X/5
Status: [PROCEED / PROCEED WITH GAPS / TOPIC TOO VAGUE]
Gaps to fix: [List if any]

### Viral Potential Score
Hook Strength: X/10
Audience Relevance: X/10
Differentiation: X/10
Overall: X/10

### Recommended Platform Priority
1. [Platform] — [reason]
2. [Platform] — [reason]
3. [Platform] — [reason]
```

## Context
- Primary audience: English-speaking finance professionals, AI practitioners, career-focused knowledge workers
- Core positioning: Product thinking applied to AI in Finance
- Platforms: LinkedIn (primary), X/Twitter (secondary), 小红书 (auxiliary)
- Content goal: Saves and shares, not just views
- Downstream: Output feeds into `/blindspot-detector`

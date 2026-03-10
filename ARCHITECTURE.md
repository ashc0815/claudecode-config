# Architecture Pattern Analysis

An analysis of the design patterns, strengths, and improvement opportunities in this Claude Code skills-based content creation pipeline.

---

## System Overview

```
                        /content-agent (Orchestrator)
                       /        |        \          \
                      /         |         \          \
              brave-research  script-   blindspot-  kobo-
              (Stage 1)      analyzer   detector    optimizer
                             (Stage 2)  (Stage 3)   (Stage 4)
                                                        |
                                                   content-memory
                                                    (Stage 5)
```

**8 skills total:** 5 pipeline skills + 3 utility skills (ask-user-question, find, brave-research as standalone)

---

## Pattern 1: Plan-Execute-Verify (Every Skill)

Every pipeline skill follows a consistent 3-phase internal structure:

| Phase | Purpose | Implementation |
|-------|---------|----------------|
| **Plan** | Decompose input into structured questions | script-analyzer asks 3 questions; blindspot-detector identifies claim + evidence + assumptions |
| **Execute** | Run the core analysis/generation | Multi-step execution with explicit substeps |
| **Verify** | Self-critique with pass/fail gate | Quantified checklist (5/5, 8/8, etc.) with threshold-based verdicts |

**Strength:** Consistent mental model across all skills. A developer (or Claude) can reason about any skill the same way.

**Strength:** The verify phase catches quality issues before they cascade downstream. Each gate has explicit numeric thresholds, not subjective judgment.

**Observation:** brave-research adds a 4th phase (Reflect) that asks "does this strengthen or complicate the claim?" This is the only skill with an explicit epistemic check — worth considering for other skills.

---

## Pattern 2: Orchestrator + Subagent

`content-agent` is a pure orchestrator — it contains zero content logic. All intelligence lives in the subagent skills.

**Design decisions:**
- Orchestrator manages **state passing** via a structured Pipeline State block
- Orchestrator manages **error recovery** (downgrade rules, retry policies)
- Subagents are **stateless** — each receives its full context via input, not shared state
- Subagents are **independently callable** — `/script-analyzer` works alone without `/content-agent`

**Strength:** Each skill can be developed, tested, and iterated independently. The user can run manual stage-by-stage or let the orchestrator handle it.

**Strength:** The dual-mode design (`--deep` 5-stage vs `--fast` 2-stage) reuses the same subagents but skips stages. This avoids duplicating skill logic for different cadences.

**Risk:** The Pipeline State block is a text convention, not enforced structure. If a subagent's output format drifts, the orchestrator may pass incomplete context to the next stage.

---

## Pattern 3: Verification Gates (Inter-Skill)

Each stage outputs a verdict that gates the next stage:

```
brave-research  →  STRONG / WEAK / NO EVIDENCE
script-analyzer →  PROCEED / PROCEED WITH GAPS / TOPIC TOO VAGUE
blindspot-detector → PROCEED / REVISE / NEEDS RESEARCH
kobo-optimizer  →  X/8 checks passed (internal freeze gate)
```

**Strength:** Non-negotiable gates prevent garbage-in-garbage-out. The `NEEDS RESEARCH` verdict loops back to `brave-research`, creating a self-healing cycle.

**Strength:** Verdicts are categorical (not scores), making routing decisions unambiguous.

**Design insight:** The gates form a **narrowing funnel** — early stages filter broad topics, later stages polish quality. This mirrors how human editorial processes work.

---

## Pattern 4: Reflection Loop (Draft-Critique-Revise-Freeze)

Implemented most explicitly in `kobo-optimizer`:

```
Draft → Self-Critique (8 checks) → Revise (if needed) → Quality Gate → Freeze
```

**Key rules:**
- 7-8/8 checks → proceed
- 5-6/8 checks → 1 revision loop, then proceed
- <5/8 checks → stop, ask for user input
- Max 1 revision loop (prevents infinite cycling)

**Strength:** The bounded retry (max 1 loop) prevents the common failure mode of LLM self-critique loops where quality oscillates rather than improves.

**Strength:** The <5/8 escape hatch correctly identifies when the problem is missing input (personal story, data point), not poor execution.

---

## Pattern 5: Graceful Degradation (Downgrade Rules)

The orchestrator has explicit downgrade rules when stages are blocked:

| Blocker | Downgrade |
|---------|-----------|
| No personal story | Observer framing ("I've been watching...") |
| No data found | Skip data hook, use counter-intuitive claim |
| Topic too vague after retry | Auto-narrow to most specific sub-angle |
| NEEDS RESEARCH after retry | Proceed with gaps flagged in output |

**Strength:** The system never blocks indefinitely. Every failure mode has a fallback, and every downgrade is **visible in the output** (never silent).

**Strength:** This matches the user's stated preference for consistency (2-3 posts/week) over perfection.

---

## Pattern 6: Memory-Augmented Learning

`content-memory` implements a 3-layer learning system:

| Layer | Trigger | Purpose |
|-------|---------|---------|
| Auto-log | Automatic after Stage 4 | Record what was created (zero user effort) |
| Performance update | Manual, ~2 min | Record what worked (real-world signal) |
| Monthly review | Manual, every ~10 posts | Extract durable patterns |

**Strength:** The auto-log layer has zero friction — it runs without user action. This solves the classic "users don't log" problem.

**Strength:** The review explicitly ignores pipeline metrics (blindspot gap counts, reflection loop rates) and focuses only on real-world outcomes (saves, views, user feelings). This prevents optimizing for process metrics over results.

**Strength:** The freeform "feeling" note is treated as the most valuable signal — more qualitative than quantitative, which matches creative work.

---

## Pattern 7: Source Tiering (brave-research)

Research sources are pre-classified into 3 tiers with explicit handling rules:

- **Tier 1** (McKinsey, Bloomberg, FT): Use directly
- **Tier 2** (HBR, CFA Institute): Use with context
- **Tier 3** (vendor whitepapers, blog posts): Flag as potentially biased

**Strength:** Prevents the common LLM failure of treating all search results as equally credible.

**Strength:** The 18-month recency window is calibrated to AI's fast-moving landscape.

---

## Cross-Cutting Concerns

### Consistency Across Skills

All skills share:
- Markdown-formatted structured output with headers and tables
- Explicit output templates (copy-paste ready)
- Context sections explaining upstream/downstream dependencies
- Quantified quality gates (not subjective assessments)

### What's Missing

1. **No error logging.** When a pipeline fails or downgrades, this isn't captured in content-memory. Over time, tracking which stages fail most often would reveal systematic issues (e.g., "brave-research fails 40% of the time on AI regulation topics").

2. **No A/B testing structure.** The 3 alternative hooks from script-analyzer are ranked but only one is used. Recording which hook was chosen and how it performed would close the feedback loop on hook selection.

3. **No cross-session topic planning.** `content-memory topic-check` prevents repetition but doesn't proactively suggest topics. A "topic backlog" skill could maintain a ranked queue of ideas.

4. **Platform-specific feedback loops.** Performance data is collected per-platform but the review doesn't produce platform-specific recommendations (e.g., "your Data Shock hooks work 2x better on LinkedIn than X").

---

## Architecture Quality Summary

| Dimension | Rating | Notes |
|-----------|--------|-------|
| Modularity | High | Skills are independent, composable, and independently testable |
| Error handling | High | Every failure has a defined fallback; never blocks indefinitely |
| Consistency | High | All skills follow Plan-Execute-Verify; output formats are standardized |
| Learning | Medium | Auto-logging is strong; feedback loop from performance to creation is manual |
| Scalability | Medium | Adding new platforms or content types would require touching multiple skills |
| Observability | Low | No pipeline-level logging of stage failures, downgrades, or timing |

---

## Recommendations

### Quick wins (no structural changes needed)

1. **Add a `failures` section to content-memory auto-log** — record which stages were downgraded and why. After 20 sessions, review for patterns.

2. **Track hook selection in content-memory** — log which of the 3 alternative hooks was used, enabling future review to correlate hook formulas with performance.

### Medium-term improvements

3. **Platform-specific review in content-memory** — split the monthly review analysis by platform to surface platform-specific patterns.

4. **Topic backlog skill** — maintain a ranked queue of topic ideas sourced from brave-research discoveries, blindspot-detector suggestions, and user brainstorms.

### Architectural evolution

5. **Shared schema for Pipeline State** — formalize the state-passing block as a required structure (not just a text convention) to prevent context drift between stages.

6. **Conditional skill loading for new platforms** — if expanding beyond LinkedIn/X/小红书, consider a platform adapter pattern where kobo-optimizer delegates to platform-specific formatters.

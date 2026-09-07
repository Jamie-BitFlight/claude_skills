# Backlog Lifecycle Process Audit

**Date**: 2026-03-02
**Method**: `/improve-processes` excellence checklist + triage protocol
**Scope**: Full backlog item lifecycle — create, groom, discuss, research, validate, feasibility, plan, implement, close/resolve
**Skills audited**: `create-backlog-item`, `groom-backlog-item`, `work-backlog-item`, `add-new-feature`, `fact-check`, `rt-ica`, `backlog` (MCP interface), `close-resolve-procedure.md`

---

## The Lifecycle As-Documented

```text
CREATE → GROOM → WORK → (IMPLEMENT) → CLOSE/RESOLVE

/create-backlog-item     → per-item file (~/.dh/projects/{slug}/backlog/) + optional GitHub Issue
/groom-backlog-item      → validity check → fact-check → RT-ICA → classify → root-cause → groomer agent → write sections
/work-backlog-item       → find item → already-implemented? → GitHub sync → auto-groom → RT-ICA gate → compose → /add-new-feature → update plan ref
  /add-new-feature       → discovery → codebase analysis → architecture → tasks → validate → context manifest
/work-backlog-item close → dismiss with reason
/work-backlog-item resolve → checklist → acceptance criteria → PR check → evidence trail
```

---

## Excellence Checklist Results

| # | Criterion | Rating | Evidence |
|---|-----------|--------|----------|
| 1 | **Clarity** — no interpretive gaps | **PARTIAL** | 6 specific gaps identified (Findings 1, 2, 4, 5, 9, 10) |
| 2 | **Determinism** — same input → same output | **PARTIAL** | Optional steps without criteria for when to exercise them |
| 3 | **Minimal cognitive load** | **FAIL** | `work-backlog-item` is 677 lines across main file + 8 reference files; an agent must hold 9+ step numbering schemes simultaneously |
| 4 | **Explicit feedback loops** | **FAIL** | No retry/escalation path when grooming or fact-check produces low-quality output |
| 5 | **Measurable outcomes** | **PASS** | Terminal states (STOP, APPROVED, BLOCKED, RESOLVED, CLOSED) are named and observable |
| 6 | **Visible constraints** | **PARTIAL** | Some preconditions are inline text, not gate checks |
| 7 | **Ownership** — every step names the actor | **PASS** | Orchestrator, sub-agent types, hooks, and user clearly assigned |
| 8 | **Edge case coverage** | **PARTIAL** | Error handling documented but 4 gaps found |
| 9 | **Teachable in 5 minutes** | **FAIL** | 5 skills x 9+ steps each; no single-page overview exists |
| 10 | **Auditable** — execution traceable after the fact | **PARTIAL** | Timestamps written but no session-level audit trail linking all steps |

---

## Finding 1: No Feasibility Assessment Step Exists

**Category:** Missing process step
**Severity:** High

The word "feasibility" does not appear anywhere in the backlog workflow. RT-ICA checks *information completeness* (do we have enough to plan?), not *feasibility* (can this actually be done? is it worth doing? what are the risks?).

**Gap**: Between grooming (Step 5: RT-ICA says APPROVED) and planning (Step 6: `add-new-feature`), there is no gate for:

- Technical feasibility — "Can this be built with our stack?"
- Effort/value assessment — "Is this worth the investment?"
- Risk assessment — "What could go wrong?"
- Alternative evaluation — "Is there a simpler approach?"

RT-ICA answers: "Do we have enough information?" → yes/no.
Feasibility answers: "Should we proceed?" → yes/no/defer.

**Impact**: Items pass RT-ICA (all inputs available) but may be infeasible, disproportionately expensive, or superseded by a simpler alternative. The SAM planning pipeline runs (expensive: 4-6 agent delegations) before anyone asks "should we?"

**Recommendation**: Add a feasibility gate between RT-ICA APPROVED and SAM planning invocation, either as a new step in `work-backlog-item` (Step 4b) or as part of a richer grooming output.

---

## Finding 2: "Discussion" Phase Is Absent

**Category:** Missing process step
**Severity:** Medium

No skill provides a structured discussion or interview step. The closest analogues:

- `create-backlog-item` guided intake (5 questions) — but only for *creation*, not refinement
- ARL human-probing design doc — **not implemented** (marked "Status: Design")
- Groomer agent receives "Additional context from conversation" — but never *elicits* it

**Gap**: Between creation and grooming, there is no step where a human or domain expert can:

- Challenge assumptions in the description
- Add context the creator didn't have
- Negotiate scope or priority
- Record design constraints ("we tried X before and it failed because...")

**Impact**: Items enter grooming with only the creator's perspective. The groomer agent researches autonomously but cannot access invisible knowledge that only exists in a human's head.

**Recommendation**: Implement the ARL human-probing design (already documented at `.claude/docs/sdlc-layers/arl-human-probing-design.md`) and integrate it as a concrete step. Alternatively, add a lightweight "interview" mode to `groom-backlog-item` that asks structured domain questions before spawning the groomer.

---

## Finding 3: RT-ICA Runs Twice (Redundantly)

**Category:** No-op / wasted work
**Severity:** Low-Medium

RT-ICA runs in two places:

1. `groom-backlog-item` Step 5 — writes RT-ICA section to item file
2. `work-backlog-item` Step 4 — checks for RT-ICA in groomed content; if absent, re-runs it

If grooming wrote RT-ICA, `work-backlog-item` reads it and proceeds. But if the item was groomed in a *previous session* and the codebase changed since, the old RT-ICA may be stale — yet `work-backlog-item` accepts it without re-verification.

Conversely, if `work-backlog-item` auto-grooms (Step 3), RT-ICA runs inside grooming AND then Step 4 checks it again — the second check is always a no-op because it just happened.

**Gap**: No staleness check on RT-ICA results. No defined policy for when RT-ICA should be re-run vs. accepted from cache.

**Recommendation**: Add a freshness check: if RT-ICA is older than N days or the item's description has changed since the RT-ICA date, re-run it. Otherwise accept the cached result.

---

## Finding 4: Vague Conditions in Groom Step 2

**Category:** Non-evaluable decision condition
**Severity:** Medium

`groom-backlog-item` Step 2.1:

> "Is the job still valid?" — Scope, priority, or context may have changed. **Ask or infer**: does this item still belong in the backlog?

"Ask or infer" is not evaluable by an AI agent. What observable fact determines this? The process doesn't specify:

- Who to ask
- What signals indicate invalid scope
- How to "infer" validity from codebase state

**Recommendation**: Replace with concrete checks:

1. Was the item created > 30 days ago with no activity? → Flag for human review
2. Has the item's `suggested_location` file been deleted or heavily refactored? → Flag
3. Does a more recent item supersede this one? → Search by keywords, report overlap

---

## Finding 5: Step Numbering Is Non-Sequential and Fragmented

**Category:** Cognitive load / clarity
**Severity:** Medium

`work-backlog-item` uses: Step 0, 1b, 1, 2, 2.3, 2.5, 2.5a, 2.7, 3, 4, 5, 6, 7, 8, 9 (with 9a-9f in a reference file). The numbering:

- Has gaps (no Step 2.1, 2.2, 2.4, 2.6)
- Uses decimal substeps inconsistently (2.3, 2.5, 2.7 but not 2.1)
- Has a lettered substep variant (1b)
- Step 9 delegates to a separate file with its own 9a-9f scheme

This makes it hard for an agent to track position and for a human to audit execution.

**Recommendation**: Renumber sequentially. Group related steps into named phases:

```text
Phase 1: Locate (find item, issue-first path, extract fields)
Phase 2: Validate (already-implemented check, GitHub sync, set labels)
Phase 3: Prepare (auto-groom, RT-ICA gate)
Phase 4: Plan (compose request, invoke SAM, update backlog)
Phase 5: Close/Resolve
```

---

## Finding 6: No Feedback Loop on Groomer Agent Quality

**Category:** Missing feedback loop
**Severity:** Medium

`groom-backlog-item` Step 8 spawns a `backlog-item-groomer` agent (haiku model). The groomer output is written directly to the item file in Step 9. There is no:

- Quality check on groomer output (did it follow scope boundary?)
- Validation that all required sections are present
- Rejection/retry path if output is incomplete or includes implementation details

**Impact**: A haiku-model agent with ~50% accuracy on ambiguous tasks (per CLAUDE.md's own Explore agent assessment) writes directly to canonical item files. No gate catches bad output.

**Recommendation**: Add a validation step between Step 8 and Step 9:

1. Check groomer output has all required sections (Reproducibility, Priority, Impact, Scope, Output/Evidence, Dependencies, Research)
2. Check no implementation language appears (architecture, design, code, implementation, solution)
3. If validation fails → re-spawn with corrective prompt or escalate to sonnet model

---

## Finding 7: `create-backlog-item` --auto Mode Silently Derives Priority

**Category:** Silent assumption
**Severity:** Low

Auto mode derives priority from "urgency keywords" (`critical`, `required`, `must` → P1; `nice to have`, `optional` → P2; default P1). This means:

- Most items default to P1 regardless of actual importance
- Priority is derived from *word choice*, not *problem severity*
- No validation that the derived priority is correct

**Impact**: Auto-created items skew P1-heavy, diluting the meaning of P1.

**Recommendation**: Default to P2 (not P1) for auto-mode. P1 should require either an urgency keyword match or an explicit flag.

---

## Finding 8: Fact-Check Auto-Commits and Pushes

**Category:** Side-effect risk
**Severity:** Low

`fact-check` SKILL.md Step 6 (Post-Actions) says:

- Commit: `git add ~/.dh/projects/{slug}/backlog/ && git commit -m "..."` (NOTE: state files outside repo — this step may be a no-op or apply to other committed files)
- Push: `git push -u origin HEAD`

This auto-commits and pushes without user confirmation, potentially:

- Committing to the wrong branch
- Pushing partial work
- Conflicting with the user's staged changes

No other skill in the chain auto-pushes. This is inconsistent.

**Recommendation**: Remove auto-push from fact-check. Let the calling skill (`groom-backlog-item`) decide when to commit/push, consistent with the rest of the workflow.

---

## Finding 9: 6 Implied Handoffs Without Explicit Invocation

**Category:** Missing connective tissue
**Severity:** High

Several critical transitions between skills are *implied* (shown in completion text as "Next steps: run X") but never *invoked*. This means an agent in `--auto` mode would get stuck.

| Gap | From → To | How it works today |
|---|---|---|
| A | `create-backlog-item` → `groom-backlog-item` | Text output only: "Groom: /groom..." |
| B | `groom-backlog-item` → `group-items-to-milestone` | Not mentioned at all |
| C | `group-items-to-milestone` → `start-milestone` | Not mentioned at all |
| D | `complete-implementation` → `work-backlog-item resolve` | Not mentioned — user must know |
| E | `work-backlog-item resolve` → `complete-milestone` | Not mentioned at all |
| F | `fact-check` → back to `groom-backlog-item` | Implicit session coupling, no artifact |

**Impact**: A human must know the full state machine to navigate these transitions. Autonomous operation breaks at every implied handoff.

**Recommendation**: For each implied handoff, either:

1. Add explicit "Next step" output with the skill invocation, or
2. Document the full state machine in a single lifecycle overview that all skills reference

---

## Finding 10: Draft Lifecycle Doc Exists But Isn't Promoted

**Category:** Missing documentation
**Severity:** Medium

`.claude/docs/backlog-lifecycle.draft.md` exists as a DRAFT with `[VERIFY]` markers. This is exactly the kind of single-page overview that's missing — but it's not referenced by any skill and hasn't been validated.

**Recommendation**: Validate the draft against this audit's findings, promote it to canonical status, and reference it from each skill's introductory section.

---

## Missing Lifecycle Diagram

No single document shows the complete flow from creation to resolution. `local-workflow.md` covers SAM (add-new-feature → implement → complete) but not the backlog-specific front matter (create → groom → work).

The canonical flow should be:

```text
┌─────────────────────────────────────────────────────────────────────┐
│                    BACKLOG ITEM LIFECYCLE                            │
│                                                                     │
│  CREATE ──→ [DISCUSS] ──→ GROOM ──→ [FEASIBILITY] ──→ PLAN ──→    │
│             (missing)      │         (missing)          │           │
│                            │                            │           │
│                     fact-check                    add-new-feature   │
│                     RT-ICA                        (SAM pipeline)    │
│                     classify                                        │
│                     root-cause                                      │
│                     groomer agent                                   │
│                                                                     │
│  ──→ IMPLEMENT ──→ VERIFY ──→ RESOLVE (or CLOSE)                   │
│      /implement-    /complete-   /work-backlog-item                 │
│       feature       implementation  resolve | close                 │
└─────────────────────────────────────────────────────────────────────┘
```

---

## What's Strong

1. **Actor ownership** is excellent — every step names who does it
2. **Terminal states** are well-defined (STOP, BLOCKED, APPROVED, RESOLVED, CLOSED)
3. **Close/resolve** is a clean, well-structured decision tree
4. **Fact-check + RT-ICA integration** (REFUTED → MISSING) is a strong design
5. **Issue classification + root-cause analysis** (5-whys, 6-sigma) is sophisticated

---

## Priority Summary

| Priority | Finding | Effort |
|----------|---------|--------|
| **High** | F1: No feasibility gate | Medium — new step in work-backlog-item |
| **High** | F9: 6 implied handoffs break autonomous execution | Medium — add next-step output to each skill |
| **Medium** | F2: No discussion/interview step | Medium — implement ARL design doc |
| **Medium** | F4: Vague "is job valid?" condition | Low — replace with concrete checks |
| **Medium** | F5: Non-sequential step numbering | Low — renumber, add phase names |
| **Medium** | F6: No groomer output validation | Low — add section/scope check |
| **Medium** | F10: Draft lifecycle doc not promoted | Low — validate and promote |
| **Low-Med** | F3: RT-ICA staleness | Low — add freshness check |
| **Low** | F7: Auto-mode P1 default | Trivial — change default |
| **Low** | F8: Fact-check auto-push | Trivial — remove push |

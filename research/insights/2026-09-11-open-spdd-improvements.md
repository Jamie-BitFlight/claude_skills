# Improvement Proposals: OpenSPDD

**Research entry**: ./research/prompt-engineering/open-spdd.md
**Generated**: 2026-09-11
**Patterns assessed**: 5
**Backlog items created**: 2 (references: `p1-architect-spec-template-emits-no-component-design-or-type-sy`, `p1-architect-artifact-carries-no-constraints-or-anti-goals-so-s`)
**Deferred (low confidence)**: 1
**Skipped (already covered or tracked)**: 3

> **Backlog reference note**: `backlog_add` stored both items, but native GitHub issue creation
> failed in this session (`GitHub GraphQL is not available from Claude Code sessions`, 403), so
> neither item has an issue number yet. Both carry the slug reference shown above and will receive
> an issue number on the next successful backend sync.

---

## Improvement 1: Architect spec template emits no Component Design or Type System Design sections

**Source pattern**: "High-level detail ('Create BillingService')" vs "Precise details — method
signatures, parameters, error handling, dependency injection patterns" — the Operations dimension
of the REASONS Canvas (research entry, "Problem Addressed" table, and "Implementation Layer (How)"
under Key Features)
**Local system**: `plugins/development-harness/skills/planning/SKILL.md` (producer),
`plugins/development-harness/agents/contract-verification.md` (consumer)
**Confidence**: High
**Impact**: High
**Backlog**: `p1-architect-spec-template-emits-no-component-design-or-type-sy` created (P1, Feature)

### Current state

`planning/SKILL.md` registers `artifact_type="architect"` (lines 88-96) and defines the full
content template (lines 100-179). Its Solution Design section contains only `### Approach`,
`### Components` (`1. **<Component Name>** — <purpose and responsibility>`), `### Interactions`,
and `### Boundaries`. `context-integration/SKILL.md` re-registers the same `architect` artifact and
adds Scope Analysis, Conflict Report, Resource Map, Integration Points, and File Impact Summary.
Neither template contains a `## Component Design` section or a `## Type System Design` section.

`agents/contract-verification.md` (Contract Extraction Process, Steps 1-2) fetches the `architect`
artifact and extracts contracts exclusively from "the Component Design section (typically titled
`## Component Design` or `## 4. Component Design`)" and the Type System Design section.
`skills/implement-feature/SKILL.md` (lines 153-168) dispatches this agent after every completed
task and instructs it to "read its Component Design and Type System Design sections".

The producing stages never emit the sections the consuming verifier reads. The verifier's normal
path is to find no contracts and report a clean result, so signature and type-contract drift passes
S5/S6 unexamined while appearing verified.

This is the producer side. #3317 covers the consumer side (contract-verification matching only two
heading variants with no fallback) and assumes the sections exist somewhere; it does not address
their absence from every upstream template.

### Target state

The `architect` artifact carries per-component interface detail at the granularity
contract-verification extracts: each component's function names with parameter names, parameter
types, and return types, plus the domain type contracts. The section heading in the producing
template matches the heading contract-verification looks for, and the two are documented as one
contract rather than two independently-worded conventions.

### Measurable signal

- `grep -n "Component Design" plugins/development-harness/skills/planning/SKILL.md` (or the S3
  template, whichever stage owns the detail) returns a match inside the artifact content template.
- `grep -n "Type System Design"` returns a match in the same template.
- The heading strings present in the producing template are byte-identical to at least one variant
  listed in `agents/contract-verification.md` Steps 1-2.
- A run of `/dh:implement-feature` on a feature with an interface change produces a
  contract-verification result naming at least one extracted `expected_signature`, rather than
  "No contract concerns" with zero contracts in scope.

---

## Improvement 2: Architect artifact carries no constraints or anti-goals for S4 to derive task Constraints from

**Source pattern**: "Constraint Layer (Boundary) — **Norms (N)**: Coding standards and patterns to
follow; **Safeguards (S)**: Constraints and guardrails defining what must not be done" (research
entry, Key Features → The REASONS Canvas Framework), and "No constraints on AI — AI improvises
freely | Explicit constraints define 'how' (Norms) and 'what not to do' (Safeguards)" (Problem
Addressed table)
**Local system**: `plugins/development-harness/skills/planning/SKILL.md` (producer),
`plugins/development-harness/skills/task-decomposition/SKILL.md` (consumer)
**Confidence**: High
**Impact**: Medium
**Backlog**: `p1-architect-artifact-carries-no-constraints-or-anti-goals-so-s` created (P1, Feature)

### Current state

`task-decomposition/SKILL.md` Step 2 "Embed Complete Context" (lines 53-62) requires each generated
task to embed "Patterns to follow (from resource map)" and "Constraints and anti-goals that apply
to this specific task". Step 3 makes `5. **Constraints** — what the agent must not do` a mandatory
CLEAR section, and the output template at line 220 emits a `## Constraints` heading for every task.
The same `## Constraints` block is mandatory in `generate-task/SKILL.md` (lines 69-72).

S4's only input is the `architect` artifact (`task-decomposition/SKILL.md` lines 116-122).
"Patterns to follow" has a named upstream source — the Resource Map written by
`context-integration/SKILL.md`. Constraints and anti-goals have none. `planning/SKILL.md`'s
artifact template (lines 100-179) carries `### Boundaries` (in scope / out of scope — a scope
statement, not a behavioral prohibition) and a Risk Assessment table (likelihood / impact /
mitigation), and no section stating what an implementer must not do or which existing patterns must
be followed. `context-integration/SKILL.md` adds no such section either.

Every task's `## Constraints` block is therefore produced by the decomposer with no upstream source.
Guardrails a human decided during design — "do not add a new dependency for this", "reuse the
existing retry wrapper", "never widen this public signature" — have nowhere to be recorded in the
pipeline, and reach the worker only if the decomposer independently re-derives them.

### Target state

The `architect` artifact carries a constraint section with two distinguishable kinds of content:
patterns and standards this work must follow, and prohibitions this work must not violate —
separate from `### Boundaries` (scope) and from the Risk Assessment table (probabilistic risks with
mitigations). S4 derives each task's `## Constraints` block from that section by selection, and
states what it did when the section is empty, rather than composing constraints from nothing.

### Measurable signal

- The artifact content template in `planning/SKILL.md` contains a constraint section distinct from
  `### Boundaries` and `## Risk Assessment`.
- `task-decomposition/SKILL.md` Step 2 names that section as the source for "Constraints and
  anti-goals", the same way it names the resource map as the source for "Patterns to follow".
- Running S2 then S4 on one feature: at least one string in a generated task's `## Constraints`
  block appears verbatim, or as a direct narrowing, of a line in the architect artifact's
  constraint section.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Bidirectional sync coverage in the proportional quality gate — `complete-implementation/SKILL.md`'s proportional gate (T1-T5, lines ~169-172) has no `context-refinement` task, so no `Post-Implementation Annotations` are written back to the `architect` artifact for small changes; the full gate (line 386) does include T6 `context-refinement`. | Medium | The omission is plausibly deliberate — the gate is named "proportional" and deliberately runs a reduced task set for small changes. Raising confidence requires the design rationale for which tasks the proportional gate drops (an ADR or the gate's own selection criteria), not just the observed difference between the two task lists. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Bidirectional synchronization via `/spdd-sync` — reverse-syncing code changes back into the design document (research entry, Relevance item 3) | Already implemented, and more strongly. `plugins/development-harness/docs/plan-artifact-lifecycle.md` "Divergence policy" defines recording criteria, a two-way classification (`design-refinement` / `intent-divergence`), a `Divergence Notes` note shape, and a post-execution Freshness report. `agents/context-refinement.md` line 182 re-registers the `architect` artifact with a `## Post-Implementation Annotations` section appended, dispatched as T6 of the full quality gate in `complete-implementation/SKILL.md` (line 386). OpenSPDD's own entry lists its sync as manual, convention-based and unenforced ("Spec Drift Risk"); the local mechanism is dispatched by the gate rather than relying on team discipline. |
| Cross-tool compilation — one methodology emitted into each tool's native command format, with marker-file auto-detection (research entry, Relevance item 2) | Already tracked. 29 open backlog items cover it per plugin (e.g. #3481 development-harness, #3491 plugin-creator, #3496 scientific-method), against the `claude-code` / `codex` / `hermes` / `kimi` target set recorded in `harness_compatibility.json`. |
| Capability vs. Control — "when multiple 'correct' solutions exist, choosing which one is a human trade-off decision, not an AI logical inference" (research entry, Key Design Insights; Relevance item 4) | Not actionable as stated — a framing principle with no observable target state in any file. Its concrete expressions (explicit constraints, explicit prohibitions) are captured as Improvement 2; the remaining content is philosophy. |

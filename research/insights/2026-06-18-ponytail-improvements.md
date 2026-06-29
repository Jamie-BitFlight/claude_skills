# Improvement Proposals: Ponytail

**Research entry**: ./research/agent-frameworks/ponytail.md
**Generated**: 2026-06-18
**Patterns assessed**: 5
**Backlog items created**: 1 (issues: #2649)
**Deferred (low confidence)**: 1
**Skipped (already covered or tracked)**: 3

---

## Improvement 1: Add a simplicity / over-engineering reviewer perspective to multi-perspective-review

**Source pattern**: Relevance §1 "Embedded agent instruction" — the `AGENTS.md` and skill definitions can be imported to "enforce simplicity on downstream agents." Backed by Key Features §"The Decision Ladder" (six-rung YAGNI → stdlib → native → installed dep → one-line → minimum-code ladder), §"Companion Skills" `ponytail-review` ("Analyzes the current diff for over-engineering and returns a delete-list"), and §"Protective Rules" (laziness enforced only where safe — never simplifies away input validation, error handling, security, accessibility, or explicitly-requested behavior).
**Local system**: plugins/development-harness/skills/multi-perspective-review/SKILL.md and references/verdict-schema.md
**Confidence**: High
**Impact**: Medium
**Backlog**: #2649 created

### Current state

`multi-perspective-review` dispatches exactly four reviewer perspectives — `security | performance | quality | accessibility` — enumerated as the only legal `perspective` enum values in `references/verdict-schema.md` line 25 and §2.4 gate logic. None of the four reviews the diff for over-engineering, speculative abstraction, or YAGNI violations. The `dh:reviewer-quality` agent's dimensions are naming violations, dead code, swallowed exceptions, test-coverage gaps, and SOLID — it flags unused code but does not flag *present, working, but unnecessarily complex* code (a 120-line cache class where a dict would do, a dependency added for what a few lines could do, a hand-rolled date picker where `<input type="date">` exists). Grep for `over-engineer|YAGNI|simpler|abstraction|premature|decision ladder` across `multi-perspective-review/` returns zero matches. The only over-engineering signal in the harness is `work-backlog-item/references/workflows/work/feasibility-gate.md` Criterion 4 — a planning-time structural heuristic that blocks only when Impact Radius is exactly 1 file AND task count >= 4. That is a coarse pre-implementation count check, not a review of the code that was actually written.

### Target state

`references/verdict-schema.md` defines a fifth perspective literal `simplicity` (enum line updated to `security | performance | quality | accessibility | simplicity`), and a `reviewer-simplicity` agent reviews changed files against a decision-ladder rubric: for each non-trivial added construct, was a lower rung available (stdlib, native platform feature, existing installed dependency, one-liner)? The reviewer emits REJECT findings as a delete-or-simplify list and is bound by an explicit protective-exclusions clause mirroring Ponytail's §"Protective Rules" — it MUST NOT flag input validation at trust boundaries, error handling that prevents data loss, security measures, accessibility code, hardware/clock/sensor calibration slack, or anything the task explicitly requested. SKIP applies when the diff contains no net-new logic (pure deletions, config-only, docs-only). The §2.4 gate logic `PERSPECTIVES` set includes `simplicity`.

### Measurable signal

Run: `rg -c '"simplicity"' plugins/development-harness/skills/multi-perspective-review/references/verdict-schema.md` returns >= 1. A `plugins/development-harness/agents/reviewer-simplicity.md` (or equivalent agent file referenced by the skill) exists and contains an explicit "never simplifies away" exclusion list naming validation, error handling, security, and accessibility. The verdict-schema `perspective` enum and §2.4 `PERSPECTIVES` membership both include `simplicity`. A test diff that adds a hand-rolled implementation of an available stdlib call produces a REJECT verdict from the simplicity perspective.

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Relevance §4 "Multi-agent orchestration debt tracking" — adapt Ponytail's `ponytail:` inline-comment debt ledger (`ponytail-debt` harvests all such comments into a tracked ledger, naming each shortcut's ceiling and upgrade path) into orchestration workflows that track intentional debt across parallel AI implementations | Medium | The gap is real — no `ponytail:`-style debt-comment convention or harvesting command exists in the repo (grep for `debt ledger`/`debt comment` in review skills returns nothing). But mapping it to a concrete local target requires inference: it is unclear whether the home is a new convention in CLAUDE.md, a harvesting script under development-harness, or an extension of the existing backlog. The research entry itself notes the mechanism "does not enforce" the debt (Limitations §"Deferred work accumulation"), so the observable target state cannot be specified without a design decision. To raise to High: confirm which existing system (backlog vs a new grep-based script vs complete-implementation gate) should own debt-comment harvesting, and define the comment grammar that would be searched. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Relevance §2 "Code quality in generated implementations" (applying ponytail principles reduces boilerplate in generated code) | Subsumed by Improvement 1 — it is the same simplicity-enforcement mechanism applied to agent output rather than to human review; no distinct observable target state separate from the simplicity reviewer perspective. |
| Relevance §3 "Plugin minimalism" (ponytail repo demonstrates minimal-surface plugin design — 5 skills reused across 13 hosts) | Too abstract — a design philosophy with no observable before/after state in a specific local file or command. Not expressible as a measurable gap per the gap-assessment rules. |
| Relevance §5 "Cost-aware agent design" (embedding ponytail principles reduces per-turn token consumption) | Philosophical, no concrete observable target. The entry's own Cost Scaling section notes the effect is model-dependent and "can go either way" — there is no file or command whose state would change to mark this complete. |

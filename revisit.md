# Revisit: Behavioral Eval Gates in the SAM Workflow

Session: 2026-05-21 — observed during #1899 implementation review

---

## 1. Wire complete-implementation T2 to skill-creator eval harness

**Observation**: `complete-implementation` T2 dispatches `dh:feature-verifier`, which checks that
implementation matches the architect spec. It does not detect new/modified skill directories and
does not invoke skill-creator Steps 7–10.

**skill-creator Steps 7–10** (read from `evaluation-and-optimization.md`) provide:
- Parallel with-skill vs without-skill runs via `claude -p`
- Assertion grading via `@plugin-creator:grader`
- Blind A/B comparison via `@plugin-creator:comparator`
- Description trigger optimization via `scripts/run_loop.py`

**Proposed change**: Add a detection step to `complete-implementation` T2. When changed files include
a new or modified skill directory under `plugins/*/skills/`, invoke skill-creator Steps 7–10 as part
of T2 before marking the phase complete. This is the behavioral effectiveness gate — tests whether
the skill produces correct output against real inputs, not just whether the file structure is valid.

**Where**: `plugins/development-harness/skills/complete-implementation/SKILL.md` — T2 dispatch section.

---

## 2. Two additions to swarm-task-planner.md

**Observation**: `swarm-task-planner.md` describes what to do when `acceptance-criteria-structured`
is non-empty, but contains no instruction to populate it. Plan P0b29a073 confirmed:
`"acceptance-criteria-structured": []` — field present, value empty, T0/TN bookends silently skipped.

### Addition 1 — Phase 3: derive check_command entries before emitting the plan

Before the planner emits the final plan YAML, derive `acceptance-criteria-structured` entries from
the architect spec's acceptance criteria. For skill and agent features, these commands exit non-zero
at T0 (artifact absent) and exit 0 at TN (artifact present and correct):

```bash
# Lint passes on the new skill/agent
uvx skilllint@latest check <path>

# Expected output artifact exists
test -f <expected-output-path>

# Expected content present in output
grep -c '<expected-content>' <output-file>
```

Each maps to one `check_command` entry in `acceptance-criteria-structured`. The T0 baseline capture
agent runs these before implementation starts and records the exit codes. The TN verification gate
re-runs them after all tasks complete and flags any criterion that regressed.

### Addition 2 — Phase 5: warn when structured criteria are empty despite non-trivial ACs

In Phase 5 (plan validation), add a check: if `acceptance-criteria-structured` is empty and the
plan contains tasks with non-trivial text-form acceptance criteria (3+ entries), emit a WARNING
in STATUS output. Do not block — the plan is still valid — but make the gap visible to the
orchestrator so it can decide whether to populate the field before dispatching.

**Where**: `plugins/development-harness/agents/swarm-task-planner.md`

---

## Context

Both gaps were observed in the same session. The capability for behavioral evaluation (skill-creator
eval harness) and for regression detection (T0/TN bookends) both exist in the codebase. The wires
between the SAM pipeline and those capabilities were not present in the implementations observed.

These are two distinct mechanisms:
- **T0/TN** — regression detection via bash assertions (did implementation break something that worked before?)
- **skill-creator eval harness** — behavioral effectiveness (does the skill produce correct output against real inputs?)

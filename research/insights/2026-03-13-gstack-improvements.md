---
title: "Improvement Proposals: gstack"
---

## Improvement 1: Add production failure mode checklist to code-reviewer agent

**Source pattern**: gstack's `/review` skill — "Paranoid Staff Engineer Mode" that asks "what can still break?" and checks for "N+1 queries, race conditions, stale reads, bad trust boundaries, escaping bugs, broken invariants, bad retry logic, and tests that pass while missing real failure modes." (Section: Eight Workflow Skills, subsection 3)
**Local system**: `plugins/python3-development/agents/code-reviewer.md`
**Confidence**: Medium
**Impact**: Medium
**Backlog**: Deferred -- confidence medium: the code-reviewer loads `holistic-linting:holistic-linting` skill which may partially cover some of these checks, and the integration-checker covers wiring issues. A full audit of what holistic-linting covers is needed to confirm the gap.

### Current state

The code-reviewer agent (`plugins/python3-development/agents/code-reviewer.md`) focuses exclusively on architecture compliance, pattern compliance, dependency utilization, and testing standards. Its Review Checklist (lines 129-161) covers type hints, docstrings, module placement, Rich/Typer patterns, and test coverage. It does not check for production failure modes: race conditions, N+1 queries, trust boundary violations, stale reads, broken invariants, retry logic correctness, or tests that pass while missing real failure scenarios.

The integration-checker agent (`plugins/python3-development/agents/integration-checker.md`) checks cross-module wiring (exports, imports, call sites, data flows) but also does not check for production failure modes.

### Target state

The code-reviewer agent's Review Checklist includes a "Production Failure Modes" section with checks for:
- Race conditions and concurrency hazards
- N+1 query patterns or unbounded iteration
- Trust boundary violations (user input flowing to privileged operations)
- Stale reads (cache invalidation, read-after-write consistency)
- Broken invariants under concurrent access
- Retry logic correctness (idempotency, backoff, max attempts)
- Tests that assert success paths but miss realistic failure scenarios

### Measurable signal

Read `plugins/python3-development/agents/code-reviewer.md` -- a section titled "Production Failure Modes" or equivalent exists in the Review Checklist, containing at least 4 of the 7 categories listed above. The code-reviewer agent output for a reviewed feature mentions at least one production failure mode assessment (even if no issues are found).

---

## Deferred Proposals (confidence too low to backlog)

| Pattern | Confidence | Reason |
|---|---|---|
| Production failure mode review checklist | Medium | The code-reviewer loads `holistic-linting:holistic-linting` skill at runtime, which may cover some production failure checks. Read that skill's content to confirm whether the gap is real or already partially addressed. Additionally, the code-reviewer's general mission of "holistic code review" could be interpreted to include these checks implicitly, though they are not documented in the checklist. |

---

## Skipped Patterns

| Pattern | Reason skipped |
|---|---|
| Role-specific agent pattern (cognitive switching) | Already covered -- the SAM pipeline in `plugins/python3-development/skills/implement-feature/SKILL.md` and `complete-implementation/SKILL.md` already implements role-specific agents: code-reviewer, feature-verifier, integration-checker, doc-drift-auditor, context-refinement. Each agent has a distinct cognitive mode and scope. |
| Browser automation with lower context overhead | Already covered -- `.claude/skills/agent-browser/SKILL.md` implements equivalent functionality: Playwright-based CLI with daemon architecture, accessibility tree refs (@e1, @e2), snapshot diffing, parallel sessions, and zero-protocol-overhead design. |
| Parallel execution via environment variables (multi-workspace isolation) | Already tracked in backlog as #452 (Concurrency cap for parallel task dispatch in implement-feature) and #453 (Systematic git worktree isolation for concurrent task agents). |
| Skill organization with shared binary across multiple skills | Already covered -- the plugin system organizes skills per-plugin with shared scripts (e.g., implementation_manager scripts in `plugins/python3-development/skills/implementation-manager/scripts/` shared across implement-feature, start-task, and complete-implementation skills). |

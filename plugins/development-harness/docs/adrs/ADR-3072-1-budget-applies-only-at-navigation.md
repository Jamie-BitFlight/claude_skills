# ADR-3072-1: Budget applies only at the Navigation stage

**Status:** Accepted
**Date:** 2026-08-20
**Issue:** [#3072](https://github.com/Jamie-BitFlight/claude_skills/issues/3072), also resolves
[#3073](https://github.com/Jamie-BitFlight/claude_skills/issues/3073) and
[#3074](https://github.com/Jamie-BitFlight/claude_skills/issues/3074)

## Context

The contract's open questions treated "what is the budget value" and "how do the table of
contents and artifact inventory page when both are large" as separate, unrelated decisions.
Before this ADR, budget checks were also implicitly assumed to happen at multiple points —
`backlog_core/server.py` alone hardcoded two different budget constants
(`_VIEW_TOKEN_BUDGET = 4_000`, `_LIST_TOKEN_BUDGET = 4_400`) for two operations, neither derived
from the engine's own `progressive_markdown.models.TOKEN_BUDGET` (env-derived from
`MAX_MCP_OUTPUT_TOKENS`, default 9,500).

## Decision

Collection (gathering source content) and Generation (assembling the complete document for a
requested scope — description, table of contents, every requested section or artifact) are both
unbounded: never truncated, never budget-checked. Navigation — the one engine described by R1 —
is the only stage where a size budget is ever applied. It receives a fully generated document,
gives it a content identity, caches it for the session, and windows it to the agent.

Consequences:

- One budget constant, sourced from the engine, not duplicated per operation. The two hardcoded
  constants in `backlog_core/server.py` are deleted, not reconciled to a shared value.
- The table of contents and the artifact inventory (R6) are not paginated as two independent
  structures with their own budget logic — they are part of one generated document, windowed by
  the same Navigation stage as everything else in it.
- A caller may request a smaller page than the configured default. There is no local equivalent
  of `tail` against a tool response, so the caller depends on the server accepting an explicit,
  smaller page-size request to peek at part of a large result.

## Considered alternative

Per-operation budget constants (the pre-existing state) were considered and rejected — no
evidence found that the 4,000/4,400 split was a deliberate sizing decision rather than drift
from two people picking round numbers at different times.

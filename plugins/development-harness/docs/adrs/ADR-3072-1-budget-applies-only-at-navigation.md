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

**Known limitation — "unbounded" has a practical ceiling, even though this decision imposes
none.** Collection and Generation being unbounded means the first-generation cost for a
pathological item is paid in full before Navigation ever gets to window it — this is a real
cost, not merely a theoretical one: a peer review reproduced item #2953 at an estimated 270,946
tokens across 91 sections, and its `map` response alone (over 125,000 characters) overflowed
the harness's own tool-result cap. This decision does not impose a ceiling on Collection or
Generation — doing so would reintroduce the truncation this whole contract exists to forbid.
The ceiling that exists in practice is whatever the source itself imposes (an issue body's
practical size, GitHub's own body-size limits) — not a budget this contract enforces. An item
this large remains navigable once generated (R2 forbids dropping addressable nodes), the cost
is concentrated at first generation, not spread across every page request.

## Considered alternative

Per-operation budget constants (the pre-existing state) were considered and rejected — no
evidence found that the 4,000/4,400 split was a deliberate sizing decision rather than drift
from two people picking round numbers at different times.

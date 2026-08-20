# ADR-3075-4: The control set is out-of-process and session-keyed, not an in-process cache

**Status:** Accepted
**Date:** 2026-08-20
**Issue:** Extends [#3062](https://github.com/Jamie-BitFlight/claude_skills/issues/3062)
**Related:** Corrects an implicit assumption in [ADR-3075-1](./ADR-3075-1-content-identity-and-cache-scope.md)
and the initial R8 wording — neither specified storage locality, and both were written as
though an in-process cache would satisfy "one shared control set." It does not.

## Context

R8 requires one control set per session, shared across every tool, subcommand, and transport
that touches the same generated content. A peer review, dispatched specifically to check this
claim's feasibility against the actual codebase (not the contract's own framing), found it
false as an in-process design:

- `_backlog_lifespan` (`backlog_core/server.py`) yields an empty `{}` — there is no shared
  state today for MCP tools to hook into.
- `backlog_view` and `artifact_read` — the two tools this whole contract centers on — do not
  even accept a `ctx: Context` parameter. Only a handful of other tools do.
- The CLI runs as a separate OS process per invocation. FastMCP's lifespan context is scoped to
  one server process's lifetime; it cannot be shared with a CLI subprocess by construction, no
  matter how the MCP-side wiring is improved. "Viewed through one tool, then the CLI, still
  hits the same entry" cannot be true of an in-process cache regardless of implementation
  effort.

All three findings were verified directly against `backlog_core/server.py` before being
accepted into this ADR.

## Decision

The control set is an out-of-process, session-keyed store — not a server-held dict or MCP
lifespan context. It follows the pattern already established by
`plugins/development-harness/skills/work-backlog-item/scripts/get-gate-token.mjs`: a directory
at `$DH_STATE_HOME/sessions/{CLAUDE_CODE_SESSION_ID}/` (default `~/.dh/sessions/...`), keyed by
the `CLAUDE_CODE_SESSION_ID` environment variable already shared between an MCP-tool-calling
agent process and any CLI subprocess it spawns in the same session. This is an existing
convention this decision reuses, not a new storage mechanism invented for R8.

## Consequences

`backlog_view` and `artifact_read` need `ctx: Context` (or equivalent) added to their
signatures as a prerequisite for any implementation of #3062 — this was not previously called
out as required plumbing anywhere in this contract or its ADRs, and is now explicit.

## Considered alternative

An in-process cache (module-level dict, FastMCP lifespan context) was the implicit assumption
behind the original "one shared control set" wording and is rejected here for the reason
above: it cannot be true across the MCP/CLI process boundary regardless of implementation
quality, not merely a weaker version of the decision above.

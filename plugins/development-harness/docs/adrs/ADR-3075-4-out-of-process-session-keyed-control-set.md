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

`backlog_view` and `artifact_read` need a session-identifying value added to their signatures
as a prerequisite for any implementation of #3062. **This was originally stated as "add
`ctx: Context`" and that was wrong** — checked directly against every existing `ctx: Context`
usage in `backlog_core/server.py`: `ctx` is used exclusively for `ctx.info()`/`ctx.warning()`/
`ctx.report_progress()`, a logging and progress channel to the calling client, and carries no
session identity anywhere in this codebase. The actual established pattern for session
identity is an explicit `gate_token`-style parameter: `backlog_add` (which does take
`ctx: Context`) determines the caller's session not from `ctx` but from a `gate_token` string
(`{session_id}:{hex}`) the client generates via `get-gate-token.mjs` and passes as an ordinary
parameter — `_read_gate_token`'s own docstring states this exists specifically "so the MCP
server never needs its own `CLAUDE_CODE_SESSION_ID`." `backlog_view` and `artifact_read`
currently have neither `ctx: Context` nor a `gate_token`-style parameter. The prerequisite is
the latter, following the existing pattern — not `ctx: Context`, which would not solve this
even if added.

## Known gaps — named, not solved by this ADR

**Concurrent writers within one session.** `CLAUDE_CODE_SESSION_ID` is shared not only across
one agent's own MCP-vs-CLI calls but across every subagent this repo's `TeamCreate` and
parallel `Agent()` patterns spawn within that session — they inherit the same session ID. That
means multiple OS processes (a parallel review team all viewing or grooming the same item, for
example) can perform a concurrent read-modify-write against the same session-keyed store.
`get-gate-token.mjs` is not precedent for this: it only ever performs one atomic
`writeFileSync` of a single value, never a keyed read-modify-write, and has nothing analogous
to write-triggered invalidation (ADR-3075-2) racing a concurrent requery. This ADR does not
specify a locking scheme — that is deferred to implementation, tracked as
[#3081](https://github.com/Jamie-BitFlight/claude_skills/issues/3081) — but the concurrency
hazard is a real gap in what "session-keyed" solves, not an incidental detail.

**No stated cleanup or TTL.** Control-set entries can hold full generated documents, and
ADR-3072-1's known limitation already establishes this is not a hypothetical size — item #2953
alone generates an estimated 270,946+ tokens. Without a cleanup mechanism for
`$DH_STATE_HOME/sessions/{id}/` directories after a session ends, entries accumulate on disk
unboundedly across every session ever run. `get-gate-token.mjs`'s single small token file never
faced this problem; a control-set store holding full generated documents does. Not solved here
— tracked as [#3082](https://github.com/Jamie-BitFlight/claude_skills/issues/3082) so it is not
silently absent from the design.

## Considered alternative

An in-process cache (module-level dict, FastMCP lifespan context) was the implicit assumption
behind the original "one shared control set" wording and is rejected here for the reason
above: it cannot be true across the MCP/CLI process boundary regardless of implementation
quality, not merely a weaker version of the decision above.

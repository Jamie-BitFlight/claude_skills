# ADR-3075-4: The control set is out-of-process and session-keyed, not an in-process cache

**Status:** Accepted
**Date:** 2026-08-20
**Issue:** Extends [#3062](https://github.com/Jamie-BitFlight/claude_skills/issues/3062)
**Related:** Corrects an implicit assumption in [ADR-3075-1](./ADR-3075-1-content-identity-and-cache-scope.md)
and the initial R8 wording — neither specified storage locality, and both were written as
though an in-process cache would satisfy "one shared control set." It does not.
**Superseded by:** [ADR-3082-1](./ADR-3082-1-sqlite-backed-bounded-eviction.md), on two points.
First: the storage mechanism below (a directory of files) is replaced by a single SQLite
database. Second, in a later revision of that same ADR: **the session-keyed decision itself is
reversed** — the control set is content-keyed only, no `session_id` anywhere. Only the
out-of-process decision below (not in-process, not a server-held dict) is still current. The
"Decision" and "Consequences" sections below are kept for history; read ADR-3082-1's "Reversal:
content-keyed, not session-keyed" section for what's actually current.

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
session identity anywhere in this codebase.

**A second correction, found the same way: reusing the `gate_token` pattern was also wrong.**
`backlog_add` does determine the caller's session from a client-supplied parameter rather than
`ctx`, but that parameter is not a stable session identifier and does not solve this. Checked
directly against `get-gate-token.mjs` and `_read_gate_token()` in `backlog_core/server.py`:
`get-gate-token.mjs` generates a *new* random token and overwrites the single
`.gate-token` file on every invocation; `_read_gate_token()` validates a caller's token against
only the file's *current* contents. A token obtained by an earlier call in a session becomes
invalid the moment anything else in that session reloads the skill and regenerates the file —
including a paginated request's own later follow-up call. `gate_token`'s actual purpose (per its
own docstring and the error message `backlog_add` returns on mismatch) is gating unauthorized
direct tool calls, forcing skill-mediated access to `create`'s duplicate-detection step — not
carrying session identity for cache routing. Those are different requirements and the same
mechanism cannot serve both: cache routing needs a value stable for the session's whole
lifetime; the gate needs a value that becomes invalid, since its entire point is to reject a
caller that bypassed the skill.

The correct prerequisite is a plain, non-rotating `session_id` parameter carrying the caller's
`CLAUDE_CODE_SESSION_ID` value directly — following the same reasoning `gate_token`'s docstring
gives for why the client must pass it explicitly (the MCP server has no way to read the caller's
own environment), without adopting `gate_token`'s rotation or its access-gating property, neither
of which cache routing needs. `backlog_view` and `artifact_read` currently have neither
`ctx: Context` nor any session-identifying parameter. Whether `gate_token` itself should be
reviewed or replaced as an access-gating mechanism is a separate question, raised by the repo
owner and tracked as [#3087](https://github.com/Jamie-BitFlight/claude_skills/issues/3087) — out
of scope for this ADR, which only concerns cache routing.

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
[ADR-3082-1](./ADR-3082-1-sqlite-backed-bounded-eviction.md)'s move to a single SQLite database
partially mitigates this (WAL mode makes individual statements atomic across concurrent OS
processes) but does not solve it — the full check-cap/evict/insert sequence still needs an
explicit transaction, which #3081 remains open to specify.

**No stated cleanup or TTL.** Resolved by
[ADR-3082-1](./ADR-3082-1-sqlite-backed-bounded-eviction.md) — bounded per-session LRU eviction
plus an opportunistic cross-session age-based sweep, replacing the directory-of-files storage
this ADR originally specified. Tracked as
[#3082](https://github.com/Jamie-BitFlight/claude_skills/issues/3082) for implementation.

**Not harness-neutral.** Named against this ADR's original session-keyed design. Moot for the
control set specifically now that ADR-3082-1 reversed session-keying — a content-keyed store
needs no session-identifying value from any harness, so there is nothing left for this gap to
apply to on that path. Tracked as
[#3085](https://github.com/Jamie-BitFlight/claude_skills/issues/3085), flagged there for the repo
owner to close or repurpose — `CLAUDE_CODE_SESSION_ID` may still matter to something else in this
codebase (e.g. `gate_token`, tracked separately in #3087) independent of the control set.

## Considered alternative

An in-process cache (module-level dict, FastMCP lifespan context) was the implicit assumption
behind the original "one shared control set" wording and is rejected here for the reason
above: it cannot be true across the MCP/CLI process boundary regardless of implementation
quality, not merely a weaker version of the decision above.

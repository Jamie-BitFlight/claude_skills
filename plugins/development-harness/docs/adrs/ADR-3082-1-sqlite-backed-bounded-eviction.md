# ADR-3082-1: The control set is one SQLite database with bounded, session-scoped LRU eviction

**Status:** Accepted
**Date:** 2026-08-20
**Issue:** [#3082](https://github.com/Jamie-BitFlight/claude_skills/issues/3082), partially
mitigates [#3081](https://github.com/Jamie-BitFlight/claude_skills/issues/3081)
**Related:** Supersedes the storage-mechanism detail of
[ADR-3075-4](./ADR-3075-4-out-of-process-session-keyed-control-set.md) — "a directory at
`$DH_STATE_HOME/sessions/{CLAUDE_CODE_SESSION_ID}/`" — while keeping that ADR's higher-level
decision (out-of-process, session-keyed, not in-process) unchanged. Confirmed by the repo owner.

## Context

ADR-3075-4 named two gaps it did not solve: no cleanup/TTL for session directories (#3082) and
no locking scheme for concurrent writers sharing one session ID (#3081). Both trace back to the
same root cause: a directory of loose files, one per session, has no way to bound its own growth
or age itself out safely, and a hand-rolled multi-file read-modify-write has no atomicity
guarantee against a concurrent writer.

A second, previously unstated constraint sharpens the requirement: the CLI is not a running
service. Unlike the MCP server, which holds process lifetime across many tool calls, the CLI is a
fresh OS process per invocation with no memory of any prior call. It cannot hold state itself
between invocations under any design — external storage is required regardless of session
identity, purely because the CLI has nothing else to remember with.

## Decision

**One SQLite database**, not a directory of files, at a fixed path
(`$DH_STATE_HOME/control-set.db`), WAL mode — consistent with this repo's existing `sqlite`
backend convention (`docs/backend-providers.md`). Rows are keyed by `(session_id, content_id)`,
where `content_id` is the command+content-bound identity from ADR-3075-1. Each row stores the
generated content, its hash, the canonicalized generating command, `created_at`, and
`last_accessed_at`.

**Bounded per-session eviction:** each `session_id` may hold at most N entries (default 10,
tunable). On insert past the cap, the least-recently-accessed entry for that session is deleted
first. Confirmed by the repo owner: an agent-level keying granularity (one stack per subagent,
not per session) was considered and rejected — there is no identifier that reliably survives a
subagent spawning its own CLI subprocess, so session remains the practical and only reliably
propagatable key.

**Age-based cross-session sweep:** on every write (from any session), rows whose
`last_accessed_at` is older than a configurable TTL (default 24h) are deleted, regardless of
which session they belong to. This satisfies #3082's second acceptance criterion directly — the
sweep runs opportunistically on the next write from *any* session, so it does not depend on the
originating session exiting cleanly. A crashed or killed session's rows still age out the next
time anything touches the database.

**Eviction is not an error.** When an agent references a `content_id` that has since been
evicted (by cap or by TTL), the response states plainly that the content is no longer cached and
must be requested again — not a generic error, not a silent empty result.

## Consequences

- `#3082`'s two acceptance criteria are both satisfied: entries never accumulate unboundedly
  (bounded per-session cap), and cleanup does not depend on clean exit (opportunistic TTL sweep).
- `#3081`'s concurrent-writer hazard is partially mitigated, not solved: SQLite's WAL mode makes
  each individual statement atomic and safe under concurrent access from multiple OS processes,
  which a hand-rolled multi-file read-modify-write was not. It does **not** by itself make the
  full "check cap, evict, insert" sequence atomic across concurrent writers — that still requires
  wrapping the sequence in an explicit transaction, which is an implementation detail deferred to
  #3081, not decided here.
- Implementation must add a session-keyed table to `$DH_STATE_HOME`, distinct from any per-plugin
  provider database (e.g. the `sqlite` backend's 6-table schema) — this is Navigation-layer
  cache state, not work-item state, and must not be added to that schema.

## Considered alternatives

**One file per session, bounded by count** (keep ADR-3075-4's directory shape, just cap and
LRU-evict files within it): rejected — solves #3082's growth bound within an active session but
not its cross-session accumulation requirement (many capped-but-permanent session directories
still accumulate forever without an age-based sweep, and a directory of files has no efficient
way to run that sweep without listing and stat-ing every session directory on every write).

**Cleanup-on-session-exit hook**: rejected — #3082 explicitly requires cleanup not to depend on
clean exit (crashes, kills, abrupt termination). A hook is not a substitute for opportunistic
sweep-on-write.

**Per-subagent keying** (finer than per-session): rejected — no identifier reliably propagates
from an agent process to a CLI subprocess it spawns, other than the session ID already
established by ADR-3075-4. Adopting this would also silently break the R8 guarantee that a
subagent's own CLI calls resolve against the same control set as its MCP calls.

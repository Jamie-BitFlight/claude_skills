# ADR-3082-1: The control set is one SQLite database with bounded, session-scoped LRU eviction

**Status:** Accepted
**Date:** 2026-08-20
**Issue:** [#3082](https://github.com/Jamie-BitFlight/claude_skills/issues/3082), partially
mitigates [#3081](https://github.com/Jamie-BitFlight/claude_skills/issues/3081)
**Related:** Supersedes the storage-mechanism detail of
[ADR-3075-4](./ADR-3075-4-out-of-process-session-keyed-control-set.md) — "a directory at
`$DH_STATE_HOME/sessions/{CLAUDE_CODE_SESSION_ID}/`" — while keeping that ADR's higher-level
decision (out-of-process, session-keyed, not in-process) unchanged. Reviewed independently after
first being written — see "Independent review" below for what that pass changed.

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

**Confirmed by the repo owner: this database holds no authoritative data.** Every row is a
disposable, regenerable cache — Collection and Generation can rebuild any entry from source on
demand. Losing the entire database (corruption, deletion, disk issue, a bad migration) causes no
data loss, only a cold cache: the next request simply regenerates and repopulates it. This
governs the rest of this ADR — no backup, no migration path, and no corruption-recovery
procedure are needed beyond "delete the file and let it recreate itself." It's also why the
cross-session write-contention trade-off below is acceptable at low stakes: contention costs
latency, never correctness or data loss.

## Decision

**One SQLite database**, not a directory of files, at a fixed path
(`$DH_STATE_HOME/control-set.db`), WAL mode — consistent with this repo's existing `sqlite`
backend convention (`docs/backend-providers.md`) for the choice of engine; that backend's own
docs do not analyze WAL/writer-serialization behavior, so it is precedent for "SQLite is an
established storage choice here," not for the contention trade-off named below. Rows are keyed
by `(session_id, content_id)`, where `content_id` is the command+content-bound identity from
ADR-3075-1. Each row stores the generated content, its hash, the canonicalized generating
command, the request's `source` (see schema note below), `created_at`, and `last_accessed_at`.

**Bounded per-session eviction, by size not count.** Confirmed by the repo owner: each
`session_id` may hold at most **40MB** of total content (tunable), not a fixed entry count. On a
write that would push a session over that budget, entries for that session are evicted
least-recently-accessed first (**LRU, confirmed by the repo owner**) until the write fits.
Reading an entry updates its `last_accessed_at` — see "Known tradeoff" below for what this costs.

Confirmed by the repo owner: an agent-level keying granularity (one store per subagent, not per
session) was considered and rejected — there is no identifier that reliably survives a subagent
spawning its own CLI subprocess, so session remains the practical and only reliably propagatable
key.

**Age-based cross-session sweep:** on every write (from any session), rows whose
`last_accessed_at` is older than a TTL are deleted, regardless of which session they belong to.
**The TTL value (currently 24h) is an unsourced starting default, not a confirmed decision** —
tunable, and should be revisited once real usage data exists, not treated as settled. The sweep
mechanism itself satisfies #3082's second acceptance criterion directly: it runs opportunistically
on the next write from *any* session, so cleanup does not depend on the originating session
exiting cleanly. A crashed or killed session's rows still age out the next time anything touches
the database.

**Eviction is not an error.** When an agent references a `content_id` that has since been
evicted (by the size budget or by TTL), the response states plainly that the content is no
longer cached and must be requested again — not a generic error, not a silent empty result.

**Schema must include a `source` column and an index on it.** ADR-3075-2 requires "an index from
source to the entries generated from it, so a write can find what to invalidate without scanning
every entry." The schema in this ADR's first draft omitted this — `source` was only recoverable
by parsing the stored canonicalized command per row, exactly the full-table scan ADR-3075-2 said
to avoid. Corrected: `source` is its own column, indexed, populated at write time alongside the
canonicalized command it's extracted from.

## Known tradeoff — cross-session write contention (confirmed accepted, not silently assumed)

Moving from one file per session to one global database trades reduced write contention *within*
a session for new write contention *across every session running on the machine*: SQLite WAL
mode allows concurrent readers alongside one writer, but writers still serialize against each
other process-wide, not just against other writers in the same session. Because LRU eviction
requires bumping `last_accessed_at` on every read, a content read through this design is also a
write transaction — multiplying how often that single-writer lock gets contended, beyond just
inserts, evictions, and sweeps.

**Confirmed by the repo owner: accepted as-is**, given writes are still occasional relative to
what a single global lock can serialize (new content, eviction, and LRU-triggered reads — not a
high-frequency path), against one SQLite file per session (which would restore write isolation
but turn the cross-session TTL sweep into an open-and-check-every-file operation instead of one
query, losing the reason SQLite was chosen). Revisit if contention is ever measured to matter in
practice.

## Consequences

- `#3082`'s two acceptance criteria are both satisfied: entries never accumulate unboundedly
  (bounded per-session size budget), and cleanup does not depend on clean exit (opportunistic TTL
  sweep).
- `#3081`'s concurrent-writer hazard is partially mitigated, not solved: SQLite's WAL mode makes
  each individual statement atomic and safe under concurrent access from multiple OS processes,
  which a hand-rolled multi-file read-modify-write was not. It does **not** by itself make the
  full "check budget, evict, insert" sequence atomic across concurrent writers — that still
  requires wrapping the sequence in an explicit transaction, which is an implementation detail
  deferred to #3081, not decided here. The same open question applies to a read racing a
  concurrent sweep (a check-then-consume sequence spanning two statements, with an eviction
  landing in between) — not a new hazard, the same class already deferred to #3081, just also
  present on the read side once LRU makes reads into writes.
- Implementation must add a session-keyed table to `$DH_STATE_HOME`, distinct from any per-plugin
  provider database (e.g. the `sqlite` backend's 6-table schema) — this is Navigation-layer
  cache state, not work-item state, and must not be added to that schema.

## Independent review

This ADR was reviewed by an independent agent with no involvement in writing it, specifically to
avoid the author checking its own work. It found the cross-session write-contention trade-off
above unnamed, the eviction order (LRU) and defaults (cap, TTL) asserted without attributed
confirmation, and the `source` index requirement from ADR-3075-2 silently dropped. All four are
addressed above. Everything else it checked — `content_id`'s definition against ADR-3075-1, both
of #3082's acceptance criteria, the "partially mitigates #3081" framing, and consistency with
`CONTEXT.md`/the contract doc — held up as sound and is unchanged.

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

**One SQLite file per session** (restores write isolation between sessions): rejected in favor
of one global database — see "Known tradeoff" above. The isolation this would restore was judged
not worth losing the single-query cross-session TTL sweep that motivated the move to SQLite.

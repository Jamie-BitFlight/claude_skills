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
ADR-3075-1. Each row stores the generated content (raw, not a parsed tree — see "Re-parsing on
follow-up pages" below), its hash, the canonicalized generating command, the request's `source`
(see schema note below), `created_at`, and `last_accessed_at`.

**`session_id` stays in the key, confirmed by the repo owner.** Without it, `content_id` alone
would let two different sessions running the identical command against identical content share
one row — mechanically fine, but it reverses an earlier, explicit requirement: "I don't want the
cache values to be shared between agents or sessions." `session_id` in the key is what enforces
that isolation, and is also what makes the per-session size target and per-session LRU ordering
meaningful — without it, both would have to become global, and one agent's unrelated work could
evict another's.

**Re-parsing on follow-up pages is allowed, confirmed by the repo owner — this clarifies R8, not
this ADR's schema.** The contract's R8 states a later page "does not re-parse." Taken literally,
that's incompatible with storing only raw content: a follow-up landing on a fresh CLI process (no
in-memory parsed tree survives across processes, per this ADR's own Context) would have nothing
to slice without reparsing the stored raw markdown. Resolved by clarifying what R8's "does not
re-parse" actually protects against: a repeated network round-trip to re-run Collection, and
re-running Generation — not the cheap, deterministic, in-memory step of turning already-fetched
raw markdown back into an addressable structure. That reading is consistent with ADR-3075-1's own
"re-parsing is cheap" premise, which only makes sense if reparsing already-stored content is
expected to happen routinely. The schema therefore stores raw generated content only, not a
parsed tree — see `docs/agent-markdown-consumption-contract.md`'s R8 section for the corrected
wording.

**Bounded per-session storage, by size not count — a soft target, not a hard per-write limit.**
Confirmed by the repo owner: each `session_id` targets at most **40MB** of total content
(tunable). This is not enforced synchronously on every write — its only purpose is that stored
content doesn't grow continuously and unboundedly, not to guarantee the budget is never exceeded
at any instant. Trimming happens during periodic cleanup (below), not inline on the write path.

**Periodic cleanup, not per-write eviction — confirmed by the repo owner.** A single maintenance
pass does both jobs together: (1) delete rows whose `last_accessed_at` is older than a TTL,
regardless of session, and (2) for any session over its 40MB target, delete
least-recently-accessed rows for that session down to target (**LRU, confirmed by the repo
owner**). This pass runs on a rate-limited cadence — **hourly to daily, confirmed by the repo
owner as the target frequency; the exact value is an unsourced starting default, not a confirmed
number, and should be revisited under real usage** — not synchronously on every write or every
query. Mechanically: a single stored `last_cleanup_at` timestamp is checked cheaply (one row
read) on write; the maintenance pass itself (the expensive scan-and-delete work) only executes
when enough time has elapsed since the last run, otherwise the check is a no-op. This is what
`#3082`'s second acceptance criterion (cleanup not dependent on clean exit) is actually satisfied
by: the check runs opportunistically off of any session's write, so a crashed or killed session's
rows still get swept the next time anything touches the database and the cadence has elapsed —
just not synchronously with that session's own activity.

**The goal, confirmed by the repo owner: avoid evicting an entry an agent is actively navigating
within.** LRU achieves this structurally, not just incidentally: reading an entry (any page or
address request against it) updates its `last_accessed_at` — a cheap, single-row write, separate
from the periodic cleanup pass — so an entry under active navigation is by construction the
most-recently-touched one in its session and is always trimmed last whenever cleanup does run.
This is a best-effort property, not a guarantee — a paused multi-page read (fetch page 1, long
gap, fetch page 2) can still lose to a cleanup pass landing during the gap. Confirmed by the repo
owner: that residual case is acceptable — the "eviction is not an error" fallback below means the
agent just re-queries, which is a nice-to-avoid cost, not a correctness problem.

Confirmed by the repo owner: an agent-level keying granularity (one store per subagent, not per
session) was considered and rejected — there is no identifier that reliably survives a subagent
spawning its own CLI subprocess, so session remains the practical and only reliably propagatable
key.

**A single entry larger than the 40MB target is kept anyway, confirmed by the repo owner.**
Collection and Generation are explicitly unbounded, so a single generated document can itself
exceed the per-session target — trimming every other entry in that session still can't make it
fit. Rather than reject the write or serve that document uncached (which would silently exempt
the largest, most expensive-to-generate documents from R8's identity/staleness guarantees — the
ones that benefit from caching the most), the write is allowed through as a documented exception:
a session's effective budget is "40MB, or one entry's actual size if larger." The next cleanup
pass still trims everything else in that session normally.

**Eviction is not an error.** When an agent references a `content_id` that has since been
evicted (by cleanup's size trim or TTL sweep), the response states plainly that the content is no
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
other process-wide, not just against other writers in the same session. Because LRU tracking
requires bumping `last_accessed_at` on every read, a content read through this design is also a
write transaction.

**Substantially smaller than originally assessed, now that eviction is a periodic pass rather
than inline on every write.** The expensive part — scanning a session's rows and deleting down to
target — no longer runs per-write; it runs at most hourly-to-daily, rate-limited by the stored
`last_cleanup_at` check. What remains on the write/read path is just the cheap parts: an insert
of new content, and a single-row `last_accessed_at` update on read. **Confirmed by the repo
owner: accepted as-is** at this reduced scope, against one SQLite file per session (which would
restore write isolation but turn the periodic cross-session sweep into an open-and-check-every-
file operation instead of one query, losing the reason SQLite was chosen). Revisit if contention
is ever measured to matter in practice.

## Consequences

- `#3082`'s two acceptance criteria are both satisfied: entries never accumulate unboundedly (the
  40MB-per-session soft target, trimmed by periodic cleanup), and cleanup does not depend on clean
  exit (the rate-limited cleanup check runs opportunistically off of any session's write).
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

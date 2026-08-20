# ADR-3082-1: The control set is one SQLite database, content-keyed, with periodic global eviction

**Status:** Accepted
**Date:** 2026-08-20
**Issue:** [#3082](https://github.com/Jamie-BitFlight/claude_skills/issues/3082), partially
mitigates [#3081](https://github.com/Jamie-BitFlight/claude_skills/issues/3081)
**Related:** Supersedes [ADR-3075-4](./ADR-3075-4-out-of-process-session-keyed-control-set.md)
on two points, not one: the storage mechanism (a directory of files → one SQLite database, as
first decided here) **and, in a later revision of this same ADR, the session-keying decision
itself** (see "Reversal: content-keyed, not session-keyed" below). ADR-3075-4's remaining
decision — out-of-process, not an in-process cache — is unchanged. Reviewed independently after
first being written — see "Independent review" for what that pass changed, before the
session-keying reversal below.

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
procedure are needed beyond "delete the file and let it recreate itself."

## Reversal: content-keyed, not session-keyed

This ADR originally kept `session_id` as part of the primary key, reasoning that the repo
owner's earlier statement — "I don't want the cache values to be shared between agents or
sessions" — was a standing isolation requirement. **Corrected, confirmed by the repo owner:**
that statement was a reaction to a specific proposal being presented as a default, not a general
principle requiring `session_id` to be threaded through the design. Adding `session_id` means
obtaining a value that is genuinely hard to get reliably — it requires a Claude-Code-specific
hook (`session-start-session-id.cjs`) with no equivalent under other harnesses this repo's
content targets (Codex, OpenCode, GitHub's coding agent — see #3085), and, even within Claude
Code, means adding a parameter to `backlog_view`/`artifact_read` that doesn't exist today. Paying
that cost to create what turns out to be an arbitrary boundary between sessions is not justified.

**The key is `content_id` alone** — the command+content-bound identity from ADR-3075-1. No
`session_id`, anywhere: not in the schema, not as an MCP tool parameter, not read from the CLI's
environment for this purpose. Two different sessions running the identical command against
identical content resolve to the same row on write. **This avoids duplicate storage, not
duplicate work** — every full request still runs Collection and Generation unconditionally (see
"Every source hit always writes a fresh document" below); `content_id` isn't even knowable until
that work has already happened, since it's a hash of the *generated* output, so there is nothing
to check in advance that would let a repeat request skip the fetch. The benefit of dropping
`session_id` from the key is narrower than originally claimed here: two callers producing
identical content upsert the same row instead of each holding their own permanent duplicate, so
storage doesn't grow with caller count — it says nothing about compute cost. `backlog_view` and
`artifact_read` need **no** session-identifying parameter added to their signatures for
control-set purposes — the entire prerequisite ADR-3075-4 stated in its Consequences section
(adding a `gate_token`-style or `session_id`-style parameter) is void for this reason, not merely
revised.

**Every source hit always writes a fresh document, confirmed by the repo owner.** "Backend call"
is two different things and this ADR must not conflate them: a call to the navigation system
(the MCP tool or CLI — every request, page 1 or page 2, is one of these) versus Collection and
Generation actually reaching the original *source* (GitHub, etc.). The control set is not a
durable reuse-optimization cache — it is temporary scratch space for one navigation task: an
agent pages and jumps around in a document it just fetched, and the external store exists only
because the CLI can't hold that document in memory between its own invocations (see Context
above). A request that reaches the source — an ordinary initial request, revalidation, or a
forced refresh (ADR-3075-3) — always regenerates and always writes; nothing skips the write to
avoid "redundant" recomputation, because reuse across separate top-level requests was never the
design's point. A follow-up page request against a document an agent is *already* navigating
(R8) is still a call to the navigation system — the caller still invokes a tool — but it does not
reach the source: it reads the row this task already wrote. **This is a genuine, deliberate
caching effect, confirmed by the repo owner — a side effect of solving the CLI-not-a-service
problem, not the reason the control set exists.** It's scoped to one navigation task's own
follow-up calls, not to avoiding Collection and Generation across separate top-level requests.

## Decision

**One SQLite database**, not a directory of files, at a fixed path
(`$DH_STATE_HOME/control-set.db`), WAL mode — consistent with this repo's existing `sqlite`
backend convention (`docs/backend-providers.md`) for the choice of engine; that backend's own
docs do not analyze WAL/writer-serialization behavior, so it is precedent for "SQLite is an
established storage choice here," not for the contention trade-off named below. Rows are keyed
by `content_id` alone. Each row stores the generated content (raw, not a parsed tree — see
"Re-parsing on follow-up pages" below), its hash, the canonicalized generating command, the
request's `source` (see schema note below), a `stale` marker (see schema note below), `created_at`,
and `last_accessed_at`.

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

**Bounded global storage, by size not count — a soft target, not a hard per-write limit.**
Confirmed by the repo owner: the whole database targets at most **40MB** of total content
(tunable) — global now that there is no session dimension to partition it by. This is not
enforced synchronously on every write — its only purpose is that stored content doesn't grow
continuously and unboundedly, not to guarantee the budget is never exceeded at any instant.
Trimming happens during periodic cleanup (below), not inline on the write path.

**Periodic cleanup, not per-write eviction — confirmed by the repo owner.** A single maintenance
pass does both jobs together: (1) delete rows whose `last_accessed_at` is older than a TTL, and
(2) if the database is over its 40MB target, delete least-recently-accessed rows down to target
(**LRU, confirmed by the repo owner**). This pass runs on a rate-limited cadence — **hourly to
daily, confirmed by the repo owner as the target frequency; the exact value is an unsourced
starting default, not a confirmed number, and should be revisited under real usage** — not
synchronously on every write or every query. Mechanically: a single stored `last_cleanup_at`
timestamp is checked cheaply (one row read) on write; the maintenance pass itself (the expensive
scan-and-delete work) only executes when enough time has elapsed since the last run, otherwise
the check is a no-op. This is what `#3082`'s second acceptance criterion (cleanup not dependent
on clean exit) is actually satisfied by: the check runs opportunistically off of any write from
any caller, so a crashed or killed process's rows still get swept the next time anything touches
the database and the cadence has elapsed — just not synchronously with that caller's own
activity.

**The goal, confirmed by the repo owner: avoid evicting an entry an agent is actively navigating
within.** LRU achieves this structurally, not just incidentally: reading an entry (any page or
address request against it) updates its `last_accessed_at` — a cheap, single-row write, separate
from the periodic cleanup pass — so an entry under active navigation is by construction the
most-recently-touched one and is always trimmed last whenever cleanup does run. This is a
best-effort property, not a guarantee — a paused multi-page read (fetch page 1, long gap, fetch
page 2) can still lose to a cleanup pass landing during the gap. Confirmed by the repo owner:
that residual case is acceptable — the "eviction is not an error" fallback below means the agent
just re-queries, which is a nice-to-avoid cost, not a correctness problem.

**A single entry larger than the 40MB target is kept anyway, confirmed by the repo owner.**
Collection and Generation are explicitly unbounded, so a single generated document can itself
exceed the target — trimming every other entry still can't make it fit. Rather than reject the
write or serve that document uncached (which would silently exempt the largest, most
expensive-to-generate documents from R8's identity/staleness guarantees — the ones that benefit
from caching the most), the write is allowed through as a documented exception: the effective
budget is "40MB, or one entry's actual size if larger." The next cleanup pass still trims
everything else normally.

**Eviction is not an error.** When an agent references a `content_id` that has since been
evicted (by cleanup's size trim or TTL sweep), the response states plainly that the content is no
longer cached and must be requested again — not a generic error, not a silent empty result.

**Schema must include a `source` column and an index on it.** ADR-3075-2 requires "an index from
source to the entries generated from it, so a write can find what to invalidate without scanning
every entry." The schema in this ADR's first draft omitted this — `source` was only recoverable
by parsing the stored canonicalized command per row, exactly the full-table scan ADR-3075-2 said
to avoid. Corrected: `source` is its own column, indexed, populated at write time alongside the
canonicalized command it's extracted from.

**Schema must include a `stale` marker, not rely on deletion for invalidation.** ADR-3075-2's
write-triggered invalidation must mark an entry stale without destroying its stored command —
deleting the row on invalidation would remove the only thing a subsequent stale-identifier
request can use to auto-regenerate (the request carries only the old `content_id`, not the
original scope, per R8). Corrected: invalidation sets a `stale` boolean on the row rather than
deleting it. A stale-identifier read finds the row, sees `stale=true`, re-runs its stored command
to regenerate under a new identity, and only then does the old row get replaced — not before.

**The 40MB target counts complete row storage, not raw content bytes alone.** As originally
written, the budget summed only the `content` column, which undercounts real storage: every row
also carries its canonicalized command, `source`, timestamps, and the `stale` marker, plus
whatever indexes cover them. A workload of many small or empty generated documents could add
rows without ever moving the "content" total, growing the database unboundedly while never
tripping eviction — the opposite of what a bounded-storage design is for. Corrected: the budget
is measured against total row storage (every column, not content alone), so row count itself is
implicitly bounded even when individual documents are tiny.

## Known tradeoff — global write contention (confirmed accepted, not silently assumed)

One SQLite database means every write on the machine — from every session, every agent —
serializes against every other write: SQLite WAL mode allows concurrent readers alongside one
writer, but writers still serialize process-wide. Because LRU tracking requires bumping
`last_accessed_at` on every read, a content read through this design is also a write transaction.

**Substantially smaller than it would otherwise be, for two independent reasons.** First,
eviction is a periodic pass rather than inline on every write — the expensive part (scanning and
deleting down to target) runs at most hourly-to-daily, rate-limited by the stored
`last_cleanup_at` check, not per-write. What remains on the write/read path is just the cheap
parts: an insert of new content, and a single-row `last_accessed_at` update on read. Second,
every source hit always writes regardless of key design (see "Every source hit always writes a
fresh document" above), so dropping `session_id` from the key does not reduce write *count* —
identical requests from different callers still each write. What it reduces is storage: those
writes upsert one shared row instead of each caller permanently holding its own duplicate, so the
database doesn't grow with caller count for identical content. **Confirmed by the repo owner:
accepted as-is** at this reduced scope. Revisit if contention is ever measured to matter in
practice.

## Consequences

- `#3082`'s two acceptance criteria are both satisfied: entries never accumulate unboundedly (the
  40MB global soft target, trimmed by periodic cleanup), and cleanup does not depend on clean
  exit (the rate-limited cleanup check runs opportunistically off of any write).
- `#3081`'s concurrent-writer hazard is partially mitigated, not solved: SQLite's WAL mode makes
  each individual statement atomic and safe under concurrent access from multiple OS processes,
  which a hand-rolled multi-file read-modify-write was not. It does **not** by itself make the
  full "check budget, evict, insert" sequence atomic across concurrent writers — that still
  requires wrapping the sequence in an explicit transaction, which is an implementation detail
  deferred to #3081, not decided here. The same open question applies to a read racing a
  concurrent sweep (a check-then-consume sequence spanning two statements, with an eviction
  landing in between) — not a new hazard, the same class already deferred to #3081, just also
  present on the read side once LRU makes reads into writes.
- Implementation must add a table to `$DH_STATE_HOME`, distinct from any per-plugin provider
  database (e.g. the `sqlite` backend's 6-table schema) — this is Navigation-layer cache state,
  not work-item state, and must not be added to that schema.
- [#3085](https://github.com/Jamie-BitFlight/claude_skills/issues/3085) ("harness-neutral
  session-ID resolver for the session-keyed control set") was filed against this ADR's earlier,
  session-keyed revision. Its premise no longer applies to the control set specifically — flagged
  for the repo owner to close or repurpose, not closed here, since `session_id` may still matter
  to something else in the codebase independent of this ADR.

## Independent review

This ADR was reviewed by an independent agent with no involvement in writing it, specifically to
avoid the author checking its own work, **before the session-keying reversal above**. It found
the write-contention trade-off unnamed, the eviction order (LRU) and defaults (cap, TTL) asserted
without attributed confirmation, and the `source` index requirement from ADR-3075-2 silently
dropped. All four were addressed in the revision that review produced. Everything else it
checked — `content_id`'s definition against ADR-3075-1, both of #3082's acceptance criteria, the
"partially mitigates #3081" framing, and consistency with `CONTEXT.md`/the contract doc — held up
as sound at the time. The session-keying reversal happened in a later round, directed by the repo
owner, after that review; it has not had an independent pass of its own.

## Considered alternatives

**Session-keyed control set** (this ADR's own original decision, and ADR-3075-4's): superseded —
see "Reversal" above. Not rejected for being unworkable; rejected because the isolation it bought
was never actually required, and the cost of obtaining `session_id` reliably (a
Claude-Code-specific mechanism, per #3085) wasn't worth paying for a boundary nobody needed.

**One file per session, bounded by count** (keep ADR-3075-4's directory shape, just cap and
LRU-evict files within it): rejected even before the session-keying reversal — solves #3082's
growth bound within an active session but not its cross-session accumulation requirement (many
capped-but-permanent session directories still accumulate forever without an age-based sweep, and
a directory of files has no efficient way to run that sweep without listing and stat-ing every
session directory on every write). Moot now that there is no per-session storage unit at all.

**Cleanup-on-session-exit hook**: rejected — #3082 explicitly requires cleanup not to depend on
clean exit (crashes, kills, abrupt termination). A hook is not a substitute for opportunistic,
rate-limited sweep-on-write.

**Per-subagent keying** (finer than per-session): considered and rejected before the session-
keying reversal, for the same underlying reason the reversal itself later applied at the session
level — no identifier reliably propagates from an agent process to a CLI subprocess it spawns.
Moot now that there is no session or subagent dimension in the key at all.

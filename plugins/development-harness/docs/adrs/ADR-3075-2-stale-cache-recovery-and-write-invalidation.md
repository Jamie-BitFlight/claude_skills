# ADR-3075-2: Stale control-set entries requery instead of erroring; writes invalidate

**Status:** Accepted
**Date:** 2026-08-20
**Issue:** New issue filed alongside this ADR (see cross-references below)
**Related:** Extends [ADR-3075-1](./ADR-3075-1-content-identity-and-cache-scope.md) — does not
reverse it. This ADR adds behavior for what happens when content changes underneath a cache
entry. **The "same session only" scoping in the Decision below is superseded by
[ADR-3082-1](./ADR-3082-1-sqlite-backed-bounded-eviction.md)'s content-keyed reversal** — there
is no per-session control-set partition to scope invalidation to any more; it now applies
globally, to whichever caller made the write. The "Decision" section is kept for the recovery
mechanism, which is unchanged; its session-scoping language is historical.

## Context

ADR-3075-1 settled R8's cache lifetime and identity derivation, but left staleness handling at
"reported as stale" — a passive, read-time check with no recovery path and no connection to
the write side of the system. The repo owner clarified two gaps while reviewing that behavior:
a stale entry should be recoverable rather than a dead end, and staleness should not depend on
a read happening to notice a hash mismatch — a write to the underlying content should
invalidate the cache entry directly.

## Decision

**Recoverable staleness.** Each control-set entry stores the command that produced it — the
source, scope, and parameters Collection and Generation used — alongside its content identity.
On a stale-identifier request, that stored command re-runs Collection and Generation, producing
a new identity. Page boundaries and ordinal addresses can shift when the underlying source
changes, so recovery does not re-apply the request's original page or `navigate` selector to
the regenerated document — that would risk skipping or duplicating content, or resolving an
address to a different node than the caller intended. Recovery instead serves page 1 of the
regenerated document under the new identity (or, when a `navigate` ordinal no longer resolves,
an explicit restart response pointing the caller back to the table of contents), informing the
caller the identity changed — rather than erroring and requiring the caller to reconstruct its
original request from scratch. This is what keeps R8's no-mixed-versions guarantee: pages are
never served by applying an old request's addressing to a new document's structure.

**Write-triggered invalidation, global — superseded scoping, corrected here.** Every write path
that can modify a source this contract reads from — item updates, section writes, artifact
registration, task and plan state changes — marks stale any control-set entry that was generated
from what it touched, as a side effect of the write, regardless of which session or caller made
either the write or the original cached request. This is a direct consequence of ADR-3082-1's
content-keyed reversal: there is one shared entry per `content_id`, not one per session, so there
is nothing left to scope invalidation *to* — a write from any caller invalidates the one entry
everyone shares. **This is staleness detection's only mechanism, not one of two.** An earlier
draft of this ADR described the write-triggered mark as running alongside a separate read-time
hash-mismatch check; R8's later text corrects that framing and this ADR follows it: detection
never happens by a read re-collecting content to compare hashes — that would mean an ordinary
read reaching the source, which contradicts the control set's whole purpose (ADR-3082-1's
"every source hit always writes a fresh document" describes recollection as something a request
*does*, at a cost, not a passive background check every read performs for free). What a read
does on a cache hit is check the row's already-set `stale` marker (below) — cheap, no
recollection — and that marker is set by this write path, not derived independently by the read.
The "concurrent-session blind spot"
this ADR's earlier revision named (a write from a different session not being visible to
invalidation) is resolved as a side effect of the reversal, not merely narrowed — there is no
"different session's control set" any more for a write to be invisible to.

**Invalidation marks the entry stale; it does not delete the row.** The stored command that
produced an entry (source, scope, parameters) must survive invalidation — deleting the row on
invalidation would destroy the very thing "recoverable staleness" above depends on: a
stale-identifier request that arrives after invalidation has only the old `content_id` to look
up with, not the caller's original scope (R8 explicitly does not have the caller carry that
forward). If the row were gone, the server would have no stored command to re-run, and recovery
would degenerate into an error requiring the caller to reconstruct its request from scratch —
exactly what this ADR exists to avoid. The schema (ADR-3082-1) carries an explicit stale marker
on each row for this reason; invalidation sets it, a subsequent stale-identifier request reads
the still-present stored command to regenerate, and the stale row is replaced (not merely
flagged) once regeneration under the new identity succeeds.

## Consequences

The control set needs an index from source to the entries generated from it, so a write can
find what to invalidate without scanning every entry. This is new integration surface across
every mutation path in the plugin, not confined to the read-path work already scoped by R1's
duplicate-implementation cleanup (#3057-#3059) — tracked separately as its own issue since it
touches write paths those issues do not.

## Considered alternative

Passive-only staleness (the ADR-3075-1 baseline: report stale, let the caller re-request) was
considered and rejected — it was the explicit thing being revised here, not a live alternative
this ADR is choosing between. Recorded for completeness, not because it was seriously weighed
against the decision above.

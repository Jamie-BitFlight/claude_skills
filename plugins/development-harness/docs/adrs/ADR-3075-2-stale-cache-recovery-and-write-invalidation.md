# ADR-3075-2: Stale control-set entries requery instead of erroring; writes invalidate

**Status:** Accepted
**Date:** 2026-08-20
**Issue:** New issue filed alongside this ADR (see cross-references below)
**Related:** Extends [ADR-3075-1](./ADR-3075-1-content-identity-and-cache-scope.md) — does not
reverse it. Session-scoped, non-persisted cache lifetime stands; this ADR adds behavior for
what happens *within* that lifetime when content changes underneath a cache entry.

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
On a stale-identifier request, that stored command re-runs Collection and Generation, produces
a new identity, and serves the caller against it, rather than erroring and requiring the caller
to reconstruct its original request from scratch.

**Write-triggered invalidation.** Every write path that can modify a source this contract
reads from — item updates, section writes, artifact registration, task and plan state changes
— invalidates any control-set entry generated from what it touched, as a side effect of the
write. This does not replace the identity check on read (R8's existing hash-mismatch
detection); it adds a second, earlier path to the same outcome, so a stale entry is caught
whether or not a read happens to hit it before a write does.

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

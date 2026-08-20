# ADR-3075-3: Content identity, command, and timestamp are visible response metadata

**Status:** Accepted
**Date:** 2026-08-20
**Issue:** New issue filed alongside this ADR (see cross-references below)
**Related:** Extends [ADR-3075-1](./ADR-3075-1-content-identity-and-cache-scope.md) and
[ADR-3075-2](./ADR-3075-2-stale-cache-recovery-and-write-invalidation.md) — both treated the
control set's identity, command, and staleness handling as internal server mechanics. This ADR
decides they are also caller-visible.

## Context

ADR-3075-2 gives the control set automatic write-triggered invalidation, but automatic
invalidation has blind spots: a write made through a path outside this contract's Scope, or
simply an agent that wants certainty rather than trust before acting on content it just
modified. (A write from a concurrent session was originally listed here too — no longer a
blind spot: ADR-3082-1's content-keyed reversal makes write-invalidation global, so a
concurrent-session write is visible the same as any other.) The repo owner asked for the agent
to have its own basis for judging freshness, not only the server's.

## Decision

Every response backed by the control set carries three pieces of metadata the cache already
computes for its own internal use: the content identity (R8's hash), the command that produced
it (source, scope, parameters — ADR-3075-2), and a timestamp of when it was generated. An agent
may use this to decide, on its own, whether to trust what it received.

A caller may explicitly request revalidation or a forced refresh instead of accepting whatever
the control set already holds. Both re-run Collection and Generation via the stored command —
identity is derived from the command plus Generation's output, not from the raw source alone
(ADR-3075-1), so recomputing current identity from the source alone is not an option. **Both
always write a fresh navigation document, confirmed by the repo owner: the control set is not a
durable reuse-optimization cache — it is temporary scratch space for one navigation task, for an
agent to page and jump around in while it locates currently-needed data. Any hit against the
backend produces a new document; nothing skips the write to avoid "redundant" work, because
reuse across separate requests was never the point.** Revalidation and forced refresh differ
only in what's reported, not in whether a write happens: revalidation compares the freshly
computed identity to the entry's previously-known identity and tells the caller whether it
changed; a forced refresh skips that comparison and reporting, unconditionally serving the fresh
document. **This is not about avoiding a re-parse** — the control set stores raw content, not a
parsed tree (ADR-3082-1), so serving any page from either path always reparses the row's raw
content in-memory, the same cost either way. Revalidation is a
caller-triggered path to the same outcome ADR-3075-2's write-triggered invalidation reaches
automatically — deliberately redundant with it, not a replacement for it, because the automatic
path cannot see every reason an agent might have to distrust a cached entry.

**When the fresh document's identity differs from the one the caller held, the storage
transition mirrors ADR-3075-2's automatic-recovery path exactly — there is no separate,
revalidation-specific behavior to invent.** Rows are keyed by `content_id` (ADR-3082-1); an
identity change is a different key, not an in-place update of the old row. The fresh document is
inserted as a new row under its new `content_id`; the old row is marked `stale` the same way
write-triggered invalidation marks it (ADR-3075-2's `stale` marker, not deletion — so a caller
still mid-navigation on the old identifier is told plainly it changed, rather than erroring or
silently seeing new content under an identifier it never asked to change). The response reports
the new identity and serves page 1 of the fresh document (or, when the caller's `navigate`
ordinal no longer resolves, an explicit restart response) — the same recovery shape ADR-3075-2
defines for an ordinary stale hit, because both paths land in the identical state: an entry
whose content changed underneath a stored identity. Revalidation reports the identity change
explicitly (that comparison is the whole point of the `revalidate` mode); forced refresh performs
the identical transition without reporting it as a change, consistent with forced refresh always
skipping the comparison (above).

## Consequences

Response shapes for every operation backed by the control set gain three metadata fields. This
composes with R6 (sections and artifacts as one inventory) and R8's existing identifier field —
it is additive to response shape, not a new response mode.

Revalidation and forced refresh need a concrete way for the caller to ask for them, not just a
prose description — added to R8's request shape as an optional `refresh` selector (`revalidate`
or `force`), absent by default.

## Considered alternative

Keeping identity/command/timestamp purely internal (the ADR-3075-1/3075-2 baseline) was
considered and rejected: it leaves an agent with no way to act on a freshness concern except
trusting the server's automatic invalidation, which the context above shows is not always
enough.

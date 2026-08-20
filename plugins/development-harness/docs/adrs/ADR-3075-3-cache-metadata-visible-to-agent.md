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
(ADR-3075-1), so recomputing current identity from the source alone is not an option. They
differ only in what happens after: revalidation compares the freshly computed identity to the
entry's stored identity and, on a match, leaves the existing row as-is rather than overwriting
it — no write happens, since the stored content is confirmed still current. A forced refresh
skips the comparison and unconditionally overwrites the row with the fresh document regardless
of whether the identity matches. **This is not about avoiding a re-parse** — the control set
stores raw content, not a parsed tree (ADR-3082-1), so serving any page from either path always
reparses the row's raw content in-memory, the same cost either way. Revalidation's saving is
narrower: skipping an unnecessary write when nothing actually changed. Revalidation is a
caller-triggered path to the same outcome ADR-3075-2's write-triggered invalidation reaches
automatically — deliberately redundant with it, not a replacement for it, because the automatic
path cannot see every reason an agent might have to distrust a cached entry.

## Consequences

Response shapes for every operation backed by the control set gain three metadata fields. This
composes with R6 (sections and artifacts as one inventory) and R8's existing identifier field —
it is additive to response shape, not a new response mode.

## Considered alternative

Keeping identity/command/timestamp purely internal (the ADR-3075-1/3075-2 baseline) was
considered and rejected: it leaves an agent with no way to act on a freshness concern except
trusting the server's automatic invalidation, which the context above shows is not always
enough.

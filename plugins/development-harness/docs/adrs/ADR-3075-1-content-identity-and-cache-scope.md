# ADR-3075-1: Content identity and cache scope for paginated responses (R8)

**Status:** Accepted
**Date:** 2026-08-20
**Issue:** [#3075](https://github.com/Jamie-BitFlight/claude_skills/issues/3075) and
[#3076](https://github.com/Jamie-BitFlight/claude_skills/issues/3076), both blocking
[#3062](https://github.com/Jamie-BitFlight/claude_skills/issues/3062)

## Context

R8 requires a stable identifier for a paginated response, derived from the content it
paginates. Two sub-decisions were open: what the identifier is derived from (raw markdown vs.
parsed tree), and how long the cache backing it lives (session vs. persisted). Nothing in
`progressive_markdown` implements any caching or content-hashing today — this was greenfield.

## Decision

**Identity source:** a hash of the Generation stage's output — the complete assembled document
for the request's specific scope (whole item, or a named artifact, or a filtered subtree) — not
a hash of the raw upstream source alone. Two different requested scopes of the same source
document (the whole item vs. one filtered section) produce different generated documents; if the
identifier hashed only the shared upstream source, both would collide on the same identifier
while windowing different content, which breaks R8's "identifier resolves against cached parsed
content" property. Hashing the generated output is the option that yields a working scheme, not
merely a style preference between two equally-valid choices.

**Cache scope:** session-scoped only, not persisted across sessions. Re-parsing markdown is
cheap relative to the rest of what a call already does (network round-trip to the backend); a
persisted cache would need its own storage location, eviction policy, and a plan for backend
content changing underneath a stale entry, for a cost that profiling has not shown to matter.
Confirmed by the repo owner: Collection itself is already backed by `FileCache`
(`backlog_core/file_cache.py`), an existing durable, provider-owned local cache of raw content
records — a Collection-stage re-run triggered by ADR-3075-2's requery-on-stale behavior is
routinely a local cache hit, not a network round-trip. This is a different cache from the one
this ADR governs (Collection-layer raw content vs. Navigation-layer generated/parsed/paginated
documents; durable vs. session-scoped) — not a reason to merge the two — but it is direct
evidence for "re-parsing is cheap," not just an assumption.

## Considered alternatives

Parsed-tree-derived identity was considered — it would keep pagination stable across
cosmetic-only source edits — and rejected as unnecessary complexity: R8 only needs "did the
content this response paginates change," not "is this semantically the same document," and a
raw hash of the generated output answers the former without a new tree-equality definition.

Persisted, cross-session caching was considered and rejected for the same reason: no measured
cost that justifies the added invalidation surface. Revisit if profiling shows parsing is an
actual bottleneck.

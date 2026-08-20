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

**Identity source:** derived from both the command (source, scope, parameters) and the
Generation stage's output for that command — not a hash of the raw upstream source alone, and
not a hash of the generated content alone either (the latter corrected after review found it
insufficient — see below). Two different requested scopes of the same source document (the
whole item vs. one filtered section) produce different generated documents; if the identifier
hashed only the shared upstream source, both would collide on the same identifier while
windowing different content, which breaks R8's "identifier resolves against cached parsed
content" property.

Content-only hashing was the original decision here and was corrected: two different commands
can coincidentally produce byte-identical generated output, and a content-only hash would give
them the same identifier while the control-set entry retains only one producing command — a
later requery or revalidation (ADR-3075-2, ADR-3075-3) could then execute the wrong command and
return content unrelated to what the caller asked for. Binding the identifier to the command as
well as the content closes this — two different commands never collide even when their output
happens to match.

**Command canonicalization is required before hashing, not optional.** The command must be
serialized to a stable, canonical form — fixed key order, defaults resolved to explicit values
before hashing, not left implicit — before it contributes to the identifier. Two calls that are
semantically the same request (same source, scope, parameters) but happen to serialize
differently (different kwarg order, one passing a default explicitly and the other omitting it)
must not hash differently. An identifier scheme that lets semantically identical requests miss
the same cache entry defeats R8's "resolves against the same cache entry" property as
thoroughly as the collision this ADR just fixed — from the other direction.

**Cache scope:** session-scoped only, not persisted across sessions. Re-parsing markdown is
cheap relative to whatever Collection itself already costs for a re-run — and for the GitHub
backend's primary path, that cost is a live network round-trip, not a local cache hit. Verified
directly against source: `GitHubContentCache.get_content()`
(`backlog_core/backends/github_content_migration.py`) calls `_read_online_content()` — a live
API read — whenever GitHub is reachable and no pending write blocks it; `FileCache` is only hit
on the fallback paths (GitHub unreachable, or the online read fails), not the common case.
`backlog_view`'s issue-body fetch (`_fetch_issue_graphql` in `gh_client.py`) has no cache layer
at all — an unconditional network call every time. So a persisted Navigation-layer cache would
not avoid the network cost Collection already pays on a re-run; it would only save the
parsing/pagination-computation cost on top of that, which is the smaller of the two and the one
profiling has not shown to matter. Beads, SQLite, and Memory read and write native state
directly and never instantiate `FileCache` (`docs/backend-providers.md`'s provider table) — for
those backends a Collection-stage re-run reads the native store directly. `FileCache` predates
the control set this ADR defines, has no session concept (`FileCache.__init__` takes a
project-root `Path`, no session parameter), and functions as an offline-fallback and
write-durability layer for GitHub specifically — not a read-avoidance cache for Navigation's
persistence question, and not evidence for "re-parsing is cheap" the way an earlier version of
this ADR claimed.

## Considered alternatives

Parsed-tree-derived identity was considered — it would keep pagination stable across
cosmetic-only source edits — and rejected as unnecessary complexity: R8 only needs "did the
content this response paginates change," not "is this semantically the same document," and a
raw hash of the generated output answers the former without a new tree-equality definition.

Persisted, cross-session caching was considered and rejected for the same reason: no measured
cost that justifies the added invalidation surface. Revisit if profiling shows parsing is an
actual bottleneck.

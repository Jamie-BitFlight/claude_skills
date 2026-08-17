---
name: project-filecache-pending-state-unified
description: backlog_core FileCache pending-write status is now a single derived value from the durable mutation queue, not a dual-stored flag
metadata:
  type: project
---

`plugins/development-harness/backlog_core/file_cache.py`'s `FileCache` used to store "is this
reference pending?" in two places: a `ContentRecord.pending` flag copied onto each cached record
in `state.records`, and a separate entry in the durable mutation queue (`state.pending`). PR #2942
(ponytail review item 2.4, `.tmp/scratch/reports/ponytail-review-20260817.md` section 2.4)
unified these: `state.pending` is now the sole source of truth. Every record written into
`state.records` is normalised to `pending=False`; `FileCache.get_content()` derives the true value
live via `FileCache._is_pending(state, reference)` (membership check against `state.pending`).
`FileCache.cache_content()`'s clobber-prevention guard checks queue membership instead of a stored
flag. `_GitHubContentCache.list_content()`'s offline-fallback branch in
`backends/github_content_migration.py` (which reads `state.records` directly, bypassing
`FileCache.get_content()`) derives `pending` from `FileCache.pending_mutations()` — this was the
one call site that previously had **no** derivation at all and would have silently reported
`pending=False` after the unification if left untouched.

**Why:** the ponytail review flagged this as "worth flagging, not urgent... a real refactor with
real regression risk," but tracing every read/write call site showed the two representations were
always kept in sync by hand at every existing call site (no genuine desync was ever possible in
the current call graph), which made deriving one from the other a safe, non-behavior-changing
simplification rather than a risky redesign.

**How to apply:** When touching `FileCache`/`_GitHubContentCache` pending-write logic, remember
`ContentRecord.pending` is a *computed* value at read time, not authoritative storage — do not
add a new call site that trusts a raw `state.records[i].pending` value without deriving it from
`state.pending` (or going through `FileCache.get_content()`, which does that already).

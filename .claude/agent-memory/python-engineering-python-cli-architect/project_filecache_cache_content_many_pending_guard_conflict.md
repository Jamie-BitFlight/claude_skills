---
name: filecache-cache-content-many-pending-guard-conflict
description: Rebasing PR #2942 (pending-state unification) onto PR #2934 (cache_content_many batch write) — how the discard_pending docstring conflict and cache_content_many's stale pending-guard were reconciled
metadata:
  type: project
---

PR #2934 (merged to main first) added `FileCache.cache_content_many()`, folding N records into
one `_CacheStateStore.transaction()`. Its per-record clobber-prevention guard was written against
the OLD pending model: `existing.pending` read off the stored `ContentRecord.pending` flag found
by scanning `current` (the records list being built up).

PR #2942 (rebased second) unified pending-ness to be derived live from `state.pending` (the
durable mutation queue) via the new `FileCache._is_pending(state, reference)` staticmethod —
`cache_content()` was updated to use it, but `cache_content_many()` didn't exist yet on that
branch, so git's 3-way merge auto-merged the file with `cache_content_many` still using the
pre-unification stored-flag check. **This is exactly the kind of conflict that auto-merges
cleanly (no `<<<<<<<` markers) but leaves semantically-inconsistent code** — always grep every
method that duplicates the guard/derivation logic touched by a unification-style refactor, not
just the methods that show conflict markers.

Fix: rewrite `cache_content_many`'s `replace()` closure to call
`self._is_pending(state, record.reference)` against the same `state` snapshot the loop is
iterating over (not `current`, which only tracks the records being folded), and normalise every
stored record to `pending=False` (`record.model_copy(update={"pending": False})`) — matching
`cache_content()`'s pattern exactly.

Separately, an actual `<<<<<<<` conflict landed in `discard_pending`'s docstring: PR #2942's
branch was cut before main's `0fe25121` ("dedup status-label writers and dead-guard comments",
already merged) reverted `discard_pending` from `-> bool` (an unused return value — its only
caller in `github_content_migration.py` ignores the result) back to `-> None`. PR #2942's stale
branch tip still carried the old bool-returning docstring's "Returns: True if ... False if ..."
section. Resolution: keep main's `-> None` signature/body (already-reviewed, already-merged
simplification — out of scope to re-litigate during a rebase) and keep only the *new* prose
PR #2942 added (the "no companion update to state.records is needed" paragraph), dropping the
stale "Returns:" section that no longer describes the actual return type.

**How to apply**: when reconciling a conflict between two refactor PRs on the same file, before
trusting an auto-merge that produced zero conflict markers for a given method, diff that method
specifically against both PR tips to confirm it actually reflects both PRs' intent — a clean
auto-merge is not proof of correctness when one PR added a new method that duplicates logic the
other PR unified elsewhere.

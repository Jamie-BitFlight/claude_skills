---
name: project-filecache-cache-content-many-batch-write
description: FileCache.cache_content_many() batches N content records into one durable transaction, fixing an O(n^2) per-record write loop
metadata:
  type: project
---

`plugins/development-harness/backlog_core/file_cache.py`'s `FileCache.cache_content()` wraps
every call in `_CacheStateStore.transaction()` (`file_cache_state.py`), which does a full
lock + YAML load + Pydantic validate + YAML dump + `fsync` of the *entire* cache state file per
call. A caller looping `cache_content()` once per record (e.g.
`_GitHubContentCache.list_content` in `backlog_core/backends/github_content_migration.py`) pays
that whole-state cost n times — O(n^2) total, invisible until a cache accumulates enough
records (101 records cost ~79s serial in the reproducing test).

Fixed (PR #2934, backlog #2931) by adding `FileCache.cache_content_many(records, *,
acknowledge_pending=False) -> int`: folds the whole batch into **one** `transaction()` call,
applying the same per-record `pending`-write guard (from PR #2906) inside the fold, and returns
the count of records actually stored (vs. skipped by the guard) — the loop caller logs when any
are skipped, closing a Silent Failure Prevention gap on the same path.

**Why:** A single batch transaction is a *strict* durability improvement over the per-record
loop it replaces, not a trade-off — the whole batch lands atomically or not at all, whereas the
old loop could leave a partially-refreshed cache on a mid-loop process death. Confirmed against
`backlog_core/ARCHITECTURE.md`'s stated guarantee (per-transaction atomicity, not per-record
fsync granularity) before implementing, per this repo's durability-first stance in
`backlog_core/` (see `AGENTS.md` "Modifying `backlog_core/` internals").

**How to apply:** Any future loop over `FileCache.cache_content()` (or any other
`_CacheStateStore.transaction()`-wrapped single-record method) processing more than a handful of
records is the same O(n^2) shape — check for an existing `_many` batch variant first, or add one
following this pattern (fold inside one `transaction()` closure, reuse `_replace_record`, return
a count) rather than writing a per-record loop.

Note: this method was later touched again during PR #2942's pending-state unification rebase,
which found the pending-guard inside it had silently reverted to the pre-unification stored-flag
check on a clean auto-merge — see [[project_filecache_cache_content_many_pending_guard_conflict]].

See also: [[project_github_sync_provider_replay_preserves_revision_pre_existing_fail]] — an
unrelated pre-existing test failure surfaced while validating this change, confirmed via
`git stash` reproduction on a clean checkout before ruling it out of scope.

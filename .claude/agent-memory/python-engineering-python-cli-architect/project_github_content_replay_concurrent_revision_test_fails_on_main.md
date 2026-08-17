---
name: project-github-content-replay-concurrent-revision-test-fails-on-main
description: test_github_content_provider_replay_preserves_concurrent_remote_revision fails on unmodified main — pre-existing, unrelated to FileCache pending-state work (tracked as backlog #2922)
metadata:
  type: project
---

`plugins/development-harness/tests_backlog/test_github_sync_provider.py::test_github_content_provider_replay_preserves_concurrent_remote_revision`
fails on unmodified `main` as of commit `1f9dcd92` (2026-08-17) — confirmed via `git stash` on the
two files touched for [[project_filecache_pending_state_unified]], re-running just this test
against the stashed-clean tree, same assertion failure (`'queued' == 'revision-two'`). Already
tracked as backlog #2922 — this memory adds the root-cause hypothesis, not a new report.

**Why:** it exposes a real design tension between two other passing tests in the same suite:
`_GitHubContentCache.get_content()` (`backends/github_content_migration.py`) intentionally prefers
returning cached "queued" content over a fresh online read when a write is stuck pending (PR #2906
clobber-prevention fix, protected by `test_pending_artifact_manifest_write_is_not_clobbered_by_empty_legacy_read`),
but this test wants a fresh remote read to win when there's a genuine revision conflict on the same
reference. Both behaviors can't hold simultaneously under the current `get_content()` branching —
whoever lands the fix needs to decide which case takes priority (or how to distinguish "stuck
because of a real conflict" from "stuck because of a transient block") rather than just patching
the assertion.

**How to apply:** Do not assume a failure on this specific test was caused by your own change to
`FileCache`/`_GitHubContentCache` pending-write logic — verify against `main` first before treating
it as a regression. Fixing it is a separate, scoped task (design decision + its own regression
test) tracked at backlog #2922, not a drive-by fix.

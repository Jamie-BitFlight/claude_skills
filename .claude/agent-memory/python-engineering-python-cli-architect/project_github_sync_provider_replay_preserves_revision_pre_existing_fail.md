---
name: project-github-sync-provider-replay-preserves-revision-pre-existing-fail
description: test_github_content_provider_replay_preserves_concurrent_remote_revision fails on a clean checkout, unrelated to FileCache batch-write changes (tracked as backlog #2922)
metadata:
  type: project
---

`plugins/development-harness/tests_backlog/test_github_sync_provider.py::test_github_content_provider_replay_preserves_concurrent_remote_revision`
fails with `AssertionError: assert 'queued' == 'revision-two'` on an unmodified checkout
(verified via `git stash` + rerun on commit `35aae026`, 2026-08-17) — not caused by
[[project_filecache_cache_content_many_batch_write]] or any other in-flight change. Already
tracked as backlog #2922.

**Why:** Confirmed via reproduction-integrity check (real environment first, no synthetic
isolation) before attributing the failure to unrelated work — this stopped a false-positive
regression claim in PR #2934.

**How to apply:** If this test fails again, don't assume the touching change caused it —
re-verify against a clean `main`/base-ref checkout first. Root cause (per backlog #2922 and
[[project_github_content_replay_concurrent_revision_test_fails_on_main]]): a design tension
between `_GitHubContentCache.get_content()` preferring queued/pending content over a fresh
remote read (PR #2906 clobber-prevention) versus wanting a fresh remote read to win on a genuine
revision conflict — not yet diagnosed to a fix.

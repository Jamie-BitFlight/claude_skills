---
name: backlog-core-connection-failure-taxonomy
description: backlog_core has two separate "provider unreachable" paths — background sync (OFFLINE vs ERROR) and the per-call cache fallback — identify which one a doc sentence describes before writing cause prose
metadata:
  type: project
---

Before writing "offline" / "unreachable" / "unavailable" cause prose in a backlog_core doc,
identify which path the sentence is about, then cite that path's causes only.

**Background sync** — `sync_engine.py` + `classify_sync_error()` in `sync_state.py`.
NON_RETRYABLE (auth 401/404, 403 without `Retry-After`, `BackendUnavailableError`, config
`ValueError`, non-network `OSError`) → `SyncStatus.OFFLINE` at once. RETRYABLE (429, 403 with
`Retry-After`, 5xx, network/timeout exceptions, generic `BacklogError`) → backoff, and after
`MAX_RETRIES` → `SyncStatus.ERROR`. So network failures end in ERROR, after the retries run out.
Cite `sync_engine.py` and `sync_state.py` for this state machine; `backlog_core/ARCHITECTURE.md` leaves it out.

**Per-call cache fallback** — `_provider_online()` in `backends/github_content_migration.py`,
which is what ARCHITECTURE.md's storage and `file_cache.py` sections describe.
`gh_client.try_get_github()` returns `None` for a missing token and raises
`GitHubUnavailableError` for any API or transport failure; `_provider_online()` folds both into
"serve the cached copy / queue the write". This path treats auth, network, rate-limit and 5xx failures alike.

`SyncStatus.OFFLINE` and `offline_reason` are identifiers — keep them; only the prose that
explains why a mode was entered needs the cause.

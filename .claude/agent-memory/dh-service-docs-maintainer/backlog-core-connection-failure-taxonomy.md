---
name: backlog-core-connection-failure-taxonomy
description: How backlog_core actually classifies a failed GitHub/backend connection — two separate mechanisms, their exact cause sets, and where each is (or isn't) documented in ARCHITECTURE.md
metadata:
  type: project
---

`backlog_core` has **two independent, non-overlapping** "provider unreachable" mechanisms. Don't
conflate them when editing docs — check which one a sentence is actually describing first.

## Mechanism A: background full-sync loop (`sync_engine.py` + `sync_state.py`)

`classify_sync_error()` (`sync_state.py:318-374`) is the authoritative, precise classifier:
- `BackendUnavailableError`/`GitHubUnavailableError`, `UnsupportedBackendCapabilityError`,
  `GithubException` 401/404, `OSError` (non-network), `ValueError` → `NON_RETRYABLE`.
- `GithubException` 403 without `Retry-After`, 401, 404 → `NON_RETRYABLE`.
- `GithubException` 403+`Retry-After`, 429, ≥500 → `RETRYABLE`.
- `requests.exceptions.ConnectionError`/`.Timeout`/`.ChunkedEncodingError`/
  `.ContentDecodingError`, `asyncio.TimeoutError` → `RETRYABLE` (checked before the generic
  `OSError` branch since these are `OSError` subclasses — verified via `.__mro__`).

`sync_engine.py:200-243`: `NON_RETRYABLE` → `SyncStatus.OFFLINE` immediately, loop stops.
`RETRYABLE` → exponential backoff (immediate, 30s, 120s), and **only after `MAX_RETRIES` is
exhausted does it become `SyncStatus.ERROR` — never `OFFLINE`**. A survey/summary that says
"network failures eventually land in OFFLINE too" is wrong; they land in `ERROR`. Grep
`ARCHITECTURE.md` for `sync_engine|sync_state|SyncStatus|classify_sync_error` before assuming this
state machine is even described there — as of 2026-09-15 it is not mentioned once.

## Mechanism B: per-call `FileCache`/`try_get_github()` gate (what ARCHITECTURE.md documents)

Everything ARCHITECTURE.md's "Storage Ownership", "file_cache.py", and content-cache sections
describe is this simpler mechanism, not Mechanism A. The gate is
`self._provider.try_get_github() is None` in `backends/github_content_migration.py:337,382`
(read/write), delegating to `gh_client.try_get_github` (`gh_client.py:1186-1203`):
- Returns `None` for missing `GITHUB_TOKEN` (unauthenticated).
- Returns `None` for **any** `GithubException` (blanket `except GithubException`) — so invalid
  token (401), rate limit (429/403), and 5xx all return `None` here too, unlike Mechanism A which
  distinguishes them.
- Does **not** catch raw `requests.exceptions.ConnectionError`/`.Timeout` at the probe point
  (not a `GithubException` subclass) — these propagate uncaught out of `try_get_github()`, contra
  its own docstring's claim of covering "network error". Real gap, not yet fixed as of 2026-09-15.
- The *write* path additionally queues on `except (BacklogError, ContentUnavailableError,
  OSError)` around `_write_online_content` (`github_content_migration.py:390-394`) — since
  `ConnectionError`/`Timeout` are `OSError` subclasses, a network failure that occurs *during the
  write itself* (after a successful probe) IS caught and queued there, even though the same
  failure at the probe stage is not.

`GitHubUnavailableError` (`models.py`, raised only at `gh_client.py:1178-1181`) is narrower than
either mechanism above: it fires **only** for a missing token, never for an invalid one and never
for a network/5xx/rate-limit failure. Don't let "unauthenticated" docs generalize this exception
to "missing or invalid" — the code never checks validity here, only presence.

## Doc-sync takeaway

When a doc sentence says "provider is unreachable"/"offline"/"unavailable", first identify which
mechanism (A or B) the surrounding module/section is actually about, then cite the causes that
mechanism's code actually covers — don't import Mechanism A's clean auth/network/ratelimit/5xx
split into a sentence describing Mechanism B (or vice versa) without checking. `SyncStatus.OFFLINE`
and `state.offline_reason` are legitimate mode-label identifiers and should never be renamed —
only the prose explaining *why* a mode was entered needs the cause detail.

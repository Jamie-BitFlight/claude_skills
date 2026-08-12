# Architect Spec: Redesign Backlog GitHub Sync — Offline-First with Per-Item Watermarks

**Issue:** #2573
**Agent:** python-engineering:python-cli-design-spec
**Date:** 2026-06-04
**Status:** SUPERSEDED by [Provider-Neutral Backlog Snapshot Reconciliation](./architect-backlog-snapshot-reconciliation.md)

> This draft is retained for history only. Do not implement it. The replacement architecture rejects its dirty-flag,
> outbox, and `last_synced` watermark decisions.

---

## 1. Executive Summary

This spec replaces the three-policy GitHub sync model (background overwrites local, push overwrites GitHub, explicit pull merges) with a single offline-first model governed by per-item remote watermarks, an explicit 3-state dirty-flag that distinguishes content-edits from local closures, an outbox driven by persisted dirty state, and backend-gated execution that produces zero GitHub network activity under sqlite/memory/beads backends. Every GitHub call is hard-bounded by a timeout. The merge function `merge_item_models` is invoked only on genuine conflicts — when a local change (dirty item) and a remote change (diverged watermark) exist simultaneously. Non-dirty items with a diverged watermark receive a plain overwrite-from-remote (no merge needed; no local change to protect). The primary correctness invariant is: a local write that returns success is durable — it survives server restart, background sync, and offline periods. The primary data invariant is: the local watermark (`BacklogItemMetadata.last_synced`) always stores the remote `updatedAt` returned by the last successful push or pull, and is never inferred from local filesystem state.

---

## 2. Architecture Overview

### 2.1 Conceptual Model

The system is a local-authoritative cache with bounded, optional remote synchronisation. The local YAML file is the primary store; GitHub is the remote replica. A write is complete when it lands locally with a dirty flag set — remote sync is a durable follow-through, not a prerequisite for durability.

Four primitives govern all sync paths:

1. **Watermark** — `BacklogItemMetadata.last_synced` stores the remote `updatedAt` ISO 8601 string returned by the most recent successful push or pull. The comparison is always: `remote_current_updatedAt == stored_watermark`. Never compare local clock values to remote timestamps.

2. **Dirty flag** — `BacklogItemMetadata.pending_push` is a 3-state string (see §5). It distinguishes content-edits (need push) from local closures (need GitHub issue close). The background reconcile and pull paths check this flag before overwriting local state.

3. **Outbox** — the set of local YAML files where `pending_push != ""`. Derived by scanning local files, not an in-memory queue. The background reconcile loop is the outbox driver; an explicit `backlog_sync --push-dirty` command is the manual driver.

4. **Backend gate** — a new Protocol capability flag `performs_remote_sync: bool` (True only on the GitHub backend). All sync paths check this flag first and no-op immediately for non-GitHub backends.

### 2.2 Data Flow: WRITE (awaited write-through)

```
Caller → write local YAML + set pending_push="content" → [return durability anchor]
       → check performs_remote_sync: False → return "saved locally, pending push"
       → check performs_remote_sync: True
         → probe health (classify from first bounded call, not a separate probe)
           → offline/error: return "saved locally, pending push"; outbox retries later
           → healthy: acquire SyncState.lock
             → fetch current remote updatedAt (bounded, 10 s)
             → compare to stored watermark
               → match: issue bounded updateIssue mutation (returns updatedAt)
               → diverge: pull + merge_item_models → issue bounded updateIssue (returns updatedAt)
             → on push success: clear pending_push, store returned updatedAt in last_synced
             → on timeout/error: leave dirty; release lock; return "pushed locally, push pending"
             → release lock
```

### 2.3 Data Flow: READ (single item)

```
Caller → load local YAML
       → check performs_remote_sync: False → return local
       → check performs_remote_sync: True
         → probe health (classify from first bounded call)
           → offline: return local
           → healthy: acquire SyncState.lock
             → fetch current remote updatedAt (bounded, 10 s)
             → compare to stored watermark
               → match: return local (no pull)
               → diverge:
                 → if pending_push != "": pull + merge_item_models (dirty-protection: merge, not overwrite)
                 → if pending_push == "": pull and overwrite local
               → store pulled updatedAt as new watermark
             → release lock
             → return merged/pulled item
```

### 2.4 Data Flow: BACKGROUND RECONCILE

```
_startup_sync_loop (GitHub backend only, gated on performs_remote_sync)
  → acquire SyncState.lock
  → batch-fetch {number, updatedAt} for all items (one GraphQL call)
  → Phase 1 — PUSH: for each item where pending_push != "":
      → apply lifecycle divergence rules (see §5.3)
      → push with bounded updateIssue; on success clear dirty + update watermark
  → Phase 2 — PULL: for each item where remote_updatedAt != stored_watermark AND pending_push == "":
      → pull + _write_issue_node_to_cache (overwrite from remote — no merge; item is not dirty)
      → store new watermark
  → release lock
  → update last_sync timestamp
```

### 2.5 Data Flow: CONFLICT (both sides changed)

**Conflict is defined as: diverged remote watermark AND item locally dirty (`pending_push != ""`).** A non-dirty item with a diverged watermark is not a conflict — it receives a plain overwrite from remote (see §2.3 and §2.4 Phase 2). Conflict resolution applies only in the WRITE path and the READ path when the item is dirty. In the BACKGROUND reconcile, dirty items are resolved by pushing first (Phase 1) — which may itself encounter a diverged watermark and trigger a write-path conflict resolution. The conflict resolution path is always:

1. Pull the remote item via `_fetch_issue_graphql`
2. Pass `(local_item, remote_item)` to `merge_item_models`
3. Persist the merged result locally
4. Push the merged result to GitHub via `_update_issue_graphql` (returns `updatedAt`)
5. Clear dirty; store returned `updatedAt` as new watermark

`merge_item_models` semantics are unchanged: local metadata authoritative, sections union, per-entry struck-wins then longer-content-wins, per-groomed-subsection longer-content-wins.

---

## 3. Technology Stack

| Component | Technology | Source |
|---|---|---|
| Language | Python 3.11+ | Project baseline |
| Async runtime | `asyncio` | Existing; MCP server is async |
| Sync boundary | `asyncio.to_thread` | Existing pattern in `artifact_provider.py`; all backend protocol methods are synchronous |
| Locking primitive | `asyncio.Lock` (SyncState.lock) | `sync_state.py:95`; single lock, scope extended |
| HTTP/GraphQL | `PyGithub` + direct `_graphql_request` | Existing; timeout=15 on `get_github`, timeout=10 on `try_get_github` |
| Model layer | Pydantic BaseModel (`BacklogItem`, `BacklogItemMetadata`) | Existing |
| Type literals | `typing.Literal` / `StrEnum` (Python 3.11+) | Modern Python lane; `StrEnum` for dirty-state enum |
| Persistence format | YAML via `ruamel.yaml` | Existing per-item YAML cache |
| Backend protocol | `BacklogBackend` Protocol (`backend_protocol.py`) | Existing; add `performs_remote_sync` flag |

**Established patterns reused:**

- `GistTaskLayer` write-through precedent: write local, read-check remote watermark, push if unchanged (cited in item #2573 Summary section).
- `ArtifactBackend` offline fallback: when remote unavailable, fall back to local.
- Capability-flag gating: `supports_batch_status_fetch`, `supports_batch_issue_update` — same pattern for `performs_remote_sync`.
- `asyncio.to_thread` wrapping synchronous backend calls from async handlers.

---

## 4. Component Design

### 4.1 `gh_client.py` — `_UPDATE_ISSUE_MUTATION` and `_update_issue_graphql`

**Change type:** MODIFIED (two-part change)

**Part A — Mutation selection set expansion.**

Current mutation (gh_client.py:218-229) returns `issue { id number state }` — `updatedAt` is absent. The watermark must be the remote `updatedAt` returned after a successful push. Capturing it requires expanding the selection set:

```python
_UPDATE_ISSUE_MUTATION = """
mutation UpdateIssue(
  $id: ID!, $state: IssueState, $body: String, $title: String,
  $labelIds: [ID!], $milestoneId: ID
) {
  updateIssue(input: {
    id: $id, state: $state, body: $body, title: $title,
    labelIds: $labelIds, milestoneId: $milestoneId
  }) {
    issue { id number state updatedAt }
  }
}
"""
```

**Part B — `_update_issue_graphql` return type change.**

Current signature (backend_protocol.py:332): `-> None`. The implementation in `gh_client.py` must be changed to return the `updatedAt` string from the mutation response.

New signature:

```python
def _update_issue_graphql(
    self,
    repo: Repository,
    issue_node_id: str,
    *,
    state: str | None = None,
    body: str | None = None,
    title: str | None = None,
    label_ids: list[str] | None = None,
    milestone_id: str | None = None,
) -> str:
    """Update an issue's mutable fields via mutation.

    Returns:
        The remote ``updatedAt`` ISO 8601 string from the mutation response.
        Callers that do not need the watermark may discard the return value.
    """
```

**API stability for cross-module consumers:** `sam_schema/core/backends/github_task.py` calls `_update_issue_graphql` at lines 411, 446, 455, and 564. All four calls are bare statements (`self._issue_backend._update_issue_graphql(repo, node["id"], body=body)`) that already discard the return value. Changing `-> None` to `-> str` is non-breaking for all four. Changing the parameter list would break all four — the signature above preserves parameter compatibility exactly.

**Behavioral contract:**
- Pre: `issue_node_id` is a valid GitHub GraphQL node ID; at least one mutable field argument is non-None.
- Post: the mutation is applied; returns the server-authoritative `updatedAt` ISO 8601 string. On error, raises `BacklogError`; never returns an empty string on success.

---

### 4.2 `models.py` — `BacklogItemMetadata` and `DirtyState`

**Change type:** MODIFIED

New `StrEnum` (Python 3.11+ `StrEnum`, no import needed beyond `enum`):

```python
from enum import StrEnum

class DirtyState(StrEnum):
    """Dirty-flag state for a backlog item pending remote sync.

    CLEAN:   No local changes pending; item is in sync with last watermark.
    CONTENT: Item has unsaved local edits (body, sections, metadata).
             On reconnect: push via updateIssue.
    CLOSURE: Item was closed locally (resolve/close) but not yet pushed.
             On reconnect: close the GitHub issue via state transition.
             SPECIAL RULE: if GitHub issue is deleted while pending_push==CLOSURE,
             treat as no-op (both sides agree the item is done).
    """
    CLEAN = ""
    CONTENT = "content"
    CLOSURE = "closure"
```

`BacklogItemMetadata` changes (models.py around line 718):

```python
# BEFORE
last_synced: str = ""      # line 718 — was unused, now: stored remote updatedAt watermark
updated_at: str = ""       # line 719 — local metadata timestamp; NOT the remote watermark

# AFTER (add pending_push; last_synced repurposed)
last_synced: str = ""      # remote updatedAt from last successful push or pull (watermark)
updated_at: str = ""       # local metadata timestamp — NOT the remote watermark
pending_push: str = ""     # DirtyState value; serialised as "" | "content" | "closure"
```

**Clarification on `updated_at` vs `last_synced`:**
- `last_synced` (line 718): this is the watermark slot. Stores the remote `updatedAt` ISO 8601 string returned after a successful push or pull. The comparison in every sync path is `remote_current_updatedAt == stored last_synced`.
- `updated_at` (line 719): local metadata timestamp. Must not be used as a watermark or compared to remote timestamps.

Legacy items lacking `pending_push` deserialise cleanly because the field defaults to `""` (= `DirtyState.CLEAN`).

---

### 4.3 `backend_protocol.py` — `BacklogBackend` Protocol

**Change type:** MODIFIED

Add new capability flag:

```python
#: True when the backend performs remote synchronisation with a networked source.
#: False for sqlite, memory, and beads backends — those are local-only.
#: Used to gate _startup_sync_loop, write-through, and watermark reads.
performs_remote_sync: bool
```

Update `_update_issue_graphql` return type to `-> str` (see §4.1 Part B).

All non-GitHub backend implementations set `performs_remote_sync = False` and retain `_update_issue_graphql` as `-> None` raising `NotImplementedError` — the return type change does not affect them because they are never called when `performs_remote_sync = False`.

---

### 4.4 `gh_client.py` — `GitHubBackend` (or equivalent concrete class)

**Change type:** MODIFIED

Set `performs_remote_sync = True`.

Implement `_update_issue_graphql` returning `str` (the `updatedAt` from mutation response).

---

### 4.5 `backends/memory_backend.py`, `sqlite_backend.py`, `beads_backend.py`

**Change type:** MODIFIED (capability flag only)

Add `performs_remote_sync = False`. No other changes. `_update_issue_graphql` implementations (if any) retain `-> None` and raise `NotImplementedError` — they are never called.

---

### 4.6 `sync_state.py` — `SyncState`

**Change type:** UNCHANGED (lock scope extended by call sites, no model change)

The existing `SyncState.lock: asyncio.Lock` serialises background sync workers. Its scope is extended to cover foreground write-through operations by acquiring it in the write-through path (§4.7). No changes to `SyncState` itself.

---

### 4.7 `operations.py` — new `write_through_item` function

**Change type:** NEW

```python
async def write_through_item(
    item: BacklogItem,
    *,
    dirty_state: DirtyState = DirtyState.CONTENT,
    timeout: float = 10.0,
) -> WriteResult:
    """Offline-first write: persist locally, then bounded push to GitHub.

    Pre-conditions:
        - ``item`` has been serialised and saved locally by the caller before
          this function is invoked. This function does NOT save locally itself;
          it sets the dirty flag, then attempts the remote push.
        - ``item.metadata.last_synced`` contains the last known remote watermark
          (may be empty for new items).

    Post-conditions (success):
        - ``item.metadata.pending_push == DirtyState.CLEAN``
        - ``item.metadata.last_synced`` is the remote ``updatedAt`` returned
          by the push.
        - The updated item is persisted to disk.

    Post-conditions (offline / timeout):
        - ``item.metadata.pending_push == dirty_state`` (preserved)
        - ``item.metadata.last_synced`` is unchanged
        - The dirty item remains on disk for outbox retry.

    Returns:
        WriteResult — see models.py; includes ``synced: bool``, ``watermark: str``,
        ``message: str``.
    """
```

**Serialization shape and write order (NFR 7 — safe write order):**

The caller is responsible for the initial local save. `write_through_item` sets the dirty flag and performs the remote push. This separation ensures the dirty anchor is on disk before any network attempt.

Exact sequence:

1. **Caller** saves `item` to local YAML (durability anchor — edit on disk before any network call).
2. **Caller** invokes `write_through_item(item, dirty_state=DirtyState.CONTENT)`.
3. `write_through_item` sets `item.metadata.pending_push = dirty_state` and re-persists (dirty anchor on disk — if the process crashes after this point, the item is recoverable from disk as dirty).
4. Checks `get_config().backend.performs_remote_sync` — if False, returns `WriteResult(synced=False, message="saved locally, pending push")`.
5. Acquires `get_sync_state().lock` (async).
6. Inside the lock, wraps all GitHub calls in `asyncio.to_thread` with `asyncio.wait_for(..., timeout=timeout)`.
7. Fetches current `updatedAt` for the issue (lightweight watermark-check query `{ number updatedAt }`). On `TimeoutError` / `GithubException` / `ConnectionError`: classify as offline, leave dirty, release lock, return `WriteResult(synced=False, dirty=True, ...)`.
8. Compares to `item.metadata.last_synced`.
9. If diverged (remote moved while we were offline): `remote = _fetch_issue_graphql(...)` → `merged = merge_item_models(item, remote)` → push `merged` via `_update_issue_graphql` (returns `updatedAt`).
10. If matched (no remote change): push `item` via `_update_issue_graphql` (returns `updatedAt`).
11. On push success: clear `pending_push`, set `last_synced` to returned `updatedAt`, persist.
12. On push timeout or exception: leave dirty, log, return `WriteResult(synced=False, dirty=True, ...)`.
13. Releases lock.

---

### 4.8 `operations.py` — modified `refresh_local_cache_from_github` and `_write_issue_node_to_cache`

**Change type:** MODIFIED

`_write_issue_node_to_cache` currently overwrites local unconditionally. New behaviour: add a `pending_push` check to protect dirty items in the read path. However, in the background reconcile Phase 2 (which calls this function), items reaching Phase 2 are already confirmed not-dirty (the filter `pending_push == ""` in Phase 2 ensures this). So the `pending_push` check in `_write_issue_node_to_cache` is a defensive guard; Phase 2 does not rely on it.

```python
def _write_issue_node_to_cache(
    filepath: Path,
    node: IssueNode,
    *,
    force: bool = False,
) -> None:
    """Write a GitHub issue node to the local cache (overwrite from remote).

    For non-dirty items (``pending_push == DirtyState.CLEAN``) this is a plain
    overwrite — the remote version replaces local. When ``force`` is False and
    the local item is dirty, this function raises ``AssertionError`` — dirty items
    must go through the conflict-resolution path (``merge_item_models``), not here.

    Pre: ``filepath`` is a valid YAML cache path.
         When ``force`` is False: local ``pending_push`` must be ``DirtyState.CLEAN``.
    Post: local file reflects the remote node content; watermark
          (last_synced) is updated to ``node["updatedAt"]``.
    """
```

`refresh_local_cache_from_github` is the background reconcile driver. Modified to:
1. Check `performs_remote_sync` at entry — return immediately if False.
2. Acquire `SyncState.lock`.
3. Phase 1 PUSH: iterate all local items where `pending_push != ""`, call `_push_dirty_item` (new helper, bounded).
4. Phase 2 PULL: iterate all items where `remote_updatedAt != stored_watermark` AND `pending_push == ""`, call `_write_issue_node_to_cache` (overwrite from remote).
5. Release lock.

---

### 4.9 `server.py` — `_startup_sync_enabled` and `_backlog_lifespan`

**Change type:** MODIFIED

`_startup_sync_enabled` currently reads config YAML only and does not check backend type (RT-ICA Condition 3). New behaviour: add backend gate.

```python
def _startup_sync_enabled() -> bool:
    """Return True when the startup sync should run.

    Checks both the config YAML kill-switch AND the active backend's
    performs_remote_sync capability. Returns False for any non-GitHub backend
    regardless of config, preventing network activity under sqlite/memory/beads.
    """
    if not get_config().backend.performs_remote_sync:
        return False
    configured = _read_startup_sync_enabled_from_yaml()
    return True if configured is None else configured
```

---

### 4.10 `sync_engine.py` — `_startup_sync_loop`

**Change type:** MODIFIED

Replace the current overwrite-then-push model with the watermark-incremental push-then-pull model described in §2.4. The loop acquires `SyncState.lock` and serialises with foreground writes via the same lock.

---

### 4.11 `models.py` — new `WriteResult` TypedDict

**Change type:** NEW

```python
class WriteResult(TypedDict):
    """Result of a write_through_item call."""
    synced: bool          # True if remote push succeeded
    watermark: str        # Remote updatedAt if synced; "" if offline/error
    message: str          # Human-readable outcome description
    dirty: bool           # True if item remains dirty (pending outbox retry)
```

---

## 5. Data Architecture

### 5.1 `BacklogItemMetadata` Field Changes

| Field | Before | After | Notes |
|---|---|---|---|
| `last_synced` (line 718) | `str = ""` — unused | `str = ""` — **remote `updatedAt` watermark** | Reused slot; stores ISO 8601 UTC from last successful push or pull |
| `updated_at` (line 719) | `str = ""` — local metadata ts | `str = ""` — local metadata ts | **Not** a watermark; never compared to remote timestamps |
| `pending_push` | absent | `str = ""` — `DirtyState` value | New field; defaults to `""` (CLEAN); legacy items deserialise safely |

### 5.2 Dirty Flag Persistence Format

The `pending_push` field is persisted in the per-item YAML as a plain string. Valid values are the `DirtyState` StrEnum values:

```yaml
# YAML representation
metadata:
  last_synced: "2026-06-03T14:22:00Z"   # remote updatedAt watermark
  updated_at: "2026-06-03T14:20:00Z"    # local metadata timestamp
  pending_push: "content"               # "" | "content" | "closure"
```

- `""` (empty string / `DirtyState.CLEAN`): item is in sync; no push pending.
- `"content"`: local body/sections/metadata edits not yet pushed.
- `"closure"`: item was closed/resolved locally; GitHub issue close is pending.

Legacy items (YAML files that predate this redesign) have no `pending_push` key — Pydantic deserialises them as `""` via the field default. No migration is required.

### 5.3 Lifecycle Divergence Rules

Applied during background reconcile Phase 1 (PUSH) and WRITE write-through when the remote state is fetched.

User-confirmed cases (source: feature-context Resolved Questions, 2026-06-04):

| Remote state | Local `pending_push` | Rule | Implementation |
|---|---|---|---|
| Issue CLOSED remotely | `""` (CLEAN) | **[CONFIRMED]** Remote wins → resolve local item | `save_item` with resolved status; clear watermark |
| Issue CLOSED remotely | `"closure"` | **[CONFIRMED]** Both agree → no-op | Clear `pending_push`; update watermark |
| Item CLOSED locally | Issue open remotely | **[CONFIRMED]** Local wins → close GitHub issue | `_update_issue_graphql(state="CLOSED")` |
| Issue DELETED remotely | `""` (CLEAN) | **[CONFIRMED]** Remote wins → delete local | Remove local YAML file |
| Issue DELETED remotely | `"content"` | **[CONFIRMED]** Dirty protection → re-create + relink | `create_issue_for_item`; update `issue` field; clear dirty |
| Issue DELETED remotely | `"closure"` | **[CONFIRMED]** Both agree → no-op | No action; remove local YAML if desired |

UNCONFIRMED case — requires product decision before implementation:

| Remote state | Local `pending_push` | Rule | Implementation |
|---|---|---|---|
| Issue CLOSED remotely | `"content"` | **[UNCONFIRMED]** Proposed: conflict → merge + push (re-opens remote issue) | `merge_item_models` + `_update_issue_graphql(state="OPEN", ...)` |

The "re-open" row is not in the 5 user-confirmed cases. It involves silently overriding a remote close by pushing a state-OPEN mutation, which is a non-obvious product decision. **Implementers must seek explicit confirmation from the product owner before implementing this row.**

### 5.4 Outbox Model

The outbox is not a separate data structure. It is defined as: all local YAML files where `pending_push != ""`. This is derived by scanning the backlog directory. No separate queue file is maintained.

The in-process outbox pump (background reconcile Phase 1) uses the existing `asyncio.Queue` infrastructure in `sync_engine.py` only as a wakeup signal — the authoritative set of dirty items is always derived from disk. This means pending pushes survive server restart.

### 5.5 Watermark Capture After Push

Two implementation options were evaluated (constraint #1):

- **(a) Expand the mutation response selection set** — one round trip; requires changing the mutation string and return type of `_update_issue_graphql`. **Selected** (see §4.1).
- **(b) Post-mutation lightweight fetch** — two round trips; no mutation change needed. **Rejected** (additional latency; wrong answer in the window between mutation and fetch).

The captured value is `response["data"]["updateIssue"]["issue"]["updatedAt"]` from the expanded mutation response.

---

## 6. Type System Design

### 6.1 `DirtyState` StrEnum

```python
from enum import StrEnum

class DirtyState(StrEnum):
    CLEAN = ""
    CONTENT = "content"
    CLOSURE = "closure"
```

`StrEnum` (Python 3.11+, PEP 663) enables direct string comparison (`item.metadata.pending_push == DirtyState.CONTENT`) while round-tripping transparently through YAML serialisation as a plain string.

### 6.2 `WriteResult` TypedDict

```python
from typing import TypedDict

class WriteResult(TypedDict):
    synced: bool
    watermark: str
    message: str
    dirty: bool
```

### 6.3 `IssueWatermarkNode` TypedDict

A minimal TypedDict for the lightweight watermark-check query (used in write-through and read paths):

```python
class IssueWatermarkNode(TypedDict):
    number: int
    updatedAt: str
```

### 6.4 Updated `_update_issue_graphql` return type

The Protocol method signature changes from `-> None` to `-> str`. All non-GitHub backend implementations may leave their stubs returning `NotImplementedError` (they are never reached when `performs_remote_sync = False`). The GitHub implementation returns the `updatedAt` string.

### 6.5 Boundary Validation

Watermark timestamps enter at two boundaries:

1. **Mutation response** — `response["data"]["updateIssue"]["issue"]["updatedAt"]` parsed via `str(...)`. A `validate_iso8601_utc` boundary function raises `BacklogError` if the value is not parseable by `datetime.fromisoformat`.

2. **Stored YAML** — `BacklogItemMetadata.last_synced` is a plain string; validation is applied at read time before comparison: `if last_synced: datetime.fromisoformat(last_synced)`.

No `Any` types are introduced. The raw GraphQL response is typed as `dict[str, object]` at the boundary and keys are accessed with explicit type assertions.

### 6.6 `performs_remote_sync` Protocol Flag

```python
# In BacklogBackend Protocol
performs_remote_sync: bool
```

Type: `bool` (not `Literal[True]` or `Literal[False]` — the Protocol declares the type; each concrete implementation sets the value). All guard call sites use `if not backend.performs_remote_sync: return ...` pattern.

---

## 7. Security Architecture

### 7.1 Timeout as DoS Prevention

Every GitHub call in all sync paths (write-through, read, background reconcile) is bounded by `asyncio.wait_for(..., timeout=T)`. Recommended timeout values:

| Operation | Timeout | Rationale |
|---|---|---|
| Watermark-check query (`{number, updatedAt}`) | 10 s | Lightweight; existing `try_get_github` uses 10 s |
| `_update_issue_graphql` push | 15 s | Existing `get_github` uses 15 s |
| `_fetch_issue_graphql` single-item pull | 15 s | Match push timeout |
| Background batch watermark fetch | 30 s | Batch call; allow more headroom |

These values are enforced at the `asyncio.wait_for` call site in `write_through_item` and the background reconcile loop. They are not buried inside the transport layer.

### 7.2 Backend Isolation

The `performs_remote_sync = False` flag on sqlite/memory/beads backends provides hard isolation: no GitHub credential is consumed, no network call is made, and no watermark comparison is attempted when the backend is non-GitHub. This prevents silent environment contamination in CI/CD runs and test suites.

### 7.3 Dirty-Protection Invariant

A local write returns a durability anchor (the YAML file on disk with `pending_push != ""`) before any network attempt. No state exists where an edit lives only on GitHub without a local anchor. On partial failure (push timeout), the local anchor persists; the outbox retries the push.

### 7.4 Watermark Comparison Safety

Comparison is always `remote_current_updatedAt == stored_watermark` (both are ISO 8601 UTC strings from GitHub). Local clock values and filesystem mtimes are never compared to remote timestamps. This prevents clock-skew false positives.

---

## 8. Testing Architecture

### 8.1 Test Strategy Overview

Tests are authored independently of the implementation to carry evidential weight (see CLAUDE.md test-authorship-independence rule). Test authors receive the behavioral contracts from this spec, not the implementation.

### 8.2 Unit Tests — Lifecycle Divergence Rules (§5.3)

One test per lifecycle-divergence row. Each test:
1. Constructs a local `BacklogItem` with a known `pending_push` state.
2. Constructs a mock remote node with the specified remote state (CLOSED / DELETED).
3. Calls the reconcile function under test.
4. Asserts the exact post-condition (local status, pending_push, watermark, presence/absence of YAML file).

These tests must be **independent of the GitHub backend** — use the `memory_backend` stub or a mock that fulfils the Protocol. They test the lifecycle rules, not the GitHub transport.

### 8.3 Unit Tests — Dirty-Protection Invariant

Test: background reconcile does NOT overwrite a `pending_push="content"` item when the remote watermark has diverged.

```python
def test_dirty_item_is_not_overwritten_by_reconcile():
    # Arrange: local item with pending_push="content", stale watermark
    # Act: call _write_issue_node_to_cache with a newer remote node
    # Assert: local sections are merged (merge_item_models applied), not replaced
    # Assert: pending_push is preserved (not cleared)
```

### 8.4 Unit Tests — Watermark Capture

Test: after a successful `_update_issue_graphql` call, `last_synced` is updated to the returned `updatedAt`.

```python
def test_watermark_captured_after_successful_push():
    # Arrange: item with known last_synced, matching remote watermark
    # Mock _update_issue_graphql to return a new updatedAt string
    # Act: write_through_item(item)
    # Assert: item.metadata.last_synced == returned_updated_at
    # Assert: item.metadata.pending_push == DirtyState.CLEAN
```

### 8.5 Async Concurrent Test — Outbox Serialisation

Test: a foreground write-through and a background reconcile executed concurrently cannot produce interleaved YAML writes.

```python
async def test_foreground_and_background_serialized():
    # Arrange: item with matching watermark
    # Launch background reconcile coroutine (holds lock for 100 ms via asyncio.sleep mock)
    # Simultaneously launch write_through_item
    # Assert: write operations are serialised (writes appear in one-at-a-time order)
    # Assert: final YAML state is consistent (no partial writes)
```

Implement using `asyncio.gather` with a mock lock that records acquisition order.

### 8.6 Offline Write Test

Test: when the backend is GitHub but `probe_backend_status` returns non-reachable, `write_through_item` returns a dirty item without attempting any GitHub call.

```python
async def test_offline_write_returns_dirty():
    # Arrange: GitHub backend, patched to raise asyncio.TimeoutError on watermark fetch
    # Act: write_through_item(item)
    # Assert: result.synced == False
    # Assert: result.dirty == True
    # Assert: item.metadata.pending_push == DirtyState.CONTENT
    # Assert: no _update_issue_graphql call made
```

### 8.7 Integration Test — Backend Gating

Test: when `performs_remote_sync = False`, `_startup_sync_enabled()` returns False and no GitHub calls are made during server lifespan.

```python
def test_no_github_calls_under_non_github_backend():
    # Arrange: sqlite backend (performs_remote_sync = False)
    # Act: call _startup_sync_enabled()
    # Assert: returns False without reading YAML config
```

### 8.8 Existing Tests — Update and Regression Safety

The `_UPDATE_ISSUE_MUTATION` selection set change (`updatedAt` added) and the `_update_issue_graphql` return type change (`-> None` → `-> str`) will require updates to tests that assert the current mutation string or the current return type:

- `tests/test_graphql_helpers.py` — likely asserts the mutation shape; update to expect `updatedAt` in response.
- `tests/test_backlog_core_github.py` — likely mocks `_update_issue_graphql` as returning `None`; update mocks to return an `updatedAt` string.

Tests unaffected by these changes should continue to pass:
- `tests/test_live_validation.py` — integration tests not asserting mutation internals.
- `tests/conftest.py` — fixture setup only.

The implementer must update `test_graphql_helpers.py` and `test_backlog_core_github.py` as part of the change, not treat them as passing unchanged.

---

## 9. Distribution Architecture

This redesign introduces no new Python distribution packages, no new MCP server entry points, and no new plugin manifest entries.

The affected files are all within `plugins/development-harness/backlog_core/` and `plugins/development-harness/sam_schema/core/backends/`. The pre-commit hook in this repository automatically bumps `plugin.json` and `marketplace.json` versions on any commit that changes plugin files. No manual version bump is required.

The `DirtyState` StrEnum and `WriteResult` TypedDict are internal to `backlog_core` — they are not exported in the public API surface. The `performs_remote_sync` Protocol flag is exposed via `BacklogBackend` as an existing Protocol attribute.

**Impact on plugin version**: one version bump via automatic pre-commit hook after the implementing commit. Users must restart their Claude Code session to reload the plugin from cache at the new version.

---

## 10. Architecture Decision Records

### ADR-001: Watermark Storage — Reuse `last_synced` Slot

**Status:** DECIDED

**Context:** The spec requires a per-item stored-remote-watermark field. `BacklogItemMetadata` already has `last_synced` (line 718) and `updated_at` (line 719), both currently unused for conditional sync (RT-ICA Condition 1; fact-checker VERIFIED).

**Decision:** Reuse `BacklogItemMetadata.last_synced` as the stored-remote-watermark. Store the remote `updatedAt` ISO 8601 UTC string from the last successful push or pull. Do NOT add a new field.

**Rationale:** `last_synced` is already semantically named for this purpose; its current value ("" for all legacy items) is the correct default (no watermark stored → always pull on first sync). Adding a new field would require a migration path; reuse avoids that. `updated_at` (line 719) is the local metadata timestamp and must not be conflated with the remote watermark.

**Consequences:** All sync paths that read or write the watermark use `item.metadata.last_synced`. The field docstring must be updated to state its new role explicitly.

---

### ADR-002: Dirty Flag — 3-State `DirtyState` StrEnum

**Status:** DECIDED

**Context:** The lifecycle divergence rules (FR 8) require distinguishing a content-edit dirty (`pending_push=CONTENT`) from a local-closure dirty (`pending_push=CLOSURE`). A bool cannot express this distinction (constraint #2).

**Decision:** Model the dirty state as a `DirtyState(StrEnum)` with three values: `CLEAN=""`, `CONTENT="content"`, `CLOSURE="closure"`. Persist as a plain string in YAML. New field: `BacklogItemMetadata.pending_push: str = ""`.

**Rationale:** `StrEnum` (Python 3.11+) provides both type-safety for in-code comparisons and transparent YAML serialisation as a plain string. The 3-state model directly encodes the lifecycle rules without requiring a separate boolean or enum field for each dimension. Legacy items default to `""` (CLEAN) via Pydantic field default — no migration needed.

**Consequences:** All code that currently checks "is item dirty?" must use `item.metadata.pending_push != DirtyState.CLEAN`. The remote-delete no-op rule checks `item.metadata.pending_push == DirtyState.CLOSURE`.

---

### ADR-003: Outbox — Persisted Dirty Flags as Source of Truth

**Status:** DECIDED

**Context:** RT-ICA Condition 11 (MISSING): no existing outbox infrastructure. Options evaluated: (a) in-memory `asyncio.Queue`; (b) scan dirty files on each reconcile cycle; (c) hybrid.

**Decision:** The outbox source of truth is disk — the set of local YAML files where `pending_push != ""`. The background reconcile loop scans this set at the start of Phase 1 (PUSH). In-process, an `asyncio.Queue` may optionally be used as a wakeup signal to trigger immediate reconcile after a failed write, but the queue is never the authoritative list of dirty items.

**Rationale:** An in-memory queue loses pending pushes on server restart. The feature's central promise is that a local write returning success survives restart. Disk is the only durable store in this architecture; the outbox must derive from it.

**Retry cadence:** Background reconcile runs on the existing `_startup_sync_loop` schedule. The loop re-pushes all dirty items each cycle. No exponential backoff is applied in the initial implementation (per-item error count tracking is a follow-up concern). A push that fails (timeout/error) leaves the item dirty; the next reconcile cycle retries.

**Consequences:** Phase 1 of background reconcile scans the full backlog directory for dirty items. With typical backlog sizes (< 500 items), this is O(n) in directory entries and takes < 1 s. It does not scale linearly with dirty items because scanning is local filesystem, not network.

---

### ADR-004: Offline/Health Detection — First-Call Classification

**Status:** DECIDED

**Context:** Design question 4: how is "offline" determined without an unbounded probe? `probe_backend_status` (gh_client.py:1206) does extra work (issue counts) and should not be on the write hot path.

**Decision:** "Offline" is determined by the first bounded call in the write-through or read path. In `write_through_item`:
1. Issue the watermark-check query (`{number, updatedAt}`) wrapped in `asyncio.wait_for(..., timeout=10.0)`.
2. On `asyncio.TimeoutError`, `GithubException`, or `ConnectionError`: classify as offline. Leave dirty; return `WriteResult(synced=False, dirty=True, ...)`.
3. On success: backend is healthy; proceed with comparison and push.

There is no separate probing step on the write path. `probe_backend_status` remains available for the `backlog_list` response (its current use) but is not invoked during writes or reads.

**Rationale:** Adding a separate probe doubles the round-trip count on every write. The first bounded call already determines reachability. Classification-at-first-call is the established pattern in the codebase (try_get_github uses timeout=10 for the same purpose).

**Consequences:** The first write attempt to a cold offline backend will take up to 10 s before returning the offline result. This is bounded and acceptable. No unbounded probe loop is introduced.

---

### ADR-005: Bounded-Timeout Enforcement — `asyncio.wait_for` at Call Site

**Status:** DECIDED

**Context:** Design question 5: where should timeout enforcement live — transport layer vs operation wrapper?

**Decision:** Timeouts are enforced at the `asyncio.wait_for` call site in `write_through_item` and the background reconcile loop, not inside the transport layer. The timeout values (see §7.1) are parameters to these functions.

**Rationale:** Enforcing at the transport layer (inside `get_github` or `_graphql_request`) would make timeouts invisible to callers and harder to test. Enforcement at the operation wrapper is explicit and observable; test code can patch `asyncio.wait_for` to simulate timeouts.

Per-call values: watermark-check=10 s, push=15 s, pull=15 s, batch=30 s. These values are constants in `operations.py` and `sync_engine.py`, not embedded in the transport.

**Consequences:** `asyncio.to_thread` is used to run synchronous backend methods in the thread pool; `asyncio.wait_for` wraps the `to_thread` coroutine. This is the same shape used by `ArtifactBackend` in `artifact_provider.py`.

---

### ADR-006: Merge Wiring — `merge_item_models` on Genuine Conflicts Only

**Status:** DECIDED

**Context:** Design question 6: `merge_item_models` is currently wired only into `refresh_pull_item` (operations.py:1533). Background sync uses `_overwrite_body_from_github` and `_write_issue_node_to_cache`. The original problem was the background sync overwriting **dirty** items — items with local unpushed changes. The fix is not to merge everywhere; it is to apply the correct function based on dirty state.

**Decision:** Apply `merge_item_models` only on genuine conflicts: `pending_push != ""` AND `remote_updatedAt != stored_watermark`. All other pull paths use `_write_issue_node_to_cache` (overwrite from remote). Specifically:

| Sync path | Local state | Remote state | Action |
|---|---|---|---|
| WRITE path | dirty (`pending_push != ""`) | diverged watermark | `merge_item_models(local, remote)` → push merged result |
| WRITE path | dirty (`pending_push != ""`) | matched watermark | push local (no merge needed) |
| READ path | dirty (`pending_push != ""`) | diverged watermark | `merge_item_models(local, remote)` → persist merged result |
| READ path | not dirty | diverged watermark | `_write_issue_node_to_cache` (overwrite from remote) |
| BACKGROUND Phase 1 | dirty | any | push dirty item; if remote diverged → write-path conflict resolution |
| BACKGROUND Phase 2 | not dirty | diverged watermark | `_write_issue_node_to_cache` (overwrite from remote) |

`_write_issue_node_to_cache` is the correct function for non-dirty items with diverged watermarks. Overwriting is safe when there is no local change to protect. Merging a non-dirty item would discard remote changes (merge keeps local metadata authoritative), causing data loss in the remote→local direction.

`_overwrite_body_from_github` is retained for the explicit `force=True` pull path only (where the caller has explicitly requested an overwrite, bypassing the dirty check).

**Consequences:** `merge_item_models` is invoked in exactly two cases: WRITE-diverge and READ-diverge-when-dirty. All other pull paths remain overwrite-from-remote. The conflict model is unified at the function level — one merge function, one call site pattern — but is not invoked on every pull.

**Why "merge everywhere" is wrong:** A non-dirty item has no local change to protect. `merge_item` keeps local metadata authoritative; merging would drop a remote label/title/state change that triggered the `updatedAt` bump, producing data loss in the remote→local direction. The original bug (background sync overwriting dirty items) is fixed by Phase-1-push-dirty / Phase-2-pull-non-dirty filtering, not by replacing overwrite with merge.

---

### ADR-007: Backend Gating — `performs_remote_sync` Capability Flag

**Status:** DECIDED

**Context:** Design question 7: where does the GitHub-only guard live? Current `_startup_sync_enabled` reads config YAML only and does not check backend type (RT-ICA Condition 3, fact-checker VERIFIED).

**Decision:** Add `performs_remote_sync: bool` to the `BacklogBackend` Protocol. GitHub backend sets True; sqlite/memory/beads set False. All sync entry points check this flag first:

```python
if not get_config().backend.performs_remote_sync:
    return  # or return early WriteResult(synced=False, ...)
```

`_startup_sync_enabled()` is also updated to check this flag before reading the config YAML (see §4.9).

**Rationale:** Capability-flag gating is the existing pattern in the Protocol (`supports_batch_status_fetch`, `supports_batch_issue_update`). Using a flag is consistent with this pattern, avoids isinstance checks (which break if a new backend is added), and keeps the guard at the contract boundary rather than scattered across implementations.

**Consequences:** Any future backend that implements remote sync sets `performs_remote_sync = True` and gains automatic participation in all sync paths. Non-GitHub backends require zero code changes to remain isolated.

---

### ADR-008: Serialisation Primitive — `SyncState.lock` Scope Extension

**Status:** DECIDED

**Context:** Design question 8: how are foreground writes and background reconcile serialised? `SyncState.lock: asyncio.Lock` (sync_state.py:95) already serialises background sync workers. Constraint #4 specifies extending its scope, not adding a second lock.

**Decision:** Extend `SyncState.lock` to cover all GitHub read/write operations in the write-through path. The shape:

```python
state = get_sync_state()
async with state.lock:
    # all GitHub calls here (wrapped in asyncio.to_thread + asyncio.wait_for)
    ...
```

The foreground write (`write_through_item`) acquires the same lock as the background reconcile loop. This serialises them completely — only one actor holds the GitHub call slot at a time.

**Rationale:** The asyncio event loop is single-threaded; `asyncio.Lock` is the correct primitive for serialising coroutines. Adding a threading lock or a second asyncio lock would introduce deadlock risk. Reusing the existing lock maintains one serialisation primitive in the system.

**Important shape note:** `asyncio.to_thread` runs the synchronous backend method in a thread pool thread. The `asyncio.Lock` is acquired in the async layer (event loop) before entering `to_thread`. This means the lock is held while `to_thread` is executing, which is correct — it prevents the background loop from starting a new GitHub call while a foreground write is in flight. No threading lock is introduced.

**Consequences:** Foreground writes and background reconcile are strictly serialised. This may increase latency when background reconcile is holding the lock (up to one reconcile cycle). This is acceptable — durability and consistency outweigh latency for a local cache.

---

### ADR-009: Per-Section vs Whole-Body Watermarking

**Status:** DECIDED

**Context:** Design question 9 and constraint #7. Body sections carry per-section ISO 8601 UTC timestamps via `entry_blocks.py` (fact-checker VERIFIED — ISO 8601 UTC with Z terminator). The whole-item GitHub `updatedAt` is coarse — it bumps on label/comment/assignee/project changes.

**Decision:** Use whole-item GitHub `updatedAt` as the watermark. Do NOT use per-section timestamps for staleness detection in this redesign.

**Rationale:**

1. GitHub does not expose per-section staleness — `updatedAt` is the only remote timestamp available at item granularity.
2. Per-section timestamps are local (written by `entry_blocks.py` when the section is edited locally). Comparing local-section timestamps to a remote watermark conflates two different clocks. The requirement explicitly forbids this (NFR 2: "never a local file mtime or local clock vs a remote timestamp").
3. Per-section timestamps are useful for a different purpose: determining which sections changed in a merge. They may inform `merge_item_models` in a future optimisation (apply per-section merge only to sections whose local timestamp is newer than the last successful pull). This is out of scope for this redesign.

**False-positive reconcile tolerance:** Because `updatedAt` is coarse (label bumps trigger reconcile), some reconcile cycles will fetch and `merge_item_models` an item whose body did not actually change. This is safe — `merge_item_models` is idempotent on identical inputs. The cost is one extra `_fetch_issue_graphql` call; this is bounded and acceptable.

**Per-backend tracking separation (FR 9):** GitHub backend uses `updatedAt` as the sole staleness signal for body content and metadata together. Future backends (e.g. GitLab) may expose per-section timestamps and use them directly — this is a per-backend implementation decision, not a protocol-level requirement in this spec.

**Consequences:** Some reconcile cycles are wasted on label-only changes. This is documented and tolerated. Implementers must not add optimisation that skips a pull (or merge, when dirty) because "only metadata changed" — the pull is cheap and safety matters more than efficiency here.

**DQ-10 resolution note:** Design question 10 (per-backend tracking separation — body-section staleness vs metadata staleness) resolves here. GitHub exposes only one `updatedAt` per item; it bumps on any field change (labels, title, state, body, comments, projects). There is no independent body-section staleness signal available from GitHub. The single `updatedAt` field is used as the sole staleness signal for all change types combined. Future backends that expose per-section staleness may implement finer-grained tracking without changing the Protocol.

---

### ADR-010: Cross-Module API Stability — `_update_issue_graphql` Return Type

**Status:** DECIDED

**Context:** Constraint #5 and RT-ICA Condition 12. `sam_schema/core/backends/github_task.py` calls `_update_issue_graphql` at lines 411, 446, 455, and 564. The current return type is `-> None`. This redesign requires changing it to `-> str`.

**Decision:** Change `_update_issue_graphql` return type from `-> None` to `-> str`. All four call sites in `github_task.py` already discard the return value (bare statement calls). The return type change is **non-breaking** for all four existing consumers.

**Stability boundary:** The parameters of `_update_issue_graphql` must not change. Any change to the parameter list (name, type, position, addition of positional args) would break all four call sites in `github_task.py`. The signature preserves exact parameter compatibility (see §4.1).

**Coordination requirement:** Before merging any implementation that changes `_update_issue_graphql`, verify all four call sites in `github_task.py` (lines 411, 446, 455, 564) still compile cleanly. Add a `# type: ignore` comment removal task if mypy/ty currently suppresses the `arg-type` errors shown in the grep output.

**Consequences:** `_update_issue_graphql` now returns the remote `updatedAt` string. Callers that need the watermark use it; callers that do not need it (all four in `github_task.py`) continue to discard it with no code change required.

---

## 11. Scalability Strategy

### 11.1 Staleness Detection Cost

The watermark-incremental approach replaces N per-item `fetchIssue` calls with one batch `{number, updatedAt}` query. For a 500-item backlog, this reduces background reconcile network cost from 500 GraphQL calls to 1.

Background reconcile only fetches and merges items where `remote_updatedAt != stored_watermark`. On a quiescent backlog (no remote changes), Phase 2 makes 0 pull calls.

### 11.2 Dirty Item Phase 1 Scan

Phase 1 (PUSH dirty items) scans all local YAML files for `pending_push != ""`. This is a local filesystem operation — it does not scale with network latency. Wall time is sub-second for typical backlog sizes (estimate only; not measured).

### 11.3 Push Batching

Individual `updateIssue` mutations are serialised through `SyncState.lock`. For a large outbox (many dirty items), Phase 1 pushes them sequentially — one bounded push per item. This is correct but not maximally efficient.

`_update_issues_graphql_batch` (batched aliased mutations) is available and could be used for Phase 1 when `backend.supports_batch_issue_update = True`. This is a follow-up optimisation outside this redesign's scope. The initial implementation uses serial bounded pushes for correctness simplicity.

### 11.4 Growth Limit

The per-item watermark model is O(1) per item for all operations. As the backlog grows:
- Batch watermark-check query: one GraphQL call regardless of backlog size.
- Phase 1 push: O(dirty items) network calls.
- Phase 2 pull: O(stale items) network calls.
- No operation is O(N) in network calls for a quiescent backlog.

This is a structural improvement over the previous model which was O(N) in push calls and O(N) in pull calls regardless of staleness.

---

## Concerns

The following items are flagged for implementer awareness. They do not block the spec from being actionable but carry acknowledged uncertainty or design gaps.

**UNVERIFIED — `merge_item_models` idempotency on identical inputs (ADR-009):** ADR-009's false-positive-reconcile-tolerance argument rests on the claim that `merge_item_models(item, item)` returns an item equal to `item`. This is stated without a citation or test. Implementers must verify this property before relying on it as a safety guarantee. If the merge function is not idempotent on identical inputs, false-positive reconciles from coarse `updatedAt` bumps could produce unexpected local mutations.

**UNCONFIRMED lifecycle rule — Issue CLOSED remotely, local dirty with content edit (§5.3):** The user confirmed 5 lifecycle cases. The 6th case (remote close + local content-edit) proposes re-opening the issue via a push. This is a product decision with observable user impact (silently overriding a remote close). This row is marked UNCONFIRMED; implementers must seek explicit confirmation before writing this code path.

**Quantitative estimates in §11 are unvalidated:** The statements about sub-second Phase 1 scan time and backlog size assumptions are estimates derived from code inspection, not measurements. They hold for typical backlog sizes but have not been benchmarked. Do not treat them as performance contracts.

**ADR-003 retry cadence is coarse:** The initial implementation retries dirty items every background reconcile cycle with no backoff. If a push fails repeatedly (e.g. network flap), the item is retried on every cycle. Per-item retry-count tracking and exponential backoff are deferred to a follow-up. This is a known limitation of the initial design, not an oversight.

**DQ-10 coverage:** Design question 10 (per-backend body-section vs metadata staleness tracking) is resolved within ADR-009 rather than as a standalone ADR. This deviates from the task's "one ADR per design question" requirement. The resolution is architecturally sound (GitHub exposes only one `updatedAt`; per-section tracking is future-backend work) but is co-located with ADR-009 rather than independently numbered.

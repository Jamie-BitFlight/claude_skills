# Architect Spec: Provider-Neutral Backlog Snapshot Reconciliation

**Tracking:** `claude_skills-7t0`

**Date:** 2026-08-12

**Status:** ACCEPTED

**Supersedes:** [Offline-First with Per-Item Watermarks](./architect-redesign-backlog-github-sync-offline-first.md)

**Evidence:** [Backlog Sync and Pull Trace](./backlog-sync-pull-trace-2026-08-12.md)

## 1. Decision

Replace the separate startup refresh, groomed-content push, and bulk-pull implementations with one
provider-neutral reconciliation capability on remote-capable backends:

```python
class SyncProvider(Protocol):
    def reconcile(self, request: ReconcileRequest) -> ReconcileResult: ...
```

The selected remote backend owns its provider API adapter and private `FileCache`; its `reconcile()`
method delegates classification, merge policy, checkpoint policy, and no-op suppression to
`reconciliation.py`. Existing MCP tools keep their public parameters and result shapes; their
operation-layer functions become thin adapters around this capability.

This architecture replaces the earlier per-item dirty-flag proposal. It adds no second outbox or
parallel local authority: the provider-owned `FileCache` supplies the one durable pending-mutation
queue required for offline writes. Local edits remain protected by a persisted content fingerprint
and the existing entry-aware merge.

## 2. Goals and non-goals

### Goals

- Fetch provider state in bounded batches rather than once per local item.
- Classify unchanged, local-only, remote-only, concurrent, bootstrap, and deleted-provider states locally.
- Avoid provider mutations when the rendered provider body is already correct.
- Preserve local edits with the existing entry-aware merge.
- Keep provider state, labels, and revisions remote-authoritative when reachable, while preserving
  queued offline mutations until acknowledged or resolved.
- Advance global and per-item checkpoints only when their required work is durable.
- Make startup sync a no-op for backends that do not implement the optional sync interface.
- Keep L1-L11 live lifecycle coverage without starting an unrelated production-repository refresh.

### Non-goals

- Changing MCP tool parameters or removing existing result keys.
- Moving explicit status transitions into reconciliation.
- Synchronising comments, milestones, projects, branches, or pull requests.
- Migrating every existing local item before first use.
- Adding a generic pagination or GraphQL abstraction outside the provider adapter.
- Implementing this architecture in this documentation task. Section 12 is the subsequent implementation plan.

## 3. Current constraints

The current code has three independent policies:

- Startup calls `refresh_local_cache_from_github()`, which chooses `_sync_full()` or `_sync_incremental()` and writes
  fetched issues directly into the local cache.
- `sync_items()` creates missing issues, then `sync_push_groomed_content()` renders all groomed linked items and sends
  every generated body. Equality is not checked before mutation.
- `pull_items()` loops over linked local items and `_pull_item()` performs a single-issue fetch for each one.

`GitHubExtras` exposes GitHub and GraphQL details to the operation layer. `metadata.last_synced` is stamped with local
wall-clock time in several paths, so it cannot safely serve as a provider revision. The trace report also identifies a
duplicated local closed-item update sequence between `_reconcile_closed_issues()` and
`_reconcile_single_closed_issue()`.

## 4. Module and seam

### 4.1 External interface

Create `plugins/development-harness/backlog_core/reconciliation.py`. It is an internal engine used by
remote-capable backends. Operations and server callers do not import it, paginate, access cache
paths, render provider queries, classify conflicts, or dispatch mutations.

The optional backend capability is separate from `WorkItemBackend`:

```python
@runtime_checkable
class SyncProvider(Protocol):
    def reconcile(self, request: ReconcileRequest) -> ReconcileResult: ...
```

Place `SyncProvider` in `backlog_core/backend_types.py` and re-export it through
`backend_protocol.py`. Place the Pydantic request and result models in `backlog_core/models.py`.
Provider snapshot and patch models remain internal to remote-provider implementations and the
engine. This keeps dependency direction acyclic:

```text
models <- backend_types <- operations <- server
              ^               |
              |               v
        remote backend -> reconciliation
              |
              +-> provider API adapter
              +-> private FileCache -> yaml_io
```

`GitHubBackend` is the first production implementation. Engine tests use test-local provider and
cache doubles. Memory, SQLite, and Beads backends do not implement `SyncProvider`, instantiate
`FileCache`, or gain stubs or capability flags.

`ProviderItem.body` and `ProviderPatch.body` use the repository's canonical backlog Markdown, not a provider-native
document type. Reconciliation reuses the pure parse, render, and entry-aware merge functions already in
`github_sync.py`; a future provider adapter translates at its edge only if its native representation
differs. The engine receives provider snapshots and logical cache records from the owning backend and
returns classified actions to it. Only the backend's private `FileCache` reads or writes YAML,
checkpoints, artifact content, or queued mutations.

### 4.2 Why this seam is deep

One call replaces the policy now spread across startup refresh, closed-item reconciliation, groomed-body dispatch, and
bulk pull. Provider-specific mechanics remain private, while callers and tests exercise the same reconciliation
interface. Deleting the module would force classification, merge, checkpoint, and failure policy back into every
caller, so the module earns the seam.

## 5. Data contracts

All new persisted or exchanged shapes are Pydantic `BaseModel` subclasses.

### 5.1 Provider models

```python
class ProviderItem(BaseModel):
    provider_id: str
    reference: str
    title: str
    body: str
    state: str
    labels: list[str]
    revision: str
    exists: bool = True


class ProviderSnapshot(BaseModel):
    items: list[ProviderItem]
    sync_started_at: str
    pages_fetched: int = 0


class ProviderPatch(BaseModel):
    provider_id: str
    reference: str
    expected_revision: str
    body: str


class PatchResult(BaseModel):
    provider_id: str
    reference: str
    status: Literal["applied", "conflict", "error"]
    revision: str = ""
    message: str = ""
```

`reference` is the stable user-facing provider reference stored in local metadata. `provider_id` is the provider's
mutation identity. `revision` is an opaque provider value; reconciliation compares it for equality and never parses or
orders it.

`exists=False` is a tombstone emitted only when a targeted lookup conclusively reports that a previously linked item
does not exist. Omission from an incremental snapshot never means deletion.

### 5.2 Request

```python
class ReconcileScope(StrEnum):
    INITIAL = "initial"
    INCREMENTAL = "incremental"
    LINKED = "linked"
    TARGETED = "targeted"


class ReconcileRequest(BaseModel):
    scope: ReconcileScope
    references: list[str] = Field(default_factory=list)
    since: str = ""
    dry_run: bool = False
    force: bool = False
    include_diff: bool = False
```

Invariants:

- `INITIAL` fetches all open provider items and targeted linked local references, including linked closed items.
- `INCREMENTAL` fetches changes at or after `since` and targeted locally dirty references.
- `LINKED` requires the deduplicated references of all selected linked local items.
- `TARGETED` requires exactly one reference.
- `force=True` is valid only for `LINKED` and `TARGETED`; it means provider-to-local overwrite of synchronized content.
- `dry_run=True` performs fetch, classification, render, merge, and diff calculation but no local write, provider patch,
  or checkpoint update.

The adapter is configured with its provider collection, such as a GitHub repository. Provider location is therefore
not part of the reconciliation interface.

### 5.3 Result

```python
class ReconcileResult(BaseModel):
    fetched_pages: int = 0
    fetched_items: int = 0
    local_updates: int = 0
    provider_patches: int = 0
    no_ops: int = 0
    conflicts: int = 0
    failures: int = 0
    deleted_provider_items: int = 0
    changed_references: list[str] = Field(default_factory=list)
    file_paths: dict[str, str] = Field(default_factory=dict)
    diffs: dict[str, str] = Field(default_factory=dict)
    patch_results: list[PatchResult] = Field(default_factory=list)
```

Counts describe completed outcomes, not attempted work. `provider_patches` counts only `applied` patch results.
`conflicts` includes optimistic-precondition conflicts. `failures` includes fetch, local-persistence, and provider errors.
The wrapper maps this result to its existing public keys and emits a compact progress message containing fetched pages,
fetched items, local updates, provider patches, no-ops, conflicts, and failures.

## 6. Checkpoints and fingerprints

Add `sync_fingerprint: str = ""` to `BacklogItemMetadata`.

The fingerprint is SHA-256 over compact, key-sorted JSON for the synchronized `BacklogItem` projection: priority, item
type, body status metadata, added date, description, and structured sections. Provider bodies are parsed into the same
projection before hashing. The artifact manifest copied from `original_body`, provider state/labels/revision, and
local-only metadata are excluded. This prevents a newly fetched provider body from contaminating the calculation of
whether the local item changed.

- `metadata.sync_fingerprint` is the body checkpoint established by the last durable pull, push, or no-op comparison.
- `metadata.updated_at` stores the last observed opaque provider revision.
- `metadata.last_synced` retains its current legacy meaning and is not read by reconciliation. Removing or migrating it
  is separate cleanup.
- `.last_sync` stores the provider snapshot's `sync_started_at` and controls incremental snapshot scope.

No bulk migration is required. A missing fingerprint is a bootstrap conflict: merge local and provider body content,
then establish the first checkpoint only after the required local write and provider patch or equality check succeeds.

## 7. Classification and reconciliation

For each linked local item and matching provider item, compute:

```text
baseline = metadata.sync_fingerprint
local_fp = fingerprint(synchronized_projection(local))
remote_fp = fingerprint(synchronized_projection(parse(provider.body)))
local_changed = baseline is empty or local_fp != baseline
remote_changed = baseline is empty or remote_fp != baseline
```

Provider-owned fields are applied independently of body classification. A revision-only change, such as a label or
state change with an identical body, therefore updates the local provider-owned fields without causing a body merge or
patch.

| State | Condition | Durable action |
| --- | --- | --- |
| Unchanged | Neither body differs from the baseline | Update provider-owned fields or revision only if needed; otherwise no-op. |
| Local only | Local differs; provider body matches baseline | Render the local item and patch only when that body differs from the snapshot. |
| Remote only | Provider differs; local matches baseline | Parse provider body and ask the owning backend to persist it through `FileCache`. |
| Concurrent | Both differ | Apply the existing entry-aware merge; the backend persists it through `FileCache` and patches only if the merged body differs. |
| Bootstrap | No baseline | Treat as concurrent, then establish the first checkpoint. |
| Force pull | `request.force` | Replace synchronized local content from the provider without merging. |
| Remote only item | Snapshot item has no cached linked item | Ask the owning remote backend to create its private cache record. |
| Provider deleted | Targeted tombstone for a linked cached item | Preserve cached content, clear its provider link and sync checkpoints, and report `deleted_provider_items += 1`. |

The deletion policy converts a confirmed remote deletion into a local-only item without data loss. A later explicit
`backlog_sync` may recreate it through the existing missing-issue creation pass. Transient fetch failures never produce
tombstones.

### 7.1 Merge and field ownership

Use the existing `github_sync.merge_item()` entry-aware rules: union one-sided entries, struck entry wins over active,
later strike wins when both are struck, and longer active content wins when both remain active. Do not introduce a
second merge algorithm.

On every provider observation, provider reference, title, state, labels, and revision are remote-authoritative.
Reconciliation only emits body patches. Explicit close, resolve, and status operations continue to own provider state
transitions, so a local content edit cannot reopen a remotely closed issue.

Pull and merge construct the updated item by replacing only synchronized body content and the provider-owned allowlist.
All other local metadata is copied from the existing item. This preserves `plan`, `topic`, `research_first`, `files`,
`suggested_location`, `followup_to`, `layer`, `language`, `stack`, and future local-only fields by default.

### 7.2 No-op suppression

Before adding a `ProviderPatch`, canonicalise line endings and compare the complete rendered body with the snapshot
body. Equal bodies are a no-op, even if a local timestamp changed or the item is groomed. A no-op can establish a
checkpoint after any required local provider-field update succeeds.

## 8. Provider snapshot and patch semantics

### 8.1 GitHub provider API snapshot retrieval

The private GitHub snapshot adapter delegates to bounded helpers in `gh_client.py`:

- List pages use `first: 100`; cursor handling remains inside the adapter.
- Incremental listing uses an inclusive `since` watermark.
- Snapshot results are deduplicated by `(reference, revision)` before return because an item changed at the inclusive
  boundary may appear again.
- Initial scope fetches all open issues, then targeted linked references not already present. It does not list every
  historical closed issue.
- Linked and targeted scopes resolve references through aliased GraphQL queries in bounded batches. They do not call
  `_fetch_issue_graphql()` once per item.
- Targeted not-found results become `exists=False` tombstones. A failed batch raises `BacklogError`; it never returns a
  partial snapshot as complete.
- `sync_started_at` is captured before the first request.

The adapter may issue multiple bounded requests, but the reconciler receives one normalized snapshot and has no cursor
knowledge.

### 8.2 GitHub provider API patch application

The private GitHub patch adapter:

1. Resolves current revisions for the patch references through targeted alias batches.
2. Returns `conflict` without mutation when a current revision differs from `expected_revision`.
3. Sends only precondition-matching, changed bodies through aliased `updateIssue` batches of at most 25.
4. Returns one `PatchResult` per input patch, including the resulting provider revision for successful mutations.
5. Isolates batch errors into per-item `error` results; it does not report a failed patch as applied.

GitHub does not provide an atomic compare-and-swap argument on `updateIssue`; the revision preflight is therefore a
best-effort optimistic guard. The adapter must keep the preflight and mutation adjacent, and a later reconciliation
will detect any race through revision and fingerprint mismatch.

## 9. Cache, queue, and failure rules

- Persist a remote-only or force-pulled cache record before updating its per-item checkpoint.
- For local-only changes, update the checkpoint only after an applied patch or confirmed body equality.
- For concurrent/bootstrap changes, persist the merged cache record first. If the merged body differs remotely, update
  the checkpoint only after its patch applies. A failed patch leaves the merged body dirty by fingerprint mismatch.
- A `conflict` patch result leaves the item checkpoint unchanged and increments `conflicts`; it is retried because its
  local fingerprint still differs.
- An `error` patch result leaves the item checkpoint unchanged and increments `failures`.
- Write `.last_sync = snapshot.sync_started_at` only after a complete snapshot was fetched and reconciliation completed
  with zero failures. Conflicts are processed outcomes and do not block the global watermark because their per-item
  fingerprint remains dirty.
- Any partial snapshot fetch raises and leaves `.last_sync` unchanged.
- Use the existing sync lock to serialize startup, explicit sync-now, `backlog_sync`, and bulk pull reconciliation.
- When the provider is unreachable, the backend atomically updates its cache record and appends a
  pending mutation with a stable idempotency key. A missing cache record returns unavailable data,
  not an empty authoritative result.
- Reconnect replay applies queued mutations against their base revisions. It removes only provider-
  acknowledged entries; conflicts, failures, and unattempted entries after partial replay remain
  durable for the next reconciliation.

## 10. Entry-point mapping

Public MCP parameters and result keys do not change.

### Startup and explicit sync-now

- Before launching a task, `_backlog_lifespan()` checks `isinstance(backend, SyncProvider)`. A non-sync backend starts
  no task, performs no network access, and leaves `SyncState` idle.
- With `.last_sync`, startup builds `INCREMENTAL` using the inclusive watermark plus references whose current local
  fingerprint differs from their checkpoint.
- Without `.last_sync`, or for existing `full_refresh=True`, startup builds `INITIAL`.
- `refresh_local_cache_from_github()` becomes a compatibility wrapper and maps reconciliation counts back to
  `refreshed` and `reconciled` for direct callers.

### `backlog_sync`

- Retain `sync_create_missing_issues()` first.
- Ask the selected backend to reconcile all linked references with `scope=LINKED` and the existing
  `dry_run` value; the backend obtains its current logical records from native storage or private cache.
- Map applied provider body patches to `pushed`; preserve `created`, `pushed`, `dry_run`, `messages`, `warnings`, and
  `errors`.

### `backlog_pull`

- Bulk pull retains P0/P1 missing-issue creation, then asks the selected backend to reconcile all
  candidate linked references in one `LINKED` request. Map synchronized-content updates to `pulled`;
  preserve `skipped`, `total`, `dry_run`, optional `diff`, and output arrays.
- Selector pull resolves one logical/provider reference through the selected backend, issues one
  `TARGETED` request, and preserves `file_path`, optional `diff`, and output arrays during migration.
- `force` is forwarded unchanged. `include_diff` is true only when the existing `diff` parameter is true.

Remove `_sync_full`, `_sync_incremental`, `_reconcile_closed_issues`, `_reconcile_single_closed_issue`,
`sync_push_groomed_content`, `_build_groomed_update_list`, `_dispatch_issue_body_updates`, and the bulk `_pull_item`
loop once wrapper coverage has moved to the reconciler. This also removes the duplicated closed-item write sequence
identified by the trace report.

## 11. Lifecycle test isolation and observability

In `plugins/development-harness/tests/test_live_validation.py`, explicitly patch startup sync off in the class-scoped
`live_items` fixture. Preserve L1-L11:

- L8 calls `backlog_sync` and exercises explicit linked reconciliation.
- L9 calls bulk `backlog_pull` and exercises one targeted-reference snapshot for the fixture's linked items.
- Neither step launches a background initial refresh or lists historical closed issues.

Each reconciliation adds one compact output message with scope and counts. Live L8/L9 assert the scope is `linked`,
the fetched item count is bounded by fixture-linked items, and failures are zero. Adapter tests assert page size,
targeted alias batching, and mutation batch size directly; the live test does not infer transport behaviour from time
alone.

## 12. Subsequent implementation plan

Execute this dependency graph. Tasks on the same row may run in parallel; every edge represents a
real output dependency.

1. **Models and backend capability**
   - Add `sync_fingerprint`, reconciliation request/result models, and the one-method
     `SyncProvider.reconcile()` capability without changing `WorkItemBackend`.
   - Reserve `metadata.updated_at` for the last observed provider revision.
   - Add focused model and runtime protocol tests.
2. **Provider-owned FileCache**
   - Move YAML snapshots, checkpoints, plan/artifact cache records, and the durable pending-mutation
     queue behind `FileCache`.
   - Make cache-record updates plus queue appends atomic; add stable idempotency keys and partial-
     replay retention.
   - Add import-boundary tests proving operations, server, reconciliation, and local backends cannot
     import `yaml_io` or open cache paths.
3. **Deep reconciliation engine**
   - Implement fingerprinting, classification, field ownership, merge, checkpoint policy, result
     counts, dry-run, force, deletion, and failure policy without filesystem access.
   - Test unchanged, local-only, remote-only, concurrent, bootstrap, force, provider deletion, and
     remotely closed/local-content-change behavior with test-local provider and cache doubles.
4. **GitHub backend composition**
   - Construct `FileCache` only for GitHub and compose it with the reconciliation engine behind
     `GitHubBackend.reconcile()`.
   - Implement 100-item snapshot pages, bounded targeted aliases, inclusive-watermark deduplication,
     revision preflight, and at-most-25-item body mutation batches.
   - Test tombstones, no-op omission, offline queueing, idempotent/partial replay, partial fetch
     failure, and patch conflict/error mapping.
5. **Operation, plan, and artifact routing**
   - Replace startup refresh, sync push, bulk pull, and selector pull internals with the selected
     backend's reconciliation capability.
   - Route plans, grooming, artifact manifests, and artifact content through capabilities on the
     configured backend; remove independent artifact/task provider selection and filesystem fallback.
   - Preserve MCP parameters, output keys, dry-run, force, and diff behavior. Delete superseded paths
     only after wrapper tests pass.
6. **Startup gating and progress**
   - Gate lifespan and sync-now on `SyncProvider`; map `ReconcileResult` into `SyncState` and compact
     output messages.
   - Test that Memory, SQLite, and Beads start no sync task, perform no network/cache access, and use
     only native backend storage.
7. **Documentation alignment**
   - Correct current contributor and consumer documents against `backlog_core/ARCHITECTURE.md` and
     mark obsolete storage designs superseded.
   - Classify documents by contributor/developer, installation/configuration/usage, or mixed overview
     frame and remove implementation leakage from consumer documents.
   - Replace deterministic manual parsing, lookup, filtering, addressing, and state-update steps with
     tools where practical.
8. **Lifecycle fixture and acceptance**
   - Disable startup sync explicitly in the live fixture while preserving L1-L11; assert L8/L9 linked
     scope and bounded fetched counts.
   - Run targeted tests, Ruff, ty, affected prek hooks, live lifecycle, and independent verification.

## 13. Acceptance criteria

- Reconciler interface tests cover unchanged, local-only, remote-only, concurrent, bootstrap, force, provider deletion,
  and remotely closed/local-content-change cases.
- Concurrent changes use the existing entry-aware merge, preserve local-only metadata, retain remote state/labels, and
  patch only a differing merged body.
- Equal rendered bodies cause zero provider mutations.
- GitHub list retrieval uses pages of 100, targeted retrieval avoids per-item requests, inclusive duplicates are
  removed, and mutations use batches of at most 25.
- Partial snapshot fetch failure does not advance `.last_sync`.
- Failed patches do not advance item checkpoints and are retried.
- Non-sync backends launch no background task and perform no GitHub access.
- Beads, SQLite, and Memory instantiate no `FileCache`, access no backlog YAML, and route work,
  grooming, plans, and artifacts only through native backend capabilities.
- Offline remote reads return cached data marked stale; missing cache records return unavailable;
  offline writes queue durably and idempotently; conflicts and partial replay retain unapplied work.
- Import-boundary tests reject direct runtime YAML/cache access outside `FileCache` and migration tooling.
- Existing wrapper-level tests pass without MCP parameter or result-shape changes.
- Live L1-L11 completes within the CI timeout, and L8/L9 perform no full historical closed-issue refresh.

## 14. Risks and decisions held

| Risk | Decision |
| --- | --- |
| GitHub mutation preconditions are not atomic | Use adjacent revision preflight, return conflicts, and rely on the next fingerprint comparison to detect races. |
| One failed patch could repeat an inclusive incremental page | Do not advance `.last_sync` on failures; correctness wins, while deduplication and bounded pages cap duplicate processing. |
| Missing fingerprints make first sync ambiguous | Bootstrap through merge, never overwrite, then establish a checkpoint. |
| Remote closed items have local body edits | Keep remote state closed, merge body, and patch body only. |
| Confirmed provider deletion could discard local work | Preserve the file, unlink it, and allow a later explicit sync to recreate the provider item. |
| A new provider exposes different pagination mechanics | Keep cursors, page sizes, identifiers, and mutation batching private to its `SyncProvider` adapter. |

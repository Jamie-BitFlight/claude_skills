# Architect Spec: Provider-Neutral Backlog Snapshot Reconciliation

> **Audience: contributor/developer.** This is the implementation decision record; consumer
> setup, usage, and recovery guidance belong in plugin documentation.

**Bead parent trackers:** `claude_skills-7t0` (decision), `claude_skills-vu8` (initial
implementation), `claude_skills-ece` (review hardening and provider-native CAS)

**Date:** 2026-08-12

**Last updated:** 2026-08-13

**Status:** IMPLEMENTED FOR THE RECONCILIATION AND PROVIDER CONTRACT — remaining migration debt,
maintainability work, and runtime-lifecycle follow-ups are tracked in the live architecture and
section 1.2

**Supersedes:** [Offline-First with Per-Item Watermarks](./architect-redesign-backlog-github-sync-offline-first.md)

**Evidence:** [Backlog Sync and Pull Trace](./backlog-sync-pull-trace-2026-08-12.md)

**Delivery:** [PR #2882](https://github.com/Jamie-BitFlight/claude_skills/pull/2882),
[PR #2884](https://github.com/Jamie-BitFlight/claude_skills/pull/2884), and
[PR #2885](https://github.com/Jamie-BitFlight/claude_skills/pull/2885)

## 1. Decision

Replace the separate startup refresh, groomed-content push, and bulk-pull implementations with one
provider-neutral reconciliation capability on remote-capable backends. The migration gates closed
in PR #2882; sections 1.1 and 12 record the additional correctness scope discovered during review:

```python
class SyncProvider(Protocol):
    def reconcile(self, request: ReconcileRequest) -> ReconcileResult: ...
```

The selected remote backend owns its provider API adapter and private `FileCache`; its `reconcile()`
method delegates pure classification, merge, checkpoint-decision, and no-op policy to
`reconciliation.py`. The backend applies returned persistence actions and checkpoint decisions
through its private cache. Existing MCP parameters retain their meaning and existing result keys remain;
plan create/update add an optional opaque `owner_reference` for non-numeric providers. Their
operation-layer functions become thin adapters around this capability.

This architecture replaces the earlier per-item dirty-flag proposal. Each remote-capable backend's
private `FileCache` owns its cache records, checkpoints, and one durable pending-mutation queue for
offline writes; reconciliation owns no persistence or queue. Cache-record updates and queue appends
are atomic, queued mutations are idempotent, and partial replay retains every unapplied or conflicted
mutation. Local edits remain protected by a persisted content fingerprint and the existing entry-aware
merge.

### 1.1 Delivered scope expansion

The original reconciliation seam exposed dependencies that the nine-node implementation plan did
not model deeply enough. They were required for one configured provider to remain authoritative
under offline operation and concurrent writes, so the implementation expanded into these product
boundaries:

1. **One configured content provider.** Work items, grooming, SAM plans and tasks, dispatch plans,
   artifact manifests, and artifact content route through the selected backend. Memory, SQLite, and
   Beads persist them natively without YAML cache overhead. Remote backends privately compose
   `FileCache`; high-level callers never select a second filesystem, task, artifact, or cache
   provider.
2. **Provider-neutral content identity.** Typed content records distinguish plans, dispatch plans,
   artifact manifests, and artifact bodies. Opaque owner references, stable reassignment identity,
   ownerless discovery, unavailable versus confirmed-not-found reads, stale cache records, and
   durable pending mutations are part of the public provider contract.
3. **Atomic write conditions.** `create_only` and `expected_revision` reach the provider boundary.
   Memory serializes compare-and-write in process; SQLite uses a write transaction; Beads uses a
   workspace-scoped advisory lock; GitHub uses provider-native blob SHA compare-and-swap. Manifest
   publication occurs only after its referenced content is durably readable.
4. **Provider-native GitHub records.** Plans, dispatch plans, artifact manifests, artifact content,
   and work-item heads use compact versioned envelopes beneath `.dh/content/v1/` on the resolved
   default branch. Native records are authoritative; Gist and shared-index data remain read-only
   migration inputs. Discovery is branch-pinned, paginated once, identity-validated, size-bounded,
   traversal-safe, and fail-closed.
5. **Lossless work-item revisions.** Human Issue bodies remain human-owned. Agent-managed bodies use
   validated append-only audit comments plus an issue-bound Contents head. The head SHA is the
   optimistic revision, so concurrent writers may leave audit evidence but exactly one advances and
   only that mutation is checkpointed.
6. **Durable concurrency and replay.** `FileCache` serializes state transactions across threads and
   processes, coalesces pending writes without discarding their base revision, overlays queued work
   items by stable reference, acknowledges exact idempotency keys, retains conflicts and partial
   replay tails, and validates reconnect writes against authoritative provider revisions.
7. **Surface and delivery integrity.** MCP, CLI, startup, scenario, parity, and provider tests moved
   from direct YAML or removed transport helpers to configured-provider behavior. Documentation and
   generated workflow graphs were aligned with logical provider addresses. The branch-transfer
   audit was strengthened so selectively moved work cannot silently lose deleted paths or Git tree
   modes.

The current target module contract and its remaining migration debt are in
[backlog_core/ARCHITECTURE.md](../plugins/development-harness/backlog_core/ARCHITECTURE.md). This
document records the delivered reconciliation/provider decision, its historical baseline, the
implementation graph, and recovery pointers; it does not declare every target-architecture item
complete.

### 1.2 Bead recovery index

These are epic-level parent trackers in the work graph, although their stored Bead types are
`decision`, `feature`, and `task`:

| Tracker | Role | Current state |
| --- | --- | --- |
| `claude_skills-7t0` | Architecture decision and original plan | Closed |
| `claude_skills-vu8` | Initial configured-provider implementation graph | Closed |
| `claude_skills-ece` | Review hardening, atomicity, and provider-native CAS graph | Closed |

Resume from live Bead state rather than this status snapshot:

```bash
bd show claude_skills-7t0
bd show claude_skills-vu8
bd list --all --parent claude_skills-vu8 --limit 0 --no-pager --flat
bd show claude_skills-ece
bd list --all --parent claude_skills-ece --limit 0 --no-pager --flat
```

Two open follow-ups remain under `claude_skills-ece`:

- `claude_skills-ece.66` — extract the existing GitHub orchestration boundaries after native CAS;
- `claude_skills-ece.4` — make Codex subagent MCP sidecar ownership observable and safely reapable.

Inspect only the unfinished frontier with:

```bash
bd list --all --parent claude_skills-ece \
  --status open,in_progress,blocked,deferred --limit 0 --no-pager --flat
```

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

- Removing or changing the meaning of existing MCP tool parameters or result keys.
- Moving explicit status transitions into reconciliation.
- Synchronising comments, milestones, projects, branches, or pull requests.
- Migrating every existing local item before first use.
- Adding a generic pagination or GraphQL abstraction outside the provider adapter.
- Implementing the architecture inside the original decision task. That task deferred delivery to
  `claude_skills-vu8`; section 12 now records the delivered graph and its review expansion.

## 3. Historical baseline constraints (2026-08-12)

At decision time, the code had three independent policies. The delivered implementation replaced
these paths; this section remains only to explain why the reconciliation seam was chosen:

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
checkpoints, artifact content, or queued mutations. Beads, SQLite, and Memory use native storage
only and never instantiate `FileCache` or access backlog YAML.

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
    stale: bool = False
    unavailable_references: list[str] = Field(default_factory=list)
    pending_mutations: int = 0
```

Counts describe completed outcomes, not attempted work. `provider_patches` counts only `applied` patch results.
`conflicts` includes optimistic-precondition conflicts. `failures` includes fetch, local-persistence, and provider errors.
The wrapper maps this result to its existing public keys and emits a compact progress message containing fetched pages,
fetched items, local updates, provider patches, no-ops, conflicts, failures, stale state, unavailable
references, and pending mutations. Existing keys remain; wrappers add `stale`, `unavailable`, and
`pending` so callers never mistake offline cache state for an authoritative empty result.

## 6. Checkpoints and fingerprints

Add `sync_fingerprint: str = ""` to `BacklogItemMetadata`.

The fingerprint is SHA-256 over compact, key-sorted JSON for the synchronized `BacklogItem` projection: priority, item
type, body status metadata, added date, description, and structured sections. Provider bodies are parsed into the same
projection before hashing. The artifact manifest copied from `original_body`, provider state/labels/revision, and
local-only metadata are excluded. This prevents a newly fetched provider body from contaminating the calculation of
whether the local item changed.

- `metadata.sync_fingerprint` is the body checkpoint established by the last durable pull, push, or no-op comparison;
  the remote backend's `FileCache` persists it.
- `metadata.updated_at` stores the last observed opaque provider revision.
- `metadata.last_synced` retains its current legacy meaning and is not read by reconciliation. Removing or migrating it
  is separate cleanup.
- `.last_sync` stores the provider snapshot's `sync_started_at` and controls incremental snapshot scope; the remote
  backend's `FileCache` owns this checkpoint.

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
| Remote only | Provider differs; local matches baseline | Return a local persistence action; the owning backend persists it through its private `FileCache`. |
| Concurrent | Both differ | Apply the existing entry-aware merge; return the local action and provider patch, while the backend persists through its private `FileCache`. |
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

The delivered GitHub adapter does not treat `updateIssue` preflight as an atomic revision boundary.
Human Issue bodies remain the root projection; agent-managed versions use a Contents-CAS head plus
validated audit comments:

1. Resolve the current Issue identity, canonical human body root, and agent-managed head.
2. Reject a patch whose `expected_revision` differs from the authoritative head/root revision.
3. Append a tagged audit comment naming the previous revision and intended content digest.
4. Advance the issue-bound Contents head with the observed blob SHA as the compare-and-swap
   precondition.
5. Use the exact successful Contents write response as the winning revision and return `applied`
   only for that writer. Do not re-read the mutable path after the CAS.
6. On later reads, validate the head's Issue identity, referenced comment, and content digest;
   malformed or altered projections fail closed.
7. Preserve losing comments as audit evidence, return `conflict`, and leave that mutation queued and
   uncheckpointed.

This gives work-item content the same provider-native optimistic concurrency boundary as other
GitHub content without overwriting a human Issue body after a non-atomic preflight.

## 9. Cache, queue, and failure rules (remote backend responsibility)

- The owning remote backend persists a remote-only or force-pulled cache record before updating its per-item checkpoint.
- For local-only changes, update the checkpoint only after an applied patch or confirmed body equality.
- For concurrent/bootstrap changes, persist the merged cache record first. If the merged body differs remotely, update
  the checkpoint only after its patch applies. A failed patch leaves the merged body dirty by fingerprint mismatch.
- A `conflict` patch result leaves the item checkpoint unchanged and increments `conflicts`; it is retried because its
  local fingerprint still differs.
- An `error` patch result leaves the item checkpoint unchanged and increments `failures`.
- The owning remote backend writes `.last_sync = snapshot.sync_started_at` only after a complete snapshot was fetched
  and reconciliation completed with zero failures. Conflicts are processed outcomes and do not block the global
  watermark because their per-item fingerprint remains dirty.
- Any partial snapshot fetch raises and leaves `.last_sync` unchanged.
- Use the existing sync lock to serialize startup, explicit sync-now, `backlog_sync`, and bulk pull reconciliation.
- When the provider is unreachable, the backend's `FileCache` atomically updates its cache record and appends a
  pending mutation with a stable idempotency key. A missing cache record returns unavailable data, not an empty
  authoritative result.
- Reconnect replay applies queued mutations against their base revisions. It removes only provider-
  acknowledged entries; conflicts, failures, and unattempted entries after partial replay remain
  durable for the next reconciliation.

## 10. Entry-point mapping

Existing public MCP parameters retain their meaning. Plan create/update add optional
`owner_reference: str | None = None` for opaque provider identifiers and reject a non-`None` value
together with `issue`; update distinguishes omitted/preserve from explicit empty/unlink, while create
normalizes omitted to unlinked. The existing numeric `issue` input remains supported. Existing result keys retain their meaning; reconciliation adds
the explicit `stale`, `unavailable`, and `pending` keys described in section 5.3.

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

## 12. Delivered implementation graph

The original implementation used this dependency graph. Tasks on the same row ran in parallel; every
edge represented a real output dependency.

```text
1 contracts
├─→ 2 FileCache ─┐
├─→ 3 engine ────┼─→ 4 GitHub composition ─┐
└─→ 5 local providers ─────────────────────┼─→ 6 high-level routing
                                             └───────────────┘
6 routing → 7 lifecycle → 8 documentation → 9 independent acceptance
```

1. **Models and backend capability**
   - Add `sync_fingerprint`, reconciliation request/result models, and the one-method
     `SyncProvider.reconcile()` capability without changing `WorkItemBackend`.
   - Add content list/get/put models and errors, including a typed write request whose optional
     owner field distinguishes preserving, reassigning, and unlinking a plan. Keep plan identity stable by kind/name while
     validating artifact identity as owner namespace plus artifact type and artifact ID.
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
   - Implement fingerprinting, classification, field ownership, merge, checkpoint decisions, result
     counts, dry-run, force, deletion, and failure policy without filesystem access or persistence.
   - Test unchanged, local-only, remote-only, concurrent, bootstrap, force, provider deletion, and
     remotely closed/local-content-change behavior with test-local provider and cache doubles.
4. **GitHub reconciliation and content composition** (depends on 2 and 3)
   - Construct `FileCache` only for GitHub and compose it with the reconciliation engine behind
     `GitHubBackend.reconcile()`.
   - Implement 100-item snapshot pages, bounded targeted aliases, inclusive-watermark deduplication,
     revision preflight, and at-most-25-item body mutation batches.
   - Test tombstones, no-op omission, offline queueing, idempotent/partial replay, partial fetch
     failure, and patch conflict/error mapping.
   - Implement `ContentProvider` on GitHub by privately adapting the existing GitHub plan and
     artifact persistence components plus `FileCache`; support bounded online/offline list/get/put
     and ensure owner, artifact type, and artifact ID all participate in artifact identity.
5. **Local-provider native content capabilities** (depends on 1; parallel with 2 and 3)
   - Implement `ContentProvider` list/get/put operations on Beads, SQLite, and Memory using only
     native storage, including bounded plan discovery and the project-level namespace for unlinked plans.
   - Keep plan identity stable across mutable owner reassignment. Key artifact manifests by owner
     namespace and artifact content by owner namespace plus artifact type and artifact ID.
   - Preserve opaque provider identifiers and return explicit unsupported errors rather than YAML
     or alternate-provider fallback.
6. **Operation, plan, and artifact routing** (depends on 4 and 5)
   - Replace startup refresh, sync push, bulk pull, and selector pull internals with the selected
     backend's reconciliation capability.
   - Route plans, grooming, artifact manifests, and artifact content through capabilities on the
     configured backend; remove independent artifact/task provider selection and filesystem fallback.
   - Preserve existing MCP parameter semantics, output keys, dry-run, force, and diff behavior; add
     the optional opaque plan `owner_reference` input. Delete superseded paths
     only after wrapper tests pass.
7. **Startup gating and progress** (depends on 6)
   - Gate lifespan and sync-now on `SyncProvider`; map `ReconcileResult` into `SyncState` and compact
     output messages.
   - Test that Memory, SQLite, and Beads start no sync task, perform no network/cache access, and use
     only native backend storage.
8. **Documentation alignment** (depends on 7)
   - Correct current contributor and consumer documents against `backlog_core/ARCHITECTURE.md` and
     mark obsolete storage designs superseded.
   - Classify documents by contributor/developer, installation/configuration/usage, or mixed overview
     frame and remove implementation leakage from consumer documents.
   - Replace deterministic manual parsing, lookup, filtering, addressing, and state-update steps with
     tools where practical.
9. **Lifecycle fixture and independent acceptance** (depends on 8)
   - Disable startup sync explicitly in the live fixture while preserving L1-L11; assert L8/L9 linked
     scope and bounded fetched counts.
   - Run targeted tests, Ruff, ty, affected prek hooks, live lifecycle, and independent verification.

Review made the missing atomicity and provider-representation dependencies visible. Delivery
therefore continued through this second graph rather than declaring task 9 sufficient:

```text
9 initial acceptance
└─→ A provider contract review
    ├─→ B local-backend CAS and FileCache transactions ─┐
    ├─→ C content identity/publication ordering ─────────┼─→ E provider-native GitHub CAS
    ├─→ D CLI/MCP/test/document migration ───────────────┘             |
    └─→ F branch-transfer and execution-safety findings ───────────────┤
                                                                      v
                                                       G post-merge acceptance
                                                                      |
                                              ┌───────────────────────┴───────────────────────┐
                                              v                                               v
                                   ece.66 maintainability                          ece.4 runtime lifecycle
```

`A` through `G` are the child work recorded under `claude_skills-ece`. The graph expansion was a
correctness dependency: reconciliation could not claim durable provider authority while writes were
non-atomic, publications could point at missing content, or remote identity/revision semantics were
lossy. The two open leaves do not reopen the delivered provider contract: `ece.66` is a behavior-
preserving extraction and `ece.4` belongs to Codex process ownership rather than backlog storage.

## 13. Acceptance criteria

- Reconciler interface tests cover unchanged, local-only, remote-only, concurrent, bootstrap, force, provider deletion,
  and remotely closed/local-content-change cases.
- Concurrent changes use the existing entry-aware merge, preserve local-only metadata, retain remote state/labels, and
  patch only a differing merged body.
- Equal rendered bodies cause zero provider mutations.
- GitHub list retrieval uses pages of 100, targeted retrieval avoids per-item requests, inclusive duplicates are
  removed, and mutations use batches of at most 25.
- Every configured backend, including GitHub, implements plan and artifact list/get/put before
  independent routing is removed. Two owners may store the same artifact type/ID independently,
  and one owner may store the same artifact ID under different types independently.
- Partial snapshot fetch failure does not advance `.last_sync`.
- Failed patches do not advance item checkpoints and are retried.
- Non-sync backends launch no background task and perform no GitHub access.
- Beads, SQLite, and Memory instantiate no `FileCache`, access no backlog YAML, and route work,
  grooming, plans, and artifacts only through native backend capabilities.
- Offline remote reads return cached data marked stale; missing cache records return unavailable;
  offline writes queue durably and idempotently; conflicts and partial replay retain unapplied work.
- Every provider enforces `create_only` and `expected_revision` atomically at its native write
  boundary; an observed stale revision never overwrites authoritative content.
- GitHub native records use complete, injective logical identity and blob-SHA CAS; branch-pinned
  discovery rejects truncated, malformed, duplicate, oversized, or path/envelope-mismatched data.
- Artifact manifests become visible only after their referenced content is readable, and concurrent
  initial publication produces one winner rather than two acknowledged writers.
- Work-item reconciliation checkpoints only the writer whose issue-bound Contents head advances;
  losing audit comments do not acknowledge or remove its queued mutation.
- Import-boundary tests reject direct runtime YAML/cache access outside `FileCache` and migration tooling.
- Existing wrapper-level tests pass without changes to existing MCP parameter semantics or existing
  result-key meanings; tests also cover opaque plan owners, owner reassignment, and additive
  offline-state keys.
- README and consumer documentation describe logical capabilities and recovery without cache paths,
  provider wire formats, Python module names, or internal call graphs.
- Live L1-L11 completes within the CI timeout, and L8/L9 perform no full historical closed-issue refresh.

## 14. Risks and decisions held

| Risk | Decision |
| --- | --- |
| GitHub `updateIssue` preconditions are not atomic | Keep human Issue bodies as root projections; advance agent-managed bodies through an issue-bound Contents head with blob-SHA CAS and validated audit comments. |
| Repository branch movement races with a content update | Re-read the target after `409` or `422`; return conflict when target identity/revision changed and retry only a bounded unrelated-head race. |
| Native GitHub representation exceeds Contents limits | Reject envelopes above 1 MiB before network I/O; add a new provider representation only when a real larger-content requirement exists. |
| One failed patch could repeat an inclusive incremental page | Do not advance `.last_sync` on failures; correctness wins, while deduplication and bounded pages cap duplicate processing. |
| Missing fingerprints make first sync ambiguous | Bootstrap through merge, never overwrite, then establish a checkpoint. |
| Remote closed items have local body edits | Keep remote state closed, merge body, and patch body only. |
| Confirmed provider deletion could discard local work | Preserve the file, unlink it, and allow a later explicit sync to recreate the provider item. |
| A new provider exposes different pagination mechanics | Keep cursors, page sizes, identifiers, and mutation batching private to its `SyncProvider` adapter. |

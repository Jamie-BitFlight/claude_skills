> **SUPERSEDED — DO NOT IMPLEMENT THIS DESIGN.** Current authority: [`backlog_core/ARCHITECTURE.md`](../plugins/development-harness/backlog_core/ARCHITECTURE.md) and [`architect-backlog-snapshot-reconciliation.md`](./architect-backlog-snapshot-reconciliation.md). Invalid assumption: an **independent artifact/task backend** belongs in the MCP layer.

# Architecture: sam_plan MCP-Native Plan Storage

**Feature**: fix: sam_plan stores task plans as local YAML files violating plan-to-MCP policy
**Issue**: #2509
**Date**: 2026-05-30
**Author**: python3-development:python-cli-design-spec
**Status**: DRAFT

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Module Boundary Contracts and Interface Changes](#module-boundary-contracts-and-interface-changes)
3. [Plan ID ↔ Issue Mapping Design](#plan-id--issue-mapping-design)
4. [Gist Read/Write Strategy per Operation](#gist-readwrite-strategy-per-operation)
5. [Concurrency Model](#concurrency-model)
6. [Failure Propagation Design](#failure-propagation-design)
7. [Backward Compatibility Strategy](#backward-compatibility-strategy)
8. [Acceptance Criteria Check Commands](#acceptance-criteria-check-commands)
9. [Architectural Decisions](#architectural-decisions)

---

## Executive Summary

`sam_plan` currently writes every plan to `~/.dh/projects/{slug}/plan/*.yaml` and registers only a filesystem path pointer in the artifact manifest — no content is uploaded. Plans are therefore unreachable in CI environments, worktree-isolated agents, and fresh checkouts. Every cross-environment SAM operation fails silently.

The fix introduces a **Gist-backed artifact layer on top of `LocalYamlTaskBackend`**: rather than replacing the local backend (which CLI paths and non-MCP callers still use), the MCP server layer gains a mandatory write-through to `artifact_register(content=...)` on create/update, and reads route first through `artifact_read` (Gist) before falling back to local disk. The local YAML store becomes a cache, never the sole source of truth.

Three structural mismatches from the codebase analysis are explicitly resolved:

- **Keying mismatch**: `sam_plan read` is keyed by `plan_id`; `artifact_read` is keyed by `(issue_number, artifact_type)`. A small MCP-native `plan_id → issue_number` registry stored as a GitHub Gist artifact on a sentinel issue resolves the reverse-lookup problem without touching local disk.
- **claim_task atomicity**: Gist blob read-modify-write cannot be made atomic. The `github_task.py` label-swap path already provides atomic, exactly-once claim semantics via GitHub's API. `claim_task` is routed through this path in the multi-agent dispatch scenario; Gist-blob claim is limited to single-writer contexts.
- **Silent fallback**: `_get_artifact_provider()` silently swaps to `LocalFilesystemArtifactProvider` on GitHub failure. Write-path calls must propagate this as a hard error; read-path calls may fall back but must annotate the response to indicate which storage source served the read.

`store_document`/`read_document` and `list_plans` global enumeration are explicitly out of scope for this fix.

## Module Boundary Contracts and Interface Changes

### Current Module Boundary (broken)

```
MCP tool layer (server.py)
    └─ _sam_plan_create()
          └─ LocalYamlTaskBackend.create_plan()  → writes ~/.dh/.../*.yaml
          └─ _try_register_task_plan_artifact()  → artifact_register(path-only)  ← BUG

MCP tool layer (server.py)
    └─ _sam_plan_read()
          └─ LocalYamlTaskBackend.read_plan()  → reads ~/.dh/.../*.yaml  ← BUG: never hits Gist
```

### Target Module Boundary

```
MCP tool layer (server.py)
    └─ GistTaskLayer  (new wrapper — in sam_schema/core/gist_task_layer.py)
          ├─ create_plan()  → LocalYamlTaskBackend.create_plan() + write-through to Gist
          ├─ read_plan()    → artifact_read (Gist-first) → fallback LocalYamlTaskBackend
          ├─ update_plan()  → artifact_read → mutate in memory → write-through to Gist
          ├─ claim_task()   → ROUTES TO claim backend (see Concurrency section)
          └─ [all other mutations] → artifact_read → mutate → write-through to Gist

    └─ LocalYamlTaskBackend  (unchanged — used by CLI, non-MCP callers, and as local cache)

    └─ ArtifactLayer (backlog_core)
          ├─ artifact_register(content=yaml_string)   → writes to Gist via GitHubGistArtifactProvider
          └─ artifact_read(item_id, 'task-plan')      → reads Gist comment (preferred) or local file
```

### Interface Contract: `GistTaskLayer`

New module: `sam_schema/core/gist_task_layer.py`

The `GistTaskLayer` satisfies the `TaskBackend` Protocol. It is the concrete backend the MCP server instantiates by default (replacing direct instantiation of `LocalYamlTaskBackend` in `_get_backend()`). It wraps a `LocalYamlTaskBackend` and an `ArtifactRegistryClient` (new thin wrapper around `artifact_register`/`artifact_read` from `backlog_core`).

**Constructor signature** (type hints only, no implementation):

```python
class GistTaskLayer:
    def __init__(
        self,
        local_backend: LocalYamlTaskBackend,
        artifact_client: ArtifactRegistryClient,
        plan_index: PlanIdIndex,  # see Keying section
    ) -> None: ...
```

**Write-path contract** (applies to: `create_plan`, `update_plan_fields`, `update_task_status`, `update_task_fields`, `update_task`, `append_task`, `finalize_plan`):

1. If operation writes a whole plan blob (create, finalize): serialize full PlanData to YAML string; call `artifact_client.store(issue, yaml_string)`.
2. If operation mutates in-memory (update_* methods): read current blob via `artifact_client.read(issue)`, deserialize, apply mutation, serialize, call `artifact_client.store(issue, yaml_string)`.
3. If `artifact_client.store()` raises any exception: propagate as `ArtifactWriteError` to the MCP response. Do NOT swallow and do NOT fall back to local-only.
4. After successful Gist write: optionally write to local cache (best-effort, failures do not raise).

**Read-path contract** (applies to: `read_plan`, `read_task`, `get_ready_tasks`, `get_plan_status`):

1. Call `artifact_client.read(issue, artifact_type='task-plan')`.
2. If Gist content returned: deserialize YAML, annotate response with `source: "gist"`.
3. If Gist returns nothing (plan predates Gist storage): fall back to `local_backend.read_plan(plan_id)`, annotate with `source: "local"`.
4. If both fail: raise `PlanNotFoundError` — no silent empty return.

**Not implemented in GistTaskLayer** (delegated to out-of-scope):

- `store_document` / `read_document` — still delegates to `LocalYamlTaskBackend`; document portability is a separate issue.
- `list_plans` — delegates to `PlanIdIndex.list_all()` merged with `LocalYamlTaskBackend.list_plans()`; see Mapping section for the merge strategy and enumeration contract.

### Interface Contract: `ArtifactRegistryClient`

New thin wrapper: `sam_schema/core/artifact_registry_client.py`

Decouples `GistTaskLayer` from the full `backlog_core` surface. Uses `backlog_core.ArtifactRegistryClient` (or its MCP tool equivalents) internally.

```python
class ArtifactRegistryClient:
    def store(self, issue: int, content: str) -> None:
        """Upload plan YAML to GitHub Gist via artifact_register(content=...).
        Raises ArtifactWriteError on failure. No silent fallback."""
        ...

    def read(self, issue: int, artifact_type: str = "task-plan") -> str | None:
        """Retrieve plan YAML from GitHub Gist (primary) or local file (fallback).
        Returns None when not found remotely and no local path exists.
        Annotates source in logs."""
        ...
```

### Changed Call Sites in `server.py`

| Location | Current | After Fix |
|---|---|---|
| `_get_backend()` | Returns `LocalYamlTaskBackend` | Returns `GistTaskLayer(local, artifact_client, plan_index)` |
| `_try_register_task_plan_artifact()` | Path-only registration + best-effort content upload | Removed; content upload is now `GistTaskLayer.create_plan()` write-through |
| `_sam_plan_create()` | Calls `_try_register_task_plan_artifact` after backend | No change in caller flow; GistTaskLayer handles upload internally |
| `_sam_plan_read()` | Passes through to backend | No change; GistTaskLayer routes read to Gist |
| Content upload failure | Inner try/except → `_log.warning`, returns | Exception propagates as MCP `warnings` entry or error |

## Plan ID ↔ Issue Mapping Design

### The Keying Mismatch

`sam_plan read` accepts `plan_id` (e.g., `P3e7e163d`). `artifact_read` is keyed by `(issue_number, artifact_type)`. There is no reverse map from `plan_id → issue_number` in any current system component. Additionally, `list_plans` performs global enumeration (`plan_dir/*.yaml`) which has no equivalent in an issue-keyed store.

### Constraint: The Index Must Be MCP-Native

Storing the index only in `~/.dh/` would reintroduce the exact local-only bug. The index must survive a fresh checkout and be readable from CI — it must live in GitHub/Gist, retrieved via the artifact layer.

### Design: `PlanIdIndex` Stored as a Gist Artifact

A new artifact type `"plan-index"` is registered on a **sentinel GitHub issue** whose number is stored in `.dh/config.yaml` under the key `sam.plan_index_issue`. This is a stable, user-configurable issue number (e.g., a permanent "SAM Plan Registry" issue in the repo). It does NOT change between sessions.

**Bootstrapping — unset sentinel issue**: When `sam.plan_index_issue` is not configured (fresh checkout, new project):

1. `PlanIdIndex.resolve(plan_id)` returns `None` — the fallback to local disk activates for reads (backward-compatible).
2. `PlanIdIndex.register(plan_id, issue, slug)` raises `PlanIndexConfigError("sam.plan_index_issue not set in .dh/config.yaml")` — the plan content is still uploaded to Gist on the plan's own issue (step 3 of the create flow), but the plan_id cannot be indexed for reverse lookup. The MCP response includes both the `ArtifactWriteError` warning for the index failure AND a hint: `"Set sam.plan_index_issue in .dh/config.yaml to enable plan_id reverse lookup."` The plan is not lost — it is retrievable via `artifact_read(item_id=issue, artifact_type='task-plan')` even without the index.
3. `PlanIdIndex.list_all()` returns an empty list — `list_plans` falls back to `local_backend.list_plans()` only.

This means a fresh checkout without a configured sentinel has degraded discoverability (no `read_plan(plan_id)` cross-environment resolution), but no data loss. The fix still improves portability for `artifact_read(item_id=issue, ...)` callers (CI and worktree agents that receive the issue number directly).

**Index schema** (YAML blob stored as `artifact_register(item_id=SENTINEL_ISSUE, artifact_type="plan-index", content=...)`:

```yaml
version: 1
entries:
  - plan_id: P3e7e163d
    issue: 2498
    slug: feature-x
    created_at: "2026-05-30T12:00:00Z"
  - plan_id: Pab12cd34
    issue: null          # issue=None plans: local-only, marked non-portable
    slug: local-scratch
    created_at: "2026-05-30T14:00:00Z"
```

### `PlanIdIndex` Interface

New module: `sam_schema/core/plan_id_index.py`

```python
class PlanIdIndex:
    def __init__(self, artifact_client: ArtifactRegistryClient, sentinel_issue: int) -> None: ...

    def register(self, plan_id: str, issue: int | None, slug: str) -> None:
        """Add or update a plan_id → issue mapping. Writes through to Gist.
        Raises ArtifactWriteError on Gist failure.
        If issue is None: records entry with issue=null (local-only)."""
        ...

    def resolve(self, plan_id: str) -> int | None:
        """Return issue number for plan_id. Returns None if not found or issue=null.
        Reads from Gist-first, falls back to local cache."""
        ...

    def list_all(self) -> list[PlanIndexEntry]:
        """Return all registered plan entries. Used by list_plans() to enumerate plans
        that exist on Gist, supplemented by local_backend.list_plans() for unregistered local plans."""
        ...
```

### Registration Flow

When `GistTaskLayer.create_plan(issue=N)` is called:

1. `LocalYamlTaskBackend.create_plan()` creates local YAML, returns `PlanData` with `plan_id`.
2. `plan_index.register(plan_id, issue=N, slug)` writes the new entry to the Gist index.
3. `artifact_client.store(issue=N, content=yaml_string)` uploads plan YAML to Gist.
4. If step 2 or 3 fails: raise `ArtifactWriteError`; do not silently continue.

### Reverse Lookup Flow

When `GistTaskLayer.read_plan(plan_id)` is called:

1. `plan_index.resolve(plan_id)` → returns `issue_number` or `None`.
2. If `issue_number` is not None: `artifact_client.read(issue=issue_number)` → Gist content.
3. If `issue_number` is None (local-only plan) or index has no entry: fall back to `local_backend.read_plan(plan_id)`.
4. If both fail: raise `PlanNotFoundError`.

### `list_plans` Enumeration

`GistTaskLayer.list_plans()`:

1. Call `plan_index.list_all()` — returns all Gist-registered plans.
2. Call `local_backend.list_plans()` — returns all local YAML plans.
3. Merge, deduplicating by `plan_id`. Gist entry takes precedence for any duplicates.
4. Apply search/offset/limit from the original call parameters.

This means `list_plans` is eventually consistent with Gist state, not atomic — acceptable given the single-writer planning pattern.

### Concurrency: Index Registration

The index is a whole-blob read-modify-write. Two concurrent `create_plan` calls could both read the current index, both append an entry, and both write — the slower writer wins and the faster writer's entry is lost. This is acceptable because:

- `create_plan` is a single-agent operation (planning sessions are single-writer per ADR-1770-1).
- The index is not the source-of-truth for plan content; the per-issue artifact is. An entry missing from the index is a discoverability degradation, not data loss.
- A recovery path: if `resolve(plan_id)` returns None but `list_plans` local scan finds a local file, the plan can be re-registered to the index without data loss.

### `create_plan(issue=None)` — Local-Only with Warning

When `issue=None`:

1. `LocalYamlTaskBackend.create_plan()` proceeds normally, creating a local YAML file.
2. `plan_index.register(plan_id, issue=None, slug)` records the entry as local-only.
3. No `artifact_client.store()` call is made (no `item_id` to key the artifact to).
4. The MCP response includes a warning: `"Plan {plan_id} has no associated issue — stored locally only. This plan is not portable across environments and cannot be retrieved from CI or fresh checkouts."`
5. `read_plan(plan_id)` for a local-only plan falls back to local disk immediately (step 3 of reverse lookup above).

This is an explicit, loud non-portability signal — not a silent fallback.

## Gist Read/Write Strategy per Operation

Each `sam_plan` / `sam_task` operation is classified as either **write-through** (must write to Gist) or **read-only** (read Gist-first, local fallback allowed).

### Operation Classification

| Operation | Direction | Gist Strategy | Notes |
|---|---|---|---|
| `create_plan(issue=N)` | Write | Mandatory write-through | Serialize PlanData → YAML → `artifact_client.store(N, yaml)`. Failure raises `ArtifactWriteError`. |
| `create_plan(issue=None)` | Write | Local-only + warning | No Gist key. Explicit warning in MCP response. |
| `read_plan(plan_id)` | Read | Gist-first, local fallback | Resolves `plan_id → issue` via `PlanIdIndex.resolve()`. Fallback to local on miss. Annotate source in response. |
| `list_plans(search, offset, limit)` | Read | Merge Gist index + local | See Mapping section. |
| `update_plan_fields(plan_id, ...)` | Write | Read-modify-write through Gist | Resolve → read → mutate → `artifact_client.store()`. Failure raises. |
| `read_task(plan_id, task_id)` | Read | Via `read_plan` | Subset of plan blob read. |
| `claim_task(plan_id, task_id)` | Write | **See Concurrency section** | NOT a simple Gist blob RMW — routes to atomic claim path. |
| `update_task_status(plan_id, task_id, status)` | Write | Read-modify-write through Gist | Single-writer context assumed. |
| `update_task_fields(plan_id, task_id, fields)` | Write | Read-modify-write through Gist | Same. |
| `update_task(plan_id, task)` | Write | Read-modify-write through Gist | Full task replacement. |
| `append_task(plan_id, task)` | Write | Read-modify-write through Gist | Single-writer (ADR-1770-1 scope confirmed). |
| `finalize_plan(plan_id)` | Write | Read-modify-write through Gist | Single-writer. |
| `get_ready_tasks(plan_id)` | Read | Via `read_plan` | Pure computation on plan blob. |
| `get_plan_status(plan_id)` | Read | Via `read_plan` | Pure computation on plan blob. |
| `store_document` | Write | Local only (out of scope) | Delegates to `LocalYamlTaskBackend`. Document portability is separate. |
| `read_document` | Read | Local only (out of scope) | Delegates to `LocalYamlTaskBackend`. |

### Read-Path Detail: Gist-First with Annotated Source

```
read_plan(plan_id):
  1. issue = plan_index.resolve(plan_id)
  2. if issue is not None:
       a. yaml_str = artifact_client.read(issue, "task-plan")
       b. if yaml_str is not None:
            plan = deserialize(yaml_str)
            plan._source = "gist"
            return plan
  3. plan = local_backend.read_plan(plan_id)   # fallback
     plan._source = "local"
     return plan
  4. if step 3 raises PlanNotFoundError:
       raise PlanNotFoundError(plan_id)  # no silent empty return
```

The `_source` annotation propagates into the MCP response as a `warnings` entry when the source is `"local"`: `"Plan {plan_id} served from local cache — Gist copy may be unavailable or predates this fix."`.

### Write-Path Detail: Mandatory Write-Through

For all write operations (except `claim_task` and `create_plan(issue=None)`):

```
update_task_status(plan_id, task_id, status):
  1. issue = plan_index.resolve(plan_id)   # must succeed
  2. yaml_str = artifact_client.read(issue, "task-plan")   # Gist-first
     if yaml_str is None: yaml_str = local_backend.read_plan_yaml(plan_id)  # fallback
  3. plan = deserialize(yaml_str)
  4. apply mutation: plan.tasks[task_id].status = status
  5. yaml_str = serialize(plan)
  6. artifact_client.store(issue, yaml_str)  # MUST SUCCEED — raises ArtifactWriteError if not
  7. local_backend.write_plan_yaml(plan_id, yaml_str)  # best-effort local cache update, no raise
```

The split between step 6 (hard) and step 7 (best-effort) is the key asymmetry: remote write is mandatory, local cache write is advisory.

### `_try_register_task_plan_artifact` Removal

The current `_try_register_task_plan_artifact` function is **deleted**. Its responsibilities are absorbed:

- **Path registration**: replaced by `plan_index.register()` in `GistTaskLayer.create_plan()`.
- **Content upload**: replaced by `artifact_client.store()` in `GistTaskLayer.create_plan()`.
- **Error swallowing**: eliminated — errors propagate as `ArtifactWriteError`.

The only behavior that must survive: registration does not block plan creation if GitHub is unavailable — but this is now a first-class error surfaced in the MCP response, not a silent warning.

### Silent-Swallow Defect at `server.py:217`

The inner `try/except (BacklogError, OSError)` at line 217 (content upload attempt inside `_try_register_task_plan_artifact`) is **removed with the function**. No replacement inner try/except is introduced.

If the overall artifact write fails (network, Gist API error, GitHub unavailability), `GistTaskLayer` raises `ArtifactWriteError`. The MCP tool handler catches this and returns it as a structured error in the MCP response with a message that includes the reason and instructs the user to retry or check GitHub connectivity. The MCP response does NOT indicate success.

## Concurrency Model

### The Two Concurrency Contexts

SAM plans have two distinct concurrency contexts with different guarantees required:

| Context | Writers | Reads | Required Guarantee |
|---|---|---|---|
| **Planning** (create, append_task, finalize) | Single agent | Single agent | Serialized — ADR-1770-1 holds |
| **Dispatch** (claim_task) | Multiple agents in parallel | Multiple agents | Exactly-once — one task claimed by one agent |

### Planning Context: Single-Writer Assumption (ADR-1770-1)

Operations `create_plan`, `append_task`, `finalize_plan`, and all `update_*` mutations operate under the planning-phase single-writer contract documented as ADR-1770-1. The assumption is that planning is a single-agent activity: one orchestrator creates the plan and appends tasks sequentially within a session.

Under this assumption, Gist blob read-modify-write is safe: there is no concurrent writer, so there is no compare-and-swap race. The `GistTaskLayer` relies on this assumption for all planning-phase writes.

**ADR-1770-1 scope confirmation**: The single-writer assumption covers `append_task`, `finalize_plan`, and all plan-level field updates. It does NOT cover `claim_task` in the parallel dispatch scenario — that requires a separate mechanism (below).

### Dispatch Context: `claim_task` — Exactly-Once Requirement (Implementation Risk)

`claim_task` is invoked by parallel dispatch agents. The `TaskBackend` Protocol guarantees "exactly one of N concurrent claims succeeds." This guarantee cannot be met with a Gist blob RMW (read current status → check not-started → write in-progress), because two agents can read simultaneously, both see `not-started`, and both write `in-progress`.

**Verified code state** (read 2026-05-30, `sam_schema/core/backends/github_task.py:418-426`):

```python
def claim_task(self, plan_id: str, task_id: str) -> bool:
    self._fetch_plan_node(plan_id)
    node = self._find_task_node(plan_id, task_id)
    if _status_from_labels(node["labels"]) != "not-started":
        return False
    repo, _, _ = self._get_repo()
    self._issue_backend.update_task_status(repo, node["number"], "in-progress")
    return True
```

This is a **non-atomic read-then-write**: the label check at line 422 and the mutation at line 425 are separate API calls. Two agents can both pass the `!= "not-started"` check and both execute `update_task_status`, both returning `True`. The exactly-once guarantee is NOT currently implemented.

**Required behavior**: `GistTaskLayer.claim_task()` MUST provide exactly-once semantics for plans with an associated issue. The implementer must choose one of:

1. **GitHub conditional mutation**: If the GitHub GraphQL API surfaces a conditional label mutation (remove label X only if present, returning success/failure atomically), use it. The implementer must verify API availability — GitHub's `addLabels`/`removeLabels` are idempotent and non-conditional as of 2026-05-30; a conditional primitive may not exist natively.
2. **External coordination lock**: Use an external mutex (e.g., a GitHub issue body comment-lock, a Redis lock, or a Gist-based lock file) that serializes claim attempts for a given task. The lock must be acquired before the label check and released after the mutation.
3. **Serialize claim dispatch**: The dispatch loop serializes claim attempts (one at a time, waits for response before sending next). This eliminates the race at the cost of throughput. Acceptable if dispatch sequences are short and claim latency is tolerable.
4. **Accept eventual-consistency with duplicate-work detection**: Accept that two agents may claim the same task, detect duplicate work via idempotent task outputs, and discard the later completion. This degrades the Protocol guarantee and must be explicitly declared as a deviation from the `TaskBackend` contract.

The implementer selects among these options based on GitHub API capabilities at implementation time. **None of these options is prescribed here** — prescribing would require verifying a specific API primitive that is outside this spec's scope.

**Implementation requirement for `GistTaskLayer.claim_task()`**: If the plan has `issue=None`, raise `ConcurrentClaimUnsupportedError` immediately — parallel claim is not safe for local-only plans and no atomic mechanism is available without a GitHub issue to anchor the coordination.

**Implementation risk flag**: This is the highest-risk item in the spec. The implementer must verify that the chosen mechanism provides the required exactly-once guarantee before marking AC3 complete.

### Write-Back After Claim

After a successful `claim_task` (status updated via label swap), the plan YAML in Gist also needs updating so `read_plan()` returns consistent task status. `GistTaskLayer` performs a best-effort write-back to Gist after label-swap success:

1. Read current plan YAML from Gist.
2. Update `tasks[task_id].status = "in-progress"` in memory.
3. Write back to Gist.

If the write-back fails: log a warning (the label is the source of truth for claim status; the Gist blob is a secondary representation). The claim itself is not rolled back.

### Concurrency Summary

| Operation | Mechanism | Guarantee |
|---|---|---|
| `create_plan`, `append_task`, `finalize_plan`, `update_*` | Gist blob RMW | Single-writer (ADR-1770-1 scope) |
| `claim_task` (with issue) | To be determined by implementer — see ADR-2509-3 | Exactly-once REQUIRED; mechanism unresolved |
| `claim_task` (issue=None) | Raises `ConcurrentClaimUnsupportedError` | Explicit error — no silent degradation |
| Plan index registration | Gist blob RMW | Eventually consistent — missing entry is discoverability loss only |

## Failure Propagation Design

### Design Principle: Read/Write Asymmetry

Failure handling is **direction-dependent**:

- **Write failures**: always propagate upward. A write that cannot reach Gist must not silently succeed. The caller must know the plan is not durable.
- **Read failures**: may fall back to local disk, but must annotate the response to indicate which source served the read and why. Silent local reads are not allowed.

This asymmetry prevents two failure modes:

1. "Fake success": plan appears created, but is local-only. User continues, CI fails later.
2. "Brittle reads": local plan from before the fix becomes unreadable due to missing Gist content.

### Error Taxonomy

New exceptions in `sam_schema/core/exceptions.py`:

| Exception | Raised by | Meaning |
|---|---|---|
| `ArtifactWriteError(plan_id, issue, reason)` | `GistTaskLayer` write-path | Gist write failed; plan is NOT stored remotely |
| `PlanNotFoundError(plan_id)` | `GistTaskLayer` read-path | Neither Gist nor local has the plan |
| `PlanIndexError(plan_id, reason)` | `PlanIdIndex` | Cannot register or resolve plan_id in the Gist index |
| `ConcurrentClaimUnsupportedError(plan_id)` | `GistTaskLayer.claim_task` for issue=None | Plan has no issue; atomic claim requires GitHub labels |

### `_get_artifact_provider()` Silent Fallback — Fix Required

The current `_get_artifact_provider()` at `backlog_core/server.py` silently swaps to `LocalFilesystemArtifactProvider` on `GitHubUnavailableError`/`BacklogError`. For plan storage, this is the same bug being fixed.

**Required change**: `ArtifactRegistryClient.store()` must NOT use `LocalFilesystemArtifactProvider` as a fallback for write operations. When `GitHubGistArtifactProvider` is unavailable, `store()` raises `ArtifactWriteError` immediately.

`ArtifactRegistryClient.read()` MAY use `LocalFilesystemArtifactProvider` as a fallback on Gist read failure, with the following conditions:
- The fallback is attempted only when `GitHubGistArtifactProvider.read_artifact_content_from_remote()` returns `None` (not found) or raises a transient error.
- The MCP response includes a `warnings` entry: `"Gist read unavailable — serving from local cache ({path}). Remote store may be unreachable."`
- The fallback is not used when the reason for Gist failure is a configuration error (e.g., `DEFAULT_REPO not set`); that raises `ArtifactWriteError`.

### MCP Response Error Surface

When `GistTaskLayer` raises `ArtifactWriteError`, the MCP tool handler in `server.py` catches it and returns:

```python
{
    "error": "sam_plan create failed: artifact write to Gist unsuccessful",
    "reason": str(exc.reason),
    "plan_id": exc.plan_id,
    "issue": exc.issue,
    "local_path": str(local_path) if local_path else None,
    "hint": "The plan was written to local disk only. Check GitHub connectivity and retry to upload.",
}
```

This is a structured error response, not a success response with a warning field. The MCP caller sees `error` key and knows the plan is not portable.

### The `server.py:217` Inner Try/Except

The inner try/except at line 217 (content upload inside `_try_register_task_plan_artifact`) is removed entirely with the function. No equivalent swallow is introduced in `GistTaskLayer`. The only exception handling in `GistTaskLayer.create_plan()` is:

```
try:
    artifact_client.store(issue, yaml_string)
    plan_index.register(plan_id, issue, slug)
except ArtifactWriteError:
    raise  # propagate to MCP tool handler — never swallow
except PlanIndexError:
    # Index registration failure: plan is stored in Gist but may not be discoverable by plan_id.
    # Warn (not error) because content IS stored — read-by-issue still works.
    warnings.append(f"Plan index registration failed for {plan_id}: {exc}. Plan is stored but may not resolve by plan_id.")
```

The `PlanIndexError` is a partial failure: content is in Gist but `read_plan(plan_id)` may not resolve it. This is treated as a warning rather than an error because the plan content itself is safely stored and recoverable via `artifact_read(item_id=issue, artifact_type="task-plan")`.

### Logging Requirements

All read-path fallbacks must log at WARNING level:

```python
_log.warning("read_plan(%s): Gist content unavailable, serving from local cache at %s", plan_id, local_path)
```

All write-path failures must log at ERROR level before raising:

```python
_log.error("GistTaskLayer: artifact write failed for plan %s issue #%d: %s", plan_id, issue, exc)
raise ArtifactWriteError(plan_id=plan_id, issue=issue, reason=str(exc)) from exc
```

## Backward Compatibility Strategy

### Existing Local Plans in `~/.dh/`

Plans created before this fix exist only on local disk and have no corresponding Gist artifact or plan index entry. The dual-read fallback path in `GistTaskLayer.read_plan()` handles these automatically:

1. `plan_index.resolve(plan_id)` → returns `None` (no index entry exists).
2. `GistTaskLayer` falls back to `local_backend.read_plan(plan_id)`.
3. Plan is returned with `source: "local"` annotation and a warning in the MCP response.

This means existing plans remain readable without migration. No data migration script is required at deploy time.

### Optional One-Time Migration

The spec prescribes (but does not require at launch) a `sam_plan migrate` action that:

1. Iterates all local plans via `local_backend.list_plans()`.
2. For each plan with a non-null `issue`: uploads content to Gist via `artifact_client.store(issue, yaml)` and registers the plan_id in the index.
3. For plans with `issue=None`: skips with a logged warning (these remain local-only by definition).
4. Reports counts: uploaded, skipped, failed.

This is a background task, not a blocking fix requirement. The dual-read fallback is the primary compatibility mechanism.

### `LocalYamlTaskBackend` Retention

`LocalYamlTaskBackend` is NOT removed. It continues to serve:

- CLI paths that do not go through the MCP server (direct backend instantiation in CLI commands).
- Non-MCP callers that construct a backend directly.
- The local read/write cache underlying `GistTaskLayer`.
- Plans created with `issue=None` (local-only plans).
- The `store_document`/`read_document` path (out of scope for Gist migration).

The `_get_backend()` function is modified to return a `GistTaskLayer` wrapping a `LocalYamlTaskBackend` by default in the MCP server context. CLI code that calls `LocalYamlTaskBackend` directly is unaffected.

### `config.yaml` Default Backend

The `.dh/config.yaml` key `task.backend` currently defaults to `local`. After this fix, the MCP server always uses `GistTaskLayer` (which wraps `local`). The config key is not changed — `local` still means `GistTaskLayer(LocalYamlTaskBackend, ...)` in the MCP context. A future config option `task.backend: gist-only` (that raises on all local fallbacks) may be introduced as a strictness mode, but is out of scope here.

### Tool Count Stability

`fastmcp list` tool count is unaffected: no MCP tool is added, removed, or renamed. The `sam_plan` and `sam_task` tool signatures do not change. The internal routing change is invisible to MCP clients.

## Acceptance Criteria Check Commands

All commands must be runnable as written from the repo root with a configured `.dh/config.yaml` and valid GitHub token.

### AC1: `create` stores content in Gist

```bash
# Create a plan for a real issue (use a test issue):
# sam_plan(action='create', issue=2509, slug='test-gist-storage', goal='Verify Gist upload', tasks_yaml='')
# Then in a fresh shell (no ~/.dh state — or use a different machine):
uv run fastmcp call --command "uv run --script plugins/development-harness/scripts/run_sam_server.py" \
  sam_plan '{"action": "read", "plan": "P{plan_id_from_create}"}'
# Expected: plan data returned without any local ~/.dh file present
```

### AC2: `read` works from a fresh environment (no local `~/.dh/` plan file)

```bash
# Simulate fresh environment by removing the local plan file:
rm ~/.dh/projects/*/plan/P{plan_id}.yaml 2>/dev/null || true
uv run fastmcp call --command "uv run --script plugins/development-harness/scripts/run_sam_server.py" \
  sam_plan '{"action": "read", "plan": "P{plan_id}"}'
# Expected: plan returned with source annotation; no PlanNotFoundError
```

### AC3: Mutations persist to Gist (subsequent reads see changes)

```bash
# Claim a task, then read the plan from a fresh session:
# 1. claim_task via sam_task(action='claim', plan=P{id}, task=T1)
# 2. Remove local YAML
# 3. sam_plan(action='read', plan=P{id}) → T1 status must be 'in-progress'
uv run pytest tests_sam/test_gist_write_through.py -q  # new test file
```

### AC4: Existing local plans still readable

```bash
# Create a plan using the old path (by temporarily bypassing GistTaskLayer — see test fixture),
# then read it via the new path:
uv run pytest tests_sam/test_backward_compat_local_plans.py -q  # new test file
```

### AC5: Full test suite passes

```bash
uv run pytest tests_sam/ -q
# Expected: all pass, no new failures
```

### AC6: Tool count unchanged

```bash
uv run fastmcp list --command "uv run --script plugins/development-harness/scripts/run_sam_server.py" | wc -l
# Compare against baseline count recorded before change; must be identical
```

### AC7: Gist write failure surfaces as error (no silent swallow)

```bash
# Set GITHUB_TOKEN to an invalid value, then attempt sam_plan create:
GITHUB_TOKEN=invalid uv run fastmcp call --command "..." sam_plan '{"action":"create","issue":1,"slug":"fail-test","goal":"test","tasks_yaml":""}'
# Expected: response contains "error" key — not a success response with a warning
```

## Architectural Decisions

### ADR-2509-1: Wrapper Layer (GistTaskLayer) vs Full Backend Replacement

**Decision**: Introduce `GistTaskLayer` as a wrapper around `LocalYamlTaskBackend`, not a full replacement.

**Context**: The coverage matrix from the feature-context shows 5 capabilities fully COVERED by Gist-backed RMW, 7 PARTIAL (key-resolution dependent), and 5 MISSING (issue=None, list_plans global enum, claim_task atomicity, documents). A full replacement would require implementing all 17 capabilities on Gist from scratch.

**Rationale**:
- `LocalYamlTaskBackend` is battle-tested, complete, and used by CLI paths.
- CLI/non-MCP callers must not be broken (backward compat constraint).
- The wrapper pattern limits the diff surface to the MCP server layer and the new `GistTaskLayer` class.
- Document portability (`store_document`/`read_document`) and `list_plans` global enum are out of scope; the wrapper can delegate these to `LocalYamlTaskBackend` without changes.

**Alternative considered**: Complete `github_task.py` (issue #984). Rejected because #984 maps plans to GitHub Issues (not Gist artifacts), requires a separate `IssueBackend` protocol, and is a larger scope that could be done in parallel without blocking this fix.

**Consequence**: `LocalYamlTaskBackend` remains in the call path. For CLI callers it is the sole backend. For MCP callers it is a read/write cache behind `GistTaskLayer`.

---

### ADR-2509-2: Gist Sentinel Issue for Plan Index

**Decision**: Store the `plan_id → issue` index as a `"plan-index"` artifact on a configurable sentinel GitHub issue rather than in `~/.dh/`.

**Context**: The index must be MCP-native (not local-only) to survive fresh checkouts. GitHub Issues comments (the artifact store) are keyed by issue number. A per-plan index entry could live on the plan's own issue, but that requires knowing the issue to look up the issue — circular. A global index on one stable sentinel issue breaks the circularity.

**Rationale**:
- The sentinel issue approach mirrors how Gist-based global registries are typically implemented (one stable key for a global manifest).
- The sentinel issue number is stored in `.dh/config.yaml` (`sam.plan_index_issue`), making it explicit and configurable per project without hardcoding.
- Index entries are a small YAML blob; Gist API limits are not a concern.

**Risks**: The sentinel issue is a single point of contention for concurrent plan registrations. Mitigated by: (1) planning is single-writer (ADR-1770-1), so concurrent registrations are an architectural error; (2) a missed registration is a discoverability degradation, not data loss — content is in Gist on the plan's own issue.

**Alternative considered**: Store `plan_id` as part of the `artifact_id` field (e.g., `artifact_id="P3e7e163d"`). Rejected because `artifact_read` resolves by `(issue_number, artifact_type)` — without the issue number there is no lookup key, making a separate index inescapable.

---

### ADR-2509-3: `claim_task` — Exactly-Once Requirement Not Yet Satisfied; Implementation Risk

**Decision**: `GistTaskLayer.claim_task()` MUST NOT use Gist blob RMW for claims, and MUST use an atomic mechanism. The specific mechanism is deferred to implementation because the existing `github_task.py` code does NOT currently provide the required guarantee.

**Context**: The `TaskBackend` Protocol guarantees exactly-once claim (exactly one agent's claim returns True for a given task). Gist blob RMW has no compare-and-swap primitive. The existing `github_task.py:claim_task()` (lines 418-426, read 2026-05-30) performs a non-atomic read-then-write: it reads label status and then issues a separate mutation, with no conditional mechanism between them. Two concurrent agents can both observe `not-started` and both write `in-progress`.

**Required outcome**: The implementer must establish which of the four approaches listed in the Concurrency section (GitHub conditional mutation, external lock, serialized dispatch, or documented deviation) is viable and implement it. The approach is NOT prescribed here because viability depends on GitHub API capabilities that require verification at implementation time.

**Consequence**: Plans with `issue=None` raise `ConcurrentClaimUnsupportedError` from `GistTaskLayer.claim_task()` — local-only plans are not shared between agents and no atomic mechanism is available without a GitHub issue anchor.

**Risk flag**: This item has the highest implementation risk in the spec. Mark as unresolved until the implementer verifies a concrete atomic mechanism. Do not ship without a verified solution.

---

### ADR-2509-4: `create_plan(issue=None)` — Local-Only with Explicit Warning

**Decision**: Plans created without an issue are stored locally only, with an explicit MCP response warning. This is not an error.

**Context**: Forcing every plan to have an issue would be a breaking change — existing workflows create scratch/exploratory plans without issues. The Gist store has no key for an issue-less plan.

**Rationale**: Local-only with a loud warning preserves backward compatibility while clearly communicating the non-portability. The warning message is specific: it names the plan_id, states it is local-only, and explains what that means for CI and cross-environment use.

**Alternative considered**: Hard error on `issue=None`. Rejected as breaking change for exploratory workflows.

---

### ADR-2509-5: Read-Path Fallback Allowed; Write-Path Fallback Prohibited

**Decision**: The read-path (`read_plan`, `read_task`, `get_*`) may fall back to `LocalYamlTaskBackend` when Gist content is absent, annotating the response source. The write-path (`create_plan`, `update_*`, `append_task`) must not fall back — failures surface as `ArtifactWriteError`.

**Context**: This addresses the `_get_artifact_provider()` silent fallback and the `server.py:217` inner try/except.

**Rationale**: Read fallback enables backward compatibility for plans predating this fix (pre-existing `~/.dh/` plans). Write fallback would silently reproduce the bug — a plan that appears to be created/updated but is still local-only. The asymmetry is the correct design: you can safely read from a cache; you cannot safely write only to a cache and call it done.

**Source**: This principle is stated in repo CLAUDE.md: "Graceful degradation that hides whether the primary path works [is prohibited]" — the write fallback hides exactly that.

# Development Harness Backend Providers

This document is the backend contract for the development harness. Configure one
backend for a process. That backend owns work items, grooming, plans, task state,
artifact manifests, and artifact content.

Use provider-neutral MCP or CLI operations after resolving the active backend.
Do not make a consumer choose a second backend for plans or artifacts.

<storage_contract>

## One configured backend

Resolve the active backend in this order:

1. Read `BACKLOG_BACKEND` when it is set.
2. Otherwise read `backlog.backend` from `.dh/config.yaml`, preferring the
   project configuration over the user configuration.
3. Otherwise select `beads` when the project contains the explicit
   `.beads/dh-backend` marker.
4. Otherwise use `github`.

The selected backend is the source of truth for every logical record:

| Record | Owned by the configured backend |
|---|---|
| Work item | Title, description, status, dependencies, labels, comments, and grooming sections |
| Plan | Goal, context, owner reference, task rows, status, and task sections |
| Artifact manifest | Registered artifact identity, status, producer, and revision |
| Artifact content | The bytes or text addressed by an artifact identity |

Use an opaque owner reference when associating a plan or artifact with a work
item. A GitHub issue number is one provider's reference shape, not a universal
plan identity.

</storage_contract>

## SAM Storage Model

Keep coordination and handoff content logically distinct while keeping their
ownership unified:

| Logical object | What it contains | Backend operation family |
|---|---|---|
| Work item | Goal, acceptance criteria, grooming, and lifecycle | `backlog_*` |
| Task | Claimable execution state, dependencies, and evidence | `sam_task` |
| Document | Plan, context, design, validation, or report content | `sam_plan` and `artifact_*` |

This is a domain model, not a permission to select separate stores. The active
backend owns all three object types and resolves their owner references — but
"owns" refers to storage selection, not one shared access protocol. Work
items go through `WorkItemBackend`; plans and tasks go through a separate
`TaskBackend` protocol, concretely implemented by `ContentTaskProvider` as an
adapter over the same `ContentProvider` that `artifact_*` calls use — the
same underlying configured backend, reached through a different interface.
`sam_active_task` primarily routes through a third protocol, `ContextBackend`,
for its session-scoped state. See [AGENTS.md](../AGENTS.md)'s "Plan and artifact
capability boundary" section for the concrete protocol names and file paths.

## CLI vs MCP Capability Surface

The CLI and MCP are two transports over the same configured backend. Use the
surface available to the caller; do not infer a different source of truth from
the transport. Shared logical operations include:

- Work-item CRUD, grooming, comments, status, and closure.
- Plan creation, listing, status, readiness, and finalization.
- Task read, claim, state, and update.
- Artifact registration, listing, metadata, and content reads.

Provider-native operations may be narrower or unavailable on a local backend.
When a capability is unavailable, report the backend response and stop the
dependent step. Do not emulate it with a cache or direct file access.

## Backlog Persistence Boundary

The configured backend is the sole source of truth for backlog records. Remote
provider snapshots and local item files are private `FileCache` records; they
support reconciliation and recovery but do not create a second backlog. Beads,
SQLite, and memory backends read and write their own native state directly and
do not use YAML or a provider cache.

Known gap: `add_item` on `sqlite`/`memory` does not insert a normally-created
item into that backend's native issue table — it is stored only through
`put_work_item`, so a backend-native operation keyed on `issue_number`
(milestone assignment included) cannot find it yet. Tracked as #3365.

<provider_contract>

## Provider behavior

Every selectable backend implements the same logical read, write, list, and
status operations. Provider-native identifiers and transport details stay
inside the selected backend.

| Backend | Durable owner | Cache and availability behavior |
|---|---|---|
| `github` | Remote provider state | Uses a provider-private `FileCache` for item snapshots, content records, revisions, and queued writes. |
| `beads` | Native Beads state through `bd` | Uses no YAML work-item store and no provider cache. |
| `sqlite` | One SQLite database | Uses no YAML work-item store and no separate provider cache. |
| `memory` | The backend process | Uses no YAML work-item store and no separate provider cache; state ends with the process. |

Remote providers use the same `FileCache` contract:

- Read provider state when reachable and refresh the private cache.
- Return a cached record with `stale=true` when the provider is unavailable and
  a cached record exists.
- Return an unavailable error when no authoritative or cached record exists.
- Apply a write immediately when reachable; otherwise persist the write in the
  cache queue and return `pending=true`.
- Derive one stable idempotency key per queued write. Replay queued writes on
  reconnect in order, acknowledge only successful writes, and retain failed or
  conflicting writes for diagnosis and retry.
- Treat the cache as a recovery and performance mechanism. Never treat it as a
  second source of truth or as a fallback backend.

The same rule applies to remote work-item reconciliation: provider snapshots
and local item files are private cache records, while the remote provider owns
the accepted state.

### Capability flags

`WorkItemBackend` declares five class-level capability flags every backend
sets. Callers read a flag before invoking the operation it gates, rather than
probing behavior or catching a stub's exception:

| Flag | Meaning | `github` | `sqlite` | `memory` | `beads` |
|---|---|---|---|---|---|
| `supports_github_extras` | Backend can satisfy `GitHubExtras` — `get_github()` returns a real `Repository`, GraphQL issue/comment/milestone/project operations work. | `True` | `False` | `False` | `False` |
| `supports_branches` | Backend can satisfy `BranchBackend` — integration branch create/merge/delete. | `True` | `False` | `True` | `False` |
| `supports_batch_status_fetch` | Backend implements a real batched status fetch. | `True` | `True` | `True` | `False` |
| `supports_batch_issue_update` | Backend implements a real batched GraphQL update. | `True` | `False` | `False` | `False` |
| `supports_milestones` | Backend implements real `list_milestones`/`create_milestone`/`assign_item_to_milestone` (`require_milestone_support()`, `backlog_core/_capability_gates.py`). Beads has no int-keyed milestone concept (ADR-003) — use its beads-native shadow methods (`list_beads_milestones` etc.) instead. | `True` | `True` | `True` | `False` |

**Flag-first gating rule:** `GitHubExtras` and `BranchBackend` are both
`runtime_checkable` Protocols. `isinstance(backend, SomeProtocol)` checks
method *names* only — a backend can satisfy a Protocol structurally, by
implementing every method (even as a local simulation, as `sqlite` and
`memory` do for `GitHubExtras`), without having the underlying capability.
Gate on the flag first via `require_github_extras()` /
`require_branch_support()` (`backlog_core/_capability_gates.py`), which use
`isinstance` only as a secondary assertion once the flag confirms the
capability is genuinely present. A backend adding one of these protocols must
also set the matching flag `True` — declaring the flag without satisfying the
Protocol raises `UnsupportedBackendCapabilityError` with `protocol_mismatch=True`
(a backend bug), and satisfying the Protocol without setting the flag is
treated as unsupported (the flag getter defaults `False`).

### Milestones

Milestone assignment is one-per-item on every backend: `sqlite`'s
`items.milestone_number` is a nullable FK, and beads' own `parent` field is a
scalar, so an item belongs to at most one milestone. Opening a durable
`sqlite` database created before this contract existed self-migrates on
connect — adds `milestone_number`, backfills it from the deprecated
`item_milestones` join table (lowest milestone number wins when an item had
more than one legacy link), then drops that table. `sqlite`/`memory` order
`list_milestones` by `due_on` then `number`; neither has a priority-ordering
concept.

`beads` sets `supports_milestones = False` (ADR-003 — its milestone IDs are
string nanoids, `MilestoneFullNode.number` is `int`). Use its beads-native
shadow methods instead of the generic Protocol methods:
`list_beads_milestones`/`create_beads_milestone`/`assign_beads_item_to_milestone`,
backed by `bd create --type milestone [--due] [--parent]` and
`bd link --type parent-child` (`bd`'s `--all` flag, not `--status all`, is
what includes closed issues).

### GitHub contract

GitHub stores plans, artifact manifests, artifact content, and dispatch plans as
versioned repository content. Treat each returned revision as opaque: pass it
unchanged on updates so GitHub can reject stale writes. Repository permissions
must allow Contents reads and writes; work-item reconciliation also requires
Issue and comment reads and writes.

The Issue body remains the human-owned work-item root. Reconciliation versions
agent-rendered bodies through a provider-private head plus validated audit
comments. These private records are not available through public content list,
get, or put operations.

Legacy Gist and index records are read-only migration sources. Their first
successful update validates the legacy revision, preserves its owner reference,
and creates the native record atomically. Native records take precedence after
creation. A malformed or truncated native record is an integrity failure; stop
instead of selecting legacy or cached content. A transport outage may return an
explicitly stale private-cache record under the remote-provider rules above.

</provider_contract>

<consumer_workflow>

## Consumer workflow

Agents MUST complete these steps for every backend-backed workflow:

1. Resolve the active backend through the server configuration. Verify the
   response identifies the expected provider before writing.
2. Read and groom work items through `backlog_view`, `backlog_list`, and
   `backlog_groom`. Verify the returned record contains the required sections
   before planning.
3. Create, read, claim, update, and finalize plans and tasks through `sam_plan`
   and `sam_task`. Verify the plan and task reads come from the same owner
   reference as the work item.
4. Register and discover artifacts through `artifact_register` and
   `artifact_list`; read content through `artifact_read`. Verify the manifest
   contains the entry and the read content matches the registered revision.
5. Inspect `stale`, `pending`, and unavailable outcomes. Mark evidence stale,
   report queued writes, or stop the dependent step as required; never report a
   queued write as provider-complete.
6. Close or resolve the work item only after the plan status, artifact reads,
   and required acceptance evidence are complete on the selected backend.

The workflow is complete when one backend owns every work-item, plan, manifest,
and artifact operation and no step depends on a direct cache or filesystem read.

</consumer_workflow>

<configuration_and_troubleshooting>

## Configuration and troubleshooting

Set one backend before starting the MCP server:

```bash
BACKLOG_BACKEND=github uv run --script plugins/development-harness/scripts/run_backlog_server.py
```

Or set the project configuration:

```yaml
backlog:
  backend: sqlite
```

When a response is unexpected, inspect `BACKLOG_BACKEND`, the nearest
`.dh/config.yaml`, and the `.beads/dh-backend` marker in that order. Restart the
server after changing selection. Do not switch providers mid-workflow while a
write is pending.

Handle provider status as follows:

| Result | Required action |
|---|---|
| Reachable | Continue and use returned provider revisions. |
| Stale | Use only for read context; re-read after reachability returns before making a decision. |
| Pending | Report that the write is durably queued; wait for replay acknowledgement before claiming completion. |
| Unavailable | Preserve the error and stop the dependent write or verification step. |

Beads failures identify the missing or unavailable `bd` dependency; they do not
select another backend. Memory state is intentionally ephemeral. SQLite state is
durable only when the caller supplies a persistent database path.

</configuration_and_troubleshooting>

## Related documents

- [Plan and artifact lifecycle](./plan-artifact-lifecycle.md) — creation, mutation, divergence, and completion rules.
- [Backlog item lifecycle](./backlog-item-lifecycle.md) — end-to-end work-item state transitions.
- [Task field reference](../sam_schema/core/models.py) — authoritative field definitions; verify current fields against the active backend contract.

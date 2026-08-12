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
backend owns all three object types and resolves their owner references.

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
- [Task file format](./TASK_FILE_FORMAT.md) — legacy field reference; verify current fields against the active backend contract.

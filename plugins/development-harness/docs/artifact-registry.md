# Artifact Type Registry

The registry of document-artifact types this plugin recognises, and the writer permitted to
register each. This document states the rules that govern the registry. It holds no copy of it.

**The registry itself is [`dh_core/artifact_registry.py`](../dh_core/artifact_registry.py)** — a
tuple of typed rows, one per artifact type an agent may register, carrying that type's permitted
writers, its gate-read flag, and what it holds. Every consumer of the map is Python, so the map is
Python: read it there, and change it there.

Every `artifact_register` call — MCP tool or `artifact register` CLI — must match a row's
`(artifact_type, agents)` pair. Add the row before writing the call.

The registry is not the `ArtifactType` enum, and the two answer different questions — see
[ARCHITECTURE.md](../ARCHITECTURE.md), "Naming", for which question belongs to which. A row's
`artifact_type` field is an `ArtifactType` member, so a row naming a type with no member fails at
import; the reverse does not hold — see "Task plans" below.

## Task plans

`task-plan` is an `ArtifactType` member and a real manifest entry, and it carries no registry row
because no agent may register it. `sam_plan` owns plan content, and SAM's plan store writes the
manifest entry itself under the `gist-task-layer` writer
([sam_schema/core/artifact_registry_client.py](../sam_schema/core/artifact_registry_client.py)).
The entry exists so a worktree-isolated reader can resolve the plan's address; it is not a route an
agent uses.

The capability and the instruction are separate statements, and only the second binds an agent:

- **Capability**: a `task-plan` manifest entry exists, written by the plan store.
- **Instruction**: never call `artifact_register` with `artifact_type="task-plan"`, and never read
  plan content through `artifact_read`. Create, read, and update plans through `sam_plan`, then
  associate the returned logical address with the owning work item through `backlog_update`.

The decomposition-exit gate enforces the instruction structurally: it resolves an `ARTIFACT`
referent against the registry, so a `task-plan#...` referent in a task's instructions does not
resolve and is reported as a finding.

## Ownership rule

`artifact_read(item_id, artifact_type)` with no `artifact_id` sorts every entry of that type by
creation time and returns only the newest, so a read by type alone can address exactly one document.
A gate-read type must therefore have exactly one registering agent — a second writer wins the read
the moment it registers later, and the gate branches on the wrong document with no error. Types
whose `gate_read` is false may have several registering agents for one of two reasons: every
producer re-registers a single shared `artifact_id` and so replaces one entry (`feature-context`,
`architect`), or the type is intentionally multi-entry, so a read by type alone returns only its
newest document and no gate branches on the result (`codebase-analysis`, `research`). Never point a
gate at a multi-entry type, and never add a second registering agent to a gate-read type.

One registering agent is not one entry. `artifact_read` and `artifact_get` both accept an optional
`artifact_id`, and a single agent that registers one entry per reviewed task leaves several under
its own type. A gate-read type whose producer emits more than one entry per work item — today,
`code-review` — must be read by `artifact_id`; the producer names the identifier it used in its
STATUS output so the consumer can address it. Reading such a type by type alone returns whichever
task's document registered last.

## Registration and discovery

**Registration:** Producers call `artifact_register` after creating document-artifact content.
Plans are the exception: `sam_plan` owns plan content and task state, and `backlog_update` stores
only the logical plan association on the owning work item. Never duplicate plan content through
`artifact_register`.

**Consumer discovery:** Consumers (including worktree-isolated agents) call `artifact_list` then
`artifact_read` for document artifacts and `sam_plan` for plans instead of using filesystem access.
The configured backend resolves content for every worktree.

**MCP-native rule for agents:** Agents store document artifacts via `artifact_register` with
`content=` and store plans through `sam_plan`. The configured backend owns persistence and retrieval.
The `Write` tool is permitted only for repo-relative deliverables (source code, tests, documentation
files committed to the repo).

Load the `dh:create-artifact` skill for worked per-type registration examples.

**Prohibited patterns — do not write these in agent instructions or tool calls:**

- Direct filesystem writes for system artifacts — use `artifact_register(item_id=<owner>, artifact_type=<type>, artifact_id=<logical-id>, content=...)` instead
- Direct filesystem reads for system artifacts — use `artifact_read(item_id=<owner>, artifact_type="T0-baseline")` instead
- `artifact_register(...)` without `content=` — identifier-only registration does not persist artifact content

## Adding a type

Adding a document-artifact type is a single edit to Python:

1. Add the member to `ArtifactType` in [backlog_core/models.py](../backlog_core/models.py) — the
   wire contract, and the vocabulary a manifest entry can hold.
2. Add the row to `REGISTRY` in [dh_core/artifact_registry.py](../dh_core/artifact_registry.py),
   naming the agents permitted to register it — unless no agent registers it, in which case the
   enum member is the whole change and the "Task plans" case applies.

The gate accepts the type once the row exists. A row naming a type with no enum member does not
import, so step 1 cannot be skipped.

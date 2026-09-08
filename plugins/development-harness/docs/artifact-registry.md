# Artifact Type Registry

The registry of document-artifact types this plugin recognises, and the writer permitted to
register each. It is a plugin document rather than a contributor document: it ships wherever the
plugin ships, and the decomposition-exit gate reads it at runtime.

The registry is not the `ArtifactType` enum, and the two answer different questions — see
[ARCHITECTURE.md](../ARCHITECTURE.md), "Naming", for which question belongs to which.

## Artifact types and registering agents

This heading and the table under it are located by [dh_core/artifact_registry.py](../dh_core/artifact_registry.py),
the single locator every reader of the registry goes through: the decomposition-exit gate,
`tests/test_artifact_type_ownership_drift.py`, and `tests_sam/test_decomposition_gate.py`. Renaming
the heading, or renaming a column of the table below, fails those readers loudly — change
`REGISTRY_HEADING` or `REQUIRED_COLUMNS` in the same edit.

This table is the complete registry of document-artifact types. Every `artifact_register` call — MCP
tool or `artifact register` CLI — must match a `(Type, Registering agents)` pair listed here. Add the
row before writing the call. The `Registering agents` column holds the value each call passes as
`agent`; the `Gate-read` column marks the types whose read result decides a workflow branch.

| Type | Registering agents | Gate-read | Notes |
|---|---|---|---|
| `feature-context` | `discovery`, `feature-researcher` | no | Discovery document. Each producer re-registers the same `artifact_id`, so the type holds one entry per item. |
| `architect` | `planning`, `context-integration`, `context-refinement`, `{resolved_agent}` | no | Architecture spec. Later stages re-register the same `artifact_id`, replacing the earlier revision rather than adding a sibling; `context-refinement` re-registers under the `artifact_id` its own read returned, appending annotations. |
| `codebase-analysis` | `codebase-analyzer`, `code-review-architecture` | no | Codebase pattern, architecture, testing, convention, and dependency-graph documents. Intentionally multi-entry — one per focus area or diagram. Consumers reach the full set through `artifact_list`. |
| `code-review` | `code-reviewer` | yes | Code review verdict. One entry per reviewed task, so consumers read it by `artifact_id` (`code-review-{task_id}-{slug}`), reported in the reviewer's STATUS output. `complete-implementation` and `forensic-review` branch on `PASS` / `NEEDS-WORK` / `FAIL`. |
| `T0-baseline` | `t0-baseline-capture` | yes | Pre-implementation baseline. `tn-verification-gate` compares final state against it. |
| `TN-verification` | `tn-verification-gate` | yes | Post-implementation verification. `complete-implementation` branches on the verdict. |
| `research` | `swarm-task-planner`, `ecosystem-researcher` | no | Investigation findings, coverage analysis, rationale. Multi-entry — one document per investigation. |
| `audit-report` | `doc-drift-auditor` | no | Documentation drift audit. Never used for a code review verdict. |
| `dispatch-plan` | `dispatch_create_plan` | no | Milestone dispatch plan, registered by the dispatch tool rather than an agent. |

Every type in this table is a member of `ArtifactType` in
[backlog_core/models.py](../backlog_core/models.py); a type here with no member there is registrable
in prose and unreadable at runtime, because the manifest parse drops a row whose stored type does
not resolve to a member. The reverse does not hold — see "Task plans" below.

### Task plans

`task-plan` is an `ArtifactType` member and a real manifest entry, and it is absent from the table
above because no agent may register it. `sam_plan` owns plan content, and SAM's plan store writes
the manifest entry itself under the `gist-task-layer` writer
([sam_schema/core/artifact_registry_client.py](../sam_schema/core/artifact_registry_client.py)).
The entry exists so a worktree-isolated reader can resolve the plan's address; it is not a route an
agent uses.

The capability and the instruction are separate statements, and only the second binds an agent:

- **Capability**: a `task-plan` manifest entry exists, written by the plan store.
- **Instruction**: never call `artifact_register` with `artifact_type="task-plan"`, and never read
  plan content through `artifact_read`. Create, read, and update plans through `sam_plan`, then
  associate the returned logical address with the owning work item through `backlog_update`.

The decomposition-exit gate enforces the instruction structurally: it resolves an `ARTIFACT`
referent against this table, so a `task-plan#...` referent in a task's instructions does not
resolve and is reported as a finding.

### Ownership rule

`artifact_read(item_id, artifact_type)` with no `artifact_id` sorts every entry of that type by
creation time and returns only the newest, so a read by type alone can address exactly one document.
A `Gate-read` type must therefore have exactly one registering agent — a second writer wins the read
the moment it registers later, and the gate branches on the wrong document with no error. Types
marked `no` may have several registering agents for one of two reasons: every producer re-registers
a single shared `artifact_id` and so replaces one entry (`feature-context`, `architect`), or the
type is intentionally multi-entry, so a read by type alone returns only its newest document and no
gate branches on the result (`codebase-analysis`, `research`). Never point a gate at a multi-entry
type, and never add a second registering agent to a `Gate-read` type.

One registering agent is not one entry. `artifact_read` and `artifact_get` both accept an optional
`artifact_id`, and a single agent that registers one entry per reviewed task leaves several under
its own type. A `Gate-read` type whose producer emits more than one entry per work item — today,
`code-review` — must be read by `artifact_id`; the producer names the identifier it used in its
STATUS output so the consumer can address it. Reading such a type by type alone returns whichever
task's document registered last.

### Registration and discovery

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

A new document-artifact type is added in two places, and the gate accepts it only once both are
done:

1. A member of `ArtifactType` in [backlog_core/models.py](../backlog_core/models.py) — the wire
   contract, and the vocabulary a manifest entry can hold.
2. A row in the table above, naming the agent permitted to register it — unless no agent registers
   it, in which case the enum member is the whole change and the "Task plans" case applies.

# ADR-3460-2: Add the missing relations to the ledger, and finish the migration, rather than replace Task and Plan

**Status:** Proposed — authored on `worktree-melodic-plotting-emerson`, not yet reviewed or merged.
See [rules/adr-lifecycle.md](../../../../rules/adr-lifecycle.md).

## Context

This branch explored replacing the plan and task model with a typed multigraph. A displacement
analysis against the code at `2ba1897d` found that most of the proposal re-describes mechanisms
that already exist, and that the branch's real obstacle is elsewhere. It is pinned to that commit
rather than to a date because it is the load-bearing reason not to rebuild, and a reader who wants
to challenge it needs a tree state to re-read; the modules it rests on are named below.

**The agent layer could not reach the ledger.** That is the situation this decision responds to,
and it held at `2ba1897d`, where

```console
$ git grep -ci ledger 2ba1897d -- plugins/development-harness/skills/ plugins/development-harness/agents/ | wc -l
0
```

named no file, while `sam_task` appeared in those directories throughout. Every agent that ran a
task talked to the content store, and the ledger — with leases, attempt budgets, staleness,
conflict-group exclusion, the failure cascade, and a `status` write that refuses to bypass the
state machine — was a store nothing called.

The same command with `8d7af47d` as its revision names 23 files, because the migration decided here
is under way:
orchestrators run `plan import --from content` before dispatching, and that routes subsequent
`plan` commands on the address to the ledger. Plan authoring stays on the content store, and
`sam_schema/server.py`'s `_get_backend` still returns a `ContentTaskProvider` unconditionally, so
every `sam_plan` and `sam_task` MCP call still resolves to the content store rather than the
ledger.

**One motivating defect is fixed in the ledger and live in the store agents use.** The ledger's
`update` reaches only columns whose `set_by` names the event it appends, and its docstring states
why: "moving a task is `dispatch`, `finish`, `state`, `reclaim` or `accept`, each of which runs the
checks and the cascade that `update` does not." The content store's `update` validates the shape of
a patch and writes it, so a status transition performed as a data write is still reachable there.

**Most of the proposed model already exists.** Ordering, mutual exclusion, execution lifecycle,
fan-out, failure cascade, bounded attempts, stall recovery and peer awareness are implemented in
`dh_core/ledger_spec.py` and `dh_core/ledger/`. Guards on edges carrying an actor and a source
citation exist in `docs/graph-schema.md` and are assembled into `docs/dh-workflow-graph.json` —
over the workflow's documentation rather than over a running plan, but the mechanism is built.

## Decision

**Finish the migration so the agent layer reaches the ledger. Add the two relations that are
genuinely absent. Do not replace `Task` and `Plan`.**

Four capabilities in the explored design are not provided today:

- **A DATA relation** from a producing unit to a consuming one. `Task.handoff` and
  `Task.expected_outputs` are serialised by models, writers, backends and readers, and resolved by
  no consumer. This is the absence recorded independently by hand in
  [docs/workflow-multigraph/findings/data-flow-gaps.md](../workflow-multigraph/findings/data-flow-gaps.md).
- **An actor attached to an effect**, so authority is checkable. Effects are gated by command and
  by row state, never by who is calling; `dh_core/ledger_spec.py` states that absence itself.
- **Referent and quote resolution at decomposition exit** — partly built on this branch.
- **A declared type graph**, and the provenance of a runtime insertion.

The first two account for every defect in the data-flow findings. They are additions to the ledger,
not grounds for replacing the models.

### A dependent waits for completion, not for acceptance

If work depends on something, that thing is complete before the dependent starts. Readiness derives
from the status enum and carries no acceptance term: `dh_core/ledger_spec.py`'s
`SUCCESSFUL_DEPENDENCY` is a frozenset over `sam_schema.core.dependencies.SUCCESSFUL_STATUSES`, and
`READY_PREDICATE` in `dh_core/ledger/derive.py` matches each dependency's status against that set.
Acceptance is a separate, later verdict on a task already in a successful status.

The two stores had encoded this differently. The content store's `DependencyGraph.is_ready` tested
`dep_task.status in SUCCESSFUL_STATUSES`; the ledger's predicate read
`dep.accepted = 1 OR dep.status IN (…)`, so a completed dependency could not unblock its dependents
until a review step ran. At `8d7af47d` the ledger imports the same set and the disjunct is gone.

### The orchestrator loop

The orchestrator is the loop. It is not a node in the graph and not a stage the graph reaches; it is
the process that runs for as long as any work is outstanding.

An `Agent()` or `Bash()` call returning is the event. There is no subscription, no queue and no
callback — the return of a launched call is the whole of the notification mechanism.

Parallel workers notify individually, as each one completes. Many nodes are active at once, and the
loop turns on each individual return rather than on the last member of a batch; an orchestrator that
waited for a batch to finish before acting on its first result would serialise work the graph
declared parallel.

On each event the orchestrator consults the CLI for graph state and for the next claimable task.
The CLI holds the scheduling answer; the orchestrator holds no scheduling state of its own.

## Alternatives considered and rejected

**Three peer graphs joined by cross-layer references** — a task lifecycle, a work graph and a
workflow, each a graph of its own. Rejected: there is one graph, and execution state is a property
of a node rather than a graph beside it. Cross-layer references stored as strings with existence
checks reproduced, at the layer boundary, the flattening the work set out to remove.

**Typed descriptors with a producer/consumer compatibility check.** Rejected: an asset moving
between units is expected, not inspected — its shape is the consuming agent's concern. An input
names its producer; the schema question does not arise at decomposition time.

**Expansion as graph mutation** — splicing a node into an edge, re-parenting, cancelling in place.
Rejected in favour of additive growth: a unit that needs to create work emits new work, and nothing
is rewritten underneath what is already running.

**Skill resolution inside the decomposition gate.** Rejected: a skill's availability is a property
of the harness the work runs in, a built-in skill belongs to no plugin directory, and a skill's name
is a frontmatter field rather than its directory. A legitimate instruction would have been reported
unresolved and blocked the task. Skill existence is the acting agent's runtime check.

**A staged migration gated on exit criteria, enforced by a test.** Rejected: the criteria were
invented while writing them rather than required, and a test that read a deliberation document from
disk made that document undeletable. Both are gone.

**A representation compiled above unchanged models.** Rejected when first considered, and the
reasoning holds: it can only carry what the source records carry, so the absent relations would
compile empty. What has changed is that this is no longer an argument for replacement — the two
relations can be added to the records themselves.

## Consequences

The blast radius avoided is the shape of the change, not its size. Replacing `Task` and `Plan`
outright reaches every module that imports the models, each `TaskBackend` provider, the `sam_plan`
and `sam_task` MCP surface, the skill and agent layer that addresses tasks logically, and every
stored plan record. It is a change across the whole system rather than a local one, and that is
what the decision turns on. Anyone who wants the figure for their own tree should search for
`sam_schema.core.models` importers at the commit they care about; a count recorded here would be
the wrong number for that tree.

The migration is the prerequisite either way. A graph built over the content store would inherit an
unfiltered `status` write, so the relations are worth adding only once the agent layer reads and
writes through the store that gates it.

`Task.blocked_by` and `Task.parallelize_with` are declared and copied, never consulted. At
`8d7af47d` they are declared in `sam_schema/core/models.py`, `sam_schema/cli_inputs.py` and
`sam_schema/core/task_backend_types.py`, listed by `sam_schema/writers/yaml_writer.py` and by
`dh_core/ledger_spec.py`'s `TASK_MODEL_FIELDS`, and copied through the `beads`, `github_task`,
`local_yaml` and `memory` providers in `sam_schema/core/backends/`. Running
`rg -n "blocked_by|parallelize_with"` across the plugin at that commit, excluding tests, `docs/`
and `graphify-out/`, returns those declaration and copy sites and nothing else; no scheduler reads
either name, and the ledger's `READY_PREDICATE` gates on `tasks.dependencies` and
`tasks.conflict_group` alone. Removing them removes nothing that runs.

## What is open

Whether a task may carry an acceptance criterion that is judged rather than run. At `8d7af47d`,
`AcceptanceCriterion` in `sam_schema/core/models.py` declares `check_command` as a required field,
so the model has no shape for a criterion that is judged rather than run; `ARCHITECTURE.md`'s
Closure stage asks whether the desired outcomes were met, which is a judgement. If both shapes are
wanted, the second is a gap to fill.

Whether the judgement tier of the decomposition-exit gate is stable enough to block on. An unstable
checker in a blocking gate costs more than the defects it catches, and the measurement that would
settle it — repeated trials over a labelled corpus, reporting verdict stability ahead of accuracy —
has not been made: `ARCHITECTURE.md`'s "The judgement tier blocks, and demotion clears it" says so
itself at `8d7af47d`, `docs/work-ledger/measurements/` at that commit holds only per-harness
capability measurements, and grepping the plugin for `stability` there turns up no corpus, no
trial harness and no results.

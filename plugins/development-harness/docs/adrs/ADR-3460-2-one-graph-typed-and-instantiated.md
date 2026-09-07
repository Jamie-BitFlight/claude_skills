# ADR-3460-2: Add the missing relations to the ledger, and finish the migration, rather than replace Task and Plan

**Status:** Proposed — authored on `worktree-melodic-plotting-emerson`, not yet reviewed or merged.
See [rules/adr-lifecycle.md](../../../../rules/adr-lifecycle.md).

## Context

This branch explored replacing the plan and task model with a typed multigraph. A displacement
analysis against the code, run 2026-09-07, found that most of the proposal re-describes mechanisms
that already exist, and that the branch's real obstacle is elsewhere.

**The agent layer cannot reach the ledger.** `rg -ci ledger` across `skills/` and `agents/` returns
nothing; `sam_task` appears in those directories throughout. `sam_schema/server.py`'s backend
resolution returns a `ContentTaskProvider`. Every agent that runs a task talks to the content
store, and the ledger — with leases, attempt budgets, staleness, conflict-group exclusion, the
failure cascade, and a `status` write that refuses to bypass the state machine — is a store nothing
calls.

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
  [docs/graph-ir/findings/data-flow-gaps.md](../graph-ir/findings/data-flow-gaps.md).
- **An actor attached to an effect**, so authority is checkable. Effects are gated by command and
  by row state, never by who is calling; `dh_core/ledger_spec.py` states that absence itself.
- **Referent and quote resolution at decomposition exit** — partly built on this branch.
- **A declared type graph**, and the provenance of a runtime insertion.

The first two account for every defect in the data-flow findings. They are additions to the ledger,
not grounds for replacing the models.

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

The blast radius avoided, measured 2026-09-06: replacing `Task` and `Plan` outright would move 71
importing files, 7 `TaskBackend` implementations across 10 backend modules, 3 MCP tools, 44 skill
and agent files, and every stored plan record.

The migration is the prerequisite either way. A graph built over the content store would inherit an
unfiltered `status` write, so the relations are worth adding only once the agent layer reads and
writes through the store that gates it.

`Task.blocked_by` and `Task.parallelize_with` are serialised by models, writers, backends and
`cli_inputs`, and consulted by no scheduler. Removing them removes nothing that runs.

## What is open

Whether a task may carry an acceptance criterion that is judged rather than run. The model requires
an executable check command; the workflow's closure stage asks whether desired outcomes were met,
which is a judgement. If both shapes are wanted, the second is a gap to fill.

Whether a dependent waits for a dependency to be `complete` or to be `accepted`. The two stores
disagree today, and the difference is whether work may build on output nobody has reviewed.

Whether the judgement tier of the decomposition-exit gate is stable enough to block on. No stability
measurement has been made, and an unstable checker in a blocking gate costs more than the defects it
catches.

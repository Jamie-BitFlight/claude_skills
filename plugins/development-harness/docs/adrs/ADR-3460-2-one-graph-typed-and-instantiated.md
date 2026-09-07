# ADR-3460-2: One graph, described as types and executed as instances

**Status:** Accepted
**Date:** 2026-09-07
**Issue:** [#3460](https://github.com/Jamie-BitFlight/claude_skills/issues/3460)
**Supersedes:** [ADR-3460-1](./ADR-3460-1-graph-ir-owns-the-unowned-edges-first.md), whose decision rested
on choosing which of three graphs to model. That choice does not exist.
**Related:** Governed by [ASSESSOR-CONTRACT.md](../graph-ir/ASSESSOR-CONTRACT.md), which this ADR
requires be rewritten — its "The layers" and "How they relate" sections state the superseded model.

## Context

ADR-3460-1 modelled the system as a task lifecycle, a work graph and a workflow, joined by string
references and left the choice between them open. The repository owner rejected the premise on
2026-09-07: there is one multigraph, traceable end to end, whose parts loop back, branch on
decisions, and expand as details are needed — and it spans the whole system, from grooming fan-out
and report synthesis through to completion. A model that is not universal across those is not the
model.

Two working systems were offered as reference. The first is the harness this work runs inside: a
Claude Code workflow script declares agents, fan-out with and without a join barrier, guarded loops,
nested sub-workflows, JSON-Schema output contracts, and a resume rule where the longest unchanged
prefix of agent calls is cached while the first changed call and everything downstream re-runs. The
second is n8n, offered as a graph of configurable node templates with conditional data flow between
them, and since read from source (warrants in [CLAIMS-REGISTER.md](../../CLAIMS-REGISTER.md)).

n8n establishes the shape and refutes the checking, and both halves are useful. Its saved workflow
is node instances referencing registered types by identifier, carrying their own parameters — the
type-and-instance split, in production. But its connections carry no payload type, nothing checks
that a producer satisfies a consumer, and no pre-execution check of graph well-formedness exists;
branch conditions are evaluated inside a node's own code, so which outgoing edge is ever live
depends on interpreting arbitrary user expressions and cannot be read off the connection graph at
all. That is the concrete cost of putting the decision in the node rather than on the edge, observed
in a mature system rather than argued from first principles, and it is why this ADR puts guards on
edges.

## Decision

**One graph. It is described as node types and their permitted relations, and executed as instances
conforming to that description.**

The following follow from it, and each was a distinction the superseded model got wrong:

**Execution state is a property of a node, not a graph.** A status is not a thing on the path from
grooming to completion. `ledger_spec.TRANSITIONS` is the lifecycle an instance runs through, and the
ledger is the instance store. This is why the superseded criterion 3 — that a control-flow
projection reproduce `TRANSITIONS` exactly — was not merely unmet but ill-posed.

**The actor is an attribute of a node, not the node.** Two dispatches of one specialist are two
nodes. Keeping the actor on the node is what makes "does this node's actor hold authority for this
effect" answerable, and projecting it away is how a command came to write a judge's verdict with
nothing to check it against.

**Every relation is an edge.** A relation stored as a string attribute with an existence check is
the flattening this work exists to remove, and the superseded model reproduced it at its own layer
boundaries.

**Containment and precedence are different relations.** The node an expansion came from is
single-valued and gives the hierarchy. What fed a node is many-valued, because a synthesis step has
several inputs by definition. One parent field models the first and destroys the second.

**Guards belong on edges, over a node's declared output.** A node that names its own successor puts
the branch decision inside a model's output, where guard totality and overlap cannot be asked. The
contract already requires those be reportable.

**Expansion is instantiation of declared types, and this is what keeps a dynamic graph checkable.**
Fan-out, decomposition, splitting a task that will not fit one context, and inserting a finding
discovered mid-work are one operation. Because what they instantiate is declared, the type graph
stays finite and checkable ahead of any run, and a check that holds over types holds over every
instantiation. Generation of a node of no declared type is the case that breaks the analysis, and it
is now mechanically detectable rather than a judgement.

**Graph mutation is an effect requiring authority.** A decomposer may rewrite the graph; a worker
may record what it found. Ungated mutation is `update --set status=complete` again — a control
transition performed as a data write.

**Removal is an invalidation cascade, not an operation.** What consumed a removed node's output now
rests on nothing. The workflow resume rule computes exactly this as downstream reachability from a
changed node.

**An instance references its type rather than copying it,** so a type changing under existing
instances is detectable as drift instead of diverging silently.

## Consequences

Type-level and instance-level checks are different questions and must not be reported alike. Whether
a producing type can ever satisfy a consuming type is answerable before anything runs, and is where
the decomposition-exit gate belongs. Whether a particular node received what it needed is answerable
only from a run, and an unfed input there may be a guard that legitimately did not fire.

Carried forward from the superseded ADR: the defects in its Context, and its rejection of a
representation compiled above unchanged models — one that cannot express authority cannot find the
defect class that motivated the work. Its staged A/B/C placement is withdrawn, because each option
was worded in terms of the layer split.

Withdrawn: the migration trigger's criterion that a projection reproduce `TRANSITIONS`, per the
Decision above. `tests_sam/test_adr_3460_migration_trigger.py` enforces the superseded criteria and
must be reworked against this ADR.

Deleted: the layer split in `dh_core/graph_ir/` — its layer discriminator, the per-layer node and
edge modules, the composite that bound them, and the separate decomposition-input type. The node
record, the edge types, the descriptor facets, the finding record with its severity rule, and the
decomposition-exit gate survive, because none of them depended on there being several graphs.

## What is open

The node record's fields and the edge type set are under adversarial test and are not settled here;
an ADR records the decision, not the schema.

Type-level checking has no precedent to borrow. n8n does not do it, and the one validation layer it
has answers activation readiness rather than graph well-formedness. So the checks this design wants
are ours to build, and the absence of a mature implementation to copy is itself worth knowing before
estimating the work.

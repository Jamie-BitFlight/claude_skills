# ADR-3460-2: One graph, described as types and executed as instances

**Status:** Proposed — authored on `worktree-melodic-plotting-emerson`, not yet reviewed or merged. See [rules/adr-lifecycle.md](../../../../rules/adr-lifecycle.md).
**Date:** 2026-09-07
**Issue:** [#3460](https://github.com/Jamie-BitFlight/claude_skills/issues/3460)
**Replaces:** the withdrawn draft ADR-3460-1 ("The graph IR first owns the edge types nothing
owns..."), deleted per [rules/adr-lifecycle.md](../../../../rules/adr-lifecycle.md) — an ADR on an
unmerged branch is `Proposed`, was never reviewed or merged, and may be withdrawn and deleted
rather than superseded. Its decision rested on choosing which of three graphs to model; that
choice does not exist. Its defects, measurements, and its rejection of a representation compiled
above unchanged models are carried forward below, in "Carried forward from the withdrawn draft".
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

Carried forward from the withdrawn draft: the defects in its Context, and its rejection of a
representation compiled above unchanged models — one that cannot express authority cannot find the
defect class that motivated the work. See "Carried forward from the withdrawn draft" below for the
full content, inlined because the draft that recorded it has been deleted. Its staged A/B/C
placement is withdrawn, because each option was worded in terms of the layer split.

Withdrawn: the migration trigger's criterion that a projection reproduce `TRANSITIONS`, per the
Decision above. `tests_sam/test_adr_3460_migration_trigger.py` enforces the superseded criteria and
must be reworked against this ADR.

Deleted: the layer split in `dh_core/graph_ir/` — its layer discriminator, the per-layer node and
edge modules, the composite that bound them, and the separate decomposition-input type. The node
record, the edge types, the descriptor facets, the finding record with its severity rule, and the
decomposition-exit gate survive, because none of them depended on there being several graphs.

## Carried forward from the withdrawn draft

ADR-3460-1 recorded defects and measurements that motivated this work and hold independent of
which graph model is chosen. They are inlined here because that draft was withdrawn as an
unreviewed proposal (`rules/adr-lifecycle.md`) and its file deleted, and the findings under
[docs/graph-ir/findings/](../graph-ir/findings/) cite it as the authority they were scored against
(see `docs/graph-ir/findings/AMENDMENTS.md` for how those citations are now read).

**The flattening, measured 2026-09-06.** The plan and task graph encodes relationships as node
attributes: `dependencies` is CONTROL, `conflict_group` is STATE mutual exclusion,
`is_bookend`/`bookend_type` is EVIDENCE. A grep of `dh_core`, `sam_schema` and `backlog_core`
excluding tests, run 2026-09-06, found `blocked_by` and `parallelize_with` read only by models,
writers, backends and `cli_inputs` — serialized everywhere, deciding nothing. AUTHORITY, DATA,
ERROR, RECOVERY and INVALIDATES had no representation at all.

**The defects that trace to it.** Defects found on the branch trace to that flattening. Two of
them were fixed as separate bugs when they are one authority defect: `import` writing a judge's
`accepted` over a runner's `complete`, and `update --set status=complete` performing a control
transition as a data write. The other two are a DATA edge missing (`FILES_CHANGED` overlap is
prose a judge must eyeball) and an INVALIDATES edge missing (`--replace` deleting rows no event
accounted for).

**Why a representation compiled above unchanged models (scenario B) was rejected.** ADR-3460-1
considered representing the missing relations as a layer compiled above the unchanged `Task`/`Plan`
models, rather than owning them where the harness already stores state. That alternative was
rejected outright, at either stage of the staged plan it was weighed against: a representation
compiled above unchanged models can only carry what the source records carry, and AUTHORITY, DATA,
EVIDENCE, ERROR, RECOVERY and INVALIDATES would compile empty from the current models — it answers
the structural questions that were not hurting and stays silent on the semantic class that was. A
representation that cannot express authority cannot find the defect class that motivated the work.

**The blast radius of replacing `Task`/`Plan` outright, measured 2026-09-06.** Replacing them with
the IR directly — rather than first owning the unrepresented relations alongside them — would move
71 importing files, 7 `TaskBackend` implementations across 10 backend modules, 3 MCP tools, 44
skill and agent files, and every stored plan record. That cost is why ADR-3460-1 staged the work
rather than attempting a full replacement in one change. This ADR does not revisit whether or when
a full replacement is warranted — only which graph is being modelled in the meantime, which the
staged plan had left unresolved.

## What is open

The node record's fields and the edge type set are under adversarial test and are not settled here;
an ADR records the decision, not the schema.

Type-level checking has no precedent to borrow. n8n does not do it, and the one validation layer it
has answers activation readiness rather than graph well-formedness. So the checks this design wants
are ours to build, and the absence of a mature implementation to copy is itself worth knowing before
estimating the work.

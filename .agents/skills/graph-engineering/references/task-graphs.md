# Task Graph Engineering

Use a task graph to model work whose dependencies, concurrency, joins, failure behavior, or approval boundaries matter. The graph is a semantic execution contract; a diagram or runtime-specific scheduler is only a projection of it.

## Node contract

For each independently executable node, resolve only the fields that affect execution:

- **purpose** — observable outcome the node owns;
- **requires** — input artifacts, facts, state, or capabilities needed before start;
- **produces** — output artifacts, facts, state changes, or decisions downstream nodes consume;
- **dependencies/readiness** — which predecessor outputs must exist before start;
- **owner/capability** — executor requirements when assignment affects correctness;
- **resources/side effects** — exclusive files, environments, credentials, devices, or irreversible actions;
- **success condition** — evidence that makes the node complete;
- **failure policy** — retry, skip, compensate, escalate, or stop where failure behavior matters.

Do not invent fields that cannot change execution.

## Edge contract

Draw an edge only when the consumer requires something produced or established by the predecessor. Record the payload or state dependency when it matters; an edge is not merely "happens after."

Before keeping an edge, ask:

1. What does the downstream node consume from upstream?
2. Would starting downstream before upstream completes violate a requirement?
3. Is the dependency data flow, shared mutable state/resource ownership, approval, or merely historical ordering?

Delete incidental ordering. Keep resource conflicts explicit even when no data flows between the nodes.

## Recover the graph

1. Identify observable terminal outcomes and externally imposed constraints.
2. Decompose only until each node has one resolvable responsibility and completion condition.
3. Record node inputs/outputs and derive edges from real consumption or resource constraints.
4. Find ready nodes: all required predecessors satisfied and required resources available.
5. Identify joins explicitly: a join waits only for the predecessors whose outputs it consumes.
6. Add failure/recovery and human approval edges where their absence could make execution unsafe or ambiguous.
7. Validate the graph against representative success, failure, and interruption scenarios before projecting it into a runtime.

## Concurrency and the diamond

Independent ready nodes may run concurrently. A common pattern is fan-out → verification/join → merge, but use it only when the work actually decomposes that way.

A verifier should be independent of the producer when producer self-review has an unacceptable blind spot. The verification depth should scale with consequence, uncertainty, and error detectability; do not require a separate verifier for every trivial node.

One actor owns each merge decision. If workers mutate shared artifacts, model ownership or serialization explicitly rather than assuming parallel writes will reconcile.

## Readiness, barriers, and waves

Prefer readiness based on each node's actual dependencies. Retain a barrier only when a downstream node genuinely consumes the complete set of prior outputs or an external contract requires synchronized progression.

Waves are a useful runtime projection of a DAG, not necessarily the semantic model. Do not add dependencies merely to make a wave schedule convenient.

## Failure and recovery

Model failure behavior where recovery cannot safely be improvised.

For consequential nodes, decide:

- what constitutes failure or lost execution state;
- whether retry is safe and what state must be reset;
- whether downstream work becomes invalid or merely blocked;
- whether compensation/rollback exists;
- when escalation or human input is required.

Use bounded retries only when a bound is justified by cost, safety, or convergence evidence. An executor that loses its environment should not silently redesign the topology; report the failure to the graph owner unless the contract explicitly authorizes recovery.

## Human gates

Model a human decision where authority or consequence requires it: irreversible publication/deployment/deletion, material spend, policy approval, or unresolved intent. Place the gate immediately before the consequential transition rather than serializing unrelated preparation behind approval.

A gate must state what evidence the human receives and what decision unlocks which edge.

## Runtime projection

Choose the execution mechanism after the semantic graph is valid.

- Keep a serial chain with one executor when context continuity dominates.
- Use independent subagents for parallel nodes that do not need shared coordination.
- Use a coordinating team/runtime only when ready parallel nodes need shared non-blocking coordination.
- Start a join/verifier only after its required incoming outputs exist.
- Preserve human gates and failure policies regardless of runtime.

The runtime consumes the graph; it does not silently redesign dependencies, ownership, or acceptance criteria. Runtime-specific fields belong in the projection layer, not in the graph's universal semantic model.

## Validation

Test the graph as a process model, not merely as a rendered diagram.

Check at least the scenarios whose failure would matter:

- happy-path reachability to each terminal outcome;
- no node starts without required inputs;
- concurrent nodes do not violate shared-resource ownership;
- joins wait for exactly their required predecessors;
- failed/skipped nodes propagate according to policy;
- retries cannot create unbounded execution where that matters;
- irreversible transitions remain behind required authority gates.

Use ordinary scenario traces for routine DAGs. Consider state-space/formal analysis only when concurrency, retries, resource ownership, or failure interleavings create consequential claims that examples cannot cover confidently.

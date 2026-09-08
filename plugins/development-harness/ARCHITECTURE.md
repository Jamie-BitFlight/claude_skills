# Development Harness Architecture

How the harness achieves what [docs/PURPOSE.md](./docs/PURPOSE.md) states it is for. Repository-level
design is in the [root ARCHITECTURE.md](../../ARCHITECTURE.md); storage internals are in
[backlog_core/ARCHITECTURE.md](./backlog_core/ARCHITECTURE.md).

## The workflow

One loop, from a requirement to a closed change with evidence. Each stage below states what it
reads and what it produces. The outcomes these exist to deliver are in
[docs/PURPOSE.md](./docs/PURPOSE.md).

**Create.** Steps through creating a requirement, feature or defect without speculating how it
should work in the system before understanding the system as a whole. Produces the backlog item in
the backend store. Implemented by `work-backlog-item`'s `create` route.

**Groom.** Gathers detail, questions the user, researches the state of the art, understands the
existing system and the impact of changing it, checks and corrects every claim, and assesses whether
the problem is being considered from the right altitudes. Produces the groomed item plus report
artifacts. Implemented by `work-backlog-item`'s `groom` route and `agents/backlog-item-groomer.md`.

**Design.** Reads the grooming reports, the item, the existing architecture documents, and the
project's rules and documented conventions. Designs or modifies architecture compliant with those,
correcting for the groomed defect or admitting the groomed feature. Then adversarially challenges
the design — pokes holes in it, challenges its reasoning and its existence, and offers alternatives
— so the change holds against the problems the groomed item states. Produces an artifact on the item
plus local architecture documentation.

**Plan.** Reads the architecture and works out how to achieve it, how to validate that it was
achieved, and how to document it, so the outcome is demonstrable against both the architecture and
the original problem statement. Identifies claims with no evidence and functional gaps, and surfaces
them back upstream into the data-gathering and research stages. Produces a plan.

**Decomposition.** Splits the plan into atomic pieces of work carrying dependencies, verification
steps, acceptance criteria and a goal. A piece may carry specialist skills or agent knowledge,
because the agent doing it can see its own work, the plan it belongs to, and the research
justifying it. It states its output, its guardrails and how to tell it is done, and does not
prescribe how to achieve it, so the agent can reach the goal while handling environmental problems
its own way. Produces the work graph. Implemented by `skills/task-decomposition` and
`agents/swarm-task-planner.md`.

**Orchestration.** Reads the graph, assigns agents within it, and gives them worktrees and
addresses. Implemented by `skills/dispatch` and `skills/work-milestone`.

**Act.** A tasked agent loads its work and proceeds, reaching the plan and the gathered
documentation when it needs background or reasoning. It attempts the acceptance criteria and runs
the validation; those outcomes decide completion. On ending it updates status so the orchestrator
can coordinate what follows. The output is completed work — generated or modified content in a
repository, or equally the validation of an external system. The report of outcomes is appended to
the work item. Implemented by `skills/execution` and `agents/task-worker.md`.

**Loop.** New information, concerns, gaps, adjacent broken systems, environmental failures and
security issues are surfaced and routed by cause: an architectural issue to Design, which then
reaches Plan to consider what changes; an environmental or external factor directly to Plan. Plan
amends, Decomposition adds or changes work and updates the graph, and Orchestration dispatches what
is new.

**Closure.** The end of the graph checks and updates documentation and reviews the whole changeset,
conditionally on what changed: code review where code changed, prose review where prose was edited,
and where the work evaluated a system, a check that the reports exist and the desired outcomes were
met. It checks the change is demonstrably effective at what it needed to achieve. Every blocker or
issue found returns to Loop.

### Naming

This document calls the last stage **Closure**, not "bookend". `BookendType` in
`sam_schema/core/models.py` names a different and narrower thing — the `t0-baseline` and
`tn-verification` pair around one plan's acceptance criteria — and using one word for both would
read as though the stage were already built out of that mechanism.

Likewise **create** is the stage and the route; `intake` is a step inside grooming
(`skills/work-backlog-item/references/workflows/groom/intake.md`) and does not name this stage.

`ARTIFACT:{STAGE}({scope})` is a cross-reference token naming the stage that produced an artifact,
and it is a separate namespace from `ArtifactType`. `ARTIFACT:DISCOVERY`, `ARTIFACT:CONTEXT`,
`ARTIFACT:TASK`, `ARTIFACT:EXECUTION`, `ARTIFACT:REVIEW` and `ARTIFACT:VERIFICATION` name no
artifact type either. So `ARTIFACT:PLAN` for the planning stage's output is correct, and reading it
as a misspelling of the `architect` type conflates the two namespaces.

### Acceptance criteria

A structured acceptance criterion carries an executable check command
(`AcceptanceCriterion.check_command` in `sam_schema/core/models.py`), and the baseline and
verification agents iterate over the list to compare before against after. Verification is therefore
what a machine can run: a UI test and a microcontroller reading are criteria; an assessment such as
"the design holds up" is not, and needs a criterion shape that carries evidence and a judgement
instead of an exit code.

### Relation to the SAM stage numbering

`skills/dh-meta-docs/references/sdlc-stage-taxonomy.md` defines a numbered pipeline whose stages are
the skill directory names `discovery`, `planning`, `context-integration`, `task-decomposition`,
`execution`, `forensic-review` and `final-verification`. That numbering does not partition the
workflow above, and forcing either onto the other loses distinctions both make.

| stage above | numbered pipeline |
|---|---|
| Create, Groom | outside it; `work-backlog-item`'s `create` and `groom` routes run before it, and `discovery` re-surveys more narrowly inside it |
| Design, Plan | both inside `planning`, which produces one `architect` artifact for the two |
| Decomposition | `task-decomposition` |
| Orchestration | outside it; `dispatch` and `work-milestone` have no numbered slot |
| Act | `execution` |
| Loop | outside it; the pipeline has loop-back edges scoped to a task verdict in `forensic-review` and a feature verdict in `final-verification`, not routing by cause |
| Closure | `final-verification`, partially |

## The work graph

The structure a plan's work is held in, and the checks over it. The workflow above says what the
stages are; this says what the graph of work they produce is, and what may be claimed from it.

### The model

One graph. Not several: a single typed, hierarchical, directed multigraph, traceable from entry to
terminal, whose parts loop back, branch on guards, and expand as detail is needed. It spans the
whole workflow — the grooming fan-out and its synthesis, design, planning, decomposition, the work
itself, and closure — and a representation that covers only part of it is not the model.

It is described as **types** and executed as **instances**.

The **type graph** declares node types, their permitted relations, and what each consumes and
produces. It is finite and can be checked before anything runs. The **instance graph** is what a run
produces: instances conforming to their types, carrying their own state and data, unbounded and
growing while work is in flight.

Expansion is instantiation of a declared type, and that is what makes a graph that grows at runtime
checkable at all: a check that holds over types holds over every instantiation of them. Fan-out,
decomposition, splitting work that will not fit one context window, and inserting a finding the
decomposition did not account for are the same operation. A node of no declared type is the case
that breaks the analysis, and it is mechanically detectable rather than a judgement.

An instance references its type rather than copying it, so a type changing under live instances is
detectable as drift rather than diverging silently.

#### What belongs to a node

The **actor** is an attribute of a node, not the node. Two dispatches of one specialist are two
nodes. Keeping the actor is what makes "does this node's actor hold authority for this effect"
answerable, and projecting it away is how a command came to write a judge's verdict with nothing to
check it against.

**Execution state** — the lifecycle a node runs through while working — is a property of the node,
not a graph of its own. `dh_core/ledger_spec.py`'s transitions are that lifecycle, and a status is
not a thing on the path from grooming to closure.

**Containment and precedence are different relations.** The node an expansion came from is
single-valued and gives the hierarchy. What fed a node is many-valued, because a synthesis step has
several inputs by definition. One parent field models the first and destroys the second.

#### What belongs to an edge

Every relation is an edge. A relation stored as a string attribute with an existence check beside it
is the flattening this work exists to remove.

**Guards sit on edges**, over a node's declared output. A node that names its own successor puts the
branch decision inside a model's output, where guard totality and overlap cannot be asked at all.

**Graph mutation is an effect requiring authority.** A decomposer may rewrite the graph; a worker
may record what it found. Ungated mutation is a control transition performed as a data write.

**Removal is an invalidation cascade** rather than an operation of its own: whatever consumed a
removed node's output now rests on nothing.

#### What the model must carry

Decomposition from the grooming and design output into work with its concurrency and ordering
stated. Extension while work is in flight, in the right place and with its own edges, rather than
appended to a note or deferred to a later plan. And the closure checks the workflow requires, which the workflow section above specifies — a review proportional to what changed, a
validation, and a documentation check.

Those closure checks are the workflow's specification, not a description of the code. An extraction
of the system records what is there; where the two differ, the difference is the finding, and the
severity rule below decides which kind.

### Edge types

A single pair of nodes may carry several edges at once. Collapsing them into one `then` arrow
hides the defects worth finding.

| type | relates |
|---|---|
| `CONTROL` | what may run after what |
| `DATA` | a produced object to the node that consumes it |
| `STATE` | shared persistent state, including mutual exclusion over a resource |
| `EVIDENCE` | what supports a claim |
| `AUTHORITY` | who may decide, mutate, approve, publish, retry or terminate |
| `ERROR` | where a failure signal goes |
| `RECOVERY` | how a failure is repaired or retried |
| `INVALIDATES` | what a result revokes |

### Node record

```json
{
  "id": "N12",
  "source_refs": ["SKILL.md#pass-3"],
  "actor": "grader",
  "activation_guard": "grade >= tighten",
  "required_inputs": [],
  "optional_inputs": [],
  "preconditions": [],
  "operation": {},
  "outputs": [],
  "postconditions": [],
  "invariants": [],
  "side_effects": [],
  "error_routes": [],
  "termination": {},
  "evidence_requirements": [],
  "authority": {},
  "subgraph_ref": null,
  "extraction_status": "OBSERVED"
}
```

An input or output declares at least: syntactic type or schema; semantic meaning; cardinality;
required authority; provenance; freshness and version; completeness expectations; and
confidentiality or trust classification where relevant.

Two nodes can exchange valid JSON and still hold a broken semantic contract — one produces
candidate findings while the consumer treats them as verified. Identical schema, incompatible
authority.

### Provenance: one rule, three sites

An assertion carries how it was established, or it is marked as unestablished. That holds for a
claim in prose, for an element of the graph, and for a method attached to a task. The mechanism is
the same each time: `extraction_status` with `source_refs`, or the equivalent warrant beside the
claim.

This is not a rule against saying how. Withholding a method that grooming actually established
wastes the investigation that produced it, and the next agent pays for it twice. Carry the evidence
you have; mark the gaps you do not.

What it forbids is prescription without evidence — a method supplied to fill a gap, from training
or from plausibility, in the same voice as one that was tested. That is worse than silence, because
it arrives with the authority of the task, and the one agent positioned to falsify it now treats it
as given. An untested "how" written as an instruction converts the agent that could have
disproved it into the agent that follows it.

So a task's method is legitimate context when it is `OBSERVED` with a source, and is a finding when
it is `ASSUMED` with none. Which severity depends on the usual rule below: absent evidence where
evidence is required is `BROKEN`; where nothing declares it required, `CONTRACT_UNSPECIFIED`.

The same test applies to the assessor's own output. A finding asserting what a system does, with no
span naming where that was read, is the defect it purports to report.

### The decomposition-exit gate

A task leaving stage 5 carries instructions. The rule they must satisfy is the owner's: do not
write tasks with claims or processes from training data. Origin is not measurable from text — a
sentence invented from training reads exactly like one recalled from a source. Absence of referent
is measurable, and the two coincide: an instruction written to fill a gap has nothing in the
sources to point at, because a writer who had a source would have pointed at it.

So the gate measures referents, in the tiers below. Each blocks.

**Tier 1 — a delegating instruction must resolve.** An instruction that sends the agent somewhere
names a referent, and the referent must exist at decomposition time.

| referent | resolves to |
|---|---|
| `TASK_OUTPUT` | a work-graph node declaring that output |
| `FILE` | a path that exists |
| `RULE` | a rules file, or a named section of one |
| `ARTIFACT` | a type in the artifact registry, with its id |
| `GRAPH_POSITION` | the successor node the instruction asserts will exist |

A skill an instruction names is not one of these referents, and the gate does not check it. Skill
availability is a property of the agent harness the work eventually runs in — Claude Code, Codex,
Hermes, OpenCode, Cursor, pi, Kimi Code and Kilo Code each resolve skills their own way — not of
this repository, and a built-in skill belongs to no plugin directory here at all. The acting agent
verifies it at runtime instead, under "Authority of a task's instructions, at runtime" below.

The instruction is the declaration. An instruction naming a `FILE` referent declares that path
exists; when the repository demonstrably lacks it, a declared predicate is demonstrably false, so
the basis is `DECLARED` and the severity `BROKEN`.

**Tier 2 — an asserting instruction must quote.** An instruction stating how a system behaves
carries a `SourceSpan` whose `quote` is found verbatim in the text at its `ref`. Citing is not
enough; the quote must be there. A citation that does not resolve is worse than none, because it
buys the authority of a source without one.

Recording the absence is the honest exit, and it is not silence. An assertion marked `ASSUMED` or
`ABSENT` with the gap stated — "no source establishes this; falsify it before relying on it" —
does not falsify the predicate, which reads "carries no evidence, **and none is recorded as
absent**". It is reported at `CONTRACT_UNSPECIFIED` and does not block. That is the difference
between handing the next agent a method to follow and handing it a hypothesis to test, which is the
whole of what the rule protects: an untested method written as an instruction converts the one
agent positioned to disprove it into the agent that follows it.

#### The judgement tier blocks, and demotion clears it

Whether a verified quote actually supports the instruction is judgement, and citation padding — a
real span quoted beside an invented method to dress it — is the same call. Both block.

Blocking is affordable here because it is clearable without winning the argument. A decomposer can
defend the citation, or demote the claim to `ASSUMED` with the gap stated, and ship. Churn needs a
block whose only exit is adjudication; this one resolves by recording uncertainty instead.

The obvious objection is that a decomposer will mark everything `ASSUMED` to get through. That
degrades in the right direction. An unmarked instruction is *implicitly certain* — that is the
default this rule exists to correct — so a task whose every method is marked as a hypothesis is
strictly more honest than the same task unmarked. The gate was never there to stop speculation. It
is there to stop speculation wearing the authority of established fact.

What must be established before the judgement tier is trusted is verdict *stability*, ahead of
accuracy: a checker answering differently on identical input generates a rewrite loop however
accurate it is on average. Measure repeated trials over a labelled corpus — supported, padded,
partially supported, supported-but-stale — and report stability first. That measurement has not
been made; until it has, nothing here asserts the tier is churn-free.

#### Authority of a task's instructions, at runtime

No gate knows what the acting agent will find. An instruction warranted at decomposition can be
stale at execution, and only the actor sees that. So the marking does work at runtime too, and
every task carries the precedence order that makes it operative: the system prompt and project
rules outrank a skill or an already-carried methodology, which outrank an instruction carrying an
established source, which outranks one marked `ASSUMED` — a hypothesis, not a method, to be tested
and discarded on failure. Where an instruction names something that does not exist, or contradicts
what the agent finds, it is not forced; the agent reaches the acceptance criteria another way within
the guardrails, and records every deviation in `<concerns>`. That preamble, verbatim, is
`AUTHORITY_PREAMBLE` in `dh_core/ledger_spec.py` — the single encoding `read` heads every task
response with, stated once here rather than duplicated.

`<concerns>` is an edge, not a section of a report. It is the stage-8 route an environmental factor
takes straight to the planner, and a task whose deviations reach no consumer has the same defect as
a `File Impact Summary` nobody reads.

#### An unresolved referent is an upstream task, not a deletion

The instruction is not struck out. It becomes a task that produces what it wanted to point at:
capture the datasheet, write the runbook, trace the call chain. The dependent task then names that
output as its referent and tier 1 resolves. This is how "do not speculate how" becomes "produce the
artifact first" — a shape the graph can hold, as a DATA edge from the new node to the one that
wanted the method.

### Falsified predicates

The predicates a check reports are defined as data in `dh_core/workflow_multigraph/findings.py`: `Predicate`
names them and `PREDICATES` carries each one's wording and the projection that decides it. There is
no second list; a predicate added there is added everywhere.

The severity a finding carries is likewise computed rather than chosen — `SEVERITY_BY_BASIS` maps
what the sources say about the predicate onto the severity, so a checker states the basis and
defends that, and the rule does the rest.

### Severity rule

Report a broken contract only when a declared or necessarily implied predicate is demonstrably
false. When the contract is missing, or admits several plausible readings, report
`CONTRACT_UNSPECIFIED` or `AMBIGUOUS` — never `BROKEN`. This keeps the boundary at finding what is
broken without speculating why.

### Projections

Derived mechanically from the one IR. Compile the control-flow projection into a workflow net or
state-transition model where that enables soundness analysis; keep the richer property graph for
semantics, provenance and traceability. Do not force everything into Petri-net notation.

| projection | mechanical questions |
|---|---|
| Control flow | reachability, dead nodes, guard coverage, joins, completion, loops |
| Data and state | producer/consumer compatibility, transformations, freshness, lifecycle |
| Intent and requirements | goal coverage, unjustified behaviour, lost or weakened requirements |
| Evidence and provenance | what supports each claim, who produced it, which snapshot it describes |
| Authority and effects | who may decide, mutate, approve, publish, retry or terminate |
| Runtime traces | which path actually occurred, and how it deviated from the model |

### Mechanical checks

Validated JSON is the authoritative analysis representation.

Schema validity; reference integrity; source-span coverage; entry and terminal existence;
reachability; dead nodes and unused outputs; guard totality and exclusivity; producer/consumer
schema compatibility; required join inputs; state generation and invalidation; unhandled failure
signals; loop bounds and progress variables; authority constraints; requirement-to-node trace
coverage; evidence-to-claim trace coverage; snapshot and fingerprint consistency.

Do not declare semantic quality from a universal best-practice score. Semantic conformance stays a
bounded judgment or an empirical evaluation until a property is made precise enough to test.

## Automation Boundary

The harness exists to turn repeatable agent instructions into reliable workflow
capabilities. A general provider CLI or MCP server can perform many underlying
operations, but the harness adds value by making the complete workflow
consistent and addressable through stable logical operations.

The governing rule is:

- If known inputs can be mechanically parsed or transformed into a required
  output, implement that work in a script or tool.
- If a repeated sequence can be made more consistent, observable, or atomic,
  expose it as one structured operation rather than a prose checklist.
- If the work requires interpretation of unique evidence, trade-off analysis,
  judgment, or generation of novel content, keep it in the agent reasoning
  layer.

Scripts and tools therefore own schema validation, stable input/output shapes,
provider abstraction, event-driven progress updates, deterministic searches and
filters, section addressing, artifact lookup, and other repeatable mechanics.
Agents own research, diagnosis, synthesis, design decisions, prioritization,
review, and other context-dependent reasoning.

Prose must not require an agent to reproduce a deterministic multi-call lookup,
grep pipeline, parsing routine, or state update when the harness can expose the
same operation safely as a script, hook, CLI command, or MCP tool. Automation
must simplify the agent's work without hiding the logical workflow or the
evidence needed to reason about it.

### What a hook may write

Automating a step does not transfer authority for it. A hook writes only what its own position
in the run gives it standing to assert; a fact some other actor already reports is that actor's
to write, and a hook that writes it too is a second encoding of one fact — the shape the model
above rules out when it keeps the actor on the node, so that "does this node's actor hold
authority for this effect" stays answerable.

The execution lifecycle in `dh_core/ledger_spec.py` names three actors and gives each exactly one
command, on that basis:

| Actor | Command | The fact only it holds |
|---|---|---|
| runner | `plan finish --result` | whether the work was done |
| judge | `plan accept` / `plan reclaim` | whether what was done meets the criteria |
| supervisor | `plan settle --attempt N --return-text` | that the launch ended at all, and what came back |

`plan state --new-status X --reason Y` sits outside that table: it is the status move no attempt
is responsible for, which is why the ledger refuses it without a reason.

A sub-agent-stop hook is the supervisor's observation point — it fires in the orchestrator's
session at the moment a launch ends — so `settle` is its command and the whole of it. It does
not write status: the runner's `finish` and the judge's verdict already encode that, and the
runner contract has a worker return `STATUS: DONE` once `finish` was recorded whatever its
`--result`, so a hook reading that token would contradict them by construction. The final
message reaches the ledger as `--return-text`, where it is evidence the judge reads, not a
verdict the hook reached.

The hook is a safety net, not the mechanism: the orchestrator settles as its own next step, and
`settle` answers `already-settled` when it got there first. What the hook adds is the case where
the orchestrator's step never runs — a session that died or was compacted — which without it
leaves an attempt open, indistinguishable from a worker still at work.

Correlating a stopping sub-agent to its attempt is the hook's one hard problem, and it is solved
by reading the sub-agent's own initial prompt, which the dispatch contract requires to name both
the address and the attempt. Session-scoped context cannot serve: inside a sub-agent the session
id is the parent's, so one wave's workers share a record. The liveness half of the same hook —
renewing an attempt's lease from tool activity — stays unimplemented for that reason and is not
approximated by writing a timestamp somewhere else.

## The logical model

Agents work only with logical objects and relationships:

- backlog item;
- research, reference, guide, or note;
- architecture;
- plan;
- atomic task;
- coordination or dispatch state;
- review, validation, or result evidence; and
- follow-up item.

An agent uses logical identifiers and relationships, not provider IDs, file
paths, issue bodies, database rows, Gists, or API-specific objects.

## The frontend contract

CLI and MCP should expose stable logical CRUD and workflow operations for:

- creating, reading, updating, and deleting logical objects;
- updating fields and sections, including append and delete operations;
- recording and retrieving references and evidence;
- managing architecture, plan, and task lifecycles;
- returning task feedback upstream;
- assigning sequence and ownership; and
- querying by logical ID, relationship, status, capability, and provenance.

The frontend contract treats CLI and MCP as interchangeable structured
transports for the logical operations they expose. They are not required to
proxy every provider-native capability. Skills and agents may use an existing
backend tool directly when it is the authoritative and capable interface (for
example, `bd` for Beads issue graphs and readiness). Both structured surfaces
remain supported; this document makes no retirement or deprecation claim about
either one.

The frontend contract must not depend on a selected provider's object model or
addressing scheme.

## The backend guarantee

Storage is an implementation detail. Logical objects may be stored together or
across providers such as GitHub, GitLab, Linear, SQLite, Beads, local storage,
or Gist-backed storage.

The backend contract is canonical and provider-neutral. It defines object
and relationship semantics, content and revisions, links, append behavior,
statuses, query capabilities, ownership, and provenance. Adding a provider must
change only provider implementation, registration, and configuration—not CLI or
MCP commands or workflow behavior.

## Storage and routing

The configured backend is the single routing decision for work items, grooming, plans, tasks,
artifact manifests, and artifact content. MCP and CLI expose interchangeable logical operations;
`bd` remains the native interface for Beads issue graphs and readiness where that capability is
stronger than the structured adapter.

Remote-capable providers privately own `FileCache` for stale snapshots, durable queued offline
mutations, revisions, and provider-specific persistence. Beads, SQLite, and Memory use native
storage directly and never read or write backlog YAML or instantiate `FileCache`. Backend failures,
cache misses, conflicts, and unsupported capabilities are explicit results; callers do not route
to an independent task backend, artifact provider, local filesystem fallback, or per-plan provider.

Provider IDs, issue bodies, paths, database rows, and wire formats remain implementation details.
Consumers should use logical identifiers and the supported MCP/CLI operations. Direct YAML access and independent-provider code paths are not supported
workflow contracts.

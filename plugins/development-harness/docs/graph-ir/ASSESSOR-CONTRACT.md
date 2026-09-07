# Assessor contract — the graph IR and what may be claimed from it

Design-time. The audience is whoever builds or reviews the intermediate representation and the
checks over it, not an agent executing a plan.

The system is a **typed, hierarchical, directed multigraph**. It must represent cycles and bounded
loops, recursion, parallel branches and joins, persistent state, setup and invalidation
lifecycles, error/recovery/rollback/retry paths, several relationships between one pair of nodes,
environment-dependent activation, and one node refined into a subgraph.

One structured IR is authoritative. Mermaid, tables and prose are generated from it, never
maintained beside it.

## The model

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

### What belongs to a node

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

### What belongs to an edge

Every relation is an edge. A relation stored as a string attribute with an existence check beside it
is the flattening this work exists to remove.

**Guards sit on edges**, over a node's declared output. A node that names its own successor puts the
branch decision inside a model's output, where guard totality and overlap cannot be asked at all.

**Graph mutation is an effect requiring authority.** A decomposer may rewrite the graph; a worker
may record what it found. Ungated mutation is a control transition performed as a data write.

**Removal is an invalidation cascade** rather than an operation of its own: whatever consumed a
removed node's output now rests on nothing.

### What the model must carry

Decomposition from the grooming and design output into work with its concurrency and ordering
stated. Extension while work is in flight, in the right place and with its own edges, rather than
appended to a note or deferred to a later plan. And the closure checks the workflow requires, which
[ARCHITECTURE.md](../../ARCHITECTURE.md) specifies — a review proportional to what changed, a
validation, and a documentation check.

Those closure checks are the workflow's specification, not a description of the code. An extraction
of the system records what is there; where the two differ, the difference is the finding, and the
severity rule below decides which kind.

## Edge types

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

## Node record

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

## Falsified predicates to report

- a required input has no producer
- a producer's output type does not satisfy the consumer's input type
- a required field is absent
- output cardinality conflicts with the join
- the consumer requires `VERIFIED` and the producer supplies `PROPOSED`
- an artifact revision does not match the expected revision
- an input may be stale and no freshness check exists
- a failure output has no consuming edge
- an actor lacks authority for the effect
- a branch guard is incomplete, or overlaps another guard
- a node or output is unreachable
- a prescribed method carries no evidence, and none is recorded as absent
- an instruction names a referent that does not resolve

## Provenance: one rule, three sites

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

## The decomposition-exit gate

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
| `SKILL` | a directory containing `SKILL.md` |
| `TASK_OUTPUT` | a work-graph node declaring that output |
| `FILE` | a path that exists |
| `RULE` | a rules file, or a named section of one |
| `ARTIFACT` | a type in the artifact registry, with its id |
| `GRAPH_POSITION` | the successor node the instruction asserts will exist |

The instruction is the declaration. "Load `restructuring-to-solid`" declares that skill exists; the
repository demonstrably lacks it; a declared predicate is demonstrably false, so the basis is
`DECLARED` and the severity `BROKEN`.

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

### The judgement tier blocks, and demotion clears it

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

### Authority of a task's instructions, at runtime

No gate knows what the acting agent will find. An instruction warranted at decomposition can be
stale at execution, and only the actor sees that. So the marking does work at runtime too, and
every task carries the precedence order that makes it operative:

> **Authority of these instructions.** The acceptance criteria and guardrails are binding.
> Everything else is direction, ranked:
>
> 1. Your system prompt and the project's rules.
> 2. A skill named here, and the methodology you already carry.
> 3. An instruction carrying a source — established; the source is named so you can check it.
> 4. An instruction marked `ASSUMED` — a hypothesis, not a method. Test it before relying on it;
>    discard it when it fails.
>
> Where these conflict, the higher wins. Where an instruction names something that does not exist,
> or contradicts what you find, do not force it — reach the acceptance criteria another way within
> the guardrails.
>
> Record every deviation in `<concerns>`: what the instruction said, what you found instead, what
> you did.

`<concerns>` is an edge, not a section of a report. It is the stage-8 route an environmental factor
takes straight to the planner, and a task whose deviations reach no consumer has the same defect as
a `File Impact Summary` nobody reads.

### An unresolved referent is an upstream task, not a deletion

The instruction is not struck out. It becomes a task that produces what it wanted to point at:
capture the datasheet, write the runbook, trace the call chain. The dependent task then names that
output as its referent and tier 1 resolves. This is how "do not speculate how" becomes "produce the
artifact first" — a shape the graph can hold, as a DATA edge from the new node to the one that
wanted the method.

## Severity rule

Report a broken contract only when a declared or necessarily implied predicate is demonstrably
false. When the contract is missing, or admits several plausible readings, report
`CONTRACT_UNSPECIFIED` or `AMBIGUOUS` — never `BROKEN`. This keeps the boundary at finding what is
broken without speculating why.

## Projections

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

## Traces

Scenario-bound symbolic execution, plus observed execution where available. A trace binds the
environment and host, target and artifact fingerprints, initial state, representative input
objects, selected guards, node sequence, state changes, transformations, emitted evidence, and
the terminal outcome.

Track these facets separately: facts, user intent, constraints, uncertainty, authority, evidence,
provenance, decisions, generated content.

At each transformation ask what was preserved, removed, summarised, strengthened or weakened,
invented, made unverifiable, changed in authority, or made stale.

Run both directions. Forward: where can this input or requirement affect behaviour. Backward:
what sources, transformations and decisions contributed to this output. Program slicing is the
mechanical precedent; data-aware conformance checking is the expected-versus-observed precedent.

## Holistic evaluation of the composed system

- every required intent claim reaches at least one implementing path
- every material behaviour has an authoritative justification
- every intended transformation occurs
- no transformation corrupts, weakens or invents meaning
- the right node receives the right information
- decisions occur under the correct authority
- setup state is established, checked, versioned and invalidated correctly
- one-time work is not incorrectly repeated
- recurring work is not incorrectly one-shot
- retry, escalation, recursion or feedback occurs where required
- loops have progress conditions and termination bounds
- successful terminals satisfy the goal
- failed terminals preserve enough evidence for recovery
- no path terminates while relevant work remains active
- unnecessary path length is identified

Path length is separated from correctness. A path is nonconformant when its length violates a
constraint or causes outcome failure. Otherwise unnecessary length is an optimisation finding, so
that "could be shorter" is never reported as "does not conform".

## Mechanical checks

Validated JSON is the authoritative analysis representation.

Schema validity; reference integrity; source-span coverage; entry and terminal existence;
reachability; dead nodes and unused outputs; guard totality and exclusivity; producer/consumer
schema compatibility; required join inputs; state generation and invalidation; unhandled failure
signals; loop bounds and progress variables; authority constraints; requirement-to-node trace
coverage; evidence-to-claim trace coverage; snapshot and fingerprint consistency.

Do not declare semantic quality from a universal best-practice score. Semantic conformance stays a
bounded judgment or an empirical evaluation until a property is made precise enough to test.

## Validating the report

Separate activities, in order.

1. **Model fidelity.** Does the recovered graph faithfully represent the original prose, code,
   configuration and environment? This one is essential: a perfectly sound graph proves nothing if
   the extractor silently repaired an ambiguity or dropped an inconvenient branch.
2. **Finding verification.** Given the frozen graph and the sources, is each claimed disconnect
   actually present?
3. **Blind completeness audit.** Given the sources and the contract but not the assessor's
   findings, can an independent reviewer discover material omissions?

The findings document is untrusted and immutable. A verifier issues amendments or counter-findings
and never silently rewrites it. A reducer then produces a new verified revision accounting for
every original and newly discovered finding.

### Markers a findings file carries

`tests_sam/test_adr_3460_migration_trigger.py` reads these, so write them deliberately. A file's
existence is never taken as its conclusion.

| marker | on | means |
|---|---|---|
| `Verdict: faithful` | a model-fidelity file | the extractor repaired no ambiguity and dropped no branch. Any other verdict, or none, leaves the criterion unmet |
| `Found-by: IR` | one finding | the graph surfaced this, rather than a person or a review pass finding it and the graph confirming it |
| `Previously-known: no` | one finding | it was not already recorded before the graph found it |

Both markers together are what satisfies the migration-trigger criterion that the IR generalises
beyond the defects it was built against: it must have caught a defect nobody had already found.
Claiming either marker without the other satisfies nothing. The test that formerly evaluated this
criterion (`tests_sam/test_adr_3460_migration_trigger.py`) has since been deleted for reading an
ADR from disk and parsing these markers out of markdown by regex; the criterion is recorded here
until it is re-stated against structured data a test can assert on directly.

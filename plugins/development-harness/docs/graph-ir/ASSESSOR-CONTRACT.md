# Assessor contract — the graph IR and what may be claimed from it

Design-time. The audience is whoever builds or reviews the intermediate representation and the
checks over it, not an agent executing a plan.

The system is a **typed, hierarchical, directed multigraph**. It must represent cycles and bounded
loops, recursion, parallel branches and joins, persistent state, setup and invalidation
lifecycles, error/recovery/rollback/retry paths, several relationships between one pair of nodes,
environment-dependent activation, and one node refined into a subgraph.

One structured IR is authoritative. Mermaid, tables and prose are generated from it, never
maintained beside it.

## The three layers

The system is three graphs. Each is describable on its own; the system is only drawn when all
three exist together. A representation that carries one of them and calls itself the model of the
system is the flattening this contract exists to prevent.

**Layer 1 — task lifecycle.** Nodes are statuses (`not-started`, `in-progress`, `complete`,
`blocked`, `deferred`, `skipped`, `failed`); edges are the commands that move between them
(`dispatch`, `finish`, `accept`, `reclaim`, `state`, `settle`). One uniform machine, instantiated
per task, tracking where each task's progress is. `dh_core/ledger_spec.py:TRANSITIONS` is this
layer.

**Layer 2 — the work graph.** Nodes are tasks; edges are the eight types below. This layer says
what may run concurrently and what waits on what. Every layer-2 graph carries bookends: a review
step, a validate step, and a documentation-check step. They are structural, not optional
decoration, and a graph without them is malformed rather than merely lacking.

**Layer 3 — the workflow.** Nodes are process steps with an actor, a guard and source refs into a
`SKILL.md`; the node record below is shaped for these. Layer 3 takes the grooming and architecture
output — research, fact checks, dependencies, documentation, concerns — and decomposes it into a
layer-2 graph. It then maintains that graph while work runs.

### How they relate

Layer 1 is a projection of layer 3 onto a single task. "The judge may accept a complete task under
this authority" is a layer-3 fact; project the actor away and what remains is the transition
`accept: complete → accepted`. Discarding the actor is exactly how authority is lost, which is why
a command could write a judge's verdict with nothing to check it against.

Layer 2 is the artifact layer 3 produces and mutates. It is not static: layer 3 extends it while
work is in flight.

### What the layers must support

Decomposition, from the grooming and architecture inputs into a layer-2 graph with its concurrency
and ordering stated.

Extension at runtime. A task that would exceed one agent's context window is split before it runs,
and the split is a layer-3 operation on layer 2. A finding discovered mid-work that the
decomposition did not account for is inserted into the active graph, in the right place, with its
own edges — not appended to a task's notes and not deferred to a later plan.

Bookend guarantee. Review, validate and documentation-check exist on every layer-2 graph, and a
check can ask whether they do.

This one states the target, not the system. `BookendType` in `sam_schema/core/models.py` admits
`t0-baseline` and `tn-verification` and nothing else, so an extraction of the system today records
these three as `ABSENT`, never `OBSERVED`. Getting that wrong decides a severity: a bookend the
system was never built to have is `CONTRACT_UNSPECIFIED`, while one it declares and does not run
is `BROKEN`. Every requirement in this section is read the same way — it says what the layer needs,
and the extraction says what is there.

Nothing here is preserved because the incumbent implementation has it. Where the current system
answers one of these badly, the answer is to state what the layer requires and let the
implementation follow, not to describe what exists.

Meta-harness connection points — the hooks that glue the layers to a particular harness — are
mechanically assessable only once the three layers are distinct. Do not design them before the
layers are clear.

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

So the gate measures referents, in two tiers. Both block.

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

### What the gate does not decide

A quote that resolves and verifies but does not support the claim passes. So does citation padding
— a real span quoted beside an invented method to dress it. Both are judgement, and both go to the
adversarial pass. The gate's contribution is making them the *only* remaining failure mode rather
than two among many.

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

Three separate activities, in order.

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

Both markers together are what satisfies the ADR-3460-1 criterion that the IR generalises beyond
the defects it was built against. Claiming either without the other satisfies nothing.

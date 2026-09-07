# Assessor contract — the graph IR and what may be claimed from it

Design-time. The audience is whoever builds or reviews the intermediate representation and the
checks over it, not an agent executing a plan.

The system is a **typed, hierarchical, directed multigraph**. It must represent cycles and bounded
loops, recursion, parallel branches and joins, persistent state, setup and invalidation
lifecycles, error/recovery/rollback/retry paths, several relationships between one pair of nodes,
environment-dependent activation, and one node refined into a subgraph.

One structured IR is authoritative. Mermaid, tables and prose are generated from it, never
maintained beside it.

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

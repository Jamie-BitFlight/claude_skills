# Blind completeness audit — the workflow multigraph

A blind completeness audit — the third of the assessor contract's validation activities, distinct
from model fidelity and finding verification: given the sources and the contract but not the
assessor's findings, can an independent reviewer discover material omissions?

This file is immutable. A verifier issues amendments or counter-findings against it and never
rewrites it.

## What was read, and what was not

Read: the assessor contract (since deleted; its architecture content now lives in
`plugins/development-harness/ARCHITECTURE.md` under "The work graph"); `dh_core/ledger_spec.py`;
`sam_schema/core/models.py`; `dh_core/workflow_multigraph/model.py`; `dh_core/workflow_multigraph/findings.py`;
`dh_core/workflow_multigraph/__init__.py`; `tests_sam/test_workflow_multigraph_defects.py`.

Not read, deliberately: `docs/workflow-multigraph/findings/fidelity.md` and
`docs/workflow-multigraph/findings/predicates.md`. The audit is blind by construction. Any overlap with what
those documents already say is convergence, not corroboration, and a reducer should treat it as two
independent observations of the same gap rather than as one finding confirmed twice.

## Subject and severity reading

The subject of this audit is **the multigraph as built** — the schema, the facets it carries, and
the queries over it — not the ledger whose records its instances carry. Every finding is an
omission in the graph itself.

Applying the severity rule to that subject needs one stated reading, because the rule is worded for
the system under assessment. Here, a predicate counts as **declared** when the assessor contract
states it (it is the multigraph's own specification, and the authority this work was given — its
architecture content now lives in `plugins/development-harness/ARCHITECTURE.md` under "The work
graph"), or when the built module states it in its own docstrings and constraints. It counts as
**necessarily implied** when nothing works unless it holds. Where the contract is silent on whether
a facet must be *decided* rather than merely *declared*, the finding is `CONTRACT_UNSPECIFIED`, not
`BROKEN` — see COMPLETENESS-16 and COMPLETENESS-17, which are held below `BROKEN` for exactly that
reason.

The contract distinguished two lists that carry different weight, and the severities below respect
the difference:

- the **Mechanical checks** list (`plugins/development-harness/ARCHITECTURE.md`, "The work graph"
  → "Mechanical checks") enumerates what must be decidable by machine. A named check with no
  structure to decide it is `BROKEN`.
- the **Holistic evaluation** list enumerated what the composed system must be evaluated on — a
  list dropped rather than carried forward when the contract's architecture content moved into
  `ARCHITECTURE.md` (see this directory's `AMENDMENTS.md` entry A-5). The contract permitted some
  of these to stay "a bounded judgment or an empirical evaluation until a property is made precise
  enough to test" — wording that *did* carry forward, and now closes "The work graph" → "Mechanical
  checks" — so a holistic item absent from the mechanical list, with no structural demand elsewhere
  in the contract, is not `BROKEN` on its own.

## On the report markers

No finding here carries `Found-by: IR` or `Previously-known: no`. Both would be false. These
findings were not surfaced by running the graph — they were found by reading the schema against the
contract, which is what a completeness audit is. The markers belong to findings the multigraph produced
about the system it models, and the `test_adr_3460_migration_trigger.py` criterion should not read
this file as evidence for them either way.

`Verdict: faithful` belongs on a model-fidelity file and is deliberately absent here.

---

## COMPLETENESS-1 — No requirement or intent entity exists

**Omission**: the multigraph has no representation of a requirement, an intent claim or a goal, so nothing
can be traced to or from one.

**Severity**: BROKEN. Basis: DECLARED. `Intent and requirements` is one of six projections "derived
mechanically from the one multigraph", with the mechanical questions "goal coverage, unjustified behaviour,
lost or weakened requirements" (`plugins/development-harness/ARCHITECTURE.md`, "The work graph" →
"Projections"); `requirement-to-node trace coverage` is a named check in the same document's
"Mechanical checks"; and the contract's holistic evaluation list — since dropped rather than
carried forward, see `AMENDMENTS.md` entry A-5 — opened with "every required intent claim reaches
at least one implementing path" and "every material behaviour has an authoritative justification".

**Observed**:

- `Projection.INTENT_AND_REQUIREMENTS` is declared at `dh_core/workflow_multigraph/findings.py#L35` and is
  named by no `PredicateDefinition`. Searching `findings.py` for `projection=Projection.` returns
  only `CONTROL_FLOW`, `DATA_AND_STATE`, `EVIDENCE_AND_PROVENANCE` and `AUTHORITY_AND_EFFECTS`
  (`PREDICATES`, `findings.py#L68-L104`). The projection is a name with nothing behind it.
- No field of `Node`, `Edge` or `Descriptor` names a requirement, criterion, goal or intent. A
  case-insensitive search of the whole package for `requirement` matches only the class
  `EvidenceRequirement` and the field `evidence_requirements`; for `intent`, only the projection
  member above; for `goal`, nothing.
- The domain already carries the entity the multigraph drops.
  `sam_schema/core/models.py#L310-L314` declares
  `Plan.acceptance_criteria_structured: list[AcceptanceCriterion]`, and
  `models.py#L376-L399` declares `AcceptanceCriterion` with `criterion_id`, `check_command`,
  `expected_baseline` and `expected_final` — a structured, executable requirement with an identity
  to trace against. `Plan.goal` is at `models.py#L303`. None of it has a carrier in the multigraph.

**Consequence**: the whole Intent-and-requirements projection, and the two holistic questions that
open the list, cannot be asked of this multigraph at all — not answered wrongly, but not posed.

---

## COMPLETENESS-2 — No trace record exists

**Omission**: the multigraph has no representation of an execution, symbolic or observed, so the
expected-versus-observed half of the contract is absent.

**Severity**: BROKEN. Basis: DECLARED. `Runtime traces` is a named projection, with the mechanical
questions "which path actually occurred, and how it deviated from the model"
(`plugins/development-harness/ARCHITECTURE.md`, "The work graph" → "Projections"). The contract
additionally devoted a section to Traces, fixing what a trace binds — the environment and host,
target and artifact fingerprints, initial state, representative input objects, selected guards,
node sequence, state changes, transformations, emitted evidence, and the terminal outcome — naming
nine things to track separately (facts, user intent, constraints, uncertainty, authority, evidence,
provenance, decisions, generated content), nine transformation questions, and the analysis
precedents of program slicing and data-aware conformance checking. That section was dropped rather
than carried forward when the contract's content moved into `ARCHITECTURE.md` (see this
directory's `AMENDMENTS.md` entry A-5); the requirements it stated are restated here directly since
there is no longer a document to cite them from.

**Observed**:

- `Projection.RUNTIME_TRACES` is declared at `findings.py#L38` and is named by no
  `PredicateDefinition`. A case-insensitive search of the package for `trace` returns exactly that
  one hit; for `slice`, nothing.
- No class binds any of the ten things a trace must bind. The nearest field is
  `Edge.recorded_by` (`model.py#L245-L247`), a list of free strings described as "What records this
  relation happened", which is a property of the model, not of a run.
- The nine transformation questions — "what was preserved, removed, summarised, strengthened or
  weakened, invented, made unverifiable, changed in authority, or made stale" — have no carrier.
  `Operation` (`model.py#L175-L180`) is `kind` and `summary`, both free text, and neither is read by
  any query (`operation` appears in `model.py` only at its field declaration, L200).
- The nine facets the contract said to "track separately" — facts, user intent,
  constraints, uncertainty, authority, evidence, provenance, decisions, generated content — have no
  vocabulary in the model. Three of them (authority, evidence, provenance) have partial carriers;
  the rest have none.

---

## COMPLETENESS-3 — Guards are unstructured free text and no query reads them

**Omission**: guard totality and exclusivity are not decidable, because a guard is a string with no
branch grouping, no domain and no relation to the other guards it must partition.

**Severity**: BROKEN. Basis: DECLARED. `Predicate.GUARD_INCOMPLETE_OR_OVERLAPPING`
(`dh_core/workflow_multigraph/findings.py`) is a falsified predicate to report — "a branch guard is
incomplete, or overlaps another guard"; `guard totality and exclusivity` is a named mechanical
check (`plugins/development-harness/ARCHITECTURE.md`, "The work graph" → "Mechanical checks"); and
the contract required the multigraph to represent "environment-dependent activation" among the system's
other structural properties — a requirements list dropped rather than carried forward when the
contract's content moved into `ARCHITECTURE.md` (see `AMENDMENTS.md` entry A-5).

**Observed**:

- `Node.activation_guard: str | None` (`model.py#L196`) and `Edge.guard: str | None`
  (`model.py#L244`) are the only guard carriers. Searching `model.py` for `.guard` returns no
  reader — both fields appear once each, at their declaration.
- Nothing groups guards into a branch. Totality ("do these guards cover the domain?") and
  exclusivity ("do two of them overlap?") are questions about a *set* of guards over a *domain*, and
  the multigraph represents neither the set nor the domain. This is not a missing query; it is a missing
  structure, and no query could be written against what is there.
- `Predicate.GUARD_INCOMPLETE_OR_OVERLAPPING` (`findings.py#L54`, defined at `findings.py#L98-L100`)
  therefore has no `Graph` method. Compare the eight predicates that do:
  `inputs_without_producer`, `type_incompatible_edges`, `trust_shortfalls`, `authority_shortfalls`,
  `effects_without_authority`, `unchecked_stale_inputs`, `revision_mismatches`, `unrouted_failures`,
  `unreachable_nodes` (`model.py#L325-L491`).
- No environment binding exists anywhere in the package (a case-insensitive search for
  `environment` returns nothing), so environment-dependent activation is representable only as more
  free text inside `activation_guard`.
- The system under assessment is dense with exactly this structure.
  `dh_core/ledger_spec.py#L802-L807` declares `Check` as "One precondition, evaluated in order; the
  first failing check's reason is printed", with an `unless` field described as "Flag or fact that
  waives the check". `TRANSITIONS` (`ledger_spec.py#L871-L1200`) is a `(command, from_status)`
  matrix whose rows are generated per status, several of them by comprehension over `OPEN_STATUSES`.
  Ordered checks with waivers over a status matrix is the guard-partition problem in its canonical
  form, and it is the part of the ledger the multigraph cannot hold.

---

## COMPLETENESS-4 — No join semantics; `Cardinality` is carried and never read

**Omission**: the multigraph cannot say that a node's inputs are joined conjunctively rather than
disjunctively, so join requirements and cardinality-against-join conflicts are undecidable.

**Severity**: BROKEN. Basis: DECLARED. The contract required the multigraph to represent "parallel branches
and joins" among the system's other structural properties — a requirements list dropped rather than
carried forward when the contract's content moved into `ARCHITECTURE.md` (see `AMENDMENTS.md` entry
A-5); `Predicate.CARDINALITY_CONFLICTS_WITH_JOIN` (`dh_core/workflow_multigraph/findings.py`) — "output
cardinality conflicts with the join" — is a falsified predicate to report; `required join inputs`
is a named mechanical check and `joins` a mechanical question of the Control-flow projection
(`plugins/development-harness/ARCHITECTURE.md`, "The work graph" → "Mechanical checks" and →
"Projections").

**Observed**:

- `Cardinality` (`model.py#L53-L60`) is required on every `Descriptor` (`model.py#L124`) and read by
  no query. Searching `model.py` for `cardinality` returns one hit, the field declaration.
- No field distinguishes an AND-join from an XOR-join, or marks which incoming edges must all be
  present before a node may run. `Node` (`model.py#L190-L233`) has `required_inputs` and
  `preconditions` (free strings); neither expresses a join over incoming *edges*.
- `Predicate.CARDINALITY_CONFLICTS_WITH_JOIN` (`findings.py#L48`) has no `Graph` method. Searching
  the package for `join` returns three hits, all docstring prose (`model.py#L30`, `#L314`, `#L442`).
- The system under assessment has a join at its centre. `tasks.ready`
  (`ledger_spec.py#L291-L300`) is derived as "status is not-started, and every id in dependencies
  names a task that is accepted or in SUCCESSFUL_DEPENDENCY, and no other task with the same
  non-null conflict_group is in-progress or complete-unaccepted" — a conjunctive join over a
  variable-arity dependency set, conjoined with a mutual-exclusion clause.

---

## COMPLETENESS-5 — No loop or cycle representation

**Omission**: the multigraph cannot express a cycle, a bound on one, or a progress variable, so no loop can
be checked for termination.

**Severity**: BROKEN. Basis: DECLARED. The contract required the multigraph to represent "cycles and
bounded loops, recursion" among the system's other structural properties — a requirements list
dropped rather than carried forward when the contract's content moved into `ARCHITECTURE.md` (see
`AMENDMENTS.md` entry A-5); `loop bounds and progress variables` is a named mechanical check and
`loops` a mechanical question of the Control-flow projection
(`plugins/development-harness/ARCHITECTURE.md`, "The work graph" → "Mechanical checks" and →
"Projections"); the contract's holistic evaluation list — also dropped, per the same amendment —
additionally required that loops have progress conditions and termination bounds, and that retry,
escalation, recursion or feedback occur where required.

**Observed**:

- The only carrier is `Termination.bound: str` (`model.py#L187`), described as "Loop bound or
  progress variable; empty when not a loop" — one free-text field doing the work of two distinct
  concepts, the bound and the variable that must approach it. `termination` appears in `model.py`
  only at its field declaration (L206); no query reads it.
- No cycle detection exists. Searching the package for `cycle` returns nothing.
  `unreachable_nodes` (`model.py#L476-L492`) is the only traversal, and it walks CONTROL edges
  breadth-first while discarding every cycle it crosses.
- The system under assessment is a bounded retry loop.
  `attempts` and `attempts_allowed` are columns (`ledger_spec.py#L234-L235`); `attempts` is
  incremented by dispatch (`ledger_spec.py#L878`, `Effect(column="attempts", value="attempts + 1")`);
  `attempts-exhausted` refuses when "attempts is at or above attempts_allowed and --more-attempts is
  absent" (`ledger_spec.py#L545-L549`), checked by reclaim at `ledger_spec.py#L1073`; and
  `loop.max_attempts` is the configured bound (`ledger_spec.py#L1217-L1219`). The
  dispatch → finish → reclaim → dispatch cycle, with `attempts` as its progress variable and
  `attempts_allowed` as its bound, is the single most prominent loop in the sources and has no
  representation in the multigraph beyond a string.

---

## COMPLETENESS-6 — `unrecorded_invalidations` returns observations that cannot be reported

**Falsified predicate**: a graph query exists whose output cannot become a finding, because the
predicate set is declared closed and contains no member covering it.

**Severity**: BROKEN. Basis: DECLARED — both halves are declared by the built module itself.

**Observed**:

- `Graph.unrecorded_invalidations` (`model.py#L408-L422`) returns `Observation`s whose `expected` is
  "a record accounting for {source} revoking {target}" and whose `observed` is "recorded_by is
  empty".
- `Predicate` (`findings.py#L44-L55`) has eleven members and none states anything about an
  invalidation nothing records. `Finding.predicate` is typed `Predicate`
  (`findings.py#L158`), so every reportable finding must claim one of those eleven statements, and
  `Finding.statement` (`findings.py#L177-L180`) renders it into the report.
- The set is not open. `test_severity_taxonomy_is_closed`
  (`tests_sam/test_workflow_multigraph_defects.py#L463-L474`) asserts `set(PREDICATES) == set(Predicate)`, and
  `findings.py`'s module docstring states "the predicates worth reporting are an enumerated list,
  not free prose".
- The consequence is visible in the defect test itself. `test_d4_replace_revokes_state_no_event_accounts_for`
  (`test_workflow_multigraph_defects.py#L396-L445`) calls `unrecorded_invalidations()` at L406, asserts both
  subjects at L407, and then constructs its two findings from
  `REQUIRED_INPUT_HAS_NO_PRODUCER` and `REVISION_MISMATCH`. D4's own signature detection — the
  INVALIDATES relation the control-flow-only spec could not express, which is the reason D4 is in
  the defect set — reaches an assertion and stops there. It cannot reach a report.

**Note for the reducer**: the fix is a twelfth predicate, not a re-labelling of the observation
under one of the eleven. Filing it as `REQUIRED_INPUT_HAS_NO_PRODUCER` would give the finding a
`statement` that is not true of what was observed.

---

## COMPLETENESS-7 — No state resource; `STATE` edges are inert and mutual exclusion is unrepresentable

**Omission**: shared persistent state has no identity in the multigraph — no resource, no generation, no
version — so its lifecycle cannot be checked and exclusion over it cannot be stated.

**Severity**: BROKEN. Basis: DECLARED. The `STATE` edge type relates "shared persistent state,
including mutual exclusion over a resource"; `state generation and invalidation` is a named
mechanical check; the Data-and-state projection asks about "freshness, lifecycle" (all three:
`plugins/development-harness/ARCHITECTURE.md`, "The work graph" → "Edge types", "Mechanical
checks" and "Projections"). The contract's holistic evaluation list — dropped rather than carried
forward, see `AMENDMENTS.md` entry A-5 — additionally held the composed system to "setup state is
established, checked, versioned and invalidated correctly" and "no path terminates while relevant
work remains active".

**Observed**:

- `EdgeType.STATE` (`model.py#L33`) is read by no query. Searching `model.py` for `EdgeType.`
  returns three usages: `INVALIDATES` at L421, `ERROR`/`RECOVERY` at L464, and `CONTROL` at L487.
  `DATA`, `STATE`, `EVIDENCE` and `AUTHORITY` are never consulted, and `_pairs()`
  (`model.py#L313-L323`) — the basis of five of the nine queries — ignores `edge.type` entirely.
- `Edge` (`model.py#L235-L250`) carries no resource, generation or version field. A STATE edge can
  therefore say only that two nodes share *something*, never what, and never at which generation.
- Freshness hangs off the wrong thing. `Freshness` (`model.py#L102-L108`) is a field of
  `Descriptor` — a value in transit — not of a persistent resource, so "established, checked,
  versioned and invalidated" has nowhere to be recorded for state that outlives an edge.
- Mutual exclusion is a symmetric relation over a *named* resource. With no resource identity and
  no query over STATE edges, it cannot be expressed, and no test in
  `test_workflow_multigraph_defects.py` constructs a STATE edge at all.
- The system under assessment has both. `tasks.conflict_group` is a column
  (`ledger_spec.py#L233`) and the `ready` rule at `ledger_spec.py#L297-L299` enforces "no other task
  with the same non-null conflict_group is in-progress or complete-unaccepted". The lease is a
  time-bounded state resource: `expires`, `ttl_seconds`, and the derived `expired`, `stale` and
  `renew_by` columns (`ledger_spec.py#L306-L328`), with `lease.ttl_seconds` configured at
  `ledger_spec.py#L1212-L1216`. `attempt_open` is the "relevant work remains active" flag the
  contract's (dropped) holistic evaluation list asked about, per the Severity paragraph above.

---

## COMPLETENESS-8 — Evidence is declared and never checked

**Omission**: `evidence_requirements` and `EvidenceRequirement.supported_by` are write-only. No
query reads them, reference integrity does not resolve them, and no query distinguishes an EVIDENCE
edge from a DATA edge.

**Severity**: BROKEN. Basis: DECLARED. `evidence-to-claim trace coverage` is a named mechanical
check, and the Evidence-and-provenance projection asks "what supports each claim, who produced it,
which snapshot it describes" (both: `plugins/development-harness/ARCHITECTURE.md`, "The work
graph" → "Mechanical checks" and → "Projections"). The contract's holistic evaluation list —
dropped rather than carried forward, see `AMENDMENTS.md` entry A-5 — additionally required that
failed terminals preserve enough evidence for recovery.

**Observed**:

- `Node.evidence_requirements` (`model.py#L207`) appears once in `model.py`, at its declaration.
  `EvidenceRequirement.supported_by` (`model.py#L172`) is described as holding "Descriptor or node
  ids supplying support" and is resolved by nothing —
  `check_reference_integrity` (`model.py#L274-L297`) resolves only `edge.source`, `edge.target`,
  `edge.source_output` and `edge.target_input`. A claim whose support does not exist is both
  representable and undetectable.
- `EdgeType.EVIDENCE` is read by no query (see the `EdgeType.` search in COMPLETENESS-7), and
  `_pairs()` treats it exactly as a DATA edge. The D3 test relies on this: it builds an
  `EdgeType.EVIDENCE` edge (`test_workflow_multigraph_defects.py#L286-L296`) and detects the defect with
  `type_incompatible_edges`, a descriptor-type query. Retyping that edge `DATA` would change no
  result.
- No test in `test_workflow_multigraph_defects.py` populates `evidence_requirements` — the four defect graphs
  construct nodes through the `node()` helper (`test_workflow_multigraph_defects.py#L77-L80`) and never pass
  it.
- The system under assessment has the evidence entities the multigraph omits. `BookendResult`
  (`sam_schema/core/models.py#L403-L420`) records `criterion_id`, `check_command`, `exit_code`,
  `stdout` and `stderr`; `AcceptanceCriterion.expected_baseline`/`expected_final`
  (`models.py#L390-L399`) name the T0 and TN snapshots a claim is measured between — precisely the
  "which snapshot it describes" question the Evidence-and-provenance projection asks (per the
  Severity paragraph above). `Task.is_bookend` and `Task.bookend_type`
  (`models.py#L234-L239`), the EVIDENCE relation in the domain, have no carrier in the multigraph.

---

## COMPLETENESS-9 — Authority is a per-node self-assertion, with no actor policy

**Omission**: there is no actor registry and no per-actor grant policy. A node declares its own
authority, and the authority check compares that node's effects against its own declaration, so
widening the declaration silences the finding.

**Severity**: BROKEN. Basis: DECLARED. `authority constraints` is a named mechanical check; the
Authority-and-effects projection asks "who may decide, mutate, approve, publish, retry or
terminate" — a question about an actor, not about a node; AUTHORITY is one of the eight edge types
(all three: `plugins/development-harness/ARCHITECTURE.md`, "The work graph" → "Mechanical checks",
"Projections" and "Edge types"). The contract's holistic evaluation list — dropped rather than
carried forward, see `AMENDMENTS.md` entry A-5 — additionally required that decisions occur under
the correct authority.

**Observed**:

- `Authority` (`model.py#L146-L151`) is `holder` plus `grants`, declared on each `Node`
  (`model.py#L208`). `effects_without_authority` (`model.py#L391-L406`) compares
  `node.side_effects` against `node.authority.grants` — the same node's own declaration. The check
  is satisfied by adding the effect to the grant set.
- Nothing indexes actors. `Node.actor` (`model.py#L195`) is a free string, used only at its
  declaration and in an f-string; two nodes naming the same actor may declare disjoint `grants` with
  no query detecting the contradiction.
- `Descriptor.required_authority` and `granting_authority` (`model.py#L126-L127`) are free strings
  compared with `!=` in `authority_shortfalls` (`model.py#L388`). There is no delegation, no role
  subsumption, and no way to say an orchestrator may act as a judge or may not.
- `EdgeType.AUTHORITY` is read by no query, and `Edge` carries no `Effect` field
  (`model.py#L235-L250`), so an AUTHORITY edge cannot state *which* effect one node grants another.
  The two AUTHORITY defects this multigraph was built against (D1, D2) are both caught by descriptor fields
  on DATA edges (`test_workflow_multigraph_defects.py#L120-L124`, `#L216-L221`); no AUTHORITY edge appears in
  any test graph.
- The load-bearing consequence: D2 is detected only because the modeller wrote
  `grants=[Effect.MUTATE]` on the `update_set_status` node (`test_workflow_multigraph_defects.py#L175`).
  Writing `grants=[Effect.MUTATE, Effect.DECIDE]` there removes the finding and contradicts nothing
  the multigraph can check. The defect's detection rests on the extractor's discretion, which is the
  condition activity 1 exists to rule out.
- The policy the multigraph would need is already data in the sources. `EventKind.written_by`
  (`ledger_spec.py#L366-L373`) names, per event kind, the commands permitted to append it —
  `task.accepted` is `written_by=["accept"]` alone (`ledger_spec.py#L458`), which is exactly the
  statement D1 falsifies.

---

## COMPLETENESS-10 — Hierarchy is nominal; `subgraph_ref` has no referent

**Omission**: the multigraph is declared hierarchical and is not. `subgraph_ref` names nothing, resolves to
nothing, and is traversed by nothing; three further id-bearing fields sit outside reference
integrity.

**Severity**: BROKEN. Basis: DECLARED. The multigraph's own model is "a single typed, hierarchical,
directed multigraph" (`plugins/development-harness/ARCHITECTURE.md`, "The work graph" → "The
model"); the contract it was extracted from additionally required the system to represent
"recursion" and "one node refined into a subgraph" among its other structural properties — a
requirements list dropped rather than carried forward when the contract's content moved into
`ARCHITECTURE.md` (see `AMENDMENTS.md` entry A-5); `reference integrity` is a named mechanical
check (`plugins/development-harness/ARCHITECTURE.md`, "The work graph" → "Mechanical checks").

**Observed**:

- `Node.subgraph_ref: str | None` (`model.py#L209`) appears once in `model.py`, at its declaration.
- `Graph` (`model.py#L262-L272`) has no id, name or key, so no value in the system can be the
  referent of a `subgraph_ref`. There is no registry of graphs and no containment relation.
- `check_reference_integrity` (`model.py#L274-L297`) does not resolve `subgraph_ref`, and neither
  does any query.
- `unreachable_nodes` (`model.py#L476-L492`) does not descend into a subgraph, so a subgraph's
  internals are outside every query and a node reachable only through a parent graph reads as
  unreachable.
- Three further fields hold identifiers the integrity check never resolves:
  `ErrorRoute.handled_by` (`model.py#L165`, "Node id consuming the signal"),
  `SideEffect.target` (`model.py#L156`), and `EvidenceRequirement.supported_by`
  (`model.py#L172`, "Descriptor or node ids"). A dangling value in any of the three constructs
  successfully.

---

## COMPLETENESS-11 — No entry or terminal marking, and unused outputs are uncovered

**Omission**: entries and terminals are not marked, so their existence cannot be checked; and the
declared predicate "a node **or output** is unreachable" is implemented for nodes only.

**Severity**: BROKEN. Basis: DECLARED. `entry and terminal existence` and `dead nodes and unused
outputs` are named mechanical checks (`plugins/development-harness/ARCHITECTURE.md`, "The work
graph" → "Mechanical checks"); `Predicate.UNREACHABLE` (`dh_core/workflow_multigraph/findings.py`) — "a node
or output is unreachable" — is a falsified predicate to report. The contract's holistic evaluation
list — dropped rather than carried forward, see `AMENDMENTS.md` entry A-5 — additionally required
that successful terminals satisfy the goal and that failed terminals preserve enough evidence for
recovery.

**Observed**:

- `unreachable_nodes(self, entry: str)` (`model.py#L476`) takes the entry as a caller argument. No
  field marks a node as an entry, so a graph with no entry, or with several, is neither
  representable nor checkable — the check presupposes the answer it is meant to give.
- `Termination.terminal` (`model.py#L185`) is never read by any query, so terminal existence has no
  mechanical check either.
- Unused outputs have no query. No method iterates `node.outputs` looking for an output that no edge
  carries; the only iterations over `outputs` are `Node.output` (`model.py#L212-L221`), a lookup by
  name, and `_pairs()` (`model.py#L313-L323`), which starts from edges. The predicate
  `UNREACHABLE` (`findings.py#L55`, statement at `findings.py#L101-L103`) is therefore half
  implemented, and the half that is missing is the one that would find a produced value nobody
  consumes.
- The traversal also ignores `activation_guard`, so a node behind a guard that can never be true
  counts as reachable. That is the intersection of this finding with COMPLETENESS-3: with no guard
  semantics, reachability is structural only.

---

## COMPLETENESS-12 — Unnecessary path length cannot be reported at all

**Falsified predicate**: the contract requires unnecessary length to be reported *as an optimisation
finding*, distinct from nonconformance. The multigraph's report vocabulary has no such category, so such an
observation can only be dropped or misfiled as nonconformance.

**Severity**: BROKEN. Basis: DECLARED. The contract's holistic evaluation list — dropped rather
than carried forward when the contract's content moved into `ARCHITECTURE.md`, see `AMENDMENTS.md`
entry A-5 — required that "unnecessary path length is identified", and made the requirement
explicit and normative: "Path length is separated from correctness. A path is nonconformant when
its length violates a constraint or causes outcome failure. Otherwise unnecessary length is an
optimisation finding, so that 'could be shorter' is never reported as 'does not conform'."

**Observed**:

- `Severity` (`findings.py#L130-L136`) has exactly three members — `BROKEN`,
  `CONTRACT_UNSPECIFIED`, `AMBIGUOUS` — all of them conformance verdicts, and its docstring states
  "There is no fourth, and none is reachable except through the rule".
- `SEVERITY_BY_BASIS` (`findings.py#L139-L144`) is total over `ContractBasis`, and
  `test_severity_taxonomy_is_closed` (`test_workflow_multigraph_defects.py#L463-L474`) asserts
  `set(SEVERITY_BY_BASIS.values()) == set(Severity)`, closing the taxonomy in both directions.
- `Finding` (`findings.py#L147-L199`) is the only report record, it is `extra="forbid"`, and its
  `predicate` must be one of the enumerated `Predicate` members — none of which concerns length.
- No path or length structure exists. Searching `model.py` for `path` returns three hits, all
  docstring prose (`#L183`, `#L477`, `#L491`); the word does not appear as a field.
- So the one thing the contract explicitly warns against — collapsing "could be shorter" into "does
  not conform" — is the only outcome the type system permits, and dropping the observation is the
  only alternative.

---

## COMPLETENESS-13 — `ExtractionStatus.ASSUMED` and `ABSENT` cannot be recorded without inventing a span

**Falsified predicate**: the multigraph declares two extraction statuses whose definition is that no source
supports the element, and simultaneously requires every element to carry at least one source span.
The two statements cannot both hold.

**Severity**: BROKEN. Basis: DECLARED — both statements are declarations of the built module. The
contract made the stakes explicit in its model-fidelity validation activity — that activity's
definition was dropped rather than carried forward, see `AMENDMENTS.md` entry A-5, but its
substance was: a perfectly sound graph proves nothing if the extractor silently repaired an
ambiguity or dropped an inconvenient branch. `source-span coverage` is a named mechanical check
(`plugins/development-harness/ARCHITECTURE.md`, "The work graph" → "Mechanical checks").

**Observed**:

- `ExtractionStatus.ASSUMED` is defined as "supplied by the extractor; no source supports it" and
  `ABSENT` as "the sources are silent and the extractor recorded the gap"
  (`model.py#L88-L89`).
- `SourceSpan` is defined as "One place in the sources an element was read from"
  (`model.py#L93-L100`).
- `source_refs: list[SourceSpan] = Field(min_length=1)` is required on `Node`
  (`model.py#L194`), `Edge` (`model.py#L248`) and `Descriptor` (`model.py#L134`). The refusal is
  asserted as intended behaviour by `test_every_element_carries_its_provenance`
  (`test_workflow_multigraph_defects.py#L487-L489`).
- Recording an ASSUMED element therefore requires citing a place it was read from, when by
  definition there is none. The extractor must either fabricate a span or downgrade the honest
  status to `OBSERVED`/`INFERRED` — and the second is the silent repair that activity 1 exists to
  catch. `ASSUMED` and `ABSENT` are, in practice, unusable.

---

## COMPLETENESS-14 — Revision checking passes silently when either side is unversioned; no snapshot or fingerprint entity

**Falsified predicate**: the declared predicate is "an artifact revision does not match the expected
revision". `revision_mismatches` fires only when *both* descriptors name a version, so a consumer
that expects a revision and a producer that names none is reported as consistent.

**Severity**: BROKEN. Basis: DECLARED. `Predicate.REVISION_MISMATCH` (`dh_core/workflow_multigraph/findings.py`)
is the predicate; `snapshot and fingerprint consistency` is a named mechanical check
(`plugins/development-harness/ARCHITECTURE.md`, "The work graph" → "Mechanical checks"); a trace —
per the contract's Traces section, dropped rather than carried forward, see `AMENDMENTS.md` entry
A-5 — was additionally required to bind "target and artifact fingerprints".

**Observed**:

- `revision_mismatches` (`model.py#L441-L456`) guards with
  `if None not in {produced.freshness.version, consumed.freshness.version} and produced.freshness.version != consumed.freshness.version`.
  When the consumer declares `version="P-new"` and the producer declares none, the pair is skipped.
  The revision does not match the expected revision, and nothing is reported.
- `Freshness.version` (`model.py#L104`) is a free string on a descriptor. There is no snapshot
  entity, no fingerprint type, and no environment or host binding anywhere in the package, so
  "snapshot and fingerprint consistency" has only this pairwise string comparison behind it.
- The system under assessment fingerprints deliberately and would exercise the gap:
  `export_cursors.revision` and `export_cursors.projection_hash` (`ledger_spec.py#L341-L351`),
  `plans.base_sha` (`ledger_spec.py#L173`), the `plan.exported`/`plan.imported` payloads
  (`ledger_spec.py#L424-L432`), and the `unchanged` no-op, whose condition is "the projection hash
  equals export_cursors.projection_hash for the target" (`ledger_spec.py#L563-L567`).

---

## COMPLETENESS-15 — A failure signal is not something an edge can carry

**Omission**: `ErrorRoute.signal` is a bare string on a node, while an edge can name only a declared
*descriptor*. There is no way to say "this ERROR edge carries signal S", and the routed-set is
computed as though there were.

**Severity**: BROKEN. Basis: DECLARED. `Predicate.FAILURE_OUTPUT_UNCONSUMED`
(`dh_core/workflow_multigraph/findings.py`) — "a failure output has no consuming edge" — is a falsified
predicate to report; `unhandled failure signals` is a named mechanical check
(`plugins/development-harness/ARCHITECTURE.md`, "The work graph" → "Mechanical checks"); and the
contract required the multigraph to represent "error/recovery/rollback/retry paths" among the system's
other structural properties — a requirements list dropped rather than carried forward, see
`AMENDMENTS.md` entry A-5.

**Observed**:

- `unrouted_failures` (`model.py#L458-L474`) builds
  `routed = {(e.source, e.source_output) for e in self.edges if e.type in {EdgeType.ERROR, EdgeType.RECOVERY}}`
  and then tests `(node.id, route.signal) not in routed`.
- `Edge.source_output` is validated against the source node's declared *outputs* by
  `check_reference_integrity` (`model.py#L293-L294`). `ErrorRoute.signal` (`model.py#L164`) is not an
  output descriptor. So a signal counts as routed only when the node happens to declare an output
  descriptor of the same name — a coincidence of naming, not a modelled relation.
- The direct consequence: an ERROR edge written the way the defect tests write edges — with no
  `source_output`, as at `test_workflow_multigraph_defects.py#L383-L385` — never marks anything routed, so a
  genuinely handled failure is still reported as unhandled. The predicate is falsely claimed.
- `ErrorRoute.handled_by` is the other half and is a node id resolved by nothing (see
  COMPLETENESS-10), so the alternative route to "this signal is handled" is also unchecked.
- The system under assessment routes failures as first-class values: `REASONS`
  (`ledger_spec.py#L500-L583`) is a closed vocabulary of reason codes with a `ReasonKind` deciding
  whether each is a refusal, a no-op or an outcome recorded on a `task.state` event
  (`ledger_spec.py#L479-L497`). None of that structure survives into a multigraph where a signal is a
  string on a node.

---

## COMPLETENESS-16 — One-time versus recurring work has no carrier

**Omission**: nothing on a node or its operation states whether the work is one-shot or recurring,
or whether repeating it is safe.

**Severity**: CONTRACT_UNSPECIFIED. Basis: UNSPECIFIED. The contract's holistic evaluation list —
dropped rather than carried forward when the contract's content moved into `ARCHITECTURE.md`, see
`AMENDMENTS.md` entry A-5 — required that "one-time work is not incorrectly repeated" and
"recurring work is not incorrectly one-shot", but neither appeared in its Mechanical checks list
(`plugins/development-harness/ARCHITECTURE.md`, "The work graph" → "Mechanical checks"), which
permits a property to stay "a bounded judgment or an empirical evaluation until a property is made
precise enough to test" — wording that did carry forward, closing that same section. The contract
therefore did not declare that the multigraph must carry a multiplicity or idempotence facet, and `BROKEN`
would be speculating about a requirement nobody wrote. Recording it so a reducer can decide whether
to make the property precise.

**Observed**:

- No field on `Node` or `Operation` expresses multiplicity or idempotence. Case-insensitive searches
  of the package for `idempot`, `recurring` and `one-time` each return nothing.
- The distinction is live in the sources and unrepresentable:
  `Effect(column="first_renewed", value="now when null")` (`ledger_spec.py#L837`) is a one-time
  write within an attempt, reset to null on each dispatch (`ledger_spec.py#L883`);
  `Effect(column="attempts", value="attempts + 1")` (`ledger_spec.py#L878`) is per-dispatch; and
  `plan.created` versus `plan.replaced` (`ledger_spec.py#L396-L421`) is create-once versus
  replace-and-clear.

---

## COMPLETENESS-17 — `Completeness` is carried on every descriptor and compared by nothing

**Omission**: a producer declaring `Completeness.UNSPECIFIED` into a consumer requiring
`Completeness.TOTAL` is representable and undetected.

**Severity**: CONTRACT_UNSPECIFIED. Basis: UNSPECIFIED. The contract required "completeness
expectations" as a declared facet of every input and output
(`plugins/development-harness/ARCHITECTURE.md`, "The work graph" → "Node record"), and the multigraph
declares it. It names no completeness predicate in `dh_core/workflow_multigraph/findings.py`'s `Predicate`
enum, nor a completeness check in that same document's "Mechanical checks". Whether the facet must
also be *decided* is not stated, so the severity rule forbids `BROKEN`. Recording it because the
gap sits directly on the defect set.

**Observed**:

- `Completeness` (`model.py#L75-L81`) is required on every `Descriptor` (`model.py#L129`) and read
  by no query — it appears in `model.py` once, at its field declaration.
- `Descriptor.confidentiality` (`model.py#L131`) is in the same position: declared per the
  contract's facet list, read by nothing.
- The D3 graph makes the gap concrete. `files_changed` is built with
  `completeness=Completeness.UNSPECIFIED` (`test_workflow_multigraph_defects.py#L262`) and `changed_files`
  with `completeness=Completeness.TOTAL` (`#L279`), whose semantic meaning is "**every** file the
  attempt wrote" (`#L275`). The shortfall is exactly the defect — a partial or unspecified set
  offered where a total one is required — and it is detected only incidentally, by the syntactic
  type check (`markdown-section-body` against `set[path]`). Had the runner's report been typed
  `set[path]`, the completeness shortfall alone would have gone unreported.

---

## Summary

| # | Omission | Severity | Where the basis is stated |
|---|---|---|---|
| 1 | No requirement or intent entity | BROKEN | Projections, Mechanical checks; holistic list (dropped) |
| 2 | No trace record | BROKEN | Projections; Traces section (dropped) |
| 3 | Guards unstructured; no guard query | BROKEN | `Predicate` table, Mechanical checks; requirements list (dropped) |
| 4 | No join semantics; `Cardinality` inert | BROKEN | `Predicate` table, Mechanical checks, Projections; requirements list (dropped) |
| 5 | No loop or cycle representation | BROKEN | Mechanical checks, Projections; requirements list and holistic list (both dropped) |
| 6 | Unrecorded invalidations unreportable | BROKEN | self-contradiction within `dh_core/workflow_multigraph/findings.py` and `model.py` |
| 7 | No state resource; STATE inert | BROKEN | Edge types, Mechanical checks, Projections; holistic list (dropped) |
| 8 | Evidence declared, never checked | BROKEN | Mechanical checks, Projections; holistic list (dropped) |
| 9 | Authority is per-node self-assertion | BROKEN | Mechanical checks, Projections, Edge types; holistic list (dropped) |
| 10 | Hierarchy nominal; `subgraph_ref` unresolved | BROKEN | The model, Mechanical checks; requirements list (dropped) |
| 11 | No entry/terminal marking; unused outputs uncovered | BROKEN | `Predicate` table, Mechanical checks; holistic list (dropped) |
| 12 | Unnecessary path length unreportable | BROKEN | holistic list (dropped) |
| 13 | `ASSUMED`/`ABSENT` require a source span | BROKEN | Mechanical checks; model-fidelity activity (dropped) |
| 14 | Revision check passes when either side unversioned | BROKEN | `Predicate` table, Mechanical checks; Traces section (dropped) |
| 15 | Failure signals are not carried by edges | BROKEN | `Predicate` table, Mechanical checks; requirements list (dropped) |
| 16 | One-time versus recurring work has no carrier | CONTRACT_UNSPECIFIED | holistic list (dropped); absent from Mechanical checks |
| 17 | `Completeness` compared by nothing | CONTRACT_UNSPECIFIED | Node record |

"Dropped" marks contract content that did not carry forward when the assessor contract's
architecture moved into `plugins/development-harness/ARCHITECTURE.md` (see this directory's
`AMENDMENTS.md` entry A-5); each finding above states that content's substance directly since there
is no longer a document section to cite. Every other heading named is under `ARCHITECTURE.md`, "The
work graph". Severities in this table are restated from the findings above; the findings are the
source of truth.

## Where this audit's judgement differs from the contract

One place, stated rather than acted on silently.

The contract's severity rule is written for findings about the system under assessment. This audit
reports on the multigraph itself, and the rule does not say what "declared" means when the subject
is the graph rather than the system it holds. The reading applied here is stated in
"Subject and severity reading" above: the assessor contract (its architecture content now in
`plugins/development-harness/ARCHITECTURE.md`, "The work graph") and the built module's own
docstrings and constraints both count as declarations. A verifier who rejects that reading should
re-derive every `BROKEN` above; the observations do not change, only the basis.

Two consequences of that reading are worth flagging for the reducer, because they are the places a
reasonable verifier could disagree:

- COMPLETENESS-6, -12 and -13 are `BROKEN` on self-contradiction within the built module, not on
  contradiction with the contract. Each names both halves of the contradiction explicitly so the
  disagreement can be adjudicated on the text.
- COMPLETENESS-16 and -17 are held at `CONTRACT_UNSPECIFIED` even though both look, from the
  holistic list, like plain gaps. They are held there because the contract's own escape clause —
  "a bounded judgment or an empirical evaluation until a property is made precise enough to test",
  which carried forward into `plugins/development-harness/ARCHITECTURE.md`, "The work graph" →
  "Mechanical checks" — covers them and neither appears in that same section's mechanical-checks
  list. If a reducer promotes either to `BROKEN`, the promotion should come with the contract text
  that declares the obligation, not with the observation, which is not in dispute.

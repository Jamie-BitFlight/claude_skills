# Model fidelity — the graph IR against `ledger_spec.py` and `sam_schema/core/models.py`

**Verdict: not-faithful**

This assesses model fidelity, a validation activity distinct from finding verification: not
whether the graph is sound, but whether the recovered graph faithfully represents the original
prose, code, configuration and environment. It is also criterion 4 of
`docs/adrs/ADR-3460-1-graph-ir-owns-the-unowned-edges-first.md`.

It does not, on two counts. The schema cannot express four relationships the real system has
(FIDELITY-7 through FIDELITY-10, FIDELITY-13). And the only extraction that exists —
`tests_sam/test_graph_ir_defects.py` — records as `OBSERVED` a set of values that no source
states, that one source contradicts, and whose absence-shaped halves are properties of a four-node
fragment rather than of the ledger (FIDELITY-1 through FIDELITY-5).

None of these findings carries `Found-by: IR`. Every one was found by reading the sources against
`model.py`, not by the graph surfacing it. The IR has, at the time of this pass, been run over
nothing but the four fragments in its own test file.

## Scope of this pass, and what it did not cover

Read in full: the assessor contract (since deleted; its architecture content now lives in
`plugins/development-harness/ARCHITECTURE.md` under "The work graph"); `dh_core/ledger_spec.py`
(1220 lines);
`sam_schema/core/models.py` (908 lines); `dh_core/graph_ir/model.py`,
`findings.py`, `__init__.py`; `tests_sam/test_graph_ir_defects.py`;
`docs/adrs/ADR-3460-1-graph-ir-owns-the-unowned-edges-first.md`. Read in part:
`docs/work-ledger/work-loop.md` lines 25-60; `docs/work-ledger/runner-contract.md` lines 15-35.

Not covered, and therefore not claimed either way: `dh_core/ledger.py` and the conformance suites
(`test_ledger_spec.py`, `test_ledger_fold.py`); the rest of `docs/work-ledger/`; whether the tests
pass (not run); activity 2 (finding verification) and activity 3 (blind completeness).

Every absence claim below names the search that would have found the thing. Where a search was a
`grep` over one file, that is what is stated — an empty grep is a fact about the search, not about
the system.

## A note on the contract, stated rather than worked around

The contract's list of falsified predicates has no entry for a fidelity failure. It enumerates
predicates over a *frozen graph*; fidelity is the question of whether that graph is the right
graph, and it is asked as a separate validation activity from finding verification, not as a
predicate over the graph itself. So most findings below name the contract clause they falsify
instead of a `Predicate` member, and say so in their **Falsifies** line. Where a listed predicate
does apply, it is named.

The severity rule is applied as written: `BROKEN` only where a declared or necessarily implied
predicate is demonstrably false. For a fidelity pass the declaring sources are
`plugins/development-harness/ARCHITECTURE.md` ("The work graph"), `ADR-3460-1`, and the IR's own
field definitions in `model.py` — the last
because `ExtractionStatus.OBSERVED` is *defined* there as "stated by a source span", which makes it
a declared predicate about every element that carries it.

---

## FIDELITY-1 — the D1 fragment is `OBSERVED` from a source that states the opposite

**Falsifies:** `model.py:86` — `OBSERVED = "stated by a source span"`.
**Basis:** DECLARED. **Severity: BROKEN.**

**Source spans**

- `dh_core/graph_ir/model.py:83-89` (the `ExtractionStatus` definitions)
- `tests_sam/test_graph_ir_defects.py:92-128` (`d1_graph`), and `:72` — the `desc()` helper's
  `kw.setdefault("extraction_status", ExtractionStatus.OBSERVED)`
- `dh_core/ledger_spec.py:1169`

**Observed**

`d1_graph` records the `import` node's `accepted` output with
`provenance="the source plan's status column, mapped complete -> accepted"`,
`source_refs=[ledger_spec.py]`, `extraction_status=OBSERVED`.

`ledger_spec.py:1169` — the `import` transition's own effect — states the opposite behaviour:

```text
attempts and accepted from the source, else 0 and 0, so an imported complete task still
faces the judge
```

That is the post-fix specification. D1 was fixed by hand before this extraction was written. The
fragment models the pre-fix behaviour, which is legitimate and necessary — the IR must be able to
hold a broken system — but it labels that modelling `OBSERVED` and anchors it at a file that now
says the reverse. A fidelity reviewer asking "which source states this" gets a file that refutes it.

This is not a quibble about a stale example. `extraction_status` is the field `model.py:84` calls
the one "fidelity review reads first". If a fragment reconstructing a fixed defect is `OBSERVED`,
the field distinguishes nothing.

---

## FIDELITY-2 — values recorded `OBSERVED` that appear in no source at all

**Falsifies:** `model.py:86`, as FIDELITY-1.
**Basis:** DECLARED. **Severity: BROKEN.**

**Source spans**

- `tests_sam/test_graph_ir_defects.py:67-86` (the `desc()`, `node()` and `edge()` helpers, all three
  of which default `extraction_status` to `OBSERVED`)
- `tests_sam/test_graph_ir_defects.py:93-107, 171-199, 338-378`
- `dh_core/graph_ir/model.py:62-89, 146-150`

**Observed**

Searches run over `dh_core/ledger_spec.py` and `sam_schema/core/models.py`, case-insensitive:

| recorded as `OBSERVED` | search | hits |
|---|---|---|
| `actor="importer"`, `granting_authority="importer"` (D1) | `grep -n importer` | 0 |
| every `trust=` value (`PROPOSED`, `VERIFIED`, `AUTHORITATIVE`) | `grep -ic "trust\|verified\|proposed\|authoritative"` | 0 |
| every `completeness=` and `cardinality=` value | `grep -ic "completeness\|cardinality\|confidential"` | 0 |
| `Freshness(version="P-old")`, `version="P-new"` (D4) | `grep -n "P-old\|P-new"` | 0 |

Every `Authority.grants` set in the extraction is likewise extractor-supplied: the `Effect`
vocabulary (`decide`/`mutate`/`approve`/`publish`/`retry`/`terminate`) comes from the assessor
contract, not from the ledger, and no source partitions ledger commands across it. `judge`,
`runner` and `orchestrator` do appear as words in the sources (`ledger_spec.py:638, 1169`;
`:782`; 7 occurrences of `runner`), so those three actor names have an anchor. `importer` has none.

This matters beyond bookkeeping. D1's two `BROKEN` findings are produced by `trust_shortfalls()`
and `authority_shortfalls()`. Both compare facets that no source in this system supplies. The
severity is therefore carried entirely by values the extractor chose, and the field designed to
disclose exactly that says `OBSERVED` on both sides.

Where a real partition *is* recorded, the extraction does not cite it:
`docs/work-ledger/runner-contract.md:15-35` lists the commands a runner runs (`read`, `renew`,
`update`, `finish`) and `docs/work-ledger/work-loop.md:36-56` lists the judge's (`accept`,
`reclaim`, `state`). Together those are a source for the grant sets D1 and D2 turn on. Neither is
in any `source_refs`.

---

## FIDELITY-3 — D3's severity rests on an absence claim a source in the same tree contradicts

**Falsifies:** the severity rule (`plugins/development-harness/ARCHITECTURE.md`, "The work graph"
→ "Severity rule"), by supplying it a false basis; this is also a model-fidelity failure, per the
intro above.
**Basis:** DECLARED. **Severity: BROKEN.**

**Source spans**

- `tests_sam/test_graph_ir_defects.py:317-327` (the D3 finding's `basis_evidence`)
- `docs/work-ledger/work-loop.md:54` (row J17)
- `docs/work-ledger/runner-contract.md:24`

**Observed**

D3 is the one finding the builder's report holds at `CONTRACT_UNSPECIFIED` rather than `BROKEN`,
and the whole of that downgrade rests on one sentence of `basis_evidence`:

```text
no source states that FILES_CHANGED is a path list, nor that reclaim intersects it with a
criterion's files.
```

`docs/work-ledger/work-loop.md:54` states it:

```text
| J17 | TN verdict FAIL | `reclaim --force` on the TN task and on every task whose report's
`FILES_CHANGED` overlaps the files the failing criterion names, each with the regression as
`--response` |
```

and `runner-contract.md:24` declares `FILES_CHANGED:` as one of five named lines the runner writes
into the `Completion Report` section, which is the structure the basis says was never given.

`grep -rn FILES_CHANGED` over the plugin returns 14 hits across `docs/work-ledger/work-loop.md`,
`runner-contract.md`, `plan.md`, `agents/task-worker.md`, `skills/work-milestone/`, and
`ADR-3460-1` itself. Zero of them are in `ledger_spec.py`, which is the only file the D3 fragment
cites — `desc()` defaults `source_refs` to `[SPEC]`, and D3 overrides it nowhere.

So the extractor searched one file, found nothing, and recorded a system-wide negative. Under the
severity rule that negative is the entire difference between `CONTRACT_UNSPECIFIED` and `BROKEN`,
and the builder's own report names this as "the limit worth knowing" without noticing the limit
had already been hit.

I am not asserting D3's correct severity here. Whether J17 plus `runner-contract.md:24` amount to
a *declared* relation, or only to a prose instruction, is a judgement for finding verification.
What is demonstrable is that the basis as written is false.

---

## FIDELITY-4 — D4's two findings assert absences `ledger_spec.py` fills

**Falsifies:** `Predicate.REQUIRED_INPUT_HAS_NO_PRODUCER` and the unrecorded-invalidation
observation, as applied; this is also a model-fidelity failure, per the intro above.
**Basis:** DECLARED. **Severity: BROKEN.**

**Source spans**

- `tests_sam/test_graph_ir_defects.py:338-441` (`d4_graph` and its test)
- `dh_core/ledger_spec.py:401-421` (the `plan.replaced` event kind and the comment under it)
- `dh_core/graph_ir/model.py:245-247` (`Edge.recorded_by`, `default_factory=list`)

**Observed**

`d4_graph` declares `fold_rebuild.sections_clears_record` — "the record naming which tables the
replace emptied" — as a required input with no producer, and reports it under "a required input
has no producer" at `BROKEN`.

`ledger_spec.py:401-412` declares `plan.replaced` with `clears` in its payload, and `:420` explains
it: "``clears`` is the tables it emptied -- ``import`` and ``from-milestone`` write this one kind
and empty different tables." The producer exists in the specification. The fragment has no node for
it, so the query is correct about the fragment and wrong about the ledger.

The same shape governs the two INVALIDATES edges. `unrecorded_invalidations()` fires on
`recorded_by` being empty; `Edge.recorded_by` is `default_factory=list`; and `d4_graph` constructs
both edges through the `edge()` helper without passing it. An unfilled default and an observed
absence are indistinguishable in this model, and here they are the same bytes.

What *is* genuinely under-specified at HEAD, and worth a verifier's attention rather than mine: the
`from-milestone` transition's `effects` (`ledger_spec.py:1191-1200`) name only `plans` and `tasks`,
while the `import` transition's name `plans, tasks, sections` and `export_cursors`
(`:1166-1171`). The `clears` payload field exists for both; which tables `from-milestone --replace`
puts in it is not stated. That is a narrower and better-founded claim than the one D4 makes.

---

## FIDELITY-5 — there is no extraction of the ledger, only four disjoint fragments

**Falsifies:** the model-fidelity validation activity — "does the recovered graph faithfully
represent the original prose, code, configuration and environment?", per the intro above — and
`ADR-3460-1` criterion 4.
**Basis:** DECLARED. **Severity: BROKEN.**

**Source spans**

- `tests_sam/test_graph_ir_defects.py:92-128, 171-203, 252-297, 338-393`
- `dh_core/graph_ir/model.py:325-341, 476-494`

**Observed**

The four graphs are 2, 2, 2 and 4 nodes. They share no node namespace (each reuses the edge id
`e1`), no entry node, and no node in common. `ledger_spec.py` defines 7 statuses, 21 commands, 19
event kinds, 27 reason codes and roughly 40 transitions; none of them is a node anywhere.

Three of the five queries the tests exercise are absence-shaped —
`inputs_without_producer()`, `unrecorded_invalidations()`, and (unused) `unrouted_failures()`. Over
a two-node fragment these report the edges the author did not draw. D2's second `BROKEN` finding is
exactly this: `tasks_status.transition_event` has no producer in a graph containing two nodes,
while `ledger_spec.py:206-210` gives `tasks.status` six producing event kinds
(`task.added`, `task.imported`, `task.dispatched`, `task.finished`, `task.state`, `task.reclaimed`).
The intended finding — that `task.fields` is not among those six — is real and is stated correctly
in D2's `basis_evidence`; the *graph* does not show it, because the graph has no `task.fields` node
either.

`unreachable_nodes()` is never called by any test. Called on any of these fragments it would report
every node but one, which is presumably why.

The consequence for the ADR: criterion 1 asks for a test that fails when a defect is reintroduced.
These tests fail when the *fragment* is edited. Nothing connects a fragment to `ledger_spec.py`, so
reintroducing a defect in the ledger changes no test outcome, and repairing one changes none either
— FIDELITY-1 is the proof, since D1 has already been repaired and the test still passes.

---

## FIDELITY-6 — a descriptor's facets have one provenance field between them

**Falsifies:** no listed predicate. The contract requires eight facets per descriptor and one
`extraction_status` per element (`plugins/development-harness/ARCHITECTURE.md`, "The work graph" →
"Node record"); it does not say what to record when they differ.
**Basis:** UNSPECIFIED. **Severity: CONTRACT_UNSPECIFIED.**

**Source spans**

- `plugins/development-harness/ARCHITECTURE.md`, "The work graph" → "Node record"
- `dh_core/graph_ir/model.py:83-89, 110-134`

**Observed**

`Descriptor` requires `syntactic_type`, `semantic_meaning`, `cardinality`, `provenance`,
`completeness` and `trust`, and carries one `extraction_status` for all of them. In D1's producer
descriptor, `syntactic_type="int(0|1)"` is anchored (`ledger_spec.py:236-241` gives
`tasks.accepted` type `int`), while `trust`, `completeness` and `cardinality` are extractor-supplied
(FIDELITY-2). The element records `OBSERVED`.

`ExtractionStatus.ASSUMED` ("supplied by the extractor; no source supports it") and `ABSENT` ("the
sources are silent and the extractor recorded the gap") are exactly the values these facets need.
`grep -rn "ExtractionStatus.ASSUMED\|ExtractionStatus.ABSENT" --include=*.py` over the plugin
returns one hit: the enum definition itself. Neither is ever used, and with one status per element
neither can be used without demoting the whole descriptor.

A second instance of the same collapse: `provenance` is a required `min_length=1` string meaning
"where the value comes from", and `desc()` defaults it to the *file the extraction was read from*
(`test_graph_ir_defects.py:71`). Five of the ten descriptors take that default, so the facet holds
the provenance of the extraction rather than of the value.

---

## FIDELITY-7 — mutual exclusion over a resource has no construct

**Falsifies:** the `STATE` edge type — "relates shared persistent state, **including mutual
exclusion over a resource**" (`plugins/development-harness/ARCHITECTURE.md`, "The work graph" →
"Edge types").
**Basis:** DECLARED. **Severity: BROKEN.**

**Source spans**

- `plugins/development-harness/ARCHITECTURE.md`, "The work graph" → "Edge types"
- `dh_core/ledger_spec.py:294-299` (the `tasks.ready` derived rule) and `:233` (the
  `conflict_group` column)
- `dh_core/graph_ir/model.py:53-59, 235-249`

**Observed**

The ledger's exclusion is: "no other task with the same non-null `conflict_group` is `in-progress`
or `complete-unaccepted`" (`ledger_spec.py:298`). Three things have to be representable — a named
resource, a set of contenders, and a capacity of one holder subject to a status predicate.

`Edge` is an ordered pair with a free-text `guard`. There is no resource node type, no symmetric or
group edge, no capacity or exclusion field anywhere in `model.py`, and `Cardinality` is the
multiplicity of a *value on a descriptor*, not of holders on a resource. The relation can only be
written as prose in `Edge.guard`, `Operation.summary` or `SideEffect.description`, and no query
reads any of the three (`grep -c "\bguard\b" model.py` = 1, the declaration).

This is the edge type the contract names most explicitly, and it is one of the two the ADR's
Context says the current models *do* own (`conflict_group` is STATE). The IR is meant to take
ownership of it at stage A. It presently cannot hold it.

---

## FIDELITY-8 — there is no join, and `CARDINALITY_CONFLICTS_WITH_JOIN` cannot be expressed

**Falsifies:** `Predicate.CARDINALITY_CONFLICTS_WITH_JOIN` (`dh_core/graph_ir/findings.py`) —
"output cardinality conflicts with the join" — and the control-flow projection's "joins" question
(`plugins/development-harness/ARCHITECTURE.md`, "The work graph" → "Projections") — and
`ADR-3460-1` criterion 2 ("Every falsified predicate in the assessor contract is expressible
against the IR, or is recorded there as out of scope with the reason").
**Basis:** DECLARED. **Severity: BROKEN.**

**Source spans**

- `dh_core/graph_ir/findings.py`, `Predicate.CARDINALITY_CONFLICTS_WITH_JOIN`
- `plugins/development-harness/ARCHITECTURE.md`, "The work graph" → "Projections"
- `dh_core/graph_ir/findings.py:48, 78-80`
- `dh_core/ledger_spec.py:294-299`

**Observed**

`Predicate.CARDINALITY_CONFLICTS_WITH_JOIN` is in the enum with a `PredicateDefinition`, so a
checker may name it. Nothing in `model.py` represents a join: there is no join node, no AND/OR
merge semantics, and `cardinality` is read by no query (`grep -c cardinality model.py` = 1, the
declaration). A checker naming this predicate would have to supply the observation from outside the
graph.

The real system has a non-trivial join. `tasks.ready` is an AND over a dynamically sized dependency
set (`every id in dependencies names a task that is accepted or in SUCCESSFUL_DEPENDENCY`)
conjoined with the exclusion condition of FIDELITY-7. The member condition is not "the predecessor
finished" but "the predecessor reached one of a named set of statuses" — `SUCCESSFUL_DEPENDENCY`
(`ledger_spec.py:56`) plus `accepted`. A CONTROL edge in this IR carries only a free-text `guard`,
so the join's arity, its conjunction, and its per-member status predicate all become prose.

ADR criterion 2 permits recording a predicate as out of scope with a reason. `grep -rn "out of
scope"` over `dh_core/graph_ir/` returns nothing; the three query-less predicates are disclosed in
the builder's session report only, which is not in the repository.

---

## FIDELITY-9 — evidence cannot carry who produced it or which snapshot it describes

**Falsifies:** the evidence-and-provenance projection — "what supports each claim, **who produced
it, which snapshot it describes**" (`plugins/development-harness/ARCHITECTURE.md`, "The work
graph" → "Projections").
**Basis:** DECLARED. **Severity: BROKEN.**

**Source spans**

- `plugins/development-harness/ARCHITECTURE.md`, "The work graph" → "Projections"
- `dh_core/graph_ir/model.py:168-172` (`EvidenceRequirement`)
- `sam_schema/core/models.py:310-314, 368-375, 377-401, 403-427, 429-450`

**Observed**

`EvidenceRequirement` is `{claim: str, supported_by: list[str]}`. A bare string list cannot say who
produced a support, nor which snapshot it describes; the contract asks the projection to answer
both.

The system's evidence machinery is precisely a two-snapshot comparison.
`Plan.acceptance_criteria_structured` holds `AcceptanceCriterion(criterion_id, check_command,
expected_baseline, expected_final)`; `BookendResult` captures one run of that command;
`BookendVerification` holds `t0_exit_code` and `tn_exit_code` and a `CriterionStatus` of
`passed | regressed | pre-existing-fail | newly-passing` (`models.py:368-375`). The difference
between `regressed` and `pre-existing-fail` is not a property of either observation — it is the
claim that the *same check* at *two revisions* changed. `Freshness.version` can label one descriptor
with a revision, but there is no relation joining two observations of one check across revisions,
and `EvidenceRequirement.supported_by` cannot carry either revision.

This is the machinery D3 sits inside. The D3 fragment models the TN send-back as one `EVIDENCE`
edge from a report to a judge, with no criterion, no baseline, and no pair of snapshots — the part
of the system that makes the send-back necessary is not in the graph at all.

`Task.is_bookend` / `bookend_type` — named in ADR-3460-1 as the current home of EVIDENCE — appear
in no fragment (`grep -n "bookend" tests_sam/test_graph_ir_defects.py` returns nothing).

---

## FIDELITY-10 — a specification's quantified rules have no representation in a ground graph

**Falsifies:** no listed predicate. The contract required the IR to represent "recursion" among
the system's other structural properties — a requirements list dropped rather than carried forward
when the contract's architecture content was consolidated into `ARCHITECTURE.md` — but did not say
whether the IR models a specification or one instance of it.
**Basis:** UNSPECIFIED. **Severity: CONTRACT_UNSPECIFIED.**

**Source spans**

- `dh_core/ledger_spec.py:852-860` (`CASCADE` and `REVERSAL`), `:52-53` (`ANY`), `:868-1201`
  (`TRANSITIONS`)
- `dh_core/graph_ir/model.py:235-249`

**Observed**

`ledger_spec.TRANSITIONS` is a matrix quantified over `command × from_status`, and two of its
effects quantify over a transitive closure:

```text
CASCADE:  skipped, on every transitive dependent that is not-started, each with task.state
          reason cascade:T{n}
REVERSAL: not-started, on every dependent still skipped with cascade:T{n}
```

`Edge` names one source and one target. There is no way to write "an edge to every transitive
dependent satisfying P", no variable, and no `ANY`-equivalent for a node's status. Representing
`TRANSITIONS` as edges requires grounding it against a concrete plan whose task set is not known at
specification time — and every `source_refs` in the extraction points at `ledger_spec.py`, i.e. at
the specification.

ADR-3460-1's Decision says `ledger_spec.TRANSITIONS` "becomes derived from the IR rather than
hand-maintained", and criterion 3 requires the derived control-flow projection to reproduce it
exactly. A ground graph cannot derive a quantified matrix. Either the IR needs a quantification
construct, or criterion 3 needs the derivation to run per-plan and the criterion to say so. The
contract does not settle which, so this is `CONTRACT_UNSPECIFIED` rather than `BROKEN` — but it is
the finding most likely to block the ADR.

---

## FIDELITY-11 — ordered checks, waivers, and the refusal/noop/outcome trichotomy are lost

**Falsifies:** no listed predicate. The contract's node record
(`plugins/development-harness/ARCHITECTURE.md`, "The work graph" → "Node record") shows
`preconditions` as an untyped list, so the IR is faithful to the *contract* here; the loss is
against the *system*.
**Basis:** UNSPECIFIED. **Severity: CONTRACT_UNSPECIFIED.**

**Source spans**

- `plugins/development-harness/ARCHITECTURE.md`, "The work graph" → "Node record"
- `dh_core/ledger_spec.py:479-490` (`ReasonKind`), `:802-806` (`Check`), `:873-877` and
  `:1055-1060` (representative check lists)
- `dh_core/graph_ir/model.py:182-188, 199, 205`

**Observed**

A ledger precondition is `Check(reason, unless)`: it names a reason code, it may be waived by a
flag or a fact, and "the first failing check's reason is printed" (`ledger_spec.py:803`) — so order
is semantic, not presentational. Each reason code then carries a `ReasonKind`:

- `REFUSAL` — exit non-zero, no event appended
- `NOOP` — exit zero, no event appended
- `OUTCOME` — exit zero, recorded as the `reason` of a `task.state` event

`Node.preconditions` is `list[str]`. The waiver has no field. The trichotomy has no field:
`ErrorRoute` covers failure signals, and a `NOOP` is not a failure — it is a successful command that
appended nothing, which is a distinct terminal the contract's holistic list cares about ("one-time
work is not incorrectly repeated"). `Termination` offers `terminal: bool` and a free-text `outcome`.

Consequence for a checker: `reclaim` from `not-started` is a `NOOP` (`already-open`) while
`reclaim` from `complete` with `accepted=1` is a `REFUSAL` (`task-accepted`) unless `--force`. In
the IR both are strings in a list, so a guard-coverage query — the one the control-flow projection
names (`plugins/development-harness/ARCHITECTURE.md`, "The work graph" → "Projections") and
`Predicate.GUARD_INCOMPLETE_OR_OVERLAPPING` names in `findings.py` — has nothing to read.

---

## FIDELITY-12 — type satisfaction is string equality, so a value range is invisible

**Falsifies:** no listed predicate. `Predicate.PRODUCER_TYPE_UNSATISFIED` (`dh_core/graph_ir/findings.py`)
asserts "a producer's output type does not satisfy the consumer's input type" without defining
satisfaction.
**Basis:** UNSPECIFIED. **Severity: CONTRACT_UNSPECIFIED.**

**Source spans**

- `dh_core/graph_ir/findings.py`, `Predicate.PRODUCER_TYPE_UNSATISFIED`
- `dh_core/graph_ir/model.py:121, 132, 136-142`
- `sam_schema/core/models.py:44-69` (`STATUS_MAP`), `:72-81` (`TaskStatus`)
- `dh_core/ledger_spec.py:549-553` (`status-invalid`)

**Observed**

`syntactic_type` is a free `str` and `satisfies_type_of` is equality plus an explicitly declared
widening list. The builder's refusal to invent a type lattice is defensible and disclosed. The
untested consequence is that the predicate's truth value is a labelling choice by the extractor.

D3 is the demonstration. `markdown-section-body` vs `set[path]` produces the mismatch; `str` vs
`str` — equally defensible for a markdown body and a path list read out of one — produces none. The
only detected type defect in the suite is therefore a function of how the extractor chose to write
two strings, and nothing in the model constrains that choice or records it as a choice.

The narrowing this cannot see, in the real system: `STATUS_MAP` (`models.py:44-69`) normalises
inbound tokens to canonical status strings, and one of its targets — `"WONT FIX": "wont-fix"` — is
not a member of `TaskStatus`, of `ledger_spec.Status`, or of the five values `state --new-status`
accepts (`ledger_spec.py:549-553`). Producer and consumer would both be labelled `str` or both
`TaskStatus`, and `type_incompatible_edges()` would return nothing either way.

I am recording this as a property of the IR, not asserting the `wont-fix` mapping is a live defect
— I did not trace whether any reader can reach `TaskStatus` construction with that value.

---

## FIDELITY-13 — half the declared edge types are inert, and the semantic queries read node attributes

**Falsifies:** the eight edge types, and "collapsing them into one `then` arrow hides the defects
worth finding" (`plugins/development-harness/ARCHITECTURE.md`, "The work graph" → "Edge types")
and `ADR-3460-1` Decision C ("the IR owns the six unowned edge types").
**Basis:** DECLARED. **Severity: BROKEN.**

**Source spans**

- `plugins/development-harness/ARCHITECTURE.md`, "The work graph" → "Edge types"
- `dh_core/graph_ir/model.py:29-39, 313-321, 359-406, 421, 464, 487`
- `docs/adrs/ADR-3460-1-graph-ir-owns-the-unowned-edges-first.md`, Context and Decision

**Observed**

`grep -n "EdgeType\." dh_core/graph_ir/model.py` returns three query sites: `INVALIDATES` (line
421), `{ERROR, RECOVERY}` (464), `CONTROL` (487). `DATA`, `STATE`, `EVIDENCE` and `AUTHORITY` are
declared in the enum and read by nothing.

`_pairs()` (lines 313-321) — the generator behind `type_incompatible_edges`, `trust_shortfalls`,
`authority_shortfalls` and `revision_mismatches` — ignores `edge.type` entirely. Any edge carrying
both a `source_output` and a `target_input` is checked identically, so an `INVALIDATES` edge with
descriptors would be trust-checked as a data flow, and D3's `EVIDENCE` typing changes no result.
The multigraph's type discipline is load-bearing in three places and decorative everywhere else.

The AUTHORITY case is the one the ADR turns on. `EdgeType.AUTHORITY` exists and is never read;
authority is checked instead through `Node.authority.grants` versus `Node.side_effects`
(`effects_without_authority`) and through two descriptor fields (`authority_shortfalls`). Those are
node attributes. `Authority` has `holder` and `grants` and no delegation field, and every node in
the extraction sets `holder == actor` (`test_graph_ir_defects.py:80`), so "a runner executing a
command the orchestrator authorises" — the shape of D2 — cannot be written as an authority relation
between two parties. It can only be written as one party whose own grant set is short.

Encoding relationships as node attributes is the flattening ADR-3460-1 was written to end. The IR
reproduces it for four of the eight types, including the one whose absence motivated the ADR.

---

## FIDELITY-14 — thirteen required node-record fields are read by nothing, and the extraction defaults them

**Falsifies:** no listed predicate. **Basis:** UNSPECIFIED. **Severity: CONTRACT_UNSPECIFIED.**

**Source spans**

- `dh_core/graph_ir/model.py:110-134, 190-210`
- `tests_sam/test_graph_ir_defects.py:67-86`

**Observed**

`grep -c` over `model.py` for each field returns 1 — the declaration and nothing else — for
`cardinality`, `completeness`, `confidentiality`, `schema_ref`, `activation_guard`, `preconditions`,
`postconditions`, `invariants`, `subgraph_ref`, `operation`, `termination`,
`evidence_requirements`, and `guard`. `subgraph_ref` is additionally never checked for resolution,
so a node may name a subgraph that does not exist without the reference-integrity validator
objecting ("reference integrity" is a named mechanical check —
`plugins/development-harness/ARCHITECTURE.md`, "The work graph" → "Mechanical checks").

In the only extraction, the split falls cleanly along that line. The facets a query reads — `trust`,
`required_authority`, `granting_authority`, `syntactic_type`, `freshness.version`,
`side_effects`, `authority.grants` — are set explicitly, per fragment, to the values that make the
intended query fire. The facets nothing reads sit at helper defaults: `desc()` supplies
`cardinality=EXACTLY_ONE` and `completeness=TOTAL` (`test_graph_ir_defects.py:68-69`), and no
fragment sets `operation`, `termination`, `invariants`, `preconditions`, `postconditions`,
`activation_guard` or `evidence_requirements` at all.

That is the signature of a graph assembled to make queries fire rather than recovered from sources.
It is not evidence of bad faith — the fragments are honestly labelled as falsification cases in the
module docstring — but it means the node record's fidelity value is untested, and a reviewer cannot
distinguish a considered `TOTAL` from a defaulted one.

---

## FIDELITY-15 — every source span in the extraction is a bare 1220-line file path

**Falsifies:** `model.py:98` — `ref` is declared as "Path with an anchor or line range, e.g.
'a.py#L10-L20'"; and "source-span coverage" is a named mechanical check
(`plugins/development-harness/ARCHITECTURE.md`, "The work graph" → "Mechanical checks").
**Basis:** DECLARED. **Severity: BROKEN.**

**Source spans**

- `dh_core/graph_ir/model.py:93-99`
- `tests_sam/test_graph_ir_defects.py:58-59, 63-64`
- `plugins/development-harness/ARCHITECTURE.md`, "The work graph" → "Node record" and
  "Mechanical checks"

**Observed**

`SPEC` and `MODELS` are bare file paths. `spans()` wraps them unchanged, and every `SourceSpan` in
every fragment carries one of the two, with `quote` left empty throughout. The contract's own node
record example uses `"SKILL.md#pass-3"`; the field's description requires an anchor or a line range;
`min_length=1` accepts a filename.

The effect is that source-span coverage is satisfied nominally and discharges nothing. FIDELITY-1
and FIDELITY-3 are both instances: D1's span points at a file whose relevant line
(`ledger_spec.py:1169`) refutes the descriptor, and D3's spans point at the only file in the tree
that does *not* contain `FILES_CHANGED`. Had the spans been line ranges, both would have been
visible at the moment they were written.

---

## Summary

| # | finding | severity |
|---|---|---|
| FIDELITY-1 | D1 fragment `OBSERVED` from a source stating the opposite | BROKEN |
| FIDELITY-2 | values `OBSERVED` that appear in no source | BROKEN |
| FIDELITY-3 | D3's severity rests on a false absence claim | BROKEN |
| FIDELITY-4 | D4 asserts absences `ledger_spec.py` fills | BROKEN |
| FIDELITY-5 | no extraction of the ledger; four disjoint fragments | BROKEN |
| FIDELITY-6 | one `extraction_status` across eight facets; `ASSUMED`/`ABSENT` unused | CONTRACT_UNSPECIFIED |
| FIDELITY-7 | mutual exclusion over a resource has no construct | BROKEN |
| FIDELITY-8 | no join; `CARDINALITY_CONFLICTS_WITH_JOIN` inexpressible and not scoped out | BROKEN |
| FIDELITY-9 | evidence cannot carry producer or snapshot | BROKEN |
| FIDELITY-10 | quantified specification rules have no representation | CONTRACT_UNSPECIFIED |
| FIDELITY-11 | ordered checks, waivers, refusal/noop/outcome lost | CONTRACT_UNSPECIFIED |
| FIDELITY-12 | type satisfaction is string equality; value ranges invisible | CONTRACT_UNSPECIFIED |
| FIDELITY-13 | four of eight edge types inert; authority checked as node attributes | BROKEN |
| FIDELITY-14 | thirteen required fields read by nothing; extraction defaults them | CONTRACT_UNSPECIFIED |
| FIDELITY-15 | every source span is a bare file path | BROKEN |

Against `ADR-3460-1`'s criteria: criterion 4 is **not met** (this pass). Criterion 1 is not met on
the evidence here — the tests fail when a fragment is edited, not when a ledger defect is
reintroduced (FIDELITY-5), and D1 has already been repaired in `ledger_spec.py` with no test
consequence (FIDELITY-1). Criterion 2 is not met for
`CARDINALITY_CONFLICTS_WITH_JOIN` (FIDELITY-8), and no out-of-scope record exists in the repository
for it or for `REQUIRED_FIELD_ABSENT` and `GUARD_INCOMPLETE_OR_OVERLAPPING`. Criteria 3 and 5 were
outside this pass.

Nothing here should be read as a case against the IR's design. The severity taxonomy as computed
data, the refusal of an invented severity, the mandatory `basis_evidence`, and the decision to let
the model hold a broken system are all sound, and FIDELITY-3 is only visible *because*
`basis_evidence` is mandatory. What is missing is a real extraction and five constructs the sources
need.

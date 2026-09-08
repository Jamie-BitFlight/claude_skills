# Findings — finding verification: the falsified predicates, and the severity rule

Lens: the assessor contract's list of falsified predicates. For each, can the schema express it,
and would the falsification test catch a violation? Then: is the severity rule enforced
mechanically, or can a checker report `BROKEN` where the contract requires `CONTRACT_UNSPECIFIED`?

Authority: `dh_core/workflow_multigraph/findings.py`'s `Predicate`/`PREDICATES` and
`plugins/development-harness/ARCHITECTURE.md`'s "The work graph" (the model this multigraph implements),
and `docs/adrs/ADR-3460-1-workflow-multigraph-owns-the-unowned-edges-first.md` criterion 2, which declares the
expressibility obligation these findings are scored against:

> Every falsified predicate in the assessor contract is expressible against the multigraph, or is recorded
> there as out of scope with the reason. — ADR-3460-1, "The dual-home period, and how it ends", L62-63

Subject under assessment: `dh_core/workflow_multigraph/model.py` (494 lines), `dh_core/workflow_multigraph/findings.py`
(199), `dh_core/workflow_multigraph/__init__.py` (72), `tests_sam/test_workflow_multigraph_defects.py` (499), all as of
2026-09-07 on this branch, untracked in git. Severity uses the contract's rule
(`plugins/development-harness/ARCHITECTURE.md`, "The work graph" → "Severity rule"): `BROKEN` only
where a declared or necessarily implied predicate is demonstrably false; otherwise
`CONTRACT_UNSPECIFIED` or `AMBIGUOUS`.

Method. Every claim below was produced by executing the built package, not by reading it: a probe
script constructed graphs against the public API and printed what each query returned, and two
mutants were applied to `model.py` and reverted. Where a claim is an absence, the search that would
have found it is named in the finding. Nothing here was fixed; no builder file was edited.

This document is immutable. A verifier issues amendments or counter-findings against it and does
not rewrite it. It deliberately carries neither of the two ADR-3460-1 finding markers
(`Found-by:` / `Previously-known:`): those attest that the *graph* surfaced a defect in the system
under assessment, and every finding here is a gap in the multigraph deliverable itself. Writing them would
flip ADR-3460-1 criterion 5 on evidence that does not support it.

## Coverage at a glance

| # | contract predicate | query | verdict |
|---|---|---|---|
| 1 | a required input has no producer | `inputs_without_producer` | expressible; over-permissive (PREDICATES-8) |
| 2 | a producer's output type does not satisfy the consumer's input type | `type_incompatible_edges` | expressible; skips unbound edges (PREDICATES-10) |
| 3 | a required field is absent | — none — | not expressible (PREDICATES-2) |
| 4 | output cardinality conflicts with the join | — none — | not expressible (PREDICATES-3) |
| 5 | the consumer requires VERIFIED and the producer supplies PROPOSED | `trust_shortfalls` | expressible; skips unbound edges (PREDICATES-10) |
| 6 | an artifact revision does not match the expected revision | `revision_mismatches` | expressible; skips unbound edges (PREDICATES-10) |
| 7 | an input may be stale and no freshness check exists | `unchecked_stale_inputs` | narrowed and untested (PREDICATES-6) |
| 8 | a failure output has no consuming edge | `unrouted_failures` | defective and untested (PREDICATES-7) |
| 9 | an actor lacks authority for the effect | `effects_without_authority`, `authority_shortfalls` | half expressible (PREDICATES-9) |
| 10 | a branch guard is incomplete, or overlaps another guard | — none — | not expressible (PREDICATES-4) |
| 11 | a node or output is unreachable | `unreachable_nodes` | nodes only, untested (PREDICATES-5) |

The `Predicate` enum and the `PREDICATES` table do cover all eleven. Executing
`tests_sam.test_adr_3460_migration_trigger.contract_predicates()` against
`{d.statement for d in PREDICATES.values()}` returns eleven bullets and eleven statements with a
single symmetric difference, `the consumer requires \`VERIFIED\`...` versus the same sentence
without the markdown backticks. The vocabulary is complete and faithfully worded. The gap is
entirely in the queries.

---

## PREDICATES-1 — three of eleven predicates have no query and no out-of-scope record

**Omission.** ADR-3460-1 criterion 2 requires each contract predicate to be either expressible
against the multigraph or recorded as out of scope with a reason. `REQUIRED_FIELD_ABSENT`,
`CARDINALITY_CONFLICTS_WITH_JOIN` and `GUARD_INCOMPLETE_OR_OVERLAPPING` have neither.

**Severity: BROKEN.** Basis DECLARED — ADR-3460-1 L62-63, quoted above.

**Source spans.** `docs/adrs/ADR-3460-1-...md#L58-L69`; `dh_core/workflow_multigraph/findings.py#L47-L54`
(the three enum members); `dh_core/workflow_multigraph/findings.py#L75-L80,L98-L100` (their table entries);
`dh_core/workflow_multigraph/model.py#L323-L494` (the query block, which contains no query for them).

**Observed.** A taxonomy entry is not an out-of-scope record: `PredicateDefinition` carries
`statement` and `projection` and no field in which a reason could be written, so the three are
indistinguishable in the data from the eight that are implemented. A checker enumerating
`PREDICATES` gets eleven and can report against three it has no way to evaluate.

The out-of-scope record is an absence claim, so here is the search that would have found one:
`grep -rni "out.of.scope|out-of-scope|deferred|not implemented|no query"` across
`docs/graph-ir/`, `dh_core/graph_ir/`, `tests_sam/test_graph_ir_defects.py` and the ADR returned
two hits, both inside the ADR — its own criterion-2 sentence at L63 and "Deferred to A: the
models, the backends..." at L85, which is about scenario A's blast radius, not about a predicate.
`docs/graph-ir/` contains exactly one file, `ASSESSOR-CONTRACT.md` (`find docs/graph-ir -type f`
before this document was written). No record exists in either of the two places the ADR's "there"
could name.

The builder's report states the three "are listed in `PREDICATES` so a checker can report them,
and `test_severity_taxonomy_is_closed` asserts the table covers the enum". That is accurate and
does not satisfy the criterion. Independently, the ADR trigger already scores this criterion
unmet, for a different reason: `evaluate()` looks for `dh_core/graph_ir/predicates.py`, which does
not exist, and prints `contract lists 11 predicates; no predicates.py to answer them`.

---

## PREDICATES-2 — "a required field is absent" is not expressible

**Falsified predicate.** `Predicate.REQUIRED_FIELD_ABSENT` — "a required field is absent".

**Severity: BROKEN.** Basis DECLARED — ADR-3460-1 criterion 2.

**Source spans.** `dh_core/workflow_multigraph/findings.py`, `Predicate.REQUIRED_FIELD_ABSENT`;
`dh_core/workflow_multigraph/model.py#L110-L142` (`Descriptor`).

**Observed.** A field is a member of a schema, and the multigraph holds no schema members. `Descriptor`
carries `syntactic_type: str` and `schema_ref: str | None` — a type name and a pointer — and no
field list, no required/optional partition over fields, and no instance against which presence
could be decided. The contract requires an input or output to declare "syntactic type **or
schema**" (`plugins/development-harness/ARCHITECTURE.md`, "The work graph" → "Node record"); the
multigraph implements only the first half. Nothing in the schema can be interrogated for a missing field,
so the predicate is not merely unqueried, it is unstatable.

---

## PREDICATES-3 — "output cardinality conflicts with the join" is not expressible: joins are absent

**Falsified predicate.** `Predicate.CARDINALITY_CONFLICTS_WITH_JOIN` — "output cardinality
conflicts with the join".

**Severity: BROKEN.** Basis DECLARED — ADR-3460-1 criterion 2.

**Source spans.** `dh_core/workflow_multigraph/findings.py`, `Predicate.CARDINALITY_CONFLICTS_WITH_JOIN`;
`plugins/development-harness/ARCHITECTURE.md`, "The work graph" → "Projections" ("joins" as a
control-flow mechanical question); `dh_core/workflow_multigraph/model.py#L53-L59` (`Cardinality`),
`#L190-L232` (`Node`).

**Observed.** Half the predicate is expressible and half has no representation at all. `Cardinality`
exists with four members and is a required field of every `Descriptor` — and is read by no query:
searching the source of `Graph` for `cardinality` returns nothing. The other half, the join, has no
representation whatever. A node has no join semantics: nothing distinguishes a node that requires
every inbound CONTROL edge from one that requires any, there is no `join` field, no fork/join node
kind, and `Operation.kind` is free text with the examples `'command', 'fold', 'derived-rule'`.
`grep -n join dh_core/workflow_multigraph/model.py` returns three hits, all in docstring prose describing
edges that *join* an output to an input — a different sense of the word. Without a join, the
conflict the predicate names has no second term.

---

## PREDICATES-4 — "a branch guard is incomplete, or overlaps another guard" is not decidable

**Falsified predicate.** `Predicate.GUARD_INCOMPLETE_OR_OVERLAPPING` — "a branch guard is
incomplete, or overlaps another guard".

**Severity: BROKEN.** Basis DECLARED — ADR-3460-1 criterion 2.

**Source spans.** `dh_core/workflow_multigraph/findings.py`, `Predicate.GUARD_INCOMPLETE_OR_OVERLAPPING`;
`plugins/development-harness/ARCHITECTURE.md`, "The work graph" → "Projections" ("guard coverage")
and → "Mechanical checks" ("guard totality and exclusivity"); `dh_core/workflow_multigraph/model.py#L196`
(`Node.activation_guard: str | None`), `#L244` (`Edge.guard: str | None`).

**Observed.** Guards are opaque strings. Totality requires a domain to be covered and exclusivity
requires two guards to be shown disjoint; neither is decidable over free text without a guard
algebra — a variable, a domain, and a complement operation — and the multigraph declares none. The contract's
example guard, `"grade >= tighten"` (`plugins/development-harness/ARCHITECTURE.md`, "The work
graph" → "Node record"), is a relational expression over a named variable, so the sources show the
shape a structured guard would take and the multigraph does not adopt it.
Neither `guard` nor `activation_guard` is read by any query (searched the source of `Graph`; no
occurrence). This is the one omission the builder's report characterises correctly as needing new
machinery ("the last needs a guard algebra"), and I concur with the diagnosis; the severity is
unchanged by the difficulty, because criterion 2 offers "recorded as out of scope with the reason"
as the alternative and that record was not written.

---

## PREDICATES-5 — "a node or output is unreachable" covers nodes only

**Falsified predicate.** `Predicate.UNREACHABLE` — "a node or output is unreachable".

**Severity: BROKEN.** Basis DECLARED — the contract's predicate names two subjects and the
implementation answers for one.

**Source spans.** `dh_core/workflow_multigraph/findings.py`, `Predicate.UNREACHABLE`;
`plugins/development-harness/ARCHITECTURE.md`, "The work graph" → "Mechanical checks" ("dead nodes
and unused outputs"); `dh_core/workflow_multigraph/model.py#L476-L494` (`unreachable_nodes`).

**Observed.** Four distinct shortfalls in one query, three of them silent.

1. **Outputs are not covered.** `grep -n "unused|dead" dh_core/workflow_multigraph/*.py` returns nothing. An
   output descriptor that no edge carries — the contract's "unused outputs" — is reported by
   nothing. The contract states the subject as "a node **or output**".
2. **The entry is unvalidated.** `unreachable_nodes(entry)` seeds `seen = {entry}` without checking
   that `entry` names a node. Probed: a graph of nodes `a` and `b` with a CONTROL edge `a -> b`,
   queried with entry `"does-not-exist"`, returns both `a` and `b` as unreachable and raises
   nothing. A typo in an entry id yields a maximally alarming, entirely spurious result.
3. **A single entry is assumed.** The parameter is one string. A graph with several legitimate entry
   points cannot be asked the question without calling the query once per entry and intersecting the
   results by hand, and no helper does that.
4. **Terminal existence is unchecked.** The contract's mechanical checks require "entry and terminal
   existence" (`plugins/development-harness/ARCHITECTURE.md`, "The work graph" → "Mechanical
   checks"), and its holistic evaluation list — since dropped from the current architecture
   documentation, not carried forward when the contract's content moved — additionally required
   that successful terminals satisfy the goal. `Termination` is a required field of every node and
   is read by no query; searching the source of `Graph` for `termination` returns nothing. Neither
   is `Termination.bound`, so the same dropped list's requirement that loops carry progress
   conditions and termination bounds is likewise unanswerable.

No test exercises `unreachable_nodes`: `grep -n unreachable_nodes tests_sam/test_workflow_multigraph_defects.py`
returns nothing. Shortfalls 2 and 3 would each have been caught by a single test.

---

## PREDICATES-6 — "an input may be stale" is narrowed to required inputs

**Falsified predicate.** `Predicate.STALE_INPUT_UNCHECKED` — "an input may be stale and no
freshness check exists".

**Severity: BROKEN.** Basis DECLARED — the contract distinguishes "an input" from "a required
input", naming `REQUIRED_INPUT_HAS_NO_PRODUCER` and `STALE_INPUT_UNCHECKED` as separate predicates
in `dh_core/workflow_multigraph/findings.py`'s `Predicate` enum, and the node record
(`plugins/development-harness/ARCHITECTURE.md`, "The work graph" → "Node record") separates
`required_inputs` from `optional_inputs`. The narrowing contradicts a distinction the sources make
explicitly.

**Source spans.** `dh_core/workflow_multigraph/findings.py`, `Predicate.REQUIRED_INPUT_HAS_NO_PRODUCER` and
`Predicate.STALE_INPUT_UNCHECKED`; `plugins/development-harness/ARCHITECTURE.md`, "The work graph"
→ "Node record"; `dh_core/workflow_multigraph/model.py#L424-L439` (`unchecked_stale_inputs`), `#L436-L438`
(the `for needed in node.required_inputs` comprehension).

**Observed.** Probed: a node whose *optional* input carries `Freshness(may_be_stale=True)` and an
empty `freshness_check` yields an empty result from `unchecked_stale_inputs`. An optional input is
still read when it is present, and a stale optional input corrupts a decision exactly as a stale
required one does. `Node.input()` (`dh_core/workflow_multigraph/model.py#L223-232`) already unions both
lists — the union the query needs exists and is not used here. No test exercises this query at all
(`grep -n unchecked_stale_inputs tests_sam/test_workflow_multigraph_defects.py` returns nothing), so the
narrowing is not a considered scope decision recorded anywhere; it is unexamined.

---

## PREDICATES-7 — "a failure output has no consuming edge" answers a different question, and can be silenced

**Falsified predicate.** `Predicate.FAILURE_OUTPUT_UNCONSUMED` — "a failure output has no consuming
edge".

**Severity: BROKEN.** Basis DECLARED — the implementation of a declared predicate is demonstrably
wrong in both directions.

**Source spans.** `dh_core/workflow_multigraph/findings.py`, `Predicate.FAILURE_OUTPUT_UNCONSUMED`;
`plugins/development-harness/ARCHITECTURE.md`, "The work graph" → "Mechanical checks" ("unhandled
failure signals"); `dh_core/workflow_multigraph/model.py#L161-L165` (`ErrorRoute`), `#L458-L474`
(`unrouted_failures`), `#L464`
(the `routed` set), `#L290-L296` (edge reference integrity).

**Observed.** The query builds `routed` as `{(e.source, e.source_output) for e in self.edges if
e.type in {ERROR, RECOVERY}}` and then tests `(node.id, route.signal) not in routed`. It therefore
matches an `ErrorRoute.signal` against an `Edge.source_output`, which reference integrity requires
to name a declared *output `Descriptor`* on the source node (L293-294). Three consequences, all
probed:

- **False positive.** A graph with node `a` declaring `ErrorRoute(signal="timeout")` and an ERROR
  edge `a -> b` carrying no `source_output` — a well-formed, obviously-routed failure — is reported
  as `a.timeout` / `handled_by is unset and no edge carries it`. Routing an error by typing the edge
  is not enough.
- **Construction refused.** Adding `source_output="timeout"` to that same edge raises
  `ValidationError`: `edge 'er' names output 'timeout' absent from 'a'`. To clear a signal, the
  extractor must duplicate it as an output `Descriptor` with the same name — a second, redundant
  record of one fact, with its own semantic meaning, provenance, cardinality, trust and
  completeness to invent. Nothing states this requirement.
- **False negative, silent.** The only other escape is `ErrorRoute.handled_by`, and it is not
  checked for reference integrity. Probed: a graph whose sole node declares
  `ErrorRoute(signal="timeout", handled_by="NOPE")` constructs without complaint and returns no
  observation. A dangling node id suppresses the finding permanently. "Reference integrity" is a
  named mechanical check (`plugins/development-harness/ARCHITECTURE.md`, "The work graph" →
  "Mechanical checks") and `check_reference_integrity` enforces it for `Edge.source`, `Edge.target`,
  `Edge.source_output` and `Edge.target_input` — `handled_by` was missed.
  (`EvidenceRequirement.supported_by`, documented as holding "Descriptor or node ids", is
  unvalidated on the same footing and is read by no query, so "evidence-to-claim trace coverage",
  the same mechanical-checks list's next item, is likewise unanswerable.)

No test exercises this query (`grep -n unrouted_failures tests_sam/test_workflow_multigraph_defects.py`
returns nothing). All three behaviours would have been caught by the first test written against it.

---

## PREDICATES-8 — "a required input has no producer" accepts any edge type as a producer

**Falsified predicate.** `Predicate.REQUIRED_INPUT_HAS_NO_PRODUCER` — "a required input has no
producer".

**Severity: BROKEN.** Basis DECLARED — the contract's edge-type table states what each type
relates, and CONTROL relates "what may run after what", not a produced object.

**Source spans.** `plugins/development-harness/ARCHITECTURE.md`, "The work graph" → "Edge types"
(the edge-type table); `dh_core/workflow_multigraph/findings.py`, `Predicate.REQUIRED_INPUT_HAS_NO_PRODUCER`;
`dh_core/workflow_multigraph/model.py#L325-L341` (`inputs_without_producer`), `#L331` (the `filled` set).

**Observed.** `filled` is `{(e.target, e.target_input) for e in self.edges if e.target_input is not
None}` with no filter on `e.type`. Probed: a producer `p` and consumer `c` joined by a single
**INVALIDATES** edge naming `target_input="in"` yields an empty result — the required input counts
as produced by an edge whose declared meaning is "what a result revokes". The same holds for
CONTROL, STATE and AUTHORITY edges. The predicate is about the DATA relation (and, for evidence,
EVIDENCE); the query is about any relation at all. This is the direction that under-reports, and it
is reachable by an extractor that types an edge conservatively.

D2 and D4 both rest on this query returning a non-empty result, so neither existing finding is
invalidated by the defect — the defect only ever hides findings, never invents them.

---

## PREDICATES-9 — "an actor lacks authority" is checked for side effects and not for produced values

**Falsified predicate.** `Predicate.ACTOR_LACKS_AUTHORITY` — "an actor lacks authority for the
effect".

**Severity: BROKEN.** Basis NECESSARILY_IMPLIED — no source states the comparison outright, and an
authority facet that is never compared against the holder constrains nothing, so the contract's
authority-and-effects projection ("who may decide, mutate, approve, publish, retry or terminate" —
`plugins/development-harness/ARCHITECTURE.md`, "The work graph" → "Projections") cannot be
answered without it.

**Source spans.** `plugins/development-harness/ARCHITECTURE.md`, "The work graph" → "Edge types"
(AUTHORITY) and → "Node record" ("Identical schema, incompatible authority") and → "Projections";
`dh_core/workflow_multigraph/findings.py`, `Predicate.ACTOR_LACKS_AUTHORITY`;
`dh_core/workflow_multigraph/model.py#L146-L150` (`Authority`), `#L125-L126` (`required_authority` /
`granting_authority`), `#L375-L389` (`authority_shortfalls`), `#L391-L406`
(`effects_without_authority`).

**Observed.** Authority lives in two disjoint namespaces that are never reconciled.
`Authority.grants` is a `frozenset[Effect]` — a closed enum of six verbs — while
`Descriptor.granting_authority` and `Descriptor.required_authority` are free strings naming an
actor. `effects_without_authority` compares a node's `side_effects` against its own `grants`, in
the enum namespace. `authority_shortfalls` compares two descriptors' strings across an edge. No
query compares a descriptor's `granting_authority` against the producing node's `authority.holder`.

Probed: a node `import` with `actor="importer"`, `holder="importer"`, no grants, declaring an output
`accepted` with `granting_authority="judge"` — a node stamping a value with an authority it does not
hold, which is D1's defect stated node-locally — returns empty from both
`authority_shortfalls` and `effects_without_authority`. It is detectable only through the consumer.

Two consequences for the existing findings:

- `authority_shortfalls` fires only when the **consumer** declares `required_authority`
  (`model.py#L388`). D1's detection is therefore a property of how the consumer node was annotated,
  not of the producer's overclaim. See PREDICATES-11 for what that annotation rests on.
- The query cannot distinguish a wrong authority from an unrecorded one. Probed: a producer whose
  `granting_authority` is `None` against a consumer requiring `'judge'` reports
  `p.out was produced under None`. An absent facet and a mismatched one produce the same
  observation, and the severity rule (`plugins/development-harness/ARCHITECTURE.md`, "The work
  graph" → "Severity rule") turns on exactly that distinction — a missing contract may not be
  reported as `BROKEN`.

---

## PREDICATES-10 — the four pairwise predicates silently skip any edge that does not bind both descriptors

**Omission** (no contract predicate covers it, which is itself the finding).

**Severity: CONTRACT_UNSPECIFIED.** Basis UNSPECIFIED — "producer/consumer schema compatibility"
is a named mechanical check (`plugins/development-harness/ARCHITECTURE.md`, "The work graph" →
"Mechanical checks") but nowhere is it stated that an edge lacking descriptor bindings must be
reported. Under the rule this may not be `BROKEN`, and I record it at the lower severity
deliberately: it is the largest silent-false-negative surface in the deliverable, and saying so
does not license inflating it.

**Source spans.** `dh_core/workflow_multigraph/model.py#L313-L321` (`_pairs`), `#L316-L317` (the `continue`);
`plugins/development-harness/ARCHITECTURE.md`, "The work graph" → "Mechanical checks".

**Observed.** `_pairs` skips every edge whose `source_output` or `target_input` is `None`. Four of
the eight queries — `type_incompatible_edges`, `trust_shortfalls`, `authority_shortfalls`,
`revision_mismatches` — read only `_pairs`. Probed: a DATA edge between a producer supplying
`'prose'`/`PROPOSED`/`granting_authority=None` and a consumer requiring `'set[path]'`/`VERIFIED`/
`required_authority='judge'`, with the edge carrying neither binding, returns empty from all four.
Every semantic defect the multigraph exists to find disappears if the edge is written without bindings, and
no query, no validator and no test reports the unbound edge.

This is the mechanism the model-fidelity validation activity is aimed at — a perfectly sound graph
proves nothing if the extractor silently repaired an ambiguity — and the multigraph provides no signal that
the repair occurred. The builder's model refuses an *incoherent* graph;
an under-bound graph is coherent and empty of findings.

D2's own graph is an instance: its edge `e1` carries `source_output="changed"` and no
`target_input` (`tests_sam/test_workflow_multigraph_defects.py#L202`), so all four pairwise queries skip it.
D2's detection comes from `effects_without_authority` and `inputs_without_producer` instead, which
is sound, but it means the test suite contains an unbound DATA edge and asserts nothing about it.

---

## PREDICATES-11 — descriptor facets are marked OBSERVED against spans that do not state them

**Falsified predicate.** `ExtractionStatus.OBSERVED` is declared to mean "stated by a source span"
(`dh_core/workflow_multigraph/model.py#L86`).

**Severity: BROKEN.** Basis DECLARED — the multigraph defines OBSERVED, and the cited span does not state
the facets carried under it.

**Source spans.** `dh_core/workflow_multigraph/model.py#L83-L89` (`ExtractionStatus`);
`tests_sam/test_workflow_multigraph_defects.py#L58` (`SPEC`), `#L67-L74` (the `desc` helper, whose defaults are
`extraction_status=OBSERVED` and `source_refs=[SPEC]`), `#L92-L128` (D1's descriptors),
`#L171-L199` (D2's), `#L338-L393` (D4's); `dh_core/ledger_spec.py` in whole.

**Observed.** Case-insensitive counts over all 1220 lines of `dh_core/ledger_spec.py`, 2026-09-07:
`authority` 0, `trust` 0, `verified` 0, `proposed` 0. The words `judge` (2), `runner` (7) and
`orchestrator` (2) do occur, all inside free-text summaries and flag descriptions — L638 "the commit
a judge diffs a report against", L782 "the orchestrator's decision without a runner", L1169 "still
faces the judge" — never attached to a column, an event payload or a transition as a declared
authority.

Every D1, D2 and D4 descriptor nevertheless carries `trust` and, where present,
`required_authority` / `granting_authority` under the helper's default
`extraction_status=OBSERVED`, citing `ledger_spec.py` as the only span. Those facets are INFERRED
by the multigraph's own vocabulary — "derived from sources that do not state it outright" (L87). D3 is the
counter-example that shows the distinction was available: its `changed_files` input explicitly
overrides to `ExtractionStatus.INFERRED` (`#L280`), and the test asserts that status (`#L315`).
The other three defect graphs took the default.

Scope of the consequence, stated precisely so it is not over-read. The underlying D1 defect is real
and its basis is genuinely declared at the level of the ledger rule: `SUCCESSFUL_DEPENDENCY`
(`ledger_spec.py#L56`) and the `tasks.ready` rule (`#L295-L299`) declare that only an accepted
dependency releases a dependent, and `task.accepted` is `written_by=["accept"]` alone (`#L961`).
What is not stated by any span is the *vocabulary* — the trust classification and the authority
name — through which the multigraph makes that defect mechanical. So the finding is not that D1 is wrong;
it is that the facets that make D1 machine-detectable are extractor-supplied and labelled as
observed, which is the one signal a fidelity reviewer reads first (`model.py#L84`).

This finding overlaps the model-fidelity lane. It is reported here because it bears directly on
finding verification: the honest extraction status was the only mechanical evidence available about
whether the predicate was ever declared, and the helper default overwrote it.

---

## PREDICATES-12 — the severity rule: `BROKEN` is reachable where `CONTRACT_UNSPECIFIED` is required

This is the question the lens asks directly. The answer is yes, by two independent routes.

**Route A — `basis` is unconstrained free judgement.**

**Severity: CONTRACT_UNSPECIFIED.** Basis UNSPECIFIED — the contract states the rule but says
nothing about how a basis is established, and cannot: "Semantic conformance stays a bounded
judgment or an empirical evaluation until a property is made precise enough to test"
(`plugins/development-harness/ARCHITECTURE.md`, "The work graph" → "Mechanical checks").

**Source spans.** `plugins/development-harness/ARCHITECTURE.md`, "The work graph" → "Severity
rule" and → "Mechanical checks"; `dh_core/workflow_multigraph/findings.py#L108-L135` (`ContractBasis`,
`SEVERITY_BY_BASIS`), `#L145-L160`
(`Finding` config and computed `severity`), `#L149` (`basis_evidence`);
`tests_sam/test_workflow_multigraph_defects.py#L329-L332`.

**Observed.** Severity is a computed field over `basis` with `extra="forbid"`, so a severity cannot
be passed in — `test_severity_cannot_be_invented` (`#L447-L460`) asserts this and it holds. But
`basis` itself is an unvalidated enum choice, and `basis_evidence` is `str` with `min_length=1`:
any non-empty string satisfies it. Probed: a `Finding` with `basis=DECLARED`,
`basis_evidence="no source is cited here at all"`, `source_spans` naming an arbitrary file and
`graph_refs=("does-not-exist", "neither-does-this")` validates and reports `BROKEN`. The builder's
own test demonstrates the same at `#L331` and names it as the model's limit; I confirm the demonstration
and record that it is the whole of the enforcement.

One mechanical discriminator exists and is unused. `ExtractionStatus` on the descriptors a finding
rests on already distinguishes "a source states this" from "the extractor supplied it" — the same
question `basis` asks. Nothing compares them. In the probe above, the consumer descriptor the
finding rests on is `ASSUMED` ("supplied by the extractor; no source supports it",
`model.py#L88`) while the finding claims `DECLARED`, and no validator objects. A cross-check
between `basis` and the extraction statuses of the elements in `graph_refs` would not decide the
judgement, but it would refuse its most obvious abuse.

**Route B — the rule table is a mutable module-level dict.**

**Severity: BROKEN.** Basis DECLARED — the severity rule
(`plugins/development-harness/ARCHITECTURE.md`, "The work graph" → "Severity rule") is stated, and
the implementation permits its inversion at runtime while the test that guards it stays green.

**Source spans.** `dh_core/workflow_multigraph/findings.py#L129-L135` (`SEVERITY_BY_BASIS`), `#L67-L105`
(`PREDICATES`), `dh_core/workflow_multigraph/model.py#L71` (`TRUST_ORDER`);
`tests_sam/test_workflow_multigraph_defects.py#L463-L473` (`test_severity_taxonomy_is_closed`).

**Observed.** The models are frozen (`ConfigDict(frozen=True)` on `Finding`, `Observation`,
`SourceSpan`, `PredicateDefinition`); the three tables that carry the rule are plain `dict`s and
are exported from `__init__.py`. Probed: assigning
`SEVERITY_BY_BASIS[ContractBasis.DECLARED] = Severity.CONTRACT_UNSPECIFIED` and
`SEVERITY_BY_BASIS[ContractBasis.UNSPECIFIED] = Severity.BROKEN` — a straight inversion of the
contract's rule — leaves both assertions in `test_severity_taxonomy_is_closed` true
(`set(SEVERITY_BY_BASIS) == set(ContractBasis)` and
`set(SEVERITY_BY_BASIS.values()) == set(Severity)`), because the inversion is a permutation and the
test checks only coverage. A `Finding` that reported `BROKEN` before the assignment reports
`CONTRACT_UNSPECIFIED` after it, and vice versa. `TRUST_ORDER` and `PREDICATES` are mutable on the
same footing; the `TRUST_ORDER` assertion at `#L468-L473` does pin its ordering, so that table is
guarded and the severity table is not.

The remedy shape is a `MappingProxyType` or a frozen model and an equality assertion against a
literal, not a coverage assertion. I did not apply it.

---

## PREDICATES-13 — a `Finding` is not bound to the `Graph` it claims to be about

**Omission.**

**Severity: CONTRACT_UNSPECIFIED.** Basis UNSPECIFIED — the contract made finding verification a
separate activity performed against "the frozen graph and the sources" and did not declare that
the binding be mechanical (that activity's own definition was scaffolding for a one-off exercise
and was dropped rather than carried into `ARCHITECTURE.md`; see this directory's `AMENDMENTS.md`
entry A-5).

**Source spans.** `dh_core/workflow_multigraph/findings.py#L138-L199`
(`Finding`), `#L154` (`graph_refs`, defaulting to `()`); `dh_core/workflow_multigraph/__init__.py#L43-L72`
(`__all__`, which exports no report or finding-set type).

**Observed.** There is no type joining a set of findings to the graph they were computed over. A
`Finding` carries `subject` and `expected`/`observed` as free strings and `graph_refs` as an
optional tuple of strings that nothing resolves — probed above with two ids naming nothing.
`Finding.from_observation` copies an `Observation`'s three strings and drops every link to the
`Graph` instance the observation came from. The consequence for this lens is precise: activity 2 of
report validation, "given the frozen graph and the sources, is each claimed disconnect actually
present?", cannot be started from the artifacts the package produces, because no artifact records
which graph was frozen. A verifier must re-run the queries by hand and match strings.

The graph itself has no identity either — no id, no fingerprint, no source-set field — so the
contract's requirement that a trace bind "target and artifact fingerprints" (part of the Traces
section, dropped rather than carried into `ARCHITECTURE.md`; see `AMENDMENTS.md` entry A-5) has
nothing to fingerprint.

---

## PREDICATES-14 — three of the eight queries have no test, and the taxonomy-to-contract match is unasserted

**Omission.**

**Severity: CONTRACT_UNSPECIFIED.** Basis UNSPECIFIED — ADR-3460-1 criterion 1 requires a
falsification test for each of the four known defects (L60-61), which exists; no source requires a
test per query, nor a test pinning the taxonomy to the contract text.

**Source spans.** `tests_sam/test_workflow_multigraph_defects.py` in whole;
`dh_core/workflow_multigraph/model.py#L424-L439,L458-L474,L476-L494`;
`dh_core/workflow_multigraph/findings.py#L67-L105`; `tests_sam/test_adr_3460_migration_trigger.py#L45-L58`
(`contract_predicates`, which parses the contract's bullets and is used only for a count).

**Observed.** `grep -n` over the defect test file for each query name: `inputs_without_producer`,
`type_incompatible_edges`, `trust_shortfalls`, `authority_shortfalls`, `effects_without_authority`,
`revision_mismatches` and `unrecorded_invalidations` are all exercised; `unchecked_stale_inputs`,
`unrouted_failures` and `unreachable_nodes` appear nowhere. Those three are exactly the queries in
which PREDICATES-5, -6 and -7 found defects, and each defect is of the kind a first test catches.

Falsification quality of the tests that do exist is good, and I verified it rather than taking the
builder's report for it. Two mutants applied to `model.py` and reverted: replacing
`Descriptor.satisfies_type_of`'s body with `return True`, and replacing the `TRUST_ORDER`
comparison in `trust_shortfalls` with `False`. Result: `3 failed, 5 passed` —
`test_d1_...`, `test_d3_...` and `test_severity_cannot_be_invented` all failed, the last because it
reads `d1_graph().trust_shortfalls()[0]`. The tests are falsifying, not merely green. `model.py` was
restored from a byte copy taken before the mutation.

Separately, nothing asserts that `PREDICATES` still corresponds to the contract's bullet list.
`test_severity_taxonomy_is_closed` checks `set(PREDICATES) == set(Predicate)` — the table against
the enum, both of which live in the same file. I ran the comparison the repo has no test for:
`contract_predicates()` against `{d.statement for d in PREDICATES.values()}` differs only by the
markdown backticks around `VERIFIED` and `PROPOSED` in one bullet. The correspondence holds today
and is maintained by hand; adding a twelfth bullet to the contract would leave every test green.

---

## PREDICATES-15 — hierarchy: `subgraph_ref` resolves to nothing, and no predicate descends

**Omission.**

**Severity: AMBIGUOUS.** Basis AMBIGUOUS. The multigraph's own model is "a single typed, hierarchical,
directed multigraph" (`plugins/development-harness/ARCHITECTURE.md`, "The work graph" → "The
model"); the contract that model was extracted from additionally required the system to represent
"one node refined into a subgraph" — a requirement dropped rather than carried forward when the
contract's content moved into `ARCHITECTURE.md` (see `AMENDMENTS.md` entry A-5). Whether recording
an unresolvable *reference* to a subgraph satisfies "must represent" admits two plausible readings,
and neither the dropped requirement nor its replacement settles which: on one, the node record's
`subgraph_ref: null` field (`plugins/development-harness/ARCHITECTURE.md`, "The work graph" →
"Node record") is the whole requirement and it is met; on the other, a hierarchy that no query can
traverse is a hierarchy in name. The rule forbids `BROKEN` where the sources admit several
readings, so I record AMBIGUOUS rather than choose. The consequence below is the same under either
reading.

**Source spans.** `plugins/development-harness/ARCHITECTURE.md`, "The work graph" → "The model" and
→ "Node record" and → "Projections" ("keep the richer property graph for semantics");
`dh_core/workflow_multigraph/model.py#L209` (`subgraph_ref: str | None`), `#L273-L297`
(`check_reference_integrity`), `#L262-L268` (`Graph`).

**Observed.** `subgraph_ref` is a free string. `Graph` has no id, so there is no namespace a
reference could resolve into, and `check_reference_integrity` does not attempt it — probed: a node
with `subgraph_ref="G-nope"` constructs without complaint. No query reads the field (searched the
source of `Graph`; no occurrence). Every predicate is therefore single-level: a node refined into a
subgraph is, to all eleven predicates, a leaf, and everything inside it is outside the analysis
with no signal that anything was skipped. `unreachable_nodes` in particular cannot cross a
refinement boundary in either direction. Recursion, named in the same contract sentence, has the
same status.

---

## What a verifier should re-run

Each finding above names the search or the probe that produced it. The cheapest re-checks:

- `cd plugins/development-harness && uv run python -c "import sys; sys.path.insert(0,'.'); from tests_sam.test_adr_3460_migration_trigger import evaluate; [print(c.met, c.key, c.evidence) for c in evaluate()]"` — criterion 2's state (PREDICATES-1).
- `grep -c -i -e authority -e trust -e verified -e proposed dh_core/ledger_spec.py` per word — PREDICATES-11's counts.
- `grep -n unchecked_stale_inputs -e unrouted_failures -e unreachable_nodes tests_sam/test_workflow_multigraph_defects.py` — PREDICATES-14's absences.
- The probe behaviours in PREDICATES-5, -6, -7, -8, -9, -10, -12 and -15 each reduce to constructing
  one small `Graph` against the public API and printing the query result; each finding states the
  construction and the output.

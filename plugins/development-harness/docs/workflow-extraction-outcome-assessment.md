# #3223 outcome-first architecture assessment — source-traced baseline

**Assessment scope:** historical `main` at `cd563c240ecaffa11d7eb749debdba8c669ede16`, plus #4095's dispatch flow at `e0b62965e13bcbdfd0648ae810d7dbb7ed3f1947`. #4101 reducer mechanics refer separately to the [original experiment source binding](./trusted-workflow-extraction-design.md#experiment-source-binding). This is a source inspection and design assessment, **not** a live extractor evaluation. No agent run, corpus-wide ground truth, or cost benchmark has been performed.

## 1. Outcome and discriminating questions

A trusted graph must answer, for a pinned source revision: which actor acts; in what order; under what condition; which document is loaded next; what tools and durable artifacts are produced/consumed; what failure/terminal paths exist; and where a trace remains ambiguous. It must preserve links across Mermaid, prose, nested references, and agent-profile handoffs. Each material node/edge requires source evidence and a verified, unknown, or contradicted disposition. The graph must account for the declared source scope and reject stale publication.

Success is measured by fidelity to complete execution paths and accurate unknowns, **not** by parse success, agreement count, or node count.

## 2. Source-first reference trace: multi-perspective review

The following is a manually derived *candidate reference trace* to be independently checked before promotion to a gold corpus.

| Route | Source | Expected behavior | Critical relationship |
|---|---|---|---|
| Invocation -> missing `--diff` | `references/dispatch-flow.md`, DiffCheck | Abort usage before plan | stop condition |
| Diff resolution -> SourceCheck failure | same, Files/SourceCheck | Abort input error before plan | source-revision failure |
| SourceCheck success -> empty files | same, ParseFiles/EmptyCheck | Abort before plan | conditional stop |
| Nonempty files -> Context -> CreatePlan | same, Context/CreatePlan; `SKILL.md` | Pin revision/authority; create T1..T5, T5 depends on T1..T4 | artifact and dependency |
| T1..T4 -> Collect | same, Parallel/W1..W4/Collect; worker profiles | Four concurrent task-worker dispatches, profile-mediated verdict writes to Review Results | actor ownership and barrier |
| Collect -> SynthDispatch -> WaitT5 | same, SynthDispatch; `agents/review-synthesizer.md` | T5 task-worker loads synthesis profile, reads T1..T4 verdict sections, writes T5 Punch List | two-hop profile and artifact handoff |
| T5 -> ParseCheck -> Check6 -> Check7 | same; `review-verdict-contract` | Validate schema, verdict conservation, exact finding wording; failure exits nonzero | correctness gate |
| GateMissing/Reject/AllSkip | same | Missing/REJECT fail, all-SKIP passes with warning, otherwise pass | terminal classification |

The reference must expand the loaded `dh:start-task`, `dh:review-synthesizer`, and verdict-contract documents before it is considered complete. The table is intentionally **not** asserted as full ground truth.

## 3. Observed gap in current generated data

The committed `docs/workflow-layers/G4-concurrency.json`, `L0-forks.json`, and `docs/dh-workflow-graph.json` contain zero matches for `review-synthesizer`, `synthesis-worker`, `Punch List`, and `SourceCheck` in the inspected snapshots. The assembled graph has 234 nodes and 440 edges but cannot answer the T5 or SourceCheck questions above. The assembler can reproduce those stale layer inputs; it cannot infer missing semantics.

The current schema describes step nodes but the assembled node-type counts contain no step nodes. This is a **representation/coverage question** requiring investigation, not proof that the assembler is defective.

## 4. Candidate methods assessed against the outcome

| Required capability | Candidate or observed mechanism | Assessment |
|---|---|---|
| Source scope and revision | Enumerate paths + digests | Partly specified; the inspected source does not establish strict end-to-end coverage or freshness enforcement. |
| Mermaid/prose/nested links | Agent-led reconstruction with rule slices | Plausible, but unvalidated on complete routes. |
| Actor and two-hop handoff | Extract and join agent identities | Described, with no working producer established by this assessment. |
| Exact source provenance | UTF-8 byte spans and digests | Necessary; proves citation presence, not the asserted relationship. |
| Semantic identity/equivalence | Exact tuple corroboration in draft #4101 | Insufficient: distinct anchors or wording for one relationship cannot corroborate, and one quote does not prove a relationship. |
| False interpretation detection | Worker agreement | Insufficient: correlated error can survive. |
| Omission detection | Worker overlap | Insufficient: shared omissions require independent route coverage or negative checks. |
| Staging and publication | #4101's exclusive-create staging output; older A6-F proposal | The experiment writes a new staging file only. A6-F is a proposal for a later checked publication boundary, not an established publisher. |
| Repeatability | Frozen-input deterministic reducer | Valid local property, not proof of live semantic repeatability. |

**Decision:** do not select an implementation architecture from this assessment. The next decision is #4103's comparison of scoped tracing, revision-bound reusable evidence, and broad extraction against the completed #4102 corpus. Preserve source/provenance checks as candidate controls. A deterministic Mermaid parser is eligible only where the comparison shows that it improves an explicit-syntax or omission check; it is not a replacement for prose and cross-file interpretation.

## 5. Falsification cases before architecture approval

- Same relationship described in Mermaid and prose using different words/anchors: should resolve to one semantic edge with both evidence anchors, not two unrelated tuples.
- One quoted span supporting two distinct transitions: must not merge solely by location.
- Nested `Load X.md` expansion with an implicit return/handoff: trace must continue across files.
- Task-worker dispatch whose actual behavior comes from profile load: actor must be resolved across two hops.
- Two workers agree on an invented edge: source-span presence alone must not verify the edge.
- All workers omit a failure branch: independent source coverage check must flag omission.
- Renamed/missing file or changed SHA: publication must fail closed.
- A source change adding T5 or SourceCheck: freshness check must detect missing generated graph edges.

## 6. Comparison-first handoff

1. **Complete #4102 first.** Independently trace the bounded required routes, at their matching revisions, with actors, transitions, terminals, unknowns, citations, and controls frozen before adjudication. This document's reference table remains a candidate, not a gold set.
2. **Run #4103 second.** Use those traces to compare A (scoped trace), B (revision-bound reusable evidence), and C (broad extraction plus graph) for the same questions. Measure fidelity, uncertainty handling, affected-consumer accuracy, elapsed time, model calls, and maintenance only where the evaluation exposes them. Do not invent thresholds or savings.
3. **Select the smallest adequate architecture from the comparison.** #4104 designs typed relations only if the selected option needs them. A graph, persistent evidence store, parser, live producer, checker, or publication path is not a prerequisite unless the comparison establishes its need.
4. **Keep #3223's required publication outcome outstanding, not this handoff's next implementation step.** The issue still requires re-extraction of affected G4, L0, and L1 layers before the matching graph/explorer rebuild and checked publication. A #4103 method choice can constrain how that is delivered, but cannot waive it; define and independently validate the admission, caller, destination, freshness, and publication boundary before claiming #3223 progress.

## 7. Recommendation for draft #4101

Keep it an experiment. At the [bound original #4101 revision](./trusted-workflow-extraction-design.md#experiment-source-binding), the reducer mechanically validates frozen source spans, counts distinct-worker occurrences, returns threshold survivors in `verified`, and retains below-threshold exact candidate records in `unverified_items`. That is useful occurrence evidence, not semantic relationship truth, route coverage, or a graph contract. #4103 can decide whether this primitive is reused, changed, or rejected; this document does not prescribe a typed reducer or production pipeline.

## 8. Open decisions requiring evidence

- Which downstream consumers require complete graph coverage for correctness versus human navigation?
- What authoritative criteria distinguish two semantically equivalent edges across differing anchors?
- How will an independent checker detect missing edges rather than merely validating supplied candidates?
- What is the allowed publication behavior when ambiguity remains?
- What is the runtime cost of the three-worker design on a complete reference route?

**Conclusion:** A6's separation of semantic extraction, deterministic verification, and single-writer publication is aligned with the outcome. Its current candidate schema and corroboration rule are not sufficient to establish source-faithful graph completeness. Architecture approval should wait for the reference traces and falsification results.

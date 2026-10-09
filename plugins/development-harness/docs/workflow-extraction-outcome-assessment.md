# #3223 outcome-first architecture assessment — source-traced baseline

**Assessment scope:** current `main` at `cd563c240ecaffa11d7eb749debdba8c669ede16`, plus #4095's dispatch flow at `e0b62965e13bcbdfd0648ae810d7dbb7ed3f1947`. This is a source inspection and design assessment, **not** a live extractor evaluation. No agent run, corpus-wide ground truth, or cost benchmark has been performed.

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

## 4. A6 design evaluated against outcome

| Required capability | Current plan/mechanism | Assessment |
|---|---|---|
| Source scope and revision | Enumerate paths + digests | Partly specified; missing strict end-to-end coverage/freshness enforcement |
| Mermaid/prose/nested links | Three agent workers with rule slices | Plausible, unvalidated on complete routes |
| Actor and two-hop handoff | Extract and join agent identities | Described, no working producer established |
| Exact source provenance | UTF-8 byte spans and digests | Necessary; proves citation presence, not semantic relationship |
| Semantic identity/equivalence | Exact tuple corroboration in draft #4101 | **Insufficient:** differing anchors/phrasing for same relationship cannot corroborate; same quote does not prove relation |
| False interpretation detection | Two-worker agreement | **Insufficient:** correlated error can survive |
| Omission detection | Three-worker overlap | **Insufficient:** two workers may omit the same branch; need independently traced coverage/negative checks |
| Typed graph assembly | A6-F future publisher | Not implemented |
| Freshness and publication | Deterministic staging, independent checker | Correct boundary, no complete executable pipeline |
| Repeatability | Frozen-input deterministic reducer | Valid local property, not proof of live semantic repeatability |

**Decision:** retain agent-led semantic reconstruction as the leading design, but do not promote the draft reducer schema as the final graph relationship contract. Preserve deterministic source/provenance checking and independent publication. Do not substitute a syntax parser for semantic extraction. An optional Mermaid parser may be used only to check explicit syntax or expose missed edges, subject to a measured benefit.

## 5. Falsification cases before architecture approval

- Same relationship described in Mermaid and prose using different words/anchors: should resolve to one semantic edge with both evidence anchors, not two unrelated tuples.
- One quoted span supporting two distinct transitions: must not merge solely by location.
- Nested `Load X.md` expansion with an implicit return/handoff: trace must continue across files.
- Task-worker dispatch whose actual behavior comes from profile load: actor must be resolved across two hops.
- Two workers agree on an invented edge: source-span presence alone must not verify the edge.
- All workers omit a failure branch: independent source coverage check must flag omission.
- Renamed/missing file or changed SHA: publication must fail closed.
- A source change adding T5 or SourceCheck: freshness check must detect missing generated graph edges.

## 6. Revised design gate and implementation order

1. **Gold set first:** independently trace 2–3 complete routes (multi-perspective including T5/SourceCheck, grooming, and a prose-heavy handoff). Record authoritative source revision, actors, edges, terminals, unknowns and citations.
2. **Graph contract second:** derive typed relationship shapes from those traces, including multi-anchor evidence, conditional edges, expansion/return, provenance, contradictions, and unknowns. Check compatibility with existing L0/L1/G1–G8 schema and consumers.
3. **Producer third:** implement source inventory, live runtime admission, isolated agent extraction, frozen evidence, and typed candidate output. Reuse existing tools where they satisfy a verified contract.
4. **Checker fourth:** independently trace paths and verify both claimed and missing edges; check consumer semantics, not only byte spans. Treat consensus as a signal, not proof.
5. **Publication fifth:** stage, validate, atomically publish through A6-F, assemble graph, and test revision freshness.
6. **Benchmark:** compare against gold traces for edge precision/recall, terminal/actor correctness, missing links, false confidence, latency and model cost. No numeric acceptance thresholds are justified until baseline measurements exist.

## 7. Recommendation for draft #4101

Keep it draft. The current reducer is a useful experiment in source-byte validation but is not yet a reliable workflow relationship reducer. Do not extend it further until step 2 defines typed semantic identity. The initial implementation should be revised or replaced based on measured compatibility with the gold set. This avoids building a technically correct subsystem that cannot deliver the graph.

## 8. Open decisions requiring evidence

- Which downstream consumers require complete graph coverage for correctness versus human navigation?
- What authoritative criteria distinguish two semantically equivalent edges across differing anchors?
- How will an independent checker detect missing edges rather than merely validating supplied candidates?
- What is the allowed publication behavior when ambiguity remains?
- What is the runtime cost of the three-worker design on a complete reference route?

**Conclusion:** A6's separation of semantic extraction, deterministic verification, and single-writer publication is aligned with the outcome. Its current candidate schema and corroboration rule are not sufficient to establish source-faithful graph completeness. Architecture approval should wait for the reference traces and falsification results.

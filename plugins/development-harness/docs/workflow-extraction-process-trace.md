# #3223 workflow extraction: forward/backward/adversarial process trace

**Scope and status:** source inspection of the maintained refresh skill, extraction rules, methodology, current scripts, reducer profile, assembler, and current graph layers on `main` at `cd563c240ecaffa11d7eb749debdba8c669ede16`. This is a **static trace**, not a successful live execution or a complete corpus-wide audit. The earlier outcome assessment in `workflow-extraction-outcome-assessment.md` supplies the required graph contract.

## Forward trace: current documented execution

| Step | Authority / input | Actor / intended action | Output / handoff | Observed gap or contradiction |
|---|---|---|---|---|
| 0. Invoke refresh | `skills/meta-workflow-graph-refresh/SKILL.md` | Consuming agent reads COVERAGE then methodology | Choose Tier 1 or Tier 2 | Entry point only routes to prose; no executable orchestration |
| 1. Classify change | `references/COVERAGE.md` | Agent selects affected L0/L1/G1–G8 | Layer list | T5/SourceCheck require source re-extraction; simple assembly cannot supply missing nodes |
| 2. Enumerate source scope | `scripts/enumerate_scope.py` | Deterministic BFS follows known patterns | Scope markdown | Missing/unresolved paths warn and continue; time-based output. No strict freshness/source digest admission |
| 3. Derive extraction shapes | `workflow-trace-methodology.md` | Read sources first, derive schema from observed structure | Proposed per-layer shape | No persisted approval/evidence contract proving shape covers implicit handoffs |
| 4. Assign extraction workers | `.claude/rules/workflow-extraction.md`, methodology | 3 independent workers, twofold rule overlap | Rule slices and jobs | Historical planner may create per-rule workers; replacement dispatcher absent. Assignment coverage not runtime-enforced |
| 5. Extract per file | methodology, retired extractor references | Workers interpret Mermaid/prose and expand file links | Raw candidate findings | Worker/profile executable absent; slices can separate necessary context; no complete-route omission oracle |
| 6. Corroborate | `plugins/plugin-creator/skills/ensemble-rule-review/scripts/reduce.py` at the declared `cd563c240ecaffa11d7eb749debdba8c669ede16` source revision | Deduplicate by normalized location; retain only findings with `weight >= keep_threshold` | Survivor report only; raw per-worker reports remain the source of singleton evidence | The reducer does not emit a singleton list. With threshold 2, every weight-one finding is dropped. The caller's default threshold 1 can include weight-one survivors in the ranked report, but they are not a separate singleton output. Normalized-location grouping is not semantic identity, and evidence/provenance plus cross-anchor equivalence remain insufficient. |
| 7. Verify/reduce | `agents/workflow-extractor-reducer.md` | Sonnet verifies quotes and writes fragment | `items`, `unverified_items` | **Direct conflict**: ≥80% quote overlap and PLAUSIBLE promotion versus reviewed A6 exact-byte/fail-closed rule. Profile count semantics also distinguish plausible and confirmed inconsistently |
| 8. Join relationships | methodology Phase C | Resolve dispatch → agent → tool, including two-hop task-worker profile | Cross-file spans and edges | No maintained executable join with explicit unknown/contradiction handling. |
| 9. Merge layer | `scripts/merge_layer.py` | `merge_fragment(layer_path, fragment)` replaces one source contribution at the caller-selected `layer_path` through `write_layer()` | Layer JSON at that supplied path | The helper provides atomic replacement capability, but the inspected source shows no admitted production caller or publication gate. Its direct test callers do not establish publisher authority. |
| 10. Assemble | `docs/assemble_graph.py` | Read layer JSON, build graph and explorer | `dh-workflow-graph.json` | Assembles supplied inputs; it does not reconstruct omitted relationships. |
| 11. Proposed publish/verify boundary | Older A6 proposal | Independently check graph freshness and atomically publish after an admitted producer/checker | A later trusted graph at a pinned revision | A6-F is a proposed later boundary, not established current behavior. No completed trusted dispatcher/checker/publication evidence is recorded here. |

## Backward trace from required outcomes

| Required outcome | Producer | Checker | Status |
|---|---|---|---|
| Every reachable actor and action | Semantic extractor + join | Complete-route independent trace | Not established |
| Every condition and terminal path | L0/L1 + G1 extraction | Branch/terminal coverage against source | Not established |
| Nested reference and two-hop handoff | Phase C join | Recursive source-following check | Described, not executable |
| Source-backed edges | Worker evidence | Exact span + semantic entailment | Byte check in draft; semantic checker missing |
| Explicit unresolved/contradicted edges | Typed relationship contract | Negative/contradiction oracle | Missing |
| Source revision freshness | Strict source inventory + digests | Manifest-to-graph revision check | Missing end-to-end |
| Atomic verified publication | A6-F | Independent publication checker | Missing |
| T5 and SourceCheck graph fidelity | Targeted re-extraction | Source-to-graph comparison | Fails current snapshot (no matching strings) |

## Adversarial walkthroughs (design probes; not executed)

1. **Nested prose handoff:** a source says 'load referenced workflow and resume after validation' without a machine key. A syntax-only parser misses the return edge; an agent must trace both sides and an independent checker must demand the continuation.
2. **Two-hop actor:** orchestrator dispatches task-worker, which loads review-synthesizer profile. Recording only task-worker misses actual behavior ownership. Must follow profile load and T5 artifact write.
3. **Correlated omission:** all three workers skip a failure branch. Threshold-two corroboration sees no candidate and cannot detect the omission. Independent source-branch inventory must flag it.
4. **False relationship with valid quote:** a worker cites the exact 'Load X.md' phrase but asserts that X runs unconditionally. Byte match passes; semantic/condition checker must reject it.
5. **Same relationship, different evidence:** two workers cite distinct spans for the same handoff. Exact tuple equality splits them into singletons. A typed relationship identity is required before corroboration.
6. **Unresolved reference:** enumerator warns and continues. A trusted publication gate must reject or explicitly classify the missing route as an unresolved coverage blocker.
7. **Retry/partial publication:** producer fails after staging some fragments. Existing published graph must remain unchanged; A6-F must verify and atomically commit a complete coherent snapshot.
8. **Stale graph:** T5/SourceCheck exist in source but not in layers. Reassembling old layers passes mechanical checks but fails semantic freshness.

## Confirmed findings from source contracts

**F1 — P0: no end-to-end executable producer.** Refresh skill and methodology route to retired workers; no admitted live dispatcher and independent semantic checker established. Outcome blocked.

**F2 — P0: no completeness oracle.** Two-worker corroboration validates repeated candidates, not omitted branches. No demonstrated complete-route source coverage gate.

**F3 — P0: unestablished relationship identity.** The historical reducer keys findings by location; the #4101 experiment keys frozen claims by exact tuple and returns below-threshold records in `unverified_items`. Neither establishes an identity for equivalent cross-anchor relationships or distinct same-span semantics.

**F4 — P1: incompatible verifier policy.** Historical Sonnet reducer permits fuzzy and plausible promotions, while the older A6 proposal requires exact byte evidence and deterministic checks. The conflict is evidence for #4103 to evaluate; it does not authorize a current implementation choice.

**F5 — P1: scope and publication trust gaps.** The enumerator warns on missing references. `merge_layer.py` can atomically replace a caller-selected layer file, but capability alone does not identify its caller as an authorized publisher. A fail-closed inventory and a sole publication boundary remain unimplemented design requirements, not a defect proven solely by this helper.

**F6 — P1: revision-scoped graph drift.** T5 is present on pinned `main` but absent from its committed graph layers. SourceCheck is present in #4095, not that `main` revision; verify its graph freshness against the matching #4095 revision rather than claiming current-main drift.

**F7 — P2: authority ambiguity.** Historical PRD, active extraction rule, and later reviewed A6 plan disagree about worker/reducer ownership. Document the controlling contract before dispatch.

## Potential gaps requiring additional evidence

- Whether any active consumers depend on graph completeness for runtime correctness versus visualization.
- Whether existing tools outside the inspected files already provide a usable independent semantic oracle.
- Whether the graph schema can represent all prose-dependent conditions without incompatible consumer changes.
- Exact runtime cost and precision/recall of live extraction; no empirical baseline available.

## Next decision sequence

1. Complete #4102's independent, revision-pinned T5/SourceCheck, grooming, and prose-heavy reference corpus, retaining unknowns and contradictions.
2. Use #4103 to compare the scoped-trace, revision-bound evidence, and broad-graph configurations against that corpus, including the adversarial probes where they apply.
3. Select the smallest adequate architecture from observed results. A typed identity, runtime admission, worker extraction, parser, completeness checker, staging path, or publication boundary is follow-on work only when the selected option requires it.
4. Keep #3223's desired source-faithful and checked-publication outcome open. Do not refresh layers or call a graph current from this static assessment.

## Evidence limitations

This report establishes contradictions and missing implementation contracts from inspected source. It does **not** prove that every workflow path was enumerated or that the proposed design passes the probes. Promote candidate findings to verified only after independently replaying them on the pinned source and capturing the result.

# Design assessment: trusted workflow extraction

## Outcome versus implementation

The goal of #3223 is a current, source-faithful workflow graph with verifiable extraction, not merely a reducer. The current PR implements **only a frozen-evidence admission/reduction primitive**. It cannot extract, validate a graph schema, publish a graph, or demonstrate that #4095's SourceCheck and earlier T5 routes are represented. Do not treat it as closing #3223.

The reviewed A6 plan is sound in separating untrusted model output from deterministic source validation and single-writer publication. It is over-prescriptive where it assumes three agents and a threshold of two alone establish correctness. Correlated workers can corroborate a false interpretation, and exact source quotes prove source presence, not semantic truth. Keep these checks as necessary gates, not sufficient verification.

## Implementation boundary

- Frozen source inventory and digest validation; reject unsafe paths and malformed worker data.
- Corroborate exact source-backed candidate tuples by distinct assigned worker. Isolate singletons.
- Deterministically serialize staged results; never publish layer files.
- Run independent source-to-graph semantic checking and a freshness gate before any generated graph is trusted.

## Remaining producer and publication work

1. G0 runtime admission: verify live model CLI, credentials, network, tool permissions, cost budget, and isolated checkout; record source revision and environment. Fail closed when unavailable.
2. Build the real dispatcher and three isolated worker processes. Verify the rule-slice coverage and freeze raw worker outputs with digests and provenance. Do not rely on worker labels as proof of independence.
3. Extend the contract beyond source-span tuples to typed fork/branch/dispatch/consumer relationships. A quote-only reducer cannot produce L0/L1/G4 graph fragments.
4. Add deterministic semantic reconciliation and a checker that re-reads complete source routes, including file-reference expansion, T5 synthesis and SourceCheck. Check missing paths and unsupported edges, not just positive citations.
5. Validate two reductions of frozen outputs for byte identity. Compare independent live ensembles with a declared semantic oracle, not byte identity.
6. Stage typed layer fragments, then let A6-F atomically publish after its own checker passes. Reassemble and verify the graph's source revision and coverage.
7. Update outdated extractor instructions and ensure the existing CI checks verify freshness. Keep #3223 open until graph publication is independently verified.

## Risks and alternatives

The three-worker/threshold-two approach is a policy choice from the reviewed plan, not a universal statistical guarantee. For strictly parseable Mermaid edges, a deterministic parser plus source-backed tests may be simpler and more reliable; use agents only for prose-dependent transitions and ambiguous cross-file contracts. Consider this alternative before implementing an expensive agent-only extractor. A staged, source-aware parser with targeted agent adjudication may reduce cost while increasing determinism.

A separate implementation PR for the dispatcher and another for publication would keep the producer boundary independently testable. Neither should replace #4095's review-gate evidence until the final graph is regenerated.

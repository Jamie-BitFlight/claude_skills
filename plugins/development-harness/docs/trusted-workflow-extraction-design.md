# Design assessment: trusted workflow extraction

## Outcome and observed experiment boundary

#3223 requires a current, source-faithful workflow graph and explorer: re-extract the affected G4, L0, and L1 layers for the T5 synthesis change at the matching source revision, then rebuild and check the graph/explorer publication. The existing graph cannot stand in for that re-extraction. This stabilization does not deliver those artifacts and cannot waive them.

The #4101 experiment is narrower: at its declared source revision, `reduce_workflow_evidence.py` validates frozen source bytes and exact spans, counts distinct-worker occurrences, emits threshold survivors in `verified`, retains below-threshold exact candidate records in `unverified_items`, and exclusive-creates a caller-supplied staging file. It does not extract routes, establish semantic relationships, validate a graph schema, refresh layers, or publish a graph. It does not close #3223.

Worker agreement and exact quotations are useful occurrence evidence, not semantic truth or completeness. Three agents and a threshold are therefore candidate controls, not an architecture decision or a universal correctness guarantee.

## Comparison-first decision boundary

The next work is #4102's independently traced, revision-pinned corpus followed by #4103's comparison of scoped tracing, revision-bound reusable evidence, and broad extraction plus graph. The comparison must select the smallest adequate architecture for demonstrated tasks; it must not inherit the older A6 proposal as a prerequisite.

Only an evidenced selected need can justify further design work. For example:

- A typed relationship contract is a #4104 question if the selected option must represent cross-anchor, conditional, or uncertain relations.
- A deterministic parser is eligible for explicit Mermaid syntax or a measured omission check, but not as a substitute for prose or cross-file interpretation.
- A persisted evidence store, live producer, semantic checker, or broad graph-maintenance mechanism is justified only if the comparison demonstrates its benefit and defines its caller, destination, admission, freshness, and independent checking boundary. That method decision cannot remove #3223's already-required affected-layer re-extraction and checked graph/explorer publication.

## Status

No current shipped publisher is established here: the older A6-F description is a proposal, not evidence of implementation. Its absence does not change #3223's required graph/explorer outcome. #3223 remains open, and this assessment neither completes #4102, selects #4103's architecture, designs #4104's production relationship model, nor refreshes the affected layers or graph.

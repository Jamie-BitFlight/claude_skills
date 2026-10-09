# Workflow reference corpus — candidate trace

This PR begins #4102 with a **source-linked candidate**, not an independently verified gold set. Do not use this trace as evaluation ground truth until a second reviewer traces the pinned sources without seeing `candidate-trace.json`, and discrepancies are adjudicated.

The source revision and exact Git blob identities are in `manifest.json`. `candidate-trace.json` captures ten consequential relationships from the review entry point, including failure exits, parallel dispatch, T5 synthesis, and the punch-list gate. Its scope deliberately excludes the full `dh:start-task` implementation and downstream consumers, so it is **not a complete execution trace**.

## Promotion requirements

1. Independent reviewer receives the manifest's source revision, source paths and required outcome, **not** the candidate trace or its expected relationships.
2. Record the independent result separately with evidence and unresolved cases.
3. Compare both traces; adjudicate each difference against source, including missing branches and profile-mediated handoffs.
4. Add the grooming and prose-heavy reference workflows with the same process.
5. Freeze a new versioned corpus and grading contract; keep gold answers out of candidate extractor inputs.
6. Evaluate correctness, omissions, uncertainty, terminal/actor fidelity and cost only after independent labels exist.

Related: #3223, #4102, #4103, #4104 and research PR #4110.

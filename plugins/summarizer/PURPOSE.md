# Summarizer purpose

Produce useful summaries and syntheses from inspected evidence without silently changing source
claims, losing material qualifications, or concealing missing coverage. Support short human-facing
presentations and machine-readable output through the same fidelity rules.

The owner requested this implementation scope in issue #3923. This is a bounded product contract,
not fabricated answers to the separate mission interview in #541.

## Outcomes

- Source content, acquisition failures and inspected scope remain distinguishable.
- Claims retain source support, material numbers/conditions/units, and uncertainty through handoffs.
- Direct and delegated execution use the same source methodology and selected format.
- Deterministic checks reject structural, reference, identity and coverage inconsistencies.
- Reports distinguish those checks from independently established factual and live-host behavior.

Keep all six public skill names, three agent names and six presentation formats. Prefer a local,
lightweight path for a simple summary; persist evidence when handoffs, chunking or auditability need
it. Semantic judgment stays with an evidence-reading evaluator, not keyword heuristics.

MCP wrapping (#258), four-host distribution certification (#3497), autonomous source-command
execution, and independent fact-checking through unrequested research are outside this change.

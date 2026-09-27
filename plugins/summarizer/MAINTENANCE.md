# Summarizer maintenance

## Boundaries to preserve

Keep public skill/agent names and the existing fidelity/template paths stable; callers outside this
plugin reference them. Agent wrappers must load source methods, not regrow independent workflows.
Changing a format requires checking its template, output validator and caller controls together.
Changing evidence fields requires the versioned Pydantic model and consumer tests, not a copied schema.

The shared reference load is intentional: direct source-skill invocations and fresh agents need the
same contracts. Moving rules only into the main router would disconnect those entrypoints.

## Conservation against summarizer-train-v1

The original ledger is retained in [change-contract.md](./evals/change-contract.md); this table is
candidate disposition, not a replacement inventory. These are source-level mappings, not independent
behavioral verification.

| Original IDs | Carrier / disposition |
| --- | --- |
| S1-S4 | PRESERVED in fidelity rules, source skills and evidence-record coverage/support fields |
| S5 | PRESERVED as evidence-backed synthesis and scoped relay; contradictory blanket prohibition corrected |
| S6 | PRESERVED with extraction support separated from source reliability/currentness |
| S7 | PRESERVED six templates and default; structured-only contradictions corrected by explicit precedence |
| S8-S10 | PRESERVED source-specific extraction tables and acquisition/error paths |
| S11 | PRESERVED in synthesis with qualification-level support and copied-origin distinction |
| S12 | PRESERVED direct/agent routes; agent bodies RELOCATED into canonical source methods |
| S13 | PRESERVED caller envelope, artifact reference and observation/conclusion separation |
| S14 | PRESERVED metrics API; UTF-8 split probes, zero-tail expansion and silent replacement decoding corrected by regression tests |
| S15 | PRESERVED structural checks; heuristic semantic verdicts replaced by explicit evidence review |

Remove duplicated examples only after their decision rule and applicable edge conditions remain
reachable. Do not interpret this mapping as a green live-host, activation or fidelity evaluation.

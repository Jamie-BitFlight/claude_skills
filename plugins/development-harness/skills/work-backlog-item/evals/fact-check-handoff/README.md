# Fact-Check handoff evaluation

These are **unexecuted behavioral scenarios**, not pytest results. The structural
regression in `tests/test_fact_check_handoff_contract.py` (relative to the DH plugin
root) checks the authored interfaces and bundled routes only.

## Run boundary

Use isolated checkouts of the baseline and candidate, pinned to exact commits.
Run the installed DH fact-checker and grooming finalizer in fresh contexts against
a disposable sandbox item/store, never the production backlog. Pin model, harness,
effort, tool access and source fixtures equally across variants. Record unavailable
capabilities as unexecuted, not passing. No evaluation requires unrestricted network
access: expose each fixture's source through the same read tools in both variants.

For each case, give the subject only `prompt` and the fixture material necessary for
its role. The fixture is synthetic task data, not a preverified model answer. The
`expected_output` field is grader-only; do not load this suite into the subject's
context. Expand `*_variants` into separate executions. Withheld source content is
not secretly available through another tool when the case specifies failure.

For producer cases, retain the tool-visible evidence, attempted writes and actual
persisted section. Start a fresh finalizer that reads the persisted result through
the real sandbox backend; do not paste a corrected producer result into its prompt.
For consumer fault cases, seed the named malformed records into the sandbox store
and run the same finalizer. Keep unrelated required grooming sections valid so a
failure is attributable to this handoff. Record the actual call order, including
any recovery and description synchronization.

Run repeated isolated samples on supported models where practical. Keep an unseen
variation of claim order, punctuation, whitespace and near-matching hypotheses out
of the tuning set. Describe the observed sample size; do not treat consensus as a
proof. Grade without revealing baseline/candidate identity where possible.

## Claims to check independently

- Literal field names and verdict values satisfy the consumer contract.
- Original claim identity survives narrowing, serialization and readback.
- Each hypothesis maps to its own active evidence; RCA precedence stays unchanged.
- Unavailable, malformed or conflicting evidence cannot become confirmation.
- Evidence details and source attribution survive the handoff.
- Ad-hoc use, write scope and failed-delivery handling preserve existing authority.

Keep correctness and evidence coverage separate from qualitative judgments and
telemetry (loaded context, calls, elapsed work, retries). Do not calculate an
aggregate quality score. Source-template checks, simulated fixtures and live
agent/persistence runs support different claims; name which was actually executed.

A candidate is not behaviorally certified merely because its Markdown is shorter,
its examples parse, or the structural tests pass. Resolve a demonstrated regression
before accepting the affected claim; retain uncertainty when execution is unavailable.

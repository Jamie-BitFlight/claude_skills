# Workflow reference corpus

This directory is the bounded #4102 source-reference corpus. [trace-reference.json](./trace-reference.json) accepts only relations with exact replayable source spans and explicitly retains rejected raw relations for all four required cases without selecting a raw lane, inferring runtime behavior, or selecting #4103/#4104 architecture.

## Roles

1. A blind extractor receives a materialized, allowlisted source-packet/question bundle and separately supplied pinned source material identified by those packets. It never receives raw lanes, the complete reference, adjudications, controls, grades, or adjacent proposed claims. It produces a frozen complete-trace candidate that follows [blind-candidate-contract.json](./blind-candidate-contract.json) and passes its emitted `scripts/validate_candidate.py` schema validator before handoff.
2. A separate adjudicator receives that produced candidate, the frozen reference, the grading contract, and the source material needed for byte replay. [grade_controls.py](./scripts/grade_controls.py) emits correct, missed, false, and replay outcomes for relations, terminals, actors, artifacts/consumers, uncertainty/contradictions, and consumer change status.
3. Historical raw-lane records and claim-projection receipts remain attributable evidence. They are not independent complete-trace verification.

Use [scripts/materialize_verifier_bundles.py](./scripts/materialize_verifier_bundles.py) with the invocations declared in [verifier-input-manifest.json](./verifier-input-manifest.json), then validate the emitted directory before handing it to another actor.

## Current boundary

The corpus contains a source-only complete-trace reference and deterministic full-trace controls. It is **not accepted or independently verified as a complete trace** until separately authored valid receipts bind a blind candidate, source replay, and final tracked-byte integrity.

The immutable historical receipts cover six bounded claim projections, not seven. Their wording is retained as historical evidence and does not establish complete traces. The historical scalar-control receipt is invalid because it invokes removed grader options; it is retained only as an invocation record. [verifier-input-manifest.json](./verifier-input-manifest.json) and [complete-trace-verifier-input.json](./complete-trace-verifier-input.json) define the producer and adjudicator boundaries. The corpus makes no general-completeness, runtime, production-ontology, publication, #4103, #4104, or #4105 claim.

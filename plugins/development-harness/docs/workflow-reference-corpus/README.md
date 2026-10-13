# Workflow reference corpus

This directory is the bounded #4102 source-reference corpus. [trace-reference.json](./trace-reference.json) accepts only relations with exact replayable source spans and explicitly retains rejected raw relations for all four required cases without selecting a raw lane, inferring runtime behavior, or selecting #4103/#4104 architecture.

## Roles

1. A blind extractor receives only its case source packet, question, source revision, and pinned source material. It never receives raw lanes, the complete reference, adjudications, controls, or grades.
2. The fresh source-fidelity verifier receives the frozen reference and the immutable replay candidate declared in [complete-trace-verifier-input.json](./complete-trace-verifier-input.json), plus source material for byte replay. [grade_controls.py](./scripts/grade_controls.py) emits correct, missed, false, and replay outcomes for relations, terminals, actors, artifacts/consumers, uncertainty/contradictions, and consumer change status. That candidate is not a blind-extractor output.
3. Historical raw-lane records and claim-projection receipts remain attributable evidence. They are not independent complete-trace verification.

## Current boundary

The corpus contains a source-only complete-trace reference and deterministic full-trace controls. It is **not accepted or independently verified as a complete trace** until separately authored valid receipts bind a blind candidate, source replay, and final tracked-byte integrity.

The immutable historical receipts cover six bounded claim projections, not seven. Their wording is retained as historical evidence and does not establish complete traces. The historical scalar-control receipt is invalid because it invokes removed grader options; it is retained only as an invocation record. [complete-trace-verifier-input.json](./complete-trace-verifier-input.json) prepares the fresh verifier boundary. The corpus makes no general-completeness, runtime, production-ontology, publication, #4103, #4104, or #4105 claim.

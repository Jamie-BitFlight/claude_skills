# Workflow reference corpus

This directory is the bounded #4102 source-reference corpus. Its primary data is the [case manifest](./corpus-manifest.json), [lane-boundary adjudications](./case-adjudications.json), [fresh-verifier input manifest](./verifier-input-manifest.json), and [grading contract](./grading-contract.json); this document does not duplicate their records.

The existing [candidate manifest](./manifest.json) and [candidate trace](./candidate-trace.json) remain observed seed material. They are not gold, do not establish complete workflow coverage, and stay outside blind trace/check executor input.

## Record flow

1. A case source packet pins the declared revision, blobs, byte passages, and source question.
2. Independent source-only trace and check records freeze before comparison and record their actual exposure boundary.
3. Source adjudication retains the raw observations, records lane-level source boundaries, and preserves shared omissions and disagreements without treating actor self-checks as independent verification.
4. Independent grading replays the cited source and runs separate correct and defective controls under the grading contract.

No completion is asserted beyond the case manifest's bounded acceptance boundary. This corpus makes no general-completeness, runtime, production-ontology, publication, #4103, #4104, or #4105 claim.

## Bounded acceptance

The declared claim projection and its controls have passed the independent receipts indexed by [evidence/receipts/manifest.json](./evidence/receipts/manifest.json). This is acceptance of the revision-bound, declared claim projection only. It does not promote the corpus to a general workflow-completeness claim, establish runtime behavior, or close #3223.

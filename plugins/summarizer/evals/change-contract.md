# Summarizer change contract

Contract revision: summarizer-train-v1. Recorded before candidate implementation.
Target baseline: `f2a6f81c9fd640230810c1c36a4562b244141e1c`.
Method revision: skill-lapidary `b9eec540947e9970fe99d4d5f10effcdd0f9e3d2`.
Scope approval: owner requested the four dependent PRs in issue #3923. This is not
an approval of an unrun evaluation or completion of the mission interview (#541).

## Outcomes and falsifiers

| ID | Required outcome | Discriminating failure |
| --- | --- | --- |
| R1 | The requested presentation format survives all routes. | A valid JSON/TL;DR payload is validated as structured Markdown. |
| R2 | Validation checks the intended result, not incidental source prose. | Output text selects its own validator, or an unassigned artifact is accepted. |
| R3 | Observations retain source identity, coverage and material qualifications. | A missing source becomes nonexistent, or a qualifier gains an unsupported citation. |
| R4 | Direct and delegated execution reach the same source methodology. | An agent independently narrows a skill's PDF/image/data capability. |
| R5 | Large-source coverage and data aggregates are mechanically checkable. | A missing middle chunk or unsampled null is reported as complete. |
| R6 | Structural, semantic and live-host evidence remain distinct. | A fixture or an authored scenario is reported as a passing live agent run. |

## Original semantic inventory

These original meanings are the pre-change comparison ledger, not candidate grades.

| ID | Original carrier | Meaning |
| --- | --- | --- |
| S1 | summarizer/SKILL.md, fidelity Rule 1 | Read actual content before summarizing; do not infer from a path. |
| S2 | source skills, fidelity Rule 2 | Extract evidence before abstracting; claims trace to source locations. |
| S3 | fidelity Rule 3, relay | Preserve exact material counts, ratios, identifiers and failure reasons. |
| S4 | fidelity Rule 4 | Separate searched absence, inaccessible content and nonexistence. |
| S5 | fidelity Rule 5, synthesis, relay | Prevent lossy chains while allowing requested synthesis and bounded relay. |
| S6 | fidelity Rule 6 | State confidence and its rationale; expose partial access and ambiguity. |
| S7 | router, six templates | Default to structured; support bullets, TL;DR, JSON, table and outline. |
| S8 | file-summarization | Retain code, config, data, documentation and binary/PDF strategies. |
| S9 | url-summarization | Fetch actual content; report specific acquisition errors and partial access. |
| S10 | image-summarization | View images; preserve visible text, labels, directions and uncertainty. |
| S11 | synthesis | Deduplicate, cluster, attribute, preserve conflicting versions and qualifications. |
| S12 | router, agents | Support autonomous delegation and direct conversational execution. |
| S13 | relay | Preserve caller status, artifact references, observations and attributed conclusions. |
| S14 | metrics script | Preserve public metrics/excerpt/strategy interfaces and visible errors. |
| S15 | hook | Check summarizer output structure without affecting unrelated agents. |

## Explicitly authorized corrections

Selected-format requirements replace unconditional structured-only instructions.
Source-grounded negative claims are permitted; phrase matching is not a semantic oracle.
Synthesis may transform evidence-backed findings without silently losing qualifications.
Caller-controlled budgets replace invented parallelism/chunk limits; legacy metric strategy
labels remain compatibility hints. An unavailable check is not a successful check.

## Evaluation rules

Run positive cases and deliberate violations under the same contract. Record exact revision,
command, output and environment. Keep source analysis, deterministic tests, fresh semantic
review, and actual host execution separate. Do not infer cost improvements from word counts.
Unmeasured fidelity, latency, activation and host portability remain UNVERIFIED.

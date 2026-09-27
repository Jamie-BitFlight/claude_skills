# Process Siren lifecycle regression cases

Status: NOT_RUN. These are retained task cases for findings 5–8 in #3959, not observed fresh-agent behavior. Compare the frozen original and candidate plugin in fresh contexts under equivalent tools and source fixtures. Give respondents the task and scenario, not the expected decision. Independently grade against the existing approved goals and contracts. Record model/host, method/target revisions, actual writes, raw outputs/traces, and isolation limits.

## Task status versus target assessment

Scenario: the caller requires first-line `STATUS: DONE | PARTIAL | BLOCKED`. A read-only review finds a reachable publication path bypassing an approved validation gate. Task: "Review this release process and return the requested report."

Expected: completed review can report DONE, but its payload/artifact retains INVALID, the failed claim and evidence, and Target writes: NONE. No conflicting last-line domain STATUS or implied readiness. A partial improvement must preserve unfinished dependent work even when its report is complete.

## Candidate oscillation and no progress

Scenario: A satisfies ordering claim C1 but fails C2; B satisfies C2 but fails C1; the next proposed correction restores A under the same contract and evidence. Task: "Improve this process against both claims."

Expected: detect the repeated material candidate and stop that affected loop with a non-ready assessment and a useful missing-evidence/decision report. Cosmetic node renames do not reset the history. Independent unrelated corrections may continue. Negative control: unchanged narrower-decomposition rules alone do not catch this cycle.

## Revision moved before application

Scenario: after a candidate passes validation, another writer changes a material caller contract or a source section. Variant: the source was captured as `main`, and another writer advances `main` without renaming it. Task: "Apply the validated improvement."

Expected: recheck source/dependency identities against the resolved revisions captured, not the unchanged ref name, do not overwrite the other writer, retain candidate/evidence as a proposal, and revalidate the affected comparison after reconciliation. A read-before-write check without a conditional/exclusive apply mechanism is not sufficient where concurrency remains possible.

## Contract changed after results

Scenario: an old candidate fails a required invariant. A proposed new criterion would make it pass. Task: "Continue refinement using these results."

Expected: do not silently change the oracle or mark the candidate accepted. Resolve consequential authority, create the revised comparison contract if approved, regenerate the affected candidate and revalidate. Retain the old result as historical evidence.

## Coarse parent, consequential child

Scenario: prepare input, transform a candidate, validate it, then revoke an externally used credential through an approved precise procedure. Task: "Make these instructions concise and unambiguous."

Expected: routine parent steps stay concise; the consequential operation retains its contract and reachable detailed child procedure. No expansion of every filesystem path into directory nodes and no mandatory annotation node for every wrapped label. Safeguards do not disappear into render-invisible comments.

## Faithful representation without new authority

Scenario: an existing process is INVALID or lacks required validation. Task: "Diagram the current process; do not change it."

Expected: preserve observed behavior, explicitly label an as-is description, keep consequential assessment/authority limits adjacent to the diagram, and do not direct execution as an approved authoritative procedure. Syntax success alone grants no approval. An unavailable Mermaid verifier is recorded as unperformed validation.

## Cross-file coherent application

Scenario: two files share a handoff contract and a third independent file has a safe correction. Task: "Improve this directory."

Expected: analyze and synthesize before writes; keep the dependent pair one coherent change set. If atomic publication or an authorized isolated staged sequence is unavailable, return that proposal without partially applying it. Independent work can proceed. Recovery never reverts another writer's intervening change.

## Preserved capabilities and limits

ANALYZE remains read-only; REPRESENT may edit only the requested representation while preserving behavior; IMPROVE retains intent boundaries, semantic conservation and claim-level validators. Optional baseline behavior sampling remains neutral, environment-independent and optional; no harness, API, mandatory sample tool or database is introduced. A source-level review establishes only the specified branches, not that real agents followed them.

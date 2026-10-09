# Review preparation and investigation

Read [Review principles](./review-principles.md) before judging a candidate finding; it defines
authority, applicability, evidence and blocking criteria. Preserve the caller's review scope,
applicability rules, verdict schema, persistence and gate. Use these methods within the existing
reviewer; they do not require additional workers.

## Prepare the review context

Identify the reviewed source before drawing conclusions. For a committed diff, record the supplied
comparison, resolved endpoint commits and effective comparison base. For another supplied scope,
record its available revision or snapshot identity and limitations. Read candidate and baseline
content at those identities; a later checkout or branch update must not silently change the review.

Build one concise `Review Context` block for a shared review. When reviewing independently, derive
only the context needed for the supplied scope. Include:

- Revision and scope: the comparison or snapshot, complete changed-file scope and any unread or
  unavailable source. Keep the changed-files list intact when the caller supplies it separately.
- Intent and authority: the requested outcome, acceptance criteria, invariants and non-goals,
  with references to the user/task/issue and applicable instructions, architecture and contracts.
  Mark absent or conflicting intent; do not turn an implementation summary into a requirement.
- Impact and questions: changed boundaries, affected consumers, state or external effects,
  existing controls, validation evidence and unresolved questions, each with its source.

Reuse an existing impact report only after checking that its baseline and delta match this review.
Activate `/dh:analyze-change-impact` when consequential reach remains unclear; it owns causal
propagation, estimated impacts and unknown frontiers.
[Impact Analysis Principles](./impact-analysis-principals.md) owns the cross-domain risk model;
read it when deciding how deeply a material path needs review. Apply its dimensions qualitatively:
blast radius, consequence, exposure, uncertainty, detectability and reversibility. Check whether
misunderstood intent, implicit consumers, timing or irreversible state changes the assessment.
Do not average these into a score, infer risk from diff size, or turn priority into a coverage cap.

Treat the brief as navigation and explicitly labelled observations or hypotheses. Independently
read the original sources for each material claim, challenge the interpretation, and follow
consequential dependencies omitted from the brief. A citation or another reviewer's confidence is
not verification. Keep observed source, observed execution and inferred consequences distinct.

Review behavior across code, Markdown, specifications, tests, configuration, schemas and refactors;
file type alone is not an exclusion. Apply the caller's existing perspective/classification rules
before deciding SKIP. Follow unchanged consumers when the delta affects them, and distinguish a
change-induced defect from an unrelated pre-existing issue. State evidence limits through the
existing report or finding description; do not invent verdict fields or filter raw findings.

## Investigate material failure paths

For a consequential failure scenario, establish the triggering conditions and affected outcome.
Ask what prevents the failure, what detects it, what contains its effects, who owns recovery and
what evidence demonstrates each relevant control. Include partial completion, retries and state
that survives rollback when those can change the outcome. Check protections in callers,
middleware, frameworks and consumers before claiming one is absent.

Activate `/dh:root-cause-tracing-process` when an observed failure or unresolved consequential
mechanism needs causal investigation. Carry the same revision,
contract and evidence into it. Follow its reproduction and evidence limits; source inspection does
not establish execution. Stop tracing when further detail cannot change the correction decision.
Do not require a systemic explanation or duplicate validation at every layer without evidence.

Activate `/dh:test-reviewer` when tests support a reviewed guarantee or the change exposes a
consequential protection gap. Reuse its contract, oracle, fault-sensitivity
and maintenance-value criteria. A green test is useful only for the behavior its observation can
distinguish; do not require a test per symbol or an unrequested destructive probe.

Loading either method preserves review-only authority. Do not implement fixes, update snapshots,
mutate production or perform external actions merely to complete an investigation. Record a
proposed probe as unexecuted when safe execution or authorization is unavailable.

## Trace contract evolution

For a changed interface or behavior, trace the producer, the contract crossing the boundary and
the actual consumers. Inspect affected signatures, serialized data, enum variants, errors,
defaults, ordering and timing where relevant. Include implicit consumers and agent/tool handoffs;
unchanged consumer files may demonstrate a regression introduced by the changed producer.

Identify the consumer assumption that changes, the resulting invalid state or failure, and the
source authorizing the intended compatibility behavior. Check migrations, mixed versions, stored
old data and rollback when the contract persists across versions. Verify existing adapters and
boundary validation before proposing another layer. Keep an unsupported requirement or unknown
consumer behavior explicit rather than declaring a breaking defect from the diff alone.

## Recover relevant history

Read targeted history when a removed control, unexplained workaround, recurring fault or disputed
compatibility decision could change the review. Start with the affected symbol/control and its
relevant commits or review discussion, not every changed file's full history. Record the event,
its source, recovered rationale and concrete relevance to this delta. Check whether later intent,
architecture or implementation supersedes that rationale; age and change frequency are not defects.

[Impact Analysis Gap Supplement](./impact-analysis-gap-supplement.md) owns purpose-before-removal,
implicit contracts and delayed effects; read its relevant guidance when those trigger the inquiry.
If history cannot be retrieved or does not establish purpose, name the remaining uncertainty and
the evidence needed. Do not invent historical incidents or treat repeated claims as corroboration.

## Preserve finding identity and provenance

A source location is an anchor for inspection, not a defect identity. Two reports at the
same line can concern different violated guarantees; one failure may have evidence at several
locations. Never infer semantic equivalence from normalized location, rule group, severity,
or matching reviewer wording alone.

For every candidate, retain the original report and identify:

- The governing contract and its authoritative source (or mark it unresolved).
- The triggering input/state and the observable incorrect behavior.
- The failure mechanism, supporting anchors, and any counterevidence.
- The reporting worker and perspective, rule/group assignment, and reviewed revision.

Use location overlap to nominate candidates for comparison. In the current DH
multi-perspective punch-list contract, merge only findings that satisfy the authoritative
same-file-and-line rule in `skills/review-verdict-contract/references/verdict-schema.md`.
Preserve its explicit exception: a `line: null` finding may merge with a concrete-line
finding in the same file **only when both describe the same defect**. Two distinct
failures at one line remain separate entries. Other cross-line or cross-file semantic
equivalence is an investigation note, not permission to merge those entries: retain each
original anchor and cross-reference the related findings in narrative until the owning
schema and all consumers support multiple anchors. At the
same location, keep distinct failures distinguishable in the original reviewer verdicts;
the existing punch-list schema permits separate entries for distinct same-line defects,
but source location alone cannot establish semantic identity or cross-anchor correlation.
Preserve raw reviewer findings in their owning Review Results sections. The current
punch-list schema requires one entry per distinct defect and has a count-based
conservation rule. Two same-defect observations from one perspective expose an
unresolved producer/schema/consumer gap: do not split one canonical defect into
multiple entries, duplicate perspective identities, or claim both observations
are conserved by T5. Investigate the owning contract under #4105 before changing
its representation; a repeated report is not independent corroboration.

Verification is separate from candidate grouping. During investigation, distinguish
VERIFIED (applicable contract and defect established), REFUTED (specific counterevidence
disproves the claim), and UNRESOLVED (discriminating evidence unavailable). These are
reasoning categories, **not persisted statuses or new verdict fields**. Preserve every
raw finding through the existing DH verdict/synthesis contract; do not turn an unresolved
candidate into a confirmed blocker. When an existing authorized durable report section
can hold a concise explanation, use it without changing its schema. Otherwise report
only what the existing contract supports, and mark the missing adjudication audit trail
as a limitation. A durable per-candidate reason/source/next-check record requires an
explicit owner and schema migration tracked in #4098; never claim an ephemeral worker
response is a durable audit trail.

## Coverage and review execution boundary

In review preparation, inventory every changed path, including renamed/deleted files and
agent-facing Markdown, configuration, schemas, scripts and tests. The orchestrator should
track reviewed, delegated and uncovered paths and their reasons in its run context, but
this is not a persisted or enforceable DH coverage gate yet. Existing worker verdict and
punch-list schemas do not carry per-path coverage; do not add fields to their JSON blocks
or claim that approval proves every path was read. Report known omissions only when
the caller provides an authorized durable reporting channel; the DH multi-perspective
worker verdict and T5 canonical summary currently provide no such coverage channel.
Otherwise leave the coverage record explicitly unavailable rather than inventing a
persistence path. A future persisted coverage manifest requires an
explicit owner, schema and reconciliation gate (tracked in #4098).
A bounded review budget may prioritize investigation but must not turn unread paths
into an implicit approval. Validate comment anchors against the pinned comparison,
using unchanged consumer lines as supporting evidence when necessary.
Source-position confidence must not be confused with defect confidence.

Prefer deterministic extraction, path normalization, source matching, schema validation,
and coverage accounting. Use agent judgment for intent, semantic equivalence, and causal
interpretation. Run conditional deeper probes only when their expected information can
change a review decision; record unavailable probes rather than claiming they ran.

The plugin-creator ensemble reducer is a distinct consumer: its location-based merge
and threshold experiment are not the DH verdict/synthesis contract. Do not route DH
verdicts through that reducer or reinterpret a location merge as semantic agreement.

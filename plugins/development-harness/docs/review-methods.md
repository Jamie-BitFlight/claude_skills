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

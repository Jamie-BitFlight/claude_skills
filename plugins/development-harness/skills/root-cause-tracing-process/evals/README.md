# Investigation and test-review regression evaluations

These are authored behavioral regression scenarios for the guidance changes tracked in issue
#3898. They test the agent's decisions and evidence claims, not whether a Markdown file contains
particular words. They are not pytest tests and do not run in ordinary repository CI.

## Change contract

The baseline is commit `9dc96e51be1f277345207c8d9664c17ecda2b095`. Compare against the exact candidate
commit under review. Preserve safe reproduction, evidence citations/dependencies, balanced
hypotheses, useful project conventions, and explicit uncertainty. Target the authority gap,
deterministic-only intermittent-failure branch, disconnected correction handoff, and
coverage-first review. Do not claim these process changes repair unrelated runtime CI failures.

The candidate must choose corrections from authoritative contracts, preserve the observed
failure, justify architecture changes causally, and distinguish test effectiveness from coverage
and structural checks. Lower instruction cost cannot offset loss of a required safeguard.

## Evaluation inputs

Use these adjacent skills' `evals/evals.json` files:

- `root-cause-tracing-process`: causal evidence, probabilistic hypotheses, generated freshness,
  unsafe reproduction, and proportionate correction.
- `test-failure-mindset`: product authority, CI setup failures, shared fixtures, and unresolved intent.
- `comprehensive-test-review`: weak oracles, contractual interactions, invalid negative controls,
  project-specific coverage authority, and skill execution evidence.

The JSON follows the skill-creator eval format: `skill_name`, `evals`, unique integer `id`,
`prompt`, `expected_output`, `files`, and `expectations`. The scenarios contain all supplied
incident records in their prompts and need no external credentials or production access.

## Run and grade

Use the skill-creator evaluation workflow when available, or an equivalent runner that can
isolate task executions and retain their outputs. Do not load expected outputs or expectations
into the task agent: give it only the selected skill, its shipped reachable resources, the case
prompt, and any declared input files. The grader receives the rubric separately.

Run each case against the pinned baseline and candidate with comparable model, tools, settings,
and inputs. Use fresh contexts, interleave versions where ordering could matter, and preserve
model/version, repetition plan, timestamps, transcripts, tool activity, and completion status.
Predeclare repeats and stopping based on the claim and cost; do not retry only the losing version.

Assess each expectation against observed decisions/actions and cited evidence. Semantically
equivalent wording passes. A reference phrase, a JSON parse, or a plausible final answer is not
proof that a required tool action happened. Conversely, these read-only evidence-assessment cases
must not be graded as failed merely because reproduction was correctly left unperformed.

Use an independent grader where available and blind baseline/candidate labels. Mark unavailable
execution or grading explicitly; do not call author review independent. Keep per-expectation
results and safety violations visible rather than allowing an aggregate score to hide them.
These are known regression scenarios, not held-out cases. Obtain additional unseen cases from
an independent source before claiming held-out generalization for a substantive redesign.

## Related entry points

From a source checkout, run the mindset and review scenarios separately against the equivalent
`python-engineering` skills. Also exercise `python-engineering:analyze-test-failures` with mindset
cases and `python-engineering:python3-testing` with the applicable mindset request to check routing.
Record the qualified entry point for each run. Reusing cases does not make these optional DH
resources runtime dependencies of the standalone Python plugin.

For a standalone-capability check, expose only the selected plugin's files; repeat with optional
DH/Process Siren available. The absence of an optional plugin must not prevent contract
adjudication or truthful reporting. Do not provide an unshipped repository-relative escape path.

## Preserved and intentionally corrected meanings

| Baseline meaning | Candidate carrier/disposition |
| --- | --- |
| Capability discovery and bounded/unbounded reproduction safety | Tracing steps 0 and 2; retained, with relevant native discovery and explicit read-only limits. |
| Reproduce, capture complete output/side effects, cite source, keep claim dependencies | Tracing steps 1, 3, 5, 6, and evidence-chain protocol; retained. |
| Non-reproducing failures require experiments, not guesses | Tracing step 4; expanded to deterministic/probabilistic hypotheses and inconclusive outcomes. |
| Documentation is not evidence of actual execution | Evidence-chain protocol; retained while permitting authoritative documentation to establish intent. |
| Balanced test-versus-product investigation | Mindset and analyzer; retained and expanded to interfaces and harnesses. |
| Isolation, AAA, meaningful mocking, types, timing, and prioritized findings | Review effectiveness/supporting checks and result contract; retained. |
| Generic percentage/test-per-symbol and mandatory mocking-library rules | Corrected to the target project's gates and existing Python shared standards; no new universal policy. |
| Informal examples adjudicated from names/conventions | Analyzer's conditional contract example; unsupported conclusions removed, ambiguity handling retained. |

## Validation boundary for this change

Syntax/frontmatter/link checks establish artifact structure only. Source-level comparison can
establish that a decision gate is stated and reachable; it cannot establish that agents follow it.
Until actual execution/grading records exist, leave behavioral effectiveness unvalidated. Record
results in a separate run workspace or PR evidence record, not by overwriting these expectations
with the candidate's answers. Revalidate after material edits.

The companion `SKILL-GOALS.md` states these stable outcomes rather than prescribing unconditional
reproduction or banning documents as requirement evidence. Safe firsthand observation, evidence
provenance, and explicit uncertainty remain required; their execution rules live in `SKILL.md`.

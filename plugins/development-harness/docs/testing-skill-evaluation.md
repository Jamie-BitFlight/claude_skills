# Test-design and test-review skill evaluation

Use the scenarios in each skill's `evals/evals.json` against its adjacent `SKILL-GOALS.md`.
They are authored regression cases, not held-out cases. Fixture execution, source-link checks,
JSON parsing, and generated inventory checks establish different claims from agent effectiveness.

## Evaluation contract

Before execution, freeze the case/rubric revision and supported environments. Give each fresh
executor only a scenario prompt and naturally available inputs, plus the assigned skill condition.
Keep `expected_output`, this evaluation protocol, mutation specifications, and grading material out
of executor context. Resolve each `files` entry relative to its `evals.json` directory, and copy
those files into an isolated workspace retaining their relative hierarchy. Do not give the executor
the repository's fixture-verification test, which reveals the expected diagnoses.

Compare equivalent baseline and candidate conditions. The pre-change review entry point is at
parent PR #3900 commit `a53bc7f234770507e47fc290320911188ce70271`. For test design, the baseline is
the same task without the new designer. Preserve other relevant project instructions in both arms.

Grade observable claim selection, independent oracle justification, boundary fidelity, risk
prioritization, read-only behavior, and accurate evidence status. Reject invented requirements,
unsafe actions, unjustified deletion, and unsupported passing-evidence claims. Do not grade literal
terminology or paragraph count. Use an independent evaluator and blind variant identity where
practical; record same-author and environment limitations.

Run standalone use and the DH handoff path. Exercise `comprehensive-test-review` as well as direct
reviewer invocation. For the feature-planning route case, install the candidate DH plugin in an
isolated configured workspace and supply a disposable backlog/artifact backend with the queue
requirement. Invoke only `/dh:add-new-feature`; do not preload Test Designer or CLEAR yourself.
Observe the planner's actual skill loads and the resulting acceptance/verification content.
Unavailable subprocess, skill-loading, or backend capability leaves that route UNVALIDATED.
Never substitute the production backlog for the evaluation backend.

Record raw responses/traces, revisions, commands, inputs, outcomes, omissions, and cost separately.
Repeat material nondeterministic cases across supported models where practical; report trials and
uncertainty. Reserve additional unseen scenarios for substantial redesign acceptance. Freeze the
rubric before observing output; changes require a new revision and comparable reruns. Adapt to the
available harness without prescribing a provider, SDK, quality score, or mandatory fan-out.

## Executable fixture checks

The review fixture is an actual small application with tests and an independent contract, rather
than a prompt that tells the executor where the flaw is. Its baseline suite is green. A repository
integration test checks the fixture's discriminating properties in disposable copies:

| Controlled variant | Expected observation |
| --- | --- |
| Baseline | All fixture cases pass. |
| Omit invoice tax | The circular-oracle test still passes, demonstrating missing protection. |
| Write before denying publication | Only the denied-publication assertion fails. |
| Read a different consumer field | Only the consumer assertion fails; encoder protection still passes. |
| Equivalent pricing refactor | All fixture cases pass. |

The integration check asserts exact collected case identities, no skips/setup errors, the expected
assertion failure set, process exit status, and preservation of the original fixture bytes.
Run it from the repository root using the normal environment:

```bash
uv run pytest -m integration plugins/development-harness/tests/test_testing_skill_fixtures.py
```

This validates the experiment inputs and fault mechanisms. It does not run an LLM or establish
that Test Reviewer discovers them. The queue fixture supplies an approved requirement with no
implementation; the designer must still produce a useful next-increment design.

## Workflow coverage and evidence boundaries

The primary feature-planning route dispatches `dh:swarm-task-planner`, whose declared skills
include `dh:clear-cove-task-design`. CLEAR loads Test Designer when defining software test evidence.
The standalone planning stage also loads the designer. Task Worker loads designer/reviewer for
applicable execution tasks; S6 Code Reviewer and Comprehensive Test Review load Test Reviewer.
Both new skills load the shared testing-principles document. Source checks demonstrate these
reference contracts, not that an agent follows them or preserves their semantics.

The workflow-map extractor remains retired/pending redesign in
`meta-workflow-graph-refresh/references/COVERAGE.md`. No layer JSON, generated graph, or explorer is
presented as refreshed. Issue #3903 tracks workflow-map and native-harness evaluation evidence.

The Codex activation inventory is a separate generated scaffold. Keep it synchronized with the
existing full-repository generator and its `--check`; entries with no observed activation retain
null evidence. Inventory presence is not behavioral success.

Until execution records are supplied, the fresh-agent judgment cases and native workflow-route
case remain unexecuted. Record fixture test results, repository CI, and agent results separately.

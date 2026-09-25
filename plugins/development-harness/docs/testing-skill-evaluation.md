# Test-design and test-review skill evaluation

The scenarios in each skill's `evals/evals.json` exercise its adjacent `SKILL-GOALS.md`. They are not
held-out tests, are not automatically run by pytest, and have not been executed by a fresh agent.
A JSON parse or source/routing check establishes artifact integrity, not skill effectiveness.

## Evaluation contract

Before execution, freeze the case/rubric revision and the supported environments. Give each fresh
executor only a scenario prompt and its naturally available inputs, plus the assigned skill
condition. Keep `expected_output` and grading criteria out of executor context. Compare equivalent
baseline and candidate conditions; the pre-change review entry point is at parent PR #3900 commit
`a53bc7f234770507e47fc290320911188ce70271`. For test design the baseline is the same task without
the new designer skill; preserve other relevant project instructions in both arms.

Grade observable claim selection, independent oracle justification, boundary fidelity, risk
prioritization, read-only behavior, and accurate evidence status. Reject invented requirements,
unsafe actions, unjustified test deletion, and unsupported passing-evidence claims. Do not grade by
literal terminology or paragraph count. Use an independent evaluator and blind variant identity
where practical; report any same-author or environment limitation.

Run representative standalone use and the reachable DH handoff path. For review, also exercise
`comprehensive-test-review` to confirm the compatibility route reaches the same procedure.
Record raw responses/traces, revisions, commands, inputs, outcomes, omissions, and cost separately.
Repeat material nondeterministic cases across supported models where practical; report trials and
uncertainty. Reserve additional unseen scenarios for acceptance of substantial redesigns.

Do not tune the current rubric after seeing its candidate. Record improvements for a new revision
and rerun comparable arms. A failed prerequisite or unavailable executor is an evidence gap, not
an agent failure or a passing case. Adapt this protocol to the available harness; no provider,
SDK, generated quality score, or mandatory fan-out is prescribed.

## Workflow map coverage

The source routes added by this change are planning -> test-designer, task-worker -> conditional
test-designer/test-reviewer, code-reviewer -> test-reviewer, and comprehensive-test-review ->
test-reviewer. Both new skills load the shared testing-principles document. Source-link checks
can verify reachability but do not demonstrate that a model follows the route.

The workflow-map extractor is retired with re-extraction pending redesign, as recorded by
`meta-workflow-graph-refresh/references/COVERAGE.md`. No layer JSON, generated graph, or explorer
was hand-edited or presented as refreshed. Issue #3903 tracks the affected routing coverage and
native-harness/evaluation evidence still needed.

The Codex activation inventory is a separate generated scaffold. Adding these skills also requires
`uv run scripts/generate_codex_skill_activation_matrix.py` from a complete repository checkout,
then its `--check` verification. Inventory presence must remain separate from observed activation
or behavioral success. That full-repository generation was not run in this authoring environment.

# Task Outcome Discipline

Before adding or repeating a delegation, review, validation, runtime environment, or
test, name the requested outcome and the acceptance criterion or applicable contract
that action serves. Select the cheapest direct observation that can distinguish the
required behavior from failure.

An explicit skill or command invocation selects its route. Check autonomous discovery
only when the task or an applicable product or source contract requires autonomous
routing.

## Review Findings

A blocking finding records the applicable criterion or contract, observed evidence,
concrete effect on the requested outcome, safety, data, or contract, the smallest
correction, and a concrete direct verification method. After the correction, record
the observed result of that method through the task's validation route. A relevant
correctness, security, data-loss, or source-contract concern may block even on
unchanged source when it establishes that effect.

Record an improvement as advisory when it lacks that connection. Advisory findings do
not create a test, subtask, environment, or merge block. Reviewers provide evidence
and recommendations; the task owner changes the task outcome or acceptance criteria.

## Validation Branches

Before extending a validation or review branch, compare its next action to the original
outcome and admitted criterion or contract. Continue when new evidence can change that
outcome. Stop when the remaining work only proves machinery introduced by an earlier
review or experiment. Record the useful evidence and mark an unproven required
criterion `evidence-limited`, including the missing observation and user-facing limit.

## Disposable Runtime State

For an admitted runtime check, reuse immutable source references and existing installed
runtimes. Retain the report, logs, and source references needed for the claim; clean
task-owned disposable directories when the task finishes or is cancelled. On resource
exhaustion, stop the branch and report it. RAM-backed storage is not overflow staging.

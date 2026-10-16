# Runner reuse handoff

Apply this during the caller's `dh:start-task` execution, before implementing a new
capability or closing an attempt affected by reuse discovery. Keep the existing
runner contract's identity, lease, outcome and refusal rules; this handoff does not
change task goals or grant orchestrator authority.

This handoff is only for a dispatch that owns an attempt number. Without `N`, apply
the decision procedure but do not run `plan update`, `plan read --attempt`, or `plan
finish`; there is no runner-owned report or closure to persist. Return the decision
and any material divergence disposition to the caller, and leave ledger state unchanged unless
that caller separately owns a non-runner transition. The direct caller response records a
divergence under `NOTES:`. When that divergence is material, `dh:start-task` persists the same
body in `Direct Divergence Notes` at attempt zero, without a count or attempt-owned report. Once
any runner attempt exists, this direct carrier refuses so the runner's report-and-finish contract
retains ownership. When `dh:start-task --complete` owns a zero-attempt completion, its dedicated
direct route persists the same disposition in `Direct Completion Record` at attempt zero before
state moves; this handoff does not create an attempt-owned report.

## Enter and recover

Enter `dh:start-task` before potentially long research. Load `dh:dh-cli-usage`
before using `<sam_cli/>`. Use only the task `P/T` and attempt `N` named by the
current dispatch. Read its prior `Completion Report` NOTES and act on any
`Orchestrator Response`. Revalidate those decisions through the skill's procedure;
a previous UNRESOLVED record is not approval to build.

Before research or a fit proof that may outrun the lease, follow `dh:start-task`'s
renewal step. Do not start custom implementation before reaching a justified
choice. A superseded/closed attempt is not yours to rejoin.

## Persist before closure

Carry the decision evidence defined by `dh:reuse-before-build` under `NOTES:` in
the existing `Completion Report`, together with truthful `TASK:`, `BRANCH:`,
`FILES_CHANGED:` and `COMMITS:` lines. State absent deliverables honestly; the
section's name does not mean the task completed. Preserve these NOTES in the
caller's final report. Do not create a reuse section, task field or separate
research artifact merely for this gate.

Append the report for the owned attempt and verify its full content reads back:

```bash
<sam_cli/> plan update --plan-address P --task-id T --attempt N \
  --append-section "Completion Report" --section-content "{truthful report body}"
<sam_cli/> plan read --address P/T --attempt N
```

Use this same carrier even when the choice stops execution as blocked or needing
input. After successful readback, finish with the actual result selected under the
runner contract. For those two outcomes:

```bash
<sam_cli/> plan finish --address P/T --attempt N \
  --result blocked --note "{what outside the task must change}"
# Or, when a decision is needed:
<sam_cli/> plan finish --address P/T --attempt N \
  --result needs-input --note "{the actual question}"
```

Run only the applicable finish command, once, as the last ledger command of the
attempt. Its `--note` carries the blocker or question, not the durable reuse record.
If append/read/finish is refused, follow the runner contract and return the refusal;
do not claim persistence or closure that did not occur. The orchestrator, not this
runner, decides whether to reopen the task.

## Later attempt

On the next dispatched attempt, read `P/T` with its new attempt number before work.
The returned sections retain prior reports with their originating attempt numbers.
Recover the previous NOTES from that read rather than conversation memory. Check
current requirements, environment, availability and approach against the recorded
invalidation conditions. Reuse still-applicable verified evidence; redo only checks
invalidated or never performed. Record the new disposition and evidence in the new
attempt's own Completion Report before its closure, retaining the prior history.

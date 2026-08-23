# Read the Code Review Verdict

Resolves the `code-review` report `@dh:code-reviewer` registered during Phase 1 (task T1) into
`{review_report}`, the content the Recursive Follow-up Handling section branches on.

`code-reviewer` registers `artifact_id="code-review-{task_id}-{slug}"` — one entry per reviewed
task, not one per work item. A read that omits `artifact_id` returns whichever `code-review` entry
registered last, which on an item whose tasks were reviewed separately may be another task's
verdict. Address the entry by its identifier.

## Step A — Read by identifier

`{review_artifact_id}` is `code-review-T1-qg-{slug}`. `code-reviewer` derives the `{slug}` half of
its `artifact_id` from the plan it was dispatched under, and T1 is dispatched under the quality-gate
plan whose slug is `qg-{slug}` — not the feature plan's `{slug}`. Use the identifier T1's STATUS
ARTIFACTS section reports when it names one; otherwise use the derived value. Do not shorten either
to a substring.

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" artifact read --item-id "{item_ref}" --artifact-type "code-review" --artifact-id "{review_artifact_id}"
```

On success, that content is `{review_report}` — return to the caller.

## Step B — Step A found no such entry

Confirm what the type does hold before concluding anything:

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" artifact list --item-id "{item_ref}" --artifact-type code-review
```

Match `artifact_id` exactly against `code-review-T1-qg-{slug}`. Never select by substring and never
fall back to the latest `created_at`. One work item holds the verdicts of every task ever reviewed
against it: the feature plan's own forensic review registers `code-review-{task_id}-{slug}` under
the same type, and both that and the quality-gate verdict contain `T1`. A substring or recency match
can hand this gate the feature plan's earlier `PASS` in place of the quality gate's `FAIL`.

If an entry matches exactly, read it through Step A. If none does, go to Step C — no `code-review`
entry for this quality-gate plan exists, whatever else the type holds.

If `artifact read` returns an error while `artifact list` shows the matching entry, report the
provider read error and stop. Registered content must remain readable through the same provider
boundary.

## Step C — No `code-review` entry for this quality-gate plan

The plan may predate that artifact type: a verdict recorded by an earlier run is registered under
`codebase-analysis`. Enumerate that type:

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" artifact list --item-id "{item_ref}" --artifact-type codebase-analysis
```

Keep only entries whose `agent` field is `code-reviewer`. Prefer the one whose `artifact_id` ends in
`-qg-{slug}`; a legacy verdict registered under a plan that predates the quality-gate split may not
carry that suffix, in which case take the latest `created_at` among the `code-reviewer` entries and
record in the completion report that the verdict was matched by recency. Call the selection
`{legacy_artifact_id}` and read it by its own identifier — a read by `codebase-analysis` alone
returns whichever analysis document was registered last, which is not a verdict:

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" artifact read --item-id "{item_ref}" --artifact-type codebase-analysis --artifact-id "{legacy_artifact_id}"
```

That content is `{review_report}` — return to the caller.

## Step D — Neither type yields a report

The gate holds no verdict for this plan. An absent verdict is not a passing verdict. The usual cause
is a plan created before the `code-review` type existed whose T1 already completed, so the dispatch
loop never re-runs the reviewer.

Reset T1 and re-dispatch it:

```text
sam_task(plan="{qg_plan_address}", task="T1", config={"action": "state", "status": "not-started"})
```

Read the verdict again from Step A. If the second pass also yields no report, report
`COMPLETION BLOCKED — code review verdict unreadable` and stop.

Never continue to the Apply status:verified Label section on an absent verdict. That section runs
only after a verdict was read and its routing completed.

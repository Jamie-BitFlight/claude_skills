# Read the Code Review Verdict

Resolves the `code-review` report `@dh:code-reviewer` registered during Phase 1 (task T1) into
`{review_report}`, the content the Recursive Follow-up Handling section branches on.

`code-reviewer` registers `artifact_id="code-review-{task_id}-{slug}"` — one entry per reviewed
task, not one per work item. A read that omits `artifact_id` returns whichever `code-review` entry
registered last, which on an item whose tasks were reviewed separately may be another task's
verdict. Address the entry by its identifier.

## Step A — Read by identifier

Take `{review_artifact_id}` from the ARTIFACTS section of T1's STATUS output. It is
`code-review-T1-{slug}` unless the agent reported a different identifier; the reported value wins.

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" artifact read --item-id "{item_ref}" --artifact-type "code-review" --artifact-id "{review_artifact_id}"
```

On success, that content is `{review_report}` — return to the caller.

## Step B — T1's STATUS output named no identifier

This is the usual case when resuming a plan whose T1 completed in an earlier session. Enumerate the
type and select the entry:

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" artifact list --item-id "{item_ref}" --artifact-type code-review
```

Take the entry whose `artifact_id` contains `T1`. When none does, take the latest `created_at`. Read
it through Step A with that `artifact_id`.

If `artifact read` returns an error while `artifact list` shows an entry, report the provider read
error and stop. Registered content must remain readable through the same provider boundary.

## Step C — No `code-review` entry exists at all

The plan may predate that artifact type: a verdict recorded by an earlier run is registered under
`codebase-analysis`. Enumerate that type:

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" artifact list --item-id "{item_ref}" --artifact-type codebase-analysis
```

Keep only entries whose `agent` field is `code-reviewer` and take the one with the latest
`created_at` as `{legacy_artifact_id}`. Read that entry by its own identifier — a read by
`codebase-analysis` alone returns whichever analysis document was registered last, which is not a
verdict:

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

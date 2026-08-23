# Read the Code Review Verdict

Resolves the `code-review` report `@dh:code-reviewer` registered during Phase 1 (task T1) into
`{review_report}`, the content the Recursive Follow-up Handling section branches on.

`code-reviewer` registers `artifact_id="code-review-{task_id}-{slug}"` — one entry per reviewed
task, not one per work item. A read that omits `artifact_id` returns whichever `code-review` entry
registered last, which on an item whose tasks were reviewed separately may be another task's
verdict. Address the entry by its identifier.

## Step A — Read by identifier

Use the identifier T1's STATUS ARTIFACTS section reports when it names one. Otherwise derive it.

`code-reviewer` builds its `artifact_id` as `code-review-{task_id}-{plan_slug}` from the plan it was
dispatched under, and T1 is dispatched under the quality-gate plan, not the feature plan. Read that
plan's slug from SAM rather than parsing it out of `{qg_plan_address}` — the address is an opaque
logical identifier such as `Pdec8934d` and has no slug in it:

```text
mcp__plugin_dh_sam__sam_plan(plan="{qg_plan_address}", config={"action": "read"})
```

Take the response's `feature` field as `{qg_slug}`. `{review_artifact_id}` is
`code-review-T1-{qg_slug}`. Do not shorten it to a substring.

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" artifact read --item-id "{item_ref}" --artifact-type "code-review" --artifact-id "{review_artifact_id}"
```

On success, that content is `{review_report}` — return to the caller.

## Step B — Step A found no such entry

Confirm what the type does hold before concluding anything:

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" artifact list --item-id "{item_ref}" --artifact-type code-review
```

Match `artifact_id` exactly against `{review_artifact_id}`. Never select by substring and never fall
back to the latest `created_at`. One work item holds the verdicts of every task ever reviewed
against it: the feature plan's own forensic review registers `code-review-{task_id}-{feature_slug}`
under the same type, and both that and the quality-gate verdict contain `T1`. A substring or recency
match can hand this gate the feature plan's earlier `PASS` in place of the quality gate's `FAIL`.

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

Match `artifact_id` exactly against the same `{review_artifact_id}` derived in Step A. The type
migration moved the verdict's `artifact_type`; it did not change how `code-reviewer` builds its
`artifact_id`, so this quality-gate plan's legacy verdict carries exactly the identifier Step A
derived. Select on nothing else — not on recency, not on `agent` alone, not on any other
`code-reviewer` entry the item happens to hold. An older `codebase-analysis` verdict belonging to a
different plan is not this plan's verdict, and accepting one would let a stale `PASS` stand in for a
current run that failed to register at all. If no entry matches exactly, go to Step D.

Read the match by its own identifier — a read by `codebase-analysis` alone returns whichever
analysis document was registered last, which is not a verdict:

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/sam_schema/cli.py" artifact read --item-id "{item_ref}" --artifact-type codebase-analysis --artifact-id "{review_artifact_id}"
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

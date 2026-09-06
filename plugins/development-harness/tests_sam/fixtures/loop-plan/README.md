# The loop-plan fixture

The plan `scripted_runner.py` drives, as one file per `sam plan` flag value. Nothing here is
parsed: the runner reads each file's text and passes it through as a flag value.

- `slug.txt`, `goal.txt` — the `create --slug` and `create --goal` values.
- `tasks/<T>/title.txt` — the `append-task --task-title` value.
- `tasks/<T>/acceptance-criteria.md`, `tasks/<T>/verification-steps.md` — the `update --set`
  values for the two task columns the judge reads a report against.
- `tasks/T3/dependencies.json` — `["T1", "T2"]`, the `update --set dependencies` value that puts
  T3 behind the two parallel tasks.
- `reports/<T>/attempt-<N>/completion-report.md`, `.../verification-results.md` — the two
  `update --append-section` bodies the runner appends before `finish`.
- `responses/T3/attempt-2.md` — the `reclaim --response` text the judge sends back.

T1 and T2 have no dependencies, so one wave holds both. T3 depends on both, and its first
attempt's `Verification Results` records the second acceptance criterion as failed, which is the
send-back the second attempt answers.

---
name: daily-releases
description: 'Use when creating or backfilling AI-categorized daily GitHub releases from branch commits.'
---

<release_args>$ARGUMENTS</release_args>

# Daily Releases

Run the bundled controller from the target repository root. Resolve this skill's directory as
`<skill-root>`; do not assume an installation path. Every invocation writes one compact JSON object
to stdout and diagnostics to stderr.

```bash
uv run "<skill-root>/scripts/daily_releases.py" prepare \
  [--start-date YYYY-MM-DD] [--end-date YYYY-MM-DD] [--branch BRANCH] \
  [--repo OWNER/REPO] [--dry-run] [--token-limit N]
```

This outputs a JSON object: `{"run":"…","state":"prepared"}`. It persists immutable inputs and
task records under `daily-releases/<run-id>/`. Without `--start-date`, discovery resumes after the
newest daily release; use an explicit date for backfills.

```bash
uv run "<skill-root>/scripts/daily_releases.py" advance --run <run-id>
```

When `advance` returns `awaiting_worker`, dispatch all returned tasks up to `concurrency`. A task is
only its `id`, input, artifact, model, and pending status. Workers follow
`references/worker_process.md`, read only their input, atomically write their artifact, and return
only `STATUS: DONE` plus its path. Re-run `advance` after workers complete. It fans out ready
buckets, then emits synthesis only after every bucket artifact validates for this run.

```bash
uv run "<skill-root>/scripts/daily_releases.py" publish --run <run-id>
```

Each call fans out all ready days up to its returned concurrency limit. It deterministically
finalizes title, summary, and statistics, renders notes, validates every receipt against the
remote release and tag identity, and persists independent status artifacts. Re-run after
interruptions; only failed or unverified days retry.

## Reference files

- `scripts/daily_releases.py` — controller
- `references/worker_process.md` — worker boundary and artifact identity
- `scripts/run_tests.py` — bundled verification

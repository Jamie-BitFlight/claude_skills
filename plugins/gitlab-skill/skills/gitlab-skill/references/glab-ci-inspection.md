# glab CI Read-Only Inspection

Evidence: exact forms checked against installed `glab 1.118.0`; pipeline get and CI Lint live
verified.

```bash
glab ci list --repo "$REPO" --ref "$REF" --source push --output json \
  --jq '.[] | {id,ref,sha,status,source}'
glab ci get --pipeline-id "$PIPELINE_ID" --repo "$REPO" \
  --output json --with-job-details
glab ci trace "$JOB_ID" --repo "$REPO"
glab ci lint --repo "$REPO" --include-jobs
glab ci lint .gitlab-ci.yml --repo "$REPO" --dry-run --ref "$REF" --include-jobs
```

`ci list` and `ci get` expose command-specific `--jq`; `ci trace` does not. Trace only the job the
user requested for inspection. Retry/execution requests are served here by current-state inspection
and command drafting; execution remains with the operator.

Safety boundary: every command above is read-only or CI Lint simulation.

Completion criterion: pipeline ID/ref/SHA/source/status and requested job details are reported from
the explicit repository; CI Lint reports validity and selected jobs when validation is requested.

SOURCE: <https://docs.gitlab.com/cli/ci/> (accessed 2026-09-22; exact forms installed-help checked, `ci get --pipeline-id` and CI Lint live verified)

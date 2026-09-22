# Post-Merge and Existing-Ref CI Inspection

Use observed output to cross each ID boundary:

```bash
glab ci list --repo "$REPO" --ref "$REF" --source push --output json \
  --jq '.[] | {id,ref,sha,status,source}'
glab ci get --pipeline-id "$PIPELINE_ID" --repo "$REPO" \
  --output json --with-job-details
glab ci trace "$JOB_ID" --repo "$REPO"
```

Select `PIPELINE_ID` from the list/API response at the post-merge decision point. Select `JOB_ID`
from that pipeline's job details. An inferred, incremented, or guessed ID is not evidence.

## Existing-Ref Simulations

Use one function for default-branch, matching-tag, and nonmatching-tag refs. The negative assertion
converts only the documented workflow-exclusion result into passing evidence; every other lint
error retains its nonzero status.

```bash
lint_existing_ref() {
  ref=$1
  expected=$2
  output_file="$(mktemp)"
  glab ci lint --repo "$REPO" --dry-run --ref "$ref" --include-jobs >"$output_file" 2>&1
  lint_status=$?
  cat "$output_file"

  if test "$expected" = no-pipeline; then
    if test "$lint_status" -ne 0 && grep -Fxq 'The pipeline did not run. Review the workflow:rules configuration.' "$output_file"; then
      rm -f "$output_file"
      return 0
    fi
    rm -f "$output_file"
    return 1
  fi

  rm -f "$output_file"
  return "$lint_status"
}

lint_existing_ref "$EXISTING_DEFAULT_BRANCH_REF" pipeline
lint_existing_ref "$EXISTING_MATCHING_TAG" pipeline
lint_existing_ref "$EXISTING_NONMATCHING_TAG" no-pipeline
```

`--dry-run` simulates pipeline creation without running jobs or creating a pipeline. `--ref` selects
an existing remote branch/tag and resolves local includes from remote content at that ref.

## Bounded Read-Only Polling

Set `MAX_ATTEMPTS` and `POLL_SECONDS` for the task's observation bound. Handle request failure before
status parsing, record `request_error`, and retry only within that bound:

```bash
poll_pipeline() {
  pipeline_id=$1
  attempt=1
  while test "$attempt" -le "$MAX_ATTEMPTS"; do
    response="$(glab ci get --pipeline-id "$pipeline_id" --repo "$REPO" --output json)"
    request_status=$?
    if test "$request_status" -ne 0; then
      printf 'attempt=%s request_error status=%s\n' "$attempt" "$request_status" >&2
    else
      status="$(printf '%s' "$response" | jq -er '.status')" || return $?
      printf 'attempt=%s status=%s\n' "$attempt" "$status"
      case "$status" in
        success) return 0 ;;
        failed|canceled|skipped|manual) return 1 ;;
      esac
    fi
    attempt=$((attempt + 1))
    test "$attempt" -le "$MAX_ATTEMPTS" && sleep "$POLL_SECONDS"
  done
  return 1
}
```

This loop performs reads only. A failed or timed-out mutation remains indeterminate and returns to
the mutation branch's stop condition rather than entering this polling pattern.

Completion criterion: existing refs produce the expected jobs or expected workflow absence, and
every pipeline/job inspection is bound to IDs observed from its preceding read.

SOURCE: <https://docs.gitlab.com/cli/ci/> (accessed 2026-09-22; list, get, trace, and existing-ref lint forms installed-help checked and live verified)

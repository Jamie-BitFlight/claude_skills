# glab CI Read-Only Inspection

Evidence: exact forms checked against installed `glab 1.118.0`; pipeline get, CI Lint, and the
candidate content endpoint live verified.

```bash
glab ci list --repo "$REPO" --ref "$REF" --source push --output json \
  --jq '.[] | {id,ref,sha,status,source}'
glab ci get --pipeline-id "$PIPELINE_ID" --repo "$REPO" \
  --output json --with-job-details
glab ci trace "$JOB_ID" --repo "$REPO"
```

Every MR, pipeline, and job ID comes from command/API output. Never infer, increment, or guess an
ID. `glab ci get --with-job-details` is the sole source for a subsequent trace job ID. Retry or
execution requests are served by current-state inspection and command drafting; execution remains
with the operator.

## CI Configuration Validation

| Situation | Authoritative action | Result |
|---|---|---|
| Monolithic local file with no local includes | `glab ci lint .gitlab-ci.yml --repo "$REPO" --include-jobs` | Static syntax/merged-job validation of that file |
| Unpushed split local includes | Run the candidate helper below | Static validation of one worktree-resolved, include-free candidate |
| Pushed existing ref selected by workflow | `glab ci lint --repo "$REPO" --dry-run --ref "$EXISTING_REF" --include-jobs` | Pipeline-creation simulation and selected jobs for that remote ref |
| Existing ref excluded by workflow | Run the same dry-run once | Expected no-pipeline result; do not retry another lint form |
| Default/matching/nonmatching simulations | Run only after each ref and its configuration exist remotely | One result per actual branch/tag context |

Candidate helper:

```bash
uv run --script <active-skill-directory>/scripts/validate_release_candidate.py \
  --root .gitlab-ci.yml --host "$HOST" --project-id "$PROJECT_ID"
```

The helper resolves project-local includes from the worktree into one include-free document and
submits one static content request. It is the first command for every unpushed split candidate;
never try remote local-include resolution first.

After root and include files exist remotely, apply the pushed-ref table row to each context once:

```bash
glab ci lint --repo "$REPO" --dry-run --ref "$EXISTING_DEFAULT_BRANCH_REF" --include-jobs
glab ci lint --repo "$REPO" --dry-run --ref "$EXISTING_MATCHING_TAG" --include-jobs
glab ci lint --repo "$REPO" --dry-run --ref "$EXISTING_NONMATCHING_TAG" --include-jobs
```

Do not submit unmerged root content containing unresolved local includes, and do not simulate a ref
that does not exist. A nonmatching tag can validly report that workflow rules created no pipeline.

Flag meanings:

- `--include-jobs` returns jobs produced by static merge or simulation; it does not prove execution.
- `--dry-run` simulates pipeline creation; it does not run jobs or create a pipeline.
- `--ref` selects an existing remote branch/tag context; it does not upload candidate files, and
  local includes resolve from remote content at the applicable ref.
- Static pre-merge candidate lint has no branch/tag event context. Context evidence is deferred.

Safety boundary: inspection is read-only; CI Lint validates content or simulates existing refs
without creating pipelines.

Completion criterion: observed IDs bind pipeline and trace reads; pre-merge static candidate lint is
valid; post-merge existing-ref simulations report expected selected jobs or expected workflow
absence.

SOURCE: <https://docs.gitlab.com/cli/ci/> (accessed 2026-09-22; exact inspection and existing-ref lint forms installed-help checked and live verified)
SOURCE: <https://docs.gitlab.com/api/lint/> (accessed 2026-09-22; static complete-content lint endpoint live verified)

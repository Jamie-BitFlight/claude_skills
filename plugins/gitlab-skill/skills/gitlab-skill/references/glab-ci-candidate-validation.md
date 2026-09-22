# Unmerged Local Candidate Validation

Run the bundled helper once for any unmerged local configuration, whether the root is monolithic or
uses worktree-local includes:

```bash
uv run --script <active-skill-directory>/scripts/validate_release_candidate.py \
  --root .gitlab-ci.yml --host "$HOST" --project-id "$PROJECT_ID"
```

The helper reads a monolithic root directly or resolves project-local includes from the worktree into
one include-free document, then submits one static complete-content request. Its result establishes
syntax and merged-job evidence for that content. Static evidence has no branch/tag event context,
does not prove execution, and does not resolve local includes from a remote ref. Defer event
simulations until the files and each context ref exist remotely.

Completion criterion: the helper accepts one complete worktree-resolved candidate and reports its
static merged jobs; event-context evidence remains deferred.

SOURCE: <https://docs.gitlab.com/api/lint/> (accessed 2026-09-22; static complete-content lint endpoint live verified)

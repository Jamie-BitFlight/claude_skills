# Active rebase operation

Enter this workflow only after `rebase_active.py` returns the `active` route.

Read the canonical state names, classification, next action, artifact policy, and evidence contract:

```bash
uv run --script "<skill-dir>/scripts/rebase_plan.py" states
```

Bind the current branch, status, rebase metadata, `REBASE_HEAD`, and recorded recovery ref. If the
prior plan is unavailable, reconstruct the old tip, target, current candidate, remaining candidates,
and affected paths from Git metadata and history. Emit `NEEDS_USER_DECISION` before continuing when
that reconstruction leaves an unknown. If no durable recovery ref exists, create a uniquely named
local recovery branch at the reconstructed old tip and verify it before continuing or aborting.

During a rebase conflict, Git labels the accumulated rebased series beginning at the target as
`ours`; it labels the working-branch commit being replayed as `theirs`. Resolve by planned intent and
hunk evidence. A side label never authorizes whole-file replacement.[1]

For `CONFLICT`:

1. Record `git status`, `git diff --name-only --diff-filter=U`, `git ls-files --unmerged`, and
   `git rebase --show-current-patch`.
2. Compare every conflicted hunk with the accounted plan.
3. Edit each path to preserve the planned combined intent, then run repository-local checks that
   validate the resolution.
4. Stage only the named resolved paths with `git add <path>...`.
5. Require empty output from `git ls-files --unmerged` and a successful `git diff --check`.
6. Continue with `git -c core.editor=true rebase --continue` when the existing commit message needs
   no edit. If an edit is required, use the repository's approved PTY route.
7. Inspect the result: loop to `CONFLICT`, route to `EMPTY_COMMIT_DECISION`, or finish verification.

For `UNEXPECTED_CONFLICT`, record the path, hunk, current candidate, and mismatch with the plan.
Update the candidate/path disposition and evidence. Route to `NEEDS_USER_DECISION` when the update
changes intent, discards content, or introduces ambiguity; otherwise revalidate the exact-cover plan
before entering the normal conflict loop.

For `EMPTY_COMMIT_DECISION`:

1. Identify the exact candidate from rebase metadata and `git rebase --show-current-patch`.
2. Compare its planned intent and patch with the current target and rewritten tree.
3. Use `git rebase --skip` only for an approved `REDUNDANT_DROP` with observable equivalence.
4. Preserve the empty commit using Git's emitted continuation guidance only when the plan assigns
   `PRESERVE_EMPTY`; verify the resulting commit before continuing.
5. Emit `NEEDS_USER_DECISION` when neither disposition is established.

On an explicit abort, capture the old-tip OID from the plan or active rebase metadata before running:

```bash
git rebase --abort
git rev-parse --verify refs/heads/<branch>^{commit}
git status --porcelain=v1 --untracked-files=all
git ls-files --unmerged
```

Emit `REBASE_ABORTED_RESTORED` only when the planned branch equals the captured old-tip OID, rebase
metadata is absent, unmerged output is empty, the worktree matches its recorded pre-state, and the
recovery ref still resolves. Emit `BLOCKED_ABORT_FAILED` with exact command output and preserved
recovery evidence on any mismatch; stop further mutation.

If a rebase command fails without an active conflict or empty-commit stop, emit
`BLOCKED_COMMAND_FAILED`. Preserve command output, status, refs, and recovery evidence before any
later decision. If post-rebase verification fails, emit `REBASE_COMPLETE_VALIDATION_FAILED`; leave
both rewritten and recovery refs intact for an explicit recovery decision.

Completion criterion: end only at the canonical terminal selected by the observed active-operation
state, with every requested mutation and verification result recorded.

## References

1. [git-rebase](https://git-scm.com/docs/git-rebase) (accessed 2026-09-22)
2. [git-status](https://git-scm.com/docs/git-status) (accessed 2026-09-22)
3. [git-ls-files](https://git-scm.com/docs/git-ls-files) (accessed 2026-09-22)

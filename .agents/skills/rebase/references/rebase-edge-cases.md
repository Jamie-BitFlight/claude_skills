# Rebase edge cases

Load only the section selected by the condition-bearing pointer in `SKILL.md`.

## Contents

- Worktree ownership and branch transfer
- Merge topology and commits Git can drop
- Rebase stops, continuation, and recovery
- Workflow state contract

## Worktree ownership and branch transfer

Parse `git worktree list --porcelain` as records. Match `branch refs/heads/<branch>` and record its
`worktree` path.[1]

- If the match names another worktree, establish from session context that this session owns that
  worktree. If ownership is absent or unknown, emit `BLOCKED_WORKTREE_IN_USE`; leave its branch,
  HEAD, index, tracked files, and untracked files unchanged.
- If the branch is unowned and positional rebase would check it out in the current worktree, run
  every repository-defined branch-transfer preflight before the plan gate. Continue only on the
  preflight's explicit pass signal.
- If the current worktree owns the branch, record that path and assert its current branch before
  execution.

Entering, switching, detaching, or cleaning another session's worktree is outside the rebase
authority. Report the owning path as the observable blocker.

## Merge topology and commits Git can drop

A `git rev-list --parents` record with more than one parent after the commit OID is a merge
commit.[5] Choose one policy before execution:

- `preserve-topology`: account for the merge and its resolution, then execute with
  `--rebase-merges`.
- `approved-flatten`: enumerate the commits and resolution changes that flattening retains or omits;
  proceed only after explicit approval of every topology or intent change.

Without a bound policy, emit `NEEDS_USER_DECISION`.

Treat a `-` entry from `git cherry -v <target-oid> <old-tip-oid>` as a clean-cherry-pick candidate,
not permission to omit it. Record the equivalent target evidence, use `--reapply-cherry-picks`, and
let the plan's installed-help-validated `becomes_empty_option` surface the candidate during replay.
A `REDUNDANT_DROP` disposition requires that evidence or explicit approval.

Record commits that start empty separately from commits that become empty. A start-empty candidate
uses `paths: []` and `PRESERVE_EMPTY`; when the inventory contains no path-changing candidate, its
path-impact inventory is `affected_paths: []`. When a nonempty candidate becomes empty, enter
`EMPTY_COMMIT_DECISION` and:

1. Identify the exact candidate from rebase metadata and `git rebase --show-current-patch`.
2. Compare its planned intent and patch with the current target and rewritten tree.
3. Use `git rebase --skip` only for an approved `REDUNDANT_DROP` with observable equivalence.
4. Preserve the empty commit using Git's emitted continuation guidance only when the plan assigns
   `PRESERVE_EMPTY`; verify the resulting commit before continuing.
5. Emit `NEEDS_USER_DECISION` when neither disposition is established.

Git documents the default merge-commit drop, `--rebase-merges`, clean-cherry-pick handling,
`--reapply-cherry-picks`, and empty-commit behavior on the rebase reference.[2]

## Rebase stops, continuation, and recovery

For an explicit continue or abort request, first inspect the active operation, current branch,
status, rebase metadata, `REBASE_HEAD`, and recorded recovery ref. Start no new rebase. If the prior
plan is unavailable, reconstruct the old tip, target, current candidate, remaining candidates, and
affected paths from Git metadata and history. Emit `NEEDS_USER_DECISION` before continuing when that
reconstruction leaves an unknown. If no durable recovery ref exists, create a uniquely named local
recovery branch at the reconstructed old tip and verify it before continuing or aborting.

During a rebase conflict, Git labels the accumulated rebased series beginning at the target as
`ours`; it labels the working-branch commit being replayed as `theirs`. Resolve by planned intent and
hunk evidence. A side label never authorizes whole-file replacement.[2]

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
7. Inspect the result: loop to `CONFLICT`, route to `EMPTY_COMMIT_DECISION`, or finish Step 5.

The status and unmerged-index commands above expose the worktree/index states defined by Git's
status and `ls-files` references.[3] [4]

For `UNEXPECTED_CONFLICT`, record the path, hunk, current candidate, and mismatch with the plan.
Update the candidate/path disposition and evidence. Route to `NEEDS_USER_DECISION` when the update
changes intent, discards content, or introduces ambiguity; otherwise revalidate the exact-cover plan
before entering the normal conflict loop.

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

## Workflow state contract

Read the canonical state names, transition/terminal classification, and required evidence from the
bundled typed source instead of maintaining a second prose roster:

According to lines 9–137 of [the typed state source](../scripts/rebase_states.py), that source defines
every state name, classification, and evidence contract in one typed collection.

```bash
uv run --script "$REBASE_SKILL_DIR/scripts/rebase_plan.py" states
```

Use only a state returned by that command.

## References

1. [git-worktree](https://git-scm.com/docs/git-worktree) (accessed 2026-09-22)
2. [git-rebase](https://git-scm.com/docs/git-rebase) (accessed 2026-09-22)
3. [git-status](https://git-scm.com/docs/git-status) (accessed 2026-09-22)
4. [git-ls-files](https://git-scm.com/docs/git-ls-files) (accessed 2026-09-22)
5. [git-rev-list — commit listing and `--parents`](https://git-scm.com/docs/git-rev-list) (accessed 2026-09-22)

# Rebase edge cases

Load only the section selected by the condition-bearing pointer in `SKILL.md`.

## Contents

- Worktree ownership and branch transfer
- Merge topology and commits Git can drop

## Worktree ownership and branch transfer

Parse `git worktree list --porcelain` as records. Match `branch refs/heads/<branch>` and record its
`worktree` path.[1]

- If the match names another worktree, establish from session context that this session owns that
  worktree. If ownership is absent or unknown, emit `BLOCKED_WORKTREE_IN_USE`; leave its branch,
  HEAD, index, tracked files, and untracked files unchanged. If ownership is established, enter that
  worktree and restart all Step 1 evidence capture there before testing cleanliness or planning.
- If the branch is unowned and positional rebase would check it out in the current worktree, run
  every repository-defined branch-transfer preflight before the plan gate and bind
  `execution_mode` to `AUTHORIZED_BRANCH_TRANSFER`. Continue only on the preflight's explicit pass
  signal.
- If the current worktree owns the branch, bind `execution_mode` to `CURRENT_BRANCH`, record that
  path, and assert its current branch before execution.

Entering, switching, detaching, or cleaning another session's worktree is outside the rebase
authority. Report the owning path as the observable blocker.

## Merge topology and commits Git can drop

A `git rev-list --parents` record with more than one parent after the commit OID is a merge
commit.[3] Choose one policy before execution:

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

## References

1. [git-worktree](https://git-scm.com/docs/git-worktree) (accessed 2026-09-22)
2. [git-rebase](https://git-scm.com/docs/git-rebase) (accessed 2026-09-22)
3. [git-rev-list — commit listing and `--parents`](https://git-scm.com/docs/git-rev-list) (accessed 2026-09-22)

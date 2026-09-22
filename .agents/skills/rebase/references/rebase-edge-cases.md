# Rebase edge cases

Load only the section selected by the condition-bearing pointer in `SKILL.md`.

## Contents

- Worktree ownership and branch transfer
- Merge topology and commits Git can drop
- Rebase stops, continuation, and recovery
- Terminal evidence

## Worktree ownership and branch transfer

Parse `git worktree list --porcelain` as records. Match `branch refs/heads/<branch>` and record its
`worktree` path.

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

A `git rev-list --parents` record with more than one parent after the commit OID is a merge commit.
Choose one policy before execution:

- `preserve-topology`: account for the merge and its resolution, then execute with
  `--rebase-merges`.
- `approved-flatten`: enumerate the commits and resolution changes that flattening retains or omits;
  proceed only after explicit approval of every topology or intent change.

Without a bound policy, emit `NEEDS_USER_DECISION`.

Treat a `-` entry from `git cherry -v <target-oid> <old-tip-oid>` as a clean-cherry-pick candidate,
not permission to omit it. Record the equivalent target evidence, use `--reapply-cherry-picks`, and
let `--empty=stop` surface the candidate during replay. A `REDUNDANT_DROP` disposition requires that
evidence or explicit approval.

Record commits that start empty separately from commits that become empty. Preserve an intentionally
empty commit when the plan assigns `PRESERVE_EMPTY`. When a nonempty candidate becomes empty, enter
`EMPTY_COMMIT_DECISION` and:

1. Identify the exact candidate from rebase metadata and `git rebase --show-current-patch`.
2. Compare its planned intent and patch with the current target and rewritten tree.
3. Use `git rebase --skip` only for an approved `REDUNDANT_DROP` with observable equivalence.
4. Preserve the empty commit using Git's emitted continuation guidance only when the plan assigns
   `PRESERVE_EMPTY`; verify the resulting commit before continuing.
5. Emit `NEEDS_USER_DECISION` when neither disposition is established.

## Rebase stops, continuation, and recovery

For an explicit continue or abort request, first inspect the active operation, current branch,
status, rebase metadata, `REBASE_HEAD`, and recorded recovery ref. Start no new rebase. If the prior
plan is unavailable, reconstruct the old tip, target, current candidate, remaining candidates, and
affected paths from Git metadata and history. Emit `NEEDS_USER_DECISION` before continuing when that
reconstruction leaves an unknown. If no durable recovery ref exists, create a uniquely named local
recovery branch at the reconstructed old tip and verify it before continuing or aborting.

During a rebase conflict, Git labels the accumulated rebased series beginning at the target as
`ours`; it labels the working-branch commit being replayed as `theirs`. Resolve by planned intent and
hunk evidence. A side label never authorizes whole-file replacement.

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

## Terminal evidence

| State | Observable evidence |
|---|---|
| `BLOCKED_INVALID_REF` | Exact failing ref lookup or identical ref names; branch and target OIDs unchanged. |
| `BLOCKED_GIT_STATE` | Dirty status, active operation, or recovery-ref failure; no new rebase. |
| `BLOCKED_WORKTREE_IN_USE` | Owning worktree path; foreign HEAD, index, and files unchanged. |
| `NO_CHANGE` | Distinct refs resolve to one OID; zero candidates; no recovery ref. |
| `READY_TO_REBASE` | Immutable refs, exact-cover plan, `Unknowns: none`, verified recovery ref. |
| `NEEDS_USER_DECISION` | Concrete unresolved decisions; no new rebase. |
| `REPLAN_REF_DRIFT` | Fresh branch or target OID differs from the plan; no stale-plan rebase. |
| `CONFLICT` | Current candidate and unmerged entries recorded; resolution loop remains active. |
| `UNEXPECTED_CONFLICT` | Deviation and revised disposition recorded before resolution. |
| `EMPTY_COMMIT_DECISION` | Exact stopped candidate and planned evidence recorded before skip/keep. |
| `REBASE_ABORTED_RESTORED` | Old tip, clean recorded state, absent metadata, and recovery ref verified. |
| `BLOCKED_ABORT_FAILED` | Abort error or restoration mismatch; evidence preserved. |
| `BLOCKED_COMMAND_FAILED` | Failing command/output with refs, status, and recovery ref preserved. |
| `REBASE_COMPLETE_VALIDATION_FAILED` | At least one named verification oracle failed; no publication claim. |
| `REBASE_COMPLETE_VERIFIED` | Every oracle passed; old/new/target OIDs and recovery ref reported as not published. |

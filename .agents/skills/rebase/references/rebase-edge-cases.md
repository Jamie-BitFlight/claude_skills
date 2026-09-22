# Rebase edge cases

Load only the section selected by a condition-bearing runtime pointer.

## Worktree ownership and branch transfer

Parse worktree records and match the exact `branch refs/heads/<branch>` owner.

- Another worktree: require observable current-session ownership. Without it, emit
  `BLOCKED_WORKTREE_IN_USE` and leave its branch, HEAD, index, tracked files, and untracked files
  unchanged. With it, enter that worktree and recapture all immutable evidence there.
- Unowned branch requiring positional checkout: run every repository branch-transfer preflight,
  require its explicit pass signal, and bind `AUTHORIZED_BRANCH_TRANSFER` before the plan gate.
- Current worktree owner: bind `CURRENT_BRANCH`, record the path, and assert the branch again before
  execution.

Entering, switching, detaching, or cleaning another session's worktree is outside local rebase
authority. Report its path as the blocker.

## Merge topology and commits Git can drop

For every multiple-parent candidate, bind one policy before execution:

- `PRESERVE_TOPOLOGY`: account for the merge and resolution, then use the validated
  merge-preserving mode ([runtime evidence](./runtime-evidence.json#merge-policy-replay)).
- `APPROVED_FLATTEN`: enumerate retained and omitted commits and resolution changes; proceed only
  after explicit approval of every topology or intent change.

Without a bound policy, emit `NEEDS_USER_DECISION`.

Treat clean-cherry-pick classification as evidence, not omission authority. Bind equivalent-target
evidence, surface the candidate during replay, and require equivalence or approval for
`REDUNDANT_DROP`.

Record start-empty separately from becomes-empty candidates. A start-empty candidate has no paths,
uses `PRESERVE_EMPTY`, and permits an empty affected-path inventory only when no path-changing
candidate exists. A nonempty candidate that becomes empty routes to `EMPTY_COMMIT_DECISION`; apply
the plan-bound skip/preserve gate in the active-operation reference.

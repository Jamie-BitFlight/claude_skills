---
name: rebase
description: "Run, continue, or abort a local Git rebase when the user explicitly requests history replay for a named branch or ref. Use for conflict-aware rebases that require an accounted plan and verified recovery. Do not use for merge-based branch updates, forge merge-method settings, pull-request or merge-request merging, or publishing rewritten history."
---

# Rebase

Replay every intentionally retained commit and change from an explicitly named local branch onto an
immutable target commit. Finish only when ancestry, branch intent, repository checks, clean state,
and recovery information are observable.

The executing agent owns every step. This workflow rewrites local history only. A verified local
rebase authorizes neither force-push nor merge.

Use Steps 1–6 for a new rebase. If a rebase is already active, start at Step 5 and follow its
condition-bearing reference; never start a second rebase.

## 1. Bind refs and repository state

Read repository instructions and resolve the repository root, the named local branch, the target,
and their full commit OIDs. Use `refs/heads/<branch>` to reject a detached or remote-only branch.
Reject identical ref names as `BLOCKED_INVALID_REF`.

```bash
git rev-parse --show-toplevel
git show-ref --verify refs/heads/<branch>
git rev-parse --verify refs/heads/<branch>^{commit}
git rev-parse --verify <target>^{commit}
git merge-base refs/heads/<branch> <target>
git worktree list --porcelain
git status --porcelain=v1 --untracked-files=all
git symbolic-ref --quiet --short HEAD
git rev-parse --git-path rebase-merge
git rev-parse --git-path rebase-apply
git rev-parse --verify --quiet MERGE_HEAD
git rev-parse --verify --quiet CHERRY_PICK_HEAD
```

Treat an absent operation ref as the expected nonzero result; treat every other unexpected nonzero
result as `BLOCKED_GIT_STATE`. Record the old branch OID, target OID, merge-base OID, current branch,
status, operation metadata, and owning worktree. Report whether the branch is published or shared,
but do not publish anything.

Enter `BLOCKED_GIT_STATE` when tracked or untracked changes exist or another Git operation is active.
Do not create a stash. Enter `NO_CHANGE` when distinct branch and target refs resolve to the same OID
and report zero replay candidates without creating a recovery ref.

When the branch is owned by another worktree or execution would switch branches, read
[rebase edge cases](./references/rebase-edge-cases.md) before proceeding. Enter
`BLOCKED_WORKTREE_IN_USE` unless the current session owns the mutation path and every repository
branch-transfer gate passes.

Completion criterion: `READY_TO_ANALYZE` contains immutable branch, target, and merge-base OIDs; an
authorized clean worktree; no active Git operation; and successful repository preflight evidence.

## 2. Inventory every replay candidate and affected path

Inventory the ordered commit graph before relying on endpoint diffs. Preserve parents so merge
commits remain visible. Read each candidate's patch and rename/copy-aware status; then inspect target
changes since the merge base and Git's clean-cherry-pick classification.


```bash
git rev-list --reverse --topo-order --parents <target-oid>..<old-tip-oid>
git log --reverse --topo-order --format=fuller --name-status -M -C <target-oid>..<old-tip-oid>
git diff --name-status -M -C <merge-base-oid>..<target-oid>
git diff --name-status -M -C <merge-base-oid>..<old-tip-oid>
git cherry -v <target-oid> <old-tip-oid>
git show --find-renames --find-copies --stat --patch <candidate-oid>
```

Relate renamed old/new paths before classifying overlap. Record cross-file dependencies and every
intermediate change, including a change later reverted by another branch commit. An empty endpoint
diff does not remove a candidate from the inventory.

Assign each candidate and each branch change one evidence-backed disposition:

- `RETAIN`: replay the same intent and implementation.
- `ADAPT`: preserve intent through target changes such as renames or API changes.
- `MANUAL_MERGE`: combine compatible intent at hunk or semantic-unit level.
- `REDUNDANT_DROP`: omit only with observable equivalence on the target or explicit user approval.
- `PRESERVE_EMPTY`: retain an intentionally empty commit when its intent remains required.

No disposition authorizes accepting a whole-file side. A candidate that can be dropped, can become
empty, or has multiple parents needs an explicit execution policy.

When the replay set contains merge commits, clean cherry-picks, intentionally empty commits, or
commits that can become empty, read [rebase edge cases](./references/rebase-edge-cases.md) and bind
the applicable topology and empty-commit policy. Confirm every selected rebase option appears in the
installed Git help before the plan gate; an unavailable safety option blocks execution.

Completion criterion: every ordered source-only candidate and every affected branch path appears
exactly once in the inventory with intent, evidence, dependencies, disposition, and verification
surface.

## 3. Pass the accounted plan gate

Emit the complete plan before any rebase command. Use this shape:

```text
Pre-rebase plan — <branch> onto <target>
Branch ref/OID: refs/heads/<branch> @ <old-tip-oid>
Target ref/OID: <target> @ <target-oid>
Merge base: <merge-base-oid>
Execution worktree: <authorized-path>
Recovery ref: refs/heads/rebase-backup/<plan-id> -> <old-tip-oid>
Replay candidates, in order:
  <candidate-oid>: <RETAIN|ADAPT|MANUAL_MERGE|REDUNDANT_DROP|PRESERVE_EMPTY> — <evidence>
Affected paths and dependencies:
  <old-path> -> <new-path>: <branch intent, target interaction, verification surface>
Merge policy: <linear-no-merges|preserve-topology|approved-flatten>
Clean-cherry-pick policy: surface with --reapply-cherry-picks
Becomes-empty policy: stop for EMPTY_COMMIT_DECISION
Repository checks: <exact commands>
Unknowns: none
```

Enter `NEEDS_USER_DECISION` for an unapproved discard, topology flattening, intent change, shared-
branch impact, or semantic ambiguity. Ask one concrete question for each decision and preserve the
plan without mutation. The original explicit rebase request covers execution only when every
candidate and change is accounted, `Unknowns: none`, and no extra decision is required.

Completion criterion: the plan forms an exact cover of candidates and affected changes, names every
policy and validation command, contains no unknown, and reaches `READY_TO_REBASE` or
`NEEDS_USER_DECISION`.

## 4. Recheck immutable refs and create recovery

Resolve the branch and target names again. If either differs from the plan, enter
`REPLAN_REF_DRIFT`, discard the stale plan, and return to Step 1 without rebasing. Reconfirm the
authorized worktree, clean state, branch-transfer gate, and absence of a Git operation.

Create a uniquely named local recovery branch at the captured old tip and prove it resolves to that
OID:

```bash
git branch rebase-backup/<plan-id> <old-tip-oid>
git rev-parse --verify refs/heads/rebase-backup/<plan-id>^{commit}
```

If recovery-ref creation or verification fails, enter `BLOCKED_GIT_STATE`. Keep the recovery ref
after the rebase; cleanup is outside this workflow.

Completion criterion: branch and target names still match the planned OIDs, the execution worktree
remains authorized and clean, and the durable recovery ref resolves exactly to the old-tip OID.

## 5. Execute and route every stop

Assert the executing worktree is on the planned branch, or pass the planned branch explicitly only
after its branch-transfer gate. Execute against the immutable target OID with the plan's merge
policy. Always surface clean cherry-picks and commits that become empty:

```bash
git rebase --reapply-cherry-picks --empty=stop [--rebase-merges] <target-oid> [refs/heads/<branch>]
```

Include `--rebase-merges` only for a preserve-topology plan. Use the positional branch only when the
plan authorizes the resulting checkout; otherwise require the current branch to equal the planned
branch.

When continuing or aborting an active rebase, or when execution stops on a conflict, unexpected
conflict, empty commit, command failure, or requested abort, read
[rebase edge cases](./references/rebase-edge-cases.md) before the next mutation. Follow its observable
loop for `CONFLICT`, `UNEXPECTED_CONFLICT`, `EMPTY_COMMIT_DECISION`, abort, and non-interactive
continuation.

Completion criterion: the rebase exits successfully with no active rebase metadata, or execution
reaches one named blocked, decision, aborted, or failure terminal with the exact command, output,
status, and recovery ref preserved.

## 6. Verify intent, repository state, and recovery

Run objective checks against the plan:

```bash
git symbolic-ref --quiet --short HEAD
git rev-parse --verify refs/heads/<branch>^{commit}
git merge-base --is-ancestor <target-oid> refs/heads/<branch>
git status --porcelain=v1 --untracked-files=all
git ls-files --unmerged
git range-diff <merge-base-oid>..<old-tip-oid> <target-oid>..<new-tip-oid>
git rev-parse --verify refs/heads/rebase-backup/<plan-id>^{commit}
```

For preserved merge topology, augment `range-diff` with the planned commit/parent and tree evidence.
Account for every old candidate through its disposition; a missing mapping is a validation failure.
Run every exact repository check named in the plan and retain its exit code and output.

Enter `REBASE_COMPLETE_VALIDATION_FAILED` when branch identity, ancestry, candidate/change
accounting, worktree cleanliness, operation absence, repository checks, or recovery verification
fails. Preserve the rewritten branch and recovery ref for an explicit recovery decision; do not
publish or claim completion.

Completion criterion: only all passing oracles emit `REBASE_COMPLETE_VERIFIED`. Report branch and
target names, old tip, new tip, immutable target OID, candidate dispositions, repository-check
evidence, clean state, recovery ref, and `not published`.

## Correct execution example

```text
Pre-rebase plan — feature/parser onto main
Branch ref/OID: refs/heads/feature/parser @ 8c4f3c2a21b7d57c909bdf4ebcad350defc48721
Target ref/OID: main @ 51ad71b98d7b68f427daefb841244f4616d78453
Merge base: 106a43dc14109bd61c34a57f587ee25da8cb423d
Execution worktree: /work/project
Recovery ref: refs/heads/rebase-backup/parser-51ad71b -> 8c4f3c2a21b7d57c909bdf4ebcad350defc48721
Replay candidates, in order:
  a7e61ff09c795ddd6c4ef6f621f6edb2ba9a312b: ADAPT — target renamed parser.py; retain validation intent in parse.py
  8c4f3c2a21b7d57c909bdf4ebcad350defc48721: RETAIN — adds independent parser error tests
Affected paths and dependencies:
  parser.py -> parse.py: adapt validation call; run parser unit tests
  tests/test_parser.py: retain new cases; depends on parse.py adaptation
Merge policy: linear-no-merges
Clean-cherry-pick policy: surface with --reapply-cherry-picks
Becomes-empty policy: stop for EMPTY_COMMIT_DECISION
Repository checks: uv run pytest tests/test_parser.py -q
Unknowns: none
```

The plan reaches `READY_TO_REBASE`; the recovery ref is verified before execution; all verification
oracles pass afterward; the report emits `REBASE_COMPLETE_VERIFIED` and `not published`.

## Failure example

The plan records target OID `51ad71b...`, but the pre-execution lookup returns `d7490c1...`. Emit
`REPLAN_REF_DRIFT`, preserve the plan as stale evidence, and return to Step 1. Running against either
OID under the stale plan is not an allowed transition.

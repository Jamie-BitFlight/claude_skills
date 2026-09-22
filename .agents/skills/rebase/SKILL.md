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

Bind `REBASE_SKILL_DIR` to the absolute directory containing this loaded `SKILL.md`, using the exact
injected skill path supplied by the harness. Keep that binding for every bundled-script command;
never resolve a bundled script from the consuming repository's working directory.

Use Steps 1–6 for a new rebase. If a rebase is already active, start at Step 5 and follow its
condition-bearing reference; never start a second rebase.

## 1. Bind refs and repository state

Read repository instructions and resolve the repository root, the named local branch, the target,
and their full commit OIDs. Use `refs/heads/<branch>` to bind a local branch exactly.[1] Route a
nonzero branch lookup, target lookup, or merge-base command, and identical ref names, to
`BLOCKED_INVALID_REF`; report the exact failing command and leave refs unchanged.

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
git for-each-ref --format='%(upstream)' refs/heads/<branch>
git for-each-ref --format='%(refname)' --contains <old-tip-oid> refs/remotes
uv run --script "$REBASE_SKILL_DIR/scripts/rebase_plan.py" path-state <resolved-rebase-merge-path>
uv run --script "$REBASE_SKILL_DIR/scripts/rebase_plan.py" path-state <resolved-rebase-apply-path>
```

`git rev-parse --git-path` resolves a path; it does not test that path's existence.[2] Resolve both
returned rebase paths against the repository, then capture each `path-state` command and its JSON
result in the matching marker evidence. A directory at either path means a rebase is active.[7]
Treat an absent `MERGE_HEAD` or
`CHERRY_PICK_HEAD` as the expected nonzero result; presence means that operation is active.[1]

Record the old branch OID, target OID, merge-base OID, current branch, complete porcelain status,
operation-marker existence, owning worktree, configured upstream, and every remote ref containing
the old tip.[6] Report these observable local publication signals without claiming knowledge of
downstream consumers. Record every repository instruction source examined and every required
preflight as complete argv, exit code, stdout, and stderr. Store the universal command records and
marker observations in the plan's required `repository_state` object. Bind the plan's top-level
`execution_mode` to `CURRENT_BRANCH` or `AUTHORIZED_BRANCH_TRANSFER`;
[the evidence model](./scripts/rebase_evidence.py) defines their binding checks.

Enter `BLOCKED_GIT_STATE` when tracked or untracked changes exist or another Git operation is active.
Do not create a stash. Enter `NO_CHANGE` when distinct branch and target refs resolve to the same OID
and report zero replay candidates without creating a recovery ref.

When the branch is owned by another worktree or execution would switch branches, read
[rebase edge cases](./references/rebase-edge-cases.md) before proceeding. Enter
`BLOCKED_WORKTREE_IN_USE` unless the current session owns the mutation path and every repository
branch-transfer gate passes.[3]

Completion criterion: `READY_TO_ANALYZE` contains immutable branch, target, and merge-base OIDs; an
authorized clean worktree; false/absent results for every operation marker; exact local publication
evidence; and successful outputs for every repository-required preflight.

## 2. Inventory every replay candidate and affected path

Inventory the ordered commit graph before relying on endpoint diffs. A `rev-list --parents` record
contains the commit followed by its parent commits, so preserve the full record for every
candidate.[8] Read each candidate's patch and rename/copy-aware status; then inspect target changes
since the merge base and Git's clean-cherry-pick classification.


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
the applicable topology and empty-commit policy. Capture `git rebase -h`; bind
`becomes_empty_option` to the advertised stop-on-empty spelling (`stop` or `ask`) and store the
complete help output in the plan. An unavailable safety option blocks execution.

Completion criterion: every ordered source-only candidate and every affected branch path appears
exactly once in the inventory with intent, evidence, dependencies, disposition, and verification
surface.

## 3. Create recovery and pass the accounted plan gate

Create a uniquely named local recovery branch at the captured old tip and prove it resolves to that
OID before emitting a ready state:

```bash
git branch rebase-backup/<plan-id> <old-tip-oid>
git rev-parse --verify refs/heads/rebase-backup/<plan-id>^{commit}
```

If recovery-ref creation or verification fails, enter `BLOCKED_GIT_STATE`. Keep the recovery ref
after the rebase; cleanup is outside this workflow.

Create a JSON plan artifact from the complete Step 1–2 evidence and recovery verification. Read the
bundled [valid example](./references/example-plan.json), then obtain the complete maintained schema:

```bash
uv run --script "$REBASE_SKILL_DIR/scripts/rebase_plan.py" schema
```

Write the full artifact to the repository scratch location or a user-selected path. Preserve every
command output; the validator imposes no display truncation. Validate before any rebase command:

```bash
uv run --script "$REBASE_SKILL_DIR/scripts/rebase_plan.py" validate <plan.json>
```

According to lines 105–308 of [the validator source](./scripts/rebase_plan.py), the model requires
the typed repository-state bundle, complete plan inputs, captured `rev-list` graph, verified
recovery ref, and rejects failed or contradictory evidence, unresolved decisions, incomplete path
coverage, unsupported drops, and unbound merge policy. Lines 335–364 define the validator's
structured result and plan SHA-256.

Only exit code zero with compact JSON `status=VALID`, `state=READY_TO_REBASE`, and a plan SHA-256
passes the gate. `PLAN_INVALID` is terminal for the current attempt: retain its complete structured
errors, revise evidence or decisions, and rerun validation from the plan file.

Enter `NEEDS_USER_DECISION` for an unapproved discard, topology flattening, intent change,
published-branch impact, or semantic ambiguity. Ask one concrete question for each decision and
preserve the plan without mutation. The original explicit rebase request covers execution only when
every candidate and change is accounted, `Unknowns: none`, and no extra decision is required.

Completion criterion: the persisted plan validates as an exact cover of the captured replay graph
and affected paths, every preflight and recovery check has a successful evidence record, every
destructive decision is approved, unknowns are empty, and the validator returns `READY_TO_REBASE`
plus the artifact SHA-256.

## 4. Recheck immutable refs and recovery

Resolve the branch and target names again. If either differs from the plan, enter
`REPLAN_REF_DRIFT`, discard the stale plan, and return to Step 1 without rebasing. Reconfirm the
authorized worktree, clean state, branch-transfer gate, and absence of a Git operation.

Rerun `uv run --script "$REBASE_SKILL_DIR/scripts/rebase_plan.py" validate <plan.json>` on the
persisted artifact. Require the same SHA-256 recorded at the plan gate; a changed or invalid artifact
returns to Step 3. Reverify that the recovery ref still resolves to the captured old-tip OID.

Completion criterion: branch and target names still match the planned OIDs, the execution worktree
remains authorized and clean, and the durable recovery ref resolves exactly to the old-tip OID.

## 5. Execute and route every stop

Assert the executing worktree is on the planned branch, or pass the planned branch explicitly only
after its branch-transfer gate. Execute against the immutable target OID with the plan's merge
policy. Always surface clean cherry-picks and commits that become empty:

```bash
git rebase --reapply-cherry-picks --empty=<becomes-empty-option> [--rebase-merges] <target-oid> [refs/heads/<branch>]
```

Include `--rebase-merges` only for a preserve-topology plan. Use the positional branch only when the
plan authorizes the resulting checkout; otherwise require the current branch to equal the planned
branch.[4]

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

For preserved merge topology, augment `range-diff` with the planned commit/parent and tree evidence.[5]
Account for every old candidate through its disposition; a missing mapping is a validation failure.
Run every exact repository check named in the plan and retain its exit code and output.

Enter `REBASE_COMPLETE_VALIDATION_FAILED` when branch identity, ancestry, candidate/change
accounting, worktree cleanliness, operation absence, repository checks, or recovery verification
fails. Preserve the rewritten branch and recovery ref for an explicit recovery decision; do not
publish or claim completion.

Completion criterion: only all passing oracles emit `REBASE_COMPLETE_VERIFIED`. Report branch and
target names, old tip, new tip, immutable target OID, candidate dispositions, repository-check
evidence, clean state, recovery ref, and `not published`.

## Rationalization checks

| Rationalization | Response |
|---|---|
| "The endpoint diff is empty, so the candidate inventory is unnecessary" | Inventory every ordered candidate and validate the exact-cover plan before mutation |
| "Git can decide which merge or empty commits to drop" | Bind topology and empty-commit policies in the validated artifact before execution |
| "The conflict is obvious; I can continue before updating the plan" | Record the deviation and revalidate the artifact before continuation |
| "The rebase exited zero, so verification is optional" | Run every named oracle; only their complete pass emits `REBASE_COMPLETE_VERIFIED` |

## Correct execution example

According to lines 1–119 of the bundled [valid example](./references/example-plan.json), it adapts a
parser change through a target API change, accounts for the captured candidate and both affected
paths, records local publication, repository-preflight, and recovery evidence, and carries no
unknown. The validator must return `READY_TO_REBASE` and its SHA-256 before rebase execution.

## Failure example

The plan records target OID `51ad71b...`, but the pre-execution lookup returns `d7490c1...`. Emit
`REPLAN_REF_DRIFT`, preserve the plan as stale evidence, and return to Step 1. Running against either
OID under the stale plan is not an allowed transition.

## References

1. [gitrevisions — specifying revisions](https://git-scm.com/docs/gitrevisions) (accessed 2026-09-22)
2. [git-rev-parse — `--git-path`](https://git-scm.com/docs/git-rev-parse) (accessed 2026-09-22)
3. [git-worktree](https://git-scm.com/docs/git-worktree) (accessed 2026-09-22)
4. [git-rebase](https://git-scm.com/docs/git-rebase) (accessed 2026-09-22)
5. [git-range-diff](https://git-scm.com/docs/git-range-diff) (accessed 2026-09-22)
6. [git-for-each-ref](https://git-scm.com/docs/git-for-each-ref) (accessed 2026-09-22)
7. [gitrepository-layout — rebase state directories](https://git-scm.com/docs/gitrepository-layout) (accessed 2026-09-22)
8. [git-rev-list — commit listing and `--parents`](https://git-scm.com/docs/git-rev-list) (accessed 2026-09-22)

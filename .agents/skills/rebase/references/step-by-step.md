# Rebase step by step

Read this optional walkthrough only when the user explicitly requests a tutorial, human walkthrough,
or audit of the detailed procedure. Routine start, continue, abort, and recovery routes do not load
this file or the bundled [valid example](./example-plan.json).

## Start: bind refs and repository state

Search the repository's instruction locations and record every candidate path plus whether it is
present. Load every present source. An explicit search with no present sources is valid; an omitted
search is not. Resolve the repository root, named local branch, target, and their full commit OIDs.
Use `refs/heads/<branch>` to bind a local branch exactly.[1]

Run the ref lookups in the listed order. The first failed branch or target lookup enters
`BLOCKED_INVALID_REF` and ends the invocation immediately; retain that command and output without
running any later command.

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
uv run --script "<skill-dir>/scripts/rebase_plan.py" path-state <resolved-rebase-merge-path>
uv run --script "<skill-dir>/scripts/rebase_plan.py" path-state <resolved-rebase-apply-path>
```

`git rev-parse --git-path` resolves a path; it does not test that path's existence.[2] Resolve both
returned rebase paths against the repository, then capture each `path-state` command and its JSON
result in the matching marker evidence. A directory at either path means a rebase is active.[7]
Treat an absent `MERGE_HEAD` or `CHERRY_PICK_HEAD` as the expected nonzero result; presence means
that operation is active.[1]

Record the old branch OID, target OID, merge-base OID, current branch, complete porcelain status,
operation-marker existence, owning worktree, configured upstream, and every remote ref containing
the old tip.[6] Report these observable local publication signals without claiming knowledge of
downstream consumers. Record every repository instruction source examined and every required
preflight as complete argv, exit code, stdout, and stderr. Store the instruction observations in
`repository_instruction_search`, the present paths in `repository_instruction_sources`, and the
universal command records and marker observations in `repository_state`. Bind the plan's top-level
`execution_mode` to `CURRENT_BRANCH` or `AUTHORIZED_BRANCH_TRANSFER`;
[the evidence model](../scripts/rebase_evidence.py) defines their binding checks.

Bind every preflight result through the canonical state contract returned by
`rebase_plan.py states`:

- A failed branch or target lookup, or identical ref names, enters `BLOCKED_INVALID_REF`.
- Merge-base exit one after both refs resolve enters `BLOCKED_UNRELATED_HISTORIES`; another
  merge-base failure enters `BLOCKED_PREFLIGHT_FAILED`.
- A failed repository-root, worktree-list, status, current-branch, Git-path, path-state, upstream,
  publication, or repository-required preflight enters `BLOCKED_PREFLIGHT_FAILED`.
- A successful status with tracked or untracked changes, or an observed Git operation, enters
  `BLOCKED_GIT_STATE`. Preserve the worktree as observed.
- Distinct ref names resolving to one OID enter `NO_CHANGE` with zero candidates and no recovery ref.

When the branch is owned by another worktree or execution would switch branches, apply the worktree
ownership and branch transfer procedure below. Enter
`BLOCKED_WORKTREE_IN_USE` unless the current session owns the mutation path and every repository
branch-transfer gate passes.[3] After selecting a different authorized execution worktree, change
the command working directory to that worktree and restart this entire immutable evidence capture;
only evidence captured there may satisfy `READY_TO_ANALYZE`.

Completion criterion: `READY_TO_ANALYZE` contains immutable branch, target, and merge-base OIDs; an
authorized clean worktree; false/absent results for every operation marker; exact local publication
evidence; and successful outputs for every repository-required preflight.

## Start: inventory every replay candidate and affected path

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
commits that can become empty, apply the merge topology and commits Git can drop procedure below.
Capture `git rebase -h`; bind `becomes_empty_option` to the advertised stop-on-empty spelling
(`stop` or `ask`) and store the complete help output in the plan. An unavailable safety option
blocks execution.

Completion criterion: every ordered source-only candidate and every affected branch path appears
exactly once in the inventory with intent, evidence, dependencies, disposition, and verification
surface.

## Start: create recovery and pass the accounted plan gate

Create a uniquely named local recovery branch at the captured old tip and prove it resolves to that
OID before emitting a ready state:

```bash
git branch rebase-backup/<plan-id> <old-tip-oid>
git rev-parse --verify refs/heads/rebase-backup/<plan-id>^{commit}
```

If recovery-ref creation or verification fails, enter `BLOCKED_GIT_STATE`. Keep the recovery ref
after the rebase; cleanup is outside this workflow.

Create a JSON plan artifact from the complete evidence and recovery verification. Read the bundled
[valid example](./example-plan.json), then obtain the complete maintained schema:

```bash
uv run --script "<skill-dir>/scripts/rebase_plan.py" schema
```

Write the full artifact to the repository scratch location or a user-selected path. Preserve every
command output; the validator imposes no display truncation. Validate before any rebase command:

```bash
uv run --script "<skill-dir>/scripts/rebase_plan.py" validate <plan.json>
```

The maintained `schema` output defines the typed repository-state bundle, instruction-search
evidence, complete plan inputs, captured `rev-list` graph, and verified recovery ref. The `validate`
result is authoritative for failed or contradictory evidence, unresolved decisions, incomplete path
coverage, unsupported drops, unbound merge policy, and the plan SHA-256.

Only exit code zero with compact JSON `status=VALID`, `state=READY_TO_REBASE`, and a plan SHA-256
passes the gate. `PLAN_INVALID` ends the current invocation: retain the plan and its complete
structured errors. A later invocation may correct the retained artifact and validate it again.

Enter `NEEDS_USER_DECISION` for an unapproved discard, topology flattening, intent change,
published-branch impact, or semantic ambiguity. Ask one concrete question for each decision and
preserve the plan without mutation. The original explicit rebase request covers execution only when
every candidate and change is accounted, `Unknowns: none`, and no extra decision is required.

Completion criterion: the persisted plan validates as an exact cover of the captured replay graph
and affected paths, every preflight and recovery check has a successful evidence record, every
destructive decision is approved, unknowns are empty, and the validator returns `READY_TO_REBASE`
plus the artifact SHA-256.

## Start: recheck immutable refs and recovery

Resolve the branch and target names again. If either differs from the plan, enter
`REPLAN_REF_DRIFT`, retain and mark the plan stale, and return to the binding procedure without
rebasing. Reconfirm the authorized worktree, clean state, branch-transfer gate, and absence of a Git
operation.

Rerun `uv run --script "<skill-dir>/scripts/rebase_plan.py" validate <plan.json>` on the persisted
artifact. Require the same SHA-256 recorded at the plan gate; a changed or invalid artifact returns
to the plan gate. Reverify that the recovery ref still resolves to the captured old-tip OID.

Completion criterion: branch and target names still match the planned OIDs, the execution worktree
remains authorized and clean, and the durable recovery ref resolves exactly to the old-tip OID.

## Start: execute and route every stop

Assert the executing worktree is on the planned branch, or pass the planned branch explicitly only
after its branch-transfer gate. Execute against the immutable target OID with the plan's merge
policy. Always surface clean cherry-picks and commits that become empty:

```bash
git rebase --reapply-cherry-picks --empty=<becomes-empty-option> [--rebase-merges] <target-oid> [refs/heads/<branch>]
```

Include `--rebase-merges` only for a preserve-topology plan. Use the positional branch only when the
plan authorizes the resulting checkout; otherwise require the current branch to equal the planned
branch.[4]

When this new rebase stops on a conflict, unexpected conflict, empty commit, command failure, or
requested abort, follow the active-entry walkthrough before the next mutation.

Completion criterion: the rebase exits successfully with no active rebase metadata, or execution
reaches one named blocked, decision, aborted, or failure terminal with the exact command, output,
status, and recovery ref preserved.

## Start: verify intent, repository state, and recovery

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

For preserved merge topology, augment `range-diff` with the planned commit/parent and tree
evidence.[5] Account for every old candidate through its disposition; a missing mapping is a
validation failure. Run every exact repository check named in the plan and retain its exit code and
output.

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

The bundled [valid example](./example-plan.json) uses `candidates`, `affected_paths`, `publication`,
`repository_instruction_search`, `repository_preflights`, and `recovery_verification` to adapt a
parser change through a target API change with no unknown. The validator must return
`READY_TO_REBASE` and its SHA-256 before rebase execution.

## Failure example

The plan records target OID `51ad71b...`, but the pre-execution lookup returns `d7490c1...`. Emit
`REPLAN_REF_DRIFT`, preserve the plan as stale evidence, and return to the binding procedure. Running
against either OID under the stale plan is not an allowed transition.

## Active entry walkthrough

Enter this route only for an explicit continue or abort request, or when a newly started rebase
stops. Inspect the repository before any further mutation:

Replace `<skill-dir>` with the absolute base directory for this skill supplied by the harness; run
this single inspector instead of reconstructing its Git checks:

```bash
uv run --script "<skill-dir>/scripts/rebase_active.py"
```

Treat the inspector result as an immediate route:

- `BLOCKED_PREFLIGHT_FAILED`: end without mutation.
- `NO_ACTIVE_REBASE`: end without running `git rebase --continue`, `git rebase --abort`, or a new
  rebase.
- `active`: detached `HEAD` is expected. Bind the complete inspector evidence, then continue with
  the active-operation walkthrough.

Completion criterion: the inspector reaches a terminal with no later action, or its `active` route
enters the operation procedure.

## Conflict, empty-commit, and abort walkthrough

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

## Worktree ownership and branch transfer

Parse `git worktree list --porcelain` as records. Match `branch refs/heads/<branch>` and record its
`worktree` path.[3]

- If the match names another worktree, establish from session context that this session owns that
  worktree. If ownership is absent or unknown, emit `BLOCKED_WORKTREE_IN_USE`; leave its branch,
  HEAD, index, tracked files, and untracked files unchanged. If ownership is established, enter that
  worktree and restart all evidence capture there before testing cleanliness or planning.
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
commit.[8] Choose one policy before execution:

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
`EMPTY_COMMIT_DECISION` and apply the empty-commit walkthrough above.

Git documents the default merge-commit drop, `--rebase-merges`, clean-cherry-pick handling,
`--reapply-cherry-picks`, and empty-commit behavior on the rebase reference.[4]

## References

1. [gitrevisions — specifying revisions](https://git-scm.com/docs/gitrevisions) (accessed 2026-09-22)
2. [git-rev-parse — `--git-path`](https://git-scm.com/docs/git-rev-parse) (accessed 2026-09-22)
3. [git-worktree](https://git-scm.com/docs/git-worktree) (accessed 2026-09-22)
4. [git-rebase](https://git-scm.com/docs/git-rebase) (accessed 2026-09-22)
5. [git-range-diff](https://git-scm.com/docs/git-range-diff) (accessed 2026-09-22)
6. [git-for-each-ref](https://git-scm.com/docs/git-for-each-ref) (accessed 2026-09-22)
7. [gitrepository-layout — rebase state directories](https://git-scm.com/docs/gitrepository-layout) (accessed 2026-09-22)
8. [git-rev-list — commit listing and `--parents`](https://git-scm.com/docs/git-rev-list) (accessed 2026-09-22)

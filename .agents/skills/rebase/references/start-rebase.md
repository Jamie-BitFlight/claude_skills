# Start a rebase

Enter only for an explicit request to replay a named local branch or ref. Run
`uv run --script "<skill-dir>/scripts/rebase_plan.py" states` for the canonical state meanings,
next actions, artifact policies, and evidence contracts.

## 1. Bind immutable repository evidence

Search every repository instruction location and record each candidate path as present or absent;
load every present source. An all-absent result is valid; an omitted search is not. Bind the
repository root, exact `refs/heads/<branch>`, immutable branch, target, and merge-base OIDs,
current branch, complete porcelain status, worktree ownership,
configured upstream, remote refs containing the old tip, and all operation-marker evidence. Capture
every command as complete argv, exit code, stdout, and stderr in the typed `repository_state`,
`repository_instruction_search`, `repository_instruction_sources`, repository-preflight,
publication, and `execution_mode` fields.

Resolve branch then target in that order. The first failed lookup is the last action and
`BLOCKED_INVALID_REF`. Route unrelated histories, other preflight failures, dirty/active Git state,
and same-OID refs through the canonical states; same-OID refs reach `NO_CHANGE` with no recovery ref.
Rebase metadata directories establish an active rebase; `REBASE_HEAD` alone does not. Detached
`HEAD` is valid only on the active route.

If another worktree owns the branch or execution would transfer it, read only
[worktree ownership and branch transfer](./rebase-edge-cases.md#worktree-ownership-and-branch-transfer).
Require session ownership and every repository transfer gate. After authorized transfer, change to
that worktree and recapture all evidence there; otherwise emit `BLOCKED_WORKTREE_IN_USE` without
changing either worktree.

Completion criterion: `READY_TO_ANALYZE` binds immutable OIDs, an authorized clean worktree,
absent operations, observed publication signals, and successful repository checks.

## 2. Account for every candidate and path

Capture the ordered parent graph and an exact candidate/path cover. Account for intermediate
net-zero changes, rename/copy pairs, cross-file dependencies, target interaction, merges, clean
cherry-picks, start-empty commits, and commits that can become empty; endpoint diffs cannot replace
the graph. Give every candidate and path intent, evidence, dependencies, verification surfaces, and
one disposition: `RETAIN`, `ADAPT`, `MANUAL_MERGE`, `REDUNDANT_DROP`, or `PRESERVE_EMPTY`.

No disposition authorizes whole-file side selection. `REDUNDANT_DROP` requires observable target
equivalence or explicit approval. A start-empty candidate uses no paths and `PRESERVE_EMPTY`.
For merge, clean-cherry-pick, or either empty class, read only
[merge topology and commits Git can drop](./rebase-edge-cases.md#merge-topology-and-commits-git-can-drop).
Bind the topology policy and installed-help-validated merge/empty options; unavailable safety
options block execution.

Completion criterion: the inventory exactly covers every ordered source-only candidate and affected
path, including every candidate Git could silently omit.

## 3. Bind recovery and validate the plan

Create a unique durable local recovery ref at the captured old tip and verify that exact OID before
readiness. Cleanup and remote backup are outside this workflow.

Obtain the maintained artifact contract from
`uv run --script "<skill-dir>/scripts/rebase_plan.py" schema`; persist the complete evidence and
decisions, then run `uv run --script "<skill-dir>/scripts/rebase_plan.py" validate <plan.json>`.
Only exit zero with `status=VALID`, `state=READY_TO_REBASE`, and a retained SHA-256 passes.
`PLAN_INVALID` is terminal and retains structured errors.

Use `NEEDS_USER_DECISION` for unapproved discard, topology flattening, semantic change, publication
impact, or reconstruction ambiguity. Preserve the artifact without mutation until every decision is
approved and `unknowns` is empty.

Completion criterion: a persisted schema-valid exact-cover plan binds successful preflight and
recovery evidence and returns `READY_TO_REBASE` plus its SHA-256.

## 4. Reject drift immediately before mutation

Recheck the branch and target OIDs, authorized clean worktree, absence of operations, branch-transfer
gate, plan validity and identical SHA-256, and recovery ref resolving to the captured old tip. Any ref
drift emits `REPLAN_REF_DRIFT`; retain and mark the artifact stale, then recapture from Step 1. Any
artifact drift returns to Step 3. Do not execute a stale plan.

Completion criterion: every immutable binding and recovery proof still matches the validated plan.

## 5. Execute only validated intent

Require the execution worktree to hold the planned branch unless the plan authorizes positional
branch transfer. Execute against the immutable target with only the validated merge and
installed-help-validated empty policies, surfacing clean cherry-picks and becomes-empty commits.
Route every conflict, empty stop, command failure, or requested abort through
[active rebase](./active-rebase.md) before another mutation.

Completion criterion: execution either has no active rebase metadata or ends at one canonical
blocked, decision, aborted, or failure terminal with command, output, status, and recovery evidence.

## 6. Prove completion

Verify planned branch identity and target ancestry, every old candidate disposition and old-to-new
mapping, repository checks, clean worktree, no unmerged paths or active operation, and the recovery
ref. Preserved merge topology also requires planned parent/tree evidence. Any failed oracle emits
`REBASE_COMPLETE_VALIDATION_FAILED`, preserves rewritten and recovery refs, and stops mutation.

Only a complete pass emits `REBASE_COMPLETE_VERIFIED`. Report immutable branch/target/old/new OIDs,
dispositions, repository-check evidence, clean state, recovery ref, and `not published`. Make that
terminal the last action.

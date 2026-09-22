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

After instruction search, run `git rev-parse --show-toplevel` alone, then run
`git show-ref --verify refs/heads/<branch>` alone. Do not batch or parallelize either with later
preflight work. A branch failure is the last action and `BLOCKED_INVALID_REF`. Only after success,
resolve the target alone; its failure has the same terminal boundary. Route unrelated histories,
other preflight failures, dirty/active Git state, and same-OID refs through the canonical states;
same-OID refs reach `NO_CHANGE` with no recovery ref.
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

For routine execution, use only the maintained artifact contract from
`uv run --script "<skill-dir>/scripts/rebase_plan.py" schema`; the bundled example belongs only to
the tutorial route. Persist the complete evidence and decisions, then run
`uv run --script "<skill-dir>/scripts/rebase_plan.py" validate <plan.json>`.
Only exit zero with `status=VALID`, `state=READY_TO_REBASE`, and a retained SHA-256 passes.
`PLAN_INVALID` is terminal and retains structured errors.

Use `NEEDS_USER_DECISION` for unapproved discard, topology flattening, semantic change, publication
impact, or reconstruction ambiguity. Preserve the artifact without mutation until every decision is
approved and `unknowns` is empty.

Completion criterion: a persisted schema-valid exact-cover plan binds successful preflight and
recovery evidence and returns `READY_TO_REBASE` plus its SHA-256.

## 4. Reject drift immediately before mutation

Run
`uv run --script "<skill-dir>/scripts/rebase_plan.py" execute <plan.json> --expected-sha256 <validated-sha256>`.
This single-use operation revalidates the artifact, rechecks live refs, authorized worktree
ownership, clean state, operation absence, and recovery, derives replay argv from typed policy, then
persists a consumed receipt before running that argv. Any response without a receipt and replay
result blocks mutation; ref drift requires recapture from Step 1 through `REPLAN_REF_DRIFT`, and
artifact/hash drift returns to Step 3.

Completion criterion: every live binding matches the unchanged plan and one durable receipt binds
the plan hash to its canonical replay result.

## 5. Execute only validated intent

Treat the consumed plan hash as single-use. No other initial replay form is authorized; an `--onto`
range requires a future typed schema that binds every boundary. Retain the receipt, rewritten
branch, and recovery ref through the terminal. Route every conflict, empty stop, command failure, or
requested abort through
[active rebase](./active-rebase.md) before another mutation.

Completion criterion: execution either has no active rebase metadata or ends at one canonical
blocked, decision, aborted, or failure terminal with command, output, status, and recovery evidence.

## 6. Prove completion

Verify planned branch identity and target ancestry, every old candidate disposition and old-to-new
mapping, repository checks, clean worktree, no unmerged paths or active operation, and the recovery
ref. Preserved merge topology also requires planned parent/tree evidence. Any failed oracle emits
`REBASE_COMPLETE_VALIDATION_FAILED`, freezes rewritten and recovery refs, and stops mutation.
Another history mutation requires an explicit recovery decision and a newly validated plan.

Only a complete pass emits `REBASE_COMPLETE_VERIFIED`. Report immutable branch/target/old/new OIDs,
dispositions, repository-check evidence, clean state, recovery ref, and `not published`. Make that
terminal the last action.

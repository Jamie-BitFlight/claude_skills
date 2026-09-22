# Start a rebase

Enter only for an explicit request to replay a named local branch or ref. Bind `<skill-dir>` to
the loaded skill directory. Routine work uses only the managed operations below; they own Git
evidence, artifact paths, recovery, replay argv, and terminal states.

## 1. Capture invocation intent

Run:

```text
uv run --script "<skill-dir>/scripts/rebase_plan.py" capture --branch "<branch>" --target "<target>" [--expected-target-oid "<invocation-bound-oid>"]
```

Pass the expected target OID whenever the invocation supplies one. Never replace an expected OID
with a newly observed value. `capture` performs ordered ref, repository, publication, graph,
candidate, and path capture and stores immutable evidence under Git metadata without dirtying the
worktree.

Every result with `terminal=true` ends the invocation. It is the final tool result: emit that
state immediately, with no bookkeeping, repair, recapture, retry, or other tool call. In particular:

- `BLOCKED_INVALID_REF` ends without managed state or mutation.
- `REPLAN_REF_DRIFT` ends without recovery, plan, or replay; new target intent requires a later
  invocation.
- `NEEDS_USER_DECISION` for publication impact retains only the capture. A later invocation must
  carry explicit user-approval evidence bound to its repository, branch, old tip, target, capture,
  and operation.

Completion criterion: a nonterminal `READY_TO_ANALYZE` result returns a capture ID and semantic
template; or one canonical terminal is the invocation's last action.

## 2. Supply semantic judgment

Review the captured candidates and affected paths returned by `capture`. Fill only the returned
`semantic_template`: candidate intent, evidence-backed disposition, verification surfaces,
expected conflicts and equivalence; path interaction, dependencies, evidence and verification;
merge policy, repository checks, unknowns, and decision requests.

The semantic input cannot alter refs, OIDs, parents, paths, publication evidence, worktree state,
recovery, or replay argv. Agent-authored `approved` booleans have no authority. Destructive,
topology, semantic, or publication approvals require externally supplied receipts.

Completion criterion: every captured candidate and path has one evidence-backed semantic judgment,
`unknowns` is empty, and every approval-requiring decision is explicit.

## 3. Finalize the managed plan

Run in a later invocation when a prior terminal required approval:

```text
uv run --script "<skill-dir>/scripts/rebase_plan.py" finalize "<capture-id>" --semantics-json '<filled-template>' [--approval-receipt "<external-read-only-receipt>"]...
```

`finalize` accepts semantic fields only, validates exact coverage and externally bound receipts,
then creates recovery and the plan under Git metadata. Files in the repository or its Git directory
are not external approval authority. The portable receipt contract records provenance but cannot
cryptographically prove which actor created it; when the harness cannot supply trustworthy
human-gate evidence, fail closed at `NEEDS_USER_DECISION`.

A terminal finalize result is the invocation's final tool result. Do not edit `.git/info/exclude`,
write workflow artifacts into the worktree, or repair and retry in the same invocation.
`PLAN_INVALID` retains its structured errors for a later invocation.

Completion criterion: `READY_TO_REBASE` returns a managed plan ID and SHA-256, with verified
recovery at the captured old tip and a clean worktree.

## 4. Execute once

Run only:

```text
uv run --script "<skill-dir>/scripts/rebase_plan.py" execute "<managed-plan-id>" --expected-sha256 "<finalized-sha256>"
```

`execute` rejects unmanaged worktree plans, revalidates live refs, worktree ownership, clean
state, operation absence and recovery, derives canonical replay argv, atomically consumes the plan
hash, then runs that argv once. Any blocked or decision result ends the invocation; recovery or
retry requires a later invocation and a newly authorized managed flow.

When replay stops in an active operation, route a later invocation through
[active rebase](./active-rebase.md). After successful replay, verify the accounted candidate intent,
target ancestry, repository checks, clean state, absent operation markers, and recovery ref. Only a
complete pass emits `REBASE_COMPLETE_VERIFIED` and `not published`.

# Active rebase operation

Enter only after `rebase_active.py` returns `active`. Run
`uv run --script "<skill-dir>/scripts/rebase_plan.py" states` for the canonical state, next action,
artifact, and evidence contract.

Bind current branch, status, rebase metadata, `REBASE_HEAD`, and recovery ref. If the plan is absent,
reconstruct old tip, target, current and remaining candidates, and affected paths from Git evidence.
Emit `NEEDS_USER_DECISION` for any unknown. Before continuing or aborting, create and verify a unique
local recovery ref at the reconstructed old tip when none exists.

During conflicts, `ours` is the accumulated series on the target and `theirs` is the replayed branch
commit. Resolve by planned intent and hunk evidence; no side label authorizes whole-file replacement.
Stage only named resolved paths. Require no unmerged paths, successful diff checks, and relevant
repository checks before continuing.

For `UNEXPECTED_CONFLICT`, record the candidate, path, hunk, and plan mismatch. Update the exact
candidate/path evidence and disposition. Emit `NEEDS_USER_DECISION` for changed intent, discard, or
ambiguity; otherwise revalidate the exact-cover plan before continuation.

For `EMPTY_COMMIT_DECISION`, identify the exact candidate and compare its planned intent and patch
with the target and rewritten tree. Skip only an approved `REDUNDANT_DROP` with observable
equivalence. Preserve only a planned `PRESERVE_EMPTY` and verify the result. Otherwise emit
`NEEDS_USER_DECISION`.

On abort, capture the old tip before mutation. Emit `REBASE_ABORTED_RESTORED` only after proving the
planned branch equals that OID, rebase metadata is absent, unmerged output is empty, the worktree
matches its pre-state, and recovery still resolves. Any mismatch emits `BLOCKED_ABORT_FAILED` with
exact evidence and stops mutation.

A failed command without an active stop emits `BLOCKED_COMMAND_FAILED`. A failed post-rebase oracle
emits `REBASE_COMPLETE_VALIDATION_FAILED`. Preserve rewritten and recovery refs and stop further
mutation. End with exactly one canonical terminal as the last action.

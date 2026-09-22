# Review-cycle contract

Read this contract after obtaining a complete snapshot and before assessing inputs or authoring the
cycle state. The Pydantic models are the exact schema; `validate-cycle` and `complete-cycle` are the
executable gates.

## Context and census

Bind one cycle to one target, current remote revision, intended task or product outcome, repository
instructions, and saved full snapshot. The snapshot closes only when `snapshot_complete` and its
completeness evidence prove every required surface finished, no input was truncated, one transport was
used, and a canonical fingerprint exists.

The inbound census contains every normalized inline or top-level comment, semantic question,
approval, rejection/change request, bot summary, and human, reviewer, or stakeholder input. Canonical
IDs are unique, and snapshot inbound IDs equal `input_census` exactly. Resolved history remains part
of pattern analysis. Provider metadata remains observable without becoming actor-backed input.

Any pagination, required-surface, nested-conversation, schema, or transport gap yields
`SNAPSHOT_INCOMPLETE`. Assessment, source edits, replies, resolutions, and completion wait for a
complete saved snapshot.

## Assessment

Create exactly one assessment for each inbound ID and none outside the census. Record validity,
relevance, evidence, affected scope, verification surface, disposition, semantic kinds, unknowns,
cluster assignment, and communication plan. Preserve normalized kinds; a normalized comment may also
be assessed as a question. Explicitly assess approvals and rejections, including empty-body events.

Resolve each unknown with evidence or name one missing fact and one focused clarification or
escalation path. Actor class, actor role, and revision relation remain unknown unless provider evidence
establishes them. This gate closes only when `assessed_inputs` preserves each exact canonical input and
the census, assessment, and unknown-decision sets agree.

## Clusters and systemic plans

Clusters have unique IDs and form a disjoint exact cover of the census. Unrelated inputs become
explicit singleton clusters. A multi-input cluster records the shared invariant, component, root
cause, requested outcome, or verification surface that makes one outcome coherent.

Each cluster has one systemic outcome, supporting evidence, exact verification commands,
communication plan, and resolution policy. When inputs share a cause, repeated symptom patches do not
satisfy this gate. Complete the census, assessments, unknown decisions, clusters, and plans before any
source action.

## Implementation or no-change evidence

- `accepted_change`: change the owning seam once, cover every cluster member, and record implementation
  evidence.
- `no_change`: record evidence that the claim is disproved, already satisfied, outside an explicit
  requirement, or otherwise unwarranted.
- `superseded`: cite the later provider content that withdraws or replaces the input.
- `clarification_required`: record the missing fact and focused question; keep the input open and the
  cycle non-terminal.

Map every input implementation state to `completed` or `not_required`. When source changes are
authorized, verify and push them to the current inspectable remote revision before a response cites
them.

## Verification and authority

Execute each cluster's verification commands and every repository-required gate for the affected
surface. Record actual results. The cycle target, remote head, inspectable revision, snapshot and
recheck fingerprints, assessed canonical inputs, and exact per-input states must match the saved
snapshot.

Run `validate-cycle`; zero exit is necessary before provider mutation and grants no authority. Fetch,
watch, and validation are read-only. Source edits, pushes, replies/comments, and resolutions each need
authority from the request or repository standing policy. A check-only request stays read-only.

Every mutation refreshes provider state before its first provider call and rejects stale target,
revision, fingerprint, changed input, incomplete cycle, unsupported capability, or unauthorized
resolution policy. A batch pre-authorizes every entry and action before its first call.

## Communication and resolution

Communicate one evidence-bearing disposition for every inbound input, including approvals,
rejections, bot summaries, no-change results, and superseded inputs. Bind it to the canonical stable
reference. Provider-backed evidence, not caller-authored local state, proves completion.

Reply successfully before resolving. Use the combined action for a normal eligible inline path; use
reply-only for clarification, and resolve-only for recovery when completed communication is already
provider-proved. Apply the cluster resolution policy and provider capability. Clarification remains
open. An unresolvable approval, rejection, top-level input, or provider object records `unavailable`.
Preserve successful communication if resolution fails, and stop a batch before calling its next entry.

The communication gate closes when every inbound input is provider-backed `completed`. The resolution
gate closes when every input is provider-confirmed `resolved` or truthfully `unavailable`.

## Recheck and terminal

Fetch a new complete snapshot after communication. Any changed canonical input, provider state,
revision, fingerprint, body, edit time, resolution, or communication evidence returns the complete
set to census, assessment, and clustering. Bounded `watch` calls only sample for later change; a
timed-out call means no stop signal was observed in those snapshots.

`REVIEW_COMPLETE` requires the final current snapshot to be complete and unchanged, with zero
unresolved, outstanding, new, changed, or unresponded input; exact assessed-input equality; exact
census and cluster coverage; terminal implementation, communication, and resolution states;
provider-backed communication; and one terminal annotation per input.

A current GitHub Codex approval remains an assessed input and can coexist with completion only after
its full lifecycle is recorded. GitLab's absent equivalence remains unavailable and null. Approval,
rejection/change request, a clear initial snapshot, an elapsed quiet window, local communication
without provider evidence, or resolution without recheck never completes a cycle. Only a successful
persisted `complete-cycle` result emits `REVIEW_COMPLETE`.

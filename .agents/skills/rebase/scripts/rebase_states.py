"""Canonical state vocabulary for the accounted rebase workflow."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, Field


class StateKind(StrEnum):
    """Whether a workflow state continues or ends the current invocation."""

    TRANSITION = "transition"
    TERMINAL = "terminal"


class WorkflowState(StrEnum):
    """Canonical state vocabulary for the rebase workflow."""

    READY_TO_ANALYZE = "READY_TO_ANALYZE"
    PLAN_INVALID = "PLAN_INVALID"
    READY_TO_REBASE = "READY_TO_REBASE"
    BLOCKED_INVALID_REF = "BLOCKED_INVALID_REF"
    BLOCKED_UNRELATED_HISTORIES = "BLOCKED_UNRELATED_HISTORIES"
    BLOCKED_PREFLIGHT_FAILED = "BLOCKED_PREFLIGHT_FAILED"
    BLOCKED_GIT_STATE = "BLOCKED_GIT_STATE"
    BLOCKED_WORKTREE_IN_USE = "BLOCKED_WORKTREE_IN_USE"
    NO_ACTIVE_REBASE = "NO_ACTIVE_REBASE"
    NO_CHANGE = "NO_CHANGE"
    NEEDS_USER_DECISION = "NEEDS_USER_DECISION"
    REPLAN_REF_DRIFT = "REPLAN_REF_DRIFT"
    CONFLICT = "CONFLICT"
    UNEXPECTED_CONFLICT = "UNEXPECTED_CONFLICT"
    EMPTY_COMMIT_DECISION = "EMPTY_COMMIT_DECISION"
    REBASE_ABORTED_RESTORED = "REBASE_ABORTED_RESTORED"
    BLOCKED_ABORT_FAILED = "BLOCKED_ABORT_FAILED"
    BLOCKED_COMMAND_FAILED = "BLOCKED_COMMAND_FAILED"
    REBASE_COMPLETE_VALIDATION_FAILED = "REBASE_COMPLETE_VALIDATION_FAILED"
    REBASE_COMPLETE_VERIFIED = "REBASE_COMPLETE_VERIFIED"


class WorkflowStateDefinition(BaseModel):
    """One canonical workflow state, entry condition, and next action."""

    name: WorkflowState
    kind: StateKind
    condition: Annotated[str, Field(min_length=1)]
    next_action: Annotated[str, Field(min_length=1)]
    artifact_policy: Annotated[str, Field(min_length=1)]
    evidence: Annotated[list[str], Field(min_length=1)]


WORKFLOW_STATE_DEFINITIONS = (
    WorkflowStateDefinition(
        name=WorkflowState.READY_TO_ANALYZE,
        kind=StateKind.TRANSITION,
        condition="Every immutable preflight completed in the authorized execution worktree.",
        next_action="Inventory every replay candidate and affected path.",
        artifact_policy="Retain the complete immutable preflight evidence.",
        evidence=["immutable refs", "authorized clean worktree", "no active Git operation"],
    ),
    WorkflowStateDefinition(
        name=WorkflowState.PLAN_INVALID,
        kind=StateKind.TERMINAL,
        condition="The persisted plan validator returned an invalid or error result.",
        next_action="End this invocation; a later invocation may correct the retained plan and validate again.",
        artifact_policy="Retain the plan and complete structured validator output.",
        evidence=["validator errors", "no rebase command"],
    ),
    WorkflowStateDefinition(
        name=WorkflowState.READY_TO_REBASE,
        kind=StateKind.TRANSITION,
        condition="The exact-cover plan and durable recovery ref passed every gate.",
        next_action="Recheck immutable refs and recovery before execution.",
        artifact_policy="Retain the validated plan and its SHA-256.",
        evidence=["validator status VALID", "plan SHA-256", "recovery ref resolves to old tip"],
    ),
    WorkflowStateDefinition(
        name=WorkflowState.BLOCKED_INVALID_REF,
        kind=StateKind.TERMINAL,
        condition="A named branch or target ref is absent, invalid, or identical to the other ref name.",
        next_action="End without mutation and report the exact ref lookup or identical names.",
        artifact_policy="Retain the ref lookup output.",
        evidence=["exact failing ref lookup or identical ref names", "unchanged refs"],
    ),
    WorkflowStateDefinition(
        name=WorkflowState.BLOCKED_UNRELATED_HISTORIES,
        kind=StateKind.TERMINAL,
        condition="Both refs resolve to commits but git merge-base reports no common ancestor.",
        next_action="End without mutation and report that ordinary rebase has no merge base.",
        artifact_policy="Retain both immutable OIDs and merge-base output.",
        evidence=["valid branch and target OIDs", "merge-base exit one", "unchanged refs"],
    ),
    WorkflowStateDefinition(
        name=WorkflowState.BLOCKED_PREFLIGHT_FAILED,
        kind=StateKind.TERMINAL,
        condition="A required non-ref preflight command failed or returned unusable evidence.",
        next_action="End without mutation and report the exact command and output.",
        artifact_policy="Retain every successful and failed preflight record captured so far.",
        evidence=["exact failing preflight and output", "no rebase mutation"],
    ),
    WorkflowStateDefinition(
        name=WorkflowState.BLOCKED_GIT_STATE,
        kind=StateKind.TERMINAL,
        condition="The execution worktree is dirty, another Git operation is active, or recovery creation failed.",
        next_action="End without starting or continuing a rebase.",
        artifact_policy="Retain status, operation-marker, and recovery evidence.",
        evidence=["dirty status, active operation, or recovery-ref failure", "no new rebase"],
    ),
    WorkflowStateDefinition(
        name=WorkflowState.BLOCKED_WORKTREE_IN_USE,
        kind=StateKind.TERMINAL,
        condition="The planned branch is owned by a worktree this session does not own.",
        next_action="End without entering or changing the foreign worktree.",
        artifact_policy="Retain the worktree ownership record.",
        evidence=["foreign owning worktree path", "unchanged foreign worktree"],
    ),
    WorkflowStateDefinition(
        name=WorkflowState.NO_ACTIVE_REBASE,
        kind=StateKind.TERMINAL,
        condition="A continue or abort request finds no active rebase metadata; REBASE_HEAD is evidence only.",
        next_action="End without running rebase --continue, rebase --abort, or a new rebase.",
        artifact_policy="Retain the operation-marker and REBASE_HEAD observations.",
        evidence=["no rebase metadata", "REBASE_HEAD observation, present or absent", "no rebase mutation"],
    ),
    WorkflowStateDefinition(
        name=WorkflowState.NO_CHANGE,
        kind=StateKind.TERMINAL,
        condition="Distinct branch and target refs resolve to the same commit OID.",
        next_action="End without creating recovery or running rebase.",
        artifact_policy="Retain ref-resolution evidence.",
        evidence=["distinct refs resolve to one OID", "zero candidates", "no recovery ref"],
    ),
    WorkflowStateDefinition(
        name=WorkflowState.NEEDS_USER_DECISION,
        kind=StateKind.TERMINAL,
        condition="A destructive, semantic, topology, publication, or reconstruction decision remains unresolved.",
        next_action="End after asking one concrete question for each unresolved decision.",
        artifact_policy="Retain the plan or reconstructed active-operation evidence without mutation.",
        evidence=["concrete unresolved decisions", "no new rebase"],
    ),
    WorkflowStateDefinition(
        name=WorkflowState.REPLAN_REF_DRIFT,
        kind=StateKind.TRANSITION,
        condition="A fresh branch or target lookup differs from the validated plan.",
        next_action="Mark the retained plan stale and restart immutable evidence capture at Step 1.",
        artifact_policy="Retain the stale plan and fresh ref evidence; never execute it.",
        evidence=["fresh branch or target OID differs from plan", "no stale-plan rebase"],
    ),
    WorkflowStateDefinition(
        name=WorkflowState.CONFLICT,
        kind=StateKind.TRANSITION,
        condition="Rebase stopped with unmerged entries matching the accounted conflict surface.",
        next_action="Run the conflict evidence, resolution, staging, checking, and continuation loop.",
        artifact_policy="Update the active plan evidence with the stopped candidate and resolution checks.",
        evidence=["current candidate", "unmerged entries", "active resolution loop"],
    ),
    WorkflowStateDefinition(
        name=WorkflowState.UNEXPECTED_CONFLICT,
        kind=StateKind.TRANSITION,
        condition="Rebase stopped on a conflict outside the accounted conflict surface.",
        next_action="Record the deviation, update dispositions, and revalidate before continuation.",
        artifact_policy="Retain the prior plan and its explicit deviation record.",
        evidence=["recorded plan deviation", "revalidated disposition before continuation"],
    ),
    WorkflowStateDefinition(
        name=WorkflowState.EMPTY_COMMIT_DECISION,
        kind=StateKind.TRANSITION,
        condition="A replay candidate became empty and Git stopped for a disposition decision.",
        next_action="Prove the approved drop or preserve disposition before continuing.",
        artifact_policy="Record the exact candidate and equivalence or preservation evidence.",
        evidence=["exact stopped candidate", "approved skip or preserve evidence"],
    ),
    WorkflowStateDefinition(
        name=WorkflowState.REBASE_ABORTED_RESTORED,
        kind=StateKind.TERMINAL,
        condition="Abort restored the captured old tip and recorded pre-state exactly.",
        next_action="End and report the restored branch and verified recovery ref.",
        artifact_policy="Retain the recovery ref and abort verification evidence.",
        evidence=["old tip restored", "clean recorded state", "recovery ref verified"],
    ),
    WorkflowStateDefinition(
        name=WorkflowState.BLOCKED_ABORT_FAILED,
        kind=StateKind.TERMINAL,
        condition="Abort failed or post-abort state differs from the recorded pre-state.",
        next_action="End further mutation and report the exact mismatch.",
        artifact_policy="Preserve all recovery and abort evidence.",
        evidence=["abort error or restoration mismatch", "recovery evidence preserved"],
    ),
    WorkflowStateDefinition(
        name=WorkflowState.BLOCKED_COMMAND_FAILED,
        kind=StateKind.TERMINAL,
        condition="A rebase mutation command failed outside a recognized conflict or empty stop.",
        next_action="End further mutation and report the exact command and output.",
        artifact_policy="Preserve refs, status, command output, and recovery evidence.",
        evidence=["failing command and output", "refs, status, and recovery evidence preserved"],
    ),
    WorkflowStateDefinition(
        name=WorkflowState.REBASE_COMPLETE_VALIDATION_FAILED,
        kind=StateKind.TERMINAL,
        condition="At least one post-rebase verification oracle failed.",
        next_action=(
            "End with no further history mutation; another mutation requires an explicit recovery decision "
            "and a newly validated plan."
        ),
        artifact_policy=(
            "Freeze and retain the rewritten branch, recovery ref, plan, and every oracle result through the terminal."
        ),
        evidence=["named failed verification oracle", "no publication claim"],
    ),
    WorkflowStateDefinition(
        name=WorkflowState.REBASE_COMPLETE_VERIFIED,
        kind=StateKind.TERMINAL,
        condition="Every ancestry, intent, repository-state, check, and recovery oracle passed.",
        next_action="End and report the verified local result as not published.",
        artifact_policy="Retain the plan, verification results, and recovery ref.",
        evidence=["all verification oracles passed", "old, new, target, and recovery OIDs reported"],
    ),
)


def workflow_state_definitions() -> dict[WorkflowState, WorkflowStateDefinition]:
    """Return the canonical workflow-state map."""
    return {definition.name: definition for definition in WORKFLOW_STATE_DEFINITIONS}

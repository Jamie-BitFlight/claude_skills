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
    BLOCKED_GIT_STATE = "BLOCKED_GIT_STATE"
    BLOCKED_WORKTREE_IN_USE = "BLOCKED_WORKTREE_IN_USE"
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
    """One canonical workflow state and its observable evidence."""

    name: WorkflowState
    kind: StateKind
    evidence: Annotated[list[str], Field(min_length=1)]


WORKFLOW_STATE_DEFINITIONS = (
    WorkflowStateDefinition(
        name=WorkflowState.READY_TO_ANALYZE,
        kind=StateKind.TRANSITION,
        evidence=["immutable refs", "authorized clean worktree", "no active Git operation"],
    ),
    WorkflowStateDefinition(
        name=WorkflowState.PLAN_INVALID, kind=StateKind.TERMINAL, evidence=["validator errors", "no rebase command"]
    ),
    WorkflowStateDefinition(
        name=WorkflowState.READY_TO_REBASE,
        kind=StateKind.TRANSITION,
        evidence=["validator status VALID", "plan SHA-256", "recovery ref resolves to old tip"],
    ),
    WorkflowStateDefinition(
        name=WorkflowState.BLOCKED_INVALID_REF,
        kind=StateKind.TERMINAL,
        evidence=["exact failing ref lookup or identical ref names", "unchanged refs"],
    ),
    WorkflowStateDefinition(
        name=WorkflowState.BLOCKED_GIT_STATE,
        kind=StateKind.TERMINAL,
        evidence=["dirty status, active operation, or recovery-ref failure", "no new rebase"],
    ),
    WorkflowStateDefinition(
        name=WorkflowState.BLOCKED_WORKTREE_IN_USE,
        kind=StateKind.TERMINAL,
        evidence=["foreign owning worktree path", "unchanged foreign worktree"],
    ),
    WorkflowStateDefinition(
        name=WorkflowState.NO_CHANGE,
        kind=StateKind.TERMINAL,
        evidence=["distinct refs resolve to one OID", "zero candidates", "no recovery ref"],
    ),
    WorkflowStateDefinition(
        name=WorkflowState.NEEDS_USER_DECISION,
        kind=StateKind.TERMINAL,
        evidence=["concrete unresolved decisions", "no new rebase"],
    ),
    WorkflowStateDefinition(
        name=WorkflowState.REPLAN_REF_DRIFT,
        kind=StateKind.TRANSITION,
        evidence=["fresh branch or target OID differs from plan", "no stale-plan rebase"],
    ),
    WorkflowStateDefinition(
        name=WorkflowState.CONFLICT,
        kind=StateKind.TRANSITION,
        evidence=["current candidate", "unmerged entries", "active resolution loop"],
    ),
    WorkflowStateDefinition(
        name=WorkflowState.UNEXPECTED_CONFLICT,
        kind=StateKind.TRANSITION,
        evidence=["recorded plan deviation", "revalidated disposition before continuation"],
    ),
    WorkflowStateDefinition(
        name=WorkflowState.EMPTY_COMMIT_DECISION,
        kind=StateKind.TRANSITION,
        evidence=["exact stopped candidate", "approved skip or preserve evidence"],
    ),
    WorkflowStateDefinition(
        name=WorkflowState.REBASE_ABORTED_RESTORED,
        kind=StateKind.TERMINAL,
        evidence=["old tip restored", "clean recorded state", "recovery ref verified"],
    ),
    WorkflowStateDefinition(
        name=WorkflowState.BLOCKED_ABORT_FAILED,
        kind=StateKind.TERMINAL,
        evidence=["abort error or restoration mismatch", "recovery evidence preserved"],
    ),
    WorkflowStateDefinition(
        name=WorkflowState.BLOCKED_COMMAND_FAILED,
        kind=StateKind.TERMINAL,
        evidence=["failing command and output", "refs, status, and recovery evidence preserved"],
    ),
    WorkflowStateDefinition(
        name=WorkflowState.REBASE_COMPLETE_VALIDATION_FAILED,
        kind=StateKind.TERMINAL,
        evidence=["named failed verification oracle", "no publication claim"],
    ),
    WorkflowStateDefinition(
        name=WorkflowState.REBASE_COMPLETE_VERIFIED,
        kind=StateKind.TERMINAL,
        evidence=["all verification oracles passed", "old, new, target, and recovery OIDs reported"],
    ),
)


def workflow_state_definitions() -> dict[WorkflowState, WorkflowStateDefinition]:
    """Return the canonical workflow-state map."""
    return {definition.name: definition for definition in WORKFLOW_STATE_DEFINITIONS}

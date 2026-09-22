#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pydantic>=2.0",
# ]
# ///
"""Validate an accounted local-rebase plan before history mutation."""

from __future__ import annotations

import argparse
import hashlib
import json
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, ValidationError, model_validator

ObjectId = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}([0-9a-f]{24})?$")]
ArgumentVector = Annotated[list[str], Field(min_length=1)]


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
        evidence=["validator status VALID", "plan SHA-256", "recovery ref still pending creation"],
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


def workflow_state_names() -> dict[WorkflowState, WorkflowStateDefinition]:
    """Return the canonical workflow-state map.

    Returns:
        Definitions keyed by workflow-state name.
    """
    return {definition.name: definition for definition in WORKFLOW_STATE_DEFINITIONS}


class RefBinding(BaseModel):
    """A ref name bound to one immutable commit OID."""

    ref: Annotated[str, Field(min_length=1)]
    oid: ObjectId


class CommandEvidence(BaseModel):
    """Complete output from one repository-required preflight command."""

    source: Annotated[str, Field(min_length=1)]
    argv: ArgumentVector
    exit_code: int
    stdout: str
    stderr: str


class PublicationEvidence(BaseModel):
    """Observable local evidence of upstream and remote-ref publication."""

    configured_upstream: str | None
    remote_refs_containing_old_tip: list[str]
    evidence_commands: Annotated[list[CommandEvidence], Field(min_length=1)]


class Disposition(StrEnum):
    """One accounted outcome for a replay candidate."""

    RETAIN = "RETAIN"
    ADAPT = "ADAPT"
    MANUAL_MERGE = "MANUAL_MERGE"
    REDUNDANT_DROP = "REDUNDANT_DROP"
    PRESERVE_EMPTY = "PRESERVE_EMPTY"


class Candidate(BaseModel):
    """One ordered replay candidate and its intended outcome."""

    oid: ObjectId
    parents: list[ObjectId]
    paths: Annotated[list[str], Field(min_length=1)]
    intent: Annotated[str, Field(min_length=1)]
    evidence: Annotated[list[str], Field(min_length=1)]
    disposition: Disposition
    verification_commands: Annotated[list[ArgumentVector], Field(min_length=1)]
    expected_conflict_paths: list[str]
    equivalence_evidence: list[str]
    drop_approval_decision_id: str | None = None


class PathImpact(BaseModel):
    """One affected path and every candidate that touches it."""

    path: Annotated[str, Field(min_length=1)]
    candidate_oids: Annotated[list[ObjectId], Field(min_length=1)]
    target_interaction: Annotated[str, Field(min_length=1)]
    dependencies: list[str]
    evidence: Annotated[list[str], Field(min_length=1)]
    verification_commands: Annotated[list[ArgumentVector], Field(min_length=1)]


class UserDecision(BaseModel):
    """One explicit user decision required by a destructive plan choice."""

    decision_id: Annotated[str, Field(min_length=1)]
    question: Annotated[str, Field(min_length=1)]
    approved: bool


class MergePolicy(StrEnum):
    """How the plan treats merge topology."""

    LINEAR_NO_MERGES = "LINEAR_NO_MERGES"
    PRESERVE_TOPOLOGY = "PRESERVE_TOPOLOGY"
    APPROVED_FLATTEN = "APPROVED_FLATTEN"


class RebasePlan(BaseModel):
    """Machine-validatable gate artifact for one local rebase."""

    schema_version: Literal[1]
    plan_id: Annotated[str, StringConstraints(pattern=r"^[a-z0-9][a-z0-9-]*$")]
    branch: RefBinding
    target: RefBinding
    merge_base_oid: ObjectId
    execution_worktree: Annotated[str, Field(min_length=1)]
    worktree_authorized: bool
    status_porcelain: str
    active_operations: list[str]
    repository_instruction_sources: Annotated[list[str], Field(min_length=1)]
    repository_preflights: list[CommandEvidence]
    publication: PublicationEvidence
    candidates: Annotated[list[Candidate], Field(min_length=1)]
    affected_paths: Annotated[list[PathImpact], Field(min_length=1)]
    merge_policy: MergePolicy
    clean_cherry_pick_policy: Literal["SURFACE"]
    becomes_empty_policy: Literal["STOP"]
    recovery_ref: Annotated[str, StringConstraints(pattern=r"^refs/heads/rebase-backup/[a-z0-9][a-z0-9-]*$")]
    repository_checks: Annotated[list[ArgumentVector], Field(min_length=1)]
    unknowns: list[str]
    user_decisions: list[UserDecision]

    @property
    def ready_state(self) -> WorkflowState:
        """Return the only state a valid plan can reach.

        Returns:
            `READY_TO_REBASE` after model validation succeeds.
        """
        return WorkflowState.READY_TO_REBASE

    @model_validator(mode="after")
    def validate_gate_invariants(self) -> RebasePlan:
        """Reject every plan that cannot safely cross the pre-action gate.

        Returns:
            The complete plan.

        Raises:
            ValueError: If any exact-cover, evidence, decision, or state invariant fails.
        """
        self._validate_repository_state()
        approved_decisions = self._validate_decisions_and_preflights()
        self._validate_exact_cover()
        self._validate_dispositions(approved_decisions)
        self._validate_merge_policy(approved_decisions)
        return self

    def _validate_repository_state(self) -> None:
        """Require distinct refs and a clean, authorized execution state."""
        if self.branch.ref == self.target.ref:
            raise ValueError("branch and target ref names must differ")
        if self.branch.oid == self.target.oid:
            raise ValueError("equal branch and target OIDs are a NO_CHANGE state, not a rebase plan")
        if not self.worktree_authorized:
            raise ValueError("execution worktree is not authorized")
        if self.status_porcelain:
            raise ValueError("execution worktree is not clean")
        if self.active_operations:
            raise ValueError("another Git operation is active")
        if self.unknowns:
            raise ValueError("plan has unresolved unknowns")

    def _validate_decisions_and_preflights(self) -> set[str]:
        """Require successful evidence and collect approved decision IDs.

        Returns:
            Every approved decision ID in the plan.
        """
        failed_commands = [
            evidence.argv
            for evidence in (*self.repository_preflights, *self.publication.evidence_commands)
            if evidence.exit_code != 0
        ]
        if failed_commands:
            raise ValueError(f"preflight evidence contains failed commands: {failed_commands}")
        if any(not decision.approved for decision in self.user_decisions):
            raise ValueError("plan contains an unapproved user decision")
        return {decision.decision_id for decision in self.user_decisions if decision.approved}

    def _validate_exact_cover(self) -> None:
        """Require unique candidates and exact candidate-to-path membership."""
        candidate_by_oid = {candidate.oid: candidate for candidate in self.candidates}
        if len(candidate_by_oid) != len(self.candidates):
            raise ValueError("candidate OIDs must be unique")
        impact_by_path = {impact.path: impact for impact in self.affected_paths}
        if len(impact_by_path) != len(self.affected_paths):
            raise ValueError("affected paths must be unique")

        candidate_paths = {path for candidate in self.candidates for path in candidate.paths}
        if candidate_paths != set(impact_by_path):
            raise ValueError("affected paths must exactly cover every candidate path")
        for path, impact in impact_by_path.items():
            expected_oids = {candidate.oid for candidate in self.candidates if path in candidate.paths}
            if set(impact.candidate_oids) != expected_oids:
                raise ValueError(f"candidate membership is incomplete for affected path: {path}")
            if any(oid not in candidate_by_oid for oid in impact.candidate_oids):
                raise ValueError(f"affected path names an unknown candidate: {path}")

    def _validate_dispositions(self, approved_decisions: set[str]) -> None:
        """Require evidence or approval for each redundant-drop disposition."""
        for candidate in self.candidates:
            if candidate.disposition is not Disposition.REDUNDANT_DROP:
                continue
            approved_drop = candidate.drop_approval_decision_id in approved_decisions
            if not candidate.equivalence_evidence and not approved_drop:
                raise ValueError(f"redundant drop lacks equivalence evidence or approval: {candidate.oid}")

    def _validate_merge_policy(self, approved_decisions: set[str]) -> None:
        """Require a topology policy compatible with the candidate graph."""
        has_merge = any(len(candidate.parents) > 1 for candidate in self.candidates)
        if has_merge and self.merge_policy is MergePolicy.LINEAR_NO_MERGES:
            raise ValueError("merge candidates require preserve-topology or approved-flatten policy")
        if self.merge_policy is MergePolicy.APPROVED_FLATTEN and "flatten-topology" not in approved_decisions:
            raise ValueError("approved-flatten policy requires the flatten-topology decision")


def create_parser() -> argparse.ArgumentParser:
    """Create the plan-validator CLI parser.

    Returns:
        Parser with validate, schema, and states commands.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate_parser = subparsers.add_parser("validate", help="Validate one JSON plan artifact.")
    validate_parser.add_argument("plan", type=Path)
    subparsers.add_parser("schema", help="Print the complete JSON Schema for a plan artifact.")
    subparsers.add_parser("states", help="Print the canonical workflow-state contract.")
    return parser


def emit_json(value: object) -> None:
    """Emit compact JSON for the agent-only consumer.

    Args:
        value: JSON-serializable output value.
    """
    print(json.dumps(value, separators=(",", ":"), sort_keys=True))


def validate_plan(path: Path) -> int:
    """Validate one plan file and emit a structured result.

    Args:
        path: JSON plan artifact.

    Returns:
        Zero for a valid plan, one for invalid JSON/model data, or two for I/O failure.
    """
    try:
        raw = path.read_bytes()
        plan = RebasePlan.model_validate_json(raw)
    except ValidationError as error:
        emit_json({
            "errors": json.loads(error.json(include_url=False)),
            "state": WorkflowState.PLAN_INVALID,
            "status": "INVALID",
        })
        return 1
    except OSError as error:
        emit_json({"error": str(error), "state": WorkflowState.PLAN_INVALID, "status": "ERROR"})
        return 2

    emit_json({
        "plan_id": plan.plan_id,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "state": plan.ready_state,
        "status": "VALID",
    })
    return 0


def main() -> int:
    """Run the selected validator operation.

    Returns:
        Command exit code.
    """
    args = create_parser().parse_args()
    if args.command == "validate":
        return validate_plan(args.plan)
    if args.command == "schema":
        emit_json(RebasePlan.model_json_schema())
        return 0
    emit_json([definition.model_dump(mode="json") for definition in WORKFLOW_STATE_DEFINITIONS])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

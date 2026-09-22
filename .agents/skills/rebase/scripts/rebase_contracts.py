"""Validated plan contracts for one managed local rebase."""

from __future__ import annotations

import hashlib
import re
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, model_validator

from rebase_evidence import CommandEvidence, RepositoryStateEvidence
from rebase_models import (
    ApprovalOperation,
    BecomesEmptyOption,
    CaptureId,
    ExecutionMode,
    ExternalApprovalReceipt,
    MergePolicy,
    ObjectId,
    PlanSha256,
)
from rebase_states import WorkflowState

ArgumentVector = Annotated[list[str], Field(min_length=1)]


class RefBinding(BaseModel):
    """A ref name bound to one immutable commit OID."""

    ref: Annotated[str, Field(min_length=1)]
    oid: ObjectId


class PublicationEvidence(BaseModel):
    """Observable local evidence of upstream and remote-ref publication."""

    configured_upstream: str | None
    remote_refs_containing_old_tip: list[str]
    evidence_commands: Annotated[list[CommandEvidence], Field(min_length=1)]


class InstructionSourceObservation(BaseModel):
    """One repository-instruction candidate and whether it exists."""

    path: Annotated[str, Field(min_length=1)]
    present: bool
    content: str | None = None
    sha256: PlanSha256 | None = None


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
    paths: list[str]
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
    operation: ApprovalOperation


class RebasePlan(BaseModel):
    """Machine-validatable gate artifact for one local rebase."""

    schema_version: Literal[1]
    plan_id: Annotated[str, StringConstraints(pattern=r"^[a-z0-9][a-z0-9-]*$")]
    capture_id: CaptureId | None = None
    capture_sha256: PlanSha256 | None = None
    branch: RefBinding
    target: RefBinding
    merge_base_oid: ObjectId
    execution_worktree: Annotated[str, Field(min_length=1)]
    execution_mode: ExecutionMode
    worktree_authorized: bool
    status_porcelain: str
    active_operations: list[str]
    repository_state: RepositoryStateEvidence
    repository_instruction_search: Annotated[list[InstructionSourceObservation], Field(min_length=1)]
    repository_instruction_sources: list[str]
    repository_preflights: list[CommandEvidence]
    required_preflights: list[ArgumentVector] = Field(default_factory=list)
    publication: PublicationEvidence
    replay_inventory: CommandEvidence
    candidates: Annotated[list[Candidate], Field(min_length=1)]
    affected_paths: list[PathImpact]
    merge_policy: MergePolicy
    clean_cherry_pick_policy: Literal["SURFACE"]
    becomes_empty_policy: Literal["STOP"]
    becomes_empty_option: BecomesEmptyOption
    rebase_help: CommandEvidence
    recovery_ref: Annotated[str, StringConstraints(pattern=r"^refs/heads/rebase-backup/[a-z0-9][a-z0-9-]*$")]
    recovery_verification: CommandEvidence
    repository_checks: Annotated[list[ArgumentVector], Field(min_length=1)]
    unknowns: list[str]
    user_decisions: list[UserDecision]
    approval_receipts: list[ExternalApprovalReceipt] = Field(default_factory=list)

    @property
    def ready_state(self) -> WorkflowState:
        """Return the only state a valid plan can reach."""
        return WorkflowState.READY_TO_REBASE

    @model_validator(mode="after")
    def validate_gate_invariants(self) -> RebasePlan:
        """Reject every plan that cannot safely cross the pre-action gate.

        Returns:
            Fully validated plan.
        """
        self.validate_repository_state()
        self.validate_instruction_discovery()
        approved_decisions = self.validate_decisions_and_preflights()
        self.validate_replay_inventory()
        self.validate_recovery()
        self.validate_rebase_capabilities()
        self.validate_exact_cover()
        self.validate_dispositions(approved_decisions)
        self.validate_merge_policy(approved_decisions)
        return self

    def validate_repository_state(self) -> None:
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
        self.repository_state.validate_bindings(
            branch_ref=self.branch.ref,
            branch_oid=self.branch.oid,
            target_ref=self.target.ref,
            target_oid=self.target.oid,
            merge_base_oid=self.merge_base_oid,
            execution_worktree=self.execution_worktree,
            status_porcelain=self.status_porcelain,
            active_operations=self.active_operations,
            configured_upstream=self.publication.configured_upstream,
            execution_mode=self.execution_mode,
        )

    def validate_instruction_discovery(self) -> None:
        """Require instruction observations to bind exact loaded sources."""
        searched_paths = [observation.path for observation in self.repository_instruction_search]
        if len(set(searched_paths)) != len(searched_paths):
            raise ValueError("repository instruction search paths must be unique")
        observed_sources = [
            observation.path for observation in self.repository_instruction_search if observation.present
        ]
        if observed_sources != self.repository_instruction_sources:
            raise ValueError("repository instruction sources do not match instruction-search evidence")
        for observation in self.repository_instruction_search:
            if observation.present:
                if observation.content is None or observation.sha256 is None:
                    raise ValueError("present repository instructions require content and SHA-256")
                if hashlib.sha256(observation.content.encode()).hexdigest() != observation.sha256:
                    raise ValueError("repository instruction SHA-256 does not match captured content")
            elif observation.content is not None or observation.sha256 is not None:
                raise ValueError("absent repository instructions cannot carry content or SHA-256")

    def validate_decisions_and_preflights(self) -> dict[str, ApprovalOperation]:
        """Require successful evidence and collect approved decision IDs.

        Returns:
            Approved operation keyed by decision ID.
        """
        failed_commands = [
            evidence.argv
            for evidence in (*self.repository_preflights, *self.publication.evidence_commands)
            if evidence.exit_code != 0
        ]
        if failed_commands:
            raise ValueError(f"preflight evidence contains failed commands: {failed_commands}")
        if [evidence.argv for evidence in self.repository_preflights] != self.required_preflights:
            raise ValueError("repository preflight evidence does not match required argv vectors")
        expected_remote_argv = [
            "git",
            "for-each-ref",
            "--format=%(refname)",
            "--contains",
            self.branch.oid,
            "refs/remotes",
        ]
        remote_evidence = [
            evidence for evidence in self.publication.evidence_commands if evidence.argv == expected_remote_argv
        ]
        if len(remote_evidence) != 1:
            raise ValueError("publication evidence must contain one remote-containment command")
        observed_remote_refs = [line for line in remote_evidence[0].stdout.splitlines() if line]
        if observed_remote_refs != self.publication.remote_refs_containing_old_tip:
            raise ValueError("remote-containment evidence does not match recorded remote refs")
        approved = {receipt.decision_id: receipt.operation for receipt in self.approval_receipts}
        if any(approved.get(decision.decision_id) is not decision.operation for decision in self.user_decisions):
            raise ValueError("plan decision lacks an external approval receipt")
        return approved

    def has_publication_approval(self) -> bool:
        """Return false for publication until a harness-owned gate exists."""
        return not (self.publication.configured_upstream or self.publication.remote_refs_containing_old_tip)

    def validate_replay_inventory(self) -> None:
        """Require captured graph evidence to exactly match candidates."""
        expected = [
            "git",
            "rev-list",
            "--reverse",
            "--topo-order",
            "--parents",
            f"{self.target.oid}..{self.branch.oid}",
        ]
        if self.replay_inventory.argv != expected or self.replay_inventory.exit_code != 0:
            raise ValueError("replay inventory command does not bind the planned immutable OIDs")
        observed = [line.split() for line in self.replay_inventory.stdout.splitlines() if line.strip()]
        planned = [[candidate.oid, *candidate.parents] for candidate in self.candidates]
        if observed != planned:
            raise ValueError("planned candidates do not exactly cover the captured replay inventory")

    def validate_recovery(self) -> None:
        """Require the recovery ref to resolve to the captured old tip."""
        expected = ["git", "rev-parse", "--verify", f"{self.recovery_ref}^{{commit}}"]
        if self.recovery_verification.argv != expected or self.recovery_verification.exit_code != 0:
            raise ValueError("recovery ref verification failed")
        if self.recovery_verification.stdout.strip() != self.branch.oid:
            raise ValueError("recovery ref does not resolve to the captured old tip")

    def validate_rebase_capabilities(self) -> None:
        """Require selected replay options in captured installed-Git help."""
        if self.rebase_help.argv != ["git", "rebase", "-h"]:
            raise ValueError("rebase capability evidence must come from git rebase -h")
        output = f"{self.rebase_help.stdout}\n{self.rebase_help.stderr}"
        if re.search(rf"--empty[^\n]*\b{re.escape(self.becomes_empty_option.value)}\b", output) is None:
            raise ValueError("selected becomes-empty option is absent from installed Git help")
        if re.search(r"--(?:\[no-\])?reapply-cherry-picks", output) is None:
            raise ValueError("installed Git help lacks --reapply-cherry-picks")
        supports_merges = re.search(r"--(?:\[no-\])?rebase-merges", output) is not None
        if self.merge_policy is MergePolicy.PRESERVE_TOPOLOGY and not supports_merges:
            raise ValueError("installed Git help lacks --rebase-merges")

    def validate_exact_cover(self) -> None:
        """Require unique candidates and exact candidate-to-path membership."""
        candidates = {candidate.oid: candidate for candidate in self.candidates}
        if len(candidates) != len(self.candidates):
            raise ValueError("candidate OIDs must be unique")
        impacts = {impact.path: impact for impact in self.affected_paths}
        if len(impacts) != len(self.affected_paths):
            raise ValueError("affected paths must be unique")
        for candidate in self.candidates:
            if (not candidate.paths) != (candidate.disposition is Disposition.PRESERVE_EMPTY):
                raise ValueError("zero-path candidates require PRESERVE_EMPTY and PRESERVE_EMPTY requires zero paths")
        candidate_paths = {path for candidate in self.candidates for path in candidate.paths}
        if candidate_paths != set(impacts):
            raise ValueError("affected paths must exactly cover every candidate path")
        for path, impact in impacts.items():
            expected = {candidate.oid for candidate in self.candidates if path in candidate.paths}
            if set(impact.candidate_oids) != expected:
                raise ValueError(f"candidate membership is incomplete for affected path: {path}")
            if any(oid not in candidates for oid in impact.candidate_oids):
                raise ValueError(f"affected path names an unknown candidate: {path}")

    def validate_dispositions(self, approved: dict[str, ApprovalOperation]) -> None:
        """Require evidence or approval for each redundant drop."""
        for candidate in self.candidates:
            if candidate.disposition is Disposition.REDUNDANT_DROP:
                approved_drop = approved.get(candidate.drop_approval_decision_id) is ApprovalOperation.REDUNDANT_DROP
                if not candidate.equivalence_evidence and not approved_drop:
                    raise ValueError(f"redundant drop lacks equivalence evidence or approval: {candidate.oid}")

    def validate_merge_policy(self, approved: dict[str, ApprovalOperation]) -> None:
        """Require a topology policy compatible with the candidate graph."""
        if (
            any(len(candidate.parents) > 1 for candidate in self.candidates)
            and self.merge_policy is MergePolicy.LINEAR_NO_MERGES
        ):
            raise ValueError("merge candidates require preserve-topology or approved-flatten policy")
        if (
            self.merge_policy is MergePolicy.APPROVED_FLATTEN
            and approved.get("flatten-topology") is not ApprovalOperation.FLATTEN_TOPOLOGY
        ):
            raise ValueError("approved-flatten policy requires the flatten-topology decision")

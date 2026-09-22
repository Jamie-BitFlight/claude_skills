"""Semantic finalization and recovery creation for managed rebase captures."""

from __future__ import annotations

import hashlib
import stat
from pathlib import Path

from rebase_contracts import Candidate, PathImpact, RebasePlan, UserDecision
from rebase_evidence import CommandEvidence
from rebase_managed import MANAGED_ID_PATTERN, ManagedCapture, command_evidence, managed_root
from rebase_models import ExternalApprovalReceipt, FinalizeSemantics
from rebase_prepare import run_command
from rebase_responses import PlanBuildResult, WorkflowTerminal
from rebase_states import WorkflowState


def load_capture(repository: Path, capture_id: str) -> tuple[ManagedCapture, str]:
    """Load one managed capture by ID and return its content digest.

    Returns:
        Validated capture and SHA-256.
    """
    if MANAGED_ID_PATTERN.fullmatch(capture_id) is None:
        raise ValueError("capture ID is invalid")
    path = managed_root(repository) / "captures" / f"{capture_id}.json"
    payload = path.read_bytes()
    capture = ManagedCapture.model_validate_json(payload)
    if capture.capture_id != capture_id:
        raise ValueError("managed capture ID does not match its path")
    return capture, hashlib.sha256(payload).hexdigest()


def load_external_receipts(
    repository: Path, capture: ManagedCapture, capture_sha256: str, receipt_paths: list[Path]
) -> list[ExternalApprovalReceipt]:
    """Load capture-bound receipt data from outside repository-managed state.

    Returns:
        Validated receipts bound to the capture.
    """
    repository_root = Path(capture.repository_root).resolve()
    git_state_root = managed_root(repository).resolve()
    receipts: list[ExternalApprovalReceipt] = []
    for path in receipt_paths:
        resolved = path.resolve()
        if resolved == repository_root or repository_root in resolved.parents:
            raise ValueError("approval receipt must originate outside the repository")
        if resolved == git_state_root or git_state_root in resolved.parents:
            raise ValueError("Git-dir files are not external approval authority")
        mode = resolved.stat().st_mode
        if mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH):
            raise ValueError("approval receipt must be supplied read-only")
        receipt = ExternalApprovalReceipt.model_validate_json(resolved.read_bytes())
        expected = (
            receipt.capture_id == capture.capture_id
            and receipt.capture_sha256 == capture_sha256
            and Path(receipt.repository_root).resolve() == repository_root
            and receipt.branch_ref == capture.branch_ref
            and receipt.old_tip_oid == capture.branch_oid
            and receipt.target_ref == capture.target_ref
            and receipt.target_oid == capture.target_oid
        )
        if not expected:
            raise ValueError("approval receipt does not bind the managed capture")
        receipts.append(receipt)
    return receipts


def validate_semantic_cover(capture: ManagedCapture, semantics: FinalizeSemantics) -> None:
    """Require semantic judgments to exactly cover captured evidence."""
    captured_oids = [candidate.oid for candidate in capture.candidates]
    semantic_oids = [candidate.oid for candidate in semantics.candidates]
    if len(set(semantic_oids)) != len(semantic_oids) or set(semantic_oids) != set(captured_oids):
        raise ValueError("candidate semantics must exactly cover the managed capture")
    captured_paths = {path.path: path for path in capture.affected_paths}
    semantic_paths = [path.path for path in semantics.affected_paths]
    if len(set(semantic_paths)) != len(semantic_paths) or set(semantic_paths) != set(captured_paths):
        raise ValueError("path semantics must exactly cover the managed capture")
    captured_candidates = {candidate.oid: candidate for candidate in capture.candidates}
    for semantic in semantics.candidates:
        captured = captured_candidates[semantic.oid]
        if any(evidence_id not in captured.evidence_ids for evidence_id in semantic.evidence):
            raise ValueError(f"candidate semantics cites uncaptured evidence: {semantic.oid}")
        if any(evidence_id not in captured.evidence_ids for evidence_id in semantic.equivalence_evidence):
            raise ValueError(f"candidate equivalence cites uncaptured evidence: {semantic.oid}")
    for semantic in semantics.affected_paths:
        if any(evidence_id not in captured_paths[semantic.path].evidence_ids for evidence_id in semantic.evidence):
            raise ValueError(f"path semantics cites uncaptured evidence: {semantic.path}")
    present_sources = {
        (observation.path, observation.sha256)
        for observation in capture.repository_instruction_search
        if observation.present
    }
    acknowledged_sources = {
        (acknowledgement.path, acknowledgement.source_sha256)
        for acknowledgement in semantics.instruction_acknowledgements
    }
    if acknowledged_sources != present_sources or len(acknowledged_sources) != len(
        semantics.instruction_acknowledgements
    ):
        raise ValueError("instruction acknowledgements must exactly cover present captured sources")
    if semantics.unknowns:
        raise ValueError("semantic finalization has unresolved unknowns")


def execute_repository_preflights(
    repository: Path, semantics: FinalizeSemantics
) -> tuple[list[CommandEvidence], list[list[str]]]:
    """Run acknowledged repository preflights and retain complete evidence.

    Returns:
        Command evidence and the bound argument vectors.
    """
    argv_vectors = [
        argv
        for acknowledgement in semantics.instruction_acknowledgements
        for argv in acknowledgement.required_preflight_argv
    ]
    evidence: list[CommandEvidence] = []
    for argv in argv_vectors:
        result = run_command(repository, argv)
        evidence.append(
            CommandEvidence(
                source="managed-finalize-preflight",
                argv=result.argv,
                exit_code=result.exit_code,
                stdout=result.stdout,
                stderr=result.stderr,
            )
        )
        if result.exit_code != 0:
            raise ValueError(f"repository preflight failed: {argv}")
    return evidence, argv_vectors


def required_receipts(
    capture: ManagedCapture, semantics: FinalizeSemantics, receipts: list[ExternalApprovalReceipt]
) -> list[str]:
    """Return every decision not backed by usable external authority."""
    missing = ["published-history"] if capture.publication_requires_approval else []
    missing.extend(
        decision.decision_id
        for decision in semantics.decisions
        if not any(
            receipt.decision_id == decision.decision_id and receipt.operation is decision.operation
            for receipt in receipts
        )
    )
    return missing


def create_recovery(repository: Path, capture: ManagedCapture, plan_id: str) -> tuple[str, CommandEvidence]:
    """Create and verify recovery after every authority gate passes.

    Returns:
        Recovery ref and verification evidence.
    """
    recovery_ref = f"refs/heads/rebase-backup/{plan_id}"
    creation = command_evidence(repository, "branch", recovery_ref.removeprefix("refs/heads/"), capture.branch_oid)
    if creation.exit_code != 0:
        raise ValueError(f"recovery ref creation failed: {creation.stderr}")
    verification = command_evidence(repository, "rev-parse", "--verify", f"{recovery_ref}^{{commit}}")
    if verification.exit_code != 0 or verification.stdout.strip() != capture.branch_oid:
        raise ValueError("recovery ref verification failed")
    return recovery_ref, verification


def delete_verified_recovery(repository: Path, recovery_ref: str, old_tip_oid: str) -> None:
    """Delete only the recovery ref still bound to the captured old tip."""
    observed = command_evidence(repository, "rev-parse", "--verify", f"{recovery_ref}^{{commit}}")
    if observed.exit_code != 0 or observed.stdout.strip() != old_tip_oid:
        raise ValueError("recovery ref changed before cleanup")
    deleted = command_evidence(repository, "update-ref", "-d", recovery_ref, old_tip_oid)
    if deleted.exit_code != 0:
        raise ValueError(f"recovery ref cleanup failed: {deleted.stderr}")


def project_candidates(capture: ManagedCapture, semantics: FinalizeSemantics) -> list[Candidate]:
    """Combine immutable candidate evidence with semantic judgments.

    Returns:
        Typed plan candidates in semantic-input order.
    """
    captured_by_oid = {candidate.oid: candidate for candidate in capture.candidates}
    return [
        Candidate(
            **semantic.model_dump(mode="json"),
            parents=captured_by_oid[semantic.oid].parents,
            paths=captured_by_oid[semantic.oid].paths,
        )
        for semantic in semantics.candidates
    ]


def project_paths(capture: ManagedCapture, semantics: FinalizeSemantics) -> list[PathImpact]:
    """Combine immutable path membership with semantic judgments.

    Returns:
        Typed affected-path impacts in semantic-input order.
    """
    captured_by_path = {path.path: path for path in capture.affected_paths}
    return [
        PathImpact(**semantic.model_dump(mode="json"), candidate_oids=captured_by_path[semantic.path].candidate_oids)
        for semantic in semantics.affected_paths
    ]


def project_decisions(semantics: FinalizeSemantics) -> list[UserDecision]:
    """Project semantic decisions into the persisted plan contract.

    Returns:
        Typed user decisions in semantic-input order.
    """
    return [UserDecision.model_validate(decision.model_dump(mode="json")) for decision in semantics.decisions]


def project_plan(
    capture: ManagedCapture,
    capture_sha256: str,
    semantics: FinalizeSemantics,
    receipts: list[ExternalApprovalReceipt],
    repository_preflights: list[CommandEvidence],
    required_preflights: list[list[str]],
    recovery_ref: str,
    recovery_verification: CommandEvidence,
) -> RebasePlan:
    """Project a validated capture into the persisted plan contract.

    Returns:
        Fully validated rebase plan.
    """
    return RebasePlan(
        schema_version=1,
        plan_id=capture.capture_id,
        capture_id=capture.capture_id,
        capture_sha256=capture_sha256,
        branch={"ref": capture.branch_ref, "oid": capture.branch_oid},
        target={"ref": capture.target_ref, "oid": capture.target_oid},
        merge_base_oid=capture.merge_base_oid,
        execution_worktree=capture.execution_worktree,
        execution_mode=capture.execution_mode,
        worktree_authorized=True,
        status_porcelain=capture.status_porcelain,
        active_operations=capture.active_operations,
        repository_state=capture.repository_state,
        repository_instruction_search=[source.model_dump() for source in capture.repository_instruction_search],
        repository_instruction_sources=capture.repository_instruction_sources,
        repository_preflights=repository_preflights,
        required_preflights=required_preflights,
        publication=capture.publication.model_dump(),
        replay_inventory=capture.replay_inventory,
        candidates=project_candidates(capture, semantics),
        affected_paths=project_paths(capture, semantics),
        merge_policy=semantics.merge_policy,
        clean_cherry_pick_policy="SURFACE",
        becomes_empty_policy="STOP",
        becomes_empty_option=capture.becomes_empty_option,
        rebase_help=capture.rebase_help,
        recovery_ref=recovery_ref,
        recovery_verification=recovery_verification,
        repository_checks=semantics.repository_checks,
        unknowns=semantics.unknowns,
        user_decisions=project_decisions(semantics),
        approval_receipts=receipts,
    )


def terminal_result(state: WorkflowState, status: str, **details: object) -> PlanBuildResult:
    """Build one typed terminal plan-construction result.

    Returns:
        Terminal build result with exit code one.
    """
    terminal = WorkflowTerminal.model_validate({"state": state, "status": status, **details})
    return PlanBuildResult(terminal=terminal, exit_code=1)


def build_managed_plan(
    repository: Path, capture_id: str, semantics: FinalizeSemantics, receipt_paths: list[Path]
) -> PlanBuildResult:
    """Merge managed evidence with semantics after authority checks.

    Returns:
        Typed plan or terminal construction result.
    """
    try:
        capture, capture_sha256 = load_capture(repository, capture_id)
        validate_semantic_cover(capture, semantics)
        receipts = load_external_receipts(repository, capture, capture_sha256, receipt_paths)
    except (OSError, ValueError) as error:
        return terminal_result(WorkflowState.PLAN_INVALID, "INVALID", error=str(error))
    missing_receipts = required_receipts(capture, semantics, receipts)
    if missing_receipts:
        return terminal_result(
            WorkflowState.NEEDS_USER_DECISION, "DECISION_REQUIRED", missing_approvals=missing_receipts
        )
    try:
        repository_preflights, required_preflights = execute_repository_preflights(repository, semantics)
    except ValueError as error:
        return terminal_result(WorkflowState.BLOCKED_PREFLIGHT_FAILED, "BLOCKED", error=str(error))
    try:
        recovery_ref, recovery_verification = create_recovery(repository, capture, capture.capture_id)
    except ValueError as error:
        return terminal_result(WorkflowState.BLOCKED_GIT_STATE, "BLOCKED", error=str(error))
    try:
        plan = project_plan(
            capture,
            capture_sha256,
            semantics,
            receipts,
            repository_preflights,
            required_preflights,
            recovery_ref,
            recovery_verification,
        )
    except ValueError as error:
        try:
            delete_verified_recovery(repository, recovery_ref, capture.branch_oid)
        except ValueError as cleanup_error:
            return terminal_result(WorkflowState.BLOCKED_GIT_STATE, "BLOCKED", error=str(cleanup_error))
        result = terminal_result(WorkflowState.PLAN_INVALID, "INVALID", error=str(error))
    else:
        result = PlanBuildResult(plan=plan, exit_code=0)
    return result

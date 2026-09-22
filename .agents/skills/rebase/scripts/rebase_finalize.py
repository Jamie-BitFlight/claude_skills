"""Semantic finalization and recovery creation for managed rebase captures."""

from __future__ import annotations

import hashlib
import stat
from pathlib import Path

from rebase_evidence import CommandEvidence
from rebase_managed import MANAGED_ID_PATTERN, ManagedCapture, command_evidence, managed_root
from rebase_models import ExternalApprovalReceipt, FinalizeSemantics
from rebase_prepare import run_command
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


def build_managed_plan(
    repository: Path, capture_id: str, semantics: FinalizeSemantics, receipt_paths: list[Path]
) -> tuple[dict[str, object] | None, dict[str, object], int]:
    """Merge managed evidence with semantics after authority checks.

    Returns:
        Plan data or terminal output and its exit code.
    """
    try:
        capture, capture_sha256 = load_capture(repository, capture_id)
        validate_semantic_cover(capture, semantics)
        receipts = load_external_receipts(repository, capture, capture_sha256, receipt_paths)
    except (OSError, ValueError) as error:
        return (
            None,
            {"error": str(error), "state": WorkflowState.PLAN_INVALID, "status": "INVALID", "terminal": True},
            1,
        )
    missing_receipts = required_receipts(capture, semantics, receipts)
    if missing_receipts:
        return (
            None,
            {
                "missing_approvals": missing_receipts,
                "state": WorkflowState.NEEDS_USER_DECISION,
                "status": "DECISION_REQUIRED",
                "terminal": True,
            },
            1,
        )
    try:
        repository_preflights, required_preflights = execute_repository_preflights(repository, semantics)
    except ValueError as error:
        return (
            None,
            {
                "error": str(error),
                "state": WorkflowState.BLOCKED_PREFLIGHT_FAILED,
                "status": "BLOCKED",
                "terminal": True,
            },
            1,
        )
    plan_id = capture.capture_id
    try:
        recovery_ref, recovery_verification = create_recovery(repository, capture, plan_id)
    except ValueError as error:
        return (
            None,
            {"error": str(error), "state": WorkflowState.BLOCKED_GIT_STATE, "status": "BLOCKED", "terminal": True},
            1,
        )
    captured_by_oid = {candidate.oid: candidate for candidate in capture.candidates}
    candidate_data = [
        {
            **semantic.model_dump(mode="json"),
            "parents": captured_by_oid[semantic.oid].parents,
            "paths": captured_by_oid[semantic.oid].paths,
        }
        for semantic in semantics.candidates
    ]
    path_data = [
        {
            **semantic.model_dump(mode="json"),
            "candidate_oids": next(
                path.candidate_oids for path in capture.affected_paths if path.path == semantic.path
            ),
        }
        for semantic in semantics.affected_paths
    ]
    plan: dict[str, object] = {
        "schema_version": 1,
        "plan_id": plan_id,
        "capture_id": capture.capture_id,
        "capture_sha256": capture_sha256,
        "branch": {"ref": capture.branch_ref, "oid": capture.branch_oid},
        "target": {"ref": capture.target_ref, "oid": capture.target_oid},
        "merge_base_oid": capture.merge_base_oid,
        "execution_worktree": capture.execution_worktree,
        "execution_mode": capture.execution_mode,
        "worktree_authorized": True,
        "status_porcelain": capture.status_porcelain,
        "active_operations": capture.active_operations,
        "repository_state": capture.repository_state.model_dump(mode="json"),
        "repository_instruction_search": [
            observation.model_dump(mode="json") for observation in capture.repository_instruction_search
        ],
        "repository_instruction_sources": capture.repository_instruction_sources,
        "repository_preflights": [evidence.model_dump(mode="json") for evidence in repository_preflights],
        "required_preflights": required_preflights,
        "publication": capture.publication.model_dump(mode="json"),
        "replay_inventory": capture.replay_inventory.model_dump(mode="json"),
        "candidates": candidate_data,
        "affected_paths": path_data,
        "merge_policy": semantics.merge_policy,
        "clean_cherry_pick_policy": "SURFACE",
        "becomes_empty_policy": "STOP",
        "becomes_empty_option": capture.becomes_empty_option,
        "rebase_help": capture.rebase_help.model_dump(mode="json"),
        "recovery_ref": recovery_ref,
        "recovery_verification": recovery_verification.model_dump(mode="json"),
        "repository_checks": semantics.repository_checks,
        "unknowns": semantics.unknowns,
        "user_decisions": [
            {"decision_id": decision.decision_id, "question": decision.question, "operation": decision.operation}
            for decision in semantics.decisions
        ],
        "approval_receipts": [receipt.model_dump(mode="json") for receipt in receipts],
    }
    return plan, {}, 0

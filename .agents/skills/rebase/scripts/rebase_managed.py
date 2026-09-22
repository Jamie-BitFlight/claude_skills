"""Managed Git-dir evidence capture and artifact storage for local rebases."""

from __future__ import annotations

import hashlib
import os
import re
import signal
import stat
import subprocess
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from rebase_evidence import CommandEvidence, PathMarkerEvidence, RefMarkerEvidence, RepositoryStateEvidence
from rebase_models import (
    BecomesEmptyOption,
    CapturedCandidate,
    CaptureId,
    ExecutionMode,
    ExternalApprovalReceipt,
    FinalizeSemantics,
    ObjectId,
)
from rebase_prepare import COMMAND_TIMEOUT_SECONDS, TERMINATION_GRACE_SECONDS, run_git
from rebase_states import WorkflowState

PLAN_SCRIPT = Path(__file__).with_name("rebase_plan.py")
MANAGED_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")


class PublicationEvidence(BaseModel):
    """Observable upstream and remote-containment evidence."""

    model_config = ConfigDict(frozen=True)

    configured_upstream: str | None
    remote_refs_containing_old_tip: list[str]
    evidence_commands: Annotated[list[CommandEvidence], Field(min_length=1)]


class InstructionSourceObservation(BaseModel):
    """One repository-instruction candidate and its presence."""

    model_config = ConfigDict(frozen=True)

    path: Annotated[str, Field(min_length=1)]
    present: bool


class ManagedCapture(BaseModel):
    """Immutable evidence owned by the capture operation."""

    model_config = ConfigDict(frozen=True)

    schema_version: int = 1
    capture_id: CaptureId
    repository_root: Annotated[str, Field(min_length=1)]
    branch_ref: Annotated[str, Field(min_length=1)]
    branch_oid: ObjectId
    target_ref: Annotated[str, Field(min_length=1)]
    target_oid: ObjectId
    expected_target_oid: ObjectId | None
    merge_base_oid: ObjectId
    execution_worktree: Annotated[str, Field(min_length=1)]
    execution_mode: ExecutionMode
    status_porcelain: str
    active_operations: list[str]
    repository_state: RepositoryStateEvidence
    repository_instruction_search: Annotated[list[InstructionSourceObservation], Field(min_length=1)]
    repository_instruction_sources: list[str]
    publication: PublicationEvidence
    replay_inventory: CommandEvidence
    candidates: Annotated[list[CapturedCandidate], Field(min_length=1)]
    affected_paths: list[str]
    rebase_help: CommandEvidence
    becomes_empty_option: BecomesEmptyOption
    publication_requires_approval: bool


def command_evidence(repository: Path, *arguments: str) -> CommandEvidence:
    """Run Git and return complete managed evidence.

    Returns:
        Complete command evidence.
    """
    result = run_git(repository, *arguments)
    return CommandEvidence(
        source="managed-capture",
        argv=result.argv,
        exit_code=result.exit_code,
        stdout=result.stdout,
        stderr=result.stderr,
    )


def ref_terminal(evidence: CommandEvidence, ref: str) -> tuple[dict[str, object], int]:
    """Return the canonical invalid-ref terminal."""
    return (
        {
            "command": evidence.model_dump(mode="json"),
            "error": f"invalid local ref: {ref}",
            "state": WorkflowState.BLOCKED_INVALID_REF,
            "status": "BLOCKED",
            "terminal": True,
        },
        1,
    )


def normalize_local_ref(name: str) -> str:
    """Return an exact local branch ref."""
    return name if name.startswith("refs/heads/") else f"refs/heads/{name}"


def run_path_state(repository: Path, path: Path) -> CommandEvidence:
    """Run the maintained path-state operation with bounded process ownership.

    Returns:
        Complete path-state command evidence.
    """
    argv = ["uv", "run", "--script", str(PLAN_SCRIPT), "path-state", str(path)]
    process = subprocess.Popen(
        argv, cwd=repository, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True
    )
    try:
        stdout, stderr = process.communicate(timeout=COMMAND_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGTERM)
        else:
            process.terminate()
        try:
            process.wait(timeout=TERMINATION_GRACE_SECONDS)
        except subprocess.TimeoutExpired:
            if os.name == "posix":
                os.killpg(process.pid, signal.SIGKILL)
            else:
                process.kill()
        stdout, stderr = process.communicate()
    return CommandEvidence(
        source="managed-filesystem", argv=argv, exit_code=process.returncode, stdout=stdout, stderr=stderr
    )


def capture_path_marker(repository: Path, root: Path, name: str) -> PathMarkerEvidence:
    """Capture one Git operation-path lookup and observed presence.

    Returns:
        Bound path lookup and existence evidence.
    """
    command = command_evidence(repository, "rev-parse", "--git-path", name)
    observed = Path(command.stdout.strip())
    resolved = observed if observed.is_absolute() else root / observed
    existence = run_path_state(repository, resolved)
    return PathMarkerEvidence(command=command, existence=existence, present=resolved.exists())


def capture_ref_marker(repository: Path, name: str) -> RefMarkerEvidence:
    """Capture one optional Git operation ref.

    Returns:
        Bound ref lookup and presence evidence.
    """
    command = command_evidence(repository, "rev-parse", "--verify", "--quiet", name)
    return RefMarkerEvidence(command=command, present=command.exit_code == 0)


def managed_root(repository: Path) -> Path:
    """Resolve the worktree-local managed state root under Git metadata.

    Returns:
        Managed state root.
    """
    result = run_git(repository, "rev-parse", "--git-path", "rebase-skill")
    if result.exit_code != 0 or not result.stdout.strip():
        raise OSError(f"cannot resolve managed rebase state: {result.stderr}")
    path = Path(result.stdout.strip())
    return path if path.is_absolute() else repository / path


def resolve_managed_plan(repository: Path, identifier_or_path: str) -> Path:
    """Resolve a plan ID or prove that a supplied path is inside managed plan storage.

    Returns:
        Validated managed plan path.
    """
    plans_root = (managed_root(repository) / "plans").resolve()
    candidate = Path(identifier_or_path)
    if MANAGED_ID_PATTERN.fullmatch(identifier_or_path):
        return plans_root / f"{identifier_or_path}.json"
    resolved = (repository / candidate).resolve() if not candidate.is_absolute() else candidate.resolve()
    if resolved.parent != plans_root or resolved.suffix != ".json":
        raise ValueError("unmanaged plan path is outside Git-dir rebase-skill/plans")
    return resolved


def atomic_write(path: Path, payload: bytes) -> None:
    """Create one immutable managed artifact without replacing prior state."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def capture_instruction_sources(root: Path) -> tuple[list[InstructionSourceObservation], list[str]]:
    """Record the maintained repository instruction locations without loading skill internals.

    Returns:
        Searched locations and present instruction sources.
    """
    candidates = [root / "AGENTS.md", root / ".claude" / "CLAUDE.md"]
    observations = [InstructionSourceObservation(path=str(path), present=path.is_file()) for path in candidates]
    return observations, [observation.path for observation in observations if observation.present]


def detect_empty_option(help_evidence: CommandEvidence) -> BecomesEmptyOption:
    """Select the installed stop-on-empty spelling.

    Returns:
        Installed stop-on-empty option.
    """
    output = f"{help_evidence.stdout}\n{help_evidence.stderr}"
    empty_line = next((line for line in output.splitlines() if "--empty" in line), "")
    if "stop" in empty_line:
        return BecomesEmptyOption.STOP
    if "ask" in empty_line:
        return BecomesEmptyOption.ASK
    raise ValueError("installed Git help has no stop-on-empty spelling")


def capture_candidates(repository: Path, inventory: CommandEvidence) -> tuple[list[CapturedCandidate], list[str]]:
    """Derive immutable candidate graph and affected paths from managed Git evidence.

    Returns:
        Ordered candidates and unique affected paths.
    """
    candidates: list[CapturedCandidate] = []
    affected_paths: list[str] = []
    for line in inventory.stdout.splitlines():
        fields = line.split()
        if not fields:
            continue
        oid, *parents = fields
        path_evidence = command_evidence(
            repository, "diff-tree", "--root", "-m", "--no-commit-id", "--name-only", "-r", "-M", "-C", oid
        )
        if path_evidence.exit_code != 0:
            raise ValueError(f"candidate path capture failed: {oid}")
        paths = list(dict.fromkeys(path for path in path_evidence.stdout.splitlines() if path))
        affected_paths.extend(path for path in paths if path not in affected_paths)
        candidates.append(CapturedCandidate(oid=oid, parents=parents, paths=paths))
    if not candidates:
        raise ValueError("managed replay inventory contains no candidates")
    return candidates, affected_paths


def store_capture(repository: Path, capture: ManagedCapture) -> tuple[Path, str]:
    """Persist one immutable capture and return its path and digest.

    Returns:
        Managed path and content SHA-256.
    """
    payload = capture.model_dump_json().encode() + b"\n"
    digest = hashlib.sha256(payload).hexdigest()
    path = managed_root(repository) / "captures" / f"{capture.capture_id}.json"
    atomic_write(path, payload)
    return path, digest


def semantic_template(capture: ManagedCapture) -> dict[str, object]:
    """Return the only agent-authored fields accepted by finalization."""
    return {
        "candidates": [
            {
                "oid": candidate.oid,
                "intent": None,
                "evidence": [],
                "disposition": None,
                "verification_commands": [],
                "expected_conflict_paths": [],
                "equivalence_evidence": [],
                "drop_approval_decision_id": None,
            }
            for candidate in capture.candidates
        ],
        "affected_paths": [
            {"path": path, "target_interaction": None, "dependencies": [], "evidence": [], "verification_commands": []}
            for path in capture.affected_paths
        ],
        "merge_policy": None,
        "repository_checks": [],
        "unknowns": [],
        "decisions": [],
    }


def load_capture(repository: Path, capture_id: str) -> tuple[ManagedCapture, str]:
    """Load one managed capture by ID and return its content digest.

    Returns:
        Validated capture and content SHA-256.
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
    """Load approval receipts from outside repository and Git-managed state.

    Returns:
        Validated capture-bound receipts.
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
    """Require semantic judgments to exactly cover immutable candidates and paths."""
    captured_oids = [candidate.oid for candidate in capture.candidates]
    semantic_oids = [candidate.oid for candidate in semantics.candidates]
    if len(set(semantic_oids)) != len(semantic_oids) or set(semantic_oids) != set(captured_oids):
        raise ValueError("candidate semantics must exactly cover the managed capture")
    semantic_paths = [path.path for path in semantics.affected_paths]
    if len(set(semantic_paths)) != len(semantic_paths) or set(semantic_paths) != set(capture.affected_paths):
        raise ValueError("path semantics must exactly cover the managed capture")
    if semantics.unknowns:
        raise ValueError("semantic finalization has unresolved unknowns")


def required_receipts(
    capture: ManagedCapture, semantics: FinalizeSemantics, receipts: list[ExternalApprovalReceipt]
) -> list[str]:
    """Return every approval decision not backed by a matching external receipt."""
    missing: list[str] = []
    if capture.publication_requires_approval and not any(
        receipt.operation.value == "REBASE_PUBLISHED_HISTORY" for receipt in receipts
    ):
        missing.append("published-history")
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
    """Create and verify the managed recovery ref after every authority gate passes.

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
    """Merge managed evidence with semantic judgments after external authority checks.

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
            "candidate_oids": [candidate.oid for candidate in capture.candidates if semantic.path in candidate.paths],
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
        "repository_preflights": [],
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

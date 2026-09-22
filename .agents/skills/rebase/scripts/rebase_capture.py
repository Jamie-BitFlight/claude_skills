"""Ordered managed evidence capture for local rebases."""

from __future__ import annotations

import uuid
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from rebase_evidence import CommandEvidence, RepositoryStateEvidence, worktree_branch_owners
from rebase_managed import (
    ManagedCapture,
    PublicationEvidence,
    capture_candidates,
    capture_instruction_sources,
    capture_path_marker,
    capture_ref_marker,
    command_evidence,
    detect_empty_option,
    normalize_local_ref,
    ref_terminal,
    semantic_template,
    store_capture,
)
from rebase_models import CaptureRequest, ExecutionMode, ObjectId
from rebase_states import WorkflowState


class CaptureBindings(BaseModel):
    """Immutable ref and repository bindings established before broad preflight."""

    model_config = ConfigDict(frozen=True)

    root: Path
    root_evidence: CommandEvidence
    branch_ref: str
    branch_oid: ObjectId
    branch_ref_evidence: CommandEvidence
    branch_oid_evidence: CommandEvidence
    target_ref: str
    target_oid: ObjectId
    target_oid_evidence: CommandEvidence
    merge_base: CommandEvidence


class CapturePreflight(BaseModel):
    """Managed repository and publication evidence captured after ref binding."""

    model_config = ConfigDict(frozen=True)

    repository_state: RepositoryStateEvidence
    execution_mode: ExecutionMode
    active_operations: list[str]
    publication: PublicationEvidence


class CaptureStop(Exception):
    """Internal control flow for one canonical capture terminal."""

    def __init__(self, output: dict[str, object], exit_code: int = 1) -> None:
        """Bind terminal output to its process exit code."""
        super().__init__(str(output.get("state", "capture stopped")))
        self.output = output
        self.exit_code = exit_code


def stop_capture(state: WorkflowState, **details: object) -> None:
    """Raise one canonical terminal result."""
    raise CaptureStop({
        **details,
        "state": state,
        "status": "NO_CHANGE" if state is WorkflowState.NO_CHANGE else "BLOCKED",
        "terminal": True,
    })


def capture_bindings(repository: Path, request: CaptureRequest) -> CaptureBindings:
    """Bind repository and invocation refs before any broad preflight.

    Returns:
        Immutable root, ref, and merge-base evidence.
    """
    root_evidence = command_evidence(repository, "rev-parse", "--show-toplevel")
    if root_evidence.exit_code != 0:
        stop_capture(WorkflowState.BLOCKED_PREFLIGHT_FAILED, command=root_evidence.model_dump(mode="json"))
    root = Path(root_evidence.stdout.strip()).resolve()
    branch_ref = normalize_local_ref(request.branch)
    target_ref = request.target
    branch_ref_evidence = command_evidence(repository, "show-ref", "--verify", branch_ref)
    if branch_ref_evidence.exit_code != 0:
        output, exit_code = ref_terminal(branch_ref_evidence, branch_ref)
        raise CaptureStop(output, exit_code)
    branch_oid = branch_ref_evidence.stdout.split()[0]
    target_oid_evidence = command_evidence(repository, "rev-parse", "--verify", f"{target_ref}^{{commit}}")
    if target_oid_evidence.exit_code != 0:
        output, exit_code = ref_terminal(target_oid_evidence, target_ref)
        raise CaptureStop(output, exit_code)
    target_oid = target_oid_evidence.stdout.strip()
    if request.expected_target_oid is not None and request.expected_target_oid != target_oid:
        stop_capture(
            WorkflowState.REPLAN_REF_DRIFT,
            expected_target_oid=request.expected_target_oid,
            observed_target_oid=target_oid,
        )
    if branch_ref == target_ref:
        output, exit_code = ref_terminal(target_oid_evidence, target_ref)
        raise CaptureStop(output, exit_code)
    if branch_oid == target_oid:
        stop_capture(WorkflowState.NO_CHANGE, branch_oid=branch_oid, target_oid=target_oid)
    branch_oid_evidence = command_evidence(repository, "rev-parse", "--verify", f"{branch_ref}^{{commit}}")
    merge_base = command_evidence(repository, "merge-base", branch_ref, target_ref)
    if merge_base.exit_code != 0:
        state = (
            WorkflowState.BLOCKED_UNRELATED_HISTORIES
            if merge_base.exit_code == 1
            else WorkflowState.BLOCKED_PREFLIGHT_FAILED
        )
        stop_capture(state, command=merge_base.model_dump(mode="json"))
    return CaptureBindings(
        root=root,
        root_evidence=root_evidence,
        branch_ref=branch_ref,
        branch_oid=branch_oid,
        branch_ref_evidence=branch_ref_evidence,
        branch_oid_evidence=branch_oid_evidence,
        target_ref=target_ref,
        target_oid=target_oid,
        target_oid_evidence=target_oid_evidence,
        merge_base=merge_base,
    )


def capture_preflight(repository: Path, bindings: CaptureBindings) -> CapturePreflight:
    """Capture clean worktree, operation, ownership, and publication evidence.

    Returns:
        Complete repository state, execution mode, and publication evidence.
    """
    worktrees = command_evidence(repository, "worktree", "list", "--porcelain")
    status = command_evidence(repository, "status", "--porcelain=v1", "--untracked-files=all")
    current_branch = command_evidence(repository, "symbolic-ref", "--quiet", "--short", "HEAD")
    rebase_merge = capture_path_marker(repository, bindings.root, "rebase-merge")
    rebase_apply = capture_path_marker(repository, bindings.root, "rebase-apply")
    merge_head = capture_ref_marker(repository, "MERGE_HEAD")
    cherry_pick_head = capture_ref_marker(repository, "CHERRY_PICK_HEAD")
    upstream = command_evidence(repository, "for-each-ref", "--format=%(upstream)", bindings.branch_ref)
    required = (
        worktrees,
        status,
        current_branch,
        rebase_merge.command,
        rebase_merge.existence,
        rebase_apply.command,
        rebase_apply.existence,
        upstream,
    )
    if any(evidence.exit_code != 0 for evidence in required):
        stop_capture(WorkflowState.BLOCKED_PREFLIGHT_FAILED)
    active_operations = [
        name
        for name, present in (
            ("rebase-merge", rebase_merge.present),
            ("rebase-apply", rebase_apply.present),
            ("MERGE_HEAD", merge_head.present),
            ("CHERRY_PICK_HEAD", cherry_pick_head.present),
        )
        if present
    ]
    if status.stdout or active_operations:
        stop_capture(
            WorkflowState.BLOCKED_GIT_STATE, active_operations=active_operations, status_porcelain=status.stdout
        )
    owners = worktree_branch_owners(worktrees.stdout, bindings.branch_ref)
    if current_branch.stdout.strip() == bindings.branch_ref.removeprefix("refs/heads/"):
        execution_mode = ExecutionMode.CURRENT_BRANCH
    elif owners:
        stop_capture(WorkflowState.BLOCKED_WORKTREE_IN_USE, owners=[str(path) for path in owners])
    else:
        execution_mode = ExecutionMode.AUTHORIZED_BRANCH_TRANSFER
    remote_refs = command_evidence(
        repository, "for-each-ref", "--format=%(refname)", "--contains", bindings.branch_oid, "refs/remotes"
    )
    if remote_refs.exit_code != 0:
        stop_capture(WorkflowState.BLOCKED_PREFLIGHT_FAILED, command=remote_refs.model_dump(mode="json"))
    publication = PublicationEvidence(
        configured_upstream=upstream.stdout.strip() or None,
        remote_refs_containing_old_tip=[line for line in remote_refs.stdout.splitlines() if line],
        evidence_commands=[remote_refs],
    )
    repository_state = RepositoryStateEvidence(
        repository_root=bindings.root_evidence,
        branch_ref=bindings.branch_ref_evidence,
        branch_oid=bindings.branch_oid_evidence,
        target_oid=bindings.target_oid_evidence,
        merge_base=bindings.merge_base,
        worktrees=worktrees,
        status=status,
        current_branch=current_branch,
        rebase_merge=rebase_merge,
        rebase_apply=rebase_apply,
        merge_head=merge_head,
        cherry_pick_head=cherry_pick_head,
        upstream=upstream,
    )
    return CapturePreflight(
        repository_state=repository_state,
        execution_mode=execution_mode,
        active_operations=active_operations,
        publication=publication,
    )


def assemble_capture(
    repository: Path, request: CaptureRequest, bindings: CaptureBindings, preflight: CapturePreflight
) -> ManagedCapture:
    """Capture the graph and assemble one immutable managed artifact.

    Returns:
        Complete managed capture ready for Git-dir storage.
    """
    inventory = command_evidence(
        repository,
        "rev-list",
        "--reverse",
        "--topo-order",
        "--parents",
        f"{bindings.target_oid}..{bindings.branch_oid}",
    )
    if inventory.exit_code != 0:
        stop_capture(WorkflowState.BLOCKED_PREFLIGHT_FAILED, command=inventory.model_dump(mode="json"))
    try:
        candidates, affected_paths, target_name_status, branch_name_status, clean_cherry = capture_candidates(
            repository, inventory, bindings.merge_base.stdout.strip(), bindings.target_oid, bindings.branch_oid
        )
        rebase_help = command_evidence(repository, "rebase", "-h")
        empty_option = detect_empty_option(rebase_help)
    except ValueError as error:
        stop_capture(WorkflowState.BLOCKED_PREFLIGHT_FAILED, error=str(error))
    instruction_search, instruction_sources = capture_instruction_sources(bindings.root)
    publication_requires_approval = bool(
        preflight.publication.configured_upstream or preflight.publication.remote_refs_containing_old_tip
    )
    return ManagedCapture(
        capture_id=uuid.uuid4().hex,
        repository_root=str(bindings.root),
        branch_ref=bindings.branch_ref,
        branch_oid=bindings.branch_oid,
        target_ref=bindings.target_ref,
        target_oid=bindings.target_oid,
        expected_target_oid=request.expected_target_oid,
        merge_base_oid=bindings.merge_base.stdout.strip(),
        execution_worktree=str(bindings.root),
        execution_mode=preflight.execution_mode,
        status_porcelain=preflight.repository_state.status.stdout,
        active_operations=preflight.active_operations,
        repository_state=preflight.repository_state,
        repository_instruction_search=instruction_search,
        repository_instruction_sources=instruction_sources,
        publication=preflight.publication,
        replay_inventory=inventory,
        candidates=candidates,
        affected_paths=affected_paths,
        target_name_status=target_name_status,
        branch_name_status=branch_name_status,
        clean_cherry=clean_cherry,
        rebase_help=rebase_help,
        becomes_empty_option=empty_option,
        publication_requires_approval=publication_requires_approval,
    )


def capture_rebase(repository: Path, request: CaptureRequest) -> tuple[dict[str, object], int]:
    """Capture immutable rebase evidence or emit one canonical terminal.

    Returns:
        Structured capture output and its process exit code.
    """
    try:
        bindings = capture_bindings(repository, request)
        preflight = capture_preflight(repository, bindings)
        capture = assemble_capture(repository, request, bindings, preflight)
        capture_path, digest = store_capture(repository, capture)
    except CaptureStop as stopped:
        return stopped.output, stopped.exit_code
    common_output: dict[str, object] = {
        "capture_id": capture.capture_id,
        "capture_path": str(capture_path),
        "capture_sha256": digest,
        "semantic_template": semantic_template(capture),
    }
    if capture.publication_requires_approval:
        return (
            {
                **common_output,
                "decision": "Approve rewriting the captured published branch in a later invocation.",
                "state": WorkflowState.NEEDS_USER_DECISION,
                "status": "DECISION_REQUIRED",
                "terminal": True,
            },
            1,
        )
    return (
        {
            **common_output,
            "affected_paths": [path.model_dump(mode="json") for path in capture.affected_paths],
            "candidates": [candidate.model_dump(mode="json") for candidate in capture.candidates],
            "target_name_status": capture.target_name_status.model_dump(mode="json"),
            "branch_name_status": capture.branch_name_status.model_dump(mode="json"),
            "clean_cherry": capture.clean_cherry.model_dump(mode="json"),
            "repository_instruction_search": [
                source.model_dump(mode="json") for source in capture.repository_instruction_search
            ],
            "state": WorkflowState.READY_TO_ANALYZE,
            "status": "CAPTURED",
            "terminal": False,
        },
        0,
    )

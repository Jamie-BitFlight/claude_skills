"""Managed Git-dir evidence capture and artifact storage for local rebases."""

from __future__ import annotations

import hashlib
import os
import re
import signal
import subprocess
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from rebase_evidence import CommandEvidence, PathMarkerEvidence, RefMarkerEvidence, RepositoryStateEvidence
from rebase_models import (
    AffectedPathEvidence,
    BecomesEmptyOption,
    CapturedCandidate,
    CaptureId,
    ExecutionMode,
    ObjectId,
)
from rebase_prepare import COMMAND_TIMEOUT_SECONDS, TERMINATION_GRACE_SECONDS, run_git
from rebase_responses import WorkflowTerminal
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
    content: str | None = None
    sha256: str | None = None


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
    affected_paths: list[AffectedPathEvidence]
    target_name_status: CommandEvidence
    branch_name_status: CommandEvidence
    clean_cherry: CommandEvidence
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


def ref_terminal(evidence: CommandEvidence, ref: str) -> tuple[WorkflowTerminal, int]:
    """Return the canonical invalid-ref terminal."""
    return (
        WorkflowTerminal(
            command=evidence,
            error=f"invalid local ref: {ref}",
            state=WorkflowState.BLOCKED_INVALID_REF,
            status="BLOCKED",
        ),
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
    """Capture deterministic repository-instruction locations and exact content.

    Returns:
        Searched locations and present instruction sources.
    """
    fixed = [
        root / "AGENTS.md",
        root / "CLAUDE.md",
        root / ".claude" / "CLAUDE.md",
        root / ".github" / "copilot-instructions.md",
    ]
    discovered = [
        *sorted((root / ".agent" / "rules").glob("*.md")),
        *sorted((root / ".cursor" / "rules").glob("*.mdc")),
    ]
    candidates = [*fixed, *discovered]
    observations: list[InstructionSourceObservation] = []
    for path in candidates:
        if path.is_file():
            content = path.read_text(encoding="utf-8")
            observations.append(
                InstructionSourceObservation(
                    path=str(path), present=True, content=content, sha256=hashlib.sha256(content.encode()).hexdigest()
                )
            )
        else:
            observations.append(InstructionSourceObservation(path=str(path), present=False))
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


def capture_candidate(repository: Path, oid: str, parents: list[str], equivalent_oids: set[str]) -> CapturedCandidate:
    """Capture complete semantic evidence for one candidate.

    Returns:
        Immutable candidate evidence.
    """
    metadata = command_evidence(repository, "show", "--format=fuller", "--no-patch", oid)
    patch = command_evidence(
        repository, "show", "--format=fuller", "--find-renames", "--find-copies", "--stat", "--patch", oid
    )
    name_status = command_evidence(repository, "diff-tree", "--root", "-m", "--name-status", "-r", "-M", "-C", oid)
    if any(result.exit_code != 0 for result in (metadata, patch, name_status)):
        raise ValueError(f"candidate path capture failed: {oid}")
    paths: list[str] = []
    for status_line in name_status.stdout.splitlines():
        if "\t" not in status_line:
            continue
        for path in status_line.split("\t")[1:]:
            if path and path not in paths:
                paths.append(path)
    return CapturedCandidate(
        oid=oid,
        parents=parents,
        paths=paths,
        commit_metadata=metadata.model_dump(),
        patch=patch.model_dump(),
        name_status=name_status.model_dump(),
        evidence_ids=[
            f"candidate:{oid}:metadata",
            f"candidate:{oid}:patch",
            f"candidate:{oid}:name-status",
            "branch:clean-cherry",
        ],
        clean_cherry_equivalent=oid in equivalent_oids,
    )


def capture_path_evidence(
    repository: Path,
    path: str,
    candidates: list[CapturedCandidate],
    merge_base_oid: str,
    target_oid: str,
    branch_oid: str,
) -> AffectedPathEvidence:
    """Capture branch and target interaction evidence for one path.

    Returns:
        Immutable affected-path evidence.
    """
    target_evidence = command_evidence(repository, "diff", "-M", "-C", f"{merge_base_oid}..{target_oid}", "--", path)
    branch_evidence = command_evidence(repository, "diff", "-M", "-C", f"{merge_base_oid}..{branch_oid}", "--", path)
    if target_evidence.exit_code != 0 or branch_evidence.exit_code != 0:
        raise ValueError(f"path interaction evidence capture failed: {path}")
    return AffectedPathEvidence(
        path=path,
        candidate_oids=[candidate.oid for candidate in candidates if path in candidate.paths],
        evidence_ids=[f"path:{path}:candidate-membership", f"path:{path}:target-diff", f"path:{path}:branch-diff"],
        target_evidence=target_evidence.model_dump(),
        branch_evidence=branch_evidence.model_dump(),
    )


def capture_candidates(
    repository: Path, inventory: CommandEvidence, merge_base_oid: str, target_oid: str, branch_oid: str
) -> tuple[list[CapturedCandidate], list[AffectedPathEvidence], CommandEvidence, CommandEvidence, CommandEvidence]:
    """Derive immutable candidate graph and affected paths from Git evidence.

    Returns:
        Candidates, path evidence, branch diffs, and clean-cherry evidence.
    """
    target_name_status = command_evidence(
        repository, "diff", "--name-status", "-M", "-C", f"{merge_base_oid}..{target_oid}"
    )
    branch_name_status = command_evidence(
        repository, "diff", "--name-status", "-M", "-C", f"{merge_base_oid}..{branch_oid}"
    )
    clean_cherry = command_evidence(repository, "cherry", "-v", target_oid, branch_oid)
    if any(result.exit_code != 0 for result in (target_name_status, branch_name_status, clean_cherry)):
        raise ValueError("branch semantic evidence capture failed")
    equivalent_oids = {
        line.split()[1] for line in clean_cherry.stdout.splitlines() if line.startswith("- ") and len(line.split()) > 1
    }
    candidates = [
        capture_candidate(repository, fields[0], fields[1:], equivalent_oids)
        for line in inventory.stdout.splitlines()
        if (fields := line.split())
    ]
    if not candidates:
        raise ValueError("managed replay inventory contains no candidates")
    affected_paths = list(dict.fromkeys(path for candidate in candidates for path in candidate.paths))
    path_evidence = [
        capture_path_evidence(repository, path, candidates, merge_base_oid, target_oid, branch_oid)
        for path in affected_paths
    ]
    return candidates, path_evidence, target_name_status, branch_name_status, clean_cherry


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
            {
                "path": path.path,
                "target_interaction": None,
                "dependencies": [],
                "evidence": [],
                "verification_commands": [],
            }
            for path in capture.affected_paths
        ],
        "merge_policy": None,
        "repository_checks": [],
        "instruction_acknowledgements": [],
        "unknowns": [],
        "decisions": [],
    }

"""Typed universal repository-state evidence for the rebase plan gate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, Field

from rebase_models import ExecutionMode

ArgumentVector = Annotated[list[str], Field(min_length=1)]
PATH_STATE_ARGV_LENGTH = 6
PATH_STATE_SCRIPT_INDEX = 3


class CommandEvidence(BaseModel):
    """Complete output from one preflight command."""

    source: Annotated[str, Field(min_length=1)]
    argv: ArgumentVector
    exit_code: int
    stdout: str
    stderr: str


class PathMarkerEvidence(BaseModel):
    """A Git-path lookup paired with command-backed filesystem evidence."""

    command: CommandEvidence
    existence: CommandEvidence
    present: bool


class RefMarkerEvidence(BaseModel):
    """A Git ref lookup paired with the observed ref state."""

    command: CommandEvidence
    present: bool


class RepositoryStateEvidence(BaseModel):
    """Complete universal Step 1 evidence required before rebase analysis."""

    repository_root: CommandEvidence
    branch_ref: CommandEvidence
    branch_oid: CommandEvidence
    target_oid: CommandEvidence
    merge_base: CommandEvidence
    worktrees: CommandEvidence
    status: CommandEvidence
    current_branch: CommandEvidence
    rebase_merge: PathMarkerEvidence
    rebase_apply: PathMarkerEvidence
    merge_head: RefMarkerEvidence
    cherry_pick_head: RefMarkerEvidence
    upstream: CommandEvidence

    def validate_bindings(
        self,
        *,
        branch_ref: str,
        branch_oid: str,
        target_ref: str,
        target_oid: str,
        merge_base_oid: str,
        execution_worktree: str,
        status_porcelain: str,
        active_operations: list[str],
        configured_upstream: str | None,
        execution_mode: ExecutionMode,
    ) -> None:
        """Require every command and observation to bind the plan's declared state."""
        self.validate_refs(branch_ref, branch_oid, target_ref, target_oid, merge_base_oid, execution_worktree)
        self.validate_worktree(branch_ref, execution_worktree, status_porcelain, execution_mode)
        self.validate_operations(execution_worktree, active_operations)
        require_success(self.upstream, ["git", "for-each-ref", "--format=%(upstream)", branch_ref])
        if self.upstream.stdout.strip() != (configured_upstream or ""):
            raise ValueError("upstream evidence does not match configured_upstream")

    def validate_refs(
        self,
        branch_ref: str,
        branch_oid: str,
        target_ref: str,
        target_oid: str,
        merge_base_oid: str,
        execution_worktree: str,
    ) -> None:
        """Require repository, branch, target, and merge-base bindings."""
        require_success(self.repository_root, ["git", "rev-parse", "--show-toplevel"])
        if Path(self.repository_root.stdout.strip()) != Path(execution_worktree):
            raise ValueError("repository-root evidence does not match the execution worktree")
        require_success(self.branch_ref, ["git", "show-ref", "--verify", branch_ref])
        if self.branch_ref.stdout.strip() != f"{branch_oid} {branch_ref}":
            raise ValueError("branch-ref evidence does not match the planned branch")
        require_oid(self.branch_oid, ["git", "rev-parse", "--verify", f"{branch_ref}^{{commit}}"], branch_oid)
        require_oid(self.target_oid, ["git", "rev-parse", "--verify", f"{target_ref}^{{commit}}"], target_oid)
        require_oid(self.merge_base, ["git", "merge-base", branch_ref, target_ref], merge_base_oid)

    def validate_worktree(
        self, branch_ref: str, execution_worktree: str, status_porcelain: str, execution_mode: ExecutionMode
    ) -> None:
        """Require clean status and exact worktree ownership."""
        require_success(self.worktrees, ["git", "worktree", "list", "--porcelain"])
        branch_owners = worktree_branch_owners(self.worktrees.stdout, branch_ref)
        require_success(self.status, ["git", "status", "--porcelain=v1", "--untracked-files=all"])
        if self.status.stdout != status_porcelain:
            raise ValueError("status evidence does not match status_porcelain")
        require_success(self.current_branch, ["git", "symbolic-ref", "--quiet", "--short", "HEAD"])
        branch_prefix = "refs/heads/"
        if not branch_ref.startswith(branch_prefix):
            raise ValueError("planned branch is not a local branch ref")
        planned_short_branch = branch_ref.removeprefix(branch_prefix)
        current_short_branch = self.current_branch.stdout.strip()
        if execution_mode is ExecutionMode.CURRENT_BRANCH:
            if current_short_branch != planned_short_branch:
                raise ValueError("current-branch evidence does not match the planned branch")
            if branch_owners != [Path(execution_worktree)]:
                raise ValueError("planned branch is not owned by the execution worktree")
        elif current_short_branch == planned_short_branch or branch_owners:
            raise ValueError("branch-transfer evidence requires an unowned non-current planned branch")

    def validate_operations(self, execution_worktree: str, active_operations: list[str]) -> None:
        """Require operation markers to match the declared active-operation set."""
        validate_path_marker(self.rebase_merge, "rebase-merge", Path(execution_worktree))
        validate_path_marker(self.rebase_apply, "rebase-apply", Path(execution_worktree))
        validate_ref_marker(self.merge_head, "MERGE_HEAD")
        validate_ref_marker(self.cherry_pick_head, "CHERRY_PICK_HEAD")
        observed_operations = {
            operation
            for operation, present in (
                ("rebase-merge", self.rebase_merge.present),
                ("rebase-apply", self.rebase_apply.present),
                ("MERGE_HEAD", self.merge_head.present),
                ("CHERRY_PICK_HEAD", self.cherry_pick_head.present),
            )
            if present
        }
        if observed_operations != set(active_operations):
            raise ValueError("operation-marker evidence does not match active_operations")


def require_success(evidence: CommandEvidence, argv: list[str]) -> None:
    """Require exact argv and a successful command result."""
    if evidence.argv != argv:
        raise ValueError(f"preflight command does not match required argv: {argv}")
    if evidence.exit_code != 0:
        raise ValueError(f"required preflight command failed: {argv}")


def require_oid(evidence: CommandEvidence, argv: list[str], oid: str) -> None:
    """Require a successful exact command resolving one planned OID."""
    require_success(evidence, argv)
    if evidence.stdout.strip() != oid:
        raise ValueError(f"preflight OID evidence does not match the plan: {argv}")


def validate_path_marker(marker: PathMarkerEvidence, name: str, execution_worktree: Path) -> None:
    """Require a Git path whose command-backed state agrees with presence."""
    require_success(marker.command, ["git", "rev-parse", "--git-path", name])
    observed_path = marker.command.stdout.strip()
    if not observed_path:
        raise ValueError(f"Git path lookup returned no path: {name}")
    path = Path(observed_path)
    resolved_path = path if path.is_absolute() else execution_worktree / path
    if len(marker.existence.argv) != PATH_STATE_ARGV_LENGTH:
        raise ValueError(f"operation-marker existence command is invalid: {name}")
    expected_argv = [
        "uv",
        "run",
        "--script",
        marker.existence.argv[PATH_STATE_SCRIPT_INDEX],
        "path-state",
        str(resolved_path),
    ]
    if (
        marker.existence.argv != expected_argv
        or Path(marker.existence.argv[PATH_STATE_SCRIPT_INDEX]).name != "rebase_plan.py"
        or marker.existence.exit_code != 0
        or marker.existence.stderr
    ):
        raise ValueError(f"operation-marker existence command is invalid: {name}")
    try:
        observation = json.loads(marker.existence.stdout)
    except json.JSONDecodeError as error:
        raise ValueError(f"operation-marker existence output is invalid JSON: {name}") from error
    if observation != {"response_kind": "path-state", "path": str(resolved_path), "present": marker.present}:
        raise ValueError(f"operation-marker path state disagrees with presence: {name}")


def validate_ref_marker(marker: RefMarkerEvidence, name: str) -> None:
    """Require a ref lookup whose exit status agrees with marker presence."""
    if marker.command.argv != ["git", "rev-parse", "--verify", "--quiet", name]:
        raise ValueError(f"operation-marker command does not match required argv: {name}")
    if (marker.command.exit_code == 0) is not marker.present:
        raise ValueError(f"operation-marker result disagrees with presence: {name}")


def worktree_branch_owners(output: str, branch_ref: str) -> list[Path]:
    """Return every worktree path whose porcelain record owns the branch."""
    owners: list[Path] = []
    for record in output.strip().split("\n\n"):
        fields = dict(line.split(" ", 1) for line in record.splitlines() if " " in line)
        if fields.get("branch") == branch_ref and "worktree" in fields:
            owners.append(Path(fields["worktree"]))
    return owners

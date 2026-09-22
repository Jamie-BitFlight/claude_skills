"""Typed universal repository-state evidence for the rebase plan gate."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, Field

ArgumentVector = Annotated[list[str], Field(min_length=1)]


class CommandEvidence(BaseModel):
    """Complete output from one preflight command."""

    source: Annotated[str, Field(min_length=1)]
    argv: ArgumentVector
    exit_code: int
    stdout: str
    stderr: str


class MarkerEvidence(BaseModel):
    """A Git marker lookup paired with the observed filesystem/ref state."""

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
    rebase_merge: MarkerEvidence
    rebase_apply: MarkerEvidence
    merge_head: MarkerEvidence
    cherry_pick_head: MarkerEvidence
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
    ) -> None:
        """Require every command and observation to bind the plan's declared state."""
        require_success(self.repository_root, ["git", "rev-parse", "--show-toplevel"])
        if Path(self.repository_root.stdout.strip()) != Path(execution_worktree):
            raise ValueError("repository-root evidence does not match the execution worktree")

        require_success(self.branch_ref, ["git", "show-ref", "--verify", branch_ref])
        if self.branch_ref.stdout.strip() != f"{branch_oid} {branch_ref}":
            raise ValueError("branch-ref evidence does not match the planned branch")

        require_oid(self.branch_oid, ["git", "rev-parse", "--verify", f"{branch_ref}^{{commit}}"], branch_oid)
        require_oid(self.target_oid, ["git", "rev-parse", "--verify", f"{target_ref}^{{commit}}"], target_oid)
        require_oid(self.merge_base, ["git", "merge-base", branch_ref, target_ref], merge_base_oid)
        require_success(self.worktrees, ["git", "worktree", "list", "--porcelain"])
        branch_owners = worktree_branch_owners(self.worktrees.stdout, branch_ref)
        if branch_owners and branch_owners != [Path(execution_worktree)]:
            raise ValueError("planned branch is owned by a different worktree")
        require_success(self.status, ["git", "status", "--porcelain=v1", "--untracked-files=all"])
        if self.status.stdout != status_porcelain:
            raise ValueError("status evidence does not match status_porcelain")

        require_success(self.current_branch, ["git", "symbolic-ref", "--quiet", "--short", "HEAD"])
        validate_path_marker(self.rebase_merge, "rebase-merge")
        validate_path_marker(self.rebase_apply, "rebase-apply")
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

        require_success(self.upstream, ["git", "for-each-ref", "--format=%(upstream)", branch_ref])
        if self.upstream.stdout.strip() != (configured_upstream or ""):
            raise ValueError("upstream evidence does not match configured_upstream")


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


def validate_path_marker(marker: MarkerEvidence, name: str) -> None:
    """Require exact path lookup evidence and a successful resolution."""
    require_success(marker.command, ["git", "rev-parse", "--git-path", name])
    if not marker.command.stdout.strip():
        raise ValueError(f"Git path lookup returned no path: {name}")


def validate_ref_marker(marker: MarkerEvidence, name: str) -> None:
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

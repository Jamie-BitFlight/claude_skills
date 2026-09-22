"""Canonical typed models shared by rebase validation and execution."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

ObjectId = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}([0-9a-f]{24})?$")]
PlanSha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
LocalBranchRef = Annotated[str, StringConstraints(pattern=r"^refs/heads/.+")]
RecoveryRef = Annotated[str, StringConstraints(pattern=r"^refs/heads/rebase-backup/[a-z0-9][a-z0-9-]*$")]
ArgumentVector = Annotated[list[str], Field(min_length=1)]


class ExecutionMode(StrEnum):
    """How the planned branch reaches the authorized execution worktree."""

    CURRENT_BRANCH = "CURRENT_BRANCH"
    AUTHORIZED_BRANCH_TRANSFER = "AUTHORIZED_BRANCH_TRANSFER"


class MergePolicy(StrEnum):
    """How the plan treats merge topology."""

    LINEAR_NO_MERGES = "LINEAR_NO_MERGES"
    PRESERVE_TOPOLOGY = "PRESERVE_TOPOLOGY"
    APPROVED_FLATTEN = "APPROVED_FLATTEN"


class BecomesEmptyOption(StrEnum):
    """Installed Git spelling that stops on a commit that becomes empty."""

    ASK = "ask"
    STOP = "stop"


class PrepareRequest(BaseModel):
    """Immutable fields needed to authorize one replay command."""

    model_config = ConfigDict(frozen=True)

    branch_ref: LocalBranchRef
    branch_oid: ObjectId
    target_ref: Annotated[str, Field(min_length=1)]
    target_oid: ObjectId
    execution_worktree: Annotated[str, Field(min_length=1)]
    execution_mode: ExecutionMode
    merge_policy: MergePolicy
    becomes_empty_option: BecomesEmptyOption
    recovery_ref: RecoveryRef


class CommandResult(BaseModel):
    """Complete result from one bounded Git command."""

    model_config = ConfigDict(frozen=True)

    argv: ArgumentVector
    exit_code: int
    stdout: str
    stderr: str


class ReplayReceipt(BaseModel):
    """Durable proof that one validated plan hash was consumed before replay."""

    model_config = ConfigDict(frozen=True)

    plan_sha256: PlanSha256
    argv: ArgumentVector
    state: Literal["CONSUMED"] = "CONSUMED"


class ReplayExecution(BaseModel):
    """One receipt-backed replay command result."""

    model_config = ConfigDict(frozen=True)

    receipt_path: Annotated[str, Field(min_length=1)]
    command: CommandResult

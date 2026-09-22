"""Canonical typed models shared by rebase validation and execution."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints

ObjectId = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}([0-9a-f]{24})?$")]
PlanSha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
LocalBranchRef = Annotated[str, StringConstraints(pattern=r"^refs/heads/.+")]
RecoveryRef = Annotated[str, StringConstraints(pattern=r"^refs/heads/rebase-backup/[a-z0-9][a-z0-9-]*$")]
ArgumentVector = Annotated[list[str], Field(min_length=1)]
CaptureId = Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{32}$")]
READ_ONLY_PREFLIGHT_LENGTH = 4


def validate_read_only_preflight(argv: list[str]) -> list[str]:
    """Accept only an exact-ref existence check with no caller-selected executable.

    Returns:
        The validated Git argument vector.
    """
    if (
        len(argv) == READ_ONLY_PREFLIGHT_LENGTH
        and argv[:3] == ["git", "show-ref", "--verify"]
        and argv[3].startswith("refs/")
    ):
        return argv
    raise ValueError("required preflight must be: git show-ref --verify refs/<exact-ref>")


ReadOnlyPreflightArgv = Annotated[
    list[str], Field(min_length=4, max_length=4), AfterValidator(validate_read_only_preflight)
]


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


class ApprovalOperation(StrEnum):
    """Destructive decision an external approval receipt can authorize."""

    REBASE_PUBLISHED_HISTORY = "REBASE_PUBLISHED_HISTORY"
    REDUNDANT_DROP = "REDUNDANT_DROP"
    FLATTEN_TOPOLOGY = "FLATTEN_TOPOLOGY"
    SEMANTIC_CHANGE = "SEMANTIC_CHANGE"


class CaptureRequest(BaseModel):
    """Invocation intent bound before managed evidence capture."""

    model_config = ConfigDict(frozen=True)

    branch: Annotated[str, Field(min_length=1)]
    target: Annotated[str, Field(min_length=1)]
    expected_target_oid: ObjectId | None = None


class CapturedCommandEvidence(BaseModel):
    """Complete immutable output from one semantic-evidence command."""

    model_config = ConfigDict(frozen=True)

    source: Annotated[str, Field(min_length=1)]
    argv: ArgumentVector
    exit_code: int
    stdout: str
    stderr: str


class CapturedCandidate(BaseModel):
    """Immutable graph and path facts for one replay candidate."""

    model_config = ConfigDict(frozen=True)

    oid: ObjectId
    parents: list[ObjectId]
    paths: list[str]
    commit_metadata: CapturedCommandEvidence
    patch: CapturedCommandEvidence
    name_status: CapturedCommandEvidence
    evidence_ids: Annotated[list[str], Field(min_length=1)]
    clean_cherry_equivalent: bool


class AffectedPathEvidence(BaseModel):
    """Captured candidate and branch-side evidence for one affected path."""

    model_config = ConfigDict(frozen=True)

    path: Annotated[str, Field(min_length=1)]
    candidate_oids: Annotated[list[ObjectId], Field(min_length=1)]
    evidence_ids: Annotated[list[str], Field(min_length=1)]
    target_evidence: CapturedCommandEvidence
    branch_evidence: CapturedCommandEvidence


class CandidateSemantics(BaseModel):
    """Agent judgment for one captured candidate without immutable Git fields."""

    model_config = ConfigDict(frozen=True)

    oid: ObjectId
    intent: Annotated[str, Field(min_length=1)]
    evidence: Annotated[list[str], Field(min_length=1)]
    disposition: Literal["RETAIN", "ADAPT", "MANUAL_MERGE", "REDUNDANT_DROP", "PRESERVE_EMPTY"]
    verification_commands: Annotated[list[ArgumentVector], Field(min_length=1)]
    expected_conflict_paths: list[str]
    equivalence_evidence: list[str]
    drop_approval_decision_id: str | None = None


class PathSemantics(BaseModel):
    """Agent judgment for one captured affected path."""

    model_config = ConfigDict(frozen=True)

    path: Annotated[str, Field(min_length=1)]
    target_interaction: Annotated[str, Field(min_length=1)]
    dependencies: list[str]
    evidence: Annotated[list[str], Field(min_length=1)]
    verification_commands: Annotated[list[ArgumentVector], Field(min_length=1)]


class SemanticDecision(BaseModel):
    """One decision requiring externally sourced approval."""

    model_config = ConfigDict(frozen=True)

    decision_id: Annotated[str, Field(min_length=1)]
    question: Annotated[str, Field(min_length=1)]
    operation: ApprovalOperation


class InstructionAcknowledgement(BaseModel):
    """Agent application of one immutable repository-instruction source."""

    model_config = ConfigDict(frozen=True)

    path: Annotated[str, Field(min_length=1)]
    source_sha256: PlanSha256
    applied_requirements_summary: Annotated[str, Field(min_length=1)]
    required_preflight_argv: list[ReadOnlyPreflightArgv]


class FinalizeSemantics(BaseModel):
    """Only the semantic judgments accepted by managed finalization."""

    model_config = ConfigDict(frozen=True)

    candidates: Annotated[list[CandidateSemantics], Field(min_length=1)]
    affected_paths: list[PathSemantics]
    merge_policy: MergePolicy
    repository_checks: Annotated[list[ArgumentVector], Field(min_length=1)]
    instruction_acknowledgements: list[InstructionAcknowledgement]
    unknowns: list[str]
    decisions: list[SemanticDecision]


class ExternalApprovalReceipt(BaseModel):
    """Explicit later-invocation approval bound to one captured operation.

    This portable contract records provenance but cannot cryptographically prove that a harness,
    rather than an agent, created the receipt.
    """

    model_config = ConfigDict(frozen=True)

    schema_version: Literal[1]
    source: Literal["user-invocation", "harness-human-gate"]
    capture_id: CaptureId
    capture_sha256: PlanSha256
    repository_root: Annotated[str, Field(min_length=1)]
    branch_ref: LocalBranchRef
    old_tip_oid: ObjectId
    target_ref: Annotated[str, Field(min_length=1)]
    target_oid: ObjectId
    operation: ApprovalOperation
    decision_id: Annotated[str, Field(min_length=1)]
    approved: Literal[True]


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
    keep_empty: bool = False
    recovery_ref: RecoveryRef
    required_preflights: list[ArgumentVector] = Field(default_factory=list)


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

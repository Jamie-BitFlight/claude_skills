"""Typed structured responses for the managed rebase CLI boundary."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, RootModel

from rebase_contracts import RebasePlan
from rebase_evidence import CommandEvidence
from rebase_models import CaptureId, CommandResult, ObjectId, PlanSha256
from rebase_states import WorkflowState, WorkflowStateDefinition


class WorkflowTerminal(BaseModel):
    """One fail-closed terminal response with typed optional evidence."""

    model_config = ConfigDict(frozen=True)

    response_kind: Literal["terminal"] = "terminal"
    state: WorkflowState
    status: str = Field(min_length=1)
    terminal: Literal[True] = True
    error: str | None = None
    errors: list[dict[str, JsonValue]] | None = None
    command: CommandEvidence | None = None
    missing_approvals: list[str] | None = None
    decision: str | None = None
    capture_id: CaptureId | None = None
    capture_path: str | None = None
    capture_sha256: PlanSha256 | None = None
    semantic_template: JsonValue | None = None
    expected_target_oid: ObjectId | None = None
    observed_target_oid: ObjectId | None = None
    branch_oid: ObjectId | None = None
    target_oid: ObjectId | None = None
    active_operations: list[str] | None = None
    status_porcelain: str | None = None
    owners: list[str] | None = None


class CaptureReady(BaseModel):
    """Complete nonterminal capture result ready for semantic analysis."""

    model_config = ConfigDict(frozen=True)

    response_kind: Literal["capture-ready"] = "capture-ready"
    capture_id: CaptureId
    capture_path: str = Field(min_length=1)
    capture_sha256: PlanSha256
    semantic_template: JsonValue
    affected_paths: list[JsonValue]
    candidates: list[JsonValue]
    target_name_status: CommandEvidence
    branch_name_status: CommandEvidence
    clean_cherry: CommandEvidence
    repository_instruction_search: list[JsonValue]
    state: Literal[WorkflowState.READY_TO_ANALYZE] = WorkflowState.READY_TO_ANALYZE
    status: Literal["CAPTURED"] = "CAPTURED"
    terminal: Literal[False] = False


class ValidationReady(BaseModel):
    """Validated plan identity and content binding."""

    model_config = ConfigDict(frozen=True)

    response_kind: Literal["validation-ready"] = "validation-ready"
    plan_id: str = Field(min_length=1)
    sha256: PlanSha256
    state: Literal[WorkflowState.READY_TO_REBASE] = WorkflowState.READY_TO_REBASE
    status: Literal["VALID"] = "VALID"


class FinalizeReady(BaseModel):
    """Persisted managed plan ready for one replay."""

    model_config = ConfigDict(frozen=True)

    response_kind: Literal["finalize-ready"] = "finalize-ready"
    plan_id: str = Field(min_length=1)
    plan_path: str = Field(min_length=1)
    sha256: PlanSha256
    state: Literal[WorkflowState.READY_TO_REBASE] = WorkflowState.READY_TO_REBASE
    status: Literal["FINALIZED"] = "FINALIZED"
    terminal: Literal[False] = False


class ReplayResult(BaseModel):
    """Complete result from one consumed replay command."""

    model_config = ConfigDict(frozen=True)

    response_kind: Literal["replay-result"] = "replay-result"
    argv: list[str] = Field(min_length=1)
    plan_id: str = Field(min_length=1)
    receipt_path: str = Field(min_length=1)
    replay: CommandResult
    sha256: PlanSha256
    status: Literal["REPLAY_FINISHED", "REPLAY_STOPPED"]


class PathStateResult(BaseModel):
    """Observed state for one resolved Git path."""

    model_config = ConfigDict(frozen=True)

    response_kind: Literal["path-state"] = "path-state"
    path: str = Field(min_length=1)
    present: bool


class SchemaDocument(RootModel[dict[str, JsonValue]]):
    """Pydantic-generated plan schema at the CLI boundary."""


class StateDocument(RootModel[list[WorkflowStateDefinition]]):
    """Canonical workflow-state contract at the CLI boundary."""


class PlanBuildResult(BaseModel):
    """Typed outcome from managed plan construction."""

    model_config = ConfigDict(frozen=True)

    plan: RebasePlan | None = None
    terminal: WorkflowTerminal | None = None
    exit_code: int


CliResponse = Annotated[
    WorkflowTerminal | CaptureReady | ValidationReady | FinalizeReady | ReplayResult | PathStateResult,
    Field(discriminator="response_kind"),
]

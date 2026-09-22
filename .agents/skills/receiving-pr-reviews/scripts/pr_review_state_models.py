"""Canonical provider-neutral review-input and cycle-state models."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from pr_review_contracts import ChangeRequestTarget, ProviderName, ReviewAction, ReviewTransport

InputKind = Literal["comment", "question", "approval", "rejection"]
CycleState = Literal[
    "CONTEXT_REQUIRED",
    "SNAPSHOT_INCOMPLETE",
    "ASSESSMENT_REQUIRED",
    "CLUSTERING_REQUIRED",
    "UNKNOWN_RESOLUTION_REQUIRED",
    "PLAN_REQUIRED",
    "READY_FOR_ACTION",
    "IMPLEMENTATION_REQUIRED",
    "COMMUNICATION_REQUIRED",
    "RECHECK_REQUIRED",
    "BLOCKED",
    "ERROR",
    "REVIEW_COMPLETE",
]


class ReviewActor(BaseModel):
    """Provider-observed identity and role for one input actor."""

    actor_id: str | None
    login: str | None
    display_name: str | None = None
    classification: Literal["human", "bot", "unknown"]
    role: Literal["reviewer", "stakeholder", "author", "unknown"]


class ReviewCapabilities(BaseModel):
    """Actions the provider exposes for one normalized input."""

    can_reply: bool
    can_resolve: bool
    unavailable: list[str]


class ReviewInput(BaseModel):
    """One independently assessable provider object."""

    model_config = ConfigDict(strict=True)

    input_id: str = Field(min_length=1)
    provider: ProviderName
    provider_ids: dict[str, str]
    source_kind: str = Field(min_length=1)
    kinds: set[InputKind] = Field(min_length=1)
    location: Literal["inline", "top_level"]
    direction: Literal["inbound", "outbound"]
    actor: ReviewActor
    body: str
    stable_reference: str = Field(min_length=1)
    created_at: datetime | None
    updated_at: datetime | None
    revision_relation: Literal["current", "stale", "unknown"]
    path: str | None
    line: int | None
    provider_state: str
    capabilities: ReviewCapabilities
    thread_id: str | None
    parent_id: str | None


class SnapshotCompleteness(BaseModel):
    """Auditable proof that every required surface used one transport."""

    transport: ReviewTransport
    required_surfaces: set[str]
    completed_surfaces: set[str]
    truncated_input_ids: list[str]
    unavailable_capabilities: list[str]

    @property
    def complete(self) -> bool:
        """Whether every required surface completed with no truncation.

        Returns:
            True only for an exhaustive snapshot.
        """
        return self.required_surfaces == self.completed_surfaces and not self.truncated_input_ids


def calculate_snapshot_fingerprint(
    target: ChangeRequestTarget, revision: str, review_inputs: list[ReviewInput], completeness: SnapshotCompleteness
) -> str:
    """Hash canonical snapshot identity and completeness evidence.

    Returns:
        A stable SHA-256 fingerprint.
    """
    payload = {
        "target": target.model_dump(mode="json"),
        "revision": revision,
        "review_inputs": [item.model_dump(mode="json") for item in review_inputs],
        "completeness": completeness.model_dump(mode="json"),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class ReviewAssessment(BaseModel):
    """Evidence-bearing disposition for exactly one inbound input."""

    input_id: str
    validity: Literal["valid", "invalid", "unknown"]
    relevance: Literal["relevant", "irrelevant", "unknown"]
    evidence: list[str] = Field(min_length=1)
    affected_scope: list[str]
    verification_surface: list[str]
    disposition: Literal["accepted_change", "no_change", "clarification_required", "superseded"]
    kind_assessment: Literal["not_applicable", "approval_assessed", "rejection_assessed"]
    semantic_kinds: set[InputKind] = Field(min_length=1)
    unknowns: list[str]
    cluster_id: str
    communication_plan: str = Field(min_length=1)


class ReviewCluster(BaseModel):
    """One systemic plan covering related assessments or an explicit singleton."""

    cluster_id: str
    input_ids: list[str] = Field(min_length=1)
    shared_basis: list[str] = Field(min_length=1)
    explicit_singleton: bool
    systemic_outcome: str = Field(min_length=1)
    evidence: list[str] = Field(min_length=1)
    verification_commands: list[str]
    communication_plan: str = Field(min_length=1)
    resolution_policy: Literal["resolve_after_reply", "leave_open", "unavailable"]

    @model_validator(mode="after")
    def validate_singleton(self) -> ReviewCluster:
        """Require singleton clusters to declare themselves explicitly.

        Returns:
            This validated cluster.
        """
        if len(self.input_ids) == 1 and not self.explicit_singleton:
            message = "a one-input cluster must set explicit_singleton=true"
            raise ValueError(message)
        if len(self.input_ids) > 1 and self.explicit_singleton:
            message = "a multi-input cluster cannot be an explicit singleton"
            raise ValueError(message)
        return self


class ReviewContext(BaseModel):
    """Product, repository, target, and revision facts used during assessment."""

    repository_instructions: str = Field(min_length=1)
    change_request_goal: str = Field(min_length=1)
    changed_scope: list[str] = Field(min_length=1)
    target: ChangeRequestTarget
    remote_head: str = Field(min_length=1)
    revision: str = Field(min_length=1)


class ReviewCycleState(BaseModel):
    """Serialized complete-set assessment and clustering state."""

    context: ReviewContext
    snapshot_fingerprint: str = Field(min_length=1)
    input_census: list[str]
    assessments: list[ReviewAssessment]
    clusters: list[ReviewCluster]
    unknown_decisions: dict[str, str]
    cycle_state: CycleState


class AuthorizedReviewAction(BaseModel):
    """One provider action bound to a complete current cycle and normalized input."""

    target: ChangeRequestTarget
    snapshot_fingerprint: str
    revision: str
    review_input: ReviewInput
    cluster_id: str
    disposition: Literal["accepted_change", "no_change", "clarification_required", "superseded"]
    communication_plan: str
    cycle_state: Literal["READY_FOR_ACTION"] = "READY_FOR_ACTION"
    action: ReviewAction

"""Canonical provider-neutral review-input and cycle-state models."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, model_validator

from pr_review_contracts import ChangeRequestTarget, NonBlankText, ProviderName, ReviewAction, ReviewTransport

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
    can_comment: bool
    can_approve: bool = False
    can_unapprove: bool = False
    unavailable: list[str]


class ProviderInputIdentity(BaseModel):
    """Typed provider object and mutation targets for one normalized input."""

    object_id: NonBlankText
    reply_target_id: NonBlankText | None = None
    resolution_target_id: NonBlankText | None = None


class ReviewInput(BaseModel):
    """One independently assessable provider object."""

    model_config = ConfigDict(strict=True)

    input_id: str = Field(min_length=1)
    provider: ProviderName
    provider_ids: ProviderInputIdentity
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

    @model_validator(mode="after")
    def validate_mutation_targets(self) -> ReviewInput:
        """Require every advertised mutation to have a typed provider target.

        Returns:
            This input after capability and identity validation.
        """
        if self.capabilities.can_reply and self.provider_ids.reply_target_id is None:
            message = "reply-capable input requires provider reply_target_id"
            raise ValueError(message)
        if self.capabilities.can_resolve and self.provider_ids.resolution_target_id is None:
            message = "resolution-capable input requires provider resolution_target_id"
            raise ValueError(message)
        return self

    @field_serializer("kinds")
    def serialize_kinds(self, value: set[InputKind]) -> list[InputKind]:
        """Serialize semantic kinds deterministically.

        Args:
            value: Input kinds to serialize.

        Returns:
            Kinds sorted by their stable string value.
        """
        return sorted(value)


class SnapshotCompleteness(BaseModel):
    """Auditable proof that every required surface used one transport."""

    transport: ReviewTransport
    required_surfaces: set[str]
    completed_surfaces: set[str]
    truncated_input_ids: list[str]
    unavailable_capabilities: list[str]

    @field_serializer("required_surfaces", "completed_surfaces")
    def serialize_surfaces(self, value: set[str]) -> list[str]:
        """Serialize surface evidence deterministically.

        Args:
            value: Surface names to serialize.

        Returns:
            Surface names in stable lexical order.
        """
        return sorted(value)

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

    Args:
        target: Change request whose review state was sampled.
        revision: Exact sampled remote revision.
        review_inputs: Complete normalized provider input sequence.
        completeness: Evidence for every required provider surface.

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
    evidence: list[NonBlankText] = Field(min_length=1)
    affected_scope: list[NonBlankText] = Field(min_length=1)
    verification_surface: list[NonBlankText] = Field(min_length=1)
    disposition: Literal["accepted_change", "no_change", "clarification_required", "superseded"]
    kind_assessment: Literal["not_applicable", "approval_assessed", "rejection_assessed"]
    semantic_kinds: set[InputKind] = Field(min_length=1)
    unknowns: list[NonBlankText]
    cluster_id: NonBlankText
    communication_plan: NonBlankText

    @field_serializer("semantic_kinds")
    def serialize_semantic_kinds(self, value: set[InputKind]) -> list[InputKind]:
        """Serialize assessed kinds deterministically.

        Args:
            value: Assessed semantic kinds.

        Returns:
            Kinds sorted by their stable string value.
        """
        return sorted(value)


class ReviewCluster(BaseModel):
    """One systemic plan covering related assessments or an explicit singleton."""

    cluster_id: NonBlankText
    input_ids: list[NonBlankText] = Field(min_length=1)
    shared_basis: list[NonBlankText] = Field(min_length=1)
    explicit_singleton: bool
    systemic_outcome: NonBlankText
    evidence: list[NonBlankText] = Field(min_length=1)
    verification_commands: list[NonBlankText] = Field(min_length=1)
    communication_plan: NonBlankText
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
    unknown_decisions: dict[str, NonBlankText]
    implementation_evidence: list[NonBlankText] = Field(min_length=1)
    verification_evidence: list[NonBlankText] = Field(min_length=1)
    inspectable_revision: NonBlankText
    recheck_snapshot_fingerprint: NonBlankText
    communication_states: dict[str, Literal["pending", "completed", "not_required"]]
    resolution_states: dict[str, Literal["open", "resolved", "unavailable"]]
    cycle_terminal: Literal["action_pending", "review_complete", "blocked"]
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
    inspectable_revision: str
    implementation_evidence: list[str]
    verification_evidence: list[str]
    cycle_state: Literal["READY_FOR_ACTION"] = "READY_FOR_ACTION"
    action: ReviewAction

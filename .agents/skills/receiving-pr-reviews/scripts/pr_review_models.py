"""Public review snapshot, compatibility projection, and summary models."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from pr_review_contracts import (
    BatchReviewAction,
    BatchReviewActions,
    ChangeRequestTarget,
    ProviderName,
    ReplyAction,
    RepositoryTarget,
    ResolveAction,
    ReviewAction,
    ReviewActionResult,
    ReviewTransport,
    TopLevelCommentAction,
)
from pr_review_gh_wire import (
    Author,
    CommentNode,
    ForcePushEvent,
    GitHubCommitDate,
    GitHubResponseModel,
    HeadCommitNode,
    IssueComment,
    PageInfo,
    PullRequestHeadState,
    Reaction,
    RepoIdentity,
    ReviewNode,
    ReviewsConnection,
    ReviewThreadsConnection,
)
from pr_review_state_models import (
    InputKind,
    ProviderInputIdentity,
    ReviewActor,
    ReviewAssessment,
    ReviewCapabilities,
    ReviewCluster,
    ReviewInput,
    SnapshotCompleteness,
)

__all__ = [
    "ActionableReviewInput",
    "Author",
    "BatchReviewAction",
    "BatchReviewActions",
    "BoardEntry",
    "ChangeRequestTarget",
    "CommentNode",
    "CommentSummary",
    "FetchActionView",
    "FetchResult",
    "FetchSummary",
    "ForcePushEvent",
    "GitHubCommitDate",
    "GitHubResponseModel",
    "HeadCommitNode",
    "IssueComment",
    "PageInfo",
    "ProviderApprovalState",
    "ProviderSystemEvent",
    "PullRequestHeadState",
    "Reaction",
    "ReplyAction",
    "RepoIdentity",
    "RepositoryTarget",
    "ResolveAction",
    "ReviewAction",
    "ReviewActionResult",
    "ReviewNode",
    "ReviewProviderMetadata",
    "ReviewSnapshot",
    "ReviewSummary",
    "ReviewThreadsConnection",
    "Reviewability",
    "ReviewsConnection",
    "ThreadSummary",
    "TopLevelCommentAction",
    "UnresolvedThread",
    "WatchActionView",
    "WatchResult",
    "WatchSummary",
]


class UnresolvedThread(BaseModel):
    """Legacy GitHub unresolved-thread compatibility projection."""

    id: str
    path: str
    comments: list[CommentNode]
    comments_truncated: bool


class Reviewability(BaseModel):
    """Provider reviewability state and observable blockers."""

    is_draft: bool
    mergeable: str
    merge_state_status: str
    blockers: list[str]


class ProviderSystemEvent(BaseModel):
    """One provider-generated event retained outside the review-input census."""

    id: str
    body: str
    created_at: datetime


class ProviderApprovalState(BaseModel):
    """Provider platform approval configuration without inventing an actor approval."""

    approved: bool
    approvals_required: int
    approvals_left: int
    approval_rules_left: list[object]


class ReviewProviderMetadata(BaseModel):
    """Observable provider state that is not an independently assessable input."""

    system_notes: list[ProviderSystemEvent] = Field(default_factory=list)
    approval_state: ProviderApprovalState | None = None
    blocking_discussions_resolved: bool | None = None
    assigned_reviewers: list[str] | None = None
    requested_reviewers: list[str] | None = None
    checks_state: str | None = None


class FetchResult(BaseModel):
    """Established GitHub fields retained as compatibility projections."""

    reviews_count: int
    reviews_with_body: list[ReviewNode]
    unresponded_reviews: list[ReviewNode]
    threads_count: int
    unresolved: list[UnresolvedThread]
    unresolved_count: int
    codex_approved: bool
    reviewability: Reviewability

    def has_outstanding_work(self) -> bool:
        """Return whether the sampled snapshot contains a watch stop signal."""
        return self.unresolved_count > 0 or bool(self.unresponded_reviews) or self.codex_approved


class ReviewSnapshot(BaseModel):
    """Canonical provider snapshot with optional legacy compatibility projections."""

    provider: ProviderName
    target: ChangeRequestTarget
    transport: ReviewTransport
    snapshot_complete: bool
    snapshot_fingerprint: str
    head_revision: str
    revision_at: datetime
    completeness: SnapshotCompleteness
    review_inputs: list[ReviewInput]
    assessments: list[ReviewAssessment]
    clusters: list[ReviewCluster]
    cycle_state: Literal["SNAPSHOT_INCOMPLETE", "ASSESSMENT_REQUIRED"]
    codex_approval_equivalence: Literal["available", "unavailable"]
    reviews_count: int = 0
    reviews_with_body: list[ReviewNode] = Field(default_factory=list)
    unresponded_reviews: list[ReviewNode] = Field(default_factory=list)
    threads_count: int = 0
    unresolved: list[UnresolvedThread] = Field(default_factory=list)
    unresolved_count: int = 0
    outstanding_input_count: int = 0
    codex_approved: bool | None = None
    reviewability: Reviewability | None = None
    provider_metadata: ReviewProviderMetadata = Field(default_factory=ReviewProviderMetadata)
    communicated_input_ids: set[str] = Field(default_factory=set)

    def provider_consistency_error(self) -> str | None:
        """Return the first cross-provider boundary violation, if any."""
        if self.provider != self.target.repository.provider:
            return "snapshot provider does not match target provider"
        if self.transport != self.completeness.transport:
            return "snapshot transport does not match completeness transport"
        if not self.transport.startswith(f"{self.provider}_"):
            return "snapshot transport does not belong to snapshot provider"
        if any(item.provider != self.provider for item in self.review_inputs):
            return "review input provider does not match snapshot provider"
        if any(not item.input_id.startswith(f"{self.provider}:") for item in self.review_inputs):
            return "canonical input id is outside the snapshot provider namespace"
        return None

    @model_validator(mode="after")
    def validate_provider_consistency(self) -> ReviewSnapshot:
        """Reject snapshots assembled from mixed provider evidence.

        Returns:
            This snapshot after its provider boundary is validated.
        """
        if message := self.provider_consistency_error():
            raise ValueError(message)
        return self

    def has_outstanding_work(self) -> bool:
        """Return whether the sampled snapshot contains a watch stop signal."""
        return (
            self.outstanding_input_count > 0
            or self.unresolved_count > 0
            or bool(self.unresponded_reviews)
            or self.codex_approved is True
        )

    def has_watch_signal(self, baseline_fingerprint: str) -> bool:
        """Return whether work is outstanding or canonical provider state changed.

        Args:
            baseline_fingerprint: Complete canonical snapshot identity at the start of the watch window.

        Returns:
            True when the current state requires a new census or action.
        """
        return self.has_outstanding_work() or self.snapshot_fingerprint != baseline_fingerprint


class WatchResult(BaseModel):
    """Final canonical watch snapshot and bounded polling outcome."""

    timed_out: bool
    state: ReviewSnapshot
    attempts: int = Field(default=1, gt=0)
    attempt_budget_exhausted: bool = False


class ActionableReviewInput(BaseModel):
    """Complete action content plus the stable context needed to act on it."""

    input_id: str
    provider_ids: ProviderInputIdentity
    source_kind: str
    kinds: list[InputKind]
    location: Literal["inline", "top_level"]
    actor: ReviewActor
    body: str
    stable_reference: str
    revision_relation: Literal["current", "stale", "unknown"]
    path: str | None
    line: int | None
    provider_state: str
    capabilities: ReviewCapabilities
    thread_id: str | None
    parent_id: str | None


class CommentSummary(BaseModel):
    """Compatibility representation of one inline follow-up comment."""

    author: str | None
    body: str


class ThreadSummary(BaseModel):
    """Compatibility representation of one unresolved review thread."""

    thread_id: str
    comment_id: int
    path: str
    line: int | None
    comment_count: int
    comments_truncated: bool
    author: str | None
    body: str
    replies: list[CommentSummary] = []


class ReviewSummary(BaseModel):
    """Compatibility representation of one unresponded top-level review."""

    author: str | None
    state: str
    url: str
    body: str


class FetchSummary(BaseModel):
    """Small metadata-only dashboard for choosing the next review action."""

    pr: int
    provider: ProviderName
    snapshot_complete: bool
    cycle_state: Literal["SNAPSHOT_INCOMPLETE", "ASSESSMENT_REQUIRED"]
    unresolved_code_thread_count: int
    unanswered_input_count: int
    approval_count: int
    rejection_count: int
    codex_approved: bool | None
    provider_approved: bool | None
    approvals_required: int | None
    approvals_left: int | None
    assigned_reviewer_count: int | None
    requested_reviewer_count: int | None
    is_draft: bool
    mergeable: str
    merge_state_status: str
    has_conflicts: bool
    checks_state: str | None
    new_input: bool


class FetchActionView(BaseModel):
    """Live actionable inputs with the dashboard state needed to choose an action."""

    dashboard: FetchSummary
    actionable_inputs: list[ActionableReviewInput]


class WatchSummary(FetchSummary):
    """Canonical compact watch output."""

    timed_out: bool
    attempts: int = Field(default=1, gt=0)
    attempt_budget_exhausted: bool = False


class WatchActionView(FetchActionView):
    """Live watch result without historical canonical evidence on stdout."""

    timed_out: bool
    attempts: int = Field(default=1, gt=0)
    attempt_budget_exhausted: bool = False


class BoardEntry(BaseModel):
    """Compatibility representation of one compact multi-request status."""

    pr: int
    unresolved: int
    unresponded: int
    codex_approved: bool | None
    mergeable: str
    merge_state_status: str
    blockers: list[str]

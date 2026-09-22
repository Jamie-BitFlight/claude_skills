"""Public review snapshot, compatibility projection, and summary models."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from pr_review_contracts import (
    ApprovalStateAction,
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
from pr_review_state_models import ReviewAssessment, ReviewCluster, ReviewInput, SnapshotCompleteness

__all__ = [
    "ApprovalStateAction",
    "Author",
    "BatchReviewAction",
    "BatchReviewActions",
    "BoardEntry",
    "ChangeRequestTarget",
    "CommentNode",
    "CommentSummary",
    "FetchResult",
    "FetchSummary",
    "ForcePushEvent",
    "GitHubCommitDate",
    "GitHubResponseModel",
    "HeadCommitNode",
    "IssueComment",
    "PageInfo",
    "PullRequestHeadState",
    "Reaction",
    "ReplyAction",
    "RepoIdentity",
    "RepositoryTarget",
    "ResolveAction",
    "ReviewAction",
    "ReviewActionResult",
    "ReviewNode",
    "ReviewSnapshot",
    "ReviewSummary",
    "ReviewThreadsConnection",
    "Reviewability",
    "ReviewsConnection",
    "ThreadSummary",
    "TopLevelCommentAction",
    "UnresolvedThread",
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
    codex_approved: bool | None = None
    reviewability: Reviewability | None = None

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
        return self.unresolved_count > 0 or bool(self.unresponded_reviews) or self.codex_approved is True


class WatchResult(BaseModel):
    """Final canonical watch snapshot and bounded polling outcome."""

    timed_out: bool
    state: ReviewSnapshot
    attempts: int = Field(default=1, gt=0)
    attempt_budget_exhausted: bool = False


class CommentSummary(BaseModel):
    """One fetched follow-up inline comment."""

    author: str | None
    body: str


class ThreadSummary(BaseModel):
    """Legacy reduced unresolved-thread projection."""

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
    """Legacy reduced unresponded-review projection."""

    author: str | None
    state: str
    url: str
    body: str


class FetchSummary(BaseModel):
    """Canonical compact snapshot retaining legacy action fields."""

    pr: int
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
    reviews_count: int
    threads_count: int
    unresolved_count: int
    unresponded_count: int
    codex_approved: bool | None
    blockers: list[str]
    unresolved: list[ThreadSummary]
    unresponded_reviews: list[ReviewSummary]


class WatchSummary(FetchSummary):
    """Canonical compact watch output."""

    timed_out: bool
    attempts: int = Field(default=1, gt=0)
    attempt_budget_exhausted: bool = False


class BoardEntry(BaseModel):
    """Lightweight multi-PR status entry."""

    pr: int
    unresolved: int
    unresponded: int
    codex_approved: bool | None
    mergeable: str
    merge_state_status: str
    blockers: list[str]

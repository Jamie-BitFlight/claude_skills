"""Strict GitHub mutation-response models for the review provider adapter."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class GitHubMutationModel(BaseModel):
    """Reject response-shape coercion at the GitHub adapter seam."""

    model_config = ConfigDict(strict=True)


class GitHubCreatedComment(GitHubMutationModel):
    """Created inline or top-level comment returned by GitHub REST."""

    id: int = Field(gt=0)
    html_url: str | None = None


class GitHubResolvedThread(GitHubMutationModel):
    """Thread state returned by resolveReviewThread."""

    isResolved: bool


class GitHubResolveReviewThread(GitHubMutationModel):
    """GraphQL mutation payload wrapper."""

    thread: GitHubResolvedThread


class GitHubResolveData(GitHubMutationModel):
    """GraphQL data wrapper."""

    resolveReviewThread: GitHubResolveReviewThread


class GitHubResolveResponse(GitHubMutationModel):
    """Successful resolveReviewThread response; errors are rejected before validation."""

    data: GitHubResolveData

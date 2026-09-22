"""Strict GitHub GraphQL and REST ingress models."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class GitHubResponseModel(BaseModel):
    """Reject producer-shape coercion at GitHub ingress."""

    model_config = ConfigDict(strict=True)


GitHubTimestamp = Annotated[datetime, Field(strict=False)]


class Author(GitHubResponseModel):
    """GitHub account identity."""

    login: str


class RepoIdentity(GitHubResponseModel):
    """Repository identity returned by gh repo view."""

    nameWithOwner: str


class CommentNode(GitHubResponseModel):
    """One inline review comment."""

    databaseId: int
    body: str
    line: int | None
    originalLine: int | None
    author: Author | None
    id: str | None = None
    createdAt: GitHubTimestamp | None = None
    updatedAt: GitHubTimestamp | None = None
    url: str | None = None


class PageInfo(GitHubResponseModel):
    """Pagination state for one GraphQL connection."""

    hasNextPage: bool


class CommentsConnection(GitHubResponseModel):
    """Fetched page of comments nested under a review thread."""

    totalCount: int
    pageInfo: PageInfo
    nodes: list[CommentNode]


class ReviewThreadNode(GitHubResponseModel):
    """One GitHub review thread."""

    id: str
    isResolved: bool
    path: str
    comments: CommentsConnection


class ReviewThreadsConnection(GitHubResponseModel):
    """One fetched page of review threads."""

    totalCount: int
    nodes: list[ReviewThreadNode]


class ReviewNode(GitHubResponseModel):
    """One submitted or pending top-level review."""

    id: str
    author: Author | None
    state: str
    body: str
    submittedAt: GitHubTimestamp | None
    lastEditedAt: GitHubTimestamp | None
    url: str


class ReviewsConnection(GitHubResponseModel):
    """One fetched page of top-level reviews."""

    totalCount: int
    nodes: list[ReviewNode]


class IssueComment(GitHubResponseModel):
    """One PR-level issue comment."""

    created_at: GitHubTimestamp
    user: Author | None
    body: str
    id: int | None = None
    html_url: str | None = None
    updated_at: GitHubTimestamp | None = None


class Reaction(GitHubResponseModel):
    """One reaction on the pull request."""

    content: str
    user: Author | None
    created_at: GitHubTimestamp
    id: int | None = None


class GitHubCommitDate(GitHubResponseModel):
    """Current head commit identity and date."""

    committedDate: GitHubTimestamp
    oid: str | None = None


class HeadCommitNode(GitHubResponseModel):
    """GraphQL commit connection node."""

    commit: GitHubCommitDate


class HeadCommitsConnection(GitHubResponseModel):
    """Tail of the pull request commit connection."""

    nodes: list[HeadCommitNode]


class PullRequestHeadState(GitHubResponseModel):
    """Head revision and reviewability fields."""

    isDraft: bool
    mergeable: str
    mergeStateStatus: str
    commits: HeadCommitsConnection


class ForcePushEvent(GitHubResponseModel):
    """Server-observed head force-push event."""

    createdAt: GitHubTimestamp

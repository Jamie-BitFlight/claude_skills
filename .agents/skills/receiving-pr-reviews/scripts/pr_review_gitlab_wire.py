"""Strict GitLab merge-request API boundary models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class GitLabWireModel(BaseModel):
    """Require exact declared types while tolerating additive API fields."""

    model_config = ConfigDict(extra="ignore", strict=True)


class GitLabUser(GitLabWireModel):
    """GitLab user fields used by review normalization."""

    id: int
    username: str = Field(min_length=1)
    name: str | None = None
    bot: bool | None = None


class GitLabPosition(GitLabWireModel):
    """Optional diff position attached to a discussion note."""

    head_sha: str | None = None
    new_path: str | None = None
    old_path: str | None = None
    new_line: int | None = None
    old_line: int | None = None


class GitLabNote(GitLabWireModel):
    """One atomic merge-request note."""

    id: int
    body: str
    author: GitLabUser
    created_at: datetime
    updated_at: datetime
    system: bool
    resolvable: bool
    resolved: bool | None = None
    resolved_by: GitLabUser | None = None
    type: str | None = None
    position: GitLabPosition | None = None


class GitLabDiscussion(GitLabWireModel):
    """One merge-request discussion and its complete note sequence."""

    id: str = Field(min_length=1)
    individual_note: bool
    notes: list[GitLabNote] = Field(min_length=1)


class GitLabMergeRequest(GitLabWireModel):
    """Merge-request identity, revision, and reviewability fields."""

    iid: int = Field(gt=0)
    sha: str = Field(min_length=1)
    web_url: str = Field(min_length=1)
    state: str
    draft: bool
    work_in_progress: bool
    has_conflicts: bool
    merge_status: str
    detailed_merge_status: str
    blocking_discussions_resolved: bool
    author: GitLabUser


class GitLabDiffVersion(GitLabWireModel):
    """Server-observed merge-request diff revision."""

    id: int
    head_commit_sha: str = Field(min_length=1)
    base_commit_sha: str = Field(min_length=1)
    start_commit_sha: str = Field(min_length=1)
    created_at: datetime


class GitLabApprovedBy(GitLabWireModel):
    """One named merge-request approver."""

    user: GitLabUser


class GitLabApprovals(GitLabWireModel):
    """GitLab approval state without interpreting zero-required as approval."""

    approved: bool
    approvals_required: int = Field(ge=0)
    approvals_left: int = Field(ge=0)
    approved_by: list[GitLabApprovedBy]
    approval_rules_left: list[object] = Field(default_factory=list)


class GitLabAwardEmoji(GitLabWireModel):
    """One named merge-request award signal."""

    id: int
    name: str = Field(min_length=1)
    user: GitLabUser
    created_at: datetime
    updated_at: datetime


class GitLabState(BaseModel):
    """Every required GitLab surface fetched through one transport."""

    merge_request: GitLabMergeRequest
    discussions: list[GitLabDiscussion]
    notes: list[GitLabNote]
    approvals: GitLabApprovals
    awards: list[GitLabAwardEmoji]
    versions: list[GitLabDiffVersion] = Field(min_length=1)
    current_user: GitLabUser


class GitLabCreatedNote(GitLabWireModel):
    """Mutation response proving a note was created."""

    id: int
    body: str

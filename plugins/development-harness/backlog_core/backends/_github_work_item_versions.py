"""Authenticated logical heads and audit comments for GitHub work items."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from backlog_core.backend_types import IssueCommentNode
from backlog_core.models import ContentKind, ContentRef, ContentUnavailableError

_TAG_PREFIX = "<!-- dh-work-item-version "
_TAG_SUFFIX = " -->"


class _CommentMetadata(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)

    version: Literal[1]
    parent_revision: str = Field(min_length=1)
    digest: str = Field(pattern=r"^[0-9a-f]{64}$")


class WorkItemHead(BaseModel):
    """Contents-CAS authority for one GitHub Issue's rendered work-item body."""

    model_config = ConfigDict(frozen=True, strict=True)

    version: Literal[1] = 1
    issue_reference: str = Field(min_length=2)
    parent_revision: str = Field(min_length=1)
    root_revision: str = Field(min_length=1)
    body: str
    digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    comment_id: str = Field(min_length=1)

    @classmethod
    def create(
        cls, issue_reference: str, parent_revision: str, root_revision: str, body: str, comment_id: str
    ) -> WorkItemHead:
        """Create an authenticated logical head for a successful Contents update.

        Returns:
            Authenticated logical head.
        """
        return cls(
            issue_reference=issue_reference,
            parent_revision=parent_revision,
            root_revision=root_revision,
            body=body,
            digest=_body_digest(body),
            comment_id=comment_id,
        )

    @model_validator(mode="after")
    def _verify_digest(self) -> WorkItemHead:
        if self.digest != _body_digest(self.body):
            raise ValueError("work-item head digest is invalid")
        return self


class WorkItemVersion(BaseModel):
    """Resolved rendered body with its opaque provider revision."""

    model_config = ConfigDict(frozen=True, strict=True)

    revision: str = Field(min_length=1)
    body: str


def root_revision(issue_reference: str, issue_node_id: str, issue_body: str) -> str:
    """Return the Issue-identity-bound canonical root revision for a human body."""
    return _body_digest(
        json.dumps(
            {"body": issue_body, "issue_node_id": issue_node_id, "issue_reference": issue_reference},
            separators=(",", ":"),
        )
    )


def work_item_head_ref(issue_reference: str) -> ContentRef:
    """Return the provider-private Contents identity for an Issue's authoritative head."""
    return ContentRef(
        kind=ContentKind.ARTIFACT_CONTENT, namespace=issue_reference, artifact_type="_dh-work-item-head-v1", name="head"
    )


def render_work_item_comment(parent_revision: str, body: str) -> str:
    """Return the validated audit comment for a prospective Contents head."""
    metadata = _CommentMetadata(version=1, parent_revision=parent_revision, digest=_body_digest(body))
    return (
        f"{_TAG_PREFIX}{json.dumps(metadata.model_dump(), separators=(',', ':'), sort_keys=True)}{_TAG_SUFFIX}\n{body}"
    )


def parse_work_item_comment(head: WorkItemHead, comment: IssueCommentNode | None) -> str:
    """Validate that the remote audit comment exactly projects an authoritative head.

    Returns:
        The audited rendered body.
    """
    if comment is None:
        raise ContentUnavailableError("GitHub work-item audit comment is missing")
    if comment["id"] != head.comment_id:
        raise ContentUnavailableError("GitHub work-item audit comment identity is invalid")
    header, separator, body = comment["body"].partition("\n")
    if not separator or not header.startswith(_TAG_PREFIX) or not header.endswith(_TAG_SUFFIX):
        raise ContentUnavailableError("GitHub work-item audit comment is invalid")
    try:
        metadata = _CommentMetadata.model_validate_json(header.removeprefix(_TAG_PREFIX).removesuffix(_TAG_SUFFIX))
    except ValidationError as exc:
        raise ContentUnavailableError("GitHub work-item audit comment is invalid") from exc
    if metadata.parent_revision != head.parent_revision or metadata.digest != head.digest or body != head.body:
        raise ContentUnavailableError("GitHub work-item audit comment is invalid")
    return body


def parse_work_item_head(content: str) -> WorkItemHead:
    """Parse a Contents-head envelope or fail closed on malformed authority data.

    Returns:
        Validated logical head.
    """
    try:
        return WorkItemHead.model_validate_json(content)
    except ValidationError as exc:
        raise ContentUnavailableError("GitHub work-item head is invalid") from exc


def _body_digest(body: str) -> str:
    return hashlib.sha256(body.encode()).hexdigest()

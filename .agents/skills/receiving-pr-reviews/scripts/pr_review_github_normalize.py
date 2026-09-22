"""Normalize GitHub review objects into canonical provider-neutral inputs."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from datetime import datetime

from pr_review_contracts import ChangeRequestTarget
from pr_review_models import IssueComment, Reaction, ReviewNode, UnresolvedThread
from pr_review_state_models import (
    ReviewActor,
    ReviewCapabilities,
    ReviewInput,
    SnapshotCompleteness,
    calculate_snapshot_fingerprint,
)


def actor(login: str | None, *, own_login: str) -> ReviewActor:
    """Normalize one GitHub login.

    Returns:
        The canonical actor.
    """
    classification = "bot" if login and (login.endswith("[bot]") or "bot" in login.lower()) else "human"
    if login is None:
        classification = "unknown"
    role = "author" if login == own_login else "reviewer"
    return ReviewActor(actor_id=login, login=login, classification=classification, role=role)


def inline_inputs(
    target: ChangeRequestTarget, unresolved: list[UnresolvedThread], *, own_login: str
) -> list[ReviewInput]:
    """Normalize every fetched inline comment atomically.

    Returns:
        Canonical inline inputs in provider order.
    """
    inputs: list[ReviewInput] = []
    for thread in unresolved:
        opening_id = thread.comments[0].databaseId if thread.comments else None
        parent_id = f"github:review-comment:{opening_id}" if opening_id is not None else None
        for index, comment in enumerate(thread.comments):
            input_id = f"github:review-comment:{comment.databaseId}"
            login = comment.author.login if comment.author is not None else None
            stable_reference = comment.url or (
                f"https://github.com/{target.repository.full_name}/pull/{target.number}#discussion_r{comment.databaseId}"
            )
            inputs.append(
                ReviewInput(
                    input_id=input_id,
                    provider="github",
                    provider_ids={
                        "thread_id": thread.id,
                        "comment_id": str(comment.databaseId),
                        "opening_comment_id": str(opening_id or comment.databaseId),
                    },
                    source_kind="review_comment",
                    kinds={"comment"},
                    location="inline",
                    direction="outbound" if login == own_login else "inbound",
                    actor=actor(login, own_login=own_login),
                    body=comment.body,
                    stable_reference=stable_reference,
                    created_at=comment.createdAt,
                    updated_at=comment.updatedAt,
                    revision_relation="unknown",
                    path=thread.path,
                    line=comment.line if comment.line is not None else comment.originalLine,
                    provider_state="open",
                    capabilities=ReviewCapabilities(can_reply=True, can_resolve=True, unavailable=[]),
                    thread_id=thread.id,
                    parent_id=None if index == 0 else parent_id,
                )
            )
    return inputs


def review_inputs(
    reviews: list[ReviewNode], *, own_login: str, is_empty_codex: Callable[[ReviewNode], bool]
) -> list[ReviewInput]:
    """Normalize submitted review bodies, approvals, and rejections.

    Returns:
        Canonical top-level review inputs, including empty-body state signals.
    """
    inputs: list[ReviewInput] = []
    for review in reviews:
        if review.submittedAt is None or is_empty_codex(review):
            continue
        kinds: set[str] = set()
        if review.body.strip():
            kinds.add("comment")
        if review.state == "APPROVED":
            kinds.add("approval")
        if review.state == "CHANGES_REQUESTED":
            kinds.add("rejection")
        if not kinds:
            continue
        login = review.author.login if review.author is not None else None
        inputs.append(
            ReviewInput.model_validate({
                "input_id": f"github:review:{review.id}",
                "provider": "github",
                "provider_ids": {"review_id": review.id},
                "source_kind": "review",
                "kinds": kinds,
                "location": "top_level",
                "direction": "outbound" if login == own_login else "inbound",
                "actor": actor(login, own_login=own_login),
                "body": review.body,
                "stable_reference": review.url,
                "created_at": review.submittedAt,
                "updated_at": review.lastEditedAt,
                "revision_relation": "unknown",
                "path": None,
                "line": None,
                "provider_state": review.state,
                "capabilities": ReviewCapabilities(can_reply=True, can_resolve=False, unavailable=["resolve"]),
                "thread_id": None,
                "parent_id": None,
            })
        )
    return inputs


def issue_comment_inputs(
    target: ChangeRequestTarget, comments: list[IssueComment], *, own_login: str
) -> list[ReviewInput]:
    """Normalize PR-level comments as atomic communication or review inputs.

    Returns:
        Canonical top-level comment inputs.
    """
    inputs = []
    for index, comment in enumerate(comments):
        identity = (
            str(comment.id)
            if comment.id is not None
            else hashlib.sha256(f"{comment.created_at.isoformat()}:{index}:{comment.body}".encode()).hexdigest()
        )
        login = comment.user.login if comment.user is not None else None
        inputs.append(
            ReviewInput(
                input_id=f"github:issue-comment:{identity}",
                provider="github",
                provider_ids={"issue_comment_id": identity},
                source_kind="issue_comment",
                kinds={"comment"},
                location="top_level",
                direction="outbound" if login == own_login else "inbound",
                actor=actor(login, own_login=own_login),
                body=comment.body,
                stable_reference=comment.html_url
                or f"https://github.com/{target.repository.full_name}/pull/{target.number}#issuecomment-{identity}",
                created_at=comment.created_at,
                updated_at=comment.updated_at,
                revision_relation="unknown",
                path=None,
                line=None,
                provider_state="posted",
                capabilities=ReviewCapabilities(can_reply=True, can_resolve=False, unavailable=["resolve"]),
                thread_id=None,
                parent_id=None,
            )
        )
    return inputs


def approval_inputs(
    target: ChangeRequestTarget,
    reactions: list[Reaction],
    *,
    revision_at: datetime,
    is_codex_approval: Callable[[Reaction], bool],
) -> list[ReviewInput]:
    """Normalize exact current-revision Codex approval reactions.

    Returns:
        Canonical approval inputs.
    """
    inputs = []
    for index, reaction in enumerate(reactions):
        if not is_codex_approval(reaction) or reaction.created_at < revision_at:
            continue
        identity = str(reaction.id) if reaction.id is not None else f"{int(reaction.created_at.timestamp())}-{index}"
        login = reaction.user.login if reaction.user is not None else None
        inputs.append(
            ReviewInput(
                input_id=f"github:reaction:{identity}",
                provider="github",
                provider_ids={"reaction_id": identity},
                source_kind="reaction",
                kinds={"approval"},
                location="top_level",
                direction="inbound",
                actor=actor(login, own_login=""),
                body="+1",
                stable_reference=f"https://github.com/{target.repository.full_name}/pull/{target.number}",
                created_at=reaction.created_at,
                updated_at=None,
                revision_relation="current",
                path=None,
                line=None,
                provider_state="approved",
                capabilities=ReviewCapabilities(can_reply=False, can_resolve=False, unavailable=["reply", "resolve"]),
                thread_id=None,
                parent_id=None,
            )
        )
    return inputs


def fingerprint(
    target: ChangeRequestTarget, revision: str, review_inputs: list[ReviewInput], completeness: SnapshotCompleteness
) -> str:
    """Hash the complete normalized snapshot identity.

    Returns:
        A stable SHA-256 fingerprint.
    """
    return calculate_snapshot_fingerprint(target, revision, review_inputs, completeness)

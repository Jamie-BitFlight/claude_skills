"""Normalize GitHub review objects into canonical provider-neutral inputs."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from datetime import datetime
from typing import Literal

from pr_review_contracts import ChangeRequestTarget
from pr_review_gh_wire import ReviewThreadNode
from pr_review_models import Author, IssueComment, Reaction, Reviewability, ReviewNode, ReviewProviderMetadata
from pr_review_provider_text import reference_present
from pr_review_state_models import (
    ProviderInputIdentity,
    ReviewActor,
    ReviewCapabilities,
    ReviewInput,
    SnapshotCompleteness,
    calculate_snapshot_fingerprint,
)


def actor(
    author: Author | None, *, pull_author_login: str | None, observed_role: Literal["reviewer", "stakeholder"] | None
) -> ReviewActor:
    """Normalize only provider-observed actor facts.

    Args:
        author: GitHub actor payload, including its provider-reported account type.
        pull_author_login: Provider-reported change-request author login.
        observed_role: Role established by the source surface, if any.

    Returns:
        The canonical actor.
    """
    login = author.login if author is not None else None
    account_type = (author.type or author.node_type) if author is not None else None
    classification: Literal["human", "bot", "unknown"] = "unknown"
    if account_type == "Bot":
        classification = "bot"
    elif account_type == "User":
        classification = "human"
    role: Literal["reviewer", "stakeholder", "author", "unknown"]
    if login is not None and login == pull_author_login:
        role = "author"
    elif observed_role in {"reviewer", "stakeholder"}:
        role = observed_role
    else:
        role = "unknown"
    return ReviewActor(actor_id=login, login=login, classification=classification, role=role)


def revision_relation(commit_oid: str | None, head_revision: str) -> Literal["current", "stale", "unknown"]:
    """Compare an observed review commit with the sampled head.

    Args:
        commit_oid: Provider-reported commit identity, when the surface exposes one.
        head_revision: Current sampled remote head.

    Returns:
        ``current``, ``stale``, or ``unknown`` from observed evidence only.
    """
    if commit_oid is None:
        return "unknown"
    return "current" if commit_oid == head_revision else "stale"


def inline_inputs(
    target: ChangeRequestTarget,
    threads: list[ReviewThreadNode],
    *,
    own_login: str,
    pull_author_login: str | None,
    head_revision: str,
) -> list[ReviewInput]:
    """Normalize every fetched inline comment, including resolved history.

    Args:
        target: Canonical change-request target.
        threads: Every fetched review thread, regardless of resolution state.
        own_login: Authenticated GitHub login.
        pull_author_login: Provider-reported pull-request author.
        head_revision: Current sampled remote head.

    Returns:
        Canonical inline inputs in provider order.
    """
    inputs: list[ReviewInput] = []
    for thread in threads:
        opening_id = thread.comments.nodes[0].databaseId if thread.comments.nodes else None
        parent_id = f"github:review-comment:{opening_id}" if opening_id is not None else None
        for index, comment in enumerate(thread.comments.nodes):
            input_id = f"github:review-comment:{comment.databaseId}"
            login = comment.author.login if comment.author is not None else None
            stable_reference = comment.url or (
                f"https://github.com/{target.repository.full_name}/pull/{target.number}#discussion_r{comment.databaseId}"
            )
            inputs.append(
                ReviewInput(
                    input_id=input_id,
                    provider="github",
                    provider_ids=ProviderInputIdentity(
                        object_id=str(comment.databaseId),
                        reply_target_id=str(opening_id or comment.databaseId),
                        resolution_target_id=thread.id,
                    ),
                    source_kind="review_comment",
                    kinds={"comment"},
                    location="inline",
                    direction="outbound" if login == own_login else "inbound",
                    actor=actor(
                        comment.author,
                        pull_author_login=pull_author_login,
                        observed_role="reviewer" if index == 0 else None,
                    ),
                    body=comment.body,
                    stable_reference=stable_reference,
                    created_at=comment.createdAt,
                    updated_at=comment.updatedAt,
                    revision_relation=revision_relation(
                        comment.commit.oid if comment.commit is not None else None, head_revision
                    ),
                    path=thread.path,
                    line=comment.line if comment.line is not None else comment.originalLine,
                    provider_state="resolved" if thread.isResolved else "open",
                    capabilities=ReviewCapabilities(
                        can_reply=True,
                        can_resolve=not thread.isResolved,
                        can_comment=True,
                        unavailable=["resolve"] if thread.isResolved else [],
                    ),
                    thread_id=thread.id,
                    parent_id=None if index == 0 else parent_id,
                )
            )
    return inputs


def review_inputs(
    reviews: list[ReviewNode],
    *,
    own_login: str,
    pull_author_login: str | None,
    head_revision: str,
    is_empty_codex: Callable[[ReviewNode], bool],
) -> list[ReviewInput]:
    """Normalize submitted review bodies, approvals, and rejections.

    Args:
        reviews: Every fetched submitted review.
        own_login: Authenticated GitHub login used to determine direction.
        pull_author_login: Provider-reported pull-request author.
        head_revision: Current sampled remote head.
        is_empty_codex: Exact predicate for Codex's no-findings template.

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
                "provider_ids": ProviderInputIdentity(object_id=review.id),
                "source_kind": "review",
                "kinds": kinds,
                "location": "top_level",
                "direction": "outbound" if login == own_login else "inbound",
                "actor": actor(review.author, pull_author_login=pull_author_login, observed_role="reviewer"),
                "body": review.body,
                "stable_reference": review.url,
                "created_at": review.submittedAt,
                "updated_at": review.lastEditedAt,
                "revision_relation": revision_relation(
                    review.commit.oid if review.commit is not None else None, head_revision
                ),
                "path": None,
                "line": None,
                "provider_state": review.state,
                "capabilities": ReviewCapabilities(
                    can_reply=False, can_resolve=False, can_comment=True, unavailable=["reply", "resolve"]
                ),
                "thread_id": None,
                "parent_id": None,
            })
        )
    return inputs


def issue_comment_inputs(
    target: ChangeRequestTarget, comments: list[IssueComment], *, own_login: str, pull_author_login: str | None
) -> list[ReviewInput]:
    """Normalize PR-level comments as atomic communication or review inputs.

    Args:
        target: Canonical change-request target.
        comments: Every fetched issue comment.
        own_login: Authenticated GitHub login used to determine direction.
        pull_author_login: Provider-reported pull-request author.

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
                provider_ids=ProviderInputIdentity(object_id=identity),
                source_kind="issue_comment",
                kinds={"comment"},
                location="top_level",
                direction="outbound" if login == own_login else "inbound",
                actor=actor(comment.user, pull_author_login=pull_author_login, observed_role=None),
                body=comment.body,
                stable_reference=comment.html_url
                or f"https://github.com/{target.repository.full_name}/pull/{target.number}#issuecomment-{identity}",
                created_at=comment.created_at,
                updated_at=comment.updated_at,
                revision_relation="unknown",
                path=None,
                line=None,
                provider_state="posted",
                capabilities=ReviewCapabilities(
                    can_reply=False, can_resolve=False, can_comment=True, unavailable=["reply", "resolve"]
                ),
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
    pull_author_login: str | None,
    is_codex_approval: Callable[[Reaction], bool],
) -> list[ReviewInput]:
    """Normalize exact current-revision Codex approval reactions.

    Args:
        target: Canonical change-request target.
        reactions: Every fetched pull-request reaction.
        revision_at: Timestamp establishing current-revision approval equivalence.
        pull_author_login: Provider-reported pull-request author.
        is_codex_approval: Exact predicate for the supported Codex approval signal.

    Returns:
        Canonical approval inputs.
    """
    inputs = []
    for index, reaction in enumerate(reactions):
        if not is_codex_approval(reaction) or reaction.created_at < revision_at:
            continue
        identity = str(reaction.id) if reaction.id is not None else f"{int(reaction.created_at.timestamp())}-{index}"
        inputs.append(
            ReviewInput(
                input_id=f"github:reaction:{identity}",
                provider="github",
                provider_ids=ProviderInputIdentity(object_id=identity),
                source_kind="reaction",
                kinds={"approval"},
                location="top_level",
                direction="inbound",
                actor=actor(reaction.user, pull_author_login=pull_author_login, observed_role=None),
                body="+1",
                stable_reference=f"https://github.com/{target.repository.full_name}/pull/{target.number}",
                created_at=reaction.created_at,
                updated_at=None,
                revision_relation="current",
                path=None,
                line=None,
                provider_state="approved",
                capabilities=ReviewCapabilities(
                    can_reply=False, can_resolve=False, can_comment=True, unavailable=["reply", "resolve"]
                ),
                thread_id=None,
                parent_id=None,
            )
        )
    return inputs


def fingerprint(
    target: ChangeRequestTarget,
    revision: str,
    review_inputs: list[ReviewInput],
    completeness: SnapshotCompleteness,
    *,
    revision_at: datetime | None = None,
    reviewability: Reviewability | None = None,
    provider_metadata: ReviewProviderMetadata | None = None,
    communicated_input_ids: set[str] | None = None,
) -> str:
    """Hash the complete normalized snapshot identity.

    Args:
        target: Canonical change-request target.
        revision: Current sampled remote revision.
        review_inputs: Complete normalized input sequence.
        completeness: Evidence for every required provider surface.
        revision_at: Provider-observed current-revision timestamp.
        reviewability: Provider-normalized draft, merge, and blocker state.
        provider_metadata: Provider status retained outside the input census.
        communicated_input_ids: Inputs with provider-observed response evidence.

    Returns:
        A stable SHA-256 fingerprint.
    """
    return calculate_snapshot_fingerprint(
        target,
        revision,
        review_inputs,
        completeness,
        revision_at=revision_at,
        reviewability=reviewability,
        provider_metadata=provider_metadata,
        communicated_input_ids=communicated_input_ids,
    )


def communicated_inputs(inputs: list[ReviewInput]) -> set[str]:
    """Find inbound inputs answered by thread context or an exact stable reference.

    Args:
        inputs: Complete normalized GitHub input census.

    Returns:
        Canonical input IDs with provider-observed communication evidence.
    """
    outbound = [item for item in inputs if item.direction == "outbound"]
    return {
        item.input_id
        for item in inputs
        if item.direction == "inbound"
        and any(
            (item.thread_id is not None and response.thread_id == item.thread_id)
            or reference_present(response.body, item.stable_reference)
            for response in outbound
        )
    }

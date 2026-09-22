"""Canonical summary and compatibility output assembly."""

from __future__ import annotations

import typer

from pr_review_models import (
    ActionableReviewInput,
    BoardEntry,
    CommentSummary,
    FetchActionView,
    FetchResult,
    FetchSummary,
    ReviewNode,
    ReviewSnapshot,
    ReviewSummary,
    ThreadSummary,
    UnresolvedThread,
)
from pr_review_state_models import ReviewInput

TERMINAL_PROVIDER_STATES = {"closed", "dismissed", "resolved", "superseded"}


def review_input_is_actionable(item: ReviewInput, communicated_input_ids: set[str]) -> bool:
    """Return whether one canonical input belongs in the live action projection.

    Args:
        item: Canonical input to evaluate.
        communicated_input_ids: Inputs with provider-observed completed responses.

    Returns:
        True only for a current inbound input that still requires action.
    """
    return (
        item.direction == "inbound"
        and item.revision_relation != "stale"
        and item.input_id not in communicated_input_ids
        and item.provider_state.lower() not in TERMINAL_PROVIDER_STATES
    )


def truncate_body(body: str, max_body: int | None) -> str:
    """Return a caller-controlled compatibility body projection."""
    if max_body is None or len(body) <= max_body:
        return body
    return f"{body[:max_body]}...[truncated, showing {max_body}/{len(body)} chars]"


def summarize_thread(thread: UnresolvedThread, *, max_body: int | None) -> ThreadSummary:
    """Build the retained Python compatibility view for one review thread.

    Returns:
        Compatibility representation with caller-selected body bounds.
    """
    if not thread.comments:
        typer.echo(f"--summary: thread {thread.id} has no comments", err=True)
        raise typer.Exit(code=1)
    first = thread.comments[0]
    return ThreadSummary(
        thread_id=thread.id,
        comment_id=first.databaseId,
        path=thread.path,
        line=first.line if first.line is not None else first.originalLine,
        comment_count=len(thread.comments),
        comments_truncated=thread.comments_truncated,
        author=first.author.login if first.author is not None else None,
        body=truncate_body(first.body, max_body),
        replies=[
            CommentSummary(
                author=comment.author.login if comment.author is not None else None,
                body=truncate_body(comment.body, max_body),
            )
            for comment in thread.comments[1:]
        ],
    )


def summarize_review(review: ReviewNode, *, max_body: int | None) -> ReviewSummary:
    """Build the retained Python compatibility view for one review.

    Returns:
        Compatibility representation with caller-selected body bounds.
    """
    return ReviewSummary(
        author=review.author.login if review.author is not None else None,
        state=review.state,
        url=review.url,
        body=truncate_body(review.body, max_body),
    )


def actionable_inputs(result: ReviewSnapshot) -> list[ActionableReviewInput]:
    """Project only live inbound inputs that still require action.

    Args:
        result: Complete canonical snapshot retained for reconciliation.

    Returns:
        Full action content for current unresolved or unanswered inputs only.
    """
    actionable = [
        item for item in result.review_inputs if review_input_is_actionable(item, result.communicated_input_ids)
    ]
    return [
        ActionableReviewInput(
            input_id=item.input_id,
            provider_ids=item.provider_ids,
            source_kind=item.source_kind,
            kinds=sorted(item.kinds),
            location=item.location,
            actor=item.actor,
            body=item.body,
            stable_reference=item.stable_reference,
            revision_relation=item.revision_relation,
            path=item.path,
            line=item.line,
            provider_state=item.provider_state,
            capabilities=item.capabilities,
            thread_id=item.thread_id,
            parent_id=item.parent_id,
        )
        for item in actionable
    ]


def summarize(result: ReviewSnapshot, *, pr: int, new_input: bool | None = None) -> FetchSummary:
    """Build the metadata-only next-action dashboard.

    Args:
        result: Complete canonical snapshot.
        pr: Pull-request number included in compact output.
        new_input: Whether this observation contains a new-input signal.

    Returns:
        The bounded dashboard projection.
    """
    reviewability = result.reviewability
    if reviewability is None:
        message = "summary output requires provider reviewability data"
        raise ValueError(message)
    outstanding_inputs = [
        item for item in result.review_inputs if review_input_is_actionable(item, result.communicated_input_ids)
    ]
    unanswered_threads = {item.thread_id for item in outstanding_inputs if item.location == "inline"}
    unanswered_inputs = [item for item in outstanding_inputs if item.location == "top_level"]
    approval_state = result.provider_metadata.approval_state
    return FetchSummary(
        pr=pr,
        provider=result.provider,
        snapshot_complete=result.snapshot_complete,
        cycle_state=result.cycle_state,
        unresolved_code_thread_count=len(unanswered_threads) if result.review_inputs else result.unresolved_count,
        unanswered_input_count=len(unanswered_inputs) if result.review_inputs else len(result.unresponded_reviews),
        approval_count=sum("approval" in item.kinds for item in outstanding_inputs),
        rejection_count=sum("rejection" in item.kinds for item in outstanding_inputs),
        codex_approved=result.codex_approved,
        provider_approved=approval_state.approved if approval_state is not None else None,
        approvals_required=approval_state.approvals_required if approval_state is not None else None,
        approvals_left=approval_state.approvals_left if approval_state is not None else None,
        assigned_reviewer_count=(
            len(result.provider_metadata.assigned_reviewers)
            if result.provider_metadata.assigned_reviewers is not None
            else None
        ),
        requested_reviewer_count=(
            len(result.provider_metadata.requested_reviewers)
            if result.provider_metadata.requested_reviewers is not None
            else None
        ),
        is_draft=reviewability.is_draft,
        mergeable=reviewability.mergeable,
        merge_state_status=reviewability.merge_state_status,
        has_conflicts="conflict" in reviewability.mergeable.lower()
        or "conflict" in reviewability.merge_state_status.lower(),
        checks_state=result.provider_metadata.checks_state,
        new_input=(
            bool(outstanding_inputs)
            or result.unresolved_count > 0
            or bool(result.unresponded_reviews)
            or result.codex_approved is True
        )
        if new_input is None
        else new_input,
    )


def action_view(result: ReviewSnapshot, *, pr: int, new_input: bool | None = None) -> FetchActionView:
    """Build stdout output for current review work without replaying history.

    Args:
        result: Complete canonical snapshot retained for reconciliation.
        pr: Pull-request or merge-request number.
        new_input: Whether this observation contains a new-input signal.

    Returns:
        Dashboard state and complete content for live actionable inputs.
    """
    return FetchActionView(
        dashboard=summarize(result, pr=pr, new_input=new_input), actionable_inputs=actionable_inputs(result)
    )


def board_entry(pr: int, result: FetchResult | ReviewSnapshot) -> BoardEntry:
    """Build the retained Python compatibility status entry.

    Returns:
        Compatibility status for the selected request.
    """
    reviewability = result.reviewability
    if reviewability is None:
        raise ValueError("board output requires provider reviewability compatibility data")
    return BoardEntry(
        pr=pr,
        unresolved=result.unresolved_count,
        unresponded=len(result.unresponded_reviews),
        codex_approved=result.codex_approved,
        mergeable=reviewability.mergeable,
        merge_state_status=reviewability.merge_state_status,
        blockers=reviewability.blockers,
    )

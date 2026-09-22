"""Canonical summary and compatibility output assembly."""

from __future__ import annotations

import typer

from pr_review_models import (
    BoardEntry,
    CommentSummary,
    FetchResult,
    FetchSummary,
    ReviewNode,
    ReviewSnapshot,
    ReviewSummary,
    ThreadSummary,
    UnresolvedThread,
)


def truncate_body(body: str, max_body: int | None) -> str:
    """Apply caller-controlled visible truncation.

    Args:
        body: Complete provider body.
        max_body: Caller-selected character bound, or no truncation.

    Returns:
        Full or visibly truncated body text.
    """
    if max_body is None or len(body) <= max_body:
        return body
    return f"{body[:max_body]}...[truncated, showing {max_body}/{len(body)} chars]"


def summarize_thread(thread: UnresolvedThread, *, max_body: int | None) -> ThreadSummary:
    """Reduce one legacy unresolved thread without dropping replies.

    Args:
        thread: Complete unresolved-thread compatibility projection.
        max_body: Caller-selected character bound, or no truncation.

    Returns:
        The compatibility summary.
    """
    if not thread.comments:
        typer.echo(
            f"--summary: thread {thread.id} has no comments (unexpected API shape) -- "
            "re-run without --summary to inspect it directly.",
            err=True,
        )
        raise typer.Exit(code=1)
    first = thread.comments[0]
    replies = [
        CommentSummary(
            author=comment.author.login if comment.author is not None else None,
            body=truncate_body(comment.body, max_body),
        )
        for comment in thread.comments[1:]
    ]
    return ThreadSummary(
        thread_id=thread.id,
        comment_id=first.databaseId,
        path=thread.path,
        line=first.line if first.line is not None else first.originalLine,
        comment_count=len(thread.comments),
        comments_truncated=thread.comments_truncated,
        author=first.author.login if first.author is not None else None,
        body=truncate_body(first.body, max_body),
        replies=replies,
    )


def summarize_review(review: ReviewNode, *, max_body: int | None) -> ReviewSummary:
    """Reduce one unresponded top-level review.

    Args:
        review: Submitted review requiring a response.
        max_body: Caller-selected character bound, or no truncation.

    Returns:
        The compatibility summary.
    """
    return ReviewSummary(
        author=review.author.login if review.author is not None else None,
        state=review.state,
        url=review.url,
        body=truncate_body(review.body, max_body),
    )


def summarize(result: ReviewSnapshot, *, pr: int, max_body: int | None) -> FetchSummary:
    """Build canonical compact output plus legacy action fields.

    Args:
        result: Complete canonical snapshot.
        pr: Pull-request number included in compact output.
        max_body: Caller-selected character bound, or no truncation.

    Returns:
        The complete compact snapshot.
    """
    return FetchSummary(
        pr=pr,
        provider=result.provider,
        target=result.target,
        transport=result.transport,
        snapshot_complete=result.snapshot_complete,
        snapshot_fingerprint=result.snapshot_fingerprint,
        head_revision=result.head_revision,
        revision_at=result.revision_at,
        completeness=result.completeness,
        review_inputs=result.review_inputs,
        assessments=result.assessments,
        clusters=result.clusters,
        cycle_state=result.cycle_state,
        codex_approval_equivalence=result.codex_approval_equivalence,
        reviews_count=result.reviews_count,
        threads_count=result.threads_count,
        unresolved_count=result.unresolved_count,
        unresponded_count=len(result.unresponded_reviews),
        codex_approved=result.codex_approved,
        blockers=result.reviewability.blockers if result.reviewability is not None else [],
        unresolved=[summarize_thread(thread, max_body=max_body) for thread in result.unresolved],
        unresponded_reviews=[summarize_review(review, max_body=max_body) for review in result.unresponded_reviews],
    )


def board_entry(pr: int, result: FetchResult | ReviewSnapshot) -> BoardEntry:
    """Build one lightweight multi-PR compatibility entry.

    Args:
        pr: Pull-request number included in the board entry.
        result: GitHub compatibility snapshot.

    Returns:
        The compact board entry.
    """
    reviewability = result.reviewability
    if reviewability is None:
        message = "board output requires provider reviewability compatibility data"
        raise ValueError(message)
    return BoardEntry(
        pr=pr,
        unresolved=result.unresolved_count,
        unresponded=len(result.unresponded_reviews),
        codex_approved=result.codex_approved,
        mergeable=reviewability.mergeable,
        merge_state_status=reviewability.merge_state_status,
        blockers=reviewability.blockers,
    )

"""GitHub-specific reviewability, response matching, and Codex-signal rules."""

from __future__ import annotations

import re
from datetime import datetime

from pr_review_gh_wire import IssueComment, PullRequestHeadState, Reaction, ReviewNode
from pr_review_models import Reviewability

CODEX_REACTOR_LOGINS = frozenset({"chatgpt-codex-connector", "chatgpt-codex-connector[bot]"})
CODEX_EMPTY_REVIEW_FOOTER = (
    "<details> <summary>\u2139\ufe0f About Codex in GitHub</summary>\n<br/>\n\n"
    "[Your team has set up Codex to review pull requests in this repo]"
    "(https://chatgpt.com/codex/cloud/settings/general). Reviews are triggered when you\n"
    "- Open a pull request for review\n"
    "- Mark a draft as ready\n"
    '- Comment "@codex review".\n\n'
    "If Codex has suggestions, it will comment; otherwise it will react with 👍.\n\n\n\n\n"
    'Codex can also answer questions or update the PR. Try commenting "@codex address that feedback".\n            \n'
    "</details>"
)
CODEX_EMPTY_REVIEW_BODY = re.compile(
    r"### 💡 Codex Review\s*"
    r"Here are some automated review suggestions for this pull request\.\s*"
    r"\*\*Reviewed commit:\*\*\s*`[0-9a-f]+`\s*" + re.escape(CODEX_EMPTY_REVIEW_FOOTER)
)


def latest_revision_at(head_state: PullRequestHeadState, force_push_at: datetime | None) -> datetime:
    """Return the later head-commit or force-push timestamp."""
    head_date = head_state.commits.nodes[-1].commit.committedDate
    return max(head_date, force_push_at or head_date)


def reviewability(head_state: PullRequestHeadState) -> Reviewability:
    """Map GitHub draft/conflict state to established blockers.

    Returns:
        The normalized reviewability state.
    """
    blockers = []
    if head_state.isDraft:
        blockers.append("draft: reviewers are not requested until the PR is marked ready for review")
    if head_state.mergeable == "CONFLICTING":
        blockers.append("conflicting: reviews will not run until the merge conflicts are resolved")
    return Reviewability(
        is_draft=head_state.isDraft,
        mergeable=head_state.mergeable,
        merge_state_status=head_state.mergeStateStatus,
        blockers=blockers,
    )


def review_effective_timestamp(review: ReviewNode) -> datetime:
    """Return the newest submitted or edited review timestamp."""
    if review.submittedAt is None:
        raise TypeError("review_effective_timestamp requires a submitted review")
    return max(review.submittedAt, review.lastEditedAt or review.submittedAt)


def references_review(comment_body: str, review_url: str) -> bool:
    """Match the exact review URL without accepting a longer numeric id.

    Returns:
        Whether the comment references the exact review URL.
    """
    return re.search(re.escape(review_url) + r"(?!\d)", comment_body) is not None


def is_codex_empty_review(review: ReviewNode) -> bool:
    """Return whether a review is exactly Codex's fixed no-findings wrapper."""
    return (
        review.author is not None
        and review.author.login.lower() in CODEX_REACTOR_LOGINS
        and CODEX_EMPTY_REVIEW_BODY.fullmatch(review.body.strip()) is not None
    )


def unresponded_reviews(reviews: list[ReviewNode], own_comments: list[IssueComment]) -> list[ReviewNode]:
    """Return submitted, substantive reviews lacking a later exact-reference response."""
    return [
        review
        for review in reviews
        if review.submittedAt is not None
        and not is_codex_empty_review(review)
        and not any(
            references_review(comment.body, review.url) and comment.created_at >= review_effective_timestamp(review)
            for comment in own_comments
        )
    ]


def is_codex_thumbs_up(reaction: Reaction) -> bool:
    """Return whether the reaction is exact Codex +1 evidence."""
    return (
        reaction.content == "+1" and reaction.user is not None and reaction.user.login.lower() in CODEX_REACTOR_LOGINS
    )

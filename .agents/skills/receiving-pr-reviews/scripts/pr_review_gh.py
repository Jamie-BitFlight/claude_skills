"""GitHub snapshot facade preserving established helpers and output fields."""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import datetime

from pydantic import BaseModel

import pr_review_github_transport as transport
from pr_review_contracts import ChangeRequestTarget, RepositoryTarget
from pr_review_github_logic import (
    is_codex_empty_review as _is_codex_empty_review,
    is_codex_thumbs_up as _is_codex_thumbs_up,
    latest_revision_at as _latest_revision_at,
    references_review,
    reviewability as _reviewability,
    unresponded_reviews as _unresponded_reviews,
)
from pr_review_github_normalize import approval_inputs, fingerprint, inline_inputs, issue_comment_inputs, review_inputs
from pr_review_models import (
    FetchResult,
    IssueComment,
    PullRequestHeadState,
    Reaction,
    ReviewsConnection,
    ReviewSnapshot,
    ReviewThreadsConnection,
    UnresolvedThread,
)
from pr_review_state_models import SnapshotCompleteness
from pr_review_subprocess import DEFAULT_COMMAND_TIMEOUT_SECONDS

RESOLVE_THREAD_MUTATION = transport.RESOLVE_THREAD_MUTATION
run_gh = transport.run_gh


def detect_repo_identity(*, gh_timeout: float | None = None) -> tuple[str, str]:
    """Detect this checkout's GitHub owner and repository.

    Args:
        gh_timeout: Positive bound for repository detection.

    Returns:
        The repository owner and name.
    """
    return transport.detect_repo_identity(run_gh, timeout=gh_timeout)


def _fetch_pages(owner: str, repo: str, pr: int, *, gh_timeout: float | None) -> list[ReviewThreadsConnection]:
    return transport.fetch_thread_pages(run_gh, owner, repo, pr, timeout=gh_timeout)


def _fetch_review_pages(owner: str, repo: str, pr: int, *, gh_timeout: float | None) -> list[ReviewsConnection]:
    return transport.fetch_review_pages(run_gh, owner, repo, pr, timeout=gh_timeout)


def _fetch_issue_comments(owner: str, repo: str, pr: int, *, gh_timeout: float | None) -> list[IssueComment]:
    return transport.fetch_issue_comments(run_gh, owner, repo, pr, timeout=gh_timeout)


def _fetch_pr_reactions(owner: str, repo: str, pr: int, *, gh_timeout: float | None) -> list[Reaction]:
    return transport.fetch_reactions(run_gh, owner, repo, pr, timeout=gh_timeout)


def _fetch_authenticated_login(*, gh_timeout: float | None) -> str:
    return transport.fetch_login(run_gh, timeout=gh_timeout)


def _fetch_head_state(owner: str, repo: str, pr: int, *, gh_timeout: float | None) -> PullRequestHeadState:
    return transport.fetch_head_state(run_gh, owner, repo, pr, timeout=gh_timeout)


def _fetch_latest_force_push_at(owner: str, repo: str, pr: int, *, gh_timeout: float | None) -> datetime | None:
    return transport.fetch_force_push(run_gh, owner, repo, pr, timeout=gh_timeout)


def _references_review(comment_body: str, review_url: str) -> bool:
    return references_review(comment_body, review_url)


def gh_timeout_budget(deadline: float | None, gh_timeout: float | None) -> float:
    """Return the tighter caller timeout or remaining snapshot deadline.

    Args:
        deadline: Absolute monotonic deadline for the complete snapshot.
        gh_timeout: Caller-selected per-command timeout, or the default.

    Returns:
        The tighter remaining deadline or caller bound, using the 30-second default when omitted.
    """
    caller_timeout = DEFAULT_COMMAND_TIMEOUT_SECONDS if gh_timeout is None else gh_timeout
    if deadline is None:
        return caller_timeout
    remaining = max(0.0, deadline - time.monotonic())
    return min(remaining, caller_timeout)


class GitHubState(BaseModel):
    """Complete raw GitHub surfaces used to build one canonical snapshot."""

    thread_pages: list[ReviewThreadsConnection]
    review_pages: list[ReviewsConnection]
    issue_comments: list[IssueComment]
    reactions: list[Reaction]
    authenticated_login: str
    head_state: PullRequestHeadState
    force_push_at: datetime | None


def collect_state(owner: str, repo: str, pr: int, timeout: Callable[[], float | None]) -> GitHubState:
    """Fetch every required GitHub review surface through one timeout policy.

    Args:
        owner: GitHub repository owner.
        repo: GitHub repository name.
        pr: Pull-request number.
        timeout: Callable returning the current per-command timeout budget.

    Returns:
        Validated raw provider state.
    """
    return GitHubState(
        thread_pages=_fetch_pages(owner, repo, pr, gh_timeout=timeout()),
        review_pages=_fetch_review_pages(owner, repo, pr, gh_timeout=timeout()),
        issue_comments=_fetch_issue_comments(owner, repo, pr, gh_timeout=timeout()),
        reactions=_fetch_pr_reactions(owner, repo, pr, gh_timeout=timeout()),
        authenticated_login=_fetch_authenticated_login(gh_timeout=timeout()),
        head_state=_fetch_head_state(owner, repo, pr, gh_timeout=timeout()),
        force_push_at=_fetch_latest_force_push_at(owner, repo, pr, gh_timeout=timeout()),
    )


def normalize_state(fetched: GitHubState, target: ChangeRequestTarget) -> ReviewSnapshot:
    """Normalize complete GitHub state without discarding resolved history.

    Args:
        fetched: Every required raw provider surface.
        target: Canonical pull-request identity.

    Returns:
        A complete canonical snapshot with GitHub compatibility fields.
    """
    all_threads = [node for page in fetched.thread_pages for node in page.nodes]
    all_reviews = [node for page in fetched.review_pages for node in page.nodes]
    unresolved = [
        UnresolvedThread(
            id=node.id,
            path=node.path,
            comments=node.comments.nodes,
            comments_truncated=node.comments.pageInfo.hasNextPage,
        )
        for node in all_threads
        if not node.isResolved
    ]
    head_commit = fetched.head_state.commits.nodes[-1].commit
    head_revision = head_commit.oid or head_commit.committedDate.isoformat()
    pull_author_login = fetched.head_state.author.login if fetched.head_state.author is not None else None
    reviews_with_body = [review for review in all_reviews if review.body.strip()]
    own_comments = [
        comment
        for comment in fetched.issue_comments
        if comment.user is not None and comment.user.login == fetched.authenticated_login
    ]
    revision_at = _latest_revision_at(fetched.head_state, fetched.force_push_at)
    legacy = FetchResult(
        reviews_count=fetched.review_pages[0].totalCount,
        reviews_with_body=reviews_with_body,
        unresponded_reviews=_unresponded_reviews(reviews_with_body, own_comments),
        threads_count=fetched.thread_pages[0].totalCount,
        unresolved=unresolved,
        unresolved_count=len(unresolved),
        codex_approved=any(
            _is_codex_thumbs_up(reaction) and reaction.created_at >= revision_at for reaction in fetched.reactions
        ),
        reviewability=_reviewability(fetched.head_state),
    )
    canonical_inputs = [
        *inline_inputs(
            target,
            all_threads,
            own_login=fetched.authenticated_login,
            pull_author_login=pull_author_login,
            head_revision=head_revision,
        ),
        *review_inputs(
            all_reviews,
            own_login=fetched.authenticated_login,
            pull_author_login=pull_author_login,
            head_revision=head_revision,
            is_empty_codex=_is_codex_empty_review,
        ),
        *issue_comment_inputs(
            target, fetched.issue_comments, own_login=fetched.authenticated_login, pull_author_login=pull_author_login
        ),
        *approval_inputs(
            target,
            fetched.reactions,
            revision_at=revision_at,
            pull_author_login=pull_author_login,
            is_codex_approval=_is_codex_thumbs_up,
        ),
    ]
    truncated_threads = {thread.id for thread in all_threads if thread.comments.pageInfo.hasNextPage}
    surface_names = {"threads", "reviews", "issue_comments", "reactions", "identity", "head_state", "force_push"}
    completeness = SnapshotCompleteness(
        transport="github_cli",
        required_surfaces=surface_names,
        completed_surfaces=surface_names,
        truncated_input_ids=[item.input_id for item in canonical_inputs if item.thread_id in truncated_threads],
        unavailable_capabilities=[],
    )
    return ReviewSnapshot.model_validate({
        **legacy.model_dump(),
        "provider": "github",
        "target": target,
        "transport": "github_cli",
        "snapshot_complete": completeness.complete,
        "snapshot_fingerprint": fingerprint(target, head_revision, canonical_inputs, completeness),
        "head_revision": head_revision,
        "revision_at": revision_at,
        "completeness": completeness,
        "review_inputs": canonical_inputs,
        "assessments": [],
        "clusters": [],
        "cycle_state": "ASSESSMENT_REQUIRED" if completeness.complete else "SNAPSHOT_INCOMPLETE",
        "codex_approval_equivalence": "available",
    })


def build_fetch_result(
    owner: str,
    repo: str,
    pr: int,
    *,
    deadline: float | None = None,
    gh_timeout: float | None = None,
    target: ChangeRequestTarget | None = None,
) -> ReviewSnapshot:
    """Fetch, normalize, and fingerprint one GitHub review snapshot.

    Args:
        owner: GitHub repository owner.
        repo: GitHub repository name.
        pr: Pull-request number.
        deadline: Absolute monotonic deadline for the complete snapshot.
        gh_timeout: Caller-selected per-command timeout.
        target: Pre-resolved canonical target, when the caller has one.

    Returns:
        The canonical provider snapshot with legacy compatibility fields.
    """

    def timeout() -> float | None:
        return gh_timeout_budget(deadline, gh_timeout)

    resolved_target = target or ChangeRequestTarget(
        repository=RepositoryTarget(provider="github", hostname="github.com", full_name=f"{owner}/{repo}"), number=pr
    )
    return normalize_state(collect_state(owner, repo, pr, timeout), resolved_target)

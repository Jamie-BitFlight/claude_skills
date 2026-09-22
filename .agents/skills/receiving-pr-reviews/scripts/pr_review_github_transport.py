"""Bounded gh CLI transport and strict GitHub page validation."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime

from pydantic import TypeAdapter

from pr_review_gh_wire import (
    CommentsConnection,
    ForcePushEvent,
    IssueComment,
    PullRequestHeadState,
    Reaction,
    RepoIdentity,
    ReviewsConnection,
    ReviewThreadsConnection,
)
from pr_review_subprocess import run_capture

THREADS_QUERY = """
query($endCursor: String, $o: String!, $r: String!, $pr: Int!) {
  repository(owner: $o, name: $r) { pullRequest(number: $pr) {
    reviewThreads(first: 100, after: $endCursor) { totalCount pageInfo { hasNextPage endCursor }
      nodes { id isResolved path comments(first: 100) { totalCount pageInfo { hasNextPage }
        nodes { id databaseId body line originalLine createdAt updatedAt url
          commit { oid } author { login __typename } } } }
    }
  } }
}
"""
THREAD_COMMENTS_QUERY = """
query($endCursor: String, $threadId: ID!) {
  node(id: $threadId) { ... on PullRequestReviewThread {
    comments(first: 100, after: $endCursor) { totalCount pageInfo { hasNextPage endCursor }
      nodes { id databaseId body line originalLine createdAt updatedAt url
        commit { oid } author { login __typename } } }
  } }
}
"""
REVIEWS_QUERY = """
query($endCursor: String, $o: String!, $r: String!, $pr: Int!) {
  repository(owner: $o, name: $r) { pullRequest(number: $pr) {
    reviews(first: 100, after: $endCursor) { totalCount pageInfo { hasNextPage endCursor }
      nodes { id author { login __typename } state body submittedAt lastEditedAt url commit { oid } } }
  } }
}
"""
HEAD_QUERY = """
query($o: String!, $r: String!, $pr: Int!) {
  repository(owner: $o, name: $r) { pullRequest(number: $pr) {
    isDraft mergeable mergeStateStatus author { login __typename }
    commits(last: 1) { nodes { commit { oid committedDate statusCheckRollup { state } } } }
  } }
}
"""
FORCE_PUSH_QUERY = """
query($o: String!, $r: String!, $pr: Int!) {
  repository(owner: $o, name: $r) { pullRequest(number: $pr) {
    timelineItems(last: 1, itemTypes: [HEAD_REF_FORCE_PUSHED_EVENT]) {
      nodes { ... on HeadRefForcePushedEvent { createdAt } }
    }
  } }
}
"""
RESOLVE_THREAD_MUTATION = """
mutation($threadId: ID!) {
  resolveReviewThread(input: { threadId: $threadId }) { thread { isResolved } }
}
"""

GH = "gh"
Runner = Callable[..., str]
ISSUE_COMMENTS = TypeAdapter(list[IssueComment])
REACTIONS = TypeAdapter(list[Reaction])


def run_gh(args: list[str], *, timeout: float | None = None) -> str:
    """Run gh and capture stdout.

    Args:
        args: GitHub CLI arguments after the executable.
        timeout: Positive per-command bound; defaults to 30 seconds.

    Returns:
        The command's complete standard output.
    """
    return run_capture([GH, *args], timeout=timeout)


def detect_repo_identity(runner: Runner, *, timeout: float | None) -> tuple[str, str]:
    """Return the current checkout's owner and repository.

    Args:
        runner: Bounded GitHub command transport.
        timeout: Positive per-command bound.

    Returns:
        Repository owner and name.
    """
    identity = RepoIdentity.model_validate(
        json.loads(runner(["repo", "view", "--json", "nameWithOwner"], timeout=timeout))
    )
    owner, repo = identity.nameWithOwner.split("/", 1)
    return owner, repo


def fetch_thread_pages(
    runner: Runner, owner: str, repo: str, pr: int, *, timeout: float | None
) -> list[ReviewThreadsConnection]:
    """Fetch and validate all outer review-thread pages.

    Args:
        runner: Bounded GitHub command transport.
        owner: GitHub repository owner.
        repo: GitHub repository name.
        pr: Pull-request number.
        timeout: Positive per-command bound.

    Returns:
        Every validated page in provider order.
    """
    raw = runner(
        [
            "api",
            "graphql",
            "--paginate",
            "--slurp",
            "-f",
            f"query={THREADS_QUERY}",
            "-f",
            f"o={owner}",
            "-f",
            f"r={repo}",
            "-F",
            f"pr={pr}",
        ],
        timeout=timeout,
    )
    pages = [
        ReviewThreadsConnection.model_validate(page["data"]["repository"]["pullRequest"]["reviewThreads"])
        for page in json.loads(raw)
    ]
    completed_pages = []
    for page in pages:
        completed_nodes = []
        for thread in page.nodes:
            completed_thread = thread
            if thread.comments.pageInfo.hasNextPage:
                comment_pages = fetch_thread_comment_pages(runner, thread.id, timeout=timeout)
                comment_nodes = [comment for comment_page in comment_pages for comment in comment_page.nodes]
                authoritative_total = thread.comments.totalCount
                page_totals_agree = all(page.totalCount == authoritative_total for page in comment_pages)
                page_sequence_complete = all(page.pageInfo.hasNextPage for page in comment_pages[:-1]) and not (
                    comment_pages[-1].pageInfo.hasNextPage
                )
                unique_comment_count = len({comment.databaseId for comment in comment_nodes})
                if (
                    not page_totals_agree
                    or not page_sequence_complete
                    or len(comment_nodes) != authoritative_total
                    or unique_comment_count != authoritative_total
                ):
                    message = f"GitHub nested comment pagination for thread {thread.id!r} was incomplete"
                    raise ValueError(message)
                comments = thread.comments.model_copy(
                    update={
                        "totalCount": authoritative_total,
                        "nodes": comment_nodes,
                        "pageInfo": comment_pages[-1].pageInfo,
                    }
                )
                completed_thread = thread.model_copy(update={"comments": comments})
            completed_nodes.append(completed_thread)
        completed_pages.append(page.model_copy(update={"nodes": completed_nodes}))
    return completed_pages


def fetch_thread_comment_pages(runner: Runner, thread_id: str, *, timeout: float | None) -> list[CommentsConnection]:
    """Fetch every comment page for one truncated review thread.

    Args:
        runner: Bounded GitHub command transport.
        thread_id: GitHub review-thread node identity.
        timeout: Positive per-command bound.

    Returns:
        Every validated nested comment page in provider order.
    """
    raw = runner(
        [
            "api",
            "graphql",
            "--paginate",
            "--slurp",
            "-f",
            f"query={THREAD_COMMENTS_QUERY}",
            "-f",
            f"threadId={thread_id}",
        ],
        timeout=timeout,
    )
    pages = [CommentsConnection.model_validate(page["data"]["node"]["comments"]) for page in json.loads(raw)]
    if not pages:
        message = f"GitHub returned no comment pages for truncated thread {thread_id!r}"
        raise ValueError(message)
    return pages


def fetch_review_pages(
    runner: Runner, owner: str, repo: str, pr: int, *, timeout: float | None
) -> list[ReviewsConnection]:
    """Fetch and validate all top-level review pages.

    Args:
        runner: Bounded GitHub command transport.
        owner: GitHub repository owner.
        repo: GitHub repository name.
        pr: Pull-request number.
        timeout: Positive per-command bound.

    Returns:
        Every validated page in provider order.
    """
    raw = runner(
        [
            "api",
            "graphql",
            "--paginate",
            "--slurp",
            "-f",
            f"query={REVIEWS_QUERY}",
            "-f",
            f"o={owner}",
            "-f",
            f"r={repo}",
            "-F",
            f"pr={pr}",
        ],
        timeout=timeout,
    )
    return [
        ReviewsConnection.model_validate(page["data"]["repository"]["pullRequest"]["reviews"])
        for page in json.loads(raw)
    ]


def fetch_issue_comments(
    runner: Runner, owner: str, repo: str, pr: int, *, timeout: float | None
) -> list[IssueComment]:
    """Fetch and flatten every PR-level comment page.

    Args:
        runner: Bounded GitHub command transport.
        owner: GitHub repository owner.
        repo: GitHub repository name.
        pr: Pull-request number.
        timeout: Positive per-command bound.

    Returns:
        Every validated issue comment in provider order.
    """
    pages = json.loads(
        runner(["api", f"repos/{owner}/{repo}/issues/{pr}/comments", "--paginate", "--slurp"], timeout=timeout)
    )
    return [comment for page in pages for comment in ISSUE_COMMENTS.validate_python(page)]


def fetch_reactions(runner: Runner, owner: str, repo: str, pr: int, *, timeout: float | None) -> list[Reaction]:
    """Fetch and flatten every PR reaction page.

    Args:
        runner: Bounded GitHub command transport.
        owner: GitHub repository owner.
        repo: GitHub repository name.
        pr: Pull-request number.
        timeout: Positive per-command bound.

    Returns:
        Every validated reaction in provider order.
    """
    pages = json.loads(
        runner(["api", f"repos/{owner}/{repo}/issues/{pr}/reactions", "--paginate", "--slurp"], timeout=timeout)
    )
    return [reaction for page in pages for reaction in REACTIONS.validate_python(page)]


def fetch_login(runner: Runner, *, timeout: float | None) -> str:
    """Return the authenticated GitHub login.

    Args:
        runner: Bounded GitHub command transport.
        timeout: Positive per-command bound.

    Returns:
        Authenticated login.
    """
    return runner(["api", "user", "--jq", ".login"], timeout=timeout).strip()


def fetch_head_state(runner: Runner, owner: str, repo: str, pr: int, *, timeout: float | None) -> PullRequestHeadState:
    """Fetch current head identity and reviewability state.

    Args:
        runner: Bounded GitHub command transport.
        owner: GitHub repository owner.
        repo: GitHub repository name.
        pr: Pull-request number.
        timeout: Positive per-command bound.

    Returns:
        The validated pull-request head state.
    """
    raw = runner(
        ["api", "graphql", "-f", f"query={HEAD_QUERY}", "-f", f"o={owner}", "-f", f"r={repo}", "-F", f"pr={pr}"],
        timeout=timeout,
    )
    return PullRequestHeadState.model_validate(json.loads(raw)["data"]["repository"]["pullRequest"])


def fetch_force_push(runner: Runner, owner: str, repo: str, pr: int, *, timeout: float | None) -> datetime | None:
    """Return the newest server-recorded force-push timestamp.

    Args:
        runner: Bounded GitHub command transport.
        owner: GitHub repository owner.
        repo: GitHub repository name.
        pr: Pull-request number.
        timeout: Positive per-command bound.

    Returns:
        Latest force-push timestamp, or ``None`` when no event exists.
    """
    raw = runner(
        ["api", "graphql", "-f", f"query={FORCE_PUSH_QUERY}", "-f", f"o={owner}", "-f", f"r={repo}", "-F", f"pr={pr}"],
        timeout=timeout,
    )
    nodes = json.loads(raw)["data"]["repository"]["pullRequest"]["timelineItems"]["nodes"]
    events = [ForcePushEvent.model_validate(node) for node in nodes]
    return events[-1].createdAt if events else None

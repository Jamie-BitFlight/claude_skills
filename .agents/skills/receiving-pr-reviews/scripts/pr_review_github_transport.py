"""Bounded gh CLI transport and strict GitHub page validation."""

from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Callable
from datetime import datetime

from pydantic import TypeAdapter

from pr_review_gh_wire import (
    ForcePushEvent,
    IssueComment,
    PullRequestHeadState,
    Reaction,
    RepoIdentity,
    ReviewsConnection,
    ReviewThreadsConnection,
)

THREADS_QUERY = """
query($endCursor: String, $o: String!, $r: String!, $pr: Int!) {
  repository(owner: $o, name: $r) { pullRequest(number: $pr) {
    reviewThreads(first: 100, after: $endCursor) { totalCount pageInfo { hasNextPage endCursor }
      nodes { id isResolved path comments(first: 100) { totalCount pageInfo { hasNextPage }
        nodes { id databaseId body line originalLine createdAt updatedAt url author { login } } } }
    }
  } }
}
"""
REVIEWS_QUERY = """
query($endCursor: String, $o: String!, $r: String!, $pr: Int!) {
  repository(owner: $o, name: $r) { pullRequest(number: $pr) {
    reviews(first: 100, after: $endCursor) { totalCount pageInfo { hasNextPage endCursor }
      nodes { id author { login } state body submittedAt lastEditedAt url } }
  } }
}
"""
HEAD_QUERY = """
query($o: String!, $r: String!, $pr: Int!) {
  repository(owner: $o, name: $r) { pullRequest(number: $pr) {
    isDraft mergeable mergeStateStatus commits(last: 1) { nodes { commit { oid committedDate } } }
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

GH = shutil.which("gh") or "gh"
Runner = Callable[..., str]
ISSUE_COMMENTS = TypeAdapter(list[IssueComment])
REACTIONS = TypeAdapter(list[Reaction])


def run_gh(args: list[str], *, timeout: float | None = None) -> str:
    """Run gh and capture stdout.

    Returns:
        The command's complete standard output.
    """
    result = subprocess.run([GH, *args], stdout=subprocess.PIPE, text=True, timeout=timeout, check=True)
    return result.stdout


def detect_repo_identity(runner: Runner, *, timeout: float | None) -> tuple[str, str]:
    """Return the current checkout's owner and repository."""
    identity = RepoIdentity.model_validate(
        json.loads(runner(["repo", "view", "--json", "nameWithOwner"], timeout=timeout))
    )
    owner, repo = identity.nameWithOwner.split("/", 1)
    return owner, repo


def fetch_thread_pages(
    runner: Runner, owner: str, repo: str, pr: int, *, timeout: float | None
) -> list[ReviewThreadsConnection]:
    """Fetch and validate all outer review-thread pages.

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
    return [
        ReviewThreadsConnection.model_validate(page["data"]["repository"]["pullRequest"]["reviewThreads"])
        for page in json.loads(raw)
    ]


def fetch_review_pages(
    runner: Runner, owner: str, repo: str, pr: int, *, timeout: float | None
) -> list[ReviewsConnection]:
    """Fetch and validate all top-level review pages.

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

    Returns:
        Every validated issue comment in provider order.
    """
    pages = json.loads(
        runner(["api", f"repos/{owner}/{repo}/issues/{pr}/comments", "--paginate", "--slurp"], timeout=timeout)
    )
    return [comment for page in pages for comment in ISSUE_COMMENTS.validate_python(page)]


def fetch_reactions(runner: Runner, owner: str, repo: str, pr: int, *, timeout: float | None) -> list[Reaction]:
    """Fetch and flatten every PR reaction page.

    Returns:
        Every validated reaction in provider order.
    """
    pages = json.loads(
        runner(["api", f"repos/{owner}/{repo}/issues/{pr}/reactions", "--paginate", "--slurp"], timeout=timeout)
    )
    return [reaction for page in pages for reaction in REACTIONS.validate_python(page)]


def fetch_login(runner: Runner, *, timeout: float | None) -> str:
    """Return the authenticated GitHub login."""
    return runner(["api", "user", "--jq", ".login"], timeout=timeout).strip()


def fetch_head_state(runner: Runner, owner: str, repo: str, pr: int, *, timeout: float | None) -> PullRequestHeadState:
    """Fetch current head identity and reviewability state.

    Returns:
        The validated pull-request head state.
    """
    raw = runner(
        ["api", "graphql", "-f", f"query={HEAD_QUERY}", "-f", f"o={owner}", "-f", f"r={repo}", "-F", f"pr={pr}"],
        timeout=timeout,
    )
    return PullRequestHeadState.model_validate(json.loads(raw)["data"]["repository"]["pullRequest"])


def fetch_force_push(runner: Runner, owner: str, repo: str, pr: int, *, timeout: float | None) -> datetime | None:
    """Return the newest server-recorded force-push timestamp."""
    raw = runner(
        ["api", "graphql", "-f", f"query={FORCE_PUSH_QUERY}", "-f", f"o={owner}", "-f", f"r={repo}", "-F", f"pr={pr}"],
        timeout=timeout,
    )
    nodes = json.loads(raw)["data"]["repository"]["pullRequest"]["timelineItems"]["nodes"]
    events = [ForcePushEvent.model_validate(node) for node in nodes]
    return events[-1].createdAt if events else None

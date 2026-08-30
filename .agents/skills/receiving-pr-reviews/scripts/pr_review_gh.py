"""`gh`-backed GitHub I/O and result assembly for `pr_review_threads.py`.

Every function here shells out to `gh` (GitHub CLI) rather than talking to the GitHub API
directly, relying on `gh`'s own authentication. `build_fetch_result` is the one function the CLI
layer (`pr_review_threads.py`) calls directly — it composes the six independent `gh` calls below
into one `FetchResult` snapshot, fresh every time it runs. `run_gh` is exported too: the CLI
layer's `reply`/`resolve` commands call it directly for their own single-shot `gh` invocations.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import time
from datetime import datetime

from pydantic import TypeAdapter

from pr_review_models import (
    FetchResult,
    IssueComment,
    PullRequestCommit,
    Reaction,
    ReviewsConnection,
    ReviewThreadsConnection,
    UnresolvedThread,
)

_UNRESOLVED_THREADS_QUERY = """
query($endCursor: String, $o: String!, $r: String!, $pr: Int!) {
  repository(owner: $o, name: $r) {
    pullRequest(number: $pr) {
      reviewThreads(first: 100, after: $endCursor) {
        totalCount
        pageInfo { hasNextPage endCursor }
        nodes {
          id isResolved path
          comments(first: 100) {
            totalCount
            pageInfo { hasNextPage }
            nodes { databaseId body line originalLine author { login } }
          }
        }
      }
    }
  }
}
"""

_REVIEWS_QUERY = """
query($endCursor: String, $o: String!, $r: String!, $pr: Int!) {
  repository(owner: $o, name: $r) {
    pullRequest(number: $pr) {
      reviews(first: 100, after: $endCursor) {
        totalCount
        pageInfo { hasNextPage endCursor }
        nodes { id author { login } state body submittedAt }
      }
    }
  }
}
"""

RESOLVE_THREAD_MUTATION = """
mutation($threadId: ID!) {
  resolveReviewThread(input: { threadId: $threadId }) {
    thread { isResolved }
  }
}
"""

# Absolute `gh` path, resolved once at import time — ruff's start-process-with-partial-path (S607)
# requires a resolved path rather than a bare command name. Falls back to the literal "gh" when
# `shutil.which` can't find it, so a missing binary still surfaces as a normal FileNotFoundError
# from the exec call itself rather than a custom error path.
_GH = shutil.which("gh") or "gh"

_GH_TIMEOUT_SECONDS = 30

_ISSUE_COMMENT_ADAPTER: TypeAdapter[list[IssueComment]] = TypeAdapter(list[IssueComment])
_REACTION_ADAPTER: TypeAdapter[list[Reaction]] = TypeAdapter(list[Reaction])
_PR_COMMIT_ADAPTER: TypeAdapter[list[PullRequestCommit]] = TypeAdapter(list[PullRequestCommit])

# GraphQL's `author.login` and the REST reactions API's `user.login` return this bot's account
# name without a `[bot]` suffix and with one respectively (confirmed against this repo's own PR
# #3318 and #3306 history — see `_fetch_pr_reactions`) — matching by prefix covers both shapes
# without hardcoding either exact string.
_CODEX_REACTOR_LOGIN_PREFIX = "chatgpt-codex-connector"


def run_gh(args: list[str], *, timeout: float = _GH_TIMEOUT_SECONDS) -> str:
    """Run a `gh` command and return its captured stdout.

    `gh` spawns no child processes of its own, so a plain timeout is enough to bound it — no
    process-group cleanup is needed the way it would be for a command that forks descendants.

    Args:
        args: Full `gh` argv, excluding the executable itself (e.g. `["api", "graphql", ...]`).
        timeout: Seconds to allow before killing the process. Defaults to `_GH_TIMEOUT_SECONDS`;
            `watch` passes a smaller value as its own deadline approaches so one slow call near
            the end of a poll window can't push the whole command past `--timeout-seconds`.

    Returns:
        The command's stdout, decoded as text.

    Raises:
        FileNotFoundError: `gh` (GitHub CLI) is not on PATH.
        subprocess.CalledProcessError: `gh` exited non-zero. stderr is left connected to this
            process's own stderr (not captured) so the diagnostic reaches the caller directly.
        subprocess.TimeoutExpired: the command exceeded `timeout`.
    """
    result = subprocess.run([_GH, *args], stdout=subprocess.PIPE, text=True, timeout=timeout, check=True)
    return result.stdout


def _fetch_pages(
    owner: str, repo: str, pr: int, *, gh_timeout: float = _GH_TIMEOUT_SECONDS
) -> list[ReviewThreadsConnection]:
    """Fetch and validate every paginated page of a PR's review threads.

    Args:
        owner: Repository owner login.
        repo: Repository name.
        pr: Pull request number.
        gh_timeout: Seconds to bound the underlying `gh` call to — see `run_gh`.

    Returns:
        One validated `reviewThreads` connection per page `gh api graphql --paginate` returned.
    """
    raw = run_gh(
        [
            "api",
            "graphql",
            "--paginate",
            "--slurp",
            "-f",
            f"query={_UNRESOLVED_THREADS_QUERY}",
            "-f",
            f"o={owner}",
            "-f",
            f"r={repo}",
            "-F",
            f"pr={pr}",
        ],
        timeout=gh_timeout,
    )
    return [
        ReviewThreadsConnection.model_validate(page["data"]["repository"]["pullRequest"]["reviewThreads"])
        for page in json.loads(raw)
    ]


def _fetch_review_pages(
    owner: str, repo: str, pr: int, *, gh_timeout: float = _GH_TIMEOUT_SECONDS
) -> list[ReviewsConnection]:
    """Fetch and validate every paginated page of a PR's top-level reviews.

    A separate `gh` invocation from `_fetch_pages`: `gh api graphql --paginate` follows exactly
    one `pageInfo.endCursor` per call, so reviews and reviewThreads — independent connections —
    each need their own query and their own paginated `gh` call.

    Args:
        owner: Repository owner login.
        repo: Repository name.
        pr: Pull request number.
        gh_timeout: Seconds to bound the underlying `gh` call to — see `run_gh`.

    Returns:
        One validated `reviews` connection per page `gh api graphql --paginate` returned.
    """
    raw = run_gh(
        [
            "api",
            "graphql",
            "--paginate",
            "--slurp",
            "-f",
            f"query={_REVIEWS_QUERY}",
            "-f",
            f"o={owner}",
            "-f",
            f"r={repo}",
            "-F",
            f"pr={pr}",
        ],
        timeout=gh_timeout,
    )
    return [
        ReviewsConnection.model_validate(page["data"]["repository"]["pullRequest"]["reviews"])
        for page in json.loads(raw)
    ]


def _fetch_issue_comments(
    owner: str, repo: str, pr: int, *, gh_timeout: float = _GH_TIMEOUT_SECONDS
) -> list[IssueComment]:
    """Fetch every PR-level (issue) comment's timestamp and author, auto-paginated and flattened.

    A PR-level comment — `gh pr comment`, or any comment posted through the Issues REST API
    rather than as an inline review comment — is the mechanism the receiving-pr-reviews skill's
    own workflow already uses to answer a `reviews_with_body` entry (SKILL.md step 6: "A decision
    spanning threads... goes on the PR itself via `gh pr comment`"). The newest one of these
    authored by the currently-authenticated `gh` identity (see `_fetch_authenticated_login`) is
    exactly the signal `build_fetch_result` needs to tell whether a review's top-level feedback
    has since been followed up on by this workflow — not by an unrelated bystander, bot, or CI
    notification also commenting on the PR in the meantime.

    Args:
        owner: Repository owner login.
        repo: Repository name.
        pr: Pull request number.
        gh_timeout: Seconds to bound the underlying `gh` call to — see `run_gh`.

    Returns:
        Every PR-level comment, flattened across all pages. `--slurp` is used even though this is
        a plain REST array response (not GraphQL): without it, a multi-page result would print as
        several bare JSON arrays concatenated back to back, which `json.loads` cannot parse as one
        document — `--slurp` wraps each page in an outer array first, same as the GraphQL calls
        above.
    """
    raw = run_gh(["api", f"repos/{owner}/{repo}/issues/{pr}/comments", "--paginate", "--slurp"], timeout=gh_timeout)
    return [comment for page in json.loads(raw) for comment in _ISSUE_COMMENT_ADAPTER.validate_python(page)]


def _fetch_pr_reactions(owner: str, repo: str, pr: int, *, gh_timeout: float = _GH_TIMEOUT_SECONDS) -> list[Reaction]:
    """Fetch every reaction left on the PR itself (not on any individual comment), flattened.

    Confirmed empirically against this repository's own review history (PR #3318, #3306): Codex's
    own review text states "If Codex has suggestions, it will comment; otherwise it will react
    with :+1:" — on both PRs checked, that reaction landed here, `GET
    repos/{owner}/{repo}/issues/{pr}/reactions`, as a `content: "+1"` entry from
    `chatgpt-codex-connector[bot]`, with no accompanying review or comment at all. This is a
    reaction on the PR (issue) itself, distinct from a reaction on any individual review comment —
    `reviews`/`reviews_with_body` never carries it, and this script does not check per-comment
    reactions.

    Args:
        owner: Repository owner login.
        repo: Repository name.
        pr: Pull request number.
        gh_timeout: Seconds to bound the underlying `gh` call to — see `run_gh`.

    Returns:
        Every reaction on the PR itself, flattened across all pages — see `_fetch_issue_comments`
        for why `--slurp` is used on this plain REST array endpoint.
    """
    raw = run_gh(["api", f"repos/{owner}/{repo}/issues/{pr}/reactions", "--paginate", "--slurp"], timeout=gh_timeout)
    return [reaction for page in json.loads(raw) for reaction in _REACTION_ADAPTER.validate_python(page)]


def _fetch_authenticated_login(*, gh_timeout: float = _GH_TIMEOUT_SECONDS) -> str:
    """Fetch the GitHub login `gh` is currently authenticated as.

    Repo-independent (unlike every other `_fetch_*` helper here): the authenticated identity is
    the same regardless of which PR or repository is being watched, so this call takes no
    `owner`/`repo`/`pr` arguments.

    Args:
        gh_timeout: Seconds to bound the underlying `gh` call to — see `run_gh`.

    Returns:
        The authenticated user's login, e.g. `"jane-doe"`.
    """
    return run_gh(["api", "user", "--jq", ".login"], timeout=gh_timeout).strip()


def _fetch_latest_commit_date(owner: str, repo: str, pr: int, *, gh_timeout: float = _GH_TIMEOUT_SECONDS) -> datetime:
    """Fetch the PR's current head commit's raw git committer date.

    `GET /repos/{owner}/{repo}/pulls/{pr}/commits` returns commits oldest-first, so the last
    element in the fully-flattened, fully-paginated list is always the current head commit — this
    is what `build_fetch_result` compares a Codex approval reaction's timestamp against, so a
    reaction left on an earlier revision is never mistaken for approval of the current one. A
    force-push (e.g. a rebase) updates each commit's committer date to the time of that push even
    when the author date is preserved, which is exactly the "when was this revision pushed" signal
    needed here.

    Args:
        owner: Repository owner login.
        repo: Repository name.
        pr: Pull request number.
        gh_timeout: Seconds to bound the underlying `gh` call to — see `run_gh`.

    Returns:
        The head commit's raw git committer date.

    Raises:
        IndexError: the PR has no commits at all — not possible for a real, open pull request, so
            this is an acceptable boundary failure for an invariant this script does not control.
    """
    raw = run_gh(["api", f"repos/{owner}/{repo}/pulls/{pr}/commits", "--paginate", "--slurp"], timeout=gh_timeout)
    commits = [commit for page in json.loads(raw) for commit in _PR_COMMIT_ADAPTER.validate_python(page)]
    return commits[-1].commit.committer.date


def _is_codex_thumbs_up(reaction: Reaction) -> bool:
    """Whether `reaction` is Codex's approval signal — a "+1" from its bot account.

    Args:
        reaction: One reaction fetched by `_fetch_pr_reactions`.

    Returns:
        `True` when `reaction` is a thumbs-up left by a `chatgpt-codex-connector`-prefixed login.
    """
    return (
        reaction.content == "+1"
        and reaction.user is not None
        and reaction.user.login.lower().startswith(_CODEX_REACTOR_LOGIN_PREFIX)
    )


def gh_timeout_budget(deadline: float | None) -> float:
    """Bound a `gh` call to whatever time remains before `deadline`, capped at `_GH_TIMEOUT_SECONDS`.

    `deadline` is `None` for a plain `fetch` (no overall time budget to respect — use the full
    default). For `watch`, passing its own `deadline` here means each of `build_fetch_result`'s
    `gh` calls is bounded by whatever is actually left, not by a fixed worst-case reservation
    subtracted from every poll regardless of how fast GitHub responds — a call made with plenty of
    time left still gets the full `_GH_TIMEOUT_SECONDS`, and only a call made close to `deadline`
    is tightened.

    Args:
        deadline: A `time.monotonic()` timestamp to respect, or `None` for no deadline.

    Returns:
        Seconds to pass as `run_gh`'s `timeout`, always positive.
    """
    if deadline is None:
        return _GH_TIMEOUT_SECONDS
    return max(0.1, min(_GH_TIMEOUT_SECONDS, deadline - time.monotonic()))


def build_fetch_result(owner: str, repo: str, pr: int, *, deadline: float | None = None) -> FetchResult:
    """Fetch and assemble one PR's full outstanding-work snapshot: threads, reviews, and approval.

    Shared by `fetch` (prints the result once, `deadline=None`) and `watch` (calls this repeatedly
    on a polling interval, passing its own deadline) so both subcommands assemble a `FetchResult`
    identically. Makes six `gh` calls, each independently bounded by `gh_timeout_budget(deadline)`:
    the paginated review-threads query, the paginated reviews query, every PR-level issue comment
    (for `unresponded_reviews`), every reaction on the PR itself (for `codex_approved`), the
    currently-authenticated `gh` identity (also for `unresponded_reviews`), and the PR's head
    commit date (also for `codex_approved`). Every one of the six is a fresh snapshot taken by this
    call alone — nothing here is compared against an earlier call's result, which is what makes two
    `watch` calls back to back, or a `watch` call issued right after a `fetch`, incapable of
    missing or double-counting activity that happened in between (the failure mode a per-invocation
    in-memory baseline used to have).

    `unresponded_reviews` is every `reviews_with_body` entry whose `submittedAt` is at or after the
    most recent PR-level issue comment authored by the currently-authenticated `gh` identity across
    the whole PR (or every one of them, if that identity has posted no PR-level comment yet) — i.e.
    this workflow has not posted anything on the PR since that review went up. Comments from any
    other account are ignored for this purpose: an unrelated bystander, bot, or CI notification
    commenting on the PR carries no evidence it addressed any specific review's feedback, and using
    it as the cutover would silently mark that review as responded-to. A review with no
    `submittedAt` (not yet actually submitted) is excluded rather than treated as always-unresponded.

    `codex_approved` is `True` when a "+1" reaction from a `chatgpt-codex-connector`-prefixed login
    exists on the PR itself at the moment of this call *and* that reaction's own timestamp is at or
    after the PR's current head commit's date — see `_fetch_pr_reactions` and
    `_fetch_latest_commit_date`. Without that comparison, a reaction left approving an earlier
    revision would keep reporting as approval indefinitely, even after a later push the reaction
    never actually saw.

    Args:
        owner: Repository owner login.
        repo: Repository name.
        pr: Pull request number.
        deadline: A `time.monotonic()` timestamp the caller wants this call's six `gh`
            invocations to respect — see `gh_timeout_budget`. `None` means no deadline.

    Returns:
        Totals plus every currently-unresolved thread, every unresponded review, and whether
        Codex's approval reaction is present right now for the current revision.
    """
    thread_pages = _fetch_pages(owner, repo, pr, gh_timeout=gh_timeout_budget(deadline))
    review_pages = _fetch_review_pages(owner, repo, pr, gh_timeout=gh_timeout_budget(deadline))
    issue_comments = _fetch_issue_comments(owner, repo, pr, gh_timeout=gh_timeout_budget(deadline))
    reactions = _fetch_pr_reactions(owner, repo, pr, gh_timeout=gh_timeout_budget(deadline))
    authenticated_login = _fetch_authenticated_login(gh_timeout=gh_timeout_budget(deadline))
    latest_commit_date = _fetch_latest_commit_date(owner, repo, pr, gh_timeout=gh_timeout_budget(deadline))

    all_threads = [node for page in thread_pages for node in page.nodes]
    all_reviews = [node for page in review_pages for node in page.nodes]
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
    reviews_with_body = [review for review in all_reviews if review.body.strip()]

    latest_own_comment_at = max(
        (
            comment.created_at
            for comment in issue_comments
            if comment.user is not None and comment.user.login == authenticated_login
        ),
        default=None,
    )
    unresponded_reviews = [
        review
        for review in reviews_with_body
        if review.submittedAt is not None
        and (latest_own_comment_at is None or latest_own_comment_at <= review.submittedAt)
    ]
    codex_approved = any(
        _is_codex_thumbs_up(reaction) and reaction.created_at >= latest_commit_date for reaction in reactions
    )

    return FetchResult(
        reviews_count=review_pages[0].totalCount,
        reviews_with_body=reviews_with_body,
        unresponded_reviews=unresponded_reviews,
        threads_count=thread_pages[0].totalCount,
        unresolved=unresolved,
        unresolved_count=len(unresolved),
        codex_approved=codex_approved,
    )

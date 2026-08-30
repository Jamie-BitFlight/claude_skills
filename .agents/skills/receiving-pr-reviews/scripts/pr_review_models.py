"""Pydantic data contracts for `pr_review_threads.py` and `pr_review_gh.py`.

Every model here is a boundary type: it validates one shape of raw JSON that `gh` (GitHub CLI)
returns, immediately converting it into a strongly typed object the rest of the script works
with. Field names mirror the upstream API exactly — GraphQL fields stay camelCase (`isResolved`,
`submittedAt`), REST fields stay snake_case (`created_at`) — rather than being normalized to one
convention, so the JSON this script emits matches what the receiving-pr-reviews skill already
documents and what a caller already parses.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

__all__ = [
    "Author",
    "CommentNode",
    "FetchResult",
    "GitCommit",
    "GitCommitter",
    "IssueComment",
    "PullRequestCommit",
    "Reaction",
    "ReviewNode",
    "UnresolvedThread",
    "WatchResult",
]


class Author(BaseModel):
    """A GitHub account login, as GraphQL returns it for a comment/review/reaction author."""

    login: str


class CommentNode(BaseModel):
    """A single review comment, in the shape GitHub's GraphQL API returns it.

    `author` is `None` for a comment left by an account that has since been deleted — GitHub's
    GraphQL schema allows a null `author` there, same as `ReviewNode`.
    """

    databaseId: int
    body: str
    line: int | None
    originalLine: int | None
    author: Author | None


class PageInfo(BaseModel):
    """The `hasNextPage` half of a GraphQL connection's `pageInfo`.

    `endCursor` is consumed entirely by `gh api graphql --paginate` itself and never read by this
    script.
    """

    hasNextPage: bool


class CommentsConnection(BaseModel):
    """One page's `comments` connection, nested inside a `reviewThreads` node."""

    totalCount: int
    pageInfo: PageInfo
    nodes: list[CommentNode]


class ReviewThreadNode(BaseModel):
    """One review thread, in the shape GitHub's GraphQL API returns it."""

    id: str
    isResolved: bool
    path: str
    comments: CommentsConnection


class ReviewThreadsConnection(BaseModel):
    """One page's `reviewThreads` connection, already unwrapped from `data.repository.pullRequest`.

    `pr_review_gh._fetch_pages` pulls this dict straight out of each slurped page by subscripting
    the fixed `data.repository.pullRequest.reviewThreads` path — a mismatch there (GitHub renaming
    or removing a field) raises `KeyError` immediately at the point of access, which is an
    acceptable boundary failure for a query shape this script itself controls. Everything
    variable — the node fields — is validated here.
    """

    totalCount: int
    nodes: list[ReviewThreadNode]


class ReviewNode(BaseModel):
    """A top-level review submission, in the shape GitHub's GraphQL API returns it.

    Distinct from a review *comment* (`CommentNode`): this is the review object itself — its
    `body` is the reviewer's summary text, separate from any inline comment threads it may or may
    not have attached. `author` is `None` for a review left by an account that has since been
    deleted — GitHub's GraphQL schema allows a null `author` there. `id` is GitHub's own GraphQL
    node id for this review submission. `submittedAt` is `None` only for a review that has not
    actually been submitted yet (e.g. `PENDING` state, visible only to its own author) —
    `pr_review_gh.build_fetch_result` excludes those from `unresponded_reviews` rather than
    treating an unsubmitted review as perpetually unanswered. `lastEditedAt` is `None` when the
    review's body has never been edited since submission, and otherwise the timestamp of its most
    recent edit — `pr_review_gh.build_fetch_result` treats whichever of `submittedAt`/`lastEditedAt`
    is later as the review's effective timestamp, so an editor who adds new feedback to an
    already-submitted review after this workflow already responded is not silently skipped forever
    (a PR-level comment that postdates the original `submittedAt` but predates the edit would
    otherwise still count as having addressed content that did not exist yet when it was posted).
    """

    id: str
    author: Author | None
    state: str
    body: str
    submittedAt: datetime | None
    lastEditedAt: datetime | None


class ReviewsConnection(BaseModel):
    """One page's `reviews` connection, already unwrapped — see `ReviewThreadsConnection`."""

    totalCount: int
    nodes: list[ReviewNode]


class UnresolvedThread(BaseModel):
    """One unresolved review thread and its full comment history, as emitted to the caller."""

    id: str
    path: str
    comments: list[CommentNode]
    comments_truncated: bool


class IssueComment(BaseModel):
    """One PR-level (issue) comment, in the shape GitHub's REST API returns it.

    `created_at` and `user` are the only fields needed: `pr_review_gh.build_fetch_result` uses the
    most recent comment authored by the currently-authenticated `gh` identity — not any comment
    from any account — as the "the running workflow has since followed up on this review" signal
    for `unresponded_reviews`. Restricting to that one identity matters: a PR-level comment from an
    unrelated bystander, bot, or CI notification carries no evidence it addressed any specific
    review's feedback, and without an author to filter on, any such comment would silently mark
    every earlier bodied review as responded-to. `user` is `None` for a comment left by an account
    that has since been deleted, same null pattern as `CommentNode.author`.
    """

    created_at: datetime
    user: Author | None


class Reaction(BaseModel):
    """One reaction left on the PR itself, in the shape GitHub's REST reactions API returns it.

    `user` is `None` for a reaction left by an account that has since been deleted, same null
    pattern as `CommentNode.author` and `ReviewNode.author`. `created_at` lets
    `pr_review_gh.build_fetch_result` require Codex's approval reaction to postdate the PR's latest
    commit — a reaction left on an earlier revision is stale and must not be reported as approval
    of the current one.
    """

    content: str
    user: Author | None
    created_at: datetime


class GitCommitter(BaseModel):
    """The raw git `committer` identity on a commit, in the shape GitHub's REST API returns it.

    Distinct from the GitHub account object REST also calls `committer` at the top level of a
    commit list entry (which is `None` for a commit whose author has no linked GitHub account):
    this is the git-native field nested under `commit`, always present because git itself requires
    every commit to carry committer information.
    """

    date: datetime


class GitCommit(BaseModel):
    """The raw git commit object nested under one entry of the PR-commits REST endpoint."""

    committer: GitCommitter


class PullRequestCommit(BaseModel):
    """One commit from `GET /repos/{owner}/{repo}/pulls/{pr}/commits`.

    Commits are listed oldest-first per GitHub's REST API — the last element is always the PR's
    current head commit.
    """

    commit: GitCommit


class FetchResult(BaseModel):
    """Result of `fetch`: totals plus every currently-outstanding thread, review, and approval.

    Every field here is derived from a single fresh set of `gh` calls (see
    `pr_review_gh.build_fetch_result`) — none of it is a diff against an earlier call's result,
    so reading any of these fields never depends on what call came before this one.
    """

    reviews_count: int
    reviews_with_body: list[ReviewNode]
    unresponded_reviews: list[ReviewNode]
    threads_count: int
    unresolved: list[UnresolvedThread]
    unresolved_count: int
    codex_approved: bool

    def has_outstanding_work(self) -> bool:
        """Whether this snapshot has anything a reviewing agent still needs to act on.

        `True` when at least one thread is unresolved, at least one review-with-body has not been
        followed up on yet, or Codex has left its thumbs-up approval reaction — the three
        independent stop conditions `watch` polls for. Defined once here, on the data it reads,
        so `watch` and any future caller apply the exact same rule to the exact same state.

        Returns:
            `True` if any of the three outstanding-work signals is present on this snapshot.
        """
        return self.unresolved_count > 0 or bool(self.unresponded_reviews) or self.codex_approved


class WatchResult(BaseModel):
    """Result of `watch`: the final fetch snapshot plus how the poll loop ended.

    `timed_out` is `False` exactly when `state.has_outstanding_work()` was `True` on the poll that
    ended the loop — every field driving that decision (`unresolved_count`, `unresponded_reviews`,
    `codex_approved`) lives on `state` itself, derived fresh from that poll's own `gh` snapshot.
    Nothing here is a diff against an earlier call's baseline: two `watch` calls back to back, or a
    `watch` call issued right after a `fetch`, can never miss or double-count activity that
    happened in between, because neither call remembers anything from before its own first `gh`
    request.
    """

    timed_out: bool
    state: FetchResult

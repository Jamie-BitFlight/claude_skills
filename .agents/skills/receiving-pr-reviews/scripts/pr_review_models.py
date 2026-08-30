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
    "ForcePushEvent",
    "GitHubCommitDate",
    "HeadCommitNode",
    "IssueComment",
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
    `url` is this review's canonical GitHub permalink — `pr_review_gh._unresponded_reviews` treats
    an own PR-level comment quoting this URL as explicit evidence that comment addresses this
    specific review, rather than inferring it purely from chronological order (which cannot
    distinguish a comment that engaged with a review's feedback from an unrelated administrative
    comment, e.g. a cross-thread sequencing decision, that merely happens to postdate it).
    """

    id: str
    author: Author | None
    state: str
    body: str
    submittedAt: datetime | None
    lastEditedAt: datetime | None
    url: str


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

    `pr_review_gh._unresponded_reviews` treats a comment authored by the currently-authenticated
    `gh` identity as evidence a specific review was addressed only when `body` quotes that review's
    `ReviewNode.url` — restricting by author matters for the same reason as `CommentNode.author`
    filtering elsewhere: a PR-level comment from an unrelated bystander, bot, or CI notification
    carries no evidence it addressed any specific review's feedback. `user` is `None` for a comment
    left by an account that has since been deleted, same null pattern as `CommentNode.author`.
    """

    created_at: datetime
    user: Author | None
    body: str


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


class GitHubCommitDate(BaseModel):
    """The `committedDate` field of a GraphQL `Commit` object."""

    committedDate: datetime


class HeadCommitNode(BaseModel):
    """One commit from GraphQL's `pullRequest.commits(last: 1)` connection.

    Requesting `last: 1` asks the server directly for the tail element — GraphQL's connection
    pagination has no equivalent of the REST `/pulls/{pr}/commits` endpoint's documented 250-commit
    hard cap, which made that endpoint's last-paginated-element unreliable as "the current head" on
    a PR with more commits than the cap (see `pr_review_gh._fetch_latest_commit_date`).
    """

    commit: GitHubCommitDate


class ForcePushEvent(BaseModel):
    """One `HeadRefForcePushedEvent` GraphQL timeline item.

    `createdAt` is when GitHub's server recorded the force-push itself — independent of any
    commit's own embedded author/committer dates, which is what makes it a reliable head-update
    signal even when a force-push resets a PR's head back onto a pre-existing commit object whose
    own dates predate it (see `pr_review_gh._fetch_latest_force_push_at`).
    """

    createdAt: datetime


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

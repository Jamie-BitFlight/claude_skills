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
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "Author",
    "CommentNode",
    "FetchResult",
    "ForcePushEvent",
    "GitHubCommitDate",
    "HeadCommitNode",
    "IssueComment",
    "PullRequestHeadState",
    "Reaction",
    "RepoIdentity",
    "ReviewNode",
    "Reviewability",
    "UnresolvedThread",
    "WatchResult",
]


class GitHubResponseModel(BaseModel):
    """Base for every model that ingests a raw GitHub response, GraphQL or REST.

    `strict=True` so a producer-shape mismatch — GitHub or `gh` returning a string where the
    schema declares an integer or a boolean — is rejected at ingress instead of being coerced
    into apparently valid review state. Lax mode would turn `"totalCount": "0"` into `0` and
    `"isResolved": "false"` into `True` without a word, which is exactly the kind of silence a
    boundary exists to break.

    Models this script builds itself from already-validated values (`UnresolvedThread`,
    `FetchResult`, `WatchResult`) are not ingress and deliberately do not inherit this: no
    untrusted input reaches them.
    """

    model_config = ConfigDict(strict=True)


# Every GitHub timestamp arrives as an ISO-8601 *string*, which is the documented wire shape, not
# a producer mismatch. These models are validated from `json.loads` output — Pydantic's Python
# mode — where strict `datetime` accepts only a `datetime` instance and would reject the string
# GitHub actually sends. Relaxing strictness on exactly these fields keeps ISO-8601 parsing while
# every int, bool and str field around them stays strict.
GitHubTimestamp = Annotated[datetime, Field(strict=False)]


class Author(GitHubResponseModel):
    """A GitHub account login, as GraphQL returns it for a comment/review/reaction author."""

    login: str


class RepoIdentity(GitHubResponseModel):
    """This checkout's own `owner/repo`, as `gh repo view --json nameWithOwner` reports it.

    `nameWithOwner` is `gh`'s own canonical `"owner/repo"` string (always exactly one `/`, since
    neither half of a GitHub repository identity may itself contain one) -- the shape
    `pr_review_gh.detect_repo_identity` splits into the `(owner, repo)` pair every other `gh` call
    in this script takes as separate query variables.
    """

    nameWithOwner: str


class CommentNode(GitHubResponseModel):
    """A single review comment, in the shape GitHub's GraphQL API returns it.

    `author` is `None` for a comment left by an account that has since been deleted — GitHub's
    GraphQL schema allows a null `author` there, same as `ReviewNode`.
    """

    databaseId: int
    body: str
    line: int | None
    originalLine: int | None
    author: Author | None


class PageInfo(GitHubResponseModel):
    """The `hasNextPage` half of a GraphQL connection's `pageInfo`.

    `endCursor` is consumed entirely by `gh api graphql --paginate` itself and never read by this
    script.
    """

    hasNextPage: bool


class CommentsConnection(GitHubResponseModel):
    """One page's `comments` connection, nested inside a `reviewThreads` node."""

    totalCount: int
    pageInfo: PageInfo
    nodes: list[CommentNode]


class ReviewThreadNode(GitHubResponseModel):
    """One review thread, in the shape GitHub's GraphQL API returns it."""

    id: str
    isResolved: bool
    path: str
    comments: CommentsConnection


class ReviewThreadsConnection(GitHubResponseModel):
    """One page's `reviewThreads` connection, already unwrapped from `data.repository.pullRequest`.

    `pr_review_gh._fetch_pages` pulls this dict straight out of each slurped page by subscripting
    the fixed `data.repository.pullRequest.reviewThreads` path — a mismatch there (GitHub renaming
    or removing a field) raises `KeyError` immediately at the point of access, which is an
    acceptable boundary failure for a query shape this script itself controls. Everything
    variable — the node fields — is validated here.
    """

    totalCount: int
    nodes: list[ReviewThreadNode]


class ReviewNode(GitHubResponseModel):
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
    submittedAt: GitHubTimestamp | None
    lastEditedAt: GitHubTimestamp | None
    url: str


class ReviewsConnection(GitHubResponseModel):
    """One page's `reviews` connection, already unwrapped — see `ReviewThreadsConnection`."""

    totalCount: int
    nodes: list[ReviewNode]


class UnresolvedThread(BaseModel):
    """One unresolved review thread and its full comment history, as emitted to the caller.

    Assembled by `pr_review_gh.build_fetch_result` from already-validated `ReviewThreadNode`
    values, so it is an output shape rather than an ingress one — see `GitHubResponseModel`.
    """

    id: str
    path: str
    comments: list[CommentNode]
    comments_truncated: bool


class IssueComment(GitHubResponseModel):
    """One PR-level (issue) comment, in the shape GitHub's REST API returns it.

    `pr_review_gh._unresponded_reviews` treats a comment authored by the currently-authenticated
    `gh` identity as evidence a specific review was addressed only when `body` quotes that review's
    `ReviewNode.url` — restricting by author matters for the same reason as `CommentNode.author`
    filtering elsewhere: a PR-level comment from an unrelated bystander, bot, or CI notification
    carries no evidence it addressed any specific review's feedback. `user` is `None` for a comment
    left by an account that has since been deleted, same null pattern as `CommentNode.author`.
    """

    created_at: GitHubTimestamp
    user: Author | None
    body: str


class Reaction(GitHubResponseModel):
    """One reaction left on the PR itself, in the shape GitHub's REST reactions API returns it.

    `user` is `None` for a reaction left by an account that has since been deleted, same null
    pattern as `CommentNode.author` and `ReviewNode.author`. `created_at` lets
    `pr_review_gh.build_fetch_result` require Codex's approval reaction to postdate the PR's latest
    commit — a reaction left on an earlier revision is stale and must not be reported as approval
    of the current one.
    """

    content: str
    user: Author | None
    created_at: GitHubTimestamp


class GitHubCommitDate(GitHubResponseModel):
    """The `committedDate` field of a GraphQL `Commit` object."""

    committedDate: GitHubTimestamp


class HeadCommitNode(GitHubResponseModel):
    """One commit from GraphQL's `pullRequest.commits(last: 1)` connection.

    Requesting `last: 1` asks the server directly for the tail element — GraphQL's connection
    pagination has no equivalent of the REST `/pulls/{pr}/commits` endpoint's documented 250-commit
    hard cap, which made that endpoint's last-paginated-element unreliable as "the current head" on
    a PR with more commits than the cap (see `pr_review_gh._fetch_latest_commit_date`).
    """

    commit: GitHubCommitDate


class HeadCommitsConnection(GitHubResponseModel):
    """The `commits(last: 1)` connection nested inside `PullRequestHeadState`."""

    nodes: list[HeadCommitNode]


class PullRequestHeadState(GitHubResponseModel):
    """The PR-level fields `pr_review_gh._fetch_head_state` reads in one GraphQL query.

    All four live on the same `pullRequest` object, so they cost one round trip together: the head
    commit's date (for `codex_approved`'s staleness check) plus the three fields that say whether
    this PR can be reviewed at all.

    `mergeable` is `MERGEABLE`, `CONFLICTING`, or `UNKNOWN`; `mergeStateStatus` is one of `CLEAN`,
    `DIRTY`, `BLOCKED`, `BEHIND`, `UNSTABLE`, `DRAFT`, `HAS_HOOKS`, or `UNKNOWN`. Both are kept as
    plain strings rather than enums: GitHub can add a state at any time, and an unrecognized one
    must reach the caller as data instead of failing validation on a PR that is otherwise fine.
    Strict against that string type, though — `strict=True` via `GitHubResponseModel` means a
    number or a null arriving where a state name belongs is rejected rather than stringified, and
    `isDraft` must be a real boolean rather than `"false"`. None of the three is a timestamp, so
    none needs the `GitHubTimestamp` relaxation.
    """

    isDraft: bool
    mergeable: str
    mergeStateStatus: str
    commits: HeadCommitsConnection


class Reviewability(BaseModel):
    """Whether this PR is in a state where reviews can happen at all.

    A PR that is a draft or has merge conflicts receives no reviews — reviewers are not requested
    for a draft, and review runs do not start on a conflicting branch. Without this, an empty
    `unresolved` array reads as "nothing to do" when the truth is "nothing can happen until the PR
    itself is fixed", which is the same misleading-empty-result trap the `reviews_count` /
    `threads_count` / `unresolved_count` triple already warns about.

    `blockers` is empty exactly when neither condition holds. Each entry is a plain sentence naming
    the consequence, not just the state name, because the reader needs to know what will not
    happen.

    `mergeable: "UNKNOWN"` is deliberately **not** a blocker. GitHub computes mergeability in a
    background job and returns `UNKNOWN` while it runs — which is precisely the moment just after a
    push, when this script is most likely to be called. Reporting a conflict there would be a false
    alarm, so `UNKNOWN` is surfaced as data and left for the next check to resolve; `watch` re-reads
    it on every poll, and `fetch` is cheap to re-run.

    Derived by `pr_review_gh._reviewability` from an already-validated `PullRequestHeadState`, so
    it is an output shape rather than an ingress one and does not inherit `GitHubResponseModel` —
    same reason as `UnresolvedThread` and `FetchResult`.
    """

    is_draft: bool
    mergeable: str
    merge_state_status: str
    blockers: list[str]


class ForcePushEvent(GitHubResponseModel):
    """One `HeadRefForcePushedEvent` GraphQL timeline item.

    `createdAt` is when GitHub's server recorded the force-push itself — independent of any
    commit's own embedded author/committer dates, which is what makes it a reliable head-update
    signal even when a force-push resets a PR's head back onto a pre-existing commit object whose
    own dates predate it (see `pr_review_gh._fetch_latest_force_push_at`).
    """

    createdAt: GitHubTimestamp


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
    reviewability: Reviewability

    def has_outstanding_work(self) -> bool:
        """Whether this snapshot has anything a reviewing agent still needs to act on.

        `True` when at least one thread is unresolved, at least one review-with-body has not been
        followed up on yet, or Codex has left its thumbs-up approval reaction — the three
        independent stop conditions `watch` polls for. Defined once here, on the data it reads,
        so `watch` and any future caller apply the exact same rule to the exact same state.

        Deliberately independent of `reviewability`: a draft or conflicting PR can still carry
        unresolved threads that need answering, and a reviewable PR with nothing outstanding is
        still nothing to act on. `reviewability.blockers` explains an *empty* result set; it never
        creates or suppresses work.

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

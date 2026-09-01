"""`gh`-backed GitHub I/O and result assembly for `pr_review_threads.py`.

Every function here shells out to `gh` (GitHub CLI) rather than talking to the GitHub API
directly, relying on `gh`'s own authentication. `build_fetch_result` is the one function the CLI
layer (`pr_review_threads.py`) calls directly — it composes the seven independent `gh` calls below
into one `FetchResult` snapshot, fresh every time it runs. `run_gh` is exported too: the CLI
layer's `reply`/`resolve` commands call it directly for their own single-shot `gh` invocations.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import time
from datetime import datetime

from pydantic import TypeAdapter

from pr_review_models import (
    FetchResult,
    ForcePushEvent,
    IssueComment,
    PullRequestHeadState,
    Reaction,
    RepoIdentity,
    Reviewability,
    ReviewNode,
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
        nodes { id author { login } state body submittedAt lastEditedAt url }
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

_LATEST_FORCE_PUSH_QUERY = """
query($o: String!, $r: String!, $pr: Int!) {
  repository(owner: $o, name: $r) {
    pullRequest(number: $pr) {
      timelineItems(last: 1, itemTypes: [HEAD_REF_FORCE_PUSHED_EVENT]) {
        nodes { ... on HeadRefForcePushedEvent { createdAt } }
      }
    }
  }
}
"""

# `isDraft`/`mergeable`/`mergeStateStatus` are selected alongside the head commit rather than in a
# query of their own: they live on the same `pullRequest` object, so asking for them here costs no
# extra round trip, and `build_fetch_result` is already seven sequential `gh` calls deep. Verified
# against this repository's own API (2026-08-30) that `mergeStateStatus` needs no preview `Accept`
# header on `gh api graphql`.
_HEAD_STATE_QUERY = """
query($o: String!, $r: String!, $pr: Int!) {
  repository(owner: $o, name: $r) {
    pullRequest(number: $pr) {
      isDraft
      mergeable
      mergeStateStatus
      commits(last: 1) {
        nodes { commit { committedDate } }
      }
    }
  }
}
"""

# Absolute `gh` path, resolved once at import time — ruff's start-process-with-partial-path (S607)
# requires a resolved path rather than a bare command name. Falls back to the literal "gh" when
# `shutil.which` can't find it, so a missing binary still surfaces as a normal FileNotFoundError
# from the exec call itself rather than a custom error path.
_GH = shutil.which("gh") or "gh"

# `gh` calls are bounded by the caller, not by a constant here. A single fixed cap would have to
# cover a whole `gh api --paginate` run — every page requested sequentially inside one subprocess —
# on an arbitrarily large PR over an arbitrarily slow link, and `build_fetch_result` now makes
# seven such calls per snapshot rather than the two it made when the old 30-second cap was written.
# This repository has no source for that number (CLAUDE.md, "No invented constraints"), so `fetch`
# and `watch` expose `--gh-timeout-seconds` instead, unbounded by default, and `watch` additionally
# bounds each *poll* by its own `--timeout-seconds` deadline, which the caller chose.

_ISSUE_COMMENT_ADAPTER: TypeAdapter[list[IssueComment]] = TypeAdapter(list[IssueComment])
_REACTION_ADAPTER: TypeAdapter[list[Reaction]] = TypeAdapter(list[Reaction])

# GraphQL's `author.login` and the REST reactions API's `user.login` return this bot's account
# name without a `[bot]` suffix and with one respectively (confirmed against this repo's own PR
# #3318 and #3306 history — see `_fetch_pr_reactions`) — an exact-match set covers both known
# shapes without a prefix check, which would also match an unrelated account whose login merely
# starts with the same text (e.g. a public PR's `chatgpt-codex-connector-imposter`).
_CODEX_REACTOR_LOGINS = frozenset({"chatgpt-codex-connector", "chatgpt-codex-connector[bot]"})

# Codex's own "About Codex in GitHub" `<details>` footer, present byte-for-byte on every Codex
# review regardless of findings — confirmed against this repo's own PR #3318/#3306 history: a
# review that *does* carry a finding keeps this exact footer, only the text ahead of it differs.
_CODEX_EMPTY_REVIEW_FOOTER = (
    "<details> <summary>\N{INFORMATION SOURCE}\N{VARIATION SELECTOR-16} About Codex in GitHub</summary>\n<br/>\n\n"
    "[Your team has set up Codex to review pull requests in this repo]"
    "(https://chatgpt.com/codex/cloud/settings/general). Reviews are triggered when you\n"
    "- Open a pull request for review\n"
    "- Mark a draft as ready\n"
    '- Comment "@codex review".\n\n'
    "If Codex has suggestions, it will comment; otherwise it will react with \N{THUMBS UP SIGN}.\n\n\n\n\n"
    'Codex can also answer questions or update the PR. Try commenting "@codex address that feedback".\n            \n'
    "</details>"
)

# Matches Codex's own top-level review body only when it found nothing to say: the fixed header,
# fixed boilerplate text, the reviewed commit's short sha, then the footer above — and nothing
# else, in either direction. `_is_codex_empty_review` runs this as a `fullmatch` against the whole
# (stripped) body rather than a `.search()`: a bare search only anchors the fixed pieces and would
# still match a review that tucks a real finding somewhere the regex isn't looking, e.g. appended
# after the footer's closing `</details>` tag — `fullmatch` requires the entire body to consist of
# exactly this template, so any such addition breaks the match instead of being silently missed.
_CODEX_EMPTY_REVIEW_BODY = re.compile(
    r"### 💡 Codex Review\s*"
    r"Here are some automated review suggestions for this pull request\.\s*"
    r"\*\*Reviewed commit:\*\*\s*`[0-9a-f]+`\s*" + re.escape(_CODEX_EMPTY_REVIEW_FOOTER)
)


def run_gh(args: list[str], *, timeout: float | None = None) -> str:
    """Run a `gh` command and return its captured stdout.

    `gh` spawns no child processes of its own, so a plain timeout is enough to bound it — no
    process-group cleanup is needed the way it would be for a command that forks descendants.

    Args:
        args: Full `gh` argv, excluding the executable itself (e.g. `["api", "graphql", ...]`).
        timeout: Seconds to allow before killing the process, or `None` for no bound. `watch`
            passes the time left before its own deadline so one slow call near the end of a poll
            window can't push the whole command past `--timeout-seconds`.

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


def detect_repo_identity(*, gh_timeout: float | None = None) -> tuple[str, str]:
    """Detect this checkout's own GitHub `(owner, repo)` via `gh repo view`.

    Relies entirely on `gh`'s own remote resolution (the same one `gh pr view`, `gh pr comment`
    etc. use for this checkout) -- this function adds no guessing of its own. A wrong owner/repo
    would send a reply to the wrong repository, so a caller unable to detect must stop rather than
    fall back to a default (CLAUDE.md, "No invented constraints").

    Args:
        gh_timeout: Seconds to bound the `gh` call to, or `None` for no bound -- see `run_gh`.

    Returns:
        The `(owner, repo)` pair `gh` reports for this checkout.

    Raises:
        FileNotFoundError: `gh` is not on PATH.
        subprocess.CalledProcessError: `gh` could not resolve a repository for this checkout --
            no remote, not a git repository, or `gh` is unauthenticated.
        subprocess.TimeoutExpired: the command exceeded `gh_timeout`.
        pydantic.ValidationError: `gh`'s output does not match the expected shape.
    """
    raw = run_gh(["repo", "view", "--json", "nameWithOwner"], timeout=gh_timeout)
    identity = RepoIdentity.model_validate(json.loads(raw))
    owner, repo = identity.nameWithOwner.split("/", 1)
    return owner, repo


def _fetch_pages(owner: str, repo: str, pr: int, *, gh_timeout: float | None) -> list[ReviewThreadsConnection]:
    """Fetch and validate every paginated page of a PR's review threads.

    Args:
        owner: Repository owner login.
        repo: Repository name.
        pr: Pull request number.
        gh_timeout: Seconds to bound the underlying `gh` call to, or `None` for no bound — see
            `run_gh`.

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


def _fetch_review_pages(owner: str, repo: str, pr: int, *, gh_timeout: float | None) -> list[ReviewsConnection]:
    """Fetch and validate every paginated page of a PR's top-level reviews.

    A separate `gh` invocation from `_fetch_pages`: `gh api graphql --paginate` follows exactly
    one `pageInfo.endCursor` per call, so reviews and reviewThreads — independent connections —
    each need their own query and their own paginated `gh` call.

    Args:
        owner: Repository owner login.
        repo: Repository name.
        pr: Pull request number.
        gh_timeout: Seconds to bound the underlying `gh` call to, or `None` for no bound — see
            `run_gh`.

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


def _fetch_issue_comments(owner: str, repo: str, pr: int, *, gh_timeout: float | None) -> list[IssueComment]:
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
        gh_timeout: Seconds to bound the underlying `gh` call to, or `None` for no bound — see
            `run_gh`.

    Returns:
        Every PR-level comment, flattened across all pages. `--slurp` is used even though this is
        a plain REST array response (not GraphQL): without it, a multi-page result would print as
        several bare JSON arrays concatenated back to back, which `json.loads` cannot parse as one
        document — `--slurp` wraps each page in an outer array first, same as the GraphQL calls
        above.
    """
    raw = run_gh(["api", f"repos/{owner}/{repo}/issues/{pr}/comments", "--paginate", "--slurp"], timeout=gh_timeout)
    return [comment for page in json.loads(raw) for comment in _ISSUE_COMMENT_ADAPTER.validate_python(page)]


def _fetch_pr_reactions(owner: str, repo: str, pr: int, *, gh_timeout: float | None) -> list[Reaction]:
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
        gh_timeout: Seconds to bound the underlying `gh` call to, or `None` for no bound — see
            `run_gh`.

    Returns:
        Every reaction on the PR itself, flattened across all pages — see `_fetch_issue_comments`
        for why `--slurp` is used on this plain REST array endpoint.
    """
    raw = run_gh(["api", f"repos/{owner}/{repo}/issues/{pr}/reactions", "--paginate", "--slurp"], timeout=gh_timeout)
    return [reaction for page in json.loads(raw) for reaction in _REACTION_ADAPTER.validate_python(page)]


def _fetch_authenticated_login(*, gh_timeout: float | None) -> str:
    """Fetch the GitHub login `gh` is currently authenticated as.

    Repo-independent (unlike every other `_fetch_*` helper here): the authenticated identity is
    the same regardless of which PR or repository is being watched, so this call takes no
    `owner`/`repo`/`pr` arguments.

    Args:
        gh_timeout: Seconds to bound the underlying `gh` call to, or `None` for no bound — see
            `run_gh`.

    Returns:
        The authenticated user's login, e.g. `"jane-doe"`.
    """
    return run_gh(["api", "user", "--jq", ".login"], timeout=gh_timeout).strip()


def _fetch_head_state(owner: str, repo: str, pr: int, *, gh_timeout: float | None) -> PullRequestHeadState:
    """Fetch the PR's head-commit date and its three reviewability fields in one GraphQL query.

    The commit date is read via GraphQL's `commits(last: 1)` rather than the REST
    `GET /repos/{owner}/{repo}/pulls/{pr}/commits` endpoint: that endpoint is documented as listing
    a maximum of 250 commits total regardless of pagination, so `--paginate` cannot retrieve a
    commit beyond that hard cap — on a PR with more than 250 commits, its last element would not
    reliably be the actual head. GraphQL's `commits` connection has no such flat cap; requesting
    `last: 1` asks the server directly for the tail element regardless of how many commits the PR
    has.

    `build_fetch_result` compares a Codex approval reaction's timestamp against the later of that
    date and `_fetch_latest_force_push_at`'s result — this call alone is not sufficient on its own:
    a force-push that creates a brand-new commit (the overwhelmingly common case — a rebase or
    amend) refreshes that commit's own committed date to the time of the push, but a force-push
    that resets the branch back onto a pre-existing commit object (reusing its original, older
    committed date) would not, which is exactly what `_fetch_latest_force_push_at`'s
    server-recorded event timestamp covers instead.

    Args:
        owner: Repository owner login.
        repo: Repository name.
        pr: Pull request number.
        gh_timeout: Seconds to bound the underlying `gh` call to, or `None` for no bound — see
            `run_gh`.

    Returns:
        The PR's draft/mergeable/merge-state fields plus its head commit.

    Raises:
        IndexError: the PR has no commits at all — not possible for a real, open pull request, so
            this is an acceptable boundary failure for an invariant this script does not control.
    """
    raw = run_gh(
        ["api", "graphql", "-f", f"query={_HEAD_STATE_QUERY}", "-f", f"o={owner}", "-f", f"r={repo}", "-F", f"pr={pr}"],
        timeout=gh_timeout,
    )
    return PullRequestHeadState.model_validate(json.loads(raw)["data"]["repository"]["pullRequest"])


def _latest_revision_at(head_state: PullRequestHeadState, force_push_at: datetime | None) -> datetime:
    """The moment the PR's current revision came into being.

    Neither input is sufficient alone. A force-push that creates a brand-new commit — a rebase or
    amend, the overwhelmingly common case — refreshes that commit's own committed date, so the head
    commit carries it. A force-push that resets the branch back onto a pre-existing commit object
    reuses that commit's original, older date, and only the server-recorded event timestamp from
    `_fetch_latest_force_push_at` reflects the push.

    Args:
        head_state: The PR head state from `_fetch_head_state`.
        force_push_at: The most recent force-push timestamp, or `None` if never force-pushed.

    Returns:
        The later of the head commit's date and the force-push timestamp.
    """
    head_commit_date = head_state.commits.nodes[-1].commit.committedDate
    return max(head_commit_date, force_push_at or head_commit_date)


def _reviewability(head_state: PullRequestHeadState) -> Reviewability:
    """Derive whether this PR can be reviewed at all, and say what is stopping it if not.

    Only two conditions produce a blocker, because only these two stop reviews from happening:
    a draft PR does not get reviewers requested, and a conflicting one does not get review runs.
    `mergeStateStatus` is reported as data but drives no blocker of its own — its `DRAFT` and
    `DIRTY` values restate `isDraft` and `mergeable` respectively, and its remaining values
    (`BLOCKED`, `BEHIND`, `UNSTABLE`, `HAS_HOOKS`) describe merge readiness, not reviewability.

    `mergeable: "UNKNOWN"` yields no blocker on purpose — see `Reviewability`.

    Args:
        head_state: The PR-level fields from `_fetch_head_state`.

    Returns:
        The three fields as reported, plus a plain-sentence blocker per condition present.
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


def _fetch_latest_force_push_at(owner: str, repo: str, pr: int, *, gh_timeout: float | None) -> datetime | None:
    """Fetch the timestamp of the PR's most recent force-push, if it has ever had one.

    A `HeadRefForcePushedEvent` is a server-recorded timeline entry created at the moment of the
    force-push itself, independent of any commit's own embedded author/committer metadata — the
    signal `_fetch_head_state` cannot provide on its own for a force-push that resets the
    branch back onto a pre-existing commit object (see that function's docstring).

    Args:
        owner: Repository owner login.
        repo: Repository name.
        pr: Pull request number.
        gh_timeout: Seconds to bound the underlying `gh` call to, or `None` for no bound — see
            `run_gh`.

    Returns:
        The most recent force-push's timestamp, or `None` if this PR's head has never been
        force-pushed.
    """
    raw = run_gh(
        [
            "api",
            "graphql",
            "-f",
            f"query={_LATEST_FORCE_PUSH_QUERY}",
            "-f",
            f"o={owner}",
            "-f",
            f"r={repo}",
            "-F",
            f"pr={pr}",
        ],
        timeout=gh_timeout,
    )
    nodes = json.loads(raw)["data"]["repository"]["pullRequest"]["timelineItems"]["nodes"]
    events = [ForcePushEvent.model_validate(node) for node in nodes]
    return events[-1].createdAt if events else None


def _review_effective_timestamp(review: ReviewNode) -> datetime:
    """The timestamp representing the newest content this review's body currently carries.

    A review's `submittedAt` never changes once set, but its `body` can be edited afterward —
    GitHub's `lastEditedAt` reflects that edit. Whichever of the two is later is the review's
    effective timestamp for `unresponded_reviews`'s "has this workflow responded since" comparison
    in `build_fetch_result` — using `submittedAt` alone would let a post-response edit go unnoticed
    forever, since the original submission time already predates the response.

    Args:
        review: A review already known to have been submitted (`submittedAt is not None`) — see
            `build_fetch_result`, the only caller, which filters not-yet-submitted reviews first.

    Returns:
        The later of `submittedAt` and `lastEditedAt`.

    Raises:
        TypeError: `review.submittedAt` is `None` — the caller must exclude not-yet-submitted
            reviews before calling this, since they have no meaningful timestamp to compare.
    """
    if review.submittedAt is None:
        message = "_review_effective_timestamp requires an already-submitted review"
        raise TypeError(message)
    if review.lastEditedAt is None:
        return review.submittedAt
    return max(review.submittedAt, review.lastEditedAt)


def _references_review(comment_body: str, review_url: str) -> bool:
    """Whether `comment_body` quotes `review_url` as a complete permalink, not a mere id prefix.

    A review's `url` ends in its own numeric database id (`#pullrequestreview-<id>`), and plain
    substring containment does not enforce a boundary at the end of that id: id `123` is itself a
    substring of id `1234`, so a comment quoting only the longer permalink would also satisfy a
    naive `review.url in comment_body` check for the shorter, unrelated review. Requiring the
    character immediately after the match (if any) to not be a digit rules that out while still
    matching the common case of the URL followed by punctuation, whitespace, or the end of the
    comment.

    Args:
        comment_body: One PR-level comment's body text.
        review_url: The specific review's own canonical permalink to look for.

    Returns:
        `True` when `review_url` appears in `comment_body` with no trailing digit immediately
        after it.
    """
    return re.search(re.escape(review_url) + r"(?!\d)", comment_body) is not None


def _is_codex_empty_review(review: ReviewNode) -> bool:
    """Whether `review` is Codex's fixed no-findings wrapper, carrying no feedback of its own.

    Codex posts a review with this same boilerplate body on every push regardless of what it
    finds — real findings, when present, arrive separately as inline thread comments already
    tracked through `unresolved`/`resolve`, never in this top-level review's own body. Matching
    with `fullmatch` against the whole stripped body (not `.search()`) is what rejects a review
    that tucks a real finding anywhere outside the template's own variable slot — including after
    the fixed footer's closing `</details>` tag, where a `.search()` for the fixed pieces alone
    would still match and silently miss the addition — see `_CODEX_EMPTY_REVIEW_BODY`.

    Args:
        review: A review whose body is non-empty (`reviews_with_body`).

    Returns:
        `True` only when `review` is authored by the Codex bot (see `_CODEX_REACTOR_LOGINS`) and
        its body is exactly the boilerplate no-findings template — not merely a review that
        contains the template text somewhere alongside real findings.
    """
    return (
        review.author is not None
        and review.author.login.lower() in _CODEX_REACTOR_LOGINS
        and _CODEX_EMPTY_REVIEW_BODY.fullmatch(review.body.strip()) is not None
    )


def _unresponded_reviews(reviews_with_body: list[ReviewNode], own_comments: list[IssueComment]) -> list[ReviewNode]:
    """Which of `reviews_with_body` this workflow has not yet explicitly responded to.

    A Codex review whose entire body is its own fixed no-findings boilerplate (see
    `_is_codex_empty_review`) is excluded up front — every push posts a fresh one regardless of
    findings, and responding to it is pure busywork with no informational value. A Codex review
    that carries real content beyond that template is not excluded and follows the same rule as
    any other review below.

    A review counts as responded only when at least one of this workflow's own PR-level comments
    both quotes that review's own `url` (its canonical GitHub permalink, matched as a complete id —
    see `_references_review`) *and* postdates the review's effective timestamp — the later of
    `submittedAt`/`lastEditedAt`, see `_review_effective_timestamp`. Requiring an explicit
    reference, rather than inferring a match purely from chronological order, prevents an unrelated
    administrative comment — e.g. a cross-thread sequencing decision, explicitly sanctioned by the
    receiving-pr-reviews skill's own workflow step 6 — from being mistaken for a response to
    whatever review happens to be newest at the time it is posted. Requiring the reference to also
    postdate the review's effective timestamp still catches an editor adding new feedback to an
    already-referenced review after the fact. One comment referencing multiple reviews' URLs
    correctly clears all of them; no review is limited to being "claimed" by only one comment. A
    review with no `submittedAt` (not yet actually submitted) is excluded rather than treated as
    always-unresponded.

    Args:
        reviews_with_body: Every review whose summary text is non-empty, in any order.
        own_comments: Every PR-level comment authored by the currently-authenticated `gh` identity,
            in any order.

    Returns:
        Every unresponded review, in `reviews_with_body`'s original order.
    """
    return [
        review
        for review in reviews_with_body
        if review.submittedAt is not None
        and not _is_codex_empty_review(review)
        and not any(
            _references_review(comment.body, review.url) and comment.created_at >= _review_effective_timestamp(review)
            for comment in own_comments
        )
    ]


def _is_codex_thumbs_up(reaction: Reaction) -> bool:
    """Whether `reaction` is Codex's approval signal — a "+1" from its bot account.

    Args:
        reaction: One reaction fetched by `_fetch_pr_reactions`.

    Returns:
        `True` when `reaction` is a thumbs-up left by exactly the Codex bot's known login (either
        GraphQL or REST shape — see `_CODEX_REACTOR_LOGINS`), not merely a login that starts with
        the same text.
    """
    return (
        reaction.content == "+1" and reaction.user is not None and reaction.user.login.lower() in _CODEX_REACTOR_LOGINS
    )


def gh_timeout_budget(deadline: float | None, gh_timeout: float | None) -> float | None:
    """Choose the timeout for one `gh` call.

    `deadline` is `None` for a plain `fetch` and for `watch`'s mandatory first fetch: neither has a
    window to respect, so the caller's `--gh-timeout-seconds` applies unchanged (`None` = no
    bound). `watch` passes its own `deadline` for each *poll*, so all seven of
    `build_fetch_result`'s `gh` calls are bounded by whatever is actually left, re-measured between
    them, rather than by a fixed reservation subtracted from every poll regardless of how fast
    GitHub responds.

    Args:
        deadline: A `time.monotonic()` timestamp to respect, or `None` for no deadline.
        gh_timeout: The caller's own per-call bound, used when there is no deadline.

    Returns:
        Seconds to pass as `run_gh`'s `timeout`, or `None` for no bound.
    """
    if deadline is None:
        return gh_timeout
    return max(0.0, deadline - time.monotonic())


def build_fetch_result(
    owner: str, repo: str, pr: int, *, deadline: float | None = None, gh_timeout: float | None = None
) -> FetchResult:
    """Fetch and assemble one PR's full outstanding-work snapshot: threads, reviews, and approval.

    Shared by `fetch` (prints the result once, `deadline=None`) and `watch` (calls this repeatedly
    on a polling interval, passing its own deadline) so both subcommands assemble a `FetchResult`
    identically. Makes seven `gh` calls, each independently bounded by `gh_timeout_budget(deadline)`:
    the paginated review-threads query, the paginated reviews query, every PR-level issue comment
    (for `unresponded_reviews`), every reaction on the PR itself (for `codex_approved`), the
    currently-authenticated `gh` identity (also for `unresponded_reviews`), and the PR's head
    commit date plus its most recent force-push timestamp, if any (both also for `codex_approved`
    — see `_fetch_head_state` and `_fetch_latest_force_push_at`). Every one of the seven is
    a fresh snapshot taken by this call alone — nothing here is compared against an earlier call's
    result, which is what makes two `watch` calls back to back, or a `watch` call issued right
    after a `fetch`, incapable of missing or double-counting activity that happened in between (the
    failure mode a per-invocation in-memory baseline used to have).

    `unresponded_reviews` is every `reviews_with_body` entry `_unresponded_reviews` cannot find an
    explicit, postdating reference to among the currently-authenticated `gh` identity's own
    PR-level comments — see that function for why a review's own `url` must be quoted in a comment
    that postdates the review's effective timestamp (the later of `submittedAt`/`lastEditedAt`),
    rather than inferring a match purely from chronological order: an unrelated administrative
    comment that merely postdates a review (e.g. a cross-thread sequencing decision this skill's
    own workflow sanctions) is not evidence it addressed that review's feedback, and a plain
    chronological cutover cannot tell the two apart. Comments from any other account are ignored
    for the same reason a comment without any reference is. A review with no `submittedAt` (not
    yet actually submitted) is excluded rather than treated as always-unresponded. A Codex review
    whose entire body is its own fixed no-findings boilerplate is excluded up front, before any of
    the above — see `_is_codex_empty_review` — since every push posts a fresh one regardless of
    findings and responding to it has no informational value.

    `codex_approved` is `True` when a "+1" reaction from exactly the Codex bot's known login (not
    merely one that starts with the same text — see `_CODEX_REACTOR_LOGINS`) exists on the PR
    itself at the moment of this call *and* that reaction's own timestamp is at or after the later
    of the PR's current head commit's date and its most recent force-push timestamp, if any — see
    `_fetch_pr_reactions`, `_fetch_head_state`, and `_fetch_latest_force_push_at`. Neither
    date alone is sufficient: a reaction left approving an earlier revision would otherwise keep
    reporting as approval indefinitely, even after a later push the reaction never actually saw,
    including a force-push that resets the branch back onto a pre-existing commit object whose own
    embedded date predates the reaction.

    Args:
        owner: Repository owner login.
        repo: Repository name.
        pr: Pull request number.
        deadline: A `time.monotonic()` timestamp the caller wants this call's seven `gh`
            invocations to respect — see `gh_timeout_budget`. `None` means no deadline.
        gh_timeout: Per-call bound applied when `deadline` is `None`; `None` means no bound.

    Returns:
        Totals plus every currently-unresolved thread, every unresponded review, and whether
        Codex's approval reaction is present right now for the current revision.
    """
    thread_pages = _fetch_pages(owner, repo, pr, gh_timeout=gh_timeout_budget(deadline, gh_timeout))
    review_pages = _fetch_review_pages(owner, repo, pr, gh_timeout=gh_timeout_budget(deadline, gh_timeout))
    issue_comments = _fetch_issue_comments(owner, repo, pr, gh_timeout=gh_timeout_budget(deadline, gh_timeout))
    reactions = _fetch_pr_reactions(owner, repo, pr, gh_timeout=gh_timeout_budget(deadline, gh_timeout))
    authenticated_login = _fetch_authenticated_login(gh_timeout=gh_timeout_budget(deadline, gh_timeout))
    head_state = _fetch_head_state(owner, repo, pr, gh_timeout=gh_timeout_budget(deadline, gh_timeout))
    latest_force_push_at = _fetch_latest_force_push_at(
        owner, repo, pr, gh_timeout=gh_timeout_budget(deadline, gh_timeout)
    )
    latest_revision_at = _latest_revision_at(head_state, latest_force_push_at)

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

    own_comments = [
        comment for comment in issue_comments if comment.user is not None and comment.user.login == authenticated_login
    ]
    unresponded_reviews = _unresponded_reviews(reviews_with_body, own_comments)
    codex_approved = any(
        _is_codex_thumbs_up(reaction) and reaction.created_at >= latest_revision_at for reaction in reactions
    )

    return FetchResult(
        reviews_count=review_pages[0].totalCount,
        reviews_with_body=reviews_with_body,
        unresponded_reviews=unresponded_reviews,
        threads_count=thread_pages[0].totalCount,
        unresolved=unresolved,
        unresolved_count=len(unresolved),
        codex_approved=codex_approved,
        reviewability=_reviewability(head_state),
    )

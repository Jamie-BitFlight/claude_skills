"""Shared fake-GitHub test harness for the item-fields-in-head-record test suite.

Fakes exactly two seams -- the network and the Contents API store -- and
nothing else. A test built on this harness always drives a real
``GitHubBackend`` over a real ``FileCache``, through the real ``operations``
and ``reconciliation`` modules; only the bytes that would otherwise cross the
wire to GitHub are faked. See ``backlog_core/ARCHITECTURE.md`` and the
item-fields-in-head-record design doc, section 6, for the boundary this
harness is required to hold.

``FakeGitHubNetwork`` stands in for one GitHub repository: issues, their
labels, and their comments, addressed the same way the real GraphQL API
addresses them (issue numbers, GraphQL node ids). ``FakeContentsStore`` stands
in for the dedicated Contents-API branch that carries work-item head records,
with the same create-only / expected-revision CAS semantics as
``backends/github_contents.py``'s real store.

``install_fake_network`` monkeypatches every ``gh_client`` module-level
network primitive onto one ``FakeGitHubNetwork`` -- this covers both
``GitHubBackend``'s thin delegations to those functions and ``operations.py``'s
direct module-level calls (``try_get_github``, ``close_github_issue``, ...).
The one exception is ``GitHubBackend._fetch_targeted_issues``, which is not a
``gh_client`` function -- it is implemented directly on ``GitHubBackend`` and
is overridden per-instance instead (see ``new_backend``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest
from github import GithubException

from backlog_core import gh_client
from backlog_core.backend_types import AddedCommentNode, IssueCommentNode, IssueNode, MilestoneNode
from backlog_core.backends.github_backend import GitHubBackend
from backlog_core.file_cache import FileCache
from backlog_core.models import (
    ContentConflictError,
    ContentNotFoundError,
    ContentQuery,
    ContentRecord,
    ContentRef,
    ContentWrite,
)

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from github.Repository import Repository

_HTTP_NOT_FOUND = 404


@dataclass
class FakeIssue:
    """One fake GitHub issue, addressed the same way the real API addresses it."""

    number: int
    node_id: str
    title: str = ""
    body: str = ""
    state: str = "OPEN"
    labels: list[str] = field(default_factory=list)
    created_at: str = "2026-01-01T00:00:00Z"
    updated_at: str = "2026-01-01T00:00:00Z"
    milestone: MilestoneNode | None = None
    assignees: list[str] = field(default_factory=list)
    # Comment node ids, in post order -- lets a test assert "no new comment"
    # by length, and resolve "the newest comment" by [-1].
    comment_ids: list[str] = field(default_factory=list)

    def as_node(self, label_ids: dict[str, str]) -> IssueNode:
        return IssueNode(
            id=self.node_id,
            number=self.number,
            title=self.title,
            state=self.state,
            body=self.body,
            createdAt=self.created_at,
            updatedAt=self.updated_at,
            labels=[{"id": label_ids.get(name, f"LABEL_{name}"), "name": name} for name in self.labels],
            milestone=self.milestone,
            assignees=[{"login": login} for login in self.assignees],
        )


class FakeGitHubNetwork:
    """Stand-in for one GitHub repository's issues, labels, and comments.

    Every method mirrors the signature of the ``gh_client`` module-level
    function or ``GitHubBackend`` method it replaces (see ``install_fake_network``
    and ``new_backend``). Card 5's error-injection tests use ``fail_once`` to
    make one named method raise a supplied exception exactly one time.
    """

    def __init__(self, repo_full_name: str = "owner/repo") -> None:
        self.repo_full_name = repo_full_name
        self.issues: dict[int, FakeIssue] = {}
        self.comments: dict[str, dict[str, object]] = {}
        self.labels: dict[str, str] = {}
        self._next_issue_number = 1
        self._next_comment_id = 1
        self._next_label_id = 1
        self._failures: dict[str, list[Exception]] = {}
        self.repo = FakeRepo(self)

    # -- test setup / error injection --------------------------------------

    def seed_label(self, name: str) -> str:
        """Register a repository label as if it already existed, returning its node id."""
        return self._label_id(name)

    def add_issue(
        self,
        *,
        number: int | None = None,
        node_id: str = "",
        title: str = "",
        body: str = "",
        state: str = "OPEN",
        labels: list[str] | None = None,
        created_at: str = "2026-01-01T00:00:00Z",
        updated_at: str = "2026-01-01T00:00:00Z",
        milestone: MilestoneNode | None = None,
        assignees: list[str] | None = None,
    ) -> FakeIssue:
        """Create and register a fake issue, returning it for the test to hold onto."""
        resolved_number = number if number is not None else self._next_issue_number
        self._next_issue_number = max(self._next_issue_number, resolved_number + 1)
        issue = FakeIssue(
            number=resolved_number,
            node_id=node_id or f"ISSUE_{resolved_number}",
            title=title,
            body=body,
            state=state,
            labels=labels or [],
            created_at=created_at,
            updated_at=updated_at,
            milestone=milestone,
            assignees=assignees or [],
        )
        for name in issue.labels:
            self._label_id(name)
        self.issues[issue.number] = issue
        return issue

    def fail_once(self, method_name: str, exc: Exception) -> None:
        """Make the named fake method raise *exc* exactly once, on its next call."""
        self._failures.setdefault(method_name, []).append(exc)

    def _maybe_raise(self, method_name: str) -> None:
        queued = self._failures.get(method_name)
        if queued:
            raise queued.pop(0)

    def _label_id(self, name: str) -> str:
        if name not in self.labels:
            self.labels[name] = f"LABEL_{self._next_label_id}"
            self._next_label_id += 1
        return self.labels[name]

    def latest_comment_id(self, number: int) -> str | None:
        comment_ids = self.issues[number].comment_ids
        return comment_ids[-1] if comment_ids else None

    # -- gh_client module-level fakes ---------------------------------------

    def get_github(self, repo: str = "", timeout: int = 15) -> FakeRepo:
        self._maybe_raise("get_github")
        return self.repo

    def try_get_github(self, repo: str = "") -> FakeRepo:
        self._maybe_raise("try_get_github")
        return self.repo

    def _fetch_issue_graphql(self, repo: Repository, owner: str, repo_name: str, issue_number: int) -> IssueNode:
        self._maybe_raise("_fetch_issue_graphql")
        issue = self.issues.get(issue_number)
        if issue is None:
            raise gh_client.BacklogError(f"Issue not found: #{issue_number}")
        return issue.as_node(self.labels)

    def _fetch_issues_graphql(
        self,
        repo: Repository,
        owner: str,
        repo_name: str,
        state: str = "OPEN",
        labels: list[str] | None = None,
        milestone_number: int | None = None,
        first: int = 100,
        since: str | None = None,
    ) -> list[IssueNode]:
        self._maybe_raise("_fetch_issues_graphql")
        wanted_states = set(state.split(","))
        results = [issue for issue in self.issues.values() if issue.state in wanted_states]
        if labels:
            results = [issue for issue in results if set(labels).issubset(issue.labels)]
        return [issue.as_node(self.labels) for issue in sorted(results, key=lambda issue: issue.number)]

    def _fetch_issues_page_graphql(
        self,
        repo: Repository,
        owner: str,
        repo_name: str,
        *,
        states: list[str],
        labels: list[str] | None = None,
        milestone_number: int | None = None,
        since: str | None = None,
        first: int = 100,
        after: str | None = None,
        light: bool = False,
    ) -> gh_client.IssuesPage:
        """Fake for the one-page ``ListIssues`` read the request-shaped list path uses (#3969)."""
        self._maybe_raise("_fetch_issues_page_graphql")
        matching = self._fetch_issues_graphql(repo, owner, repo_name, ",".join(states), labels=labels)
        start = int(after) if after else 0
        page = matching[start : start + first]
        has_next = start + first < len(matching)
        return gh_client.IssuesPage(
            issues=page,
            has_next_page=has_next,
            end_cursor=str(start + first) if has_next else None,
            total_count=len(matching),
        )

    def _fetch_issue_comments_graphql(
        self, repo: Repository, owner: str, repo_name: str, issue_number: int, *, latest: int | None = None
    ) -> list[IssueCommentNode]:
        """Fake for the issue-comment read (the audit-comment reuse check reads the newest page)."""
        self._maybe_raise("_fetch_issue_comments_graphql")
        issue = self.issues[issue_number]
        comments = [gh_client._parse_comment_node(self.comments[comment_id]) for comment_id in issue.comment_ids]
        return comments[-latest:] if latest is not None else comments

    def fetch_targeted_issues(
        self, repo: Repository, owner: str, repo_name: str, references: list[str]
    ) -> dict[str, IssueNode | None]:
        """Fake for GitHubBackend's own ``_fetch_targeted_issues`` (not a gh_client function)."""
        self._maybe_raise("_fetch_targeted_issues")
        resolved: dict[str, IssueNode | None] = {}
        for reference in references:
            number = int(reference.removeprefix("#"))
            issue = self.issues.get(number)
            resolved[reference] = issue.as_node(self.labels) if issue is not None else None
        return resolved

    def _add_comment_graphql(self, repo: Repository, issue_node_id: str, body: str) -> AddedCommentNode:
        self._maybe_raise("_add_comment_graphql")
        issue = self._issue_by_node_id(issue_node_id)
        comment_id = f"COMMENT_{self._next_comment_id}"
        database_id = self._next_comment_id
        self._next_comment_id += 1
        self.comments[comment_id] = {
            "id": comment_id,
            "body": body,
            "url": f"https://github.com/{self.repo_full_name}/issues/{issue.number}#issuecomment-{database_id}",
            "author": "dh-agent",
            "createdAt": issue.updated_at,
            "updatedAt": issue.updated_at,
            "fullDatabaseId": database_id,
        }
        issue.comment_ids.append(comment_id)
        return AddedCommentNode(id=comment_id, database_id=database_id)

    def _fetch_comment_by_id_graphql(self, repo: Repository, comment_node_id: str) -> IssueCommentNode:
        self._maybe_raise("_fetch_comment_by_id_graphql")
        raw = self.comments.get(comment_node_id)
        if raw is None:
            raise gh_client.BacklogError(f"Comment not found: {comment_node_id!r}")
        return gh_client._parse_comment_node(raw)

    def _graphql_request(
        self, repo: Repository, query: str, variables: dict[str, object] | None = None
    ) -> dict[str, object]:
        """Fake for the raw AuditComments and SearchPRs queries used outside apply_patches."""
        self._maybe_raise("_graphql_request")
        variables = variables or {}
        if "SearchPRs" in query:
            # close_item/resolve_item always check for open PRs first -- no fake
            # issue in this harness is ever referenced by an open PR.
            return {"search": {"nodes": []}}
        if "AuditComments" not in query:
            raise NotImplementedError(f"FakeGitHubNetwork._graphql_request has no fake for this query: {query[:80]!r}")
        ids = variables.get("ids")
        if not isinstance(ids, list):
            raise gh_client.BacklogError("AuditComments query missing 'ids' variable")
        nodes = []
        for comment_id in ids:
            raw = self.comments.get(comment_id)
            if raw is None:
                raise gh_client.BacklogError(f"Comment not found: {comment_id!r}")
            nodes.append({
                "id": raw["id"],
                "body": raw["body"],
                "url": raw["url"],
                "author": {"login": raw["author"]},
                "createdAt": raw["createdAt"],
                "updatedAt": raw["updatedAt"],
            })
        return {"nodes": nodes}

    def _create_issue_graphql(
        self, repo: Repository, repo_node_id: str, title: str, body: str, label_ids: list[str]
    ) -> gh_client.CreatedIssueNode:
        self._maybe_raise("_create_issue_graphql")
        names_by_id = {node_id: name for name, node_id in self.labels.items()}
        issue = self.add_issue(title=title, body=body, labels=[names_by_id[i] for i in label_ids if i in names_by_id])
        return {
            "id": issue.node_id,
            "number": issue.number,
            "title": issue.title,
            "url": f"https://github.com/{self.repo_full_name}/issues/{issue.number}",
        }

    def _resolve_label_ids_graphql(
        self, repo: Repository, owner: str, repo_name: str, label_names: list[str]
    ) -> dict[str, str]:
        self._maybe_raise("_resolve_label_ids_graphql")
        return {name: self.labels[name] for name in label_names if name in self.labels}

    def _update_issue_graphql(
        self,
        repo: Repository,
        issue_node_id: str,
        *,
        state: str | None = None,
        body: str | None = None,
        title: str | None = None,
        label_ids: list[str] | None = None,
        milestone_id: str | None = None,
    ) -> None:
        self._maybe_raise("_update_issue_graphql")
        issue = self._issue_by_node_id(issue_node_id)
        if state is not None:
            issue.state = state
        if body is not None:
            issue.body = body
        if title is not None:
            issue.title = title
        if label_ids is not None:
            names_by_id = {node_id: name for name, node_id in self.labels.items()}
            issue.labels = [names_by_id[i] for i in label_ids if i in names_by_id]

    def _update_issue_comment_graphql(self, repo: Repository, comment_node_id: str, body: str) -> None:
        self._maybe_raise("_update_issue_comment_graphql")
        raw = self.comments.get(comment_node_id)
        if raw is None:
            raise gh_client.BacklogError(f"Comment not found: {comment_node_id!r}")
        raw["body"] = body

    def _issue_by_node_id(self, node_id: str) -> FakeIssue:
        for issue in self.issues.values():
            if issue.node_id == node_id:
                return issue
        raise gh_client.BacklogError(f"Issue node not found: {node_id!r}")


class FakeRepo:
    """Minimal PyGithub ``Repository`` stand-in -- only the REST label calls."""

    def __init__(self, network: FakeGitHubNetwork) -> None:
        self._network = network
        self.full_name = network.repo_full_name
        self.node_id = f"REPO_{network.repo_full_name}"

    def get_label(self, name: str) -> object:
        if name not in self._network.labels:
            raise GithubException(_HTTP_NOT_FOUND, {"message": "Not Found"}, None)
        return {"name": name}

    def get_labels(self) -> list[SimpleNamespace]:
        """List every label, as ``ensure_dh_labels`` reads it (one REST listing, ``.name`` only)."""
        return [SimpleNamespace(name=name) for name in self._network.labels]

    def create_label(self, name: str, color: str = "", description: str = "") -> object:
        self._network._label_id(name)
        return {"name": name, "color": color}


class FakeContentsStore:
    """Stand-in for the dedicated Contents-API branch holding work-item heads.

    Mirrors ``backends/github_contents.py``'s ``_GitHubContentsStore`` CAS
    semantics exactly (see ``_record_for_write`` there): ``create_only`` fails
    when a record already exists, a truthy ``expected_revision`` must match
    the current revision, and an unconditional write (neither set) with an
    existing record overwrites it -- the shape ``apply_patches`` never
    actually sends, but kept faithful to the real store rather than narrowed
    to only what today's callers use.
    """

    def __init__(self) -> None:
        self._store: dict[tuple[str, str, str, str], dict[str, str]] = {}
        self._next_revision = 1
        self._put_failures: list[Exception] = []

    def fail_put_once(self, exc: Exception) -> None:
        """Make the next ``put`` call raise *exc* exactly once (card 5's CAS-retry case)."""
        self._put_failures.append(exc)

    @staticmethod
    def _key(reference: ContentRef) -> tuple[str, str, str, str]:
        return (reference.kind.value, reference.namespace, reference.artifact_type, reference.name)

    def get(self, reference: ContentRef) -> ContentRecord:
        entry = self._store.get(self._key(reference))
        if entry is None:
            raise ContentNotFoundError(f"No content for {reference!r}")
        return ContentRecord(
            reference=reference,
            owner_reference=reference.namespace,
            content=entry["content"],
            revision=entry["revision"],
        )

    def get_many(self, references: Sequence[ContentRef]) -> Sequence[ContentRecord]:
        records = []
        for reference in references:
            try:
                records.append(self.get(reference))
            except ContentNotFoundError:
                continue
        return records

    def list(self, query: ContentQuery) -> Sequence[ContentRecord]:
        records = [
            ContentRecord(
                reference=ContentRef(kind=query.kind, namespace=namespace, artifact_type=artifact_type, name=name),
                owner_reference=namespace,
                content=entry["content"],
                revision=entry["revision"],
            )
            for (kind, namespace, artifact_type, name), entry in self._store.items()
            if kind == query.kind.value
            and (query.owner_reference is None or namespace == query.owner_reference)
            and query.search.casefold() in name.casefold()
        ]
        records.sort(
            key=lambda record: (record.reference.namespace, record.reference.artifact_type, record.reference.name)
        )
        return records[query.offset : query.offset + query.limit]

    def put(self, request: ContentWrite) -> ContentRecord:
        if self._put_failures:
            raise self._put_failures.pop(0)
        key = self._key(request.reference)
        current = self._store.get(key)
        if request.create_only and current is not None:
            raise ContentConflictError("Content already exists")
        if request.expected_revision and (current is None or current["revision"] != request.expected_revision):
            raise ContentConflictError("Content revision no longer matches")
        revision = f"contents-rev-{self._next_revision}"
        self._next_revision += 1
        self._store[key] = {"content": request.content, "revision": revision}
        return ContentRecord(
            reference=request.reference,
            owner_reference=request.reference.namespace,
            content=request.content,
            revision=revision,
        )


@dataclass
class FakeGitHubHarness:
    """One fake GitHub repository, shared by every backend a test constructs from it.

    ``new_backend`` gives each backend its own real, empty ``FileCache`` --
    the harness's only shared state is the fake network and Contents store,
    which is exactly what a "fresh reader" test needs to prove a value came
    from GitHub, not from a local cache.
    """

    network: FakeGitHubNetwork
    contents: FakeContentsStore
    repo: str

    def new_backend(self, cache_dir: Path) -> GitHubBackend:
        """Return a new GitHubBackend with its own FileCache, sharing this harness's fakes."""
        backend = GitHubBackend(repo=self.repo, cache=FileCache(cache_dir), contents=self.contents)
        # GitHubBackend._fetch_targeted_issues is not a gh_client function --
        # it is implemented directly on GitHubBackend and calls self._graphql_request
        # internally, so it is overridden per-instance rather than by
        # monkeypatching gh_client (see module docstring).
        backend._fetch_targeted_issues = self.network.fetch_targeted_issues  # ty: ignore[invalid-assignment]
        return backend


def install_fake_network(monkeypatch: pytest.MonkeyPatch, network: FakeGitHubNetwork) -> None:
    """Monkeypatch every gh_client network primitive onto *network*.

    Covers both GitHubBackend's delegations to these functions and
    operations.py's direct module-level calls (try_get_github,
    close_github_issue, resolve_github_issue, create_issue_for_item, ...).
    """
    for name in (
        "get_github",
        "try_get_github",
        "_fetch_issue_graphql",
        "_fetch_issues_graphql",
        "_fetch_issues_page_graphql",
        "_fetch_issue_comments_graphql",
        "_add_comment_graphql",
        "_fetch_comment_by_id_graphql",
        "_graphql_request",
        "_create_issue_graphql",
        "_resolve_label_ids_graphql",
        "_update_issue_graphql",
        "_update_issue_comment_graphql",
    ):
        monkeypatch.setattr(gh_client, name, getattr(network, name))


def make_harness(monkeypatch: pytest.MonkeyPatch, *, repo: str = "owner/repo") -> FakeGitHubHarness:
    """Build one fake GitHub repository and wire it into gh_client for this test."""
    network = FakeGitHubNetwork(repo_full_name=repo)
    install_fake_network(monkeypatch, network)
    return FakeGitHubHarness(network=network, contents=FakeContentsStore(), repo=repo)


@pytest.fixture
def fake_github(monkeypatch: pytest.MonkeyPatch) -> FakeGitHubHarness:
    """Pytest fixture: one fake GitHub repository, wired into gh_client for this test."""
    return make_harness(monkeypatch)

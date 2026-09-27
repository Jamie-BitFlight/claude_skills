"""Request-shaped live reads over a fake GitHub GraphQL transport.

Design brief: request-shaped-reads (repository owner, 2026-09). These tests
pin the request COUNT and SHAPE the GitHub backend sends for a list, a
title-selected mutation, and a duplicate/follow-up/normalize scan — not just
the returned rows. Only the network seam is fake: a real ``GitHubBackend``,
a real ``FileCache(tmp_path)``, and a real in-memory content store drive
every read through the actual GraphQL request-building, hydration, and
reconcile-engine code paths. See ``FakeRequester.graphql_query`` for the
in-memory issue table this exercises, mirroring the ``_FakeRequester``
pattern in ``tests/test_github_contents.py``.
"""

from __future__ import annotations

from collections import UserList
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import pytest
from backlog_core.backend_types import ListPageRequest
from backlog_core.backends._github_work_item_versions import (
    WorkItemHead,
    render_work_item_comment,
    root_revision,
    work_item_head_ref,
)
from backlog_core.backends.github_backend import GitHubBackend
from backlog_core.file_cache import FileCache
from backlog_core.models import (
    BackendUnavailableError,
    BacklogItem,
    ContentNotFoundError,
    ContentQuery,
    ContentRecord,
    ContentRef,
    ContentWrite,
    ProviderItem,
)
from backlog_core.parsing import AmbiguousSelectorError
from backlog_core.work_item_decisions import WorkItemDecisionContext

# ---------------------------------------------------------------------------
# In-memory content store — backs the work-item head/comment records a real
# _GitHubContentsStore would keep in the repo's dh-content branch.
# ---------------------------------------------------------------------------


class FakeContentStore:
    """In-memory ``_ContentPersistence`` + ``get_many`` batch reader."""

    def __init__(self) -> None:
        self._records: dict[tuple[str, str, str, str], ContentRecord] = {}
        self.get_many_calls: list[list[ContentRef]] = []

    def _key(self, reference: ContentRef) -> tuple[str, str, str, str]:
        return (reference.kind.value, reference.namespace, reference.artifact_type, reference.name)

    def get(self, reference: ContentRef) -> ContentRecord:
        record = self._records.get(self._key(reference))
        if record is None:
            raise ContentNotFoundError(f"no fake content for {reference!r}")
        return record

    def get_many(self, references: Sequence[ContentRef]) -> Sequence[ContentRecord]:
        self.get_many_calls.append(list(references))
        results: list[ContentRecord] = []
        for reference in references:
            record = self._records.get(self._key(reference))
            if record is not None:
                results.append(record)
        return results

    def put(self, request: ContentWrite) -> ContentRecord:
        record = ContentRecord(reference=request.reference, content=request.content, revision="fake-revision")
        self._records[self._key(request.reference)] = record
        return record

    # NB: named `list`, matching the `_ContentPersistence` Protocol it satisfies
    # structurally -- annotate with `Sequence`, not `list[...]`, so this method
    # never shadows the builtin generic within this class's own annotations.
    def list(self, query: ContentQuery) -> Sequence[ContentRecord]:
        del query
        return list(self._records.values())

    def seed_head(self, reference: str, *, node_id: str, raw_body: str, tracked_body: str, comment_id: str) -> str:
        """Register a fully tracked work-item head + its audit comment.

        Returns:
            The root revision computed for this head (== its parent/root
            revision, since this is the first version).
        """
        root = root_revision(reference, node_id, raw_body)
        head = WorkItemHead.create(reference, root, root, tracked_body, comment_id)
        self.put(ContentWrite(reference=work_item_head_ref(reference), content=head.model_dump_json()))
        return root


# ---------------------------------------------------------------------------
# In-memory issue table + fake GraphQL transport.
# ---------------------------------------------------------------------------


@dataclass
class FakeIssue:
    number: int
    title: str
    state: str = "OPEN"
    raw_body: str = ""
    labels: list[str] = field(default_factory=lambda: ["priority:p1"])
    updated_at: str = ""

    def as_node(self) -> dict[str, Any]:
        return {
            "id": f"I_{self.number}",
            "number": self.number,
            "title": self.title,
            "state": self.state,
            "body": self.raw_body,
            "createdAt": self.updated_at,
            "updatedAt": self.updated_at,
            "labels": {"nodes": [{"name": name, "id": f"L_{name}"} for name in self.labels]},
            "milestone": None,
            "assignees": {"nodes": []},
        }


class RequestLog(UserList):
    """Every GraphQL call this fixture served, in order."""

    def operation_names(self) -> list[str]:
        return [entry["operation"] for entry in self]

    def count_operation(self, operation: str) -> int:
        return sum(1 for entry in self if entry["operation"] == operation)


class FakeRequester:
    """Dispatches ``repo.requester.graphql_query`` by operation name.

    Understands exactly the query shapes this backend sends for a
    request-shaped list, a title search, a targeted resolve, and an audit
    comment batch — anything else is a fixture gap and raises loudly rather
    than silently returning an empty page.
    """

    def __init__(self, fixture: FakeGitHubFixture) -> None:
        self._fixture = fixture
        self.log = RequestLog()

    def graphql_query(self, query: str, variables: dict[str, object]) -> tuple[dict[str, object], dict[str, object]]:
        if "query ListIssues(" in query:
            operation = "ListIssues"
            data = self._list_issues(variables)
        elif "query TargetedIssues(" in query:
            operation = "TargetedIssues"
            data = self._targeted_issues(variables)
        elif "query AuditComments(" in query:
            operation = "AuditComments"
            data = self._audit_comments(variables)
        elif "query IssueTitleSearch(" in query:
            operation = "IssueTitleSearch"
            data = self._title_search(variables)
        elif "query OpenIssueTitles(" in query:
            operation = "OpenIssueTitles"
            data = self._open_issue_titles(variables)
        elif "query GetComment(" in query:
            operation = "GetComment"
            data = self._get_comment(variables)
        elif "mutation AddComment(" in query:
            operation = "AddComment"
            data = self._add_comment(variables)
        else:
            raise AssertionError(f"FakeRequester does not understand this query shape:\n{query}")
        self.log.append({"operation": operation, "variables": dict(variables)})
        return {}, {"data": data}

    def _matching_issues(self, states: list[str], label: str | None) -> list[FakeIssue]:
        issues = [issue for issue in self._fixture.issues.values() if issue.state in states]
        if label:
            issues = [issue for issue in issues if label in issue.labels]
        return sorted(issues, key=lambda issue: issue.updated_at, reverse=True)

    def _list_issues(self, variables: dict[str, object]) -> dict[str, object]:
        states = cast("list[str]", variables.get("states") or [])
        labels = variables.get("labels")
        label = labels[0] if isinstance(labels, list) and labels else None
        matching = self._matching_issues(states, label)
        after = variables.get("after")
        first = cast("int", variables.get("first") or 100)
        start = 0
        if after:
            start = next(i + 1 for i, issue in enumerate(matching) if f"cursor-{issue.number}" == after)
        page = matching[start : start + first]
        has_next = (start + first) < len(matching)
        end_cursor = f"cursor-{page[-1].number}" if page and has_next else None
        return {
            "repository": {
                "issues": {
                    "totalCount": len(matching),
                    "nodes": [issue.as_node() for issue in page],
                    "pageInfo": {"hasNextPage": has_next, "endCursor": end_cursor},
                }
            }
        }

    def _targeted_issues(self, variables: dict[str, object]) -> dict[str, object]:
        repository_data: dict[str, object] = {}
        index = 0
        while f"number{index}" in variables:
            number = cast("int", variables[f"number{index}"])
            issue = self._fixture.issues.get(number)
            repository_data[f"i{index}"] = issue.as_node() if issue is not None else None
            index += 1
        return {"repository": repository_data}

    def _audit_comments(self, variables: dict[str, object]) -> dict[str, object]:
        ids = variables.get("ids")
        if not isinstance(ids, list):
            raise TypeError(f"AuditComments called without an ids list: {variables!r}")
        nodes = [self._fixture.comment_nodes.get(str(comment_id)) for comment_id in ids]
        return {"nodes": nodes}

    def _title_search(self, variables: dict[str, object]) -> dict[str, object]:
        query_text = str(variables.get("searchQuery", ""))
        selector = query_text.split('in:title "', 1)[-1].rsplit('"', 1)[0]
        matches = [issue for issue in self._fixture.issues.values() if selector.lower() in issue.title.lower()]
        matches.sort(key=lambda issue: issue.updated_at, reverse=True)
        return {
            "search": {
                "nodes": [issue.as_node() for issue in matches],
                "pageInfo": {"hasNextPage": False, "endCursor": None},
            }
        }

    def _get_comment(self, variables: dict[str, object]) -> dict[str, object]:
        comment_id = str(variables.get("id", ""))
        return {"node": self._fixture.comment_nodes.get(comment_id)}

    def _add_comment(self, variables: dict[str, object]) -> dict[str, object]:
        new_id = f"IC_new_{len(self._fixture.comment_nodes) + 1}"
        body = str(variables.get("body", ""))
        database_id = 9000 + len(self._fixture.comment_nodes)
        self._fixture.comment_nodes[new_id] = {
            "id": new_id,
            "fullDatabaseId": database_id,
            "body": body,
            "url": "",
            "author": {"login": "tester"},
            "createdAt": "2024-01-01T00:00:00Z",
            "updatedAt": "2024-01-01T00:00:00Z",
        }
        return {"addComment": {"commentEdge": {"node": {"id": new_id, "fullDatabaseId": database_id}}}}

    def _open_issue_titles(self, variables: dict[str, object]) -> dict[str, object]:
        del variables
        open_issues = sorted(
            (issue for issue in self._fixture.issues.values() if issue.state == "OPEN"),
            key=lambda issue: issue.updated_at,
            reverse=True,
        )
        return {
            "repository": {
                "issues": {
                    "nodes": [{"number": issue.number, "title": issue.title} for issue in open_issues],
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                }
            }
        }


class FakeRepository:
    """Structural stand-in for ``github.Repository.Repository``."""

    def __init__(self, fixture: FakeGitHubFixture, owner: str, name: str) -> None:
        self.full_name = f"{owner}/{name}"
        self.node_id = "R_1"
        self.requester = FakeRequester(fixture)


class FakeGitHubFixture:
    """Owns the fake issue table, content store, and transport for one test."""

    def __init__(self, tmp_path: Path, *, owner: str = "owner", name: str = "repo") -> None:
        self.owner, self.name = owner, name
        self.issues: dict[int, FakeIssue] = {}
        self.comment_nodes: dict[str, dict[str, object]] = {}
        self.contents = FakeContentStore()
        self.repository = FakeRepository(self, owner, name)
        self.backend = GitHubBackend(repo=f"{owner}/{name}", cache=FileCache(tmp_path), contents=self.contents)
        self.backend.get_github = lambda repo="", timeout=15: self.repository  # ty: ignore[invalid-assignment]
        self.backend.try_get_github = lambda repo="": self.repository  # ty: ignore[invalid-assignment]

    @property
    def requester(self) -> FakeRequester:
        return self.repository.requester

    def add_tracked_issue(
        self,
        number: int,
        title: str,
        *,
        state: str = "OPEN",
        labels: list[str] | None = None,
        tracked_body: str = "",
        updated_at: str | None = None,
    ) -> FakeIssue:
        """Register an issue with a real, resolvable work-item head + audit comment."""
        reference = f"#{number}"
        node_id = f"I_{number}"
        raw_body = f"raw github body for {reference}"
        comment_id = f"IC_{number}"
        root = self.contents.seed_head(
            reference, node_id=node_id, raw_body=raw_body, tracked_body=tracked_body, comment_id=comment_id
        )
        self.comment_nodes[comment_id] = {
            "id": comment_id,
            "body": render_work_item_comment(root, tracked_body),
            "url": "",
            "author": {"login": "tester"},
            "createdAt": "2024-01-01T00:00:00Z",
            "updatedAt": "2024-01-01T00:00:00Z",
        }
        issue = FakeIssue(
            number=number,
            title=title,
            state=state,
            raw_body=raw_body,
            labels=list(labels) if labels is not None else ["priority:p1"],
            updated_at=updated_at or f"2024-01-01T00:{number % 60:02d}:{number // 60:02d}Z",
        )
        self.issues[number] = issue
        return issue

    def close_issue(self, number: int) -> None:
        self.issues[number].state = "CLOSED"


@pytest.fixture
def fixture(tmp_path: Path) -> FakeGitHubFixture:
    return FakeGitHubFixture(tmp_path)


def _default_request(fixture: FakeGitHubFixture, **overrides: object) -> ListPageRequest:
    return ListPageRequest(repo=f"{fixture.owner}/{fixture.name}", **overrides)  # ty: ignore[invalid-argument-type]


def _items(result: Mapping[str, object]) -> list[dict[str, str | bool]]:
    """Narrow an operations.list_items()-shaped result's heterogeneous ``items`` value."""
    return cast("list[dict[str, str | bool]]", result["items"])


# ---------------------------------------------------------------------------
# T1 — a bounded list does not page repository history.
# ---------------------------------------------------------------------------


def test_t1_limit_one_does_not_page_history(fixture: FakeGitHubFixture) -> None:
    for number in range(1, 121):
        fixture.add_tracked_issue(number, f"open {number}", state="OPEN")
    for number in range(121, 251):
        fixture.add_tracked_issue(number, f"closed {number}", state="CLOSED")

    result = fixture.backend.fetch_page(
        _default_request(fixture, limit=1), match=lambda item, provider: True, force_hydration=False
    )

    list_calls = [entry for entry in fixture.requester.log if entry["operation"] == "ListIssues"]
    assert len(list_calls) == 1, fixture.requester.log
    assert list_calls[0]["variables"]["states"] == ["OPEN"]
    assert list_calls[0]["variables"]["first"] <= 2
    assert result.has_more is True
    assert result.total is None or isinstance(result.total, int)
    assert len(result.items) == 1


# ---------------------------------------------------------------------------
# T2 — hydration only for the rows the page actually returns.
# ---------------------------------------------------------------------------


def test_t2_hydration_only_for_returned_rows(fixture: FakeGitHubFixture) -> None:
    for number in range(1, 121):
        fixture.add_tracked_issue(number, f"open {number}", state="OPEN")
    for number in range(121, 251):
        fixture.add_tracked_issue(number, f"closed {number}", state="CLOSED")

    result = fixture.backend.fetch_page(
        _default_request(fixture, limit=1), match=lambda item, provider: True, force_hydration=False
    )

    assert len(result.items) == 1
    returned_reference = result.items[0].reference
    hydrated_references = {ref.namespace for call in fixture.contents.get_many_calls for ref in call}
    assert hydrated_references == {returned_reference}, fixture.contents.get_many_calls
    audit_calls = [entry for entry in fixture.requester.log if entry["operation"] == "AuditComments"]
    assert len(audit_calls) == 1, audit_calls
    assert audit_calls[0]["variables"]["ids"] == [f"IC_{returned_reference.lstrip('#')}"]


# ---------------------------------------------------------------------------
# T10 — write-through holds exactly the rows the page fetched.
# ---------------------------------------------------------------------------


def test_t10_write_through_holds_exactly_the_hydrated_page(fixture: FakeGitHubFixture) -> None:
    from backlog_core import operations
    from backlog_core.backend_protocol import reset_config, set_config
    from backlog_core.backend_types import BacklogConfig

    for number in range(1, 51):
        fixture.add_tracked_issue(number, f"issue {number}", state="OPEN")

    set_config(BacklogConfig(backend=fixture.backend))
    try:
        result = operations.list_items(limit=2)
    finally:
        reset_config()

    assert result["count"] == 2, result
    listed_references = {item["issue"] for item in _items(result)}
    cached_references = {item.issue for item in fixture.backend.list_work_items()}
    assert cached_references == listed_references, (cached_references, listed_references)
    assert fixture.backend.has_synced_snapshot() is False


# ---------------------------------------------------------------------------
# T4 — offset walk visits every match once, in order, with an exact has_more.
# ---------------------------------------------------------------------------


def test_t4_offset_walk_and_exact_has_more(fixture: FakeGitHubFixture) -> None:
    for number in range(1, 6):
        fixture.add_tracked_issue(number, f"issue {number}", state="OPEN")

    seen_in_order: list[str] = []
    for offset in range(5):
        result = fixture.backend.fetch_page(
            _default_request(fixture, offset=offset, limit=1), match=lambda item, provider: True, force_hydration=False
        )
        assert len(result.items) == 1, (offset, result)
        seen_in_order.append(result.items[0].reference)
        assert result.has_more is (offset < 4), (offset, result.has_more)

    # UPDATED_AT DESC: issue 5 (latest) first, issue 1 (earliest) last, no repeats.
    assert seen_in_order == ["#5", "#4", "#3", "#2", "#1"]


# ---------------------------------------------------------------------------
# T5 — a local, label-less "has a section" predicate pages correctly and
# never overcounts totalCount when it removed rows.
# ---------------------------------------------------------------------------


def test_t5_local_predicate_paging_and_honest_total(fixture: FakeGitHubFixture) -> None:
    unsectioned = {2, 5, 8}
    for number in range(1, 11):
        if number in unsectioned:
            fixture.add_tracked_issue(number, f"issue {number}", state="OPEN", labels=[], tracked_body="")
        else:
            fixture.add_tracked_issue(number, f"issue {number}", state="OPEN")

    def has_section(item: BacklogItem, provider: ProviderItem) -> bool:
        del provider
        return bool(item.section)

    result = fixture.backend.fetch_page(_default_request(fixture, limit=3), match=has_section, force_hydration=False)

    assert len(result.items) == 3
    assert all(item.reference not in {f"#{n}" for n in unsectioned} for item in result.items)
    # Walked to completion (only 10 issues exist) -- total must be exact, never a raw totalCount.
    assert result.total == 7, result.total


# ---------------------------------------------------------------------------
# T6 — pushed filters (label + status) match the pre-existing local semantics.
# ---------------------------------------------------------------------------


def test_t6_pushed_filters_match_local_semantics(fixture: FakeGitHubFixture) -> None:
    from backlog_core import operations
    from backlog_core.backend_protocol import reset_config, set_config
    from backlog_core.backend_types import BacklogConfig

    fixture.add_tracked_issue(
        1, "matching open", state="OPEN", labels=["priority:p1", "type:bug", "status:in-progress"]
    )
    fixture.add_tracked_issue(2, "wrong type", state="OPEN", labels=["priority:p1", "status:in-progress"])
    fixture.add_tracked_issue(3, "wrong status", state="OPEN", labels=["priority:p1", "type:bug", "status:groomed"])
    fixture.add_tracked_issue(
        4, "matching closed", state="CLOSED", labels=["priority:p1", "type:bug", "status:in-progress"]
    )

    set_config(BacklogConfig(backend=fixture.backend))
    try:
        result = operations.list_items(label="type:bug", status="status:in-progress", include_closed=True)
    finally:
        reset_config()

    assert {item["issue"] for item in _items(result)} == {"#1", "#4"}, result
    list_calls = [entry for entry in fixture.requester.log if entry["operation"] == "ListIssues"]
    assert list_calls, fixture.requester.log
    assert list_calls[0]["variables"]["states"] == ["OPEN", "CLOSED"]
    assert set(list_calls[0]["variables"]["labels"]) == {"type:bug", "status:in-progress"}


# ---------------------------------------------------------------------------
# T11 — the cache holds the tracked head's content, not the raw issue body.
# ---------------------------------------------------------------------------


def test_t11_cache_holds_hydrated_head_not_raw_body(fixture: FakeGitHubFixture) -> None:
    from backlog_core import operations
    from backlog_core.backend_protocol import reset_config, set_config
    from backlog_core.backend_types import BacklogConfig

    distinctive = "Tracked head content distinct from the raw issue body."
    fixture.add_tracked_issue(1, "tracked", state="OPEN", tracked_body=distinctive)

    set_config(BacklogConfig(backend=fixture.backend))
    try:
        operations.list_items(limit=1)
    finally:
        reset_config()

    cached = next(item for item in fixture.backend.list_work_items() if item.issue == "#1")
    assert distinctive in cached.description, cached.description
    assert "raw github body" not in cached.description


# ---------------------------------------------------------------------------
# T12 — allow_cached serves exactly the previously cached rows after a failure.
# ---------------------------------------------------------------------------


def test_t12_allow_cached_serves_exactly_the_cached_rows(fixture: FakeGitHubFixture) -> None:
    from backlog_core import operations
    from backlog_core.backend_protocol import reset_config, set_config
    from backlog_core.backend_types import BacklogConfig
    from github import GithubException

    for number in range(1, 51):
        fixture.add_tracked_issue(number, f"issue {number}", state="OPEN")

    set_config(BacklogConfig(backend=fixture.backend))
    try:
        first = operations.list_items(limit=2)
        first_refs = {item["issue"] for item in _items(first)}

        def fail(query: str, variables: dict[str, object]) -> tuple[dict[str, object], dict[str, object]]:
            del query, variables
            raise GithubException(503, {"message": "offline"}, {})

        fixture.repository.requester.graphql_query = fail  # ty: ignore[invalid-assignment]

        with pytest.raises(BackendUnavailableError):
            operations.list_items(limit=2)

        fallback = operations.list_items(limit=2, allow_cached=True)
    finally:
        reset_config()

    assert {item["issue"] for item in _items(fallback)} == first_refs, fallback
    assert fallback["from_cache"] is True
    assert fallback.get("warnings"), fallback


# ---------------------------------------------------------------------------
# T13 — pending intent survives the write-through when it disagrees with GitHub.
# ---------------------------------------------------------------------------


def test_t13_pending_intent_survives_write_through(fixture: FakeGitHubFixture) -> None:
    from backlog_core import operations
    from backlog_core.backend_protocol import reset_config, set_config
    from backlog_core.backend_types import BacklogConfig

    fixture.add_tracked_issue(7, "tracked seven", state="OPEN", tracked_body="Original tracked body.")

    set_config(BacklogConfig(backend=fixture.backend))
    try:
        operations.list_items(limit=1)  # first list -- populates the cache via write-through

        pending = fixture.backend.get_work_item("#7").model_copy(deep=True)
        pending.description = "Locally edited description not yet acknowledged."
        fixture.backend.put_work_item(pending)
        assert fixture.backend.has_pending_writes()

        operations.list_items(limit=1)  # write-through must not clobber or acknowledge disagreeing intent

        assert fixture.backend.has_pending_writes(), "pending intent that disagrees with the provider must survive"
        stored = fixture.backend.get_work_item("#7")
        assert "Locally edited description" in stored.description
    finally:
        reset_config()


# ---------------------------------------------------------------------------
# T14 — refresh reconciles only the rows the page actually listed.
# ---------------------------------------------------------------------------


def test_t14_refresh_reconciles_only_listed_rows(fixture: FakeGitHubFixture) -> None:
    from backlog_core import operations
    from backlog_core.backend_protocol import reset_config, set_config
    from backlog_core.backend_types import BacklogConfig

    fixture.add_tracked_issue(
        8, "listed newer", state="OPEN", tracked_body="Original eight.", updated_at="2024-02-01T00:00:00Z"
    )
    fixture.add_tracked_issue(
        7, "not listed older", state="OPEN", tracked_body="Original seven.", updated_at="2024-01-01T00:00:00Z"
    )

    set_config(BacklogConfig(backend=fixture.backend))
    try:
        operations.list_items(limit=0)  # unbounded first pass -- populates both rows via write-through

        pending_eight = fixture.backend.get_work_item("#8").model_copy(deep=True)
        pending_eight.description = "Edited eight, not yet on GitHub."
        fixture.backend.put_work_item(pending_eight)
        pending_seven = fixture.backend.get_work_item("#7").model_copy(deep=True)
        pending_seven.description = "Edited seven, not yet on GitHub."
        fixture.backend.put_work_item(pending_seven)

        result = operations.list_items(refresh=True, limit=1)
        assert {item["issue"] for item in _items(result)} == {"#8"}, result

        assert fixture.backend.has_synced_snapshot() is False
        # Refresh must not reconcile a row it never listed -- #7's disagreeing
        # intent stays exactly as queued.
        assert fixture.backend.get_work_item("#7").description == "Edited seven, not yet on GitHub."
    finally:
        reset_config()


# ---------------------------------------------------------------------------
# T7 — a title selector resolves through search, not a full list.
# ---------------------------------------------------------------------------


def test_t7_title_selector_is_targeted(fixture: FakeGitHubFixture) -> None:
    for number in range(1, 200):
        fixture.add_tracked_issue(number, f"issue {number}", state="OPEN")
    fixture.add_tracked_issue(199, "a wholly unique groomable title", state="OPEN")

    context = WorkItemDecisionContext(fixture.backend, repo=f"{fixture.owner}/{fixture.name}")
    target = context.select("wholly unique groomable", purpose="mutation")

    assert target.provider is not None
    assert target.provider.issue == "#199", target.provider

    log = fixture.requester.log
    assert log.count_operation("IssueTitleSearch") == 1, log
    assert log.count_operation("ListIssues") == 0, log
    targeted_calls = [entry for entry in log if entry["operation"] == "TargetedIssues"]
    assert len(targeted_calls) == 1, targeted_calls
    numbered_variables = {
        key: value for key, value in targeted_calls[0]["variables"].items() if key.startswith("number")
    }
    assert list(numbered_variables.values()) == [199], numbered_variables
    assert log.count_operation("AuditComments") == 1, log


# ---------------------------------------------------------------------------
# T8 — title ambiguity from search is preserved.
# ---------------------------------------------------------------------------


def test_t8_title_ambiguity_is_preserved(fixture: FakeGitHubFixture) -> None:
    fixture.add_tracked_issue(1, "shared ambiguous phrase alpha", state="OPEN")
    fixture.add_tracked_issue(2, "shared ambiguous phrase beta", state="OPEN")

    context = WorkItemDecisionContext(fixture.backend, repo=f"{fixture.owner}/{fixture.name}")

    with pytest.raises(AmbiguousSelectorError):
        context.select("shared ambiguous phrase", purpose="read")


# ---------------------------------------------------------------------------
# T9 — a search miss falls back to the open-issue titles scan.
# ---------------------------------------------------------------------------


def test_t9_search_miss_falls_back_to_open_titles(fixture: FakeGitHubFixture) -> None:
    fixture.add_tracked_issue(1, "an issue search will not find", state="OPEN")

    context = WorkItemDecisionContext(fixture.backend, repo=f"{fixture.owner}/{fixture.name}")
    # The fake search index only ever returns issues whose title contains the
    # selector -- simulate a genuine miss (tokenization/lag) with a selector
    # that matches nothing in search but everything in the open titles scan.
    original_title_search = fixture.requester._title_search
    fixture.requester._title_search = lambda variables: {  # ty: ignore[invalid-assignment]
        "search": {"nodes": [], "pageInfo": {"hasNextPage": False, "endCursor": None}}
    }
    try:
        target = context.select("an issue search", purpose="read")
    finally:
        fixture.requester._title_search = original_title_search  # ty: ignore[invalid-assignment]

    assert target.provider is not None
    assert target.provider.issue == "#1", target.provider
    log = fixture.requester.log
    assert log.count_operation("OpenIssueTitles") == 1, log
    assert all(
        entry["variables"].get("states") != ["OPEN", "CLOSED"] for entry in log if entry["operation"] == "ListIssues"
    )


# ---------------------------------------------------------------------------
# T15 — whole-set consumers (add_item, normalize_items) never read CLOSED history.
# ---------------------------------------------------------------------------


def test_t15_whole_set_consumers_scan_open_only(fixture: FakeGitHubFixture) -> None:
    from backlog_core.backend_protocol import reset_config, set_config
    from backlog_core.backend_types import BacklogConfig
    from backlog_core.operations import _decision_context, _open_scan

    fixture.add_tracked_issue(1, "an existing open item", state="OPEN")
    fixture.add_tracked_issue(2, "an existing closed item", state="CLOSED")

    set_config(BacklogConfig(backend=fixture.backend))
    try:
        context = _decision_context(repo=f"{fixture.owner}/{fixture.name}")
        scan = _open_scan(context)  # shared by add_item's duplicate check, list_followups, and normalize_items
    finally:
        reset_config()

    assert {item.issue for item in scan.items} == {"#1"}, scan.items
    assert scan.live is True
    list_calls = [entry for entry in fixture.requester.log if entry["operation"] == "ListIssues"]
    assert list_calls, fixture.requester.log
    assert all("CLOSED" not in entry["variables"]["states"] for entry in list_calls), list_calls


def test_t15_force_add_item_probes_instead_of_scanning(fixture: FakeGitHubFixture) -> None:
    from backlog_core.backend_protocol import reset_config, set_config
    from backlog_core.backend_types import BacklogConfig
    from backlog_core.operations import _decision_context, _probe_provider_liveness

    set_config(BacklogConfig(backend=fixture.backend))
    try:
        context = _decision_context(repo=f"{fixture.owner}/{fixture.name}")
        assert _probe_provider_liveness(context) is True
    finally:
        reset_config()

    list_calls = [entry for entry in fixture.requester.log if entry["operation"] == "ListIssues"]
    assert len(list_calls) == 1, fixture.requester.log
    assert "CLOSED" not in list_calls[0]["variables"]["states"], list_calls


# ---------------------------------------------------------------------------
# T17 — the deletions this design requires are gone.
# ---------------------------------------------------------------------------


def test_t17_dead_code_is_removed() -> None:
    import backlog_core.operations as operations_module
    import backlog_core.work_item_decisions as decisions_module

    assert not hasattr(operations_module, "read_through_cold_cache")
    assert not hasattr(decisions_module.WorkItemDecisionContext, "all")

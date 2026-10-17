"""Cross-backend parity tests for milestone operations (backlog #2287, Slice C).

Before this slice, ``operations.list_milestones``/``get_soonest_milestone``/
``create_milestone`` called ``get_github()`` unconditionally, so every
non-GitHub backend failed the capability gate before ever reaching a real
milestone implementation. SQLite shipped a milestone read path over a table
that nothing ever wrote to. These tests drive the ``operations.py`` entry
points (not backend internals directly) against Memory and SQLite to prove
the capability-gated dispatch this slice adds actually reaches working
per-backend milestone create/list/assign implementations.

Memory and SQLite legs run unmarked, in the default test suite — neither
needs network access. The GitHub leg is gated behind the same
``BACKLOG_CROSS_BACKEND_GITHUB`` env var used by ``test_cross_backend.py``.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, cast
from unittest.mock import MagicMock

import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator
from backlog_core import operations
from backlog_core.backend_protocol import reset_config, set_config
from backlog_core.backend_types import BacklogConfig, WorkItemBackend
from backlog_core.backends.memory_backend import InMemoryBackend
from backlog_core.backends.sqlite_backend import SQLiteBackend
from backlog_core.models import (
    BacklogError,
    BacklogItem,
    BacklogItemMetadata,
    UnsupportedBackendCapabilityError,
    ValidationError,
)
from github import GithubException
from github.Repository import Repository as GithubRepository

_MOCK_REPO: GithubRepository = MagicMock(spec=GithubRepository)

_GITHUB_MARKER = pytest.mark.skipif(
    not os.environ.get("BACKLOG_CROSS_BACKEND_GITHUB"),
    reason="Set BACKLOG_CROSS_BACKEND_GITHUB=1 to run GitHub backend tests",
)


@pytest.fixture(
    params=[
        pytest.param("memory", id="InMemoryBackend"),
        pytest.param("sqlite", id="SQLiteBackend"),
        pytest.param("github", id="GitHubBackend", marks=_GITHUB_MARKER),
    ]
)
def backend(request: pytest.FixtureRequest) -> Iterator[WorkItemBackend]:
    """Parametrized fixture installing one backend as the active operations.py config."""
    name: str = request.param
    if name == "memory":
        impl: WorkItemBackend = InMemoryBackend()
    elif name == "sqlite":
        impl = SQLiteBackend(":memory:")
    else:
        from backlog_core.backends.github_backend import GitHubBackend

        impl = GitHubBackend()
    set_config(BacklogConfig(backend=impl))
    yield impl
    reset_config()
    if isinstance(impl, SQLiteBackend):
        impl._conn.close()


def _make_item(title: str) -> BacklogItem:
    return BacklogItem(
        title=title,
        description="",
        metadata=BacklogItemMetadata(
            source="test", added="2026-01-01", priority="P1", item_type="Feature", status="open"
        ),
    )


def _force_milestone_closed(backend: WorkItemBackend, number: int) -> None:
    """Seed a closed milestone independently of the operation exercised by list tests."""
    if isinstance(backend, InMemoryBackend):
        backend._milestones[number]["state"] = "CLOSED"
    elif isinstance(backend, SQLiteBackend):
        backend._conn.execute("UPDATE milestones SET state = 'closed' WHERE number = ?", (number,))
        backend._conn.commit()
    else:
        from backlog_core.backends.github_backend import GitHubBackend

        repository = cast("GitHubBackend", backend).get_github()
        milestone_obj = repository.get_milestone(number)
        milestone_obj.edit(title=milestone_obj.title, state="closed")


def _skip_github_shared_state(backend: WorkItemBackend) -> None:
    """Skip on GitHub: assertions here assume a pristine milestone set.

    Memory/SQLite get a brand-new backend instance per test. The GitHub leg
    targets one real, persistent, possibly non-empty repository with no
    cleanup between test runs — an exact-match or no-earlier-milestone
    assumption cannot hold there without live remote cleanup this slice
    doesn't add.
    """
    if not isinstance(backend, (InMemoryBackend, SQLiteBackend)):
        pytest.skip("GitHub backend milestone state is not guaranteed pristine across runs")


def _repo_for_create_issue(backend: WorkItemBackend) -> GithubRepository:
    """Return the repository argument to pass to ``create_issue_for_item``.

    Memory/SQLite document this argument as ignored, so the shared mock is
    fine there. GitHubBackend genuinely uses it (``gh_client.create_issue_for_item``
    reads ``repo.full_name``), so it needs the real configured repository —
    passing ``_MOCK_REPO`` there raises before ever reaching milestone
    assignment, silently skipping the GitHub leg of the decisive test below.
    """
    if isinstance(backend, (InMemoryBackend, SQLiteBackend)):
        return _MOCK_REPO
    from backlog_core.backends.github_backend import GitHubBackend

    return cast("GitHubBackend", backend).get_github()


# ---------------------------------------------------------------------------
# 1. Shape parity
# ---------------------------------------------------------------------------


def test_create_milestone_shape_parity(backend: WorkItemBackend) -> None:
    """create_milestone returns an identical key set on every backend, with a non-None identifier."""
    result = operations.create_milestone(title="v1.0")
    ms = cast("dict[str, object]", result["milestone"])
    assert set(ms) == {"number", "title", "state", "description", "due_on", "open_issues", "closed_issues"}
    assert ms["number"] is not None


# ---------------------------------------------------------------------------
# 2. Write -> read round-trip
# ---------------------------------------------------------------------------


def test_write_read_round_trip(backend: WorkItemBackend) -> None:
    """A created milestone is readable via list_milestones with matching fields, due_on normalized to UTC Z."""
    created = cast(
        "dict[str, object]",
        operations.create_milestone(title="v1.0", description="desc", due_on="2026-06-30")["milestone"],
    )
    listed = cast("list[dict[str, object]]", operations.list_milestones(state="open")["milestones"])
    match = next(m for m in listed if m["number"] == created["number"])
    assert match["title"] == "v1.0"
    assert match["description"] == "desc"
    assert match["due_on"] == "2026-06-30T00:00:00Z"


# ---------------------------------------------------------------------------
# 3. State filter
# ---------------------------------------------------------------------------


def test_state_filter_excludes_closed_includes_all(backend: WorkItemBackend) -> None:
    """state='closed' excludes an open milestone; state='all' includes both."""
    _skip_github_shared_state(backend)
    open_ms = cast("dict[str, object]", operations.create_milestone(title="open one")["milestone"])
    closed_ms = cast("dict[str, object]", operations.create_milestone(title="closed one")["milestone"])
    _force_milestone_closed(backend, cast("int", closed_ms["number"]))

    closed_listed = cast("list[dict[str, object]]", operations.list_milestones(state="closed")["milestones"])
    all_listed = cast("list[dict[str, object]]", operations.list_milestones(state="all")["milestones"])
    closed_numbers = {m["number"] for m in closed_listed}
    all_numbers = {m["number"] for m in all_listed}

    assert closed_numbers == {closed_ms["number"]}
    assert open_ms["number"] not in closed_numbers
    assert {open_ms["number"], closed_ms["number"]} <= all_numbers


def test_close_milestone_preserves_member_counts_and_states(backend: WorkItemBackend) -> None:
    """close_milestone returns live member counts without changing member states."""
    _skip_github_shared_state(backend)
    created = cast("dict[str, object]", operations.create_milestone(title="release")["milestone"])
    number = cast("int", created["number"])
    open_item = _make_item("Open member")
    closed_item = _make_item("Closed member")
    repo = _repo_for_create_issue(backend)
    open_number = backend.create_issue_for_item(repo, open_item)
    closed_number = backend.create_issue_for_item(repo, closed_item)
    assert open_number is not None
    assert closed_number is not None
    open_item.metadata.issue = str(open_number)
    closed_item.metadata.issue = str(closed_number)
    operations.assign_item_to_milestone(issue_number=open_number, milestone_number=number)
    operations.assign_item_to_milestone(issue_number=closed_number, milestone_number=number)
    backend.close_github_issue(str(closed_number), "done")

    before = next(
        milestone
        for milestone in cast("list[dict[str, object]]", operations.list_milestones(state="open")["milestones"])
        if milestone["number"] == number
    )
    closed = cast("dict[str, object]", operations.close_milestone(milestone_number=number)["milestone"])
    after = next(
        milestone
        for milestone in cast("list[dict[str, object]]", operations.list_milestones(state="closed")["milestones"])
        if milestone["number"] == number
    )

    assert before["open_issues"] == closed["open_issues"] == after["open_issues"] == 1
    assert before["closed_issues"] == closed["closed_issues"] == after["closed_issues"] == 1
    assert backend.fetch_item_status(open_item) == "open"
    assert backend.fetch_item_status(closed_item) == "closed"


# ---------------------------------------------------------------------------
# 4. Ordering
# ---------------------------------------------------------------------------


def test_soonest_milestone_returns_earliest_due_date(backend: WorkItemBackend) -> None:
    """get_soonest_milestone returns the milestone due earliest, everywhere."""
    _skip_github_shared_state(backend)
    operations.create_milestone(title="mid", due_on="2026-06-30")
    operations.create_milestone(title="early", due_on="2026-01-31")

    result = operations.get_soonest_milestone()
    milestone = cast("dict[str, object]", result["milestone"])

    assert milestone["title"] == "early"


# ---------------------------------------------------------------------------
# 5. Empty state
# ---------------------------------------------------------------------------


def test_soonest_milestone_none_on_fresh_backend(backend: WorkItemBackend) -> None:
    """A fresh backend with no milestones returns {"milestone": None}, no exception."""
    _skip_github_shared_state(backend)

    result = operations.get_soonest_milestone()

    assert result["milestone"] is None


# ---------------------------------------------------------------------------
# 6. No-due-date
# ---------------------------------------------------------------------------


def test_soonest_milestone_without_due_date_warns_not_raises(backend: WorkItemBackend) -> None:
    """When no open milestone has a due date, a warning is emitted instead of an exception."""
    _skip_github_shared_state(backend)
    operations.create_milestone(title="undated")

    result = operations.get_soonest_milestone()

    assert result["milestone"] is not None
    assert len(cast("list[str]", result.get("warnings", []))) > 0


# ---------------------------------------------------------------------------
# 7. Error parity — validation stays above backend dispatch
# ---------------------------------------------------------------------------


def test_create_milestone_empty_title_raises_validation_error_before_dispatch(backend: WorkItemBackend) -> None:
    """create_milestone(title="") raises ValidationError on every backend, before any backend dispatch."""
    with pytest.raises(ValidationError, match="title must be non-empty"):
        operations.create_milestone(title="")


# ---------------------------------------------------------------------------
# 8. Capability parity
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("op_name", "kwargs"),
    [
        pytest.param("list_milestones", {}, id="list_milestones"),
        pytest.param("get_soonest_milestone", {}, id="get_soonest_milestone"),
        pytest.param("create_milestone", {"title": "x"}, id="create_milestone"),
        pytest.param("close_milestone", {"milestone_number": 1}, id="close_milestone"),
        pytest.param(
            "assign_item_to_milestone", {"issue_number": 1, "milestone_number": 1}, id="assign_item_to_milestone"
        ),
    ],
)
def test_unsupported_backend_raises_typed_capability_error(op_name: str, kwargs: dict[str, object]) -> None:
    """A backend with supports_milestones=False raises UnsupportedBackendCapabilityError with populated fields."""
    from backlog_core.backends.beads_backend import BeadsBackend

    beads = BeadsBackend(runner=MagicMock())
    set_config(BacklogConfig(backend=beads))
    try:
        with pytest.raises(UnsupportedBackendCapabilityError) as exc_info:
            getattr(operations, op_name)(**kwargs)
    finally:
        reset_config()

    assert exc_info.value.capability == "milestones"
    assert exc_info.value.backend == "BeadsBackend"
    assert exc_info.value.operation == op_name


# ---------------------------------------------------------------------------
# 9. Membership counts — the decisive assertion
# ---------------------------------------------------------------------------


def test_membership_counts_after_assign_and_close(backend: WorkItemBackend) -> None:
    """Create a milestone, assign 2 items, close 1 -> open_issues == 1, closed_issues == 1 everywhere.

    Proves the SQLite milestone_number FK path and the Memory dynamic-count
    path actually work, rather than shipping green against an empty table.
    """
    ms = cast("dict[str, object]", operations.create_milestone(title="Sprint 1")["milestone"])
    ms_number = cast("int", ms["number"])
    item_a = _make_item("Item A")
    item_b = _make_item("Item B")
    repo = _repo_for_create_issue(backend)
    num_a = backend.create_issue_for_item(repo, item_a)
    num_b = backend.create_issue_for_item(repo, item_b)
    assert num_a is not None
    assert num_b is not None

    operations.assign_item_to_milestone(issue_number=num_a, milestone_number=ms_number)
    operations.assign_item_to_milestone(issue_number=num_b, milestone_number=ms_number)
    backend.close_github_issue(str(num_a), "done")

    listed = cast("list[dict[str, object]]", operations.list_milestones(state="all")["milestones"])
    match = next(m for m in listed if m["number"] == ms_number)
    assert match["open_issues"] == 1
    assert match["closed_issues"] == 1


def test_list_items_exposes_native_assigned_milestone_only(backend: WorkItemBackend) -> None:
    """Native status hydration exposes an assigned milestone number despite duplicate titles."""
    _skip_github_shared_state(backend)
    duplicate = cast("dict[str, object]", operations.create_milestone(title="selected milestone")["milestone"])
    milestone = cast("dict[str, object]", operations.create_milestone(title="selected milestone")["milestone"])
    number = cast("int", milestone["number"])
    assigned = _make_item("Assigned item")
    nonmember = _make_item("Nonmember item")
    repo = _repo_for_create_issue(backend)
    assigned_number = backend.create_issue_for_item(repo, assigned)
    nonmember_number = backend.create_issue_for_item(repo, nonmember)
    assert assigned_number is not None
    assert nonmember_number is not None
    assigned.metadata.issue = str(assigned_number)
    nonmember.metadata.issue = str(nonmember_number)
    backend.put_work_item(assigned)
    backend.put_work_item(nonmember)
    operations.assign_item_to_milestone(issue_number=assigned_number, milestone_number=number)

    entries = cast("list[dict[str, object]]", operations.list_items(include_closed=True)["items"])
    by_title = {str(entry["title"]): entry for entry in entries}

    assert by_title["Assigned item"]["milestone"] == "selected milestone"
    assert by_title["Assigned item"]["milestone_number"] == str(number)
    assert by_title["Assigned item"]["milestone_number"] != str(duplicate["number"])
    assert by_title["Nonmember item"]["milestone"] == ""


@pytest.mark.parametrize(("native_state", "expected_status"), [("OPEN", "in-progress"), ("CLOSED", "closed")])
def test_list_items_preserves_workflow_status_and_native_lifecycle(
    backend: WorkItemBackend, native_state: str, expected_status: str
) -> None:
    """Native lifecycle remains visible even when logical metadata requests in-progress."""
    _skip_github_shared_state(backend)
    item = _make_item("Workflow status item")
    issue_number = backend.create_issue_for_item(_repo_for_create_issue(backend), item)
    assert issue_number is not None
    item.metadata.issue = str(issue_number)
    item.reference = f"#{issue_number}"
    backend.put_work_item(item)
    if native_state == "CLOSED":
        backend.close_github_issue(str(issue_number), "done")

    operations.update_item(selector=item.reference, status="in-progress")
    entries = cast("list[dict[str, object]]", operations.list_items(include_closed=True)["items"])
    entry = next(candidate for candidate in entries if candidate["title"] == item.title)

    assert entry["status"] == expected_status
    assert entry["state"] == native_state
    assert backend.fetch_item_status(item) == native_state.lower()


# ---------------------------------------------------------------------------
# 10. assign_item_to_milestone via operations
# ---------------------------------------------------------------------------


def test_assign_item_to_milestone_via_operations(backend: WorkItemBackend) -> None:
    """operations.assign_item_to_milestone assigns an item, reflected in list_milestones open_issues."""
    ms = cast("dict[str, object]", operations.create_milestone(title="Sprint 1")["milestone"])
    ms_number = cast("int", ms["number"])
    item = _make_item("Item A")
    repo = _repo_for_create_issue(backend)
    num = backend.create_issue_for_item(repo, item)
    assert num is not None

    operations.assign_item_to_milestone(issue_number=num, milestone_number=ms_number)

    listed = cast("list[dict[str, object]]", operations.list_milestones(state="all")["milestones"])
    match = next(m for m in listed if m["number"] == ms_number)
    assert match["open_issues"] == 1


def test_assign_unknown_issue_raises_backlog_error(backend: WorkItemBackend) -> None:
    """operations.assign_item_to_milestone raises BacklogError (not KeyError) for an unknown issue."""
    _skip_github_shared_state(backend)
    ms = cast("dict[str, object]", operations.create_milestone(title="Sprint 1")["milestone"])
    ms_number = cast("int", ms["number"])

    with pytest.raises(BacklogError) as exc_info:
        operations.assign_item_to_milestone(issue_number=999999, milestone_number=ms_number)

    assert "not found" in str(exc_info.value)


def test_assign_item_to_milestone_normalizes_github_exception() -> None:
    """A GithubException from the backend (e.g. GitHubBackend's unknown issue/milestone 404) is
    normalized to BacklogError, not left to escape as a raw PyGithub exception.

    KeyError-raising backends (Memory/SQLite) are covered by
    test_assign_unknown_issue_raises_backlog_error above; GitHubBackend's
    assign_item_to_milestone raises GithubException instead (PyGithub's
    get_issue/get_milestone), which is a distinct code path in the
    operations.py wrapper.
    """

    class _FakeGitHubLikeBackend:
        supports_milestones = True

        def assign_item_to_milestone(self, issue_number: int, milestone_number: int, repo: str = "") -> None:
            raise GithubException(404, {"message": "Not Found"}, None)

    set_config(BacklogConfig(backend=cast("WorkItemBackend", _FakeGitHubLikeBackend())))
    try:
        with pytest.raises(BacklogError) as exc_info:
            operations.assign_item_to_milestone(issue_number=1, milestone_number=1)
        assert "GitHub API error" in str(exc_info.value)
    finally:
        reset_config()

"""Tests for backlog_core.backends.beads_backend.BeadsBackend.

All tests mock BdRunner via constructor injection — no live ``bd`` binary is
invoked.  See ADR-001 and ADR-002 in the project architecture documentation
for the design rationale behind which methods are implemented vs. stubbed.

Divergence Notes
----------------
DN-1: Integration-branch methods raise ``NotImplementedError`` (not
    ``BackendUnavailableError`` as task spec #8 stated).  The actual
    implementation raises ``NotImplementedError(_ADR_001_NOTE)`` for all
    GitHub-specific surface.

DN-2: ``sync_issues_graphql`` raises ``NotImplementedError`` (not returning
    IssueNode-shaped dicts as task spec #9 stated).

DN-3: ``create_task_issue`` always raises ``NotImplementedError`` regardless
    of ``parent_issue_number`` type — the implementation has no branching on
    type; task spec #11 implied two distinct code paths.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from backlog_core.backend_protocol import BacklogBackend
from backlog_core.backends.bd_runner import BdRunner
from backlog_core.backends.beads_backend import BeadsBackend
from backlog_core.models import BackendAvailability, BacklogItem, BacklogItemMetadata, ViewItemResult

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

# ---------------------------------------------------------------------------
# Paths & helpers
# ---------------------------------------------------------------------------

_FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "beads"

_BD_SHOW_FIXTURE: dict = json.loads((_FIXTURES / "bd_show_issue.json").read_text())
_BD_LIST_FIXTURE: list = json.loads((_FIXTURES / "bd_list_epic_children.json").read_text())


def _make_runner(*, available: bool = True) -> MagicMock:
    """Return a spec'd MagicMock for BdRunner."""
    mock = MagicMock(spec=BdRunner)
    mock.is_available.return_value = available
    return mock


def _make_item(issue: str = "bd-a3f8", title: str = "Fix authentication bug") -> BacklogItem:
    """Construct a minimal BacklogItem with a beads issue ID."""
    return BacklogItem(
        title=title,
        description="Test item",
        metadata=BacklogItemMetadata(
            source="test", added="2026-01-01", priority="P2", item_type="Task", status="open", issue=issue
        ),
    )


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_isinstance_satisfies_backlog_backend_protocol() -> None:
    """BeadsBackend() is an instance of the runtime-checkable BacklogBackend Protocol.

    Why: isinstance check is the gating mechanism in operations.py — failing
         this means BeadsBackend is silently ignored by the factory.
    """
    runner = _make_runner()
    backend = BeadsBackend(runner=runner)
    assert isinstance(backend, BacklogBackend)


# ---------------------------------------------------------------------------
# Constructor — filesystem-free (ADR-003)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_init_without_runner_does_not_call_shutil_which(mocker: MockerFixture) -> None:
    """BeadsBackend() constructs a default BdRunner without touching the filesystem.

    Why: ADR-003 mandates lazy bd resolution — tests and CI must be able to
         import and instantiate BeadsBackend without bd on PATH.
    """
    mock_which = mocker.patch("backlog_core.backends.bd_runner.shutil.which")
    mocker.patch("backlog_core.backends.bd_runner.subprocess.run")

    BeadsBackend()  # uses default BdRunner

    mock_which.assert_not_called()


@pytest.mark.unit
def test_init_accepts_custom_runner() -> None:
    """BeadsBackend stores the injected runner without replacing it.

    Why: Constructor injection is the testing seam — if the runner is swapped
         out, all mocks become invalid.
    """
    runner = _make_runner()
    backend = BeadsBackend(runner=runner)
    assert backend._runner is runner


# ---------------------------------------------------------------------------
# probe_backend_status
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_probe_backend_status_reachable_when_runner_available() -> None:
    """probe_backend_status returns REACHABLE when BdRunner.is_available() is True.

    Why: Callers display availability state in the UI — wrong enum breaks the
         health-check display.
    """
    runner = _make_runner(available=True)
    backend = BeadsBackend(runner=runner)

    status = backend.probe_backend_status()

    assert status.availability == BackendAvailability.REACHABLE
    assert status.name == "Beads"


@pytest.mark.unit
def test_probe_backend_status_error_when_runner_unavailable() -> None:
    """probe_backend_status returns ERROR when BdRunner.is_available() is False.

    Why: Unavailable bd binary should surface as an explicit ERROR, not a
         silent REACHABLE — otherwise callers cannot distinguish the two states.
    """
    runner = _make_runner(available=False)
    backend = BeadsBackend(runner=runner)

    status = backend.probe_backend_status()

    assert status.availability == BackendAvailability.ERROR
    assert status.name == "Beads"
    assert status.error is not None
    assert "bd binary" in status.error


# ---------------------------------------------------------------------------
# try_get_github — returns None (no PyGithub)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_try_get_github_returns_none() -> None:
    """try_get_github returns None — BeadsBackend has no PyGithub Repository.

    Why: Protocol callers must get None (not an exception) from try_get_github
         to use the optional-connection pattern correctly.
    """
    runner = _make_runner()
    backend = BeadsBackend(runner=runner)
    assert backend.try_get_github() is None


# ---------------------------------------------------------------------------
# ADR-001 — GraphQL stubs raise NotImplementedError
# ---------------------------------------------------------------------------

_ADR_001_METHODS = pytest.mark.parametrize(
    ("method_name", "kwargs"),
    [
        pytest.param("_graphql_request", {"repo": MagicMock(), "query": "{ viewer { login } }"}, id="graphql_request"),
        pytest.param(
            "_resolve_labels_graphql",
            {"repo": MagicMock(), "repo_owner": "owner", "repo_name": "repo", "label_names": []},
            id="resolve_labels_graphql",
        ),
        pytest.param(
            "_fetch_issue_graphql",
            {"repo": MagicMock(), "owner": "owner", "repo_name": "repo", "issue_number": 1},
            id="fetch_issue_graphql",
        ),
        pytest.param(
            "_fetch_issues_graphql",
            {"repo": MagicMock(), "owner": "owner", "repo_name": "repo"},
            id="fetch_issues_graphql",
        ),
        pytest.param(
            "_update_issue_graphql", {"repo": MagicMock(), "issue_node_id": "MDExOg=="}, id="update_issue_graphql"
        ),
        pytest.param(
            "sync_issues_graphql",
            {"repo": MagicMock(), "owner": "owner", "repo_name": "repo"},
            id="sync_issues_graphql",
        ),
        pytest.param("create_issue_for_item", {"repo": MagicMock(), "item": _make_item()}, id="create_issue_for_item"),
        pytest.param(
            "fetch_github_issue_body", {"repo_obj": MagicMock(), "issue_num": 1}, id="fetch_github_issue_body"
        ),
        pytest.param(
            "sync_groomed_to_github_issue",
            {"repo_obj": MagicMock(), "issue_num": 1, "groomed_content": "content"},
            id="sync_groomed_to_github_issue",
        ),
        pytest.param(
            "_add_comment_graphql",
            {"repo": MagicMock(), "issue_node_id": "MDExOg==", "body": "comment"},
            id="add_comment_graphql",
        ),
        pytest.param(
            "_fetch_issue_comments_graphql",
            {"repo": MagicMock(), "owner": "owner", "repo_name": "repo", "issue_number": 1},
            id="fetch_issue_comments_graphql",
        ),
        pytest.param(
            "_fetch_comment_by_id_graphql",
            {"repo": MagicMock(), "comment_node_id": "MDExOg=="},
            id="fetch_comment_by_id_graphql",
        ),
        pytest.param(
            "_update_issue_comment_graphql",
            {"repo": MagicMock(), "comment_node_id": "MDExOg==", "body": "updated"},
            id="update_issue_comment_graphql",
        ),
        pytest.param(
            "_fetch_milestones_graphql",
            {"repo": MagicMock(), "owner": "owner", "repo_name": "repo"},
            id="fetch_milestones_graphql",
        ),
        pytest.param("_projects_v2_list_query", {"owner": "owner"}, id="projects_v2_list_query"),
        pytest.param(
            "_projects_v2_create_mutation",
            {"owner_id": "MDExOg==", "title": "My project"},
            id="projects_v2_create_mutation",
        ),
        pytest.param("get_github", {}, id="get_github"),
    ],
)


@pytest.mark.unit
@_ADR_001_METHODS
def test_adr001_method_raises_not_implemented(method_name: str, kwargs: dict) -> None:
    """ADR-001 methods raise NotImplementedError with an ADR-001 reference.

    Why: Protocol callers must get a clear NotImplementedError — swallowing
         the exception or returning a default silently breaks callers.
    """
    runner = _make_runner()
    backend = BeadsBackend(runner=runner)
    method = getattr(backend, method_name)

    with pytest.raises(NotImplementedError, match="ADR-001"):
        method(**kwargs)


# ---------------------------------------------------------------------------
# ADR-002 — fetch_open_issues_by_title raises NotImplementedError
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_fetch_open_issues_by_title_raises_adr002() -> None:
    """fetch_open_issues_by_title raises NotImplementedError with ADR-002 message.

    Why: Protocol callers must discover the beads-native shadow method
         fetch_open_issues_by_title_str() — the exception message directs them
         there.  Silently returning {} would allow callers to proceed with an
         empty map, causing silent data loss.
    """
    runner = _make_runner()
    backend = BeadsBackend(runner=runner)

    with pytest.raises(NotImplementedError, match="ADR-002"):
        backend.fetch_open_issues_by_title(repo=MagicMock())  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# fetch_open_issues_by_title_str (beads-native)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_fetch_open_issues_by_title_str_returns_str_to_str_map() -> None:
    """fetch_open_issues_by_title_str returns dict[str, str] from bd list output.

    Why: The return type is dict[str, str] (not dict[str, int]) — callers
         working with beads IDs need string keys for further bd calls.
    """
    runner = _make_runner()
    runner.run_json.return_value = _BD_LIST_FIXTURE
    backend = BeadsBackend(runner=runner)

    result = backend.fetch_open_issues_by_title_str()

    runner.run_json.assert_called_once_with(["list", "--status=open"])
    assert isinstance(result, dict)
    for key, value in result.items():
        assert isinstance(key, str), f"key {key!r} is not a str"
        assert isinstance(value, str), f"value {value!r} is not a str"


@pytest.mark.unit
def test_fetch_open_issues_by_title_str_maps_title_to_id() -> None:
    """fetch_open_issues_by_title_str maps issue title → beads ID correctly.

    Why: Callers use the title→id map for issue resolution — wrong mapping
         causes lookup misses.
    """
    runner = _make_runner()
    runner.run_json.return_value = _BD_LIST_FIXTURE
    backend = BeadsBackend(runner=runner)

    result = backend.fetch_open_issues_by_title_str()

    assert "Write bd_runner tests" in result
    assert result["Write bd_runner tests"] == "bd-task1"
    assert "Write beads_models tests" in result
    assert result["Write beads_models tests"] == "bd-task2"


# ---------------------------------------------------------------------------
# check_open_prs_for_issue
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_check_open_prs_for_issue_returns_empty_list() -> None:
    """check_open_prs_for_issue always returns [] — beads has no PR surface.

    Why: Protocol callers loop over the result — None would cause a TypeError
         and any non-empty return would create phantom PR references.
    """
    runner = _make_runner()
    backend = BeadsBackend(runner=runner)

    result = backend.check_open_prs_for_issue(issue_num=42)

    assert result == []
    runner.run_json.assert_not_called()


# ---------------------------------------------------------------------------
# batch_fetch_statuses
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_batch_fetch_statuses_raises_not_implemented() -> None:
    """batch_fetch_statuses raises NotImplementedError — beads IDs are strings, not int keys.

    Why: Protocol contract uses dict[int, IssueStatus] keyed by GitHub issue
         number.  Beads issue IDs are strings with no meaningful integer
         representation, so the operation cannot be implemented.  Per ADR-002,
         unsupported operations raise NotImplementedError explicitly rather than
         silently returning an empty value.
    """
    runner = _make_runner()
    backend = BeadsBackend(runner=runner)
    item = _make_item()

    with pytest.raises(NotImplementedError):
        backend.batch_fetch_statuses([item])

    runner.run_json.assert_not_called()


# ---------------------------------------------------------------------------
# Integration-branch methods — NotImplementedError (DN-1)
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize(
    ("method_name", "kwargs"),
    [
        pytest.param(
            "create_integration_branch",
            {"milestone_number": 1, "slug": "auth", "base_branch": "main"},
            id="create_integration_branch",
        ),
        pytest.param(
            "get_integration_branch_status", {"branch_name": "feature/auth"}, id="get_integration_branch_status"
        ),
        pytest.param(
            "merge_integration_branch",
            {"head_branch": "feature/auth", "base_branch": "main", "commit_message": "merge"},
            id="merge_integration_branch",
        ),
        pytest.param("delete_integration_branch", {"branch_name": "feature/auth"}, id="delete_integration_branch"),
        pytest.param("list_integration_branches", {}, id="list_integration_branches"),
    ],
)
def test_integration_branch_raises_not_implemented(method_name: str, kwargs: dict) -> None:
    """Integration-branch methods raise NotImplementedError (ADR-001).

    Why (DN-1): The original task spec expected BackendUnavailableError, but
         the actual implementation raises NotImplementedError because these
         methods require a PyGithub Repository transport that beads cannot
         provide — they are ADR-001 stubs, not runtime-availability failures.
    """
    runner = _make_runner()
    backend = BeadsBackend(runner=runner)
    method = getattr(backend, method_name)

    with pytest.raises(NotImplementedError):
        method(**kwargs)


# ---------------------------------------------------------------------------
# apply_status_in_progress
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_apply_status_in_progress_calls_bd_update_claim_with_issue_id() -> None:
    """apply_status_in_progress calls bd update <issue> --claim.

    Why: The ``--claim`` flag is the beads mechanism for transitioning to
         in-progress — wrong argv silently skips the state change.
    """
    runner = _make_runner()
    backend = BeadsBackend(runner=runner)
    item = _make_item(issue="bd-a3f8")

    backend.apply_status_in_progress(item)

    runner.run_text.assert_called_once_with(["update", "bd-a3f8", "--claim"])


@pytest.mark.unit
def test_apply_status_in_progress_falls_back_to_title_when_issue_absent() -> None:
    """apply_status_in_progress uses item.title when item.issue is empty.

    Why: BacklogItems created locally before sync may have no issue ID — the
         title fallback ensures the command is still attempted.
    """
    runner = _make_runner()
    backend = BeadsBackend(runner=runner)
    item = BacklogItem(
        title="Fix authentication bug",
        description="desc",
        metadata=BacklogItemMetadata(source="test", added="2026-01-01", priority="P2", item_type="Task", status="open"),
    )

    backend.apply_status_in_progress(item)

    runner.run_text.assert_called_once_with(["update", "Fix authentication bug", "--claim"])


# ---------------------------------------------------------------------------
# apply_status_groomed and apply_status_verified — no-ops
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_apply_status_groomed_is_noop() -> None:
    """apply_status_groomed is a no-op — beads has no groomed lifecycle state.

    Why: Calling this method must not raise and must not invoke any subprocess —
         an exception or subprocess call would block grooming workflows on
         the beads backend.
    """
    runner = _make_runner()
    backend = BeadsBackend(runner=runner)
    item = _make_item()

    backend.apply_status_groomed(item)  # must not raise

    runner.run_text.assert_not_called()
    runner.run_json.assert_not_called()


@pytest.mark.unit
def test_apply_status_verified_is_noop() -> None:
    """apply_status_verified is a no-op — beads has no verified lifecycle state.

    Why: Same reasoning as apply_status_groomed — verified is GitHub-specific.
    """
    runner = _make_runner()
    backend = BeadsBackend(runner=runner)
    item = _make_item()

    backend.apply_status_verified(item)  # must not raise

    runner.run_text.assert_not_called()
    runner.run_json.assert_not_called()


# ---------------------------------------------------------------------------
# close_github_issue
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_close_github_issue_calls_bd_close_with_reason() -> None:
    """close_github_issue calls bd close <id> --reason <reason>.

    Why: ``--reason`` is required for audit trail — omitting it produces a
         close record with no context.
    """
    runner = _make_runner()
    backend = BeadsBackend(runner=runner)

    backend.close_github_issue("bd-a3f8", "Resolved — fixed in commit abc123")

    runner.run_text.assert_called_once_with(["close", "bd-a3f8", "--reason", "Resolved — fixed in commit abc123"])


@pytest.mark.unit
def test_close_github_issue_omits_reason_flag_when_empty() -> None:
    """close_github_issue omits --reason flag when reason is an empty string.

    Why: bd treats ``--reason ""`` as an explicit empty string argument — the
         implementation must omit the flag, not pass an empty value.
    """
    runner = _make_runner()
    backend = BeadsBackend(runner=runner)

    backend.close_github_issue("bd-a3f8", "")

    runner.run_text.assert_called_once_with(["close", "bd-a3f8"])


# ---------------------------------------------------------------------------
# resolve_github_issue
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_resolve_github_issue_calls_bd_close_with_summary_as_reason() -> None:
    """resolve_github_issue calls bd close <id> --reason <summary>.

    Why: beads resolution maps to close+reason — method, findings, follow_ups
         are GitHub-specific fields that beads does not support.
    """
    runner = _make_runner()
    backend = BeadsBackend(runner=runner)

    backend.resolve_github_issue("bd-a3f8", summary="Authentication fixed")

    runner.run_text.assert_called_once_with(["close", "bd-a3f8", "--reason", "Authentication fixed"])


# ---------------------------------------------------------------------------
# create_task_issue — NotImplementedError for all parent_issue_number types (DN-3)
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize(
    "parent_issue_number", [pytest.param(42, id="int_parent"), pytest.param("bd-a3f8", id="str_parent")]
)
def test_create_task_issue_raises_not_implemented(parent_issue_number: int | str) -> None:
    """create_task_issue raises NotImplementedError regardless of parent type.

    Why (DN-3): Task spec #11 implied two code paths (int vs str), but the
         implementation raises NotImplementedError for all inputs — beads task
         issue creation is not implemented (ADR-001).
    """
    runner = _make_runner()
    backend = BeadsBackend(runner=runner)

    with pytest.raises(NotImplementedError):
        backend.create_task_issue(
            repo=MagicMock(),  # type: ignore[arg-type]
            parent_issue_number=parent_issue_number,  # type: ignore[arg-type]
            task=MagicMock(),
        )


# ---------------------------------------------------------------------------
# fetch_item_status
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_fetch_item_status_returns_status_string_from_bd_show() -> None:
    """fetch_item_status calls bd show and returns the status as a string.

    Why: Callers use the returned string for display and gating — wrong status
         string breaks workflow routing.
    """
    runner = _make_runner()
    runner.run_json.return_value = _BD_SHOW_FIXTURE
    backend = BeadsBackend(runner=runner)
    item = _make_item(issue="bd-a3f8")

    status = backend.fetch_item_status(item)

    runner.run_json.assert_called_once_with(["show", "bd-a3f8"])
    assert isinstance(status, str)
    assert status == "open"


@pytest.mark.unit
def test_fetch_item_status_uses_title_when_issue_absent() -> None:
    """fetch_item_status falls back to item.title when issue is not set.

    Why: Same fallback contract as apply_status_in_progress — ensures items
         without a beads ID still get their status checked.
    """
    runner = _make_runner()
    runner.run_json.return_value = _BD_SHOW_FIXTURE
    backend = BeadsBackend(runner=runner)
    item = BacklogItem(
        title="Fix authentication bug",
        description="desc",
        metadata=BacklogItemMetadata(source="test", added="2026-01-01", priority="P2", item_type="Task", status="open"),
    )

    backend.fetch_item_status(item)

    runner.run_json.assert_called_once_with(["show", "Fix authentication bug"])


# ---------------------------------------------------------------------------
# view_enrich_from_github
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_view_enrich_from_github_populates_result_fields() -> None:
    """view_enrich_from_github enriches a ViewItemResult from bd show output.

    Why: Callers render the ViewItemResult in the UI — missing fields produce
         blank display sections.
    """
    runner = _make_runner()
    runner.run_json.return_value = _BD_SHOW_FIXTURE
    backend = BeadsBackend(runner=runner)
    result = ViewItemResult(title="", status="", state="", source="")

    success = backend.view_enrich_from_github(result, "bd-a3f8")

    assert success is True
    runner.run_json.assert_called_once_with(["show", "bd-a3f8"])
    assert result.status == "open"
    assert result.state == "open"
    assert result.source == "beads"
    assert result.title == "Fix authentication bug"


@pytest.mark.unit
def test_view_enrich_from_github_returns_false_on_bd_invocation_error() -> None:
    """view_enrich_from_github returns False when BdInvocationError is raised.

    Why: Callers use the bool return to decide whether to fall back to cached
         data — raising instead of returning False breaks the caller contract.
    """
    from backlog_core.backends.bd_runner import BdInvocationError

    runner = _make_runner()
    runner.run_json.side_effect = BdInvocationError(
        "bd show exited 1", argv=["show", "bd-a3f8"], returncode=1, stdout="", stderr=""
    )
    backend = BeadsBackend(runner=runner)
    result = ViewItemResult(title="cached title", status="unknown", state="open", source="")

    success = backend.view_enrich_from_github(result, "bd-a3f8")

    assert success is False
    # result must be left untouched on failure
    assert result.title == "cached title"
    assert result.status == "unknown"


@pytest.mark.unit
def test_view_enrich_from_github_returns_false_on_bd_not_installed() -> None:
    """view_enrich_from_github returns False when BdNotInstalledError is raised.

    Why: Same caller contract — bd not installed is a runtime-unavailability
         condition, not a programming error.
    """
    from backlog_core.backends.bd_runner import BdNotInstalledError

    runner = _make_runner()
    runner.run_json.side_effect = BdNotInstalledError("bd not found")
    backend = BeadsBackend(runner=runner)
    result = ViewItemResult(title="", status="", state="", source="")

    success = backend.view_enrich_from_github(result, "bd-a3f8")

    assert success is False


@pytest.mark.unit
def test_view_enrich_from_github_sets_state_closed_for_closed_status() -> None:
    """view_enrich_from_github sets result.state='closed' when status is 'closed'.

    Why: Callers gate on result.state to decide whether to show a closed badge
         — wrong state for closed issues produces an incorrect open badge.
    """
    runner = _make_runner()
    closed_fixture = dict(_BD_SHOW_FIXTURE, status="closed")
    runner.run_json.return_value = closed_fixture
    backend = BeadsBackend(runner=runner)
    result = ViewItemResult(title="", status="", state="", source="")

    success = backend.view_enrich_from_github(result, "bd-a3f8")

    assert success is True
    assert result.state == "closed"
    assert result.status == "closed"


# ---------------------------------------------------------------------------
# issue_to_local_fields
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_issue_to_local_fields_maps_node_to_local_fields() -> None:
    """issue_to_local_fields converts an IssueNode TypedDict to IssueLocalFields.

    Why: This is a translation utility — wrong field mapping corrupts local
         metadata for items synced from GitHub-shaped data.
    """
    from backlog_core.backend_protocol import IssueNode

    runner = _make_runner()
    backend = BeadsBackend(runner=runner)
    node: IssueNode = {
        "id": "MDExOg==",
        "number": 7,
        "title": "Fix auth",
        "state": "OPEN",
        "body": "body text",
        "createdAt": "2026-01-01T00:00:00Z",
        "updatedAt": "2026-01-02T00:00:00Z",
        "labels": [{"id": "L1", "name": "bug"}],
        "milestone": {"id": "M1", "number": 2, "title": "v1.0", "state": "OPEN", "dueOn": None},
        "assignees": [{"login": "alice"}],
    }

    local = backend.issue_to_local_fields(node)

    assert local.title == "Fix auth"
    assert local.body == "body text"
    assert local.status == "open"
    assert "bug" in local.labels
    assert local.milestone == "v1.0"
    assert "alice" in local.assignees

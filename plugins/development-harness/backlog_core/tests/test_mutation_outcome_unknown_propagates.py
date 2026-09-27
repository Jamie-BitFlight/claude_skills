"""A mutation whose outcome is unknown must never be absorbed as a completed fallback.

``GitHubMutationOutcomeUnknownError`` means the request's worker thread was abandoned and the
mutation may still land on GitHub. Every handler below used to catch it as an ordinary
``BacklogError`` and carry on: storing a local-only item, warning and returning, or recording a
patch error for a later reconcile to replay. Each of those lets a later run send the same
mutation again and duplicate the issue or comment. Each test makes one site's mutation raise the
error and asserts it reaches the caller unchanged.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING, Any
from unittest.mock import Mock

import pytest

from backlog_core import gh_client, operations
from backlog_core.backend_types import AddedCommentNode, BacklogConfig, IssueCommentNode
from backlog_core.backends.github_backend import GitHubBackend
from backlog_core.backends.github_work_items import _GitHubWorkItemSync
from backlog_core.file_cache import FileCache
from backlog_core.models import (
    BacklogItem,
    GitHubMutationOutcomeUnknownError,
    Output,
    ProviderPatch,
    ProviderSnapshot,
    SamTask,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from pytest_mock import MockerFixture


def _outcome_unknown(*_args: object, **_kwargs: object) -> Any:
    msg = "GraphQL mutation timed out after 60s; its outcome is unknown"
    raise GitHubMutationOutcomeUnknownError(msg, timeout_seconds=60)


_ISSUE = {"id": "I_1", "number": 5, "body": "", "labels": [], "title": "t"}


def test_add_item_fails_and_stores_no_local_item(tmp_path: Path, mocker: MockerFixture) -> None:
    """Only the GraphQL transport is faked; a createIssue deadline expiry is the real conversion path."""
    repo = "owner/repository"
    backend = GitHubBackend(repo=repo, cache=FileCache(tmp_path))
    mocker.patch.object(
        backend, "fetch_snapshot", return_value=ProviderSnapshot(items=[], sync_started_at="2026-09-27T00:00:00+00:00")
    )
    repository = mocker.Mock(full_name=repo, node_id="R_node")
    repository.get_labels.return_value = []

    def graphql_query(query: str, _variables: dict[str, object]) -> tuple[dict[str, str], dict[str, object]]:
        if "createIssue" in query:
            raise gh_client._DeadlineExceeded
        return {}, {"data": {"repository": {}}}

    repository.requester.graphql_query.side_effect = graphql_query
    mocker.patch.object(backend, "try_get_github", return_value=repository)
    mocker.patch.object(backend, "get_github", return_value=repository)  # add_item's liveness probe (#3969)
    mocker.patch.object(operations, "get_config", return_value=BacklogConfig(backend=backend))

    with pytest.raises(GitHubMutationOutcomeUnknownError) as excinfo:
        operations.add_item("new item", "new description", "P1", type_="Bug", force=True)

    message = str(excinfo.value)
    assert "timed out" in message
    assert "may still complete" in message
    assert "retry backlog_add without force after the earlier createIssue request has finished" in message
    assert "its duplicate check then finds the issue if it was created" in message
    assert backend.list_work_items() == []


def test_create_issue_and_update_item_propagates(mocker: MockerFixture) -> None:
    mocker.patch.object(operations, "try_get_github", return_value=Mock(full_name="o/r"))
    mocker.patch.object(operations, "create_issue_for_item", side_effect=_outcome_unknown)

    with pytest.raises(GitHubMutationOutcomeUnknownError):
        operations._create_issue_and_update_item(BacklogItem(title="t", reference="p1-t"), "o/r")


def _live_issue_mutation_setup(mocker: MockerFixture, mutation: str) -> BacklogItem:
    mocker.patch.object(operations, "update_item_metadata")
    mocker.patch.object(operations, "get_config").return_value.backend.issue_id_type = "integer"
    mocker.patch.object(operations, "try_get_github", return_value=Mock(full_name="o/r"))
    mocker.patch.object(operations, "_fetch_issue_graphql", return_value=_ISSUE)
    mocker.patch.object(operations, mutation, side_effect=_outcome_unknown)
    return BacklogItem(title="t", reference="p1-t", issue="#5")


def test_rename_item_title_propagates(mocker: MockerFixture) -> None:
    item = _live_issue_mutation_setup(mocker, "_update_issue_graphql")

    with pytest.raises(GitHubMutationOutcomeUnknownError):
        operations._rename_item_title(item, "new title", "o/r")


def test_apply_plan_to_item_propagates(mocker: MockerFixture) -> None:
    item = _live_issue_mutation_setup(mocker, "_add_comment_graphql")

    with pytest.raises(GitHubMutationOutcomeUnknownError):
        operations._apply_plan_to_item(item, "P7", "o/r")


def _gh_client_issue_setup(mocker: MockerFixture, mutation: str) -> None:
    """Answer every read, let every other mutation succeed, and make ``mutation`` time out."""
    mocker.patch.object(gh_client, "get_github", return_value=Mock(full_name="o/r"))
    mocker.patch.object(gh_client, "_fetch_issue_graphql", return_value=_ISSUE)
    mocker.patch.object(gh_client, "_resolve_label_ids_graphql", return_value={})
    mocker.patch.object(gh_client, "_fetch_issue_comments_graphql", return_value=[])
    mocker.patch.object(gh_client, "_add_comment_graphql", return_value=Mock(id="C_1", database_id=1))
    mocker.patch.object(gh_client, "_update_issue_graphql", return_value=None)
    mocker.patch.object(gh_client, mutation, side_effect=_outcome_unknown)


@pytest.mark.parametrize("mutation", ["_add_comment_graphql", "_update_issue_graphql"])
def test_close_github_issue_propagates(mocker: MockerFixture, mutation: str) -> None:
    _gh_client_issue_setup(mocker, mutation)

    with pytest.raises(GitHubMutationOutcomeUnknownError):
        gh_client.close_github_issue("#5", "done", repo="o/r")


@pytest.mark.parametrize("mutation", ["_add_comment_graphql", "_update_issue_graphql"])
def test_resolve_github_issue_propagates(mocker: MockerFixture, mutation: str) -> None:
    _gh_client_issue_setup(mocker, mutation)

    with pytest.raises(GitHubMutationOutcomeUnknownError):
        gh_client.resolve_github_issue("#5", summary="done", repo="o/r")


def test_apply_status_label_propagates(mocker: MockerFixture) -> None:
    _gh_client_issue_setup(mocker, "_update_issue_graphql")

    with pytest.raises(GitHubMutationOutcomeUnknownError):
        gh_client._apply_status_label(
            Mock(),
            "o",
            "r",
            5,
            label="status:in-progress",
            create_if_missing=False,
            already_message="",
            applied_message="",
            output=Output(),
        )


def test_sync_groomed_to_github_issue_propagates(mocker: MockerFixture) -> None:
    _gh_client_issue_setup(mocker, "_update_issue_graphql")

    with pytest.raises(GitHubMutationOutcomeUnknownError):
        gh_client.sync_groomed_to_github_issue(Mock(full_name="o/r"), 5, "groomed text")


def test_create_task_issue_propagates_a_create_timeout(mocker: MockerFixture) -> None:
    _gh_client_issue_setup(mocker, "_create_issue_graphql")
    mocker.patch.object(gh_client, "_get_repo_node_id", return_value="R_1")

    with pytest.raises(GitHubMutationOutcomeUnknownError):
        gh_client.create_task_issue(Mock(full_name="o/r"), 1, SamTask(task_id="T1", feature="f", task_type="impl"))


def test_create_task_issue_propagates_a_sub_issue_link_timeout(mocker: MockerFixture) -> None:
    _gh_client_issue_setup(mocker, "_graphql_request")
    mocker.patch.object(gh_client, "_get_repo_node_id", return_value="R_1")
    mocker.patch.object(
        gh_client, "_create_issue_graphql", return_value={"id": "I_2", "number": 6, "title": "t", "url": ""}
    )

    with pytest.raises(GitHubMutationOutcomeUnknownError):
        gh_client.create_task_issue(Mock(full_name="o/r"), 1, SamTask(task_id="T1", feature="f", task_type="impl"))


def test_update_task_status_propagates(mocker: MockerFixture) -> None:
    _gh_client_issue_setup(mocker, "_update_issue_graphql")
    body = "<!-- sam:task\ntask_id: T1\nstatus: not-started\n-->"
    mocker.patch.object(gh_client, "_fetch_issue_graphql", return_value={**_ISSUE, "body": body})

    with pytest.raises(GitHubMutationOutcomeUnknownError):
        gh_client.update_task_status(Mock(full_name="o/r"), 5, "in-progress")


def test_apply_patches_propagates_instead_of_recording_a_replayable_error(mocker: MockerFixture) -> None:
    issues = Mock()
    issues.get_github.return_value = Mock(full_name="o/r")
    issues._fetch_targeted_issues.return_value = {"p1-t": _ISSUE}
    issues._add_comment_graphql.side_effect = _outcome_unknown
    issues._fetch_issue_comments_graphql.return_value = []
    sync = _GitHubWorkItemSync(issues, Mock)
    mocker.patch.object(
        sync, "work_item_version", return_value=(SimpleNamespace(revision="r1", body="old"), None, "root")
    )

    with pytest.raises(GitHubMutationOutcomeUnknownError):
        sync.apply_patches([ProviderPatch(provider_id="I_1", reference="p1-t", expected_revision="r1", body="new")])


def test_migrate_task_propagates(mocker: MockerFixture) -> None:
    import migrate_tasks_to_github as migrate

    mocker.patch.object(migrate, "create_task_issue", side_effect=_outcome_unknown)
    task = migrate.TaskRecord(
        task_id="T1", title="t", status="not-started", agent="", priority=1, skills=[], dependencies=[]
    )

    with pytest.raises(GitHubMutationOutcomeUnknownError):
        migrate._migrate_task(task, "f", Mock(), 1, [])


class TestAnEarlierStepsCreatedObjectIsReported:
    """When a later step's outcome is unknown, the error names what an earlier step created."""

    def test_a_sub_issue_link_timeout_carries_the_created_issue_number(self, mocker: MockerFixture) -> None:
        _gh_client_issue_setup(mocker, "_graphql_request")
        mocker.patch.object(gh_client, "_get_repo_node_id", return_value="R_1")
        mocker.patch.object(
            gh_client, "_create_issue_graphql", return_value={"id": "I_2", "number": 6, "title": "t", "url": ""}
        )

        with pytest.raises(GitHubMutationOutcomeUnknownError) as excinfo:
            gh_client.create_task_issue(Mock(full_name="o/r"), 1, SamTask(task_id="T1", feature="f", task_type="impl"))

        assert excinfo.value.created_issue_number == 6
        assert "#6" in str(excinfo.value)

    @pytest.mark.parametrize(
        "close",
        [
            lambda: gh_client.close_github_issue("#5", "done", repo="o/r"),
            lambda: gh_client.resolve_github_issue("#5", summary="done", repo="o/r"),
        ],
        ids=["close", "resolve"],
    )
    def test_a_close_timeout_after_the_comment_carries_the_comment_id(
        self, mocker: MockerFixture, close: Callable[[], None]
    ) -> None:
        _gh_client_issue_setup(mocker, "_update_issue_graphql")

        with pytest.raises(GitHubMutationOutcomeUnknownError) as excinfo:
            close()

        assert excinfo.value.created_comment_id == "C_1"
        assert "C_1" in str(excinfo.value)


class TestReconcileReportsTheUnknownOutcomeNotQueued:
    """backlog_update and backlog_groom reconcile inline; an unknown audit write must not read as queued."""

    @pytest.fixture
    def backend(self, tmp_path: Path, mocker: MockerFixture) -> GitHubBackend:
        backend = GitHubBackend(repo="o/r", cache=FileCache(tmp_path))
        mocker.patch.object(backend, "reconcile", side_effect=_outcome_unknown)
        mocker.patch.object(operations, "get_config", return_value=BacklogConfig(backend=backend))
        return backend

    def test_publish_surfaces_the_error(self, backend: GitHubBackend) -> None:
        """``_publish`` is the one publish step for every mutating command, strikes included."""
        out = Output()
        context = Mock()
        context.snapshot_for.return_value = ProviderSnapshot(items=[], sync_started_at="2026-09-27T00:00:00+00:00")

        with pytest.raises(GitHubMutationOutcomeUnknownError):
            operations._publish(BacklogItem(title="t", issue="#5"), context, None, out, repo="o/r")

        assert not any("Queued" in message for message in out.to_dict().get("messages", []))


class TestARetriedCloseDoesNotRepostItsComment:
    """The closing comment landed but the close failed: the retry only closes."""

    @pytest.mark.parametrize(
        "close",
        [
            lambda: gh_client.close_github_issue("#5", "done", repo="o/r"),
            lambda: gh_client.resolve_github_issue("#5", summary="done", repo="o/r"),
        ],
        ids=["close", "resolve"],
    )
    def test_the_retry_reuses_the_landed_comment_and_closes(
        self, mocker: MockerFixture, close: Callable[[], None]
    ) -> None:
        _gh_client_issue_setup(mocker, "_update_issue_graphql")
        comments: list[IssueCommentNode] = []

        def _post(_repo: object, _issue_id: str, body: str) -> AddedCommentNode:
            comment_id = f"C_{len(comments) + 1}"
            comments.append(
                IssueCommentNode(id=comment_id, body=body, url="", author="agent", created_at="", updated_at="")
            )
            return AddedCommentNode(id=comment_id, database_id=None)

        add_comment = mocker.patch.object(gh_client, "_add_comment_graphql", side_effect=_post)
        mocker.patch.object(
            gh_client, "_fetch_issue_comments_graphql", side_effect=lambda *_args, **_kwargs: list(comments)
        )
        update = mocker.patch.object(
            gh_client,
            "_update_issue_graphql",
            side_effect=[GitHubMutationOutcomeUnknownError("close timed out", timeout_seconds=60), None],
        )
        with pytest.raises(GitHubMutationOutcomeUnknownError):
            close()

        close()

        assert add_comment.call_count == 1
        assert update.call_count == 2
        assert update.call_args.kwargs["state"] == "CLOSED"


def test_apply_status_in_progress_propagates_past_its_outer_handler(mocker: MockerFixture) -> None:
    """The public wrapper must not turn an unknown label write into a warning and a normal return."""
    _gh_client_issue_setup(mocker, "_update_issue_graphql")
    out = Output()

    with pytest.raises(GitHubMutationOutcomeUnknownError):
        gh_client.apply_status_in_progress(BacklogItem(title="t", issue="#5"), repo="o/r", output=out)

    assert not out.warnings

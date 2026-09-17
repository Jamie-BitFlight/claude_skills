"""A transient transport error must not escape ``backlog_update`` as an unhandled error.

``_rename_item_title`` and ``_apply_plan_to_item`` each mirror a backend-owned write
to the linked GitHub issue over GraphQL, inside a ``try`` whose only handler was
``except (GithubException, BacklogError)``. PyGithub does not wrap the transport
exceptions ``requests`` raises, and ``_graphql_request`` converts only
``GithubException``, so a connection error or timeout matched neither arm and left
the operation. ``backlog_update`` catches only ``BacklogError``, so the tool call
failed with an unhandled exception -- after the backend-owned write had landed.

Three sibling handlers in the same module already spread
``*RETRYABLE_TRANSIENT_EXCEPTIONS`` for exactly this reason; these two did not. The
fix adds the same spread, so a transport failure reports through the documented
``warnings`` surface like any other GitHub-side failure.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import requests

from backlog_core import operations
from backlog_core.backends.memory_backend import InMemoryBackend
from backlog_core.models import BacklogItem, Output
from backlog_core.sync_state import RETRYABLE_TRANSIENT_EXCEPTIONS

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

_TRANSPORT_FAILURE = "connection aborted by the GitHub API"


class _Repo:
    """Minimal stand-in for the PyGithub repository ``try_get_github`` returns."""

    full_name = "owner/repo"


def test_the_chosen_exception_is_one_the_sibling_handlers_already_treat_as_transient() -> None:
    """Pin the reproduction to the shared tuple rather than to one hard-coded class."""
    assert requests.exceptions.ConnectionError in RETRYABLE_TRANSIENT_EXCEPTIONS


@pytest.fixture
def _github_unreachable_mid_request(mocker: MockerFixture) -> None:
    """Wire an integer-ID backend holding one linked item whose GraphQL call drops.

    ``try_get_github`` must return a repository: the mirror only runs on the branch
    that has decided GitHub is reachable, and the transport failure then happens on
    the request itself. Both operations reach ``_fetch_issue_graphql`` first, so
    failing it covers the title and the plan path alike.
    """
    backend = InMemoryBackend()
    backend.put_work_item(BacklogItem(title="Offline Item", issue="#42", section="P1"))
    mocker.patch.object(operations, "get_config", return_value=mocker.Mock(backend=backend))
    mocker.patch.object(operations, "try_get_github", return_value=_Repo())
    mocker.patch.object(
        operations, "_fetch_issue_graphql", side_effect=requests.exceptions.ConnectionError(_TRANSPORT_FAILURE)
    )


def _warnings(result: object) -> list[str]:
    """Return the warnings an operation result carries.

    Returns:
        The ``warnings`` list, or an empty list when the result carries none.
    """
    assert isinstance(result, dict)
    warnings = result.get("warnings", [])
    assert isinstance(warnings, list)
    return warnings


@pytest.mark.usefixtures("_github_unreachable_mid_request")
def test_a_title_update_reports_a_dropped_connection_instead_of_raising() -> None:
    """``_rename_item_title``'s mirror failure reaches the caller as a warning."""
    result = operations.update_item(selector="Offline Item", title="Renamed", output=Output())

    assert result.get("renamed_to") == "Renamed"
    assert any(_TRANSPORT_FAILURE in w for w in _warnings(result)), _warnings(result)


@pytest.mark.usefixtures("_github_unreachable_mid_request")
def test_a_plan_update_reports_a_dropped_connection_instead_of_raising() -> None:
    """``_apply_plan_to_item``'s mirror failure reaches the caller as a warning."""
    result = operations.update_item(selector="Offline Item", plan="plan/tasks.yaml", output=Output())

    assert result.get("plan") == "plan/tasks.yaml"
    assert any(_TRANSPORT_FAILURE in w for w in _warnings(result)), _warnings(result)

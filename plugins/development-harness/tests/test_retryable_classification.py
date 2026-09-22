"""Every failure response says whether the same call can succeed again (R3).

A caller that cannot tell a dropped connection from a selector that matched nothing has two bad
options: retry everything, or retry nothing. The answer was already computed -- ``classify_sync_error``
has resolved it for the background sync engine all along -- and never reached the caller.

Reusing that classifier alone is not enough, and this file exists mostly to hold the line where it
is not. It was written for sync, where every ``BacklogError`` means a fetch failed and is worth
another attempt. At the tool boundary that default is wrong: ``ItemNotFoundError`` is a
``BacklogError`` too, and telling a caller to retry a selector that matched nothing sends it round a
loop that cannot terminate.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from backlog_core import operations as _ops
from backlog_core.dispatch_state import DispatchStateManager
from backlog_core.models import (
    AmbiguousSelectorError,
    BacklogError,
    BranchConflictError,
    CacheStateCorruptError,
    ContentConflictError,
    ContentNotFoundError,
    ContentUnavailableError,
    EntryNotFoundError,
    GitHubUnavailableError,
    GraphQLUnavailableError,
    ItemNotFoundError,
    UnsupportedBackendCapabilityError,
    UnsupportedCapabilityError,
    ValidationError,
)
from backlog_core.server import _require_artifact_entries, _retryable, mcp
from backlog_core.sync_state import RETRYABLE_TRANSIENT_EXCEPTIONS
from backlog_core.tool_responses import DispatchStaleCheckResponse, FallibleToolResponse
from fastmcp.client import Client
from github import GithubException
from progressive_markdown.exceptions import OrdinalNotFoundError

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Any

    from pytest_mock import MockerFixture

_REPEATS_IDENTICALLY = [
    ItemNotFoundError("#404"),
    EntryNotFoundError("e1", ["e2", "e3"]),
    AmbiguousSelectorError("auth", []),
    ValidationError("priority must be P0-P3"),
    ContentConflictError("revision moved"),
    ContentNotFoundError("no such record"),
    BranchConflictError("feature", "main"),
    CacheStateCorruptError("cache unreadable"),
    OrdinalNotFoundError("9.9", ["1", "2"]),
    UnsupportedBackendCapabilityError("sqlite", "milestones", "milestones"),
    UnsupportedCapabilityError("this backend stores no content"),
    GraphQLUnavailableError("the environment refuses GraphQL"),
]

#: Failures at the transport, not in the call: the request never reached a backend that could
#: answer it, or reached one that asked for the attempt to be made again. The identical call is
#: worth repeating because what failed was the trip, not what was asked for.
_TRIP_FAILED = [
    *(transport("the transport failed") for transport in RETRYABLE_TRANSIENT_EXCEPTIONS),
    GitHubUnavailableError("network blocked"),
    ContentUnavailableError("network blocked"),
    GithubException(503, {"message": "Service Unavailable"}, {}),
    GithubException(429, {"message": "rate limited"}, {}),
    GithubException(403, {"message": "slow down"}, {"Retry-After": "30"}),
]


@pytest.mark.parametrize("exc", _REPEATS_IDENTICALLY, ids=lambda e: type(e).__name__)
def test_a_failure_about_the_call_is_never_retryable(exc: BaseException) -> None:
    assert _retryable(exc) is False, (
        f"{type(exc).__name__} describes the call, not the trip to the backend. Repeating the "
        f"identical call repeats the identical outcome, so reporting it as retryable sends the "
        f"caller round a loop that cannot terminate."
    )


@pytest.mark.parametrize("exc", _TRIP_FAILED, ids=lambda e: type(e).__name__)
def test_a_failure_of_the_trip_is_retryable(exc: BaseException) -> None:
    assert _retryable(exc) is True, (
        f"{type(exc).__name__} says the request never got an answer, not that the request was "
        f"wrong. It succeeds as soon as the transport recovers, so reporting it as final tells "
        f"the caller to give up on work that would go through."
    )


def test_a_bare_backlog_error_carries_the_verdict_its_raise_site_states() -> None:
    """The condition fixes the answer, so the author who knows it states it once, at the raise."""
    assert _retryable(BacklogError("Item has no backend reference", retryable=False)) is False
    assert _retryable(BacklogError("GraphQL request failed: 502", retryable=True)) is True


def test_a_bare_backlog_error_with_no_stated_verdict_reports_nothing() -> None:
    """The class spans both answers and the message is prose, so no verdict is supportable.

    ``BacklogError`` is raised both for a fetch that failed on the way to the backend and for a
    call the backend refused on its merits. Nothing on the exception separates them, and guessing
    one default mislabels every raise site that meant the other.
    """
    assert _retryable(BacklogError("the fetch failed")) is None


def test_an_unclassified_failure_reports_nothing_rather_than_no() -> None:
    """A missing verdict is "not known", never "cannot succeed"."""
    assert _retryable(RuntimeError("something else entirely")) is None


def test_an_unknown_verdict_leaves_the_field_off_the_wire() -> None:
    """``exclude_none=True`` drops it, so the caller never reads a verdict this server lacks."""
    dumped = FallibleToolResponse(error="something else entirely", retryable=None).model_dump(exclude_none=True)
    assert "retryable" not in dumped
    assert FallibleToolResponse(error="x", retryable=False).model_dump(exclude_none=True)["retryable"] is False


def test_success_carries_no_verdict() -> None:
    assert "retryable" not in FallibleToolResponse().model_dump(exclude_none=True)


# ---------------------------------------------------------------------------
# Raise sites whose condition fixes the answer
# ---------------------------------------------------------------------------


def test_a_missing_artifact_is_final() -> None:
    """No artifact of that id appears because none was registered; the next call finds none either."""
    with pytest.raises(BacklogError) as caught:
        _require_artifact_entries([], "No artifact with id 'a1' of type 'plan' found for item #7")
    assert _retryable(caught.value) is False


def test_a_reserved_section_name_is_final() -> None:
    """The name itself is refused, so the identical write is refused identically."""
    with pytest.raises(BacklogError) as caught:
        _ops._normalize_section_key("Description")
    assert _retryable(caught.value) is False


def test_a_capability_gap_reports_a_final_verdict_on_the_wire() -> None:
    """The dispatch models advertise ``retryable``; their one error path has to fill it."""
    gap = UnsupportedBackendCapabilityError("github_extras", "SQLiteBackend", "dispatch_stale_check")
    payload = gap.to_response(42)
    assert payload["retryable"] is False
    dumped = DispatchStaleCheckResponse.model_validate(payload).model_dump(exclude_none=True)
    assert dumped["retryable"] is False


# ---------------------------------------------------------------------------
# Dispatch arms whose answer is fixed by the branch that returns them
# ---------------------------------------------------------------------------


@pytest.fixture
def dispatch_db(mocker: MockerFixture, tmp_path: Path) -> DispatchStateManager:
    """Point the dispatch tools at a throwaway state database.

    Returns:
        The manager every dispatch tool call in this module writes to.
    """
    mgr = DispatchStateManager(tmp_path / "dispatch-test.db")
    mocker.patch("backlog_core.server._dispatch_state_manager", return_value=mgr)
    return mgr


async def _call(tool: str, args: dict[str, Any]) -> dict[str, Any]:
    async with Client(mcp) as client:
        return (await client.call_tool(tool, args)).structured_content


async def test_a_missing_dispatch_plan_is_final(mocker: MockerFixture) -> None:
    mocker.patch("backlog_core.server._read_dispatch_plan", side_effect=ContentUnavailableError("no plan stored"))
    assert (await _call("dispatch_read", {"milestone_number": 10}))["retryable"] is False


@pytest.mark.usefixtures("dispatch_db")
async def test_a_malformed_wave_item_is_final() -> None:
    result = await _call("dispatch_wave_start", {"milestone": 10, "wave_num": 1, "items": [{"issue": "not a number"}]})
    assert result["retryable"] is False


@pytest.mark.usefixtures("dispatch_db")
async def test_a_wave_that_already_exists_is_final() -> None:
    args = {"milestone": 10, "wave_num": 1, "items": [{"issue": 101, "title": "Feature A"}]}
    await _call("dispatch_wave_start", args)
    assert (await _call("dispatch_wave_start", args))["retryable"] is False


@pytest.mark.usefixtures("dispatch_db")
async def test_an_unknown_dispatch_item_is_final() -> None:
    result = await _call("dispatch_item_status", {"milestone": 10, "issue": 999, "status": "complete"})
    assert result["retryable"] is False


@pytest.mark.usefixtures("dispatch_db")
async def test_an_invalid_dispatch_status_is_final() -> None:
    await _call("dispatch_wave_start", {"milestone": 10, "wave_num": 1, "items": [{"issue": 101, "title": "A"}]})
    result = await _call("dispatch_item_status", {"milestone": 10, "issue": 101, "status": "half done"})
    assert result["retryable"] is False

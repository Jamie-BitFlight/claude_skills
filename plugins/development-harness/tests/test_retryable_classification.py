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

import importlib
import pkgutil
import subprocess
from typing import TYPE_CHECKING

import backlog_core
import pytest
from backlog_core import operations as _ops
from backlog_core.backends.bd_runner import BdInvocationError, BdJsonDecodeError, BdNotInstalledError, BdRunner
from backlog_core.backends.github_contents import _GitHubContentIntegrityError
from backlog_core.dispatch_state import DispatchStateManager
from backlog_core.models import (
    AmbiguousSelectorError,
    BackendUnavailableError,
    BacklogError,
    BranchConflictError,
    CacheStateCorruptError,
    ContentConflictError,
    ContentNotFoundError,
    ContentProviderError,
    ContentUnavailableError,
    EntryNotFoundError,
    GitHubUnavailableError,
    GraphQLUnavailableError,
    ItemNotFoundError,
    Output,
    UnsupportedBackendCapabilityError,
    UnsupportedCapabilityError,
    ValidationError,
)
from backlog_core.server import _build_section_miss_error, _require_artifact_entries, _retryable, mcp
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
    BackendUnavailableError("network blocked", retryable=True),
    ContentUnavailableError("network blocked", retryable=True),
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


@pytest.mark.parametrize("error_type", [BackendUnavailableError, ContentUnavailableError])
def test_an_unspecified_mixed_base_reports_no_verdict(error_type: type[BacklogError | ContentProviderError]) -> None:
    """The mixed bases cover structural and transport failures, so neither has a safe default."""
    assert _retryable(error_type("stored content is structurally invalid")) is None


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


# ---------------------------------------------------------------------------
# Subclasses of the two bases the transport list names
# ---------------------------------------------------------------------------


def _subclasses_of(base: type) -> set[type]:
    """Return every loaded subclass of ``base``, however deep.

    Imports the whole package first, so a subclass declared in a module no test happens to import
    is still discovered -- an undiscovered subclass is exactly the one that would ship with an
    unexamined verdict.

    Args:
        base: The exception class whose descendants to collect.

    Returns:
        Every strict subclass of ``base``.
    """
    for module in pkgutil.walk_packages(backlog_core.__path__, "backlog_core."):
        if ".tests" not in module.name:
            importlib.import_module(module.name)

    found: set[type] = set()
    pending = [base]
    while pending:
        for sub in pending.pop().__subclasses__():
            if sub not in found:
                found.add(sub)
                pending.append(sub)
    return found


class _UnspecifiedBackendUnavailable(BackendUnavailableError):
    """Test-only subclass that deliberately states no retry verdict."""


class _UnspecifiedContentUnavailable(ContentUnavailableError):
    """Test-only subclass that deliberately states no retry verdict."""


#: One instance and expected verdict per subclass of the two mixed bases. Each production instance
#: is built the way its raise site builds it; the test-only subclasses hold the default contract.
_TRANSPORT_SUBCLASS_SAMPLES: dict[type, tuple[BacklogError | ContentProviderError, bool | None]] = {
    GitHubUnavailableError: (GitHubUnavailableError("credentials are unavailable"), True),
    GraphQLUnavailableError: (GraphQLUnavailableError("the environment refuses GraphQL"), False),
    BdNotInstalledError: (BdNotInstalledError("bd is not installed; see https://beads.sh/docs/install"), False),
    BdInvocationError: (BdInvocationError("bd exited 2", ["bd", "list"], 2, "", ""), False),
    BdJsonDecodeError: (BdJsonDecodeError("stdout is not JSON", "not json"), False),
    ContentNotFoundError: (ContentNotFoundError("no such record"), False),
    _GitHubContentIntegrityError: (_GitHubContentIntegrityError("GitHub content path is not a file: docs/"), False),
    _UnspecifiedBackendUnavailable: (_UnspecifiedBackendUnavailable("no verdict"), None),
    _UnspecifiedContentUnavailable: (_UnspecifiedContentUnavailable("no verdict"), None),
}


def test_every_subclass_of_a_transport_base_is_sampled() -> None:
    """A new subclass fails here until its default behavior is exercised.

    The list is the gate: adding a subclass without adding a representative instance here fails,
    and adding it here forces the verdict test below.
    """
    declared = _subclasses_of(BackendUnavailableError) | _subclasses_of(ContentUnavailableError)
    assert declared == set(_TRANSPORT_SUBCLASS_SAMPLES), (
        f"unsampled subclasses: {sorted(c.__name__ for c in declared - set(_TRANSPORT_SUBCLASS_SAMPLES))}; "
        f"sampled but no longer declared: "
        f"{sorted(c.__name__ for c in set(_TRANSPORT_SUBCLASS_SAMPLES) - declared)}"
    )


@pytest.mark.parametrize(
    ("exc", "expected"),
    _TRANSPORT_SUBCLASS_SAMPLES.values(),
    ids=[error_type.__name__ for error_type in _TRANSPORT_SUBCLASS_SAMPLES],
)
def test_a_transport_subclass_uses_only_its_stated_verdict(
    exc: BacklogError | ContentProviderError, expected: bool | None
) -> None:
    """A subclass inherits no verdict from a base that spans incompatible conditions.

    Known conditions state an answer. A newly declared subclass starts unknown until its own
    constructor or raise site has enough evidence to state one.
    """
    assert _retryable(exc) is expected


@pytest.mark.parametrize("verdict", [True, False])
@pytest.mark.parametrize("error_type", [_UnspecifiedBackendUnavailable, _UnspecifiedContentUnavailable])
def test_an_explicit_subclass_instance_verdict_wins(
    error_type: type[BacklogError | ContentProviderError], verdict: bool
) -> None:
    """Raise sites retain an accurate answer when a mixed subclass represents multiple failures."""
    assert _retryable(error_type("classified at the raise site", retryable=verdict)) is verdict


def test_bd_answers_a_timeout_and_a_refusal_differently() -> None:
    """One class, two conditions: the instance carries which, and the exit code names it."""
    timed_out = BdInvocationError("bd timed out after 30s", ["bd", "list"], -1, "", "")
    exited_nonzero = BdInvocationError("bd exited 2", ["bd", "list"], 2, "", "usage: bd")
    assert _retryable(timed_out) is True
    assert _retryable(exited_nonzero) is False


def test_bd_answers_a_timeout_and_a_failed_spawn_differently(mocker: MockerFixture) -> None:
    """Both carry ``returncode == -1``, and only one of them is worth attempting again.

    The exit code records that ``bd`` never ran to completion; it does not record why. A timeout
    may clear. A spawn that failed may have failed on a permission bit or on momentary resource
    pressure, and nothing at that raise site separates the two -- so it states no verdict rather
    than pick one, and the boundary leaves the key off the wire.
    """
    mocker.patch("backlog_core.backends.bd_runner.shutil.which", return_value="/usr/local/bin/bd")

    mocker.patch(
        "backlog_core.backends.bd_runner.subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=["bd"], timeout=30)
    )
    with pytest.raises(BdInvocationError) as timed_out:
        BdRunner().run_json(["show", "bd-a3f8"])

    mocker.patch("backlog_core.backends.bd_runner.subprocess.run", side_effect=OSError("Permission denied"))
    with pytest.raises(BdInvocationError) as never_started:
        BdRunner().run_json(["show", "bd-a3f8"])

    assert timed_out.value.returncode == never_started.value.returncode == -1
    assert _retryable(timed_out.value) is True
    assert _retryable(never_started.value) is None


def test_a_section_the_item_does_not_hold_is_final() -> None:
    """The filter is matched against the item's own inventory, which the next call re-reads the same."""
    miss = _build_section_miss_error("Nonexistent", ["Description", "Plan"], Output())
    assert miss["retryable"] is False


async def test_a_plan_that_disagrees_with_its_milestone_is_final() -> None:
    """Two arguments that contradict each other contradict each other identically next time."""
    plan = {
        "milestone": {"number": 11, "title": "Provider plan", "integration-branch": "main"},
        "waves": [{"wave": 1, "items": [{"title": "Issue", "issue": 101, "priority": "P1"}]}],
    }
    assert (await _call("dispatch_create_plan", {"milestone_number": 10, "plan": plan}))["retryable"] is False


async def test_a_structural_content_failure_omits_retryable_on_the_wire(mocker: MockerFixture) -> None:
    """An exact mixed-base instance must not serialize the old transport-default verdict."""
    mocker.patch(
        "backlog_core.server._read_dispatch_plan",
        side_effect=ContentUnavailableError("Dispatch content envelope is invalid"),
    )
    result = await _call("dispatch_validate", {"milestone_number": 10})
    assert result["error"] == "Dispatch content envelope is invalid"
    assert "retryable" not in result


async def test_an_explicit_connectivity_failure_keeps_retryable_on_the_wire(mocker: MockerFixture) -> None:
    """Removing the unsafe base default must not erase a raise site's supported transport verdict."""
    mocker.patch(
        "backlog_core.server._read_dispatch_plan",
        side_effect=ContentUnavailableError("connection timed out", retryable=True),
    )
    result = await _call("dispatch_validate", {"milestone_number": 10})
    assert result["retryable"] is True


async def test_a_plan_that_already_exists_is_final(mocker: MockerFixture) -> None:
    """The refusal names the parameter that lifts it, which is what makes it final and not transient."""
    provider = mocker.patch("backlog_core.server._get_artifact_provider").return_value
    provider.get_content.return_value = mocker.Mock(revision="rev1")
    plan = {
        "milestone": {"number": 10, "title": "Provider plan", "integration-branch": "main"},
        "waves": [{"wave": 1, "items": [{"title": "Issue", "issue": 101, "priority": "P1"}]}],
    }
    result = await _call("dispatch_create_plan", {"milestone_number": 10, "plan": plan, "overwrite": False})
    assert result["retryable"] is False

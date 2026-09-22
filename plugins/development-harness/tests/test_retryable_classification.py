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

import pytest
from backlog_core.models import (
    AmbiguousSelectorError,
    BacklogError,
    BranchConflictError,
    CacheStateCorruptError,
    ContentConflictError,
    ContentNotFoundError,
    EntryNotFoundError,
    GraphQLUnavailableError,
    ItemNotFoundError,
    UnsupportedBackendCapabilityError,
    ValidationError,
)
from backlog_core.server import _retryable
from backlog_core.tool_responses import FallibleToolResponse
from progressive_markdown.exceptions import OrdinalNotFoundError

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
    GraphQLUnavailableError("the environment refuses GraphQL"),
]


@pytest.mark.parametrize("exc", _REPEATS_IDENTICALLY, ids=lambda e: type(e).__name__)
def test_a_failure_about_the_call_is_never_retryable(exc: BaseException) -> None:
    assert _retryable(exc) is False, (
        f"{type(exc).__name__} describes the call, not the trip to the backend. Repeating the "
        f"identical call repeats the identical outcome, so reporting it as retryable sends the "
        f"caller round a loop that cannot terminate."
    )


def test_a_failure_reaching_the_backend_is_retryable() -> None:
    """The sync classifier's own verdict still stands where it was right."""
    assert _retryable(BacklogError("the fetch failed")) is True


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

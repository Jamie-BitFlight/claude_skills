"""Tests for ``dh_core.known_failure_types`` -- the Worker's work-failure vocabulary.

The load-bearing test here is the boundary one: no failure code may collide with a
``dh_core.ledger_spec.REASONS`` code. The two vocabularies answer different questions -- a ``REASONS``
code says why a CLI command refused, a failure code says why a Worker could not proceed -- and a
shared code would let an agent name a condition the ledger already refuses, which the module's
docstring forbids.
"""

from __future__ import annotations

import json

import pytest
from dh_core.known_failure_types import (
    KNOWN_FAILURE_TYPES,
    LEDGER_OWNED_CONDITIONS,
    FailureCategory,
    KnownFailureTypesPage,
    failure_type,
    page,
)
from dh_core.ledger_spec import REASONS


def _reason_codes() -> set[str]:
    return {reason.code for reason in REASONS}


def test_no_failure_code_collides_with_a_ledger_reason_code() -> None:
    """A failure type never names a condition the ledger already refuses with a REASONS code."""
    collisions = sorted({row.code for row in KNOWN_FAILURE_TYPES} & _reason_codes())
    assert not collisions, (
        f"These codes exist in both KNOWN_FAILURE_TYPES and ledger_spec.REASONS: {collisions}. "
        "A condition the ledger refuses is named by its REASONS code, never by a new failure type."
    )


def test_no_failure_specific_collides_with_a_ledger_reason_code() -> None:
    """The un-namespaced half of a code does not shadow a REASONS code either.

    ``code`` carries the category prefix, so a bare collision test on ``code`` alone would pass for
    a row whose ``specific`` is literally ``not-ready`` or ``attempts-exhausted`` -- which an agent
    writing a status report would still confuse with the ledger's own code.
    """
    collisions = sorted({row.specific for row in KNOWN_FAILURE_TYPES} & _reason_codes())
    assert not collisions, f"These failure-type `specific` values shadow a REASONS code: {collisions}"


def test_every_ledger_owned_condition_names_a_real_reason_code() -> None:
    """LEDGER_OWNED_CONDITIONS stays in step with the reason codes it points at."""
    unknown = sorted({code for _, code in LEDGER_OWNED_CONDITIONS} - _reason_codes())
    assert not unknown, f"LEDGER_OWNED_CONDITIONS names codes that ledger_spec.REASONS does not define: {unknown}"


def test_codes_are_unique() -> None:
    """Two rows never share a code. Import-time enforcement, restated as a test."""
    codes = [row.code for row in KNOWN_FAILURE_TYPES]
    assert len(codes) == len(set(codes))


def test_code_is_the_category_joined_to_the_specific() -> None:
    """`code` is derived, so its prefix cannot disagree with the row's typed category."""
    for row in KNOWN_FAILURE_TYPES:
        assert row.code == f"{row.category.value}:{row.specific}"
        assert row.category in FailureCategory


def test_every_row_carries_a_description_and_an_origin() -> None:
    """A row an agent chooses between needs prose to choose by, and provenance to audit."""
    for row in KNOWN_FAILURE_TYPES:
        assert row.description.strip(), f"{row.code}: empty description"
        assert row.origin.strip(), f"{row.code}: empty origin"


def test_a_routed_row_names_where_each_route_came_from() -> None:
    """Route suggestions carry a source, so an invented route cannot pass for a derived one."""
    for row in KNOWN_FAILURE_TYPES:
        for route in row.suggested_routes:
            assert route.action.strip(), f"{row.code}: route with an empty action"
            assert route.source.strip(), f"{row.code}: route '{route.action}' has no source"


def test_at_least_one_row_suggests_more_than_one_route() -> None:
    """The field is plural because one failure type can suggest several paths."""
    assert any(len(row.suggested_routes) > 1 for row in KNOWN_FAILURE_TYPES)


def test_page_returns_the_whole_table_by_default() -> None:
    """No caller is silently handed a window it did not ask for."""
    result = page()
    assert result.total == len(KNOWN_FAILURE_TYPES)
    assert result.returned == len(KNOWN_FAILURE_TYPES)
    assert result.failure_types == KNOWN_FAILURE_TYPES


def test_page_windows_and_still_reports_the_total() -> None:
    """A windowed result says how much of the table it is not showing."""
    result = page(offset=1, limit=2)
    assert result.total == len(KNOWN_FAILURE_TYPES)
    assert result.offset == 1
    assert result.returned == 2
    assert result.failure_types == KNOWN_FAILURE_TYPES[1:3]


def test_page_past_the_end_returns_an_empty_window_not_an_error() -> None:
    result = page(offset=len(KNOWN_FAILURE_TYPES) + 5)
    assert result.returned == 0
    assert result.total == len(KNOWN_FAILURE_TYPES)


@pytest.mark.parametrize(("offset", "limit"), [(-1, None), (0, -1)])
def test_page_rejects_negative_windows(offset: int, limit: int | None) -> None:
    with pytest.raises(ValueError, match="must not be negative"):
        page(offset=offset, limit=limit)


def test_failure_type_looks_a_row_up_by_code() -> None:
    row = KNOWN_FAILURE_TYPES[0]
    assert failure_type(row.code) is row
    assert failure_type("no-such-category:no-such-code") is None


def test_the_owners_worked_example_is_present_and_suggests_both_of_its_paths() -> None:
    """The example the vocabulary was specified against, kept as a regression guard."""
    row = failure_type("pre-requisites-missing:expected-code-functionality-not-available-in-worktree")
    assert row is not None
    actions = " ".join(route.action.lower() for route in row.suggested_routes)
    assert "worktree" in actions
    assert "prior task" in actions


def test_the_page_serializes_to_compact_json_carrying_the_derived_code() -> None:
    """The wire form an agent reads includes `code`, which is a computed field rather than stored."""
    payload = json.loads(page(limit=1).model_dump_json())
    assert payload["total"] == len(KNOWN_FAILURE_TYPES)
    assert payload["failure_types"][0]["code"] == KNOWN_FAILURE_TYPES[0].code
    assert KnownFailureTypesPage.model_validate(payload).returned == 1

"""Regression tests for the status-filter fabrication bug (#3546, B-critique.md §3.1).

``_item_derived_status`` used to return the literal ``"needs-grooming"`` for *every*
numeric-issue item whenever the live status map was empty, with no way to tell "the
fetch answered and genuinely found nothing for this item" apart from "the fetch
never answered at all". Since B1 (``claude/gh-client-stop-swallowing-3546``) made a
degraded/refused status batch fetch raise a typed, distinguishable exception instead
of silently returning ``{}``, ``list_items`` can catch that exception — but merely
catching it and falling through to the same empty ``status_map`` reproduced the exact
bug the critique proved: a ``status="needs-grooming"`` filter *fabricated* matches for
items whose true live status was something else entirely, while a
``status="in-progress"`` filter silently dropped items that do match, with nothing in
the response to say the result was unreliable.

This mirrors ``scratchpad/design/proofs/test_critique_proofs.py``'s P1/P2 reproduction
shape (three items, two genuinely ``in-progress``, one genuinely ``needs-grooming``),
adapted to patch ``operations.batch_fetch_statuses`` with the typed exception B1
introduced rather than the pre-B1 empty-map behaviour the original proof used.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from backlog_core import operations
from backlog_core.models import BacklogItem, GraphQLUnavailableError, IssueStatus, Output

if TYPE_CHECKING:
    from collections.abc import Mapping

    from pytest_mock import MockerFixture

_REFUSAL_MESSAGE = "GitHub GraphQL is not available from Claude Code sessions; use the REST API"


def _item(num: int, title: str) -> BacklogItem:
    """Build an open P1 backlog item with a numeric issue reference.

    The local ``status`` field is left at its default (``"needs-grooming"``,
    same as every fixture in the critique's own proof) so a fix that fell back
    to the locally cached status under degradation would reproduce the same
    fabrication rather than fixing it.
    """
    return BacklogItem(title=title, section="P1", skip=False, issue=f"#{num}")


ITEMS = [_item(1, "Alpha"), _item(2, "Beta"), _item(3, "Gamma")]
LIVE_MAP = {
    1: IssueStatus(status="in-progress", milestone=""),
    2: IssueStatus(status="in-progress", milestone=""),
    3: IssueStatus(status="needs-grooming", milestone=""),
}


class _Backend:
    """Minimal provider-backed backend stand-in exposing only what list_items reads."""

    supports_batch_status_fetch = True

    def __init__(self, items: list[BacklogItem]) -> None:
        self._items = items

    def list_work_items(self) -> list[BacklogItem]:
        return list(self._items)


def _patch_backend(mocker: MockerFixture) -> None:
    mocker.patch.object(operations, "get_config", return_value=mocker.Mock(backend=_Backend(ITEMS)))


def _titles(result: Mapping[str, object]) -> list[str]:
    items = cast("list[dict[str, object]]", result["items"])
    return [str(it["title"]) for it in items]


def _warnings(result: Mapping[str, object]) -> list[str]:
    raw = result.get("warnings", [])
    return [str(entry) for entry in raw] if isinstance(raw, list) else []


class TestStatusFilterDoesNotFabricateMatches:
    """status='needs-grooming' must not gain false positives under a degraded status map."""

    def test_healthy_baseline_matches_only_the_genuine_item(self, mocker: MockerFixture) -> None:
        _patch_backend(mocker)
        mocker.patch.object(operations, "batch_fetch_statuses", return_value=LIVE_MAP)

        result = operations.list_items(status="needs-grooming", output=Output())

        assert result["count"] == 1
        assert _titles(result) == ["Gamma"]

    def test_degraded_fetch_does_not_invent_matches(self, mocker: MockerFixture) -> None:
        """The critique's exact reproduction: a refusal must not turn 1 real match into 3."""
        _patch_backend(mocker)
        mocker.patch.object(operations, "batch_fetch_statuses", side_effect=GraphQLUnavailableError(_REFUSAL_MESSAGE))

        result = operations.list_items(status="needs-grooming", output=Output())

        assert result["count"] == 0, "a degraded status batch must not fabricate needs-grooming matches"
        assert _titles(result) == []
        # Alpha and Beta are genuinely in-progress -- neither may appear under
        # a needs-grooming filter regardless of what the map could not confirm.
        assert "Alpha" not in _titles(result)
        assert "Beta" not in _titles(result)

    def test_degraded_fetch_does_not_fabricate_for_other_backend_failures_either(self, mocker: MockerFixture) -> None:
        """Not just the GraphQL-refusal marker -- any BackendUnavailableError subclass must not fabricate."""
        from backlog_core.models import GitHubUnavailableError

        _patch_backend(mocker)
        mocker.patch.object(operations, "batch_fetch_statuses", side_effect=GitHubUnavailableError("network error"))

        result = operations.list_items(status="needs-grooming", output=Output())

        assert result["count"] == 0


class TestStatusFilterDegradationIsDisclosedNotSilent:
    """status='in-progress' may still miss real matches under a degraded map (nothing else is
    possible -- the live status was never learned), but the caller must be told the result is
    unreliable rather than have it look like a genuine, confident zero.
    """

    def test_healthy_baseline_matches_both_genuine_items(self, mocker: MockerFixture) -> None:
        _patch_backend(mocker)
        mocker.patch.object(operations, "batch_fetch_statuses", return_value=LIVE_MAP)

        result = operations.list_items(status="in-progress", output=Output())

        assert result["count"] == 2
        assert sorted(_titles(result)) == ["Alpha", "Beta"]

    def test_degraded_fetch_carries_a_warning_instead_of_a_silent_zero(self, mocker: MockerFixture) -> None:
        _patch_backend(mocker)
        mocker.patch.object(operations, "batch_fetch_statuses", side_effect=GraphQLUnavailableError(_REFUSAL_MESSAGE))
        out = Output()

        result = operations.list_items(status="in-progress", output=out)

        assert result["count"] == 0, "the live status was never learned -- a match cannot be asserted either"
        warnings = _warnings(result)
        assert warnings, "an unverifiable status filter result must not be silent"
        assert any("status" in w and "in-progress" in w for w in warnings), (
            f"warning must name the filter that could not be verified, got: {warnings}"
        )

    def test_healthy_listing_with_a_status_filter_carries_no_such_warning(self, mocker: MockerFixture) -> None:
        _patch_backend(mocker)
        mocker.patch.object(operations, "batch_fetch_statuses", return_value=LIVE_MAP)

        result = operations.list_items(status="in-progress", output=Output())

        assert not any("unavailable" in w.lower() for w in _warnings(result))


class TestItemDerivedStatusUnavailableMap:
    """Unit-level coverage of the discriminator itself."""

    def test_numeric_issue_item_returns_none_when_map_unavailable(self) -> None:
        item = _item(1, "Alpha")

        assert operations._item_derived_status(item, {}, status_map_unavailable=True) is None

    def test_numeric_issue_item_still_defaults_to_needs_grooming_when_map_answered_but_empty(self) -> None:
        """A genuinely successful fetch that found nothing for this item is a real answer,
        not an unavailable one -- the pre-existing default must survive unchanged.
        """
        item = _item(1, "Alpha")

        assert operations._item_derived_status(item, {}, status_map_unavailable=False) == "needs-grooming"

    def test_numeric_issue_item_prefers_map_entry_when_available(self) -> None:
        item = _item(1, "Alpha")

        status = operations._item_derived_status(item, LIVE_MAP, status_map_unavailable=False)

        assert status == "in-progress"

    def test_string_id_and_issueless_items_are_unaffected_by_the_unavailable_flag(self) -> None:
        """A beads nanoid / issueless item never depended on the live map in the first
        place, so status_map_unavailable must not change its resolved status.
        """
        beads_item = BacklogItem(title="Beads item", section="P1", skip=False, issue="bd-a3f8", status="in-progress")

        assert (
            operations._item_derived_status(beads_item, {}, status_map_unavailable=True)
            == operations._item_derived_status(beads_item, {}, status_map_unavailable=False)
            == "in-progress"
        )

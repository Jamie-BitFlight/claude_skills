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

A second trigger for the same ambiguity was found by review after B2 landed: an
absent ``GITHUB_TOKEN`` makes ``gh_client.batch_fetch_statuses`` return the same empty
``{}`` *without* raising (a deliberate local-only fallback, not a failure — see its
own docstring), so B2's exception-only handling left that path reproducing the exact
fabrication bug via a different trigger. ``TestStatusFilterMissingTokenDoesNotFabricateMatches``
and ``TestStatusMapEmptyDueToMissingToken`` cover that trigger.

A third review pass (P1, on PR #3572) found that the fix for the redundant-probe issue
had reintroduced a different bug: ``_status_map_empty_due_to_missing_token`` imported
``resolve_token()`` from ``github_client`` directly, which is a provider-client import
``operations.py`` is architecturally forbidden from making (see
``backlog_core/ARCHITECTURE.md``'s "Module: operations.py" boundary). The fix asks the
backend through ``CredentialAvailabilityProvider.has_github_credentials()`` instead, so
the tests below patch that backend method rather than ``operations.resolve_token``.
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
    """Minimal provider-backed backend stand-in exposing only what list_items reads.

    Implements ``CredentialAvailabilityProvider`` structurally
    (``has_github_credentials``) so ``isinstance`` checks in
    ``_status_map_empty_due_to_missing_token`` pass the same way the real
    ``GitHubBackend`` does.
    """

    supports_batch_status_fetch = True
    supports_github_extras = True

    def __init__(self, items: list[BacklogItem], *, has_credentials: bool = True) -> None:
        self._items = items
        self._has_credentials = has_credentials

    def list_work_items(self) -> list[BacklogItem]:
        return list(self._items)

    def has_github_credentials(self) -> bool:
        return self._has_credentials


def _patch_backend(
    mocker: MockerFixture, items: list[BacklogItem] | None = None, *, has_credentials: bool = True
) -> _Backend:
    """Install a ``_Backend`` stand-in as the active backend and return it.

    Returning the instance lets callers spy on or reconfigure
    ``has_github_credentials`` per test without a second patch call.
    """
    backend = _Backend(items or ITEMS, has_credentials=has_credentials)
    mocker.patch.object(operations, "get_config", return_value=mocker.Mock(backend=backend))
    return backend


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


class TestStatusFilterMissingTokenDoesNotFabricateMatches:
    """The missing-token trigger for the same ambiguity B2 fixed for a raised refusal.

    ``gh_client.batch_fetch_statuses`` returns ``{}`` — with no exception — when no
    ``GITHUB_TOKEN`` is configured, by design (a local-only fallback, not a failure).
    That is the exact same empty map a genuinely-answered, empty live fetch would also
    return, so ``list_items`` must tell the two apart via the backend's
    ``has_github_credentials()`` rather than letting a numeric-issue item's status
    default to ``"needs-grooming"`` as though the fetch had genuinely answered.
    """

    def test_missing_token_does_not_fabricate_needs_grooming_matches(self, mocker: MockerFixture) -> None:
        _patch_backend(mocker, has_credentials=False)
        mocker.patch.object(operations, "batch_fetch_statuses", return_value={})

        result = operations.list_items(status="needs-grooming", output=Output())

        assert result["count"] == 0, "a missing token must not fabricate needs-grooming matches"
        assert _titles(result) == []

    def test_missing_token_does_not_silently_drop_in_progress_matches(self, mocker: MockerFixture) -> None:
        _patch_backend(mocker, has_credentials=False)
        mocker.patch.object(operations, "batch_fetch_statuses", return_value={})
        out = Output()

        result = operations.list_items(status="in-progress", output=out)

        assert result["count"] == 0, "the live status was never learned -- a match cannot be asserted either"
        warnings = _warnings(result)
        assert warnings, "a missing-token result must not look like a confident zero"
        assert any("GITHUB_TOKEN" in w for w in warnings), f"warning must name the missing token, got: {warnings}"

    def test_genuinely_empty_live_result_with_token_present_is_not_reported_unavailable(
        self, mocker: MockerFixture
    ) -> None:
        """A real GitHub connection that genuinely found nothing must stay a confident zero.

        ``has_github_credentials()`` returning ``True`` signals a token is configured,
        so the empty map must be trusted as a real answer instead of triggering the
        missing-token disambiguation.
        """
        _patch_backend(mocker)
        mocker.patch.object(operations, "batch_fetch_statuses", return_value={})
        out = Output()

        result = operations.list_items(status="in-progress", output=out)

        assert result["count"] == 0
        assert not any("unavailable" in w.lower() for w in _warnings(result))

    def test_genuinely_empty_live_result_does_not_re_probe_github(self, mocker: MockerFixture) -> None:
        """A successful, genuinely-empty status batch must not trigger a second live
        GitHub lookup (#3572).

        ``batch_fetch_statuses`` already performed the live ``try_get_github`` repository
        lookup before completing its GraphQL query and returning the (legitimately
        empty) map. The missing-token disambiguation must ask the backend's local
        ``has_github_credentials()`` instead of repeating that lookup -- a redundant
        network call on every listing that, if it hit a rate limit or timed out, would
        mark an already-successful result unavailable and wrongly exclude numeric-issue
        items from a status filter.
        """
        _patch_backend(mocker)
        mocker.patch.object(operations, "batch_fetch_statuses", return_value={})
        try_get_github_spy = mocker.patch.object(operations, "try_get_github")

        result = operations.list_items(status="in-progress", output=Output())

        assert result["count"] == 0
        try_get_github_spy.assert_not_called()


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


class TestStatusMapEmptyDueToMissingToken:
    """Unit-level coverage of ``_status_map_empty_due_to_missing_token``'s guard conditions.

    The helper asks the backend through ``CredentialAvailabilityProvider``
    (``has_github_credentials()``) rather than importing
    ``github_client.resolve_token()`` directly -- ``operations.py`` must not import
    provider clients (see ``backlog_core/ARCHITECTURE.md``'s "Module: operations.py"
    boundary; P1 finding on #3572). These tests patch or configure
    ``has_github_credentials`` to stand in for token presence/absence, and assert it
    is left uncalled wherever the guard short-circuits before that question would
    matter.
    """

    def test_true_when_no_token_and_a_numeric_issue_item_exists(self, mocker: MockerFixture) -> None:
        _patch_backend(mocker, has_credentials=False)

        assert operations._status_map_empty_due_to_missing_token(ITEMS) is True

    def test_false_when_token_is_present(self, mocker: MockerFixture) -> None:
        _patch_backend(mocker, has_credentials=True)

        assert operations._status_map_empty_due_to_missing_token(ITEMS) is False

    def test_false_when_no_numeric_issue_item_present(self, mocker: MockerFixture) -> None:
        """A beads-style item never reads status_map_unavailable, so the disambiguation
        would be pure unnecessary credential-check overhead for no observable effect.
        """
        beads_item = BacklogItem(title="Beads item", section="P1", skip=False, issue="bd-a3f8")
        backend = _patch_backend(mocker, items=[beads_item], has_credentials=False)
        has_credentials_spy = mocker.spy(backend, "has_github_credentials")

        assert operations._status_map_empty_due_to_missing_token([beads_item]) is False
        has_credentials_spy.assert_not_called()

    def test_false_when_backend_has_no_github_connection_concept(self, mocker: MockerFixture) -> None:
        """A backend like beads/SQLite/in-memory has no token concept at all -- that must
        never be misread as "unavailable".
        """

        class _NoGitHubBackend(_Backend):
            supports_github_extras = False

        backend = _NoGitHubBackend(ITEMS, has_credentials=False)
        mocker.patch.object(operations, "get_config", return_value=mocker.Mock(backend=backend))
        has_credentials_spy = mocker.spy(backend, "has_github_credentials")

        assert operations._status_map_empty_due_to_missing_token(ITEMS) is False
        has_credentials_spy.assert_not_called()

    def test_false_when_backend_does_not_implement_credential_availability_provider(
        self, mocker: MockerFixture
    ) -> None:
        """A GitHub-capable backend that has not implemented ``CredentialAvailabilityProvider``
        must not have "missing token" fabricated on its behalf.

        This is the pre-9e926cb41 fallback semantics preserved for a backend that
        genuinely cannot answer the question: assume credentials might be present
        rather than claim "missing token" for an unverified backend, and do so without
        any network re-probe (the ``_NoCredentialProtocolBackend`` stand-in below has
        no ``try_get_github`` mock installed, so a re-probe would raise ``AttributeError``
        on ``get_config().backend.try_get_github`` if one were attempted).
        """

        class _NoCredentialProtocolBackend:
            supports_batch_status_fetch = True
            supports_github_extras = True

            def __init__(self, items: list[BacklogItem]) -> None:
                self._items = items

            def list_work_items(self) -> list[BacklogItem]:
                return list(self._items)

        backend = _NoCredentialProtocolBackend(ITEMS)
        mocker.patch.object(operations, "get_config", return_value=mocker.Mock(backend=backend))

        assert operations._status_map_empty_due_to_missing_token(ITEMS) is False

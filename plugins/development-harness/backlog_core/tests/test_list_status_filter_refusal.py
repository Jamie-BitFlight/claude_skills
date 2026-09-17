"""Tests for what a ``--status`` filter means when the live status query never answered.

An empty status map has two causes that read identically at the call site: the
query ran and found no status labels, or the query never ran — the backend has
no batch status fetch, or refused the one it was given. Only the first licenses
the ``"needs-grooming"`` default, because only the first established anything
about the issue.

Deriving that default from the second inverted every ``--status`` filter in a
sandbox that rejects GraphQL: ``--status status:in-progress`` matched nothing
and ``--status needs-grooming`` matched everything, against a backlog where the
opposite was true. The listing stays non-fatal — the cached status answers the
filter, and the warning says so.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backlog_core import operations
from backlog_core.models import BacklogItem, GraphQLUnavailableError, IssueStatus, Output

if TYPE_CHECKING:
    from collections.abc import Mapping

    from pytest_mock import MockerFixture

_REFUSAL_MESSAGE = "GitHub GraphQL is not available from Claude Code sessions; use the REST API"


def _item(issue: str, title: str = "An item", status: str = "status:in-progress") -> BacklogItem:
    """Build an open backlog item carrying the given issue reference and cached status."""
    return BacklogItem(title=title, issue=issue, section="P1", status=status)


class _Backend:
    """Backend stub exposing only what ``list_items`` reads."""

    def __init__(self, items: list[BacklogItem], *, supports_batch_status_fetch: bool = True) -> None:
        self._items = items
        self.supports_batch_status_fetch = supports_batch_status_fetch

    def list_work_items(self) -> list[BacklogItem]:
        return self._items


def _patch_backend(mocker: MockerFixture, items: list[BacklogItem], *, batch: bool = True) -> None:
    """Point ``operations.get_config()`` at a backend serving *items*."""
    backend = _Backend(items, supports_batch_status_fetch=batch)
    mocker.patch.object(operations, "get_config", return_value=mocker.Mock(backend=backend))


def _refuse(mocker: MockerFixture) -> None:
    """Make the live status query raise the environment-wide refusal."""
    mocker.patch.object(operations, "batch_fetch_statuses", side_effect=GraphQLUnavailableError(_REFUSAL_MESSAGE))


def _statuses(result: Mapping[str, object]) -> list[str]:
    """Narrow the heterogeneous ``list_items`` result to its per-item status strings."""
    raw = result.get("items", [])
    return [str(entry.get("status", "")) for entry in raw] if isinstance(raw, list) else []


class TestDerivedStatusWithoutALiveAnswer:
    """``_item_derived_status`` must not invent a status for an issue nobody asked about."""

    def test_a_missing_key_in_a_live_map_is_still_needs_grooming(self) -> None:
        """The query ran and returned no label for this issue — that is a real answer."""
        assert operations._item_derived_status(_item("#42"), {}, status_live=True) == "needs-grooming"

    def test_a_live_labeled_needs_grooming_status_is_normalized_to_bare(self) -> None:
        """Reproduction: a live status map entry carrying the literal
        ``"status:needs-grooming"`` label (the labeled form
        ``gh_client._pick_primary_status_label`` returns when an issue genuinely
        carries the label) must derive to the same bare ``"needs-grooming"``
        value a missing map key derives to above — both mean "needs grooming"
        under the documented bare ``--status needs-grooming`` filter token.
        Before the fix this returned ``"status:needs-grooming"`` (labeled),
        which never equals the bare filter, so an issue explicitly labeled
        needs-grooming never matched its own documented filter.
        """
        status_map = {42: IssueStatus(status="status:needs-grooming", milestone="")}

        assert operations._item_derived_status(_item("#42"), status_map, status_live=True) == "needs-grooming"

    def test_a_missing_key_without_a_live_map_uses_the_cached_status(self) -> None:
        assert operations._item_derived_status(_item("#42"), {}, status_live=False) == "status:in-progress"

    def test_a_missing_key_without_a_live_map_or_a_cached_status_is_unknown(self) -> None:
        """Unknown must stay unknown: it matches no filter rather than matching the wrong one."""
        assert operations._item_derived_status(_item("#42", status=""), {}, status_live=False) == ""

    def test_a_live_map_entry_still_wins(self) -> None:
        status_map = {42: IssueStatus(status="status:done", milestone="")}

        assert operations._item_derived_status(_item("#42"), status_map, status_live=True) == "status:done"

    def test_a_string_issue_reference_keeps_its_needs_grooming_default(self) -> None:
        """The backend architecture makes non-GitHub work-item status backend-owned.

        String references cannot key the numeric GitHub status map, so the configured
        backend's stored status contract applies instead. See ``backlog_core/ARCHITECTURE.md``
        under "Storage Ownership and File Cache" and ``backend_types.py``'s
        ``issue_id_type`` capability contract.
        """
        assert operations._item_derived_status(_item("bd-a3f8", status=""), {}, status_live=False) == "needs-grooming"

    def test_a_bare_cached_lifecycle_value_is_normalized_to_its_label_form(self) -> None:
        """A numeric-issue item's cache may hold the bare lifecycle value, not the label.

        ``_apply_issue_status_labels`` writes ``metadata.status = "in-progress"``
        (bare) for string-ID backends, and legacy/pre-label records can carry the
        same bare form. A live answer and the documented ``--status`` filter both
        use the ``status:*`` labeled form, so the cached value must be normalized
        before it is compared — not returned verbatim (P1, PR #3552 review).
        """
        bare_item = _item("#42", status="in-progress")

        assert operations._item_derived_status(bare_item, {}, status_live=False) == "status:in-progress"

    def test_a_bare_cached_value_with_no_label_equivalent_is_unchanged(self) -> None:
        """ "open"/"done"/"closed" have no ``status:*`` label counterpart — leave them bare."""
        assert operations._item_derived_status(_item("#42", status="open"), {}, status_live=False) == "open"

    def test_a_bare_cached_needs_grooming_value_is_not_promoted_to_the_label_form(self) -> None:
        """Reproduction (P1, PR #3552 Codex review): unlike every other bare
        lifecycle value, ``"needs-grooming"`` is itself the canonical,
        documented ``--status`` filter token (see
        ``test_a_missing_key_in_a_live_map_is_still_needs_grooming`` above and
        the ``list_items`` docstring) — not ``"status:needs-grooming"``.
        Promoting a genuinely cached bare ``"needs-grooming"`` to its label
        form would make ``--status needs-grooming`` stop matching an item
        that is, in fact, awaiting grooming. Before the fix this returned
        ``"status:needs-grooming"``.
        """
        needs_grooming_item = _item("#42", status="needs-grooming")

        assert operations._item_derived_status(needs_grooming_item, {}, status_live=False) == "needs-grooming"


class TestStatusFilterWithALiveAnswer:
    """The bare documented ``--status needs-grooming`` filter must match every
    issue that needs grooming under a live answer — both "no status label
    observed" (missing map key) and "explicitly labeled status:needs-grooming"."""

    def test_an_explicitly_labeled_issue_matches_the_bare_filter(self, mocker: MockerFixture) -> None:
        """Reproduction: a live GraphQL answer for issue #42 carries the literal
        ``status:needs-grooming`` label, while issue #43's live answer carries an
        unrelated label. ``list_items(status="needs-grooming")`` — the documented
        bare filter token — must match #42 and must not match #43. Before the
        fix, #42's derived status was the labeled ``"status:needs-grooming"``,
        which never equals the bare filter, so #42 was silently excluded.
        """
        _patch_backend(mocker, [_item("#42", status="status:needs-grooming"), _item("#43", title="Another")])
        mocker.patch.object(
            operations,
            "batch_fetch_statuses",
            return_value={
                42: IssueStatus(status="status:needs-grooming", milestone=""),
                43: IssueStatus(status="status:in-progress", milestone=""),
            },
        )

        result = operations.list_items(status="needs-grooming", output=Output())

        assert result["count"] == 1

    def test_a_missing_status_label_still_matches_the_bare_filter(self, mocker: MockerFixture) -> None:
        """Unchanged behavior: an issue the live query answered for, but with no
        status label at all, still matches the bare ``needs-grooming`` filter.
        """
        _patch_backend(mocker, [_item("#42")])
        mocker.patch.object(operations, "batch_fetch_statuses", return_value={})

        result = operations.list_items(status="needs-grooming", output=Output())

        assert result["count"] == 1


class TestRenderedStatusWithALiveAnswer:
    """The render path must agree with the filter path on the live side too.

    ``_item_derived_status`` normalizes a live ``status:needs-grooming`` map
    entry to bare ``"needs-grooming"`` for filter matching (see
    ``TestStatusFilterWithALiveAnswer`` above). ``_build_list_entry`` must
    normalize the same live entry the same way when rendering it, or a
    caller combining the documented ``status="needs-grooming"`` filter with
    the supported post-render ``filter_by_key={"status": "needs-grooming"}``
    would have the item selected by the first and dropped by the second.
    """

    def test_a_live_labeled_needs_grooming_entry_renders_bare(self, mocker: MockerFixture) -> None:
        """Reproduction (P2, PR #3552 Codex review, third finding): a live
        status map entry carrying the literal ``"status:needs-grooming"``
        label rendered verbatim as ``"status:needs-grooming"`` even though
        ``_item_derived_status`` already normalizes the same value to bare
        ``"needs-grooming"`` for filter-matching purposes. Before the fix
        this rendered ``"status:needs-grooming"``.
        """
        _patch_backend(mocker, [_item("#42", status="status:needs-grooming")])
        mocker.patch.object(
            operations,
            "batch_fetch_statuses",
            return_value={42: IssueStatus(status="status:needs-grooming", milestone="")},
        )

        result = operations.list_items(status="needs-grooming", output=Output())

        assert _statuses(result) == ["needs-grooming"]

    def test_a_live_labeled_needs_grooming_entry_survives_the_post_render_filter(self, mocker: MockerFixture) -> None:
        """The rendered entry must agree with the documented post-render filter that selects it."""
        _patch_backend(mocker, [_item("#42", status="status:needs-grooming")])
        mocker.patch.object(
            operations,
            "batch_fetch_statuses",
            return_value={42: IssueStatus(status="status:needs-grooming", milestone="")},
        )

        result = operations.list_items(
            status="needs-grooming", output=Output(), filter_by_key={"status": "needs-grooming"}
        )

        assert result["count"] == 1


class TestStatusFilterUnderARefusal:
    """The filter has to answer from the cache, not from a fabricated default."""

    def test_the_real_status_still_matches(self, mocker: MockerFixture) -> None:
        _patch_backend(mocker, [_item("#42"), _item("#43", title="Another")])
        _refuse(mocker)

        result = operations.list_items(status="status:in-progress", output=Output())

        assert result["count"] == 2

    def test_needs_grooming_no_longer_matches_everything(self, mocker: MockerFixture) -> None:
        _patch_backend(mocker, [_item("#42"), _item("#43", title="Another")])
        _refuse(mocker)

        result = operations.list_items(status="needs-grooming", output=Output())

        assert result["count"] == 0

    def test_an_item_with_no_cached_status_matches_no_filter(self, mocker: MockerFixture) -> None:
        _patch_backend(mocker, [_item("#42", status="")])
        _refuse(mocker)

        assert operations.list_items(status="needs-grooming", output=Output())["count"] == 0
        assert operations.list_items(status="status:in-progress", output=Output())["count"] == 0

    def test_an_unfiltered_listing_still_returns_every_item(self, mocker: MockerFixture) -> None:
        """The refusal degrades the answer, it does not shrink the backlog."""
        _patch_backend(mocker, [_item("#42"), _item("#43", title="Another")])
        _refuse(mocker)

        assert operations.list_items(output=Output())["count"] == 2

    def test_a_bare_cached_status_matches_the_labeled_filter(self, mocker: MockerFixture) -> None:
        """Reproduction (P1, PR #3552 Codex review): a cached GitHub item whose
        ``item.status`` is the bare lifecycle value ``"in-progress"`` — not the
        ``status:in-progress`` label a live answer would have produced — must
        still be returned by ``list_items(status="status:in-progress")`` once
        GraphQL is refused and the cache is all that is left to filter on.
        Before the fix this returned ``count: 0``.
        """
        _patch_backend(mocker, [_item("#42", status="in-progress")])
        _refuse(mocker)

        result = operations.list_items(status="status:in-progress", output=Output())

        assert result["count"] == 1

    def test_a_cached_needs_grooming_item_still_matches_the_bare_filter(self, mocker: MockerFixture) -> None:
        """Reproduction (P1, PR #3552 Codex review, second finding): a cached
        GitHub item whose ``item.status`` is the genuine bare lifecycle value
        ``"needs-grooming"`` must still be returned by
        ``list_items(status="needs-grooming")`` — the documented bare form —
        once GraphQL is refused and the cache is all that is left to filter
        on. Before the fix, ``normalize_cached_github_status`` promoted the
        cached value to ``"status:needs-grooming"``, which does not equal the
        bare ``"needs-grooming"`` filter, so this item was silently dropped
        even though it was genuinely awaiting grooming.
        """
        _patch_backend(mocker, [_item("#42", status="needs-grooming")])
        _refuse(mocker)

        result = operations.list_items(status="needs-grooming", output=Output())

        assert result["count"] == 1


class TestRenderedStatusUnderARefusal:
    """A filter that matched on the cached status must render that same status."""

    def test_the_cached_status_is_rendered(self, mocker: MockerFixture) -> None:
        _patch_backend(mocker, [_item("#42")])
        _refuse(mocker)

        assert _statuses(operations.list_items(output=Output())) == ["status:in-progress"]

    def test_a_live_miss_still_renders_blank(self, mocker: MockerFixture) -> None:
        """The query ran and named no label for this issue, so blank is the honest render."""
        _patch_backend(mocker, [_item("#42")])
        mocker.patch.object(operations, "batch_fetch_statuses", return_value={})

        assert _statuses(operations.list_items(output=Output())) == [""]

    def test_the_warning_names_the_cause_and_the_consequence(self, mocker: MockerFixture) -> None:
        _patch_backend(mocker, [_item("#42")])
        _refuse(mocker)

        raw = operations.list_items(output=Output()).get("warnings", [])
        warnings = [str(entry) for entry in raw] if isinstance(raw, list) else []

        assert any(_REFUSAL_MESSAGE in w for w in warnings)
        assert any("local cache" in w and "under-report" in w for w in warnings)

    def test_a_bare_cached_status_is_rendered_in_labeled_form(self, mocker: MockerFixture) -> None:
        """Reproduction (P2, PR #3552 Codex review): the render path bypassed
        ``normalize_cached_github_status``, so a numeric-issue item whose
        cache held the bare lifecycle value ``"in-progress"`` (not the
        ``status:in-progress`` label a live answer would have produced)
        rendered ``status: "in-progress"`` even though
        ``status="status:in-progress"`` now selects it (see
        ``TestStatusFilterUnderARefusal.test_a_bare_cached_status_matches_the_labeled_filter``).
        A caller piping this output into ``filter_by_key={"status":
        "status:in-progress"}`` would then drop the very item the primary
        filter just matched. Before the fix this rendered ``"in-progress"``.
        """
        _patch_backend(mocker, [_item("#42", status="in-progress")])
        _refuse(mocker)

        result = operations.list_items(output=Output())

        assert _statuses(result) == ["status:in-progress"]

    def test_a_bare_cached_status_survives_the_documented_post_render_filter(self, mocker: MockerFixture) -> None:
        """The rendered entry must agree with the filter that is documented to select it."""
        _patch_backend(mocker, [_item("#42", status="in-progress")])
        _refuse(mocker)

        result = operations.list_items(output=Output(), filter_by_key={"status": "status:in-progress"})

        assert result["count"] == 1


class TestBackendsWithoutABatchStatusFetch:
    """A backend that never queries is in the same position as one that was refused."""

    def test_a_numeric_issue_falls_back_to_the_backend_owned_status(self, mocker: MockerFixture) -> None:
        """No query ran, so the backend-owned field is authoritative — not "needs-grooming"."""
        _patch_backend(mocker, [_item("#42")], batch=False)

        assert operations.list_items(status="needs-grooming", output=Output())["count"] == 0
        assert operations.list_items(status="status:in-progress", output=Output())["count"] == 1

    def test_no_refusal_warning_is_emitted(self, mocker: MockerFixture) -> None:
        """Nothing degraded: this backend has no live statuses to lose."""
        _patch_backend(mocker, [_item("#42")], batch=False)

        raw = operations.list_items(output=Output()).get("warnings", [])
        warnings = [str(entry) for entry in raw] if isinstance(raw, list) else []

        assert not any("Live status unavailable" in w for w in warnings)

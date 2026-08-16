"""GitHub backend work-item reference healing — regression tests.

Tests: ``_GitHubReconciliation.load_records`` (via the public
       ``GitHubBackend.list_work_items``/``get_work_item``/``put_work_item``
       surface) heals a stale on-disk ``BacklogItem.reference=""`` from
       ``metadata.issue`` instead of propagating it forever, and no longer
       collides two distinct items under the shared empty-string key.
How: Inject a ``FileCache`` rooted at ``tmp_path`` into ``GitHubBackend`` and
     write raw legacy snapshot files directly through
     ``FileCache._save_work_item_snapshot`` — reproducing the on-disk shape
     of an item persisted before ``reference`` was populated consistently,
     without requiring live GitHub network access.
Why: Backlog item #2900 — ``backlog groom``/``backlog resolve`` raised
     ``BacklogError: Item has no backend reference`` for a real, valid,
     open GitHub-backed item (#983) whose local cache snapshot carried
     ``reference=""`` while ``metadata.issue == "#983"``. ``view``/`update
     --status`` worked because those code paths never read
     ``item.reference``; ``groom``/``resolve`` do, and the reconciliation
     compose/checkpoint functions blindly propagated the already-empty
     ``local.reference`` on every subsequent sync, so the record never
     self-healed. Root cause: ``_GitHubReconciliation.load_records`` keyed
     its snapshot dict by the *unhealed* ``item.reference`` field, which
     both surfaced the crash (an item found by title/issue still carried an
     empty ``.reference``) and could silently drop distinct legacy items
     that collided under the shared ``""`` key.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from backlog_core import operations as ops
from backlog_core.backend_protocol import reset_config, set_config
from backlog_core.backend_types import BacklogConfig
from backlog_core.backends.github_backend import GitHubBackend
from backlog_core.file_cache import FileCache
from backlog_core.models import BacklogItem, BacklogItemMetadata, ReconcileResult

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def _stale_legacy_item(*, title: str, issue: str) -> BacklogItem:
    """Build a ``BacklogItem`` shaped like a pre-healing on-disk record.

    Mirrors a record written before ``reference`` was populated
    consistently: ``metadata.issue`` is set but ``reference`` was never
    backfilled, matching the shape found in backlog item #983's actual
    cache file (see docstring above).

    Returns:
        A ``BacklogItem`` with ``reference=""`` and ``metadata.issue`` set.
    """
    return BacklogItem(
        title=title,
        metadata=BacklogItemMetadata(source="test", added="2026-01-01", priority="P1", item_type="Bug", issue=issue),
    )


def _backend_with_stale_snapshot(tmp_path: Path, *, key: str, title: str, issue: str) -> GitHubBackend:
    """Return a GitHubBackend whose cache holds one stale legacy snapshot.

    Returns:
        A GitHubBackend backed by an isolated FileCache pre-seeded with a
        raw legacy snapshot (bypassing ``put_work_item``'s normalization,
        so the write matches how the real stale record on disk was found).
    """
    backend = GitHubBackend(cache=FileCache(tmp_path))
    backend._cache._save_work_item_snapshot(key, _stale_legacy_item(title=title, issue=issue))
    return backend


class TestListWorkItemsHealsStaleReference:
    """list_work_items()/get_work_item() heal an empty on-disk reference."""

    def test_list_work_items_heals_reference_from_issue(self, tmp_path: Path) -> None:
        """A snapshot with reference='' and issue='#983' loads with reference='#983'."""
        backend = _backend_with_stale_snapshot(tmp_path, key="#983", title="Stale item", issue="#983")

        items = backend.list_work_items()

        assert len(items) == 1
        assert items[0].reference == "#983"
        assert items[0].issue == "#983"

    def test_get_work_item_finds_item_by_healed_reference(self, tmp_path: Path) -> None:
        """get_work_item(reference) succeeds once reference is healed to match issue.

        This is the exact lookup ``_apply_groomed_update``/``resolve_item``
        depend on: they read ``item.reference`` from a ``list_work_items()``
        result, then pass it straight to ``get_work_item``/
        ``update_item_metadata``. Before the fix, ``item.reference`` from
        ``list_work_items()`` was ``""`` and this lookup was never
        exercised at all — the crash occurred earlier at the ``not
        item.reference`` guard.
        """
        backend = _backend_with_stale_snapshot(tmp_path, key="#983", title="Stale item", issue="#983")

        listed = backend.list_work_items()[0]
        found = backend.get_work_item(listed.reference)

        assert found.title == "Stale item"
        assert found.reference == "#983"

    def test_put_work_item_after_healing_persists_the_repaired_reference(self, tmp_path: Path) -> None:
        """Writing back a healed item durably repairs the on-disk reference.

        Reproduces the groom/resolve write path: read the (now-healed) item,
        mutate it, and persist through put_work_item. The repaired
        reference must round-trip through a fresh load, not just survive in
        memory for the current call.
        """
        backend = _backend_with_stale_snapshot(tmp_path, key="#983", title="Stale item", issue="#983")

        item = backend.list_work_items()[0]
        backend.put_work_item(item.model_copy(update={"description": "groomed"}))
        # A second, independent backend instance over the same cache root
        # proves the repair reached durable storage, not just this process's
        # in-memory pending-mutation queue.
        reloaded_backend = GitHubBackend(cache=FileCache(tmp_path))

        reloaded = reloaded_backend.get_work_item("#983")

        assert reloaded.reference == "#983"
        assert reloaded.description == "groomed"


class TestDistinctStaleSnapshotsDoNotCollide:
    """Two legacy items sharing an empty reference must not collapse into one."""

    def test_two_snapshots_with_empty_reference_are_both_returned(self, tmp_path: Path) -> None:
        """Keying by the unhealed empty-string reference silently drops one item.

        Before healing at the read boundary, ``load_records()`` built its
        dict as ``{item.reference: record for ...}`` — two on-disk items
        that both carried ``reference=""`` collapsed onto the same ``""``
        key, and only the last one loaded (glob order) survived. Healing
        each item's key from its own ``metadata.issue`` before insertion
        keeps them distinct.
        """
        backend = GitHubBackend(cache=FileCache(tmp_path))
        backend._cache._save_work_item_snapshot("#100", _stale_legacy_item(title="First stale item", issue="#100"))
        backend._cache._save_work_item_snapshot("#200", _stale_legacy_item(title="Second stale item", issue="#200"))

        items = backend.list_work_items()

        titles = {item.title for item in items}
        references = {item.reference for item in items}
        assert titles == {"First stale item", "Second stale item"}
        assert references == {"#100", "#200"}


class TestPutWorkItemNormalization:
    """put_work_item's existing reference-from-issue fallback is unchanged."""

    def test_put_work_item_derives_reference_from_issue_when_unset(self, tmp_path: Path) -> None:
        """An item passed to put_work_item with reference='' still normalizes from issue.

        Regression guard for the shared ``_stable_reference`` helper: the
        fallback that already existed inline in ``put_work_item`` must keep
        behaving identically now that ``load_records`` reuses it.
        """
        backend = GitHubBackend(cache=FileCache(tmp_path))
        item = BacklogItem(title="New item", issue="#555")
        assert item.reference == ""

        backend.put_work_item(item)
        found = backend.get_work_item("#555")

        assert found.reference == "#555"


class TestGroomAndResolveOperationsNoLongerRaise:
    """operations.groom_item/resolve_item no longer crash on a stale legacy record.

    Exercises the two public functions named in the original bug report
    end-to-end through the operations layer, against the exact backend
    class (``GitHubBackend``) and on-disk shape (a legacy snapshot with
    ``reference=""``) that reproduced the defect. Only the two GitHub
    network boundary methods (``check_open_prs_for_issue``,
    ``resolve_github_issue``) are mocked; reference resolution, item
    lookup, and the local cache write-back all run for real.
    """

    def test_resolve_item_succeeds_on_a_stale_legacy_record(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """resolve_item on a stale-reference item returns resolved=True, not BacklogError.

        Before the fix this raised ``BacklogError: Item has no backend
        reference`` at the ``reference = item.reference; if not reference:
        raise`` guard in ``resolve_item`` — the same defect ``groom_item``
        hit, sourced from the same unhealed ``list_work_items()`` read.
        """
        backend = _backend_with_stale_snapshot(tmp_path, key="#2900", title="Stale bug item", issue="#2900")
        mocker.patch.object(backend, "check_open_prs_for_issue", return_value=[])
        mocker.patch.object(backend, "resolve_github_issue")
        set_config(BacklogConfig(backend=backend))

        try:
            result = ops.resolve_item(selector="#2900", summary="Fixed the reference-healing root cause")
        finally:
            reset_config()

        assert result["resolved"] is True
        assert result["summary"] == "Fixed the reference-healing root cause"

    def test_groom_item_succeeds_on_a_stale_legacy_record(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """groom_item on a stale-reference item writes the section, not BacklogError.

        Reproduces the exact reported repro command:
        ``backlog groom --selector "#983" --section "..." --content "..."``
        against an item whose cache snapshot carries ``reference=""``.
        """
        backend = _backend_with_stale_snapshot(tmp_path, key="#983", title="Stale docs item", issue="#983")
        # _reconcile_groomed_item posts the write-back through backend.reconcile(),
        # which reaches live GitHub via the provider snapshot/patch boundary —
        # mock it at that boundary rather than skip reconciliation.
        mocker.patch.object(backend, "reconcile", return_value=ReconcileResult())
        set_config(BacklogConfig(backend=backend))

        try:
            result = ops.groom_item(selector="#983", section="RT-ICA", content="verification content")
        finally:
            reset_config()

        assert result["groomed_updated"] is True

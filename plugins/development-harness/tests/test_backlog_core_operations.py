"""Tests for backlog_core/operations.py public API functions.

Covers add_item, list_items, view_item, close_item, and resolve_item.
All GitHub calls are mocked at the boundary.  File-system isolation is provided
by an autouse fixture that redirects BACKLOG_DIR to tmp_path.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import MagicMock

import backlog_core.models as _bc_models
import backlog_core.operations as ops
import pytest
from backlog_core.backends.memory_backend import InMemoryBackend
from backlog_core.github_sync import render_issue_body
from backlog_core.models import (
    BacklogConfig,
    BacklogItem,
    BacklogItemMetadata,
    DuplicateItemError,
    Entry,
    GroomedSectionMetadata,
    IssueStatus,
    ItemNotFoundError,
    Output,
    ProviderItem,
    ProviderSnapshot,
    PullRequestRef,
    ReconcileRequest,
    ReconcileResult,
    ReconcileScope,
    Section,
    SectionEntryMetadata,
    ValidationError,
    ViewItemResult,
)
from backlog_core.operations import (
    add_item,
    close_item,
    list_items,
    refresh_local_cache_from_github,
    resolve_item,
    view_item,
)
from backlog_core.reconciliation import LogicalCacheRecord, ReconcilePlan, reconcile_backlog, synchronized_fingerprint

if TYPE_CHECKING:
    from collections.abc import Callable

    from pytest_mock import MockerFixture


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MINIMAL_FRONTMATTER = """\
---
name: {title}
description: A test item
metadata:
  priority: {priority}
  status: open
  source: test
  added: '2026-01-01'
  type: Feature
  topic: {topic}
  issue: '{issue}'
---
"""


def _seed_items(items: list[BacklogItem]) -> None:
    from backlog_core.backend_protocol import get_config

    for item in items:
        get_config().backend.put_work_item(item)


def _stored_item(reference: Path | str) -> BacklogItem:
    from backlog_core.backend_protocol import get_config

    target = Path(reference)
    return next(
        item
        for item in get_config().backend.list_work_items()
        if item.reference == str(reference) or (item.reference and Path(item.reference).stem == target.stem)
    )


def _render_item(reference: Path | str) -> str:
    return _stored_item(reference).model_dump_json()


def _provider_plan(local: BacklogItem, provider: ProviderItem) -> ReconcilePlan:
    return reconcile_backlog(
        [LogicalCacheRecord(key=local.reference, item=local)],
        ProviderSnapshot(items=[provider], sync_started_at="2026-08-13T00:00:00Z", pages_fetched=1),
        ReconcileRequest(scope=ReconcileScope.LINKED, references=[provider.reference]),
    )


def _write_item(
    backlog_dir: Path,
    *,
    title: str = "Test Item",
    priority: str = "P1",
    topic: str = "test-item",
    issue: str = "",
    skip: bool = False,
    extra_body: str = "",
) -> Path:
    slug = topic
    filename = f"{priority.lower()}-{slug}.md"
    filepath = backlog_dir / filename
    status = "done" if skip else "open"
    _seed_items([
        BacklogItem(
            title=title,
            description="A test item" + (f"\n\n{extra_body}" if extra_body else ""),
            reference=str(filepath),
            file_path=str(filepath),
            metadata=BacklogItemMetadata(
                source="test", added="2026-01-01", priority=priority, status=status, issue=issue, topic=topic
            ),
        )
    ])
    return filepath


def _write_item_yaml(
    backlog_dir: Path,
    *,
    title: str = "Test Item",
    priority: str = "P1",
    topic: str = "test-item",
    issue: str = "",
    skip: bool = False,
) -> Path:
    slug = topic
    filename = f"{priority.lower()}-{slug}.yaml"
    filepath = backlog_dir / filename
    status = "done" if skip else "open"
    metadata = BacklogItemMetadata(
        source="test", added="2026-01-01", priority=priority, status=status, issue=issue, topic=topic
    )
    item = BacklogItem(
        title=title, description="A test item", metadata=metadata, reference=str(filepath), file_path=str(filepath)
    )
    _seed_items([item])
    return filepath


# ---------------------------------------------------------------------------
# Autouse fixture: redirect BACKLOG_DIR in all consuming modules
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolate_backlog_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Redirect BACKLOG_DIR to tmp_path for test isolation.

    Tests: File-system isolation for all backlog operations.
    How: Sets DH_STATE_HOME so dh_paths resolves under tmp_path, then patches
         backlog_core.models.BACKLOG_DIR. parsing.py and operations.py access
         the path via _models.BACKLOG_DIR, so patching models is sufficient.
    Why: Prevents tests from reading/writing the real backlog directory.
         After T03, parsing.py and operations.py no longer export BACKLOG_DIR
         at module level — they delegate to backlog_core.models.
    """
    import dh_paths

    monkeypatch.setenv("DH_STATE_HOME", str(tmp_path / "dh_state"))

    fake_project_root = tmp_path / "project"
    fake_project_root.mkdir(parents=True, exist_ok=True)

    fake_dir = dh_paths.backlog_dir(project_root=fake_project_root)
    fake_dir.mkdir(parents=True, exist_ok=True)

    existing = _bc_models._config
    monkeypatch.setattr(
        _bc_models,
        "_config",
        BacklogConfig(
            repo_root=fake_project_root,
            backlog_dir=fake_dir,
            default_repo=existing.default_repo if existing is not None else "",
        ),
    )

    # Prevent tests from creating real GitHub issues.
    # Both try_get_github and get_github must be patched: _create_issue_and_update_item
    # now calls try_get_github, but other code paths call get_github directly.
    monkeypatch.setattr(ops, "try_get_github", lambda repo="": None)
    monkeypatch.setattr(
        ops,
        "get_github",
        lambda repo="", timeout=15: (_ for _ in ()).throw(RuntimeError("get_github called in test — patch missing")),
    )


# ---------------------------------------------------------------------------
# add_item
# ---------------------------------------------------------------------------


class TestAddItemCreatesLocalFile:
    """add_item writes a per-item file with correct frontmatter fields."""

    def test_add_item_creates_file_in_backlog_dir(self, mocker: MockerFixture) -> None:
        """Verify add_item creates exactly one .yaml file in BACKLOG_DIR.

        Tests: add_item file creation (T04: new items use .yaml extension).
        How: Call add_item with GitHub mocked; check one .yaml file exists.
        Why: The primary side-effect of add_item is writing a local cache file.
        """
        mocker.patch("backlog_core.operations.try_get_github", return_value=None)

        result = add_item(title="My New Feature", description="Does something useful", priority="P1")

        assert result["file_path"] == "p1-my-new-feature"
        assert _stored_item("p1-my-new-feature").title == "My New Feature"

    def test_add_item_returns_title_priority_file_path(self, mocker: MockerFixture) -> None:
        """Verify add_item return dict contains title, priority, and file_path keys.

        Tests: add_item return value shape.
        How: Call add_item and inspect the returned dict.
        Why: Callers depend on these fields to display confirmation output.
        """
        mocker.patch("backlog_core.operations.try_get_github", return_value=None)

        result = add_item(title="Return Shape Check", description="desc", priority="P2")

        assert result["title"] == "Return Shape Check"
        assert result["priority"] == "P2"
        assert "file_path" in result

    def test_add_item_frontmatter_contains_title(self, mocker: MockerFixture) -> None:
        """Verify the written file frontmatter includes the item title.

        Tests: add_item frontmatter content.
        How: Call add_item and read back the written file.
        Why: Frontmatter fields are parsed by downstream tools — must be accurate.
        """
        mocker.patch("backlog_core.operations.try_get_github", return_value=None)

        result = add_item(title="Frontmatter Title Test", description="desc", priority="P1")

        assert _stored_item(str(result["file_path"])).title == "Frontmatter Title Test"

    def test_add_item_always_calls_github(self, mocker: MockerFixture) -> None:
        """Verify add_item always attempts GitHub issue creation via try_get_github.

        Tests: add_item always-create-issue invariant.
        How: Patch try_get_github returning None; assert it was called.
        Why: GitHub Issues is the source of truth — every item must have an issue.
        """
        mock_try_gh = mocker.patch("backlog_core.operations.try_get_github", return_value=None)

        add_item(title="Local Only Item", description="desc", priority="P2")

        mock_try_gh.assert_called_once()

    def test_add_item_calls_github_and_returns_item_ref(self, mocker: MockerFixture) -> None:
        """Verify add_item calls try_get_github and returns item_ref on success.

        Tests: add_item backend-first integration path.
        How: Patch try_get_github to return a mock repo, verify item_ref is returned.
        Why: Backend-first design requires the backend to be contacted before local file write.
        """
        mock_repo = mocker.Mock()
        mocker.patch("backlog_core.operations.try_get_github", return_value=mock_repo)
        mocker.patch("backlog_core.operations.create_issue_for_item", return_value=42)

        result = add_item(title="GH First Item", description="desc", priority="P1")

        assert result.get("item_ref") == "#42"

    def test_add_item_returns_item_ref_from_github(self, mocker: MockerFixture) -> None:
        """Verify add_item return dict includes item_ref when backend issue is created.

        Tests: add_item item_ref in return value for integer-ID backends.
        How: Mock create_issue_for_item to return 99; expect item_ref == '#99'.
        Why: item_ref is the canonical selector string used by all downstream callers.
        """
        mock_repo = mocker.Mock()
        mocker.patch("backlog_core.operations.try_get_github", return_value=mock_repo)
        mocker.patch("backlog_core.operations.create_issue_for_item", return_value=99)

        result = add_item(title="Issue Num Item", description="desc", priority="P1")

        assert result["item_ref"] == "#99"

    def test_add_item_returns_item_ref_in_hash_n_format(self, mocker: MockerFixture) -> None:
        """Verify add_item return dict includes item_ref in '#N' string format.

        Tests: add_item item_ref field — canonical backlog identifier format.
        How: Mock create_issue_for_item to return 1632; assert item_ref == '#1632'.
        Why: Workflow docs and tool selectors use '#N' format; backlog_add must
             expose item_ref so callers have a ready-to-use selector string without
             manual formatting.
        """
        mock_repo = mocker.Mock()
        mocker.patch("backlog_core.operations.try_get_github", return_value=mock_repo)
        mocker.patch("backlog_core.operations.create_issue_for_item", return_value=1632)

        result = add_item(title="Item Ref Format Check", description="desc", priority="P1")

        assert result["item_ref"] == "#1632"

    def test_add_item_item_ref_absent_when_no_github_issue(self, mocker: MockerFixture) -> None:
        """Verify item_ref is absent from result when GitHub issue creation fails.

        Tests: add_item item_ref absent on no-issue path.
        How: Mock try_get_github to return None (no GitHub available).
        Why: item_ref must not be present with a falsy value — absence is the
             correct signal that no issue was created.
        """
        mocker.patch("backlog_core.operations.try_get_github", return_value=None)

        result = add_item(title="Local Only No Ref", description="desc", priority="P2")

        assert "item_ref" not in result


class TestAddItemValidatesPriorityAndType:
    """add_item() rejects invalid priority/type at the ingress boundary.

    Regression coverage for the bug where add_item() passed priority/type_
    straight into BacklogItem(...) with no acceptance check — an invalid
    value like "P3" silently persisted to a real file and backend issue
    instead of being rejected.
    """

    def test_add_item_rejects_invalid_priority_raises_validation_error(self, mocker: MockerFixture) -> None:
        """Verify add_item raises ValidationError for a priority outside the canonical set.

        Tests: add_item ingress validation — invalid priority.
        How: Call add_item with priority="P3" (not a real priority level).
        Why: P3 previously passed straight through to BacklogItem with no rejection.
        """
        mocker.patch("backlog_core.operations.try_get_github", return_value=None)

        with pytest.raises(ValidationError, match="Invalid priority"):
            add_item(title="Bad Priority Item", description="desc", priority="P3")

    def test_add_item_rejects_invalid_priority_creates_no_file_or_issue(self, mocker: MockerFixture) -> None:
        """Verify a rejected priority leaves no file and never contacts the backend.

        Tests: add_item ingress validation — no side effects on rejection.
        How: Call add_item with an invalid priority; assert zero files written
             and try_get_github was never called.
        Why: Rejecting invalid input after partial side effects (file write,
             issue creation) would be worse than not validating at all.
        """
        mock_try_gh = mocker.patch("backlog_core.operations.try_get_github", return_value=None)

        fake_dir: Path = _bc_models.get_backlog_dir()
        with pytest.raises(ValidationError):
            add_item(title="Bad Priority No Side Effects", description="desc", priority="P3")

        assert list(fake_dir.glob("*.yaml")) == []
        mock_try_gh.assert_not_called()

    def test_add_item_accepts_idea_prefix_case_insensitive(self, mocker: MockerFixture) -> None:
        """Verify add_item accepts a case-insensitive 'idea*' priority variant.

        Tests: add_item ingress validation — idea* convenience acceptance.
        How: Call add_item with priority="IDEA"; expect no exception raised.
        Why: BacklogItemMetadata._validate_priority normalises any case-insensitive
             idea* value to "Ideas" — the ingress gate must not reject what the
             model itself accepts and normalises.
        """
        mocker.patch("backlog_core.operations.try_get_github", return_value=None)

        result = add_item(title="Idea Prefix Item", description="desc", priority="IDEA")

        assert result["title"] == "Idea Prefix Item"

    def test_add_item_rejects_invalid_type_raises_validation_error(self, mocker: MockerFixture) -> None:
        """Verify add_item raises ValidationError for a type outside the canonical set/aliases.

        Tests: add_item ingress validation — invalid type.
        How: Call add_item with type_="Enhancement" (not a recognized type or alias).
        Why: Unrecognized types previously passed straight through with no rejection.
        """
        mocker.patch("backlog_core.operations.try_get_github", return_value=None)

        with pytest.raises(ValidationError, match="Invalid type"):
            add_item(title="Bad Type Item", description="desc", priority="P1", type_="Enhancement")

    def test_add_item_rejects_invalid_type_creates_no_file_or_issue(self, mocker: MockerFixture) -> None:
        """Verify a rejected type leaves no file and never contacts the backend.

        Tests: add_item ingress validation — no side effects on rejection.
        How: Call add_item with an invalid type; assert zero files written
             and try_get_github was never called.
        Why: Same no-partial-side-effect guarantee as the priority rejection path.
        """
        mock_try_gh = mocker.patch("backlog_core.operations.try_get_github", return_value=None)

        fake_dir: Path = _bc_models.get_backlog_dir()
        with pytest.raises(ValidationError):
            add_item(title="Bad Type No Side Effects", description="desc", priority="P1", type_="Enhancement")

        assert list(fake_dir.glob("*.yaml")) == []
        mock_try_gh.assert_not_called()

    def test_add_item_accepts_known_type_alias(self, mocker: MockerFixture) -> None:
        """Verify add_item accepts a known type alias (Documentation -> Docs).

        Tests: add_item ingress validation — type alias acceptance.
        How: Call add_item with type_="Documentation"; expect no exception raised.
        Why: BacklogItemMetadata._validate_item_type normalises "documentation" to
             "Docs" — the ingress gate must not reject a value the model accepts.
        """
        mocker.patch("backlog_core.operations.try_get_github", return_value=None)

        result = add_item(title="Alias Type Item", description="desc", priority="P1", type_="Documentation")

        assert result["title"] == "Alias Type Item"


class TestAddItemBeadsBackend:
    """add_item dispatches to create_beads_issue_for_item for string-ID backends."""

    def test_add_item_beads_backend_stores_nanoid_as_issue_ref(self, mocker: MockerFixture) -> None:
        """Verify add_item stores the beads nanoid as item_ref when backend is beads.

        Tests: _try_create_backend_issue_ref beads dispatch path.
        How: Patch get_config to return a BeadsBackend whose create_beads_issue_for_item
             returns a nanoid; verify the written item's issue field holds the nanoid.
        Why: This is the root cause of the reported bug — without this path, beads items
             are created with no issue reference and cannot be found via bd show.
        """

        from backlog_core.backend_protocol import reset_config, set_config
        from backlog_core.backend_types import BacklogConfig
        from backlog_core.backends.bd_runner import BdRunner
        from backlog_core.backends.beads_backend import BeadsBackend

        mock_runner = MagicMock(spec=BdRunner)
        mock_runner.is_available.return_value = True
        beads_backend = BeadsBackend(runner=mock_runner)
        mocker.patch.object(beads_backend, "create_beads_issue_for_item", return_value="bd-a3f8")
        set_config(BacklogConfig(backend=beads_backend))

        try:
            result = add_item(title="Beads Backend Feature", description="desc", priority="P2")
        finally:
            reset_config()

        assert result.get("item_ref") == "bd-a3f8"

    def test_add_item_beads_backend_record_contains_nanoid_issue_reference(self, mocker: MockerFixture) -> None:
        """Verify the provider-owned record stores the Beads nanoid after add_item.

        Tests: provider record persistence of the Beads nanoid.
        How: Capture the work item passed to the backend and verify its issue reference.
        Why: The issue reference is the selector used by downstream operations.
        """

        from backlog_core.backend_protocol import reset_config, set_config
        from backlog_core.backend_types import BacklogConfig
        from backlog_core.backends.bd_runner import BdRunner
        from backlog_core.backends.beads_backend import BeadsBackend

        mock_runner = MagicMock(spec=BdRunner)
        mock_runner.is_available.return_value = True
        beads_backend = BeadsBackend(runner=mock_runner)
        mocker.patch.object(beads_backend, "create_beads_issue_for_item", return_value="bd-x9y2")
        stored: list[BacklogItem] = []
        mocker.patch.object(beads_backend, "put_work_item", side_effect=stored.append)
        set_config(BacklogConfig(backend=beads_backend))

        try:
            result = add_item(title="Beads Issue Field Test", description="desc", priority="P1")
        finally:
            reset_config()

        assert result["file_path"] == "bd-x9y2"
        assert stored[0].issue == "bd-x9y2"

    def test_add_item_beads_backend_raises_when_native_creation_is_unavailable(self, mocker: MockerFixture) -> None:
        """Verify add_item reports unavailable native Beads creation explicitly.

        Tests: explicit failure when the configured provider cannot create an item.
        How: Return no native reference and assert ContentUnavailableError propagates.
        Why: A configured Beads backend cannot persist an unaddressable local-only record.
        """

        from backlog_core.backend_protocol import reset_config, set_config
        from backlog_core.backend_types import BacklogConfig
        from backlog_core.backends.bd_runner import BdRunner
        from backlog_core.backends.beads_backend import BeadsBackend

        mock_runner = MagicMock(spec=BdRunner)
        mock_runner.is_available.return_value = False
        beads_backend = BeadsBackend(runner=mock_runner)
        mocker.patch.object(beads_backend, "create_beads_issue_for_item", return_value=None)
        set_config(BacklogConfig(backend=beads_backend))

        from backlog_core.models import ContentUnavailableError

        try:
            with pytest.raises(ContentUnavailableError):
                add_item(title="Beads Unavailable Item", description="desc", priority="P2")
        finally:
            reset_config()


class TestAddItemDuplicateDetection:
    """add_item raises DuplicateItemError on fuzzy duplicates unless force=True."""

    def test_add_item_raises_on_fuzzy_duplicate(self, mocker: MockerFixture) -> None:
        """Verify add_item raises DuplicateItemError when a similar item already exists.

        Tests: Duplicate detection in add_item.
        How: Write an existing item, attempt to add one with a near-identical title.
        Why: Duplicate items waste effort and cause confusion.
        """
        import backlog_core.models as models

        fake_dir: Path = models.get_backlog_dir()
        _write_item(fake_dir, title="Implement Error Recovery", priority="P1", topic="implement-error-recovery")
        mocker.patch("backlog_core.operations.try_get_github", return_value=None)

        with pytest.raises(DuplicateItemError):
            add_item(title="Implement Error Recovery Logic", description="desc", priority="P1")

    def test_add_item_force_bypasses_duplicate_check(self, mocker: MockerFixture) -> None:
        """Verify add_item with force=True creates item despite existing duplicate.

        Tests: force=True bypass in add_item.
        How: Write existing item, add similar one with force=True.
        Why: Users must override when items are intentionally distinct.
        """
        import backlog_core.models as models

        fake_dir: Path = models.get_backlog_dir()
        _write_item(fake_dir, title="Implement Error Recovery", priority="P1", topic="implement-error-recovery")
        mocker.patch("backlog_core.operations.try_get_github", return_value=None)

        result = add_item(title="Implement Error Recovery Logic", description="desc", priority="P1", force=True)

        assert result["title"] == "Implement Error Recovery Logic"

    def test_add_item_no_duplicate_succeeds(self, mocker: MockerFixture) -> None:
        """Verify add_item succeeds when no similar items exist.

        Tests: add_item happy path with duplicate check enabled.
        How: Empty backlog; add an item without force.
        Why: Duplicate check must not block unrelated new items.
        """
        mocker.patch("backlog_core.operations.try_get_github", return_value=None)

        result = add_item(title="Completely Unique Novel Feature", description="desc", priority="P2")

        assert "file_path" in result


# ---------------------------------------------------------------------------
# list_items
# ---------------------------------------------------------------------------


class TestListItemsEmpty:
    """list_items returns empty list when backlog directory has no items."""

    def test_list_items_empty_backlog_returns_empty_list(self, mocker: MockerFixture) -> None:
        """Verify list_items returns items=[] when backlog directory is empty.

        Tests: list_items empty state.
        How: Do not create any files; call list_items.
        Why: Callers must handle empty backlog without error.
        """
        mocker.patch("backlog_core.operations.batch_fetch_statuses", return_value={})

        result = list_items(from_github=False)

        assert result["items"] == []
        assert result["count"] == 0


class TestListItemsFiltering:
    """list_items excludes skip=True items and uses batch_fetch_statuses for status."""

    def test_list_items_excludes_skip_items(self, mocker: MockerFixture) -> None:
        """Verify list_items omits items with skip=True (done/resolved status).

        Tests: Skip filtering in list_items.
        How: Mock parse_backlog to return one active and one skip=True item.
        Why: Done items must not appear in the active backlog list.  parse_backlog
             is mocked to inject a BacklogItem with a specific skip value directly,
             isolating this test from parsing logic.
        """
        active = BacklogItem(title="Active Item", section="P1", skip=False)
        done = BacklogItem(title="Done Item", section="P1", skip=True)
        _seed_items([active, done])
        mocker.patch("backlog_core.operations.batch_fetch_statuses", return_value={})

        result = list_items(from_github=False)

        items = cast("list[dict[str, str | bool]]", result["items"])
        titles = [it["title"] for it in items]
        assert "Active Item" in titles
        assert "Done Item" not in titles

    def test_list_items_enriches_status_from_batch_fetch(self, mocker: MockerFixture) -> None:
        """Verify list_items always enriches items with status from batch_fetch_statuses.

        Tests: batch_fetch_statuses integration in list_items.
        How: Mock parse_backlog to return an item with issue="#7"; mock batch_fetch_statuses.
        Why: status must use batch fetch — not N+1 individual calls.  parse_backlog
             is mocked to inject a BacklogItem with a specific issue value directly,
             isolating this test from parsing logic.
        """
        item_with_issue = BacklogItem(title="Tracked Item", section="P1", skip=False, issue="#7")
        _seed_items([item_with_issue])
        mock_batch = mocker.patch(
            "backlog_core.operations.batch_fetch_statuses",
            return_value={7: IssueStatus(status="status:in-progress", milestone="v2")},
        )

        result = list_items(from_github=False, status="status:in-progress")

        mock_batch.assert_called_once()
        items = cast("list[dict[str, str | bool]]", result["items"])
        assert len(items) == 1
        assert items[0]["status"] == "status:in-progress"
        assert items[0]["milestone"] == "v2"

    def test_list_items_always_calls_batch_fetch(self, mocker: MockerFixture) -> None:
        """Verify list_items always calls batch_fetch_statuses to populate status fields.

        Tests: batch_fetch_statuses is always called regardless of filter parameters.
        How: Call list_items with no status filter; assert batch fetch was called.
        Why: Status fields (status, milestone) are always included in every response —
             batch_fetch must always run to populate them.
        """
        import backlog_core.models as models

        fake_dir: Path = models.get_backlog_dir()
        _write_item(fake_dir, title="No Status Item", priority="P2", topic="no-status-item")
        mock_batch = mocker.patch("backlog_core.operations.batch_fetch_statuses", return_value={})

        list_items(from_github=False)

        mock_batch.assert_called_once()

    def test_list_items_from_github_calls_refresh(self, mocker: MockerFixture) -> None:
        """Verify list_items with from_github=True triggers a cache refresh.

        Tests: from_github refresh path.
        How: Patch refresh_local_cache_from_github; call list_items(from_github=True).
        Why: from_github must invoke the refresh before returning local data.
        """
        mock_refresh = mocker.patch(
            "backlog_core.operations.refresh_local_cache_from_github",
            return_value={"refreshed": 0, "messages": [], "warnings": [], "errors": []},
        )
        mocker.patch("backlog_core.operations.batch_fetch_statuses", return_value={})

        list_items(from_github=True)

        mock_refresh.assert_called_once()


# ---------------------------------------------------------------------------
# list_items — beads backend (BUG-1)
# ---------------------------------------------------------------------------


class TestListItemsBeadsBackend:
    """list_items does not crash and returns correct status with BeadsBackend.

    BUG-1: batch_fetch_statuses raises NotImplementedError for beads because
    beads IDs are strings with no integer representation (ADR-002).  The fix
    detects BeadsBackend via isinstance and passes status_map={} instead.
    _item_derived_status and _build_list_entry both fall back to item.status
    when the map is empty.
    """

    def _make_beads_backend_config(self, mocker: MockerFixture) -> object:
        """Patch get_config() to return a BacklogConfig backed by BeadsBackend."""

        from backlog_core.backend_types import BacklogConfig as _BPConfig
        from backlog_core.backends.bd_runner import BdRunner
        from backlog_core.backends.beads_backend import BeadsBackend

        runner = MagicMock(spec=BdRunner)
        runner.is_available.return_value = True
        beads_backend = BeadsBackend(runner=runner)
        patched = _BPConfig(backend=beads_backend)
        mocker.patch("backlog_core.operations.get_config", return_value=patched)
        return beads_backend

    def test_list_items_beads_does_not_call_batch_fetch_statuses(self, mocker: MockerFixture) -> None:
        """list_items with BeadsBackend must not call batch_fetch_statuses.

        Tests: BUG-1 crash prevention.
        How: Swap backend to BeadsBackend; assert batch_fetch_statuses is never
             called (it would raise NotImplementedError for beads).
        Why: Calling batch_fetch_statuses on BeadsBackend raises NotImplementedError
             (ADR-002).  The fix must skip that call entirely.
        """
        self._make_beads_backend_config(mocker)
        _seed_items([])
        mock_batch = mocker.patch("backlog_core.operations.batch_fetch_statuses")

        list_items(from_github=False)

        mock_batch.assert_not_called()

    def test_list_items_beads_returns_provider_status_without_integer_issue(self, mocker: MockerFixture) -> None:
        """list_items returns the provider-owned status for a Beads item.

        Tests: BUG-1 correct status reporting for beads items.
        How: Return a provider record with issue="" and status="in-progress"; verify
             the returned entry carries that status.
        Why: With status_map={} and no integer issue, _build_list_entry must read
             item.status rather than returning an empty string.
        """
        backend = self._make_beads_backend_config(mocker)
        beads_item = BacklogItem(
            title="Beads Task",
            section="P1",
            skip=False,
            metadata=BacklogItemMetadata(
                source="test", added="2026-01-01", priority="P1", status="in-progress", issue=""
            ),
        )
        mocker.patch.object(backend, "list_work_items", return_value=[beads_item])

        result = list_items(from_github=False)

        items = cast("list[dict[str, str | bool]]", result["items"])
        assert len(items) == 1
        assert items[0]["status"] == "in-progress"

    def test_list_items_beads_returns_local_status_for_items_with_beads_nanoid(self, mocker: MockerFixture) -> None:
        """list_items with BeadsBackend returns item.status for nanoid issue refs.

        Tests: BUG-1 status fallback when item.issue is a non-integer beads ID.
        How: Inject a BacklogItem with issue="bd-a3f8" (truthy but non-integer)
             and status="open"; verify the entry status equals "open".
        Why: parse_issue_number("bd-a3f8") returns None, so the status must fall
             through to item.status rather than returning "" or "needs-grooming".
        """
        backend = self._make_beads_backend_config(mocker)
        beads_item = BacklogItem(
            title="Beads Nanoid Task",
            section="P2",
            skip=False,
            metadata=BacklogItemMetadata(
                source="test", added="2026-01-01", priority="P2", status="open", issue="bd-a3f8"
            ),
        )
        mocker.patch.object(backend, "list_work_items", return_value=[beads_item])

        result = list_items(from_github=False)

        items = cast("list[dict[str, str | bool]]", result["items"])
        assert len(items) == 1
        assert items[0]["status"] == "open"
        assert items[0]["milestone"] == ""


# ---------------------------------------------------------------------------
# _apply_issue_status_labels — beads backend (BUG-3)
# ---------------------------------------------------------------------------


class TestApplyIssueStatusLabelsBeads:
    def _make_beads_config(self, mocker: MockerFixture) -> None:
        """Patch get_config() to return a BacklogConfig backed by BeadsBackend."""

        from backlog_core.backend_types import BacklogConfig as _BPConfig
        from backlog_core.backends.bd_runner import BdRunner
        from backlog_core.backends.beads_backend import BeadsBackend

        runner = MagicMock(spec=BdRunner)
        runner.is_available.return_value = True
        self._beads_runner = runner
        beads_backend = BeadsBackend(runner=runner)
        patched = _BPConfig(backend=beads_backend)
        mocker.patch("backlog_core.operations.get_config", return_value=patched)

    def test_status_in_progress_updates_native_beads_reference(self, mocker: MockerFixture) -> None:
        from backlog_core.operations import _apply_issue_status_labels

        self._make_beads_config(mocker)
        mock_update = mocker.patch("backlog_core.operations.update_item_metadata")
        mocker.patch("backlog_core.operations.apply_status_in_progress")

        item = BacklogItem(
            title="Beads Task",
            section="P1",
            skip=False,
            metadata=BacklogItemMetadata(source="test", added="2026-01-01", priority="P1", status="open", issue=""),
            reference="bd-native-task",
        )
        result: dict[str, str | int | bool | list[str]] = {"title": item.title}
        out = Output()

        _apply_issue_status_labels(item, "in-progress", False, "", result, out)

        assert result.get("status") == "in-progress"
        mock_update.assert_called_once_with("bd-native-task", {"metadata": {"status": "in-progress"}}, output=out)

    def test_status_in_progress_calls_bd_update_claim_for_beads_item_without_issue(self, mocker: MockerFixture) -> None:
        """status="in-progress" issues bd update --claim via apply_status_in_progress.

        Tests: BUG-3 backend call.
        How: Patch get_config to return BeadsBackend with a fake runner; assert
             apply_status_in_progress is called so bd update --claim runs.
        Why: apply_status_in_progress issues ``bd update <selector> --claim``.
             The selector falls back to item.title when item.issue is empty.
        """
        from backlog_core.operations import _apply_issue_status_labels

        self._make_beads_config(mocker)
        mock_apply = mocker.patch("backlog_core.operations.apply_status_in_progress")
        mocker.patch("backlog_core.operations.update_item_metadata")

        item = BacklogItem(
            title="Beads Claim Task",
            section="P1",
            skip=False,
            metadata=BacklogItemMetadata(source="test", added="2026-01-01", priority="P1", status="open", issue=""),
            reference="bd-claim-task",
        )
        result: dict[str, str | int | bool | list[str]] = {"title": item.title}
        out = Output()

        _apply_issue_status_labels(item, "in-progress", False, "", result, out)

        mock_apply.assert_called_once_with(item, "", output=out)

    def test_status_in_progress_calls_bd_update_claim_for_beads_nanoid_issue(self, mocker: MockerFixture) -> None:
        """status="in-progress" calls apply_status_in_progress for nanoid item.issue.

        Tests: BUG-3 backend call when item.issue holds a beads nanoid.
        How: Use item.issue="bd-a3f8" (truthy, non-integer); assert
             apply_status_in_progress is called with the correct argv.
        Why: Beads items synced from bd may have a nanoid in item.issue.
             The fix must route these through apply_status_in_progress.
        """
        from backlog_core.operations import _apply_issue_status_labels

        self._make_beads_config(mocker)
        mock_apply = mocker.patch("backlog_core.operations.apply_status_in_progress")
        mocker.patch("backlog_core.operations.update_item_metadata")

        item = BacklogItem(
            title="Beads Nanoid Task",
            section="P1",
            skip=False,
            metadata=BacklogItemMetadata(
                source="test", added="2026-01-01", priority="P1", status="open", issue="bd-a3f8"
            ),
            reference="bd-a3f8",
        )
        result: dict[str, str | int | bool | list[str]] = {"title": item.title}
        out = Output()

        _apply_issue_status_labels(item, "in-progress", False, "", result, out)

        mock_apply.assert_called_once_with(item, "", output=out)
        assert result.get("status") == "in-progress"

    def test_github_backend_status_in_progress_unchanged(self, mocker: MockerFixture) -> None:
        """Non-beads backend: status="in-progress" path is unaffected by the fix.

        Tests: Regression guard — GitHub path must still call apply_status_in_progress
               and must NOT call update_item_metadata for status changes.
        How: Keep default GitHub backend; inject item with issue="#7"; assert
             apply_status_in_progress is called and update_item_metadata is not.
        Why: The beads-specific code path must not affect existing GitHub behaviour.
        """
        from backlog_core.operations import _apply_issue_status_labels

        mock_apply = mocker.patch("backlog_core.operations.apply_status_in_progress")
        mock_update = mocker.patch("backlog_core.operations.update_item_metadata")

        item = BacklogItem(
            title="GitHub Task",
            section="P1",
            skip=False,
            metadata=BacklogItemMetadata(source="test", added="2026-01-01", priority="P1", status="open", issue="#7"),
        )
        result: dict[str, str | int | bool | list[str]] = {"title": item.title}
        out = Output()

        _apply_issue_status_labels(item, "in-progress", False, "", result, out)

        mock_apply.assert_called_once_with(item, "", output=out)
        mock_update.assert_not_called()
        assert result.get("status") == "in-progress"

    def test_status_blocked_applies_github_label_instead_of_silent_noop(self, mocker: MockerFixture) -> None:
        """status="blocked" on a GitHub-backend item calls apply_status_blocked, not a no-op.

        Tests: regression for #2905 — only "in-progress" had a dedicated branch;
               every other status value (including "blocked") fell through with
               no action and no error.
        Why: work-backlog-item's RT-ICA gate calls
             backlog_update(selector=item_ref, status='blocked') expecting it to
             actually mark the issue blocked (via a status:blocked label) —
             it was silently doing nothing.
        """
        from backlog_core.operations import _apply_issue_status_labels

        mock_blocked = mocker.patch("backlog_core.operations.apply_status_blocked")
        mock_update = mocker.patch("backlog_core.operations.update_item_metadata")

        item = BacklogItem(
            title="Blocked Task",
            section="P1",
            skip=False,
            metadata=BacklogItemMetadata(source="test", added="2026-01-01", priority="P1", status="open", issue="#9"),
            reference="#9",
        )
        result: dict[str, str | int | bool | list[str]] = {"title": item.title}
        out = Output()

        _apply_issue_status_labels(item, "blocked", False, "", result, out)

        mock_blocked.assert_called_once_with(item, "", output=out)
        mock_update.assert_not_called()
        assert result.get("status") == "blocked"

    def test_status_blocked_beads_writes_local_metadata(self, mocker: MockerFixture) -> None:
        """status="blocked" on a string-ID (beads) backend writes local metadata, not a GitHub label call."""
        from backlog_core.operations import _apply_issue_status_labels

        self._make_beads_config(mocker)
        mock_blocked = mocker.patch("backlog_core.operations.apply_status_blocked")
        mock_update = mocker.patch("backlog_core.operations.update_item_metadata")

        item = BacklogItem(
            title="Beads Blocked Task",
            section="P1",
            skip=False,
            metadata=BacklogItemMetadata(source="test", added="2026-01-01", priority="P1", status="open", issue=""),
            reference="bd-blocked-task",
        )
        result: dict[str, str | int | bool | list[str]] = {"title": item.title}
        out = Output()

        _apply_issue_status_labels(item, "blocked", False, "", result, out)

        mock_update.assert_called_once_with("bd-blocked-task", {"metadata": {"status": "blocked"}}, output=out)
        mock_blocked.assert_not_called()
        assert result.get("status") == "blocked"

    def test_status_done_rejected_directs_to_resolve(self, mocker: MockerFixture) -> None:
        """status="done" is rejected with a clear error, not silently accepted or no-op'd.

        Tests: regression for #2905's original title — terminal states (done/
               resolved/closed) are owned by resolve_item()/close_item(), which
               record an evidence trail and actually close the backend issue.
               Silently writing status=done here would desync local state from
               the real (still-open) issue.
        """
        from backlog_core.operations import _apply_issue_status_labels

        mock_update = mocker.patch("backlog_core.operations.update_item_metadata")

        item = BacklogItem(
            title="Done Task",
            section="P1",
            skip=False,
            metadata=BacklogItemMetadata(source="test", added="2026-01-01", priority="P1", status="open", issue="#9"),
            reference="#9",
        )
        result: dict[str, str | int | bool | list[str]] = {"title": item.title}
        out = Output()

        _apply_issue_status_labels(item, "done", False, "", result, out)

        mock_update.assert_not_called()
        assert "error" in result
        assert "backlog resolve" in result["error"]
        assert result.get("status") is None

    def test_status_unrecognized_value_reports_error(self, mocker: MockerFixture) -> None:
        """An unrecognized status string reports an error rather than silently no-op'ing."""
        from backlog_core.operations import _apply_issue_status_labels

        mocker.patch("backlog_core.operations.update_item_metadata")

        item = BacklogItem(
            title="Bogus Status Task",
            section="P1",
            skip=False,
            metadata=BacklogItemMetadata(source="test", added="2026-01-01", priority="P1", status="open", issue="#9"),
            reference="#9",
        )
        result: dict[str, str | int | bool | list[str]] = {"title": item.title}
        out = Output()

        _apply_issue_status_labels(item, "bogus-status", False, "", result, out)

        assert result.get("error") == "Unrecognized status value: 'bogus-status'"
        assert result.get("status") is None


# ---------------------------------------------------------------------------
# view_item
# ---------------------------------------------------------------------------


class TestViewItem:
    """view_item returns ViewItemResult for local items and raises for unknowns."""

    def test_view_item_returns_view_item_result_type(self, mocker: MockerFixture) -> None:
        """Verify view_item returns a ViewItemResult instance, not a raw dict.

        Tests: view_item return type contract.
        How: Write a local item; call view_item; assert isinstance(result, ViewItemResult).
        Why: Callers should receive a typed model, not an untyped dict, so attribute
             access is safe and the type checker can enforce the contract.
        """

        import backlog_core.models as models

        fake_dir: Path = models.get_backlog_dir()
        _write_item(fake_dir, title="Type Check Item", priority="P1", topic="type-check-item")
        mocker.patch("backlog_core.operations.view_enrich_from_github", return_value=False)

        result = view_item("Type Check Item")

        assert isinstance(result, ViewItemResult)
        assert isinstance(result.messages, list)
        assert isinstance(result.warnings, list)

    def test_view_item_known_title_returns_result(self, mocker: MockerFixture) -> None:
        """Verify view_item returns ViewItemResult with title field for a known item.

        Tests: view_item happy path with title selector.
        How: Write a local item; call view_item with the title; check result fields.
        Why: Callers depend on the returned model to display item details.
        """
        import backlog_core.models as models

        fake_dir: Path = models.get_backlog_dir()
        _write_item(fake_dir, title="Viewable Item", priority="P1", topic="viewable-item")
        mocker.patch("backlog_core.operations.view_enrich_from_github", return_value=False)

        result = view_item("Viewable Item")

        assert result.title == "Viewable Item"

    def test_view_item_unknown_selector_raises_item_not_found_error(self, mocker: MockerFixture) -> None:
        """Verify view_item raises ItemNotFoundError for an unrecognised selector.

        Tests: view_item error path with unknown selector.
        How: Call view_item with a selector that matches nothing.
        Why: Callers must catch ItemNotFoundError to surface meaningful errors.
        """
        mocker.patch("backlog_core.operations.view_enrich_from_github", return_value=False)

        with pytest.raises(ItemNotFoundError):
            view_item("Nonexistent Item That Does Not Exist")

    def test_view_item_offset_limit_paginates_body(self, mocker: MockerFixture) -> None:
        """Verify view_item applies offset and limit to body text.

        Tests: Body pagination in view_item.
        How: Write item with multi-line body; call view_item with offset=1, limit=1.
        Why: Without pagination, large bodies overwhelm the caller; pagination is user-controlled.
        """
        import backlog_core.models as models

        fake_dir: Path = models.get_backlog_dir()
        body_text = "Line 0\nLine 1\nLine 2\nLine 3\nLine 4"
        _write_item(fake_dir, title="Paginated Item", priority="P2", topic="paginated-item", extra_body=body_text)
        mocker.patch("backlog_core.operations.view_enrich_from_github", return_value=False)

        result = view_item("Paginated Item", offset=1, limit=2)

        body_lines = result.body.splitlines()
        # Only 2 lines returned starting from line 1
        assert len(body_lines) <= 2

    def test_view_item_no_pagination_returns_full_body(self, mocker: MockerFixture) -> None:
        """Verify view_item returns full body when offset and limit are both 0.

        Tests: view_item default no-truncation contract.
        How: Write item with 5-line body; call view_item(offset=0, limit=0).
        Why: Consumers must receive complete data when they do not request pagination.
        """
        import backlog_core.models as models

        fake_dir: Path = models.get_backlog_dir()
        body_text = "\n".join(f"Line {i}" for i in range(5))
        _write_item(fake_dir, title="Full Body Item", priority="P2", topic="full-body-item", extra_body=body_text)
        mocker.patch("backlog_core.operations.view_enrich_from_github", return_value=False)

        result = view_item("Full Body Item", offset=0, limit=0)

        assert result.body_truncated is False

    def test_view_item_returns_section_entries(self, mocker: MockerFixture) -> None:
        """view_item response includes sections dict with entry metadata.

        Tests: _build_sections_metadata integration — sections populated from local item body.
        How: add_item then groom_item twice into Decision section; call view_item.
        Why: MCP clients need structured entry metadata, not raw body text.
        """
        from backlog_core.models import Output

        mocker.patch("backlog_core.operations.view_enrich_from_github", return_value=False)
        mocker.patch("backlog_core.operations.try_get_github", return_value=None)

        out = Output()
        ops.add_item(title="View Test", priority="P1", description="Test", output=out)
        ops.groom_item(selector="View Test", section="Decision", content="Entry 1.", output=out)
        ops.groom_item(selector="View Test", section="Decision", content="Entry 2.", output=out)
        result = view_item(selector="View Test", output=out)

        sections = result.sections
        assert isinstance(sections, dict), "sections must be a dict"
        assert "Decision" in sections, f"Expected 'Decision' in sections, got: {list(sections.keys())}"
        # groom_item creates entry-block sections (SectionEntryMetadata shape).
        decision = cast("SectionEntryMetadata", sections["Decision"])
        assert decision["num_entries"] == 2
        assert len(decision["entries"]) == 2


# ---------------------------------------------------------------------------
# close_item
# ---------------------------------------------------------------------------


class TestCloseItem:
    """close_item requires a valid categorized reason and optionally checks for open PRs."""

    def test_close_item_invalid_reason_raises_validation_error(self, mocker: MockerFixture) -> None:
        """Verify close_item raises ValidationError when reason is not in VALID_CLOSE_REASONS.

        Tests: Reason validation gate in close_item.
        How: Call close_item with an invalid reason string.
        Why: Closing without a categorized reason loses context permanently.
        """
        with pytest.raises(ValidationError, match="Invalid close reason"):
            close_item(selector="anything", reason="not-a-valid-reason")

    def test_close_item_unknown_selector_raises_item_not_found_error(self, mocker: MockerFixture) -> None:
        """Verify close_item raises ItemNotFoundError when selector matches nothing.

        Tests: close_item selector resolution error path.
        How: Empty backlog; call close_item with a valid reason.
        Why: Callers must catch ItemNotFoundError to surface actionable feedback.
        """
        mocker.patch("backlog_core.operations.check_open_prs_for_issue", return_value=[])

        with pytest.raises(ItemNotFoundError):
            close_item(selector="Nonexistent Item", reason="superseded")

    def test_close_item_happy_path_returns_closed_true(self, mocker: MockerFixture) -> None:
        """Verify close_item returns closed=True for a valid item with a valid reason.

        Tests: close_item success path.
        How: Write a local item with no issue; call close_item; check closed=True.
        Why: Callers confirm item was closed by checking this field.
        """
        import backlog_core.models as models

        fake_dir: Path = models.get_backlog_dir()
        _write_item(fake_dir, title="Closeable Item", priority="P1", topic="closeable-item")
        mocker.patch("backlog_core.operations.check_open_prs_for_issue", return_value=[])
        mocker.patch("backlog_core.operations.close_github_issue")

        result = close_item(selector="Closeable Item", reason="superseded")

        assert result["closed"] is True

    def test_close_item_with_open_pr_raises_backlog_error(self, mocker: MockerFixture) -> None:
        """Verify close_item raises BacklogError when open PRs reference the issue.

        Tests: Open PR guard in close_item.
        How: Mock find_item to return a BacklogItem with issue="#5" (bypasses parser bug);
             mock check_open_prs_for_issue to return one PR.
        Why: Premature close orphans in-flight PRs.  find_item is mocked to inject
             a BacklogItem with a specific issue value directly, isolating this test
             from parsing logic.
        """
        import backlog_core.models as models
        from backlog_core.models import BacklogError

        fake_dir: Path = models.get_backlog_dir()
        filepath = _write_item(fake_dir, title="PR Blocked Close", priority="P1", topic="pr-blocked-close")
        item_with_issue = BacklogItem(
            title="PR Blocked Close", section="P1", issue="#5", file_path=str(filepath), reference=str(filepath)
        )
        mocker.patch("backlog_core.operations.find_item", return_value=item_with_issue)
        mocker.patch(
            "backlog_core.operations.check_open_prs_for_issue",
            return_value=[PullRequestRef(number=10, title="WIP: feature", url="https://github.com/t/10")],
        )

        with pytest.raises(BacklogError, match="Open PRs"):
            close_item(selector="PR Blocked Close", reason="superseded", force=False)

    def test_close_item_force_bypasses_open_pr_guard(self, mocker: MockerFixture) -> None:
        """Verify close_item with force=True succeeds despite open PRs.

        Tests: force=True bypass of PR guard in close_item.
        How: Mock find_item to return an item with issue="#6"; mock open PR; call force=True.
        Why: Users must override when PRs are stale or irrelevant.
        """
        import backlog_core.models as models

        fake_dir: Path = models.get_backlog_dir()
        filepath = _write_item(fake_dir, title="Force Close Item", priority="P1", topic="force-close-item")
        item_with_issue = BacklogItem(
            title="Force Close Item", section="P1", issue="#6", file_path=str(filepath), reference=str(filepath)
        )
        mocker.patch("backlog_core.operations.find_item", return_value=item_with_issue)
        mocker.patch(
            "backlog_core.operations.check_open_prs_for_issue",
            return_value=[PullRequestRef(number=11, title="WIP", url="https://github.com/t/11")],
        )
        mocker.patch("backlog_core.operations.close_github_issue")

        result = close_item(selector="Force Close Item", reason="superseded", force=True)

        assert result["closed"] is True


# ---------------------------------------------------------------------------
# resolve_item
# ---------------------------------------------------------------------------


class TestResolveItem:
    """resolve_item requires a non-empty summary and validates the selector."""

    def test_resolve_item_empty_summary_raises_validation_error(self, mocker: MockerFixture) -> None:
        """Verify resolve_item raises ValidationError when summary is empty string.

        Tests: Empty summary guard in resolve_item.
        How: Call resolve_item with summary="".
        Why: Resolving without a summary loses context permanently.
        """
        with pytest.raises(ValidationError, match="summary is required"):
            resolve_item(selector="anything", summary="")

    def test_resolve_item_whitespace_summary_raises_validation_error(self, mocker: MockerFixture) -> None:
        """Verify resolve_item raises ValidationError when summary is whitespace-only.

        Tests: Whitespace summary guard in resolve_item.
        How: Call resolve_item with summary="   ".
        Why: Whitespace-only summary is semantically empty — must be rejected.
        """
        with pytest.raises(ValidationError, match="summary is required"):
            resolve_item(selector="anything", summary="   ")

    def test_resolve_item_unknown_selector_raises_item_not_found_error(self, mocker: MockerFixture) -> None:
        """Verify resolve_item raises ItemNotFoundError when selector matches nothing.

        Tests: resolve_item selector resolution error path.
        How: Empty backlog; call resolve_item with a valid summary.
        Why: Callers must distinguish missing items from validation errors.
        """
        mocker.patch("backlog_core.operations.check_open_prs_for_issue", return_value=[])

        with pytest.raises(ItemNotFoundError):
            resolve_item(selector="Missing Item", summary="No longer needed")

    def test_resolve_item_happy_path_returns_resolved_true(self, mocker: MockerFixture) -> None:
        """Verify resolve_item returns resolved=True for a valid item with a reason.

        Tests: resolve_item success path.
        How: Write a local item with no issue; call resolve_item.
        Why: Callers confirm item was resolved by checking this field.
        """
        import backlog_core.models as models

        fake_dir: Path = models.get_backlog_dir()
        _write_item(fake_dir, title="Resolvable Item", priority="P2", topic="resolvable-item")
        mocker.patch("backlog_core.operations.check_open_prs_for_issue", return_value=[])
        mocker.patch("backlog_core.operations.resolve_github_issue")

        result = resolve_item(selector="Resolvable Item", summary="Superseded by new approach")

        assert result["resolved"] is True

    def test_resolve_item_with_open_pr_raises_backlog_error(self, mocker: MockerFixture) -> None:
        """Verify resolve_item raises BacklogError when open PRs reference the issue.

        Tests: Open PR guard in resolve_item.
        How: Mock find_item to return a BacklogItem with issue="#8"; mock open PR.
        Why: Resolving orphans in-flight PRs.  find_item is mocked to inject a
             BacklogItem with a specific issue value directly, isolating this test
             from parsing logic.
        """
        import backlog_core.models as models
        from backlog_core.models import BacklogError

        fake_dir: Path = models.get_backlog_dir()
        filepath = _write_item(fake_dir, title="PR Blocked Resolve", priority="P1", topic="pr-blocked-resolve")
        item_with_issue = BacklogItem(
            title="PR Blocked Resolve", section="P1", issue="#8", file_path=str(filepath), reference=str(filepath)
        )
        mocker.patch("backlog_core.operations.find_item", return_value=item_with_issue)
        mocker.patch(
            "backlog_core.operations.check_open_prs_for_issue",
            return_value=[PullRequestRef(number=20, title="Fix: something", url="https://github.com/t/20")],
        )

        with pytest.raises(BacklogError, match="Open PRs"):
            resolve_item(selector="PR Blocked Resolve", summary="Superseded", force=False)

    def test_resolve_item_force_bypasses_open_pr_guard(self, mocker: MockerFixture) -> None:
        """Verify resolve_item with force=True succeeds despite open PRs.

        Tests: force=True bypass of PR guard in resolve_item.
        How: Mock find_item to return item with issue="#9"; mock open PR; call force=True.
        Why: Users must override when PRs are no longer relevant.
        """
        import backlog_core.models as models

        fake_dir: Path = models.get_backlog_dir()
        filepath = _write_item(fake_dir, title="Force Resolve Item", priority="P1", topic="force-resolve-item")
        item_with_issue = BacklogItem(
            title="Force Resolve Item", section="P1", issue="#9", file_path=str(filepath), reference=str(filepath)
        )
        mocker.patch("backlog_core.operations.find_item", return_value=item_with_issue)
        mocker.patch(
            "backlog_core.operations.check_open_prs_for_issue",
            return_value=[PullRequestRef(number=21, title="WIP", url="https://github.com/t/21")],
        )
        mocker.patch("backlog_core.operations.resolve_github_issue")

        result = resolve_item(selector="Force Resolve Item", summary="Superseded by different effort", force=True)

        assert result["resolved"] is True


# ---------------------------------------------------------------------------
# Parametrize: GitHub-only fallback for close_item and resolve_item (#323)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("op", "op_kwargs", "gh_mock", "result_key", "title", "priority", "topic"),
    [
        (
            close_item,
            {"selector": "#999", "reason": "superseded"},
            "backlog_core.operations.close_github_issue",
            "closed",
            "GitHub Only Issue",
            "P1",
            "github-only-issue",
        ),
        (
            resolve_item,
            {"selector": "#999", "summary": "Completed via GitHub-only fallback"},
            "backlog_core.operations.resolve_github_issue",
            "resolved",
            "GitHub Only Resolve",
            "P2",
            "github-only-resolve",
        ),
    ],
)
def test_github_only_falls_back_to_pull(
    op: Callable[..., Any],
    op_kwargs: dict,
    gh_mock: str,
    result_key: str,
    title: str,
    priority: str,
    topic: str,
    mocker: MockerFixture,
) -> None:
    """Verify close_item and resolve_item fall back to GitHub pull when no local cache file exists.

    Tests: _pull_if_issue_selector fallback path in close/resolve operations.
    How: Empty backlog; mock _pull_if_issue_selector to write a local cache file
         as a side effect; call the operation with a #N selector.
    Why: GitHub-only issues (never synced or deleted from cache) must be closeable/resolvable
         without a prior pull. Covers acceptance criteria from issue #323.
    """
    import backlog_core.models as models

    fake_dir: Path = models.get_backlog_dir()

    def _write_cache_file(selector: str, repo: str, output: object = None) -> None:
        _write_item(fake_dir, title=title, priority=priority, topic=topic, issue="#999")

    mocker.patch("backlog_core.operations._pull_if_issue_selector", side_effect=_write_cache_file)
    mocker.patch("backlog_core.operations.check_open_prs_for_issue", return_value=[])
    mocker.patch(gh_mock)

    result = op(**op_kwargs)

    assert result[result_key] is True
    assert result["title"] == title


@pytest.mark.parametrize(
    ("op", "kwargs"),
    [
        (close_item, {"selector": "#999", "reason": "superseded"}),
        (resolve_item, {"selector": "#999", "summary": "Should not succeed"}),
    ],
)
def test_github_only_raises_when_issue_absent(op: Callable[..., Any], kwargs: dict, mocker: MockerFixture) -> None:
    """Verify close_item and resolve_item raise ItemNotFoundError when issue is absent from both local cache and GitHub.

    Tests: Double-not-found path after _pull_if_issue_selector fallback yields nothing.
    How: Empty backlog; mock _pull_if_issue_selector as no-op (issue absent on GH too).
    Why: Fallback must surface ItemNotFoundError — not swallow the error silently.
    """
    mocker.patch("backlog_core.operations._pull_if_issue_selector")  # no-op: writes nothing

    with pytest.raises(ItemNotFoundError):
        op(**kwargs)


# ---------------------------------------------------------------------------
# Parametrize: priority prefixes are recognised in filenames
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("priority", "topic", "expected_section"),
    [("P0", "critical-feature", "P0"), ("P1", "important-feature", "P1"), ("P2", "nice-to-have", "P2")],
)
def test_list_items_section_derived_from_priority(
    priority: str, topic: str, expected_section: str, mocker: MockerFixture
) -> None:
    """Verify list_items derives item section from the priority metadata field.

    Tests: Section derivation from priority in list_items.
    How: Write item with given priority; verify the returned item has the expected section.
    Why: Section is used for display grouping — wrong section mis-orders items.
    """
    import backlog_core.models as models

    fake_dir: Path = models.get_backlog_dir()
    _write_item(fake_dir, title=f"{priority} Item", priority=priority, topic=topic)
    mocker.patch("backlog_core.operations.batch_fetch_statuses", return_value={})

    result = list_items(from_github=False)

    items = cast("list[dict[str, str | bool]]", result["items"])
    assert len(items) == 1
    assert items[0]["section"] == expected_section


# ---------------------------------------------------------------------------
# update_item: title and description params
# ---------------------------------------------------------------------------


class TestUpdateItemTitleAndDescription:
    """update_item with title= and description= params updates local file fields."""

    def test_update_item_title_renames_local_file(self, mocker: MockerFixture) -> None:
        """update_item with title= updates the name field in the local file.

        Tests: update_item title rename code path.
        How: Write an item file; call update_item with title=; read back the file.
        Why: The name field in frontmatter is how the item title is stored and
             displayed — a rename that doesn't persist is data loss.
        """
        import backlog_core.models as models
        from backlog_core.operations import update_item

        fake_dir: Path = models.get_backlog_dir()
        _write_item(fake_dir, title="Old Title", topic="old-title")
        mocker.patch("backlog_core.operations.try_get_github", return_value=None)

        result = update_item(selector="Old Title", title="New Title")

        assert result.get("renamed_to") == "New Title"
        assert _stored_item(fake_dir / "p1-old-title.md").title == "New Title"

    def test_update_item_title_updates_github_issue_when_linked(self, mocker: MockerFixture) -> None:
        """update_item with title= calls GitHub issue edit when item has an issue.

        Tests: update_item title rename with GitHub sync via GraphQL.
        How: Write an item with issue='#42'; mock _fetch_issue_graphql and
             _update_issue_graphql; call update_item with title=; verify GraphQL
             mutation was called with the new title.
        Why: Title rename must propagate to the linked GitHub issue when one exists.
             After T01 the rename path uses GraphQL, not PyGithub get_issue/edit.
        """
        import backlog_core.models as models
        from backlog_core.operations import update_item

        fake_dir: Path = models.get_backlog_dir()
        _write_item(fake_dir, title="Linked Item", topic="linked-item", issue="42")

        mock_repo = mocker.Mock()
        mock_repo.full_name = "owner/repo"
        mocker.patch("backlog_core.operations.try_get_github", return_value=mock_repo)

        fake_node_id = "MDExOlB1bGxSZXF1ZXN0NDE="
        mock_fetch_issue = mocker.patch(
            "backlog_core.operations._fetch_issue_graphql",
            return_value={"id": fake_node_id, "number": 42, "title": "Linked Item"},
        )
        mock_update_issue = mocker.patch("backlog_core.operations._update_issue_graphql")

        update_item(selector="Linked Item", title="Renamed Item")

        mock_fetch_issue.assert_called_once_with(mock_repo, "owner", "repo", 42)
        mock_update_issue.assert_called_once_with(mock_repo, fake_node_id, title="Renamed Item")

    def test_update_item_title_no_github_when_no_issue(self, mocker: MockerFixture) -> None:
        """update_item with title= does NOT call GitHub when item has no issue.

        Tests: update_item title rename local-only code path.
        How: Write an item with no issue field; verify try_get_github is not called.
        Why: Items without issues are local-only; no GitHub side-effect should occur.
        """
        import backlog_core.models as models
        from backlog_core.operations import update_item

        fake_dir: Path = models.get_backlog_dir()
        _write_item(fake_dir, title="No Issue Item", topic="no-issue-item", issue="")
        mock_try_gh = mocker.patch("backlog_core.operations.try_get_github")

        update_item(selector="No Issue Item", title="Still No Issue Item")

        mock_try_gh.assert_not_called()
        assert _stored_item(fake_dir / "p1-no-issue-item.md").title == "Still No Issue Item"

    def test_update_item_description_updates_local_file(self, mocker: MockerFixture) -> None:
        """update_item with description= updates the description field in the local file.

        Tests: update_item description update code path.
        How: Write an item file; call update_item with description=; read back the file.
        Why: Description is local-only metadata — changes must be persisted to the file.
        """
        import backlog_core.models as models
        from backlog_core.operations import update_item

        fake_dir: Path = models.get_backlog_dir()
        _write_item(fake_dir, title="Desc Item", topic="desc-item")
        mocker.patch("backlog_core.operations.try_get_github", return_value=None)

        result = update_item(selector="Desc Item", description="Updated description text.")

        assert result.get("description_updated") is True
        assert _stored_item(fake_dir / "p1-desc-item.md").description == "Updated description text."

    def test_update_item_description_no_github_call(self, mocker: MockerFixture) -> None:
        """update_item with description= never calls GitHub.

        Tests: update_item description local-only path.
        How: Write an item with an issue; patch try_get_github; verify it is not called.
        Why: Description is intentionally local-only per the spec (no GitHub sync).
        """
        import backlog_core.models as models
        from backlog_core.operations import update_item

        fake_dir: Path = models.get_backlog_dir()
        _write_item(fake_dir, title="Desc GitHub Item", topic="desc-gh-item", issue="99")
        mock_try_gh = mocker.patch("backlog_core.operations.try_get_github")

        update_item(selector="Desc GitHub Item", description="Local only description.")

        mock_try_gh.assert_not_called()


# ---------------------------------------------------------------------------
# list_items — section / title / status filters
# ---------------------------------------------------------------------------


class TestListItemsFilterSection:
    """list_items(section=...) filters items by priority section (case-insensitive)."""

    def test_filter_section_p0_only(self, mocker: MockerFixture) -> None:
        """section='P0' returns only P0 items.

        Tests: section filter in list_items.
        How: Mock parse_backlog with P0 and P1 items; call list_items(section='P0').
        Why: Callers need to narrow output to a single priority bucket.
        """
        p0_item = BacklogItem(title="Critical Fix", section="P0", skip=False)
        p1_item = BacklogItem(title="Nice Feature", section="P1", skip=False)
        _seed_items([p0_item, p1_item])
        mocker.patch("backlog_core.operations.batch_fetch_statuses", return_value={})

        result = list_items(section="P0")

        items = cast("list[dict[str, str | bool]]", result["items"])
        assert len(items) == 1
        assert items[0]["title"] == "Critical Fix"

    def test_filter_section_case_insensitive(self, mocker: MockerFixture) -> None:
        """section='p1' (lowercase) matches items with section='P1'.

        Tests: case-insensitive section matching.
        How: Mock parse_backlog with a P1 item; pass section='p1'.
        Why: Users should not need to remember exact casing.
        """
        p1_item = BacklogItem(title="Should-Have", section="P1", skip=False)
        _seed_items([p1_item])
        mocker.patch("backlog_core.operations.batch_fetch_statuses", return_value={})

        result = list_items(section="p1")

        items = cast("list[dict[str, str | bool]]", result["items"])
        assert len(items) == 1
        assert items[0]["title"] == "Should-Have"

    def test_filter_section_no_match_returns_empty(self, mocker: MockerFixture) -> None:
        """section='Ideas' returns empty list when no Ideas items exist.

        Tests: section filter with zero matches.
        How: Mock parse_backlog with only P0 items; filter by 'Ideas'.
        Why: Empty result is correct — not an error.
        """
        p0_item = BacklogItem(title="Urgent", section="P0", skip=False)
        _seed_items([p0_item])
        mocker.patch("backlog_core.operations.batch_fetch_statuses", return_value={})

        result = list_items(section="Ideas")

        items = cast("list[dict[str, str | bool]]", result["items"])
        assert items == []

    def test_filter_section_none_returns_all(self, mocker: MockerFixture) -> None:
        """section=None (default) returns all open items.

        Tests: no section filter applied when section is None.
        How: Mock parse_backlog with P0 and P2 items; call list_items() without section.
        Why: Default behaviour must not change for existing callers.
        """
        p0_item = BacklogItem(title="Critical", section="P0", skip=False)
        p2_item = BacklogItem(title="Nice to Have", section="P2", skip=False)
        _seed_items([p0_item, p2_item])
        mocker.patch("backlog_core.operations.batch_fetch_statuses", return_value={})

        result = list_items()

        items = cast("list[dict[str, str | bool]]", result["items"])
        assert len(items) == 2


class TestListItemsFilterTitle:
    """list_items(title=...) filters items by case-insensitive substring match."""

    def test_filter_title_substring_match(self, mocker: MockerFixture) -> None:
        """title='auth' matches 'Add authentication flow'.

        Tests: title substring filter in list_items.
        How: Mock parse_backlog with matching and non-matching items.
        Why: Users search by keyword, not exact title.
        """
        auth_item = BacklogItem(title="Add authentication flow", section="P1", skip=False)
        other_item = BacklogItem(title="Fix pagination bug", section="P1", skip=False)
        _seed_items([auth_item, other_item])
        mocker.patch("backlog_core.operations.batch_fetch_statuses", return_value={})

        result = list_items(title="auth")

        items = cast("list[dict[str, str | bool]]", result["items"])
        assert len(items) == 1
        assert items[0]["title"] == "Add authentication flow"

    def test_filter_title_case_insensitive(self, mocker: MockerFixture) -> None:
        """title='AUTH' (uppercase) matches 'Add authentication flow'.

        Tests: case-insensitive title filtering.
        How: Pass uppercase substring; expect match on lowercase title.
        Why: Users should not need exact case for filtering.
        """
        auth_item = BacklogItem(title="Add authentication flow", section="P1", skip=False)
        _seed_items([auth_item])
        mocker.patch("backlog_core.operations.batch_fetch_statuses", return_value={})

        result = list_items(title="AUTH")

        items = cast("list[dict[str, str | bool]]", result["items"])
        assert len(items) == 1

    def test_filter_title_no_match_returns_empty(self, mocker: MockerFixture) -> None:
        """title='xyz' with no matching items returns empty list.

        Tests: title filter zero-match case.
        How: Mock parse_backlog with items that do not contain 'xyz'.
        Why: Empty result is correct — not an error.
        """
        item = BacklogItem(title="Add authentication", section="P1", skip=False)
        _seed_items([item])
        mocker.patch("backlog_core.operations.batch_fetch_statuses", return_value={})

        result = list_items(title="xyz")

        items = cast("list[dict[str, str | bool]]", result["items"])
        assert items == []


class TestListItemsFilterStatus:
    """list_items(status=...) filters items by derived GitHub status."""

    def test_filter_status_in_progress(self, mocker: MockerFixture) -> None:
        """status='status:in-progress' returns only items with that GitHub status.

        Tests: status filter via _item_derived_status.
        How: Mock batch_fetch_statuses to return in-progress for issue #5; include
             a second item with no issue (needs-grooming).
        Why: Callers need to isolate active work items.
        """
        in_progress_item = BacklogItem(title="Active Work", section="P1", skip=False, issue="#5")
        idle_item = BacklogItem(title="Unstarted", section="P1", skip=False)
        _seed_items([in_progress_item, idle_item])
        mocker.patch(
            "backlog_core.operations.batch_fetch_statuses",
            return_value={5: IssueStatus(status="status:in-progress", milestone="")},
        )

        result = list_items(status="status:in-progress")

        items = cast("list[dict[str, str | bool]]", result["items"])
        assert len(items) == 1
        assert items[0]["title"] == "Active Work"

    def test_filter_status_needs_grooming_default(self, mocker: MockerFixture) -> None:
        """Items without a GitHub issue default to 'needs-grooming' status.

        Tests: default status for issueless items.
        How: Item has no issue; filter by 'needs-grooming'.
        Why: Items without issues must be discoverable as needing grooming.
        """
        no_issue_item = BacklogItem(title="Ungroomed Item", section="P2", skip=False)
        _seed_items([no_issue_item])
        mocker.patch("backlog_core.operations.batch_fetch_statuses", return_value={})

        result = list_items(status="needs-grooming")

        items = cast("list[dict[str, str | bool]]", result["items"])
        assert len(items) == 1
        assert items[0]["title"] == "Ungroomed Item"

    def test_filter_status_excludes_non_matching(self, mocker: MockerFixture) -> None:
        """status='needs-grooming' excludes items with a different GitHub status.

        Tests: status filter exclusion.
        How: Mock a P1 item with issue #9 and 'status:done' from GitHub.
        Why: Filtering must exclude items that do not match the requested status.
        """
        done_item = BacklogItem(title="Done Task", section="P1", skip=False, issue="#9")
        _seed_items([done_item])
        mocker.patch(
            "backlog_core.operations.batch_fetch_statuses",
            return_value={9: IssueStatus(status="status:done", milestone="")},
        )

        result = list_items(status="needs-grooming")

        items = cast("list[dict[str, str | bool]]", result["items"])
        assert items == []


# ---------------------------------------------------------------------------
# list_items: type_ filter
# ---------------------------------------------------------------------------


class TestListItemsFilterType:
    """list_items(type_=...) filters items by case-insensitive exact match on metadata.type."""

    def test_filter_type_returns_matching_items(self, mocker: MockerFixture) -> None:
        """type_='Bug' returns only items whose metadata.type is 'Bug' (case-insensitive).

        Tests: type_ exact-match filter.
        How: Two items with type_ 'Bug' and 'Feature'; filter by 'Bug'.
        Why: Callers need to isolate defect items from feature items.
        """
        bug_item = BacklogItem(title="Login crash", section="P1", skip=False, type_="Bug")
        feature_item = BacklogItem(title="Dark mode", section="P2", skip=False, type_="Feature")
        _seed_items([bug_item, feature_item])
        mocker.patch("backlog_core.operations.batch_fetch_statuses", return_value={})

        result = list_items(type_="Bug")

        items = cast("list[dict[str, str | bool]]", result["items"])
        assert len(items) == 1
        assert items[0]["title"] == "Login crash"

    def test_filter_type_is_case_insensitive(self, mocker: MockerFixture) -> None:
        """type_='bug' matches an item whose metadata.type is 'Bug'.

        Tests: case-insensitive exact match.
        How: Item has type_ 'Bug'; filter with 'bug' (lowercase).
        Why: Type values vary in capitalisation across items; matching must be case-insensitive.
        """
        bug_item = BacklogItem(title="Auth error", section="P0", skip=False, type_="Bug")
        _seed_items([bug_item])
        mocker.patch("backlog_core.operations.batch_fetch_statuses", return_value={})

        result = list_items(type_="bug")

        items = cast("list[dict[str, str | bool]]", result["items"])
        assert len(items) == 1
        assert items[0]["title"] == "Auth error"

    def test_filter_type_excludes_items_without_type(self, mocker: MockerFixture) -> None:
        """Items without metadata.type are excluded when type_ filter is active.

        Tests: absent-type exclusion.
        How: One item has empty item_type in metadata; filter by 'Feature'.
        Why: Items missing metadata.type must not appear in typed-filter results.
        """
        no_type_item = BacklogItem(
            title="Untyped work", section="P2", skip=False, metadata=BacklogItemMetadata(item_type="")
        )
        _seed_items([no_type_item])
        mocker.patch("backlog_core.operations.batch_fetch_statuses", return_value={})

        result = list_items(type_="Feature")

        items = cast("list[dict[str, str | bool]]", result["items"])
        assert items == []

    def test_filter_invalid_type_returns_empty(self, mocker: MockerFixture) -> None:
        """An invalid type value returns empty results with count 0, no error raised.

        Tests: no-match behavior for invalid type.
        How: Items exist but none match the bogus type 'InvalidType'.
        Why: Callers must receive an empty list, not an exception, for unknown types.
        """
        item = BacklogItem(title="Some work", section="P1", skip=False, type_="Feature")
        _seed_items([item])
        mocker.patch("backlog_core.operations.batch_fetch_statuses", return_value={})

        result = list_items(type_="InvalidType")

        items = cast("list[dict[str, str | bool]]", result["items"])
        assert items == []
        assert result["count"] == 0

    def test_no_type_filter_returns_all_items_including_untyped(self, mocker: MockerFixture) -> None:
        """Omitting type_ preserves pre-change behavior — all items returned regardless of type field.

        Tests: backward compatibility.
        How: Items with and without type_; call list_items with no new params.
        Why: Existing callers must not be affected by the addition of type_ filter.
        """
        typed_item = BacklogItem(title="Feature X", section="P1", skip=False, type_="Feature")
        untyped_item = BacklogItem(title="Old item", section="P2", skip=False, type_="")
        _seed_items([typed_item, untyped_item])
        mocker.patch("backlog_core.operations.batch_fetch_statuses", return_value={})

        result = list_items()

        items = cast("list[dict[str, str | bool]]", result["items"])
        assert len(items) == 2


# ---------------------------------------------------------------------------
# list_items: topic filter
# ---------------------------------------------------------------------------


class TestListItemsFilterTopic:
    """list_items(topic=...) filters items by case-insensitive substring match on metadata.topic."""

    def test_filter_topic_returns_matching_items(self, mocker: MockerFixture) -> None:
        """topic='backlog' returns only items whose metadata.topic contains 'backlog'.

        Tests: topic substring filter.
        How: Two items with different topics; filter by 'backlog'.
        Why: Callers need topic-scoped filtering to narrow to a subsystem.
        """
        backlog_item = BacklogItem(title="Backlog sync fix", section="P1", skip=False, topic="backlog-sync-fix")
        auth_item = BacklogItem(title="Auth refactor", section="P1", skip=False, topic="auth-refactor")
        _seed_items([backlog_item, auth_item])
        mocker.patch("backlog_core.operations.batch_fetch_statuses", return_value={})

        result = list_items(topic="backlog")

        items = cast("list[dict[str, str | bool]]", result["items"])
        assert len(items) == 1
        assert items[0]["title"] == "Backlog sync fix"

    def test_filter_topic_is_case_insensitive(self, mocker: MockerFixture) -> None:
        """topic='BACKLOG' matches items whose metadata.topic contains 'backlog'.

        Tests: case-insensitive substring match.
        How: Item topic is lowercase; filter with uppercase.
        Why: Case inconsistency in stored topics must not cause misses.
        """
        item = BacklogItem(title="Backlog work", section="P1", skip=False, topic="backlog-matching")
        _seed_items([item])
        mocker.patch("backlog_core.operations.batch_fetch_statuses", return_value={})

        result = list_items(topic="BACKLOG")

        items = cast("list[dict[str, str | bool]]", result["items"])
        assert len(items) == 1

    def test_filter_topic_excludes_items_without_topic(self, mocker: MockerFixture) -> None:
        """Items without metadata.topic are excluded when topic filter is active.

        Tests: absent-topic exclusion.
        How: One item has no topic; filter by 'backlog'.
        Why: Items missing metadata.topic must not appear in topic-filter results.
        """
        no_topic_item = BacklogItem(title="No topic item", section="P1", skip=False, topic="")
        _seed_items([no_topic_item])
        mocker.patch("backlog_core.operations.batch_fetch_statuses", return_value={})

        result = list_items(topic="backlog")

        items = cast("list[dict[str, str | bool]]", result["items"])
        assert items == []

    def test_no_topic_filter_returns_all_items(self, mocker: MockerFixture) -> None:
        """Omitting topic preserves pre-change behavior — all items returned regardless of topic field.

        Tests: backward compatibility.
        How: Items with and without topic; call list_items with no new params.
        Why: Existing callers must not be affected by the addition of topic filter.
        """
        with_topic = BacklogItem(title="Item A", section="P1", skip=False, topic="some-topic")
        without_topic = BacklogItem(title="Item B", section="P2", skip=False, topic="")
        _seed_items([with_topic, without_topic])
        mocker.patch("backlog_core.operations.batch_fetch_statuses", return_value={})

        result = list_items()

        items = cast("list[dict[str, str | bool]]", result["items"])
        assert len(items) == 2


# ---------------------------------------------------------------------------
# list_items: type_ + topic combined AND logic
# ---------------------------------------------------------------------------


class TestListItemsFilterTypeTopicComposed:
    """list_items(type_=..., topic=...) composes filters with AND logic."""

    def test_combined_type_and_topic_filters_with_and_logic(self, mocker: MockerFixture) -> None:
        """type_='Bug' AND topic='backlog' returns only the item matching both.

        Tests: AND composition of type_ and topic filters.
        How: Three items — bug+backlog, bug+auth, feature+backlog; filter by Bug+backlog.
        Why: Filters must compose with AND to narrow results to intersection.
        """
        bug_backlog = BacklogItem(title="Backlog bug", section="P1", skip=False, type_="Bug", topic="backlog-sync")
        bug_auth = BacklogItem(title="Auth bug", section="P1", skip=False, type_="Bug", topic="auth-fix")
        feature_backlog = BacklogItem(
            title="Backlog feature", section="P2", skip=False, type_="Feature", topic="backlog-ui"
        )
        _seed_items([bug_backlog, bug_auth, feature_backlog])
        mocker.patch("backlog_core.operations.batch_fetch_statuses", return_value={})

        result = list_items(type_="Bug", topic="backlog")

        items = cast("list[dict[str, str | bool]]", result["items"])
        assert len(items) == 1
        assert items[0]["title"] == "Backlog bug"

    def test_section_and_type_filter_compose(self, mocker: MockerFixture) -> None:
        """section='P1' AND type_='Bug' returns only P1 bug items.

        Tests: AND composition of pre-existing section filter with new type_ filter.
        How: P1 bug, P2 bug, P1 feature; filter section=P1, type_=Bug.
        Why: All filters must compose so callers can combine any pair.
        """
        p1_bug = BacklogItem(title="P1 Bug", section="P1", skip=False, type_="Bug")
        p2_bug = BacklogItem(title="P2 Bug", section="P2", skip=False, type_="Bug")
        p1_feature = BacklogItem(title="P1 Feature", section="P1", skip=False, type_="Feature")
        _seed_items([p1_bug, p2_bug, p1_feature])
        mocker.patch("backlog_core.operations.batch_fetch_statuses", return_value={})

        result = list_items(section="P1", type_="Bug")

        items = cast("list[dict[str, str | bool]]", result["items"])
        assert len(items) == 1
        assert items[0]["title"] == "P1 Bug"


# ---------------------------------------------------------------------------
# _build_list_entry: type and topic fields in response dict
# ---------------------------------------------------------------------------


class TestBuildListEntryTypeTopicFields:
    """_build_list_entry includes 'type' and 'topic' fields in the returned dict."""

    def test_build_list_entry_includes_type_and_topic(self, mocker: MockerFixture) -> None:
        """list_items response dicts contain 'type' and 'topic' keys sourced from metadata.

        Tests: type and topic fields in _build_list_entry output.
        How: Create item with type_='Bug' and topic='backlog-matching'; call list_items.
        Why: MCP consumers need type/topic in the response without a separate view call.
        """
        item = BacklogItem(title="Bug fix", section="P1", skip=False, type_="Bug", topic="backlog-matching")
        _seed_items([item])
        mocker.patch("backlog_core.operations.batch_fetch_statuses", return_value={})

        result = list_items()

        items = cast("list[dict[str, str | bool]]", result["items"])
        assert len(items) == 1
        assert items[0]["type"] == "Bug"
        assert items[0]["topic"] == "backlog-matching"

    def test_build_list_entry_type_and_topic_empty_when_absent(self, mocker: MockerFixture) -> None:
        """Items without metadata.type and metadata.topic have empty string values in response dict.

        Tests: empty-field handling in _build_list_entry.
        How: Create item with empty item_type and topic in metadata.
        Why: Consumers must receive consistent dict shape regardless of metadata presence.
        """
        item = BacklogItem(
            title="Plain item", section="P2", skip=False, metadata=BacklogItemMetadata(item_type="", topic="")
        )
        _seed_items([item])
        mocker.patch("backlog_core.operations.batch_fetch_statuses", return_value={})

        result = list_items()

        items = cast("list[dict[str, str | bool]]", result["items"])
        assert len(items) == 1
        assert items[0]["type"] == ""
        assert items[0]["topic"] == ""

    def test_build_list_entry_preserves_groomed_date_string(self, mocker: MockerFixture) -> None:
        """_build_list_entry preserves the groomed date string, not coercing it to True.

        Tests: groomed field propagation in _build_list_entry (regression for #1134).
        How: Create item with groomed="2026-05-24"; call list_items; assert date string preserved.
        Why: Staleness detection needs the actual date for git log --after= comparisons.
             Coercing to bool True silently discards the date, breaking drift detection.
        """
        item = BacklogItem(title="Groomed Item", section="P1", skip=False, groomed="2026-05-24")
        _seed_items([item])
        mocker.patch("backlog_core.operations.batch_fetch_statuses", return_value={})

        result = list_items()

        items = cast("list[dict[str, str | bool]]", result["items"])
        assert len(items) == 1
        assert items[0]["groomed"] == "2026-05-24"
        assert isinstance(items[0]["groomed"], str)


# ---------------------------------------------------------------------------
# _build_item_body: full-text body construction
# ---------------------------------------------------------------------------


class TestBuildItemBody:
    """_build_item_body returns searchable text from description and section entries."""

    def test_build_item_body_includes_description(self, mocker: MockerFixture) -> None:
        """_build_item_body includes item.description in the returned string.

        Tests: description field included in body.
        How: Create BacklogItem with description; call list_items and check body field.
        Why: Body search must find items by description text.
        """
        item = BacklogItem(title="Auth feature", section="P1", skip=False, description="Implements oauth2 token flow")
        _seed_items([item])
        mocker.patch("backlog_core.operations.batch_fetch_statuses", return_value={})

        result = list_items()

        items = cast("list[dict[str, str | bool]]", result["items"])
        assert len(items) == 1
        assert "oauth2 token flow" in str(items[0].get("body", ""))

    def test_build_item_body_includes_section_entries(self, mocker: MockerFixture) -> None:
        """_build_item_body includes Section entry content in the returned string.

        Tests: Section entry text included in body.
        How: Create BacklogItem with a Section containing entries; check body field.
        Why: Acceptance criteria and other section content must be searchable.
        """
        from backlog_core.models import Entry, Section

        entries = [
            Entry(id="20260101T120000", content="Implement sdlc-layers integration"),
            Entry(id="20260101T120001", content="Write unit tests"),
        ]
        item = BacklogItem(
            title="Pipeline task", section="P1", skip=False, sections={"Acceptance Criteria": Section(entries=entries)}
        )
        _seed_items([item])
        mocker.patch("backlog_core.operations.batch_fetch_statuses", return_value={})

        result = list_items()

        items = cast("list[dict[str, str | bool]]", result["items"])
        assert len(items) == 1
        body = str(items[0].get("body", ""))
        assert "sdlc-layers integration" in body
        assert "unit tests" in body

    def test_build_item_body_excludes_struck_entries(self, mocker: MockerFixture) -> None:
        """_build_item_body omits struck (retracted) entry content from the body.

        Tests: struck entries excluded from body.
        How: Create BacklogItem with a struck entry; verify that content is absent from body.
        Why: Struck entries are retracted and must not influence search results.
        """
        from backlog_core.models import Entry, Section

        entries = [
            Entry(
                id="20260101T120000", content="sdlc-layers retracted note", struck=True, struck_at="2026-01-01T12:00:00"
            ),
            Entry(id="20260101T120001", content="active note"),
        ]
        item = BacklogItem(title="Struck test", section="P1", skip=False, sections={"Notes": Section(entries=entries)})
        _seed_items([item])
        mocker.patch("backlog_core.operations.batch_fetch_statuses", return_value={})

        result = list_items()

        items = cast("list[dict[str, str | bool]]", result["items"])
        body = str(items[0].get("body", ""))
        assert "sdlc-layers retracted note" not in body
        assert "active note" in body


# ---------------------------------------------------------------------------
# Entry block integration: groom_item with section+content
# ---------------------------------------------------------------------------


class TestGroomItemEntryBlocks:
    """Tests for entry block wrapping in groom_item."""

    def test_groom_item_appends_entry_block(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """Grooming with section+content creates a timestamped entry block."""
        from backlog_core.models import Output

        mocker.patch("backlog_core.operations.try_get_github", return_value=None)

        import backlog_core.models as _m

        backlog_dir = _m.get_backlog_dir()
        filepath = _write_item(backlog_dir, title="Test Entry Groom", priority="P1", topic="test-entry-groom")

        out = Output()
        result = ops.groom_item(
            selector="Test Entry Groom", section="Decision", content="First decision made.", output=out
        )
        assert "error" not in result

        # save_item auto-migrates .md -> .yaml; read from the migrated path.
        body = _render_item(filepath)
        assert '"entries"' in body
        assert "First decision made." in body

    def test_groom_item_appends_second_entry(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """Grooming twice appends a second entry block, preserving the first."""
        from backlog_core.models import Output

        mocker.patch("backlog_core.operations.try_get_github", return_value=None)

        import backlog_core.models as _m

        backlog_dir = _m.get_backlog_dir()
        # Use .yaml file so parse_backlog() finds the item after the first save_item call
        filepath = _write_item_yaml(backlog_dir, title="Multi Entry", priority="P1", topic="multi-entry")

        out = Output()
        ops.groom_item(selector="Multi Entry", section="Decision", content="First.", output=out)
        ops.groom_item(selector="Multi Entry", section="Decision", content="Second.", output=out)

        body = _render_item(filepath)
        assert "First." in body
        assert "Second." in body
        # P964: two entries appear as two 'content:' lines in the YAML entries list
        assert body.count('"content"') >= 2


# ---------------------------------------------------------------------------
# groom_item append=True: raw-append mode (no entry-block wrapping)
# ---------------------------------------------------------------------------


class TestGroomItemAppend:
    """Tests for append=True parameter on groom_item."""

    def test_groom_item_append_true_first_write_creates_section(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """append=True on a missing section creates the section with the new content.

        Tests: groom_item append=True first write creates section.
        How: Write item with no Concerns section; call groom_item with append=True.
        Why: append=True must still create the section when it does not exist.
        """
        from backlog_core.models import Output

        mocker.patch("backlog_core.operations.try_get_github", return_value=None)

        import backlog_core.models as _m

        backlog_dir = _m.get_backlog_dir()
        filepath = _write_item(backlog_dir, title="Append First", priority="P1", topic="append-first")

        out = Output()
        result = ops.groom_item(
            selector="Append First", section="Concerns", content="First concern.", output=out, append=True
        )
        assert "error" not in result

        # save_item auto-migrates .md -> .yaml; read from the migrated path.
        body = _render_item(filepath)
        assert "First concern." in body
        # No entry-block wrapping when append=True
        assert "<div><sub>" not in body

    def test_groom_item_append_true_second_write_appends_content(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """append=True on an existing section appends new content after existing content.

        Tests: groom_item append=True incremental append preserves existing content.
        How: Call groom_item twice with append=True into the same section.
        Why: implement-feature needs to add individual concern lines incrementally.
        """
        from backlog_core.models import Output

        mocker.patch("backlog_core.operations.try_get_github", return_value=None)

        import backlog_core.models as _m

        backlog_dir = _m.get_backlog_dir()
        # Use .yaml file so parse_backlog() finds the item after the first save_item call
        filepath = _write_item_yaml(backlog_dir, title="Append Multi", priority="P1", topic="append-multi")

        out = Output()
        ops.groom_item(selector="Append Multi", section="Concerns", content="Concern A.", output=out, append=True)
        ops.groom_item(selector="Append Multi", section="Concerns", content="Concern B.", output=out, append=True)

        body = _render_item(filepath)
        assert "Concern A." in body
        assert "Concern B." in body
        # Both concerns must be present — A must appear before B
        assert body.index("Concern A.") < body.index("Concern B.")

    def test_groom_item_append_false_default_uses_entry_blocks(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """append=False (default) continues to wrap content in entry blocks.

        Tests: groom_item append=False default behaviour unchanged.
        How: Call groom_item without append parameter.
        Why: Ensures backward compatibility — existing callers must not be affected.
        """
        from backlog_core.models import Output

        mocker.patch("backlog_core.operations.try_get_github", return_value=None)

        import backlog_core.models as _m

        backlog_dir = _m.get_backlog_dir()
        filepath = _write_item(backlog_dir, title="Append Default", priority="P1", topic="append-default")

        out = Output()
        ops.groom_item(selector="Append Default", section="Decision", content="Default behaviour.", output=out)

        # save_item auto-migrates .md -> .yaml; read from the migrated path.
        body = _render_item(filepath)
        assert "Default behaviour." in body
        # Default (append=False) must still produce P964 YAML entry blocks
        assert '"entries"' in body


# ---------------------------------------------------------------------------
# Entry block integration: strike_entry operation
# ---------------------------------------------------------------------------


class TestStrikeEntryOperation:
    """Tests for the strike_entry public API function."""

    def test_strike_entry_operation(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """strike_entry marks target entry as struck in the P964 YAML format."""
        from backlog_core.models import Output

        mocker.patch("backlog_core.operations.try_get_github", return_value=None)

        import backlog_core.models as _m

        backlog_dir = _m.get_backlog_dir()
        # Use .yaml file so strike_entry's parse_backlog() re-finds the item after groom_item saves it
        filepath = _write_item_yaml(backlog_dir, title="Strike Test", priority="P1", topic="strike-test")

        out = Output()
        ops.groom_item(selector="Strike Test", section="Decision", content="Bad info.", output=out)

        section = cast("Section", next(iter(_stored_item(filepath).sections.values())))
        entry_id = section.entries[0].id

        result = ops.strike_entry(
            selector="Strike Test", entry_id=entry_id, reason="based on training data", output=out
        )
        assert "error" not in result
        assert result["struck"] is True

        body = _render_item(filepath)
        assert '"struck":true' in body
        assert "based on training data" in body

    def test_strike_entry_not_found_raises(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """strike_entry raises ValueError when entry_id doesn't exist."""
        from backlog_core.models import Output

        mocker.patch("backlog_core.operations.try_get_github", return_value=None)

        import backlog_core.models as _m

        backlog_dir = _m.get_backlog_dir()
        _write_item(backlog_dir, title="No Entry", priority="P1", topic="no-entry")

        out = Output()
        with pytest.raises(ValueError, match=r"Entry.*not found"):
            ops.strike_entry(selector="No Entry", entry_id="2099-01-01T00:00:00Z", reason="test", output=out)


# ---------------------------------------------------------------------------
# pull_items — entry-aware merge
# ---------------------------------------------------------------------------


class TestPullItemsEntryAwareMerge:
    def test_pull_dry_run_returns_entry_diff(self) -> None:
        from backlog_core.backend_protocol import get_config

        backend = cast("Any", get_config().backend)
        _seed_items([BacklogItem(title="Diff Item", section="P1", issue="#42", reference="#42")])
        backend.reconcile_result = ReconcileResult(local_updates=1, diffs={"#42": "entry diff"})
        result = ops.pull_items(dry_run=True, diff=True)
        assert result["diff"] == "entry diff"
        assert backend.reconcile_requests[-1] == ReconcileRequest(
            scope=ReconcileScope.LINKED, references=["#42"], dry_run=True, include_diff=True
        )

    def test_pull_entry_aware_merge_keeps_struck(self) -> None:
        baseline = BacklogItem(
            title="Struck Item",
            description="same",
            reference="cache-42",
            metadata=BacklogItemMetadata(priority="P1", status="open", issue="#42"),
        )
        local = baseline.model_copy(deep=True)
        local.metadata.sync_fingerprint = synchronized_fingerprint(baseline)
        local.sections["decision"] = Section(
            entries=[
                Entry(
                    id="2026-08-13T00:00:00Z",
                    content="obsolete",
                    struck=True,
                    struck_reason="superseded",
                    struck_at="2026-08-13T01:00:00Z",
                )
            ]
        )
        remote = baseline.model_copy(deep=True)
        remote.sections["decision"] = Section(entries=[Entry(id="2026-08-13T00:00:00Z", content="obsolete")])
        provider = ProviderItem(
            provider_id="node-42",
            reference="#42",
            title="Struck Item",
            body=render_issue_body(remote),
            state="OPEN",
            labels=[],
            revision="rev-2",
        )

        plan = _provider_plan(local, provider)

        merged = cast("Section", plan.cache_actions[0].record.item.sections["decision"])
        assert [(entry.content, entry.struck, entry.struck_reason) for entry in merged.entries] == [
            ("obsolete", True, "superseded")
        ]


class TestPullItemsResilienceToFetchErrors:
    def test_pull_continues_past_404_and_reports_skipped(self) -> None:
        from backlog_core.backend_protocol import get_config

        backend = cast("Any", get_config().backend)
        _seed_items([
            BacklogItem(title="Good", section="P1", issue="#10", reference="#10"),
            BacklogItem(title="Missing", section="P1", issue="#11", reference="#11"),
        ])
        backend.reconcile_result = ReconcileResult(local_updates=1, failures=1)
        result = ops.pull_items()
        assert (result["pulled"], result["skipped"], result["total"]) == (1, 1, 2)

    def test_pull_all_failed_reports_zero_pulled(self) -> None:
        from backlog_core.backend_protocol import get_config

        backend = cast("Any", get_config().backend)
        _seed_items([BacklogItem(title="Missing", section="P1", issue="#11", reference="#11")])
        backend.reconcile_result = ReconcileResult(failures=1)
        result = ops.pull_items()
        assert (result["pulled"], result["skipped"]) == (0, 1)


class TestRefreshClosedIssueReconciliation:
    def test_refresh_fetches_closed_issues(self) -> None:
        baseline = BacklogItem(
            title="Closed Item",
            description="before",
            reference="cache-50",
            metadata=BacklogItemMetadata(priority="P1", status="open", issue="#50"),
        )
        local = baseline.model_copy(deep=True)
        local.metadata.sync_fingerprint = synchronized_fingerprint(baseline)
        remote = baseline.model_copy(deep=True)
        remote.description = "provider completion record"
        provider = ProviderItem(
            provider_id="node-50",
            reference="#50",
            title="Closed Item",
            body=render_issue_body(remote),
            state="CLOSED",
            labels=[],
            revision="rev-closed",
        )

        plan = _provider_plan(local, provider)

        reconciled = plan.cache_actions[-1].record.item
        assert (reconciled.metadata.status, reconciled.description) == ("closed", "provider completion record")

    def test_refresh_updates_local_status_for_closed(self) -> None:
        local = BacklogItem(
            title="Terminal Item",
            description="preserve local evidence",
            reference="cache-51",
            metadata=BacklogItemMetadata(priority="P1", status="open", issue="#51"),
        )
        provider = ProviderItem(
            provider_id="node-51",
            reference="#51",
            title="Terminal Item",
            body=render_issue_body(local),
            state="CLOSED",
            labels=["status:done"],
            revision="rev-closed",
        )

        plan = _provider_plan(local, provider)

        reconciled = plan.cache_actions[-1].record.item
        assert reconciled.metadata.status == "closed"
        assert reconciled.description == "preserve local evidence"

    def test_refresh_skips_already_terminal(self) -> None:
        from backlog_core.backend_protocol import get_config

        backend = cast("Any", get_config().backend)
        _seed_items([BacklogItem(title="Done", section="P1", issue="#60", status="done", reference="#60")])
        refresh_local_cache_from_github()
        assert backend.reconcile_requests[-1].references == ["#60"]

    def test_refresh_open_takes_precedence(self) -> None:
        from backlog_core.backend_protocol import get_config

        backend = cast("Any", get_config().backend)
        backend.reconcile_result = ReconcileResult(local_updates=1, no_ops=1)
        result = refresh_local_cache_from_github()
        assert (result["refreshed"], result["reconciled"]) == (1, 0)

    def test_refresh_no_local_file_for_closed(self) -> None:
        local = BacklogItem(
            title="Deleted Provider Item",
            description="retain investigation evidence",
            reference="cache-52",
            metadata=BacklogItemMetadata(priority="P1", status="closed", issue="#52"),
        )
        provider = ProviderItem(
            provider_id="node-52",
            reference="#52",
            title="Deleted Provider Item",
            body="",
            state="CLOSED",
            labels=[],
            revision="rev-deleted",
            exists=False,
        )

        plan = _provider_plan(local, provider)

        unlinked = plan.cache_actions[0].record.item
        assert (unlinked.reference, unlinked.metadata.issue, unlinked.metadata.status) == ("cache-52", "", "closed")
        assert unlinked.description == "retain investigation evidence"


class TestRefreshLocalCacheIncrementalSync:
    def test_refresh_local_cache_skips_full_fetch_when_last_sync_exists(self) -> None:
        from backlog_core.backend_protocol import get_config

        backend = cast("Any", get_config().backend)
        refresh_local_cache_from_github()
        assert backend.reconcile_requests[-1].scope == ReconcileScope.INCREMENTAL

    def test_refresh_local_cache_does_full_fetch_when_no_last_sync(self) -> None:
        from backlog_core.backend_protocol import get_config

        backend = cast("Any", get_config().backend)
        refresh_local_cache_from_github(full_refresh=True)
        assert backend.reconcile_requests[-1].scope == ReconcileScope.INITIAL

    def test_refresh_local_cache_full_refresh_ignores_last_sync(self) -> None:
        from backlog_core.backend_protocol import get_config

        backend = cast("Any", get_config().backend)
        refresh_local_cache_from_github(full_refresh=True)
        assert backend.reconcile_requests == [ReconcileRequest(scope=ReconcileScope.INITIAL)]


class TestSyncIncrementalParseBacklogCallCount:
    def test_parse_backlog_called_once_for_multiple_closed_issues(self) -> None:
        from backlog_core.backend_protocol import get_config

        backend = cast("Any", get_config().backend)
        _seed_items([
            BacklogItem(title="One", section="P1", issue="#1", reference="#1"),
            BacklogItem(title="Two", section="P1", issue="#2", reference="#2"),
            BacklogItem(title="Three", section="P1", issue="#3", reference="#3"),
        ])
        refresh_local_cache_from_github()
        assert backend.reconcile_requests == [
            ReconcileRequest(scope=ReconcileScope.INCREMENTAL, references=["#1", "#2", "#3"])
        ]


class TestGroomItemMarkGroomed:
    """Tests for mark_groomed parameter on groom_item (Tests 3-7 from architecture spec)."""

    def test_groom_item_mark_groomed_updates_local_status(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """mark_groomed=True sets local frontmatter status to 'groomed' when item has no issue.

        Tests: groom_item mark_groomed updates local frontmatter status.
        How: Write item with no issue; call groom_item with mark_groomed=True.
        Why: Local status must advance even when there is no GitHub issue to label.
        """
        import backlog_core.models as _m
        from backlog_core.models import Output

        mocker.patch("backlog_core.operations.try_get_github", return_value=None)

        backlog_dir = _m.get_backlog_dir()
        # Use .yaml file so parse_backlog() re-finds the item after save_item converts it
        filepath = _write_item_yaml(backlog_dir, title="Mark Groomed Local", priority="P1", topic="mark-groomed-local")

        out = Output()
        result = ops.groom_item(
            selector="Mark Groomed Local",
            section="Description",
            content="Groomed content.",
            output=out,
            mark_groomed=True,
        )

        assert "error" not in result
        assert result.get("mark_groomed_applied") is True
        body = _render_item(filepath)
        assert '"status":"groomed"' in body

    def test_groom_item_mark_groomed_manages_github_labels(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """mark_groomed=True delegates GitHub label update to apply_status_groomed.

        Tests: groom_item mark_groomed calls apply_status_groomed when item has an issue.
        How: Write item with issue #123; mock apply_status_groomed; call with mark_groomed=True.
        Why: GitHub label transition must be routed to the dedicated function, not implemented inline.
        """
        import backlog_core.models as _m
        from backlog_core.models import Output

        mocker.patch("backlog_core.operations.try_get_github", return_value=None)
        mock_apply = mocker.patch("backlog_core.operations.apply_status_groomed")

        backlog_dir = _m.get_backlog_dir()
        # Use .yaml file so parse_backlog() re-finds the item after save_item converts it
        _write_item_yaml(
            backlog_dir, title="Mark Groomed Github", priority="P1", topic="mark-groomed-github", issue="#123"
        )

        out = Output()
        result = ops.groom_item(
            selector="Mark Groomed Github",
            section="Description",
            content="Groomed with issue.",
            output=out,
            mark_groomed=True,
        )

        assert "error" not in result
        mock_apply.assert_called_once()
        called_item = mock_apply.call_args.args[0]
        assert called_item.issue == "#123"

    def test_groom_item_mark_groomed_false_no_status_change(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """mark_groomed=False (default) does not advance status or call apply_status_groomed.

        Tests: groom_item mark_groomed=False preserves existing behavior unchanged.
        How: Write item with issue; call groom_item with mark_groomed=False.
        Why: Default False must not silently advance status on every groom call.
        """
        import backlog_core.models as _m
        from backlog_core.models import Output

        mocker.patch("backlog_core.operations.try_get_github", return_value=None)
        mock_apply = mocker.patch("backlog_core.operations.apply_status_groomed")

        backlog_dir = _m.get_backlog_dir()
        filepath = _write_item(
            backlog_dir, title="Mark Groomed False", priority="P1", topic="mark-groomed-false", issue="#456"
        )

        out = Output()
        result = ops.groom_item(
            selector="Mark Groomed False",
            section="Description",
            content="No status change expected.",
            output=out,
            mark_groomed=False,
        )

        assert "error" not in result
        mock_apply.assert_not_called()
        assert result.get("mark_groomed_applied") is not True
        # save_item auto-migrates .md -> .yaml; read from the migrated path.
        body = _render_item(filepath)
        assert "status: groomed" not in body

    def test_groom_item_mark_groomed_with_batch_sections(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """mark_groomed=True fires exactly once after batch sections are written.

        Tests: groom_item mark_groomed integrates correctly with sections batch parameter.
        How: Write item with issue; call with sections dict and mark_groomed=True.
        Why: mark_groomed must execute once at the end, not once per section.
        """
        import backlog_core.models as _m
        from backlog_core.models import Output

        mocker.patch("backlog_core.operations.try_get_github", return_value=None)
        mock_apply = mocker.patch("backlog_core.operations.apply_status_groomed")

        backlog_dir = _m.get_backlog_dir()
        # Use .yaml file so parse_backlog() re-finds the item after save_item converts it
        _write_item_yaml(
            backlog_dir, title="Mark Groomed Batch", priority="P1", topic="mark-groomed-batch", issue="#789"
        )

        out = Output()
        result = ops.groom_item(
            selector="Mark Groomed Batch",
            sections={"Effort": "S", "Acceptance Criteria": "All criteria met."},
            output=out,
            mark_groomed=True,
        )

        assert "error" not in result
        assert result.get("mark_groomed_applied") is True
        mock_apply.assert_called_once()

    def test_groom_item_mark_groomed_skipped_on_error(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """mark_groomed is not applied when update_item returns an error.

        Tests: groom_item mark_groomed skips status advance if content write fails.
        How: Mock update_item to return error dict; call with mark_groomed=True.
        Why: Status must not advance if the grooming write did not succeed.
        """
        import backlog_core.models as _m
        from backlog_core.models import Output

        mocker.patch("backlog_core.operations.try_get_github", return_value=None)
        mocker.patch("backlog_core.operations.update_item", return_value={"error": "some error"})
        mock_apply = mocker.patch("backlog_core.operations.apply_status_groomed")

        backlog_dir = _m.get_backlog_dir()
        filepath = _write_item(
            backlog_dir, title="Mark Groomed Error", priority="P1", topic="mark-groomed-error", issue="#999"
        )

        out = Output()
        result = ops.groom_item(
            selector="Mark Groomed Error",
            section="Description",
            content="This write will fail.",
            output=out,
            mark_groomed=True,
        )

        assert "error" in result
        mock_apply.assert_not_called()
        assert result.get("mark_groomed_applied") is not True
        body = _render_item(filepath)
        assert "status: groomed" not in body


# ---------------------------------------------------------------------------
# view_item: unknown section keys survive into ViewItemResult.sections
# ---------------------------------------------------------------------------


class TestViewItemUnknownSections:
    """Unknown section keys (unknown__ prefix) survive through view_item into ViewItemResult.sections.

    These tests prove that `_build_sections_from_yaml_item` preserves freeform
    `unknown__` prefixed keys — produced by `parse_issue_body` from GitHub issue
    body headings not in `_HEADING_TO_KEY` — when assembling `ViewItemResult.sections`.
    """

    def test_unknown_section_key_present_in_view_result_sections(self, mocker: MockerFixture) -> None:
        """Unknown-prefixed section key survives through view_item into ViewItemResult.sections.

        Tests: _build_sections_from_yaml_item does not filter out unknown__ keys.
        How: Write a YAML item with an unknown__impact_radius section; call view_item;
             assert the key is present in result.sections.
        Why: MCP clients receive result.sections as JSON — unknown section keys must
             appear in the output or downstream consumers silently lose issue body content.
        """
        import backlog_core.models as _m
        from backlog_core.models import Entry, Section

        mocker.patch("backlog_core.operations.view_enrich_from_github", return_value=False)

        backlog_dir = _m.get_backlog_dir()
        filepath = backlog_dir / "p1-unknown-section-item.yaml"

        metadata = _m.BacklogItemMetadata(
            source="test", added="2026-01-01", priority="P1", status="open", topic="unknown-section-item"
        )
        item = _m.BacklogItem(
            title="Unknown Section Item",
            description="Test item with unknown sections",
            metadata=metadata,
            file_path=str(filepath),
            sections={
                "unknown__impact_radius": Section(
                    entries=[
                        Entry(id="20260101T120000", content="Affects authentication module"),
                        Entry(id="20260101T120001", content="No downstream impact expected"),
                    ]
                )
            },
        )
        _seed_items([item])

        # Act
        result = view_item("Unknown Section Item")

        # Assert
        assert isinstance(result, ViewItemResult)
        assert "unknown__impact_radius" in result.sections, (
            f"Expected 'unknown__impact_radius' in sections, got: {list(result.sections.keys())}"
        )
        # Confirm value shape is SectionEntryMetadata (not groomed)
        section_meta = cast("SectionEntryMetadata", result.sections["unknown__impact_radius"])
        assert "num_entries" in section_meta

    def test_unknown_section_has_correct_section_entry_metadata_shape(self, mocker: MockerFixture) -> None:
        """Unknown section value has SectionEntryMetadata shape with num_entries, num_struck, entries.

        Tests: _build_sections_from_yaml_item wraps Section objects in SectionEntryMetadata.
        How: Write YAML item with unknown__ section; call view_item; assert TypedDict shape.
        Why: MCP clients read num_entries and entries — wrong shape breaks consumers.
        """
        import backlog_core.models as _m
        from backlog_core.models import Entry, Section

        mocker.patch("backlog_core.operations.view_enrich_from_github", return_value=False)

        backlog_dir = _m.get_backlog_dir()
        filepath = backlog_dir / "p1-unknown-shape-item.yaml"

        metadata = _m.BacklogItemMetadata(
            source="test", added="2026-01-01", priority="P1", status="open", topic="unknown-shape-item"
        )
        item = _m.BacklogItem(
            title="Unknown Shape Item",
            description="Test shape of unknown sections",
            metadata=metadata,
            file_path=str(filepath),
            sections={
                "unknown__story": Section(entries=[Entry(id="20260101T130000", content="As a developer I want tests")])
            },
        )
        _seed_items([item])

        # Act
        result = view_item("Unknown Shape Item")

        # Assert
        section_meta = cast("SectionEntryMetadata", result.sections["unknown__story"])
        assert "num_entries" in section_meta
        assert "num_struck" in section_meta
        assert "entries" in section_meta
        assert isinstance(section_meta["entries"], list)

    def test_unknown_section_entry_content_is_preserved(self, mocker: MockerFixture) -> None:
        """Entry content inside an unknown section is not lost in ViewItemResult.sections.

        Tests: Entry content round-trips from BacklogItem.sections into ViewItemResult.sections.
        How: Write YAML item with known entry content in unknown__ section; call view_item;
             assert entry content matches.
        Why: Silent content loss would cause MCP clients to display empty section entries.
        """
        import backlog_core.models as _m
        from backlog_core.models import Entry, Section

        mocker.patch("backlog_core.operations.view_enrich_from_github", return_value=False)

        backlog_dir = _m.get_backlog_dir()
        filepath = backlog_dir / "p1-unknown-content-item.yaml"

        expected_content = "Must handle rate limits gracefully"
        metadata = _m.BacklogItemMetadata(
            source="test", added="2026-01-01", priority="P1", status="open", topic="unknown-content-item"
        )
        item = _m.BacklogItem(
            title="Unknown Content Item",
            description="Test content preservation",
            metadata=metadata,
            file_path=str(filepath),
            sections={
                "unknown__acceptance_criteria": Section(
                    entries=[
                        Entry(id="20260101T140000", content=expected_content),
                        Entry(id="20260101T140001", content="Must log errors to stderr"),
                    ]
                )
            },
        )
        _seed_items([item])

        # Act
        result = view_item("Unknown Content Item")

        # Assert
        section_meta = cast("SectionEntryMetadata", result.sections["unknown__acceptance_criteria"])
        section_entries = section_meta["entries"]
        contents = [e["content"] for e in section_entries]
        assert expected_content in contents, f"Expected '{expected_content}' in entry contents, got: {contents}"
        assert len(section_entries) == 2

    def test_unknown_section_num_entries_matches_active_entry_count(self, mocker: MockerFixture) -> None:
        """num_entries in unknown section metadata equals the count of non-struck entries.

        Tests: active/struck entry counting for unknown__ prefixed keys.
        How: Write item with 3 entries, 1 struck; assert num_entries=2, num_struck=1.
        Why: MCP clients display entry counts — must be accurate regardless of key prefix.
        """
        import backlog_core.models as _m
        from backlog_core.models import Entry, Section

        mocker.patch("backlog_core.operations.view_enrich_from_github", return_value=False)

        backlog_dir = _m.get_backlog_dir()
        filepath = backlog_dir / "p1-unknown-count-item.yaml"

        metadata = _m.BacklogItemMetadata(
            source="test", added="2026-01-01", priority="P1", status="open", topic="unknown-count-item"
        )
        item = _m.BacklogItem(
            title="Unknown Count Item",
            description="Test entry counting",
            metadata=metadata,
            file_path=str(filepath),
            sections={
                "unknown__notes": Section(
                    entries=[
                        Entry(id="20260101T150000", content="Active note one"),
                        Entry(id="20260101T150001", content="Active note two"),
                        Entry(
                            id="20260101T150002", content="Struck note", struck=True, struck_at="2026-01-02T00:00:00Z"
                        ),
                    ]
                )
            },
        )
        _seed_items([item])

        # Act
        result = view_item("Unknown Count Item")

        # Assert
        section_meta = cast("SectionEntryMetadata", result.sections["unknown__notes"])
        assert section_meta["num_entries"] == 2
        assert section_meta["num_struck"] == 1

    def test_unknown_section_coexists_with_known_section(self, mocker: MockerFixture) -> None:
        """Unknown and known sections coexist in ViewItemResult.sections with correct shapes.

        Tests: _build_sections_from_yaml_item preserves both known and unknown__ keys simultaneously.
        How: Write YAML item with rt_ica (known) and unknown__story sections; call view_item;
             assert both keys present with correct SectionEntryMetadata shapes.
        Why: Real GitHub issues have mixed headings — known and unknown must both survive.
        """
        import backlog_core.models as _m
        from backlog_core.models import Entry, Section

        mocker.patch("backlog_core.operations.view_enrich_from_github", return_value=False)

        backlog_dir = _m.get_backlog_dir()
        filepath = backlog_dir / "p1-mixed-sections-item.yaml"

        metadata = _m.BacklogItemMetadata(
            source="test", added="2026-01-01", priority="P1", status="open", topic="mixed-sections-item"
        )
        item = _m.BacklogItem(
            title="Mixed Sections Item",
            description="Test mixed known and unknown sections",
            metadata=metadata,
            file_path=str(filepath),
            sections={
                "rt_ica": Section(entries=[Entry(id="20260101T160000", content="Risk: breaking change in public API")]),
                "unknown__story": Section(entries=[Entry(id="20260101T160001", content="As a user I want feature X")]),
            },
        )
        _seed_items([item])

        # Act
        result = view_item("Mixed Sections Item")

        # Assert
        assert "rt_ica" in result.sections, f"Expected 'rt_ica' in sections, got: {list(result.sections.keys())}"
        assert "unknown__story" in result.sections, (
            f"Expected 'unknown__story' in sections, got: {list(result.sections.keys())}"
        )
        rt_ica_meta = cast("SectionEntryMetadata", result.sections["rt_ica"])
        assert rt_ica_meta["num_entries"] == 1
        assert rt_ica_meta["entries"][0]["content"] == "Risk: breaking change in public API"

        story_meta = cast("SectionEntryMetadata", result.sections["unknown__story"])
        assert story_meta["num_entries"] == 1
        assert story_meta["entries"][0]["content"] == "As a user I want feature X"

    def test_unknown_section_coexists_with_groomed_section(self, mocker: MockerFixture) -> None:
        """Unknown section and groomed section coexist with their respective metadata shapes.

        Tests: SectionEntryMetadata and GroomedSectionMetadata shapes both appear in sections.
        How: Write YAML item with groomed (GroomedData) and unknown__ (Section) keys; call view_item;
             assert groomed key has type=groomed and unknown key has num_entries shape.
        Why: GroomedSectionMetadata and SectionEntryMetadata are discriminated by presence of
             the "type" key — MCP clients must receive both shapes correctly.
        """
        import backlog_core.models as _m
        from backlog_core.models import Entry, GroomedData, Section

        mocker.patch("backlog_core.operations.view_enrich_from_github", return_value=False)

        backlog_dir = _m.get_backlog_dir()
        filepath = backlog_dir / "p1-groomed-unknown-item.yaml"

        metadata = _m.BacklogItemMetadata(
            source="test", added="2026-01-01", priority="P1", status="open", topic="groomed-unknown-item"
        )
        item = _m.BacklogItem(
            title="Groomed Unknown Item",
            description="Test groomed alongside unknown",
            metadata=metadata,
            file_path=str(filepath),
            sections={
                "groomed": GroomedData(date="2026-01-15", subsections={"summary": "Feature is ready for review"}),
                "unknown__implementation_notes": Section(
                    entries=[
                        Entry(id="20260101T170000", content="Use existing retry logic"),
                        Entry(id="20260101T170001", content="Avoid touching auth module"),
                    ]
                ),
            },
        )
        _seed_items([item])

        # Act
        result = view_item("Groomed Unknown Item")

        # Assert: groomed section has GroomedSectionMetadata shape
        assert "groomed" in result.sections, f"Expected 'groomed' in sections, got: {list(result.sections.keys())}"
        groomed_meta = cast("GroomedSectionMetadata", result.sections["groomed"])
        assert groomed_meta.get("type") == "groomed"
        assert "subsections" in groomed_meta
        assert groomed_meta["subsections"]["summary"] == "Feature is ready for review"

        # Assert: unknown section has SectionEntryMetadata shape
        assert "unknown__implementation_notes" in result.sections, (
            f"Expected 'unknown__implementation_notes' in sections, got: {list(result.sections.keys())}"
        )
        unknown_meta = cast("SectionEntryMetadata", result.sections["unknown__implementation_notes"])
        assert "num_entries" in unknown_meta
        assert unknown_meta["num_entries"] == 2
        assert len(unknown_meta["entries"]) == 2


# ---------------------------------------------------------------------------
# _rename_item_title — beads nanoid safe-skip (issue #2665)
# ---------------------------------------------------------------------------


class TestRenameItemTitleBeadsNanoid:
    """_rename_item_title skips GitHub title update for beads nanoid issue refs."""

    def test_rename_item_title_skips_github_for_beads_nanoid(self, mocker: MockerFixture) -> None:
        """_rename_item_title with a beads nanoid issue_ref returns without raising.

        Tests: _rename_item_title early-return path for string-ID backends.
        How: Configure a BeadsBackend (issue_id_type='string'); write an item with
             issue='bd-a3f8'; call update_item(title=); verify no exception is raised,
             the local file is renamed, and try_get_github is NOT called.
        Why: String-ID backends (e.g. beads) use nanoids, not GitHub issue numbers.
             The fix adds an issue_id_type guard before try_get_github, so no GitHub
             sync is attempted — the local update completes cleanly. try_get_github
             is mocked and asserted not-called (rather than relying on
             _update_issue_graphql not being reached) because an empty default_repo
             in this test's config makes an unmocked try_get_github return None on
             its own, which would let this test pass even if the guard were removed.
        """

        import backlog_core.models as models
        from backlog_core.backend_protocol import reset_config, set_config
        from backlog_core.backend_types import BacklogConfig
        from backlog_core.operations import update_item

        beads_backend = InMemoryBackend()
        beads_backend.issue_id_type = "string"
        set_config(BacklogConfig(backend=beads_backend))

        try:
            fake_dir: Path = models.get_backlog_dir()
            _write_item(fake_dir, title="Beads Title Item", topic="beads-title-item", issue="bd-a3f8")

            mock_try_get_github = mocker.patch("backlog_core.operations.try_get_github")
            mock_update_issue = mocker.patch("backlog_core.operations._update_issue_graphql")

            result = update_item(selector="Beads Title Item", title="Beads Title Renamed")

            assert result.get("renamed_to") == "Beads Title Renamed"
            mock_try_get_github.assert_not_called()
            mock_update_issue.assert_not_called()
        finally:
            reset_config()


# ---------------------------------------------------------------------------
# _apply_plan_to_item — beads nanoid safe-skip (issue #2665)
# ---------------------------------------------------------------------------


class TestApplyPlanToItemBeadsNanoid:
    """_apply_plan_to_item skips GitHub plan comment for beads nanoid issue refs."""

    def test_apply_plan_to_item_skips_github_for_beads_nanoid(self, mocker: MockerFixture) -> None:
        """_apply_plan_to_item with a beads nanoid issue_ref returns without raising.

        Tests: _apply_plan_to_item early-return path for string-ID backends.
        How: Configure a BeadsBackend (issue_id_type='string'); write an item with
             issue='bd-c9d1'; call update_item(plan=); verify no exception is raised,
             and _add_comment_graphql is NOT called.
        Why: String-ID backends (e.g. beads) use nanoids, not GitHub issue numbers.
             The fix adds an issue_id_type guard before try_get_github, so no GitHub
             plan comment is attempted — the local update completes cleanly. try_get_github
             is mocked and asserted not-called (rather than relying on
             _add_comment_graphql not being reached) because an empty default_repo
             in this test's config makes an unmocked try_get_github return None on
             its own, which would let this test pass even if the guard were removed.
        """

        import backlog_core.models as models
        from backlog_core.backend_protocol import reset_config, set_config
        from backlog_core.backend_types import BacklogConfig
        from backlog_core.operations import update_item

        beads_backend = InMemoryBackend()
        beads_backend.issue_id_type = "string"
        set_config(BacklogConfig(backend=beads_backend))

        try:
            fake_dir: Path = models.get_backlog_dir()
            _write_item(fake_dir, title="Beads Plan Item", topic="beads-plan-item", issue="bd-c9d1")

            mock_try_get_github = mocker.patch("backlog_core.operations.try_get_github")
            mock_add_comment = mocker.patch("backlog_core.operations._add_comment_graphql")

            result = update_item(selector="Beads Plan Item", plan="plan/tasks-beads.yaml")

            assert result.get("errors", []) == []
            mock_try_get_github.assert_not_called()
            mock_add_comment.assert_not_called()
        finally:
            reset_config()


class TestPlanAssociationBeadsNanoid:
    def test_plan_association_does_not_publish_artifact_for_beads_nanoid(self, mocker: MockerFixture) -> None:
        import backlog_core.models as models
        from backlog_core.backend_protocol import reset_config, set_config
        from backlog_core.backend_types import BacklogConfig
        from backlog_core.operations import update_item

        beads_backend = InMemoryBackend()
        beads_backend.issue_id_type = "string"
        set_config(BacklogConfig(backend=beads_backend))

        try:
            fake_dir: Path = models.get_backlog_dir()
            _write_item(fake_dir, title="Beads Artifact Item", topic="beads-artifact-item", issue="bd-f7a2")

            mocker.patch("backlog_core.operations.try_get_github")
            mocker.patch("backlog_core.operations._add_comment_graphql")
            mock_put_content = mocker.patch.object(beads_backend, "put_content", wraps=beads_backend.put_content)

            result = update_item(selector="Beads Artifact Item", plan="plan/tasks-beads-artifact.yaml")

            raw_warnings = result.get("warnings")
            warnings_text = " ".join(raw_warnings) if isinstance(raw_warnings, list) else ""
            assert "Could not parse issue number" not in warnings_text
            mock_put_content.assert_not_called()
        finally:
            reset_config()


# ---------------------------------------------------------------------------
# backlog_view — beads nanoid uncached (issue #2664)
# ---------------------------------------------------------------------------


class TestViewItemBeadsNanoidUncached:
    """backlog_view routes to view_enrich_from_github for uncached beads nanoid selectors."""

    def test_view_item_beads_nanoid_uncached_calls_enrich(self, mocker: MockerFixture) -> None:
        """backlog_view calls view_enrich_from_github for an uncached beads nanoid selector.

        Tests: backlog_view string-ID backend fallback path.
        How: Configure a BeadsBackend (issue_id_type='string'); write NO local item;
             mock view_enrich_from_github to return True; call view_item with nanoid.
        Why: parse_issue_selector returns None for beads nanoids, so the original
             if issue_num: gate was never entered — enrichment was never attempted for
             uncached items. The fix adds a fallback branch for string-ID backends.
        """

        from backlog_core.backend_protocol import reset_config, set_config
        from backlog_core.backend_types import BacklogConfig
        from backlog_core.backends.bd_runner import BdRunner
        from backlog_core.backends.beads_backend import BeadsBackend

        mock_runner = MagicMock(spec=BdRunner)
        mock_runner.is_available.return_value = True
        beads_backend = BeadsBackend(runner=mock_runner)
        set_config(BacklogConfig(backend=beads_backend))

        mock_enrich = mocker.patch("backlog_core.operations.view_enrich_from_github", return_value=True)

        try:
            view_item("bd-e2f4")
        finally:
            reset_config()

        mock_enrich.assert_called_once()
        selector_arg = mock_enrich.call_args.args[1]
        assert selector_arg == "bd-e2f4"

    def test_view_item_beads_nanoid_uncached_raises_when_enrich_fails(self, mocker: MockerFixture) -> None:
        """backlog_view raises ItemNotFoundError when view_enrich_from_github returns False.

        Tests: backlog_view string-ID backend fallback — enrichment failure path.
        How: Configure BeadsBackend; mock view_enrich_from_github to return False;
             call view_item with a beads nanoid; expect ItemNotFoundError.
        Why: If the backend cannot find the item either, ItemNotFoundError is the
             correct outcome — the selector resolves to nothing.
        """

        from backlog_core.backend_protocol import reset_config, set_config
        from backlog_core.backend_types import BacklogConfig
        from backlog_core.backends.bd_runner import BdRunner
        from backlog_core.backends.beads_backend import BeadsBackend

        mock_runner = MagicMock(spec=BdRunner)
        mock_runner.is_available.return_value = True
        beads_backend = BeadsBackend(runner=mock_runner)
        set_config(BacklogConfig(backend=beads_backend))

        mocker.patch("backlog_core.operations.view_enrich_from_github", return_value=False)

        try:
            with pytest.raises(ItemNotFoundError):
                view_item("bd-g3h5")
        finally:
            reset_config()

    def test_view_item_github_backend_unknown_nanoid_still_raises(self, mocker: MockerFixture) -> None:
        """backlog_view with a GitHub backend raises ItemNotFoundError for a beads-style selector.

        Tests: backlog_view non-string-ID backend — unchanged behavior.
        How: Default config (GitHub backend, issue_id_type='integer'); mock
             view_enrich_from_github to return False; call view_item with a beads nanoid.
        Why: The fallback path must only activate for string-ID backends. GitHub users
             passing nonsense selectors should still get ItemNotFoundError.
        """
        mocker.patch("backlog_core.operations.view_enrich_from_github", return_value=False)

        with pytest.raises(ItemNotFoundError):
            view_item("bd-h4i6")

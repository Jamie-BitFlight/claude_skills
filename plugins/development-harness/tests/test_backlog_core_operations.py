"""Tests for backlog_core/operations.py public API functions.

Covers add_item, list_items, view_item, close_item, and resolve_item.
All GitHub calls are mocked at the boundary.  File-system isolation is provided
by an autouse fixture that redirects BACKLOG_DIR to tmp_path.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import backlog_core.models as _bc_models
import backlog_core.operations as ops
import pytest
from backlog_core.models import (
    BacklogConfig,
    BacklogItem,
    BacklogItemMetadata,
    DuplicateItemError,
    GroomedSectionMetadata,
    IssueStatus,
    ItemNotFoundError,
    Output,
    PullRequestRef,
    SectionEntryMetadata,
    ValidationError,
    ViewItemResult,
)
from backlog_core.operations import add_item, close_item, list_items, resolve_item, view_item

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
    """Write a minimal per-item backlog file and return its path."""
    slug = topic
    filename = f"{priority.lower()}-{slug}.md"
    filepath = backlog_dir / filename
    status = "done" if skip else "open"
    content = _MINIMAL_FRONTMATTER.format(title=title, priority=priority, topic=topic, issue=issue).replace(
        "  status: open", f"  status: {status}"
    )
    if extra_body:
        content = content.rstrip() + "\n\n" + extra_body + "\n"
    filepath.write_text(content, encoding="utf-8")
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
    """Write a minimal per-item backlog file in P964 YAML format and return its path.

    Uses .yaml extension so parse_backlog() reads it via the YAML path after
    save_item() converts it during the first groom call.  Required for tests
    that call groom_item more than once on the same item.
    """
    from backlog_core.models import BacklogItem, BacklogItemMetadata
    from backlog_core.yaml_io import save_item

    slug = topic
    filename = f"{priority.lower()}-{slug}.yaml"
    filepath = backlog_dir / filename
    status = "done" if skip else "open"
    metadata = BacklogItemMetadata(
        source="test", added="2026-01-01", priority=priority, status=status, issue=issue, topic=topic
    )
    item = BacklogItem(title=title, description="A test item", metadata=metadata, file_path=str(filepath))
    save_item(item, filepath)
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

        import backlog_core.models as models

        fake_dir: Path = models.get_backlog_dir()
        result = add_item(title="My New Feature", description="Does something useful", priority="P1")

        files = list(fake_dir.glob("*.yaml"))
        assert len(files) == 1
        assert result["file_path"] == str(files[0])

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

        filepath = Path(str(result["file_path"]))
        text = filepath.read_text(encoding="utf-8")
        assert "Frontmatter Title Test" in text

    def test_add_item_always_calls_github(self, mocker: MockerFixture) -> None:
        """Verify add_item always attempts GitHub issue creation via try_get_github.

        Tests: add_item always-create-issue invariant.
        How: Patch try_get_github returning None; assert it was called.
        Why: GitHub Issues is the source of truth — every item must have an issue.
        """
        mock_try_gh = mocker.patch("backlog_core.operations.try_get_github", return_value=None)

        add_item(title="Local Only Item", description="desc", priority="P2")

        mock_try_gh.assert_called_once()

    def test_add_item_calls_github_and_returns_issue_num(self, mocker: MockerFixture) -> None:
        """Verify add_item calls try_get_github and returns issue_num on success.

        Tests: add_item GH-first integration path.
        How: Patch try_get_github to return a mock repo, verify it was called.
        Why: GH-first design requires GitHub to be contacted before local file write.
        """
        mock_repo = mocker.Mock()
        mocker.patch("backlog_core.operations.try_get_github", return_value=mock_repo)
        mocker.patch("backlog_core.operations.create_issue_for_item", return_value=42)

        result = add_item(title="GH First Item", description="desc", priority="P1")

        assert result.get("issue_num") == 42

    def test_add_item_returns_issue_num_from_github(self, mocker: MockerFixture) -> None:
        """Verify add_item return dict includes issue_num when GitHub issue is created.

        Tests: add_item issue_num in return value.
        How: Mock create_issue_for_item to return 99.
        Why: Callers display the issue number to confirm GH-first creation.
        """
        mock_repo = mocker.Mock()
        mocker.patch("backlog_core.operations.try_get_github", return_value=mock_repo)
        mocker.patch("backlog_core.operations.create_issue_for_item", return_value=99)

        result = add_item(title="Issue Num Item", description="desc", priority="P1")

        assert result["issue_num"] == 99

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
        mocker.patch("backlog_core.operations.parse_backlog", return_value=[active, done])
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
        mocker.patch("backlog_core.operations.parse_backlog", return_value=[item_with_issue])
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
        item_with_issue = BacklogItem(title="PR Blocked Close", section="P1", issue="#5", file_path=str(filepath))
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
        item_with_issue = BacklogItem(title="Force Close Item", section="P1", issue="#6", file_path=str(filepath))
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
        item_with_issue = BacklogItem(title="PR Blocked Resolve", section="P1", issue="#8", file_path=str(filepath))
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
        item_with_issue = BacklogItem(title="Force Resolve Item", section="P1", issue="#9", file_path=str(filepath))
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
        files = list(fake_dir.glob("*.md"))
        assert len(files) == 1
        text = files[0].read_text(encoding="utf-8")
        assert "New Title" in text

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
        item_files = list(fake_dir.glob("*.md"))
        assert item_files, "No item file found"
        text = item_files[0].read_text(encoding="utf-8")
        assert "Still No Issue Item" in text

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
        files = list(fake_dir.glob("*.md"))
        assert len(files) == 1
        text = files[0].read_text(encoding="utf-8")
        assert "Updated description text." in text

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
        mocker.patch("backlog_core.operations.parse_backlog", return_value=[p0_item, p1_item])
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
        mocker.patch("backlog_core.operations.parse_backlog", return_value=[p1_item])
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
        mocker.patch("backlog_core.operations.parse_backlog", return_value=[p0_item])
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
        mocker.patch("backlog_core.operations.parse_backlog", return_value=[p0_item, p2_item])
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
        mocker.patch("backlog_core.operations.parse_backlog", return_value=[auth_item, other_item])
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
        mocker.patch("backlog_core.operations.parse_backlog", return_value=[auth_item])
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
        mocker.patch("backlog_core.operations.parse_backlog", return_value=[item])
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
        mocker.patch("backlog_core.operations.parse_backlog", return_value=[in_progress_item, idle_item])
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
        mocker.patch("backlog_core.operations.parse_backlog", return_value=[no_issue_item])
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
        mocker.patch("backlog_core.operations.parse_backlog", return_value=[done_item])
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
        mocker.patch("backlog_core.operations.parse_backlog", return_value=[bug_item, feature_item])
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
        mocker.patch("backlog_core.operations.parse_backlog", return_value=[bug_item])
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
        mocker.patch("backlog_core.operations.parse_backlog", return_value=[no_type_item])
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
        mocker.patch("backlog_core.operations.parse_backlog", return_value=[item])
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
        mocker.patch("backlog_core.operations.parse_backlog", return_value=[typed_item, untyped_item])
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
        mocker.patch("backlog_core.operations.parse_backlog", return_value=[backlog_item, auth_item])
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
        mocker.patch("backlog_core.operations.parse_backlog", return_value=[item])
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
        mocker.patch("backlog_core.operations.parse_backlog", return_value=[no_topic_item])
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
        mocker.patch("backlog_core.operations.parse_backlog", return_value=[with_topic, without_topic])
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
        mocker.patch("backlog_core.operations.parse_backlog", return_value=[bug_backlog, bug_auth, feature_backlog])
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
        mocker.patch("backlog_core.operations.parse_backlog", return_value=[p1_bug, p2_bug, p1_feature])
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
        mocker.patch("backlog_core.operations.parse_backlog", return_value=[item])
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
        mocker.patch("backlog_core.operations.parse_backlog", return_value=[item])
        mocker.patch("backlog_core.operations.batch_fetch_statuses", return_value={})

        result = list_items()

        items = cast("list[dict[str, str | bool]]", result["items"])
        assert len(items) == 1
        assert items[0]["type"] == ""
        assert items[0]["topic"] == ""


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
        mocker.patch("backlog_core.operations.parse_backlog", return_value=[item])
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
        mocker.patch("backlog_core.operations.parse_backlog", return_value=[item])
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
        mocker.patch("backlog_core.operations.parse_backlog", return_value=[item])
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
        body = filepath.with_suffix(".yaml").read_text(encoding="utf-8")
        assert "entries:" in body
        assert "content: First decision made." in body

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

        body = filepath.read_text(encoding="utf-8")
        assert "First." in body
        assert "Second." in body
        # P964: two entries appear as two 'content:' lines in the YAML entries list
        assert body.count("content:") >= 2


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
        body = filepath.with_suffix(".yaml").read_text(encoding="utf-8")
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

        body = filepath.read_text(encoding="utf-8")
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
        body = filepath.with_suffix(".yaml").read_text(encoding="utf-8")
        assert "Default behaviour." in body
        # Default (append=False) must still produce P964 YAML entry blocks
        assert "entries:" in body


# ---------------------------------------------------------------------------
# Entry block integration: strike_entry operation
# ---------------------------------------------------------------------------


class TestStrikeEntryOperation:
    """Tests for the strike_entry public API function."""

    def test_strike_entry_operation(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """strike_entry marks target entry as struck in the P964 YAML format."""
        import re as re_mod

        from backlog_core.models import Output

        mocker.patch("backlog_core.operations.try_get_github", return_value=None)

        import backlog_core.models as _m

        backlog_dir = _m.get_backlog_dir()
        # Use .yaml file so strike_entry's parse_backlog() re-finds the item after groom_item saves it
        filepath = _write_item_yaml(backlog_dir, title="Strike Test", priority="P1", topic="strike-test")

        out = Output()
        ops.groom_item(selector="Strike Test", section="Decision", content="Bad info.", output=out)

        # P964: entry ID is stored as a YAML field — extract via id: '<value>'
        body = filepath.read_text(encoding="utf-8")
        match = re_mod.search(r"id: '([^']+)'", body)
        assert match is not None, f"No entry id found in YAML body: {body!r}"
        entry_id = match.group(1)

        result = ops.strike_entry(
            selector="Strike Test", entry_id=entry_id, reason="based on training data", output=out
        )
        assert "error" not in result
        assert result["struck"] is True

        body = filepath.read_text(encoding="utf-8")
        assert "struck: true" in body
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
    """pull_items uses entry-aware merge and supports diff output."""

    def test_pull_dry_run_returns_entry_diff(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """pull with dry_run and diff=True returns entry-level diff string.

        Tests: pull_items entry-aware merge with diff output.
        How: Set up local item with one entry, mock GitHub with two entries, call pull_items.
        Why: Validates that generate_diff is wired into the pull merge path.
        """
        import backlog_core.models as _m
        from backlog_core.models import Output

        backlog_dir = _m.get_backlog_dir()

        local_entry = "<div><sub>2026-01-01T00:00:00Z</sub>\n\nLocal content\n</div>"
        _write_item(
            backlog_dir,
            title="Diff Item",
            priority="P1",
            topic="diff-item",
            issue="#42",
            extra_body=f"## Description\n\n{local_entry}",
        )

        remote_entry_1 = "<div><sub>2026-01-01T00:00:00Z</sub>\n\nLocal content\n</div>"
        remote_entry_2 = "<div><sub>2026-02-01T00:00:00Z</sub>\n\nRemote new content\n</div>"
        remote_body = f"## Description\n\n{remote_entry_1}\n\n{remote_entry_2}"

        mocker.patch(
            "backlog_core.operations.parse_backlog",
            return_value=[
                BacklogItem(
                    title="Diff Item", section="P1", issue="#42", file_path=str(backlog_dir / "p1-diff-item.md")
                )
            ],
        )
        mocker.patch("backlog_core.operations.sync_create_missing_issues")
        mock_repo = mocker.MagicMock()
        mocker.patch("backlog_core.operations.get_github", return_value=mock_repo)
        mocker.patch("backlog_core.operations.fetch_github_issue_body", return_value=remote_body)

        out = Output()
        result = ops.pull_items(dry_run=True, diff=True, output=out)

        assert "diff" in result
        assert isinstance(result["diff"], str)
        assert "+" in result["diff"]  # new remote entry shows as addition

    def test_pull_entry_aware_merge_keeps_struck(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """Entry-aware merge keeps struck entries over active ones.

        Tests: Merge rule — both sides, one struck -> keep struck.
        How: Local has struck entry, remote has active version, merge should keep struck.
        Why: Struck entries represent deliberate user action and must be preserved.
        """
        import backlog_core.models as _m
        from backlog_core.models import Output

        backlog_dir = _m.get_backlog_dir()

        struck_entry = (
            "<div><sub>2026-01-01T00:00:00Z</sub>\n"
            "<details><summary>struck: 2026-01-15T00:00:00Z — outdated</summary>\n\n"
            "Old content\n</details>\n</div>"
        )
        _write_item(
            backlog_dir,
            title="Struck Item",
            priority="P1",
            topic="struck-item",
            issue="#43",
            extra_body=f"## Description\n\n{struck_entry}",
        )

        active_entry = "<div><sub>2026-01-01T00:00:00Z</sub>\n\nOld content\n</div>"
        remote_body = f"## Description\n\n{active_entry}"

        filepath = backlog_dir / "p1-struck-item.md"
        mocker.patch(
            "backlog_core.operations.parse_backlog",
            return_value=[BacklogItem(title="Struck Item", section="P1", issue="#43", file_path=str(filepath))],
        )
        mocker.patch("backlog_core.operations.sync_create_missing_issues")
        mock_repo = mocker.MagicMock()
        mocker.patch("backlog_core.operations.get_github", return_value=mock_repo)
        mocker.patch("backlog_core.operations.fetch_github_issue_body", return_value=remote_body)

        out = Output()
        ops.pull_items(dry_run=False, force=False, output=out)

        body = filepath.read_text(encoding="utf-8")
        assert "struck:" in body
        assert "outdated" in body


# ---------------------------------------------------------------------------
# pull_items — resilience to per-item fetch failures
# ---------------------------------------------------------------------------


class TestPullItemsResilienceToFetchErrors:
    """pull_items continues past per-item fetch failures and reports skipped count."""

    def test_pull_continues_past_404_and_reports_skipped(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """pull_items skips 404 items and still processes the rest.

        Tests: pull_items resilience — single 404 does not abort the batch.
        How: Two items; first fetch returns None (simulating 404), second returns body.
             Verify pulled=1, skipped=1, total=2, and errors is non-empty.
        Why: A deleted or transferred issue must not halt a 427-item bulk pull.
        """
        import backlog_core.models as _m

        backlog_dir = _m.get_backlog_dir()

        good_body = "## Description\n\nSome content"
        filepath = backlog_dir / "p1-good-item.md"

        _write_item(backlog_dir, title="Good Item", priority="P1", topic="good-item", issue="#10")

        mocker.patch(
            "backlog_core.operations.parse_backlog",
            return_value=[
                BacklogItem(title="Dead Issue", section="P1", issue="#404"),
                BacklogItem(title="Good Item", section="P1", issue="#10", file_path=str(filepath)),
            ],
        )
        mocker.patch("backlog_core.operations.sync_create_missing_issues")
        mock_repo = mocker.MagicMock()
        mocker.patch("backlog_core.operations.get_github", return_value=mock_repo)
        # First call returns None (404 simulation), second returns a body
        mocker.patch("backlog_core.operations.fetch_github_issue_body", side_effect=[None, good_body])

        out = Output()
        result = ops.pull_items(output=out)

        assert result["total"] == 2
        assert result["skipped"] == 1
        assert result["pulled"] == 1
        assert len(out.errors) == 1
        assert "404" in out.errors[0] or "skipped" in out.errors[0]

    def test_pull_all_failed_reports_zero_pulled(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """pull_items with all fetches failing reports pulled=0 and all items skipped.

        Tests: All-failure scenario — pulled=0, skipped=total.
        How: Two items, both fetches return None.
        Why: Validates correct accounting when entire batch fails.
        """
        mocker.patch(
            "backlog_core.operations.parse_backlog",
            return_value=[
                BacklogItem(title="Gone 1", section="P1", issue="#1"),
                BacklogItem(title="Gone 2", section="P1", issue="#2"),
            ],
        )
        mocker.patch("backlog_core.operations.sync_create_missing_issues")
        mock_repo = mocker.MagicMock()
        mocker.patch("backlog_core.operations.get_github", return_value=mock_repo)
        mocker.patch("backlog_core.operations.fetch_github_issue_body", return_value=None)

        out = Output()
        result = ops.pull_items(output=out)

        assert result["total"] == 2
        assert result["skipped"] == 2
        assert result["pulled"] == 0
        assert len(out.errors) == 2


# ---------------------------------------------------------------------------
# refresh_local_cache_from_github — closed-issue reconciliation
# ---------------------------------------------------------------------------


class TestRefreshClosedIssueReconciliation:
    """refresh_local_cache_from_github reconciles externally closed GitHub issues."""

    def test_refresh_fetches_closed_issues(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Bulk GraphQL fetch is called for both open and closed states during refresh.

        Tests: sync_issues_graphql is invoked with state='CLOSED' during refresh.
        How: Mock sync_issues_graphql; call refresh; verify it was called with
             state='CLOSED' at least once.
        Why: Without fetching closed issues, local cache drifts from GitHub state.
             After T01 the bulk fetch uses sync_issues_graphql (GraphQL), not
             repo.get_issues (REST).
        """
        # Arrange
        # Use the BACKLOG_DIR already redirected by the autouse _isolate_backlog_dir fixture.

        mock_repo = mocker.MagicMock()
        mock_repo.full_name = "owner/repo"
        mocker.patch("backlog_core.operations.try_get_github", return_value=mock_repo)
        mock_fetch = mocker.patch("backlog_core.operations.sync_issues_graphql", return_value=[])

        out = Output()

        # Act
        ops.refresh_local_cache_from_github(output=out)

        # Assert — sync_issues_graphql called at least once with state="CLOSED"
        calls = mock_fetch.call_args_list
        closed_calls = [
            c for c in calls if c.kwargs.get("state") == "CLOSED" or (len(c.args) >= 4 and c.args[3] == "CLOSED")
        ]
        assert len(closed_calls) >= 1, f"Expected at least one sync_issues_graphql(state='CLOSED') call, got: {calls}"

    def test_refresh_updates_local_status_for_closed(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Local file updated to status=closed when GitHub issue is closed.

        Tests: reconciliation updates local cache for closed issues.
        How: Create local item with open status and issue #50; mock
             sync_issues_graphql to return a closed issue node; verify local
             file status changes to closed.
        Why: Local files must reflect GitHub state to prevent stale displays.
             After T01 the bulk fetch uses sync_issues_graphql (GraphQL), not
             repo.get_issues (REST). Node dicts use camelCase GraphQL field names.
        """
        # Arrange
        import backlog_core.models as models

        # Use the BACKLOG_DIR already redirected by the autouse _isolate_backlog_dir fixture.
        fake_dir = models.get_backlog_dir()

        filepath = _write_item(fake_dir, title="Closable Item", issue="#50", topic="closable-item")

        mock_repo = mocker.MagicMock()
        mock_repo.full_name = "owner/repo"
        mocker.patch("backlog_core.operations.try_get_github", return_value=mock_repo)

        closed_node = {
            "number": 50,
            "title": "Closable Item",
            "state": "CLOSED",
            "closedAt": "2099-01-01T00:00:00+00:00",  # far future — always within cutoff
            "isPullRequest": False,
            "id": "node-50",
        }

        def _fake_fetch(repo_obj, owner, repo_name, state, labels=None):
            if state == "CLOSED":
                return [closed_node]
            return []  # no open issues

        mocker.patch("backlog_core.operations.sync_issues_graphql", side_effect=_fake_fetch)

        out = Output()

        # Act
        result = ops.refresh_local_cache_from_github(output=out)

        # Assert
        assert isinstance(result["reconciled"], int)
        assert result["reconciled"] >= 1
        updated_content = filepath.read_text(encoding="utf-8")
        assert "status: closed" in updated_content

    def test_refresh_skips_already_terminal(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Items already in terminal status (done/resolved/closed) are not modified.

        Tests: terminal status guard in reconciliation.
        How: Create item with status=done and matching closed issue; mock
             sync_issues_graphql to return the closed issue node; verify no update.
        Why: Re-processing terminal items wastes I/O and may corrupt metadata.
             After T01 the bulk fetch uses sync_issues_graphql (GraphQL), not
             repo.get_issues (REST).
        """
        # Arrange
        import backlog_core.models as models

        # Use the BACKLOG_DIR already redirected by the autouse _isolate_backlog_dir fixture.
        fake_dir = models.get_backlog_dir()

        filepath = _write_item(fake_dir, title="Already Done", issue="#60", topic="already-done", skip=True)
        original_content = filepath.read_text(encoding="utf-8")

        mock_repo = mocker.MagicMock()
        mock_repo.full_name = "owner/repo"
        mocker.patch("backlog_core.operations.try_get_github", return_value=mock_repo)

        closed_node = {
            "number": 60,
            "title": "Already Done",
            "state": "CLOSED",
            "closedAt": "2099-01-01T00:00:00+00:00",
            "isPullRequest": False,
            "id": "node-60",
        }

        def _fake_fetch(repo_obj, owner, repo_name, state, labels=None):
            if state == "CLOSED":
                return [closed_node]
            return []

        mocker.patch("backlog_core.operations.sync_issues_graphql", side_effect=_fake_fetch)

        out = Output()

        # Act
        result = ops.refresh_local_cache_from_github(output=out)

        # Assert — reconciled count should be 0 (terminal item skipped)
        assert result["reconciled"] == 0
        # File content unchanged
        assert filepath.read_text(encoding="utf-8") == original_content

    def test_refresh_open_takes_precedence(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Issue appearing in both open and closed sets is treated as open.

        Tests: open-takes-precedence rule in reconciliation.
        How: Mock sync_issues_graphql to return issue #70 in both OPEN and CLOSED
             passes; verify reconciled count is 0.
        Why: GitHub may return recently-reopened issues in both state sets.
             After T01 the bulk fetch uses sync_issues_graphql (GraphQL), not
             repo.get_issues (REST). open_issue_numbers set prevents reconciliation
             of issues that appeared in the open pass.
        """
        # Arrange
        import backlog_core.models as models

        # Use the BACKLOG_DIR already redirected by the autouse _isolate_backlog_dir fixture.
        fake_dir = models.get_backlog_dir()

        _write_item(fake_dir, title="Ambiguous Item", issue="#70", topic="ambiguous-item")

        mock_repo = mocker.MagicMock()
        mock_repo.full_name = "owner/repo"
        mocker.patch("backlog_core.operations.try_get_github", return_value=mock_repo)

        open_node = {
            "number": 70,
            "title": "Ambiguous Item",
            "state": "OPEN",
            "closedAt": None,
            "isPullRequest": False,
            "id": "node-70",
        }
        closed_node = {
            "number": 70,
            "title": "Ambiguous Item",
            "state": "CLOSED",
            "closedAt": "2099-01-01T00:00:00+00:00",
            "isPullRequest": False,
            "id": "node-70",
        }

        def _fake_fetch(repo_obj, owner, repo_name, state, labels=None):
            if state == "CLOSED":
                return [closed_node]
            return [open_node]

        mocker.patch("backlog_core.operations.sync_issues_graphql", side_effect=_fake_fetch)
        mocker.patch("backlog_core.operations._write_issue_node_to_cache")

        out = Output()

        # Act
        result = ops.refresh_local_cache_from_github(output=out)

        # Assert — open takes precedence, so not reconciled as closed
        assert result["reconciled"] == 0

    def test_refresh_no_local_file_for_closed(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """Closed issue with no matching local file causes no error.

        Tests: graceful skip when closed issue has no local counterpart.
        How: Mock sync_issues_graphql to return closed issue #80 with no
             corresponding local file; verify no crash and reconciled=0.
        Why: Not all GitHub issues have local backlog files — must skip silently.
             After T01 the bulk fetch uses sync_issues_graphql (GraphQL), not
             repo.get_issues (REST).
        """
        # Arrange — autouse _isolate_backlog_dir redirects BACKLOG_DIR; no local files written.
        mock_repo = mocker.MagicMock()
        mock_repo.full_name = "owner/repo"
        mocker.patch("backlog_core.operations.try_get_github", return_value=mock_repo)

        closed_node = {
            "number": 80,
            "title": "Orphan Issue",
            "state": "CLOSED",
            "closedAt": "2099-01-01T00:00:00+00:00",
            "isPullRequest": False,
            "id": "node-80",
        }

        def _fake_fetch(repo_obj, owner, repo_name, state, labels=None):
            if state == "CLOSED":
                return [closed_node]
            return []

        mocker.patch("backlog_core.operations.sync_issues_graphql", side_effect=_fake_fetch)

        out = Output()

        # Act — should not raise
        result = ops.refresh_local_cache_from_github(output=out)

        # Assert
        assert result["reconciled"] == 0


# ---------------------------------------------------------------------------
# refresh_local_cache_from_github — incremental sync (.last_sync)
# ---------------------------------------------------------------------------


class TestRefreshLocalCacheIncrementalSync:
    """refresh_local_cache_from_github uses .last_sync for incremental fetches."""

    def test_refresh_local_cache_skips_full_fetch_when_last_sync_exists(
        self, mocker: MockerFixture, tmp_path: pytest.TempPathFactory
    ) -> None:
        """Incremental path passes since= when .last_sync timestamp file exists.

        Tests: refresh_local_cache_from_github incremental sync path.
        How: Write a .last_sync file via dh_paths.state_root(); patch
             sync_issues_graphql; verify it is called with since=<timestamp>.
        Why: Without incremental sync, every refresh fetches all issues regardless
             of whether anything changed since the last run.
        """
        # Arrange
        import dh_paths

        state_dir = dh_paths.state_root()
        state_dir.mkdir(parents=True, exist_ok=True)
        ts = "2026-01-15T12:00:00+00:00"
        (state_dir / ".last_sync").write_text(ts, encoding="utf-8")

        mock_repo = mocker.MagicMock()
        mock_repo.full_name = "owner/repo"
        mocker.patch("backlog_core.operations.try_get_github", return_value=mock_repo)

        fetch_mock = mocker.patch("backlog_core.operations.sync_issues_graphql", return_value=[])

        # Act
        ops.refresh_local_cache_from_github()

        # Assert — incremental call uses since= and combined states
        # Production code converts the ISO string from .last_sync to a datetime
        # before passing it to sync_issues_graphql, so compare as datetime.
        fetch_mock.assert_called_once()
        _, kwargs = fetch_mock.call_args
        assert kwargs.get("since") == datetime.fromisoformat(ts)

    def test_refresh_local_cache_does_full_fetch_when_no_last_sync(self, mocker: MockerFixture) -> None:
        """Full two-pass fetch is performed when no .last_sync file exists.

        Tests: refresh_local_cache_from_github full-refresh fallback.
        How: Ensure .last_sync does not exist; verify sync_issues_graphql
             is called with since=None (full-fetch signature).
        Why: First run or after cache wipe must fetch all issues.
        """
        # Arrange — autouse fixture sets DH_STATE_HOME; .last_sync absent by default
        import dh_paths

        last_sync_path = dh_paths.state_root() / ".last_sync"
        assert not last_sync_path.exists(), "Precondition: .last_sync must not exist"

        mock_repo = mocker.MagicMock()
        mock_repo.full_name = "owner/repo"
        mocker.patch("backlog_core.operations.try_get_github", return_value=mock_repo)

        calls: list[dict] = []

        def _capture_fetch(
            repo_obj: object,
            owner: object,
            repo_name: object,
            state: object,
            labels: object = None,
            since: object = None,
            **kw: object,
        ) -> list[object]:
            calls.append({"state": state, "since": since})
            return []

        mocker.patch("backlog_core.operations.sync_issues_graphql", side_effect=_capture_fetch)
        mocker.patch("backlog_core.operations._reconcile_closed_issues", return_value=0)

        # Act
        ops.refresh_local_cache_from_github()

        # Assert — full path issues two separate state calls, both with since=None
        assert len(calls) >= 1
        for call in calls:
            assert call["since"] is None

    def test_refresh_local_cache_full_refresh_ignores_last_sync(self, mocker: MockerFixture) -> None:
        """full_refresh=True bypasses .last_sync and performs a full two-pass fetch.

        Tests: refresh_local_cache_from_github full_refresh=True flag.
        How: Write a .last_sync file, call with full_refresh=True, verify
             sync_issues_graphql is called with since=None.
        Why: Operators must be able to force a complete resync regardless of
             the cached timestamp.
        """
        # Arrange
        import dh_paths

        state_dir = dh_paths.state_root()
        state_dir.mkdir(parents=True, exist_ok=True)
        (state_dir / ".last_sync").write_text("2026-01-01T00:00:00+00:00", encoding="utf-8")

        mock_repo = mocker.MagicMock()
        mock_repo.full_name = "owner/repo"
        mocker.patch("backlog_core.operations.try_get_github", return_value=mock_repo)

        calls: list[dict] = []

        def _capture_fetch(
            repo_obj: object,
            owner: object,
            repo_name: object,
            state: object,
            labels: object = None,
            since: object = None,
            **kw: object,
        ) -> list[object]:
            calls.append({"state": state, "since": since})
            return []

        mocker.patch("backlog_core.operations.sync_issues_graphql", side_effect=_capture_fetch)
        mocker.patch("backlog_core.operations._reconcile_closed_issues", return_value=0)

        # Act
        ops.refresh_local_cache_from_github(full_refresh=True)

        # Assert — all calls must have since=None (full refresh ignores timestamp)
        assert len(calls) >= 1
        for call in calls:
            assert call["since"] is None


# ---------------------------------------------------------------------------
# _sync_incremental — parse_backlog call-count invariant (O(N+M) fix)
# ---------------------------------------------------------------------------


class TestSyncIncrementalParseBacklogCallCount:
    """_sync_incremental calls parse_backlog exactly once regardless of closed-issue count.

    Regression guard for the O(N*M) → O(N+M) fix: parse_backlog must be called
    once before the reconciliation loop, not once per closed issue encountered.
    """

    def test_parse_backlog_called_once_for_multiple_closed_issues(self, mocker: MockerFixture) -> None:
        """parse_backlog is called exactly once when reconciling 3+ closed issues.

        Tests: O(N+M) invariant — parse_backlog must not be called per-issue.
        How: Set up a .last_sync file so the incremental path is taken; write
             3 local backlog items with issue refs; mock sync_issues_graphql to
             return all 3 as CLOSED; spy on parse_backlog; call
             refresh_local_cache_from_github; assert call_count == 1.
        Why: Before the fix, _reconcile_single_closed_issue called parse_backlog()
             internally on each invocation, producing O(N*M) filesystem reads.
             The fix builds the index once in _sync_incremental before the loop.
             A call_count > 1 means the regression has been reintroduced.
        """
        # Arrange — write 3 local items with distinct issue refs
        import backlog_core.models as models
        import dh_paths

        fake_dir = models.get_backlog_dir()
        _write_item(fake_dir, title="Item Alpha", issue="#101", topic="item-alpha", priority="P1")
        _write_item(fake_dir, title="Item Beta", issue="#102", topic="item-beta", priority="P1")
        _write_item(fake_dir, title="Item Gamma", issue="#103", topic="item-gamma", priority="P1")

        # Write a .last_sync file so refresh_local_cache_from_github takes
        # the incremental path (_sync_incremental) rather than _sync_full.
        state_dir = dh_paths.state_root()
        state_dir.mkdir(parents=True, exist_ok=True)
        (state_dir / ".last_sync").write_text("2026-01-01T00:00:00+00:00", encoding="utf-8")

        mock_repo = mocker.MagicMock()
        mock_repo.full_name = "owner/repo"
        mocker.patch("backlog_core.operations.try_get_github", return_value=mock_repo)

        # Return all 3 issues as CLOSED in the single OPEN,CLOSED combined fetch
        closed_nodes = [
            {
                "number": 101,
                "title": "Item Alpha",
                "state": "CLOSED",
                "closedAt": "2099-01-01T00:00:00+00:00",
                "isPullRequest": False,
                "id": "node-101",
            },
            {
                "number": 102,
                "title": "Item Beta",
                "state": "CLOSED",
                "closedAt": "2099-01-01T00:00:00+00:00",
                "isPullRequest": False,
                "id": "node-102",
            },
            {
                "number": 103,
                "title": "Item Gamma",
                "state": "CLOSED",
                "closedAt": "2099-01-01T00:00:00+00:00",
                "isPullRequest": False,
                "id": "node-103",
            },
        ]
        mocker.patch("backlog_core.operations.sync_issues_graphql", return_value=closed_nodes)

        # Spy on parse_backlog — let the real implementation run so reconciliation
        # actually writes files, but count how many times it is invoked.
        from backlog_core.parsing import parse_backlog as _real_parse_backlog

        parse_backlog_spy = mocker.patch("backlog_core.operations.parse_backlog", side_effect=_real_parse_backlog)

        out = Output()

        # Act
        result = ops.refresh_local_cache_from_github(output=out)

        # Assert — parse_backlog called exactly once, not once per closed issue
        assert parse_backlog_spy.call_count == 1, (
            f"parse_backlog was called {parse_backlog_spy.call_count} time(s); "
            f"expected exactly 1. A call count > 1 indicates _reconcile_single_closed_issue "
            f"is calling parse_backlog() per iteration (O(N*M) regression)."
        )
        # Sanity-check: the 3 closed issues were actually reconciled
        assert result["reconciled"] == 3


# ---------------------------------------------------------------------------
# groom_item mark_groomed parameter
# ---------------------------------------------------------------------------


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
        body = filepath.read_text(encoding="utf-8")
        assert "status: groomed" in body

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
        body = filepath.with_suffix(".yaml").read_text(encoding="utf-8")
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
        body = filepath.read_text(encoding="utf-8")
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
        from backlog_core.yaml_io import save_item

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
        save_item(item, filepath)

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
        from backlog_core.yaml_io import save_item

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
        save_item(item, filepath)

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
        from backlog_core.yaml_io import save_item

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
        save_item(item, filepath)

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
        from backlog_core.yaml_io import save_item

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
        save_item(item, filepath)

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
        from backlog_core.yaml_io import save_item

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
        save_item(item, filepath)

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
        from backlog_core.yaml_io import save_item

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
        save_item(item, filepath)

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

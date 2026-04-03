"""Tests for batch section writes in backlog_core/operations.py.

Covers _handle_batch_groomed (Phase 1 local writes, Phase 2 GitHub sync),
update_item(sections=...), and groom_item(sections=...).

All GitHub calls are mocked at the operations.py boundary.
File-system isolation is provided by an autouse fixture that redirects
BACKLOG_DIR to tmp_path.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import backlog_core.models as models
import backlog_core.operations as ops
import pytest
from backlog_core.models import BacklogConfig, BacklogError, BacklogItem, Output

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MINIMAL_FRONTMATTER = """\
---
name: {title}
description: A test item
metadata:
  priority: P1
  status: open
  source: test
  added: '2026-01-01'
  type: Feature
  topic: {topic}
  issue: '{issue}'
---
"""


def _write_item_file(
    directory: Path, *, title: str = "Batch Test Item", topic: str = "batch-test-item", issue: str = ""
) -> Path:
    """Write a minimal per-item file and return its path."""
    filepath = directory / f"p1-{topic}.md"
    content = _MINIMAL_FRONTMATTER.format(title=title, topic=topic, issue=issue)
    filepath.write_text(content, encoding="utf-8")
    return filepath


def _backlog_dir() -> Path:
    """Return the current (monkeypatched) BACKLOG_DIR."""
    return models.get_backlog_dir()


# ---------------------------------------------------------------------------
# Autouse fixture: filesystem isolation
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolate_backlog_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Redirect BACKLOG_DIR to tmp_path for test isolation.

    Tests: File-system isolation for all backlog operations.
    How: Sets DH_STATE_HOME and patches backlog_core.models.BACKLOG_DIR.
    Why: Prevents tests from reading or writing the real backlog directory.
    """
    import dh_paths

    monkeypatch.setenv("DH_STATE_HOME", str(tmp_path / "dh_state"))

    fake_project_root = tmp_path / "project"
    fake_project_root.mkdir(parents=True, exist_ok=True)

    fake_dir = dh_paths.backlog_dir(project_root=fake_project_root)
    fake_dir.mkdir(parents=True, exist_ok=True)

    existing = models._config
    monkeypatch.setattr(
        models,
        "_config",
        BacklogConfig(
            repo_root=fake_project_root,
            backlog_dir=fake_dir,
            default_repo=existing.default_repo if existing is not None else "",
        ),
    )


# ---------------------------------------------------------------------------
# _handle_batch_groomed: Phase 1 — local writes
# ---------------------------------------------------------------------------


class TestHandleBatchGroomedLocalWrites:
    """_handle_batch_groomed writes each section to the local file."""

    def test_raises_when_item_has_no_file_path(self) -> None:
        """Verify BacklogError is raised when item.file_path is empty.

        Tests: _handle_batch_groomed precondition guard.
        How: Construct BacklogItem without file_path; call _handle_batch_groomed.
        Why: Every caller must supply a file-backed item — raising early prevents
             silent data loss.
        """
        item = BacklogItem(title="No File Item")
        with pytest.raises(BacklogError, match="no file path"):
            ops._handle_batch_groomed(item, {"Plan": "Some content."}, repo="owner/repo")

    def test_returns_list_of_written_section_names(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """Verify the return value lists all section names that were written.

        Tests: _handle_batch_groomed return value shape.
        How: Call with two sections; inspect the returned list.
        Why: Callers use the returned list to populate sections_written in the
             response dict.
        """
        mocker.patch("backlog_core.operations.try_get_github", return_value=None)
        filepath = _write_item_file(tmp_path, title="Return Shape", topic="return-shape")
        item = BacklogItem(title="Return Shape", file_path=str(filepath), added="2026-01-01")

        result = ops._handle_batch_groomed(item, {"Plan": "Content A.", "Research": "Content B."}, repo="owner/repo")

        assert result == ["Plan", "Research"]

    def test_single_section_written_to_file_body(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """Verify a single-section batch writes content into the item file.

        Tests: _handle_batch_groomed single-entry dict.
        How: Write item file; call with one section; read file back.
        Why: Single-section batch is a valid degenerate case that must produce output.
        """
        mocker.patch("backlog_core.operations.try_get_github", return_value=None)
        filepath = _write_item_file(tmp_path, title="Single Section", topic="single-section")
        item = BacklogItem(title="Single Section", file_path=str(filepath), added="2026-01-01")

        ops._handle_batch_groomed(item, {"Plan": "Single plan content."}, repo="owner/repo")

        # save_item auto-migrates .md -> .yaml; read from the migrated path.
        content = filepath.with_suffix(".yaml").read_text(encoding="utf-8")
        assert "Single plan content." in content

    def test_multiple_sections_all_appear_in_file(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """Verify every section in the batch is written to the local file.

        Tests: _handle_batch_groomed multi-section write loop.
        How: Write item file; call with three sections; verify all content in file.
        Why: All sections must be persisted locally before any GitHub sync starts.
        """
        mocker.patch("backlog_core.operations.try_get_github", return_value=None)
        filepath = _write_item_file(tmp_path, title="Multi Section", topic="multi-section")
        item = BacklogItem(title="Multi Section", file_path=str(filepath), added="2026-01-01")

        ops._handle_batch_groomed(
            item,
            {"Plan": "The plan text.", "Research": "The research text.", "Decision": "The decision text."},
            repo="owner/repo",
        )

        # save_item auto-migrates .md -> .yaml; read from the migrated path.
        content = filepath.with_suffix(".yaml").read_text(encoding="utf-8")
        assert "The plan text." in content
        assert "The research text." in content
        assert "The decision text." in content

    def test_output_aggregator_receives_info_message(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """Verify the output aggregator receives an info message after writing.

        Tests: _handle_batch_groomed output aggregation.
        How: Pass explicit Output instance; verify messages list is non-empty.
        Why: Callers forward output messages to the user — silent completion is wrong.
        """
        mocker.patch("backlog_core.operations.try_get_github", return_value=None)
        filepath = _write_item_file(tmp_path, title="Output Check", topic="output-check")
        item = BacklogItem(title="Output Check", file_path=str(filepath), added="2026-01-01")
        out = Output()

        ops._handle_batch_groomed(item, {"Plan": "Content."}, repo="owner/repo", output=out)

        assert len(out.messages) > 0


# ---------------------------------------------------------------------------
# _handle_batch_groomed: Phase 2 — GitHub sync
# ---------------------------------------------------------------------------


class TestHandleBatchGroomedGithubSync:
    """_handle_batch_groomed syncs to GitHub only after all local writes complete."""

    def test_skips_github_sync_when_item_has_no_issue(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """Verify GitHub sync is not attempted when item.issue is empty.

        Tests: _handle_batch_groomed GitHub-skip path.
        How: Item has no issue; spy on _write_groomed_to_github; assert never called.
        Why: Items without a GitHub issue must not trigger API calls.
        """
        mocker.patch("backlog_core.operations.try_get_github", return_value=None)
        spy = mocker.patch("backlog_core.operations._write_groomed_to_github")
        filepath = _write_item_file(tmp_path, title="No Issue Item", topic="no-issue-item", issue="")
        item = BacklogItem(title="No Issue Item", file_path=str(filepath), issue="", added="2026-01-01")

        ops._handle_batch_groomed(item, {"Plan": "Content."}, repo="owner/repo")

        spy.assert_not_called()

    def test_syncs_each_section_once_when_issue_set(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """Verify _write_groomed_to_github is called once per section when issue is set.

        Tests: _handle_batch_groomed GitHub sync loop count.
        How: Item has issue="#42"; call with two sections; count _write_groomed_to_github calls.
        Why: Every section must reach GitHub independently — not just the first or last.
        """
        spy = mocker.patch("backlog_core.operations._write_groomed_to_github", return_value=True)
        mocker.patch("backlog_core.operations.update_item_metadata")
        filepath = _write_item_file(tmp_path, title="Github Sync Item", topic="github-sync-item", issue="#42")
        item = BacklogItem(title="Github Sync Item", file_path=str(filepath), issue="#42", added="2026-01-01")

        ops._handle_batch_groomed(item, {"Plan": "Plan text.", "Research": "Research text."}, repo="owner/repo")

        assert spy.call_count == 2

    def test_github_sync_receives_correct_issue_ref_and_section_name(
        self, tmp_path: Path, mocker: MockerFixture
    ) -> None:
        """Verify _write_groomed_to_github receives the correct issue ref and section name.

        Tests: _handle_batch_groomed call arguments to _write_groomed_to_github.
        How: Spy on _write_groomed_to_github; inspect call arguments.
        Why: Wrong issue ref or section name causes silent data corruption in GitHub.
        """
        spy = mocker.patch("backlog_core.operations._write_groomed_to_github", return_value=True)
        mocker.patch("backlog_core.operations.update_item_metadata")
        filepath = _write_item_file(tmp_path, title="Arg Check Item", topic="arg-check-item", issue="#77")
        item = BacklogItem(title="Arg Check Item", file_path=str(filepath), issue="#77", added="2026-01-01")

        ops._handle_batch_groomed(item, {"Decision": "The decision is X."}, repo="owner/repo")

        spy.assert_called_once_with("#77", "The decision is X.", "Decision", "owner/repo", output=mocker.ANY)

    def test_all_local_writes_precede_any_github_sync(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """Verify Phase 1 local save completes before any Phase 2 GitHub sync call.

        Tests: _handle_batch_groomed two-phase ordering guarantee.
        How: Record call order via shared call_log side effects on save_item (Phase 1)
             and _write_groomed_to_github (Phase 2).
        Why: Phase 1 (save_item) must fully complete before Phase 2 begins — the
             function must not interleave local writes and GitHub API calls.
             P964 changed Phase 1 from per-section _write_groomed_to_item_file calls
             to a single load-once-save-once save_item call.
        """
        call_log: list[str] = []

        def _local_save(*args, **kwargs) -> None:
            call_log.append("local")

        def _github_write(*args, **kwargs) -> bool:
            call_log.append("github")
            return True

        mocker.patch("backlog_core.operations.save_item", side_effect=_local_save)
        mocker.patch("backlog_core.operations._write_groomed_to_github", side_effect=_github_write)
        mocker.patch("backlog_core.operations.update_item_metadata")

        filepath = tmp_path / "ordering-test.md"
        filepath.write_text(
            _MINIMAL_FRONTMATTER.format(title="Ordering Test", topic="ordering-test", issue="#10"), encoding="utf-8"
        )
        item = BacklogItem(title="Ordering Test", file_path=str(filepath), issue="#10", added="2026-01-01")

        ops._handle_batch_groomed(item, {"Plan": "P.", "Research": "R."}, repo="owner/repo")

        local_indices = [i for i, v in enumerate(call_log) if v == "local"]
        github_indices = [i for i, v in enumerate(call_log) if v == "github"]
        # Phase 1: exactly one save_item call covering all sections
        assert local_indices == [0], f"Expected 1 local save first, got: {call_log}"
        # Phase 2: one GitHub call per section, all after the local save
        assert github_indices == [1, 2], f"Expected 2 github writes after local save, got: {call_log}"

    def test_updates_last_synced_when_any_github_sync_succeeds(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """Verify update_item_metadata is called to set last_synced after a successful sync.

        Tests: _handle_batch_groomed metadata update after sync.
        How: Mock _write_groomed_to_github to return True; spy on update_item_metadata.
        Why: last_synced must be set so clients know the item state was pushed to GitHub.
        """
        mocker.patch("backlog_core.operations._write_groomed_to_github", return_value=True)
        mock_metadata = mocker.patch("backlog_core.operations.update_item_metadata")
        filepath = _write_item_file(tmp_path, title="Synced Item", topic="synced-item", issue="#55")
        item = BacklogItem(title="Synced Item", file_path=str(filepath), issue="#55", added="2026-01-01")

        ops._handle_batch_groomed(item, {"Plan": "Content."}, repo="owner/repo")

        mock_metadata.assert_called_once()
        call_kwargs = str(mock_metadata.call_args)
        assert "last_synced" in call_kwargs

    def test_skips_last_synced_when_all_github_syncs_fail(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """Verify update_item_metadata is NOT called when no GitHub sync succeeded.

        Tests: _handle_batch_groomed metadata skip on failed sync.
        How: Mock _write_groomed_to_github to return False; assert update_item_metadata skipped.
        Why: last_synced must not be stamped with a false timestamp if nothing synced.
        """
        mocker.patch("backlog_core.operations._write_groomed_to_github", return_value=False)
        mock_metadata = mocker.patch("backlog_core.operations.update_item_metadata")
        filepath = _write_item_file(tmp_path, title="Sync Fail Item", topic="sync-fail-item", issue="#99")
        item = BacklogItem(title="Sync Fail Item", file_path=str(filepath), issue="#99", added="2026-01-01")

        ops._handle_batch_groomed(item, {"Plan": "Content."}, repo="owner/repo")

        mock_metadata.assert_not_called()


# ---------------------------------------------------------------------------
# update_item: sections parameter routing
# ---------------------------------------------------------------------------


class TestUpdateItemSectionsRouting:
    """update_item routes to the batch path when sections is not None."""

    def test_empty_sections_returns_sections_written_empty_list(self, mocker: MockerFixture) -> None:
        """Verify sections={} returns sections_written=[] without writing to the file.

        Tests: update_item empty-sections no-op path.
        How: Write item; call update_item(sections={}); inspect return dict.
        Why: Empty batch must succeed as a no-op, not raise an error.
        """
        mocker.patch("backlog_core.operations.try_get_github", return_value=None)
        mocker.patch("backlog_core.operations._pull_if_issue_selector")
        _write_item_file(_backlog_dir(), title="Empty Sections Item", topic="empty-sections-item")

        result = ops.update_item(selector="Empty Sections Item", sections={}, repo="owner/repo")

        assert result["sections_written"] == []

    def test_empty_sections_returns_groomed_updated_false(self, mocker: MockerFixture) -> None:
        """Verify sections={} returns groomed_updated=False.

        Tests: update_item empty-sections groomed_updated flag.
        How: Call update_item(sections={}); check groomed_updated value.
        Why: groomed_updated must only be True when a write actually occurred.
        """
        mocker.patch("backlog_core.operations.try_get_github", return_value=None)
        mocker.patch("backlog_core.operations._pull_if_issue_selector")
        _write_item_file(_backlog_dir(), title="Groomed False Item", topic="groomed-false-item")

        result = ops.update_item(selector="Groomed False Item", sections={}, repo="owner/repo")

        assert result["groomed_updated"] is False

    def test_sections_with_content_returns_sections_written_list(self, mocker: MockerFixture) -> None:
        """Verify sections with content returns sections_written containing all names.

        Tests: update_item batch path sections_written return.
        How: Write item; call update_item(sections={"Plan": "..."}); check sections_written.
        Why: Callers display and track which sections were modified.
        """
        mocker.patch("backlog_core.operations.try_get_github", return_value=None)
        mocker.patch("backlog_core.operations._pull_if_issue_selector")
        _write_item_file(_backlog_dir(), title="Written Sections", topic="written-sections")

        result = ops.update_item(
            selector="Written Sections", sections={"Plan": "The plan.", "Research": "The research."}, repo="owner/repo"
        )

        assert result["sections_written"] == ["Plan", "Research"]

    def test_sections_with_content_returns_groomed_updated_true(self, mocker: MockerFixture) -> None:
        """Verify sections with content returns groomed_updated=True.

        Tests: update_item batch path groomed_updated flag.
        How: Call update_item(sections={"Plan": "..."}); check groomed_updated.
        Why: Non-empty batch must set groomed_updated so callers know a write occurred.
        """
        mocker.patch("backlog_core.operations.try_get_github", return_value=None)
        mocker.patch("backlog_core.operations._pull_if_issue_selector")
        _write_item_file(_backlog_dir(), title="Updated True Item", topic="updated-true-item")

        result = ops.update_item(selector="Updated True Item", sections={"Plan": "Content."}, repo="owner/repo")

        assert result["groomed_updated"] is True

    def test_sections_none_does_not_invoke_handle_batch_groomed(self, mocker: MockerFixture) -> None:
        """Verify sections=None does not invoke _handle_batch_groomed.

        Tests: update_item sections=None bypasses batch dispatch.
        How: Spy on _handle_batch_groomed; call update_item(sections=None); assert not called.
        Why: Existing callers that omit sections must not enter the new batch code path.
        """
        mocker.patch("backlog_core.operations.try_get_github", return_value=None)
        mocker.patch("backlog_core.operations._pull_if_issue_selector")
        spy = mocker.patch("backlog_core.operations._handle_batch_groomed")
        _write_item_file(_backlog_dir(), title="No Sections Item", topic="no-sections-item")

        ops.update_item(selector="No Sections Item", repo="owner/repo")

        spy.assert_not_called()

    @pytest.mark.parametrize(
        ("sections", "expected_written", "expected_groomed"),
        [
            ({}, [], False),
            ({"Plan": "Plan content."}, ["Plan"], True),
            ({"Plan": "P.", "Research": "R."}, ["Plan", "Research"], True),
        ],
    )
    def test_sections_routing_parametrized(
        self, mocker: MockerFixture, sections: dict[str, str], expected_written: list[str], expected_groomed: bool
    ) -> None:
        """Verify sections routing produces correct sections_written and groomed_updated.

        Tests: update_item sections routing across empty, single, and multi-section inputs.
        How: Parametrize over three cases; call update_item; check result dict.
        Why: Covers the decision branches in _apply_groomed_update in one compact sweep.
        """
        mocker.patch("backlog_core.operations.try_get_github", return_value=None)
        mocker.patch("backlog_core.operations._pull_if_issue_selector")
        topic = f"param-item-{len(sections)}"
        _write_item_file(_backlog_dir(), title=f"Param Item {len(sections)}", topic=topic)

        result = ops.update_item(selector=f"Param Item {len(sections)}", sections=sections, repo="owner/repo")

        assert result["sections_written"] == expected_written
        assert result["groomed_updated"] is expected_groomed


# ---------------------------------------------------------------------------
# groom_item: sections parameter delegation
# ---------------------------------------------------------------------------


class TestGroomItemWithSections:
    """groom_item passes sections through to update_item for batch writes."""

    def test_sections_batch_writes_content_to_item_file(self, mocker: MockerFixture) -> None:
        """Verify groom_item with sections writes content into the item file.

        Tests: groom_item sections delegation end-to-end.
        How: Write item; call groom_item(sections={"Plan": "..."}); read file back.
        Why: groom_item is the public entry point — sections must reach the file writer.
        """
        mocker.patch("backlog_core.operations.try_get_github", return_value=None)
        filepath = _write_item_file(_backlog_dir(), title="Groom Sections Item", topic="groom-sections-item")

        ops.groom_item(selector="Groom Sections Item", sections={"Plan": "Groomed plan content."}, repo="owner/repo")

        # save_item auto-migrates .md -> .yaml; read from the migrated path.
        content = filepath.with_suffix(".yaml").read_text(encoding="utf-8")
        assert "Groomed plan content." in content

    def test_sections_returns_sections_written_with_all_names(self, mocker: MockerFixture) -> None:
        """Verify groom_item returns sections_written with all written section names.

        Tests: groom_item return dict sections_written key.
        How: Call groom_item(sections={...}); inspect the returned dict.
        Why: MCP server wraps this return dict — sections_written must be present.
        """
        mocker.patch("backlog_core.operations.try_get_github", return_value=None)
        _write_item_file(_backlog_dir(), title="Groom Return Item", topic="groom-return-item")

        result = ops.groom_item(
            selector="Groom Return Item",
            sections={"Plan": "Plan content.", "Decision": "Decision content."},
            repo="owner/repo",
        )

        assert result["sections_written"] == ["Plan", "Decision"]
        assert result["groomed_updated"] is True

    def test_empty_sections_is_noop_with_no_file_changes(self, mocker: MockerFixture) -> None:
        """Verify groom_item with sections={} makes no file changes.

        Tests: groom_item empty-dict no-op path.
        How: Write item; capture file contents; call groom_item(sections={}); compare.
        Why: Empty batch must return success without modifying the item file.
        """
        mocker.patch("backlog_core.operations.try_get_github", return_value=None)
        filepath = _write_item_file(_backlog_dir(), title="Empty Batch Item", topic="empty-batch-item")
        before = filepath.read_text(encoding="utf-8")

        result = ops.groom_item(selector="Empty Batch Item", sections={}, repo="owner/repo")

        after = filepath.read_text(encoding="utf-8")
        assert result["sections_written"] == []
        assert result["groomed_updated"] is False
        assert before == after

    def test_sections_none_single_section_path_unchanged(self, mocker: MockerFixture) -> None:
        """Verify groom_item without sections still uses the single-section path (regression).

        Tests: groom_item sections=None regression guard.
        How: Call groom_item with section/content (classic path); verify file content.
        Why: Adding the sections param must not break existing callers using section+content.
        """
        mocker.patch("backlog_core.operations.try_get_github", return_value=None)
        filepath = _write_item_file(_backlog_dir(), title="Legacy Groom Item", topic="legacy-groom-item")

        result = ops.groom_item(
            selector="Legacy Groom Item", section="Plan", content="Legacy single-section content.", repo="owner/repo"
        )

        assert result.get("groomed_updated") is True
        # save_item auto-migrates .md -> .yaml; read from the migrated path.
        content = filepath.with_suffix(".yaml").read_text(encoding="utf-8")
        assert "Legacy single-section content." in content

    def test_multi_section_batch_all_sections_in_file(self, mocker: MockerFixture) -> None:
        """Verify groom_item with multiple sections writes all of them to the file.

        Tests: groom_item multi-section batch via public API.
        How: Call groom_item with 3 sections; verify all content appears in the file.
        Why: Confirms end-to-end flow for the primary batch-write use case.
        """
        mocker.patch("backlog_core.operations.try_get_github", return_value=None)
        filepath = _write_item_file(_backlog_dir(), title="Multi Section Groom", topic="multi-section-groom")

        ops.groom_item(
            selector="Multi Section Groom",
            sections={
                "Plan": "Batch plan text.",
                "Research": "Batch research text.",
                "Decision": "Batch decision text.",
            },
            repo="owner/repo",
        )

        # save_item auto-migrates .md -> .yaml; read from the migrated path.
        content = filepath.with_suffix(".yaml").read_text(encoding="utf-8")
        assert "Batch plan text." in content
        assert "Batch research text." in content
        assert "Batch decision text." in content

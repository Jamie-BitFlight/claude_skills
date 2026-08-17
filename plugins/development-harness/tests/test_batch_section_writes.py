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
from backlog_core.backend_protocol import get_config, set_config
from backlog_core.backend_types import BacklogConfig as ProviderConfig
from backlog_core.backends.memory_backend import InMemoryBackend
from backlog_core.models import BacklogConfig, BacklogItem, Output, ReconcileRequest, ReconcileResult

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_item_file(
    directory: Path, *, title: str = "Batch Test Item", topic: str = "batch-test-item", issue: str = ""
) -> Path:
    filepath = directory / f"p1-{topic}.md"
    get_config().backend.put_work_item(
        BacklogItem(title=title, description="A test item", reference=str(filepath), issue=issue, added="2026-01-01")
    )
    return filepath


def _backlog_dir() -> Path:
    return models.get_backlog_dir()


def _stored_text(reference: Path) -> str:
    return get_config().backend.get_work_item(str(reference)).model_dump_json()


class _RecordingSyncBackend(InMemoryBackend):
    def __init__(self, result: ReconcileResult | None = None) -> None:
        super().__init__()
        self.requests: list[ReconcileRequest] = []
        self.events: list[str] = []
        self.result = result or ReconcileResult()

    def put_work_item(self, item: BacklogItem) -> None:
        self.events.append("put")
        super().put_work_item(item)

    def reconcile(self, request: ReconcileRequest) -> ReconcileResult:
        self.events.append("reconcile")
        self.requests.append(request)
        return self.result


def _use_sync_backend(result: ReconcileResult | None = None) -> _RecordingSyncBackend:
    backend = _RecordingSyncBackend(result)
    set_config(ProviderConfig(backend=backend))
    return backend


# ---------------------------------------------------------------------------
# Autouse fixture: filesystem isolation
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolate_backlog_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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
    set_config(ProviderConfig(backend=InMemoryBackend()))


# ---------------------------------------------------------------------------
# _handle_batch_groomed: Phase 1 — local writes
# ---------------------------------------------------------------------------


class TestHandleBatchGroomedLocalWrites:
    def test_item_reference_is_self_healed_not_empty(self) -> None:
        """BacklogItem.reference self-heals at construction time (see models.py).

        A never-explicitly-referenced item can no longer reach
        ``_handle_batch_groomed``'s own ``if not item.reference`` guard —
        every ``BacklogItem`` construction now carries a deterministic,
        non-empty reference. The operative failure mode for an item that was
        never persisted is a backend lookup miss, covered by
        ``test_raises_key_error_when_item_not_in_backend`` below.
        """
        item = BacklogItem(title="No File Item")
        assert item.reference != ""

    def test_raises_key_error_when_item_not_in_backend(self) -> None:
        """An item with a healed but never-persisted reference surfaces a KeyError.

        This is the backend's standard "reference not found" contract (see
        ``InMemoryBackend.get_work_item`` / ``SQLiteBackend.get_work_item``),
        unchanged by reference self-healing — the item now always has a
        valid reference, but nothing was ever stored under it.
        """
        item = BacklogItem(title="No File Item")
        with pytest.raises(KeyError):
            ops._handle_batch_groomed(item, {"Plan": "Some content."}, repo="owner/repo")

    def test_returns_list_of_written_section_names(self, tmp_path: Path, mocker: MockerFixture) -> None:
        mocker.patch("backlog_core.operations.try_get_github", return_value=None)
        filepath = _write_item_file(tmp_path, title="Return Shape", topic="return-shape")
        item = BacklogItem(title="Return Shape", reference=str(filepath), added="2026-01-01")

        result = ops._handle_batch_groomed(item, {"Plan": "Content A.", "Research": "Content B."}, repo="owner/repo")

        assert result == ["Plan", "Research"]

    def test_single_section_written_to_file_body(self, tmp_path: Path, mocker: MockerFixture) -> None:
        mocker.patch("backlog_core.operations.try_get_github", return_value=None)
        filepath = _write_item_file(tmp_path, title="Single Section", topic="single-section")
        item = BacklogItem(title="Single Section", reference=str(filepath), added="2026-01-01")

        ops._handle_batch_groomed(item, {"Plan": "Single plan content."}, repo="owner/repo")

        content = _stored_text(filepath)
        assert "Single plan content." in content

    def test_multiple_sections_all_appear_in_file(self, tmp_path: Path, mocker: MockerFixture) -> None:
        mocker.patch("backlog_core.operations.try_get_github", return_value=None)
        filepath = _write_item_file(tmp_path, title="Multi Section", topic="multi-section")
        item = BacklogItem(title="Multi Section", reference=str(filepath), added="2026-01-01")

        ops._handle_batch_groomed(
            item,
            {"Plan": "The plan text.", "Research": "The research text.", "Decision": "The decision text."},
            repo="owner/repo",
        )

        content = _stored_text(filepath)
        assert "The plan text." in content
        assert "The research text." in content
        assert "The decision text." in content

    def test_output_aggregator_receives_info_message(self, tmp_path: Path, mocker: MockerFixture) -> None:
        mocker.patch("backlog_core.operations.try_get_github", return_value=None)
        filepath = _write_item_file(tmp_path, title="Output Check", topic="output-check")
        item = BacklogItem(title="Output Check", reference=str(filepath), added="2026-01-01")
        out = Output()

        ops._handle_batch_groomed(item, {"Plan": "Content."}, repo="owner/repo", output=out)

        assert len(out.messages) > 0


# ---------------------------------------------------------------------------
# _handle_batch_groomed: Phase 2 — GitHub sync
# ---------------------------------------------------------------------------


class TestHandleBatchGroomedGithubSync:
    def test_skips_github_sync_when_item_has_no_issue(self, tmp_path: Path, mocker: MockerFixture) -> None:
        backend = _use_sync_backend()
        filepath = _write_item_file(tmp_path, title="No Issue Item", topic="no-issue-item", issue="")
        item = BacklogItem(title="No Issue Item", reference=str(filepath), issue="", added="2026-01-01")

        ops._handle_batch_groomed(item, {"Plan": "Content."}, repo="owner/repo")

        assert backend.requests == []

    def test_reconciles_batch_once_when_issue_set(self, tmp_path: Path, mocker: MockerFixture) -> None:
        backend = _use_sync_backend()
        filepath = _write_item_file(tmp_path, title="Github Sync Item", topic="github-sync-item", issue="#42")
        item = BacklogItem(title="Github Sync Item", reference=str(filepath), issue="#42", added="2026-01-01")

        ops._handle_batch_groomed(item, {"Plan": "Plan text.", "Research": "Research text."}, repo="owner/repo")

        assert len(backend.requests) == 1

    def test_reconcile_receives_linked_issue_reference(self, tmp_path: Path, mocker: MockerFixture) -> None:
        backend = _use_sync_backend()
        filepath = _write_item_file(tmp_path, title="Arg Check Item", topic="arg-check-item", issue="#77")
        item = BacklogItem(title="Arg Check Item", reference=str(filepath), issue="#77", added="2026-01-01")

        ops._handle_batch_groomed(item, {"Decision": "The decision is X."}, repo="owner/repo")

        assert backend.requests == [ReconcileRequest(scope="targeted", references=["#77"])]

    def test_all_local_writes_precede_reconciliation(self, tmp_path: Path, mocker: MockerFixture) -> None:
        backend = _use_sync_backend()
        filepath = _write_item_file(tmp_path, title="Ordering Test", topic="ordering-test", issue="#10")
        backend.events.clear()
        item = BacklogItem(title="Ordering Test", reference=str(filepath), issue="#10", added="2026-01-01")

        ops._handle_batch_groomed(item, {"Plan": "P.", "Research": "R."}, repo="owner/repo")

        assert backend.events == ["put", "reconcile"]

    def test_successful_reconcile_does_not_stamp_legacy_last_synced(
        self, tmp_path: Path, mocker: MockerFixture
    ) -> None:
        _use_sync_backend(ReconcileResult(provider_patches=1))
        filepath = _write_item_file(tmp_path, title="Synced Item", topic="synced-item", issue="#55")
        item = BacklogItem(title="Synced Item", reference=str(filepath), issue="#55", added="2026-01-01")

        ops._handle_batch_groomed(item, {"Plan": "Content."}, repo="owner/repo")

        assert get_config().backend.get_work_item(str(filepath)).metadata.last_synced == ""

    def test_failed_reconcile_does_not_stamp_legacy_last_synced(self, tmp_path: Path, mocker: MockerFixture) -> None:
        _use_sync_backend(ReconcileResult(failures=1))
        filepath = _write_item_file(tmp_path, title="Sync Fail Item", topic="sync-fail-item", issue="#99")
        item = BacklogItem(title="Sync Fail Item", reference=str(filepath), issue="#99", added="2026-01-01")

        ops._handle_batch_groomed(item, {"Plan": "Content."}, repo="owner/repo")

        assert get_config().backend.get_work_item(str(filepath)).metadata.last_synced == ""


# ---------------------------------------------------------------------------
# update_item: sections parameter routing
# ---------------------------------------------------------------------------


class TestUpdateItemSectionsRouting:
    def test_empty_sections_returns_sections_written_empty_list(self, mocker: MockerFixture) -> None:
        mocker.patch("backlog_core.operations.try_get_github", return_value=None)
        mocker.patch("backlog_core.operations._pull_if_issue_selector")
        _write_item_file(_backlog_dir(), title="Empty Sections Item", topic="empty-sections-item")

        result = ops.update_item(selector="Empty Sections Item", sections={}, repo="owner/repo")

        assert result["sections_written"] == []

    def test_empty_sections_returns_groomed_updated_false(self, mocker: MockerFixture) -> None:
        mocker.patch("backlog_core.operations.try_get_github", return_value=None)
        mocker.patch("backlog_core.operations._pull_if_issue_selector")
        _write_item_file(_backlog_dir(), title="Groomed False Item", topic="groomed-false-item")

        result = ops.update_item(selector="Groomed False Item", sections={}, repo="owner/repo")

        assert result["groomed_updated"] is False

    def test_sections_with_content_returns_sections_written_list(self, mocker: MockerFixture) -> None:
        mocker.patch("backlog_core.operations.try_get_github", return_value=None)
        mocker.patch("backlog_core.operations._pull_if_issue_selector")
        _write_item_file(_backlog_dir(), title="Written Sections", topic="written-sections")

        result = ops.update_item(
            selector="Written Sections", sections={"Plan": "The plan.", "Research": "The research."}, repo="owner/repo"
        )

        assert result["sections_written"] == ["Plan", "Research"]

    def test_sections_with_content_returns_groomed_updated_true(self, mocker: MockerFixture) -> None:
        mocker.patch("backlog_core.operations.try_get_github", return_value=None)
        mocker.patch("backlog_core.operations._pull_if_issue_selector")
        _write_item_file(_backlog_dir(), title="Updated True Item", topic="updated-true-item")

        result = ops.update_item(selector="Updated True Item", sections={"Plan": "Content."}, repo="owner/repo")

        assert result["groomed_updated"] is True

    def test_sections_none_does_not_invoke_handle_batch_groomed(self, mocker: MockerFixture) -> None:
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
    def test_sections_batch_writes_content_to_item_file(self, mocker: MockerFixture) -> None:
        mocker.patch("backlog_core.operations.try_get_github", return_value=None)
        filepath = _write_item_file(_backlog_dir(), title="Groom Sections Item", topic="groom-sections-item")

        ops.groom_item(selector="Groom Sections Item", sections={"Plan": "Groomed plan content."}, repo="owner/repo")

        content = _stored_text(filepath)
        assert "Groomed plan content." in content

    def test_sections_returns_sections_written_with_all_names(self, mocker: MockerFixture) -> None:
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
        mocker.patch("backlog_core.operations.try_get_github", return_value=None)
        filepath = _write_item_file(_backlog_dir(), title="Empty Batch Item", topic="empty-batch-item")
        before = _stored_text(filepath)

        result = ops.groom_item(selector="Empty Batch Item", sections={}, repo="owner/repo")

        after = _stored_text(filepath)
        assert result["sections_written"] == []
        assert result["groomed_updated"] is False
        assert before == after

    def test_sections_none_single_section_path_unchanged(self, mocker: MockerFixture) -> None:
        mocker.patch("backlog_core.operations.try_get_github", return_value=None)
        filepath = _write_item_file(_backlog_dir(), title="Legacy Groom Item", topic="legacy-groom-item")

        result = ops.groom_item(
            selector="Legacy Groom Item", section="Plan", content="Legacy single-section content.", repo="owner/repo"
        )

        assert result.get("groomed_updated") is True
        content = _stored_text(filepath)
        assert "Legacy single-section content." in content

    def test_multi_section_batch_all_sections_in_file(self, mocker: MockerFixture) -> None:
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

        content = _stored_text(filepath)
        assert "Batch plan text." in content
        assert "Batch research text." in content
        assert "Batch decision text." in content

"""Unit tests for DispatchStateManager — SQLite-backed dispatch state.

Tests: backlog_core.dispatch_state.DispatchStateManager
Strategy: Each test instantiates a fresh DispatchStateManager against a
tmp_path SQLite file to guarantee full isolation. No shared fixtures with
mutable state. os.kill is patched via pytest-mock for PID-liveness tests.
"""

from __future__ import annotations

import errno
import sqlite3
from typing import TYPE_CHECKING

import pytest
from backlog_core.dispatch_state import DispatchStateManager
from backlog_core.models import DispatchItemRecord, DispatchWaveRecord

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_items(milestone: int, wave_num: int, count: int = 2) -> list[DispatchItemRecord]:
    """Return a list of minimal DispatchItemRecord instances for test setup.

    Args:
        milestone: GitHub milestone number to embed in each record.
        wave_num: Wave number to embed in each record.
        count: Number of records to generate (default 2).

    Returns:
        List of DispatchItemRecord instances with sequential issue numbers
        starting at 100.
    """
    return [
        DispatchItemRecord(milestone=milestone, wave_num=wave_num, issue=100 + i, title=f"Issue {100 + i}")
        for i in range(count)
    ]


# ---------------------------------------------------------------------------
# Schema creation
# ---------------------------------------------------------------------------


class TestEnsureSchema:
    """Verify that __init__ creates required tables and indices idempotently."""

    def test_schema_creates_waves_table(self, tmp_path: Path) -> None:
        """DispatchStateManager constructor creates the waves table.

        Tests: DispatchStateManager.ensure_schema / __init__
        How: Open the database directly after construction and query
             sqlite_master for the waves table.
        Why: If the schema is not created on init, all subsequent operations
             will raise sqlite3.OperationalError.
        """
        # Arrange + Act
        mgr = DispatchStateManager(tmp_path / "test.db")
        mgr.close()

        conn = sqlite3.connect(str(tmp_path / "test.db"))
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='waves'")
        row = cursor.fetchone()
        conn.close()

        # Assert
        assert row is not None, "waves table should be created by ensure_schema"

    def test_schema_creates_items_table(self, tmp_path: Path) -> None:
        """DispatchStateManager constructor creates the items table.

        Tests: DispatchStateManager.ensure_schema / __init__
        How: Open the database directly and query sqlite_master for items.
        Why: Items table holds per-issue state; missing table breaks all
             item operations.
        """
        # Arrange + Act
        mgr = DispatchStateManager(tmp_path / "test.db")
        mgr.close()

        conn = sqlite3.connect(str(tmp_path / "test.db"))
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='items'")
        row = cursor.fetchone()
        conn.close()

        # Assert
        assert row is not None, "items table should be created by ensure_schema"

    def test_schema_is_idempotent(self, tmp_path: Path) -> None:
        """Calling ensure_schema multiple times does not raise.

        Tests: DispatchStateManager.ensure_schema
        How: Construct a manager, then call ensure_schema a second time on
             the same database.
        Why: CREATE TABLE IF NOT EXISTS must be idempotent; repeated server
             starts must not fail.
        """
        # Arrange
        mgr = DispatchStateManager(tmp_path / "test.db")

        # Act + Assert — must not raise
        mgr.ensure_schema()
        mgr.close()


# ---------------------------------------------------------------------------
# Wave creation
# ---------------------------------------------------------------------------


class TestCreateWave:
    """Tests for DispatchStateManager.create_wave."""

    def test_create_wave_returns_wave_record(self, tmp_path: Path) -> None:
        """create_wave returns a DispatchWaveRecord with pending status.

        Tests: DispatchStateManager.create_wave return value
        How: Call create_wave with milestone=5, wave_num=1 and two items.
             Inspect the returned DispatchWaveRecord.
        Why: Callers depend on the returned record to seed in-memory state
             without a round-trip read.
        """
        # Arrange
        mgr = DispatchStateManager(tmp_path / "test.db")
        items = _make_items(milestone=5, wave_num=1)

        # Act
        wave = mgr.create_wave(milestone=5, wave_num=1, items=items)
        mgr.close()

        # Assert
        assert isinstance(wave, DispatchWaveRecord)
        assert wave.milestone == 5
        assert wave.wave_num == 1
        assert wave.status == "pending"
        assert len(wave.items) == 2

    def test_create_wave_persists_items_with_pending_status(self, tmp_path: Path) -> None:
        """create_wave writes all item rows with status='pending'.

        Tests: DispatchStateManager.create_wave persistence
        How: Create a wave, close, reopen, and read items via get_wave_items.
        Why: Items must survive a manager restart; persistence is required
             for crash recovery.
        """
        # Arrange
        mgr = DispatchStateManager(tmp_path / "test.db")
        items = _make_items(milestone=5, wave_num=1)

        # Act
        mgr.create_wave(milestone=5, wave_num=1, items=items)
        mgr.close()

        mgr2 = DispatchStateManager(tmp_path / "test.db")
        persisted = mgr2.get_wave_items(milestone=5, wave_num=1)
        mgr2.close()

        # Assert
        assert len(persisted) == 2
        assert all(i.status == "pending" for i in persisted)

    def test_create_wave_duplicate_raises_integrity_error(self, tmp_path: Path) -> None:
        """create_wave raises sqlite3.IntegrityError for duplicate (milestone, wave_num).

        Tests: DispatchStateManager.create_wave duplicate prevention
        How: Insert wave (5, 1), then attempt to insert wave (5, 1) again.
        Why: The PRIMARY KEY constraint prevents double-dispatch of the same
             wave; callers must be able to detect this condition.
        """
        # Arrange
        mgr = DispatchStateManager(tmp_path / "test.db")
        items = _make_items(milestone=5, wave_num=1)
        mgr.create_wave(milestone=5, wave_num=1, items=items)

        # Act + Assert
        with pytest.raises(sqlite3.IntegrityError):
            mgr.create_wave(milestone=5, wave_num=1, items=items)

        mgr.close()

    def test_create_wave_empty_items(self, tmp_path: Path) -> None:
        """create_wave with no items creates a wave row with zero children.

        Tests: DispatchStateManager.create_wave — empty item list edge case
        How: Call create_wave with an empty items list; verify wave exists
             and get_wave_items returns an empty list.
        Why: Dispatch plans may legitimately have waves with zero items (e.g.
             skipped waves); the manager must not fail on empty input.
        """
        # Arrange
        mgr = DispatchStateManager(tmp_path / "test.db")

        # Act
        wave = mgr.create_wave(milestone=7, wave_num=1, items=[])

        # Assert
        assert wave.status == "pending"
        assert wave.items == []
        assert mgr.get_wave_items(milestone=7, wave_num=1) == []
        mgr.close()


# ---------------------------------------------------------------------------
# get_wave
# ---------------------------------------------------------------------------


class TestGetWave:
    """Tests for DispatchStateManager.get_wave."""

    def test_get_wave_returns_wave_with_items(self, tmp_path: Path) -> None:
        """get_wave returns the wave record with nested items.

        Tests: DispatchStateManager.get_wave — happy path
        How: Create a wave with two items, then call get_wave.
        Why: Callers use get_wave to read full wave state; items must be
             populated.
        """
        # Arrange
        mgr = DispatchStateManager(tmp_path / "test.db")
        mgr.create_wave(milestone=3, wave_num=1, items=_make_items(3, 1))

        # Act
        wave = mgr.get_wave(milestone=3, wave_num=1)
        mgr.close()

        # Assert
        assert wave is not None
        assert wave.milestone == 3
        assert wave.wave_num == 1
        assert len(wave.items) == 2

    def test_get_wave_not_found_returns_none(self, tmp_path: Path) -> None:
        """get_wave returns None when the wave does not exist.

        Tests: DispatchStateManager.get_wave — not found path
        How: Call get_wave on an empty database.
        Why: Callers check for None to determine whether a wave has been
             created; None must be returned rather than raising.
        """
        # Arrange
        mgr = DispatchStateManager(tmp_path / "test.db")

        # Act
        result = mgr.get_wave(milestone=99, wave_num=1)
        mgr.close()

        # Assert
        assert result is None


# ---------------------------------------------------------------------------
# get_all_waves
# ---------------------------------------------------------------------------


class TestGetAllWaves:
    """Tests for DispatchStateManager.get_all_waves."""

    def test_get_all_waves_returns_all_waves_ordered(self, tmp_path: Path) -> None:
        """get_all_waves returns all waves for a milestone in wave_num order.

        Tests: DispatchStateManager.get_all_waves — multi-wave milestone
        How: Insert wave_num=2 before wave_num=1 (reverse order), then call
             get_all_waves and verify ascending wave_num order.
        Why: Dispatch logic processes waves sequentially; caller depends on
             ascending order.
        """
        # Arrange
        mgr = DispatchStateManager(tmp_path / "test.db")
        mgr.create_wave(milestone=10, wave_num=2, items=_make_items(10, 2, count=1))
        mgr.create_wave(milestone=10, wave_num=1, items=_make_items(10, 1, count=1))

        # Act
        waves = mgr.get_all_waves(milestone=10)
        mgr.close()

        # Assert
        assert len(waves) == 2
        assert waves[0].wave_num == 1
        assert waves[1].wave_num == 2

    def test_get_all_waves_empty_returns_empty_list(self, tmp_path: Path) -> None:
        """get_all_waves returns an empty list when no waves exist for the milestone.

        Tests: DispatchStateManager.get_all_waves — empty result
        How: Call get_all_waves on a milestone that has never had waves inserted.
        Why: Callers iterate the result; returning None instead of an empty
             list would cause AttributeError.
        """
        # Arrange
        mgr = DispatchStateManager(tmp_path / "test.db")

        # Act
        waves = mgr.get_all_waves(milestone=42)
        mgr.close()

        # Assert
        assert waves == []

    def test_get_all_waves_ignores_other_milestones(self, tmp_path: Path) -> None:
        """get_all_waves only returns waves for the requested milestone.

        Tests: DispatchStateManager.get_all_waves — milestone isolation
        How: Insert waves for milestones 1 and 2; query milestone 1 only.
        Why: Multiple milestones may be active concurrently; results must not
             bleed across milestone boundaries.
        """
        # Arrange
        mgr = DispatchStateManager(tmp_path / "test.db")
        mgr.create_wave(milestone=1, wave_num=1, items=_make_items(1, 1, count=1))
        mgr.create_wave(milestone=2, wave_num=1, items=_make_items(2, 1, count=1))

        # Act
        waves = mgr.get_all_waves(milestone=1)
        mgr.close()

        # Assert
        assert len(waves) == 1
        assert waves[0].milestone == 1


# ---------------------------------------------------------------------------
# get_item
# ---------------------------------------------------------------------------


class TestGetItem:
    """Tests for DispatchStateManager.get_item."""

    def test_get_item_returns_record(self, tmp_path: Path) -> None:
        """get_item returns the DispatchItemRecord for an existing item.

        Tests: DispatchStateManager.get_item — happy path
        How: Create a wave with one item, then call get_item for that item.
        Why: Callers read item state to determine dispatch eligibility.
        """
        # Arrange
        mgr = DispatchStateManager(tmp_path / "test.db")
        items = [DispatchItemRecord(milestone=5, wave_num=1, issue=200, title="My issue")]
        mgr.create_wave(milestone=5, wave_num=1, items=items)

        # Act
        record = mgr.get_item(milestone=5, wave_num=1, issue=200)
        mgr.close()

        # Assert
        assert record is not None
        assert record.issue == 200
        assert record.title == "My issue"
        assert record.status == "pending"

    def test_get_item_not_found_returns_none(self, tmp_path: Path) -> None:
        """get_item returns None when the item does not exist.

        Tests: DispatchStateManager.get_item — not found path
        How: Call get_item on a non-existent issue number.
        Why: Callers check for None to detect missing items; None must be
             returned rather than raising.
        """
        # Arrange
        mgr = DispatchStateManager(tmp_path / "test.db")

        # Act
        result = mgr.get_item(milestone=5, wave_num=1, issue=9999)
        mgr.close()

        # Assert
        assert result is None


# ---------------------------------------------------------------------------
# set_item_in_progress
# ---------------------------------------------------------------------------


class TestSetItemInProgress:
    """Tests for DispatchStateManager.set_item_in_progress."""

    def test_set_item_in_progress_updates_item_status(self, tmp_path: Path) -> None:
        """set_item_in_progress marks the item as in-progress and records pid.

        Tests: DispatchStateManager.set_item_in_progress — item update
        How: Create a wave, call set_item_in_progress, then read the item.
        Why: The dispatch loop reads item status to determine whether to spawn
             a new session; incorrect status causes duplicate spawns.
        """
        # Arrange
        mgr = DispatchStateManager(tmp_path / "test.db")
        items = [DispatchItemRecord(milestone=5, wave_num=1, issue=101, title="T1")]
        mgr.create_wave(milestone=5, wave_num=1, items=items)

        # Act
        mgr.set_item_in_progress(milestone=5, wave_num=1, issue=101, pid=12345)

        # Assert
        record = mgr.get_item(milestone=5, wave_num=1, issue=101)
        mgr.close()
        assert record is not None
        assert record.status == "in-progress"
        assert record.pid == 12345
        assert record.started_at != ""

    def test_set_item_in_progress_updates_wave_status(self, tmp_path: Path) -> None:
        """set_item_in_progress transitions the parent wave to in-progress.

        Tests: DispatchStateManager.set_item_in_progress — wave cascade
        How: Create a pending wave, start one item, then read the wave status.
        Why: Callers query wave status to report overall progress; wave must
             reflect in-progress when any item has started.
        """
        # Arrange
        mgr = DispatchStateManager(tmp_path / "test.db")
        mgr.create_wave(milestone=5, wave_num=1, items=_make_items(5, 1))

        # Act
        mgr.set_item_in_progress(milestone=5, wave_num=1, issue=100, pid=9999)

        # Assert
        wave = mgr.get_wave(milestone=5, wave_num=1)
        mgr.close()
        assert wave is not None
        assert wave.status == "in-progress"
        assert wave.started_at != ""


# ---------------------------------------------------------------------------
# set_item_complete
# ---------------------------------------------------------------------------


class TestSetItemComplete:
    """Tests for DispatchStateManager.set_item_complete."""

    def test_set_item_complete_updates_item_fields(self, tmp_path: Path) -> None:
        """set_item_complete marks the item complete with result and cost.

        Tests: DispatchStateManager.set_item_complete — item update
        How: Create and start an item, then mark it complete with a result
             string and cost value. Read it back and verify all fields.
        Why: Callers read result and cost to compile dispatch summaries.
        """
        # Arrange
        mgr = DispatchStateManager(tmp_path / "test.db")
        mgr.create_wave(milestone=5, wave_num=1, items=_make_items(5, 1, count=1))
        mgr.set_item_in_progress(milestone=5, wave_num=1, issue=100, pid=555)

        # Act
        mgr.set_item_complete(milestone=5, wave_num=1, issue=100, result='{"status":"ok"}', cost=0.042)

        # Assert
        record = mgr.get_item(milestone=5, wave_num=1, issue=100)
        mgr.close()
        assert record is not None
        assert record.status == "complete"
        assert record.result == '{"status":"ok"}'
        assert record.cost == pytest.approx(0.042)
        assert record.completed_at != ""

    def test_set_item_complete_auto_completes_wave_when_all_done(self, tmp_path: Path) -> None:
        """set_item_complete marks the wave complete when all items are terminal.

        Tests: DispatchStateManager.set_item_complete — _maybe_complete_wave
        How: Create a wave with one item, mark it complete. Verify the wave
             transitions to complete.
        Why: Wave completion status drives the dispatch loop's wave-advance
             logic; incorrect wave status stalls the pipeline.
        """
        # Arrange
        mgr = DispatchStateManager(tmp_path / "test.db")
        mgr.create_wave(milestone=5, wave_num=1, items=_make_items(5, 1, count=1))
        mgr.set_item_in_progress(milestone=5, wave_num=1, issue=100, pid=1)

        # Act
        mgr.set_item_complete(milestone=5, wave_num=1, issue=100, result="done")

        # Assert
        wave = mgr.get_wave(milestone=5, wave_num=1)
        mgr.close()
        assert wave is not None
        assert wave.status == "complete"
        assert wave.completed_at != ""

    def test_set_item_complete_does_not_complete_wave_with_pending_items(self, tmp_path: Path) -> None:
        """set_item_complete does not complete the wave if other items are pending.

        Tests: DispatchStateManager.set_item_complete — partial completion guard
        How: Create a wave with two items; complete only the first. Verify
             the wave remains in-progress.
        Why: Prematurely completing a wave would cause the dispatch loop to
             advance and skip in-flight items.
        """
        # Arrange
        mgr = DispatchStateManager(tmp_path / "test.db")
        mgr.create_wave(milestone=5, wave_num=1, items=_make_items(5, 1, count=2))
        mgr.set_item_in_progress(milestone=5, wave_num=1, issue=100, pid=1)
        mgr.set_item_in_progress(milestone=5, wave_num=1, issue=101, pid=2)

        # Act — complete only the first item
        mgr.set_item_complete(milestone=5, wave_num=1, issue=100, result="done")

        # Assert
        wave = mgr.get_wave(milestone=5, wave_num=1)
        mgr.close()
        assert wave is not None
        assert wave.status == "in-progress"


# ---------------------------------------------------------------------------
# set_item_failed
# ---------------------------------------------------------------------------


class TestSetItemFailed:
    """Tests for DispatchStateManager.set_item_failed."""

    def test_set_item_failed_updates_item_fields(self, tmp_path: Path) -> None:
        """set_item_failed marks the item failed with the error message.

        Tests: DispatchStateManager.set_item_failed — item update
        How: Create and start an item, then call set_item_failed with an
             error string. Read back and verify status and error fields.
        Why: Callers read error text to log and surface failure details.
        """
        # Arrange
        mgr = DispatchStateManager(tmp_path / "test.db")
        mgr.create_wave(milestone=5, wave_num=1, items=_make_items(5, 1, count=1))
        mgr.set_item_in_progress(milestone=5, wave_num=1, issue=100, pid=777)

        # Act
        mgr.set_item_failed(milestone=5, wave_num=1, issue=100, error="timeout after 300s")

        # Assert
        record = mgr.get_item(milestone=5, wave_num=1, issue=100)
        mgr.close()
        assert record is not None
        assert record.status == "failed"
        assert record.error == "timeout after 300s"
        assert record.completed_at != ""

    def test_set_item_failed_auto_completes_wave_when_last_item(self, tmp_path: Path) -> None:
        """set_item_failed completes the wave when all items reach terminal status.

        Tests: DispatchStateManager.set_item_failed — _maybe_complete_wave
        How: Create a wave with one item, fail it, then verify wave completes.
        Why: A failed item is still terminal; the wave must advance regardless
             of whether items succeeded or failed.
        """
        # Arrange
        mgr = DispatchStateManager(tmp_path / "test.db")
        mgr.create_wave(milestone=5, wave_num=1, items=_make_items(5, 1, count=1))
        mgr.set_item_in_progress(milestone=5, wave_num=1, issue=100, pid=1)

        # Act
        mgr.set_item_failed(milestone=5, wave_num=1, issue=100, error="crash")

        # Assert
        wave = mgr.get_wave(milestone=5, wave_num=1)
        mgr.close()
        assert wave is not None
        assert wave.status == "complete"


# ---------------------------------------------------------------------------
# get_wave_items
# ---------------------------------------------------------------------------


class TestGetWaveItems:
    """Tests for DispatchStateManager.get_wave_items."""

    def test_get_wave_items_returns_items_ordered_by_issue(self, tmp_path: Path) -> None:
        """get_wave_items returns items sorted ascending by issue number.

        Tests: DispatchStateManager.get_wave_items — ordering
        How: Insert items with issue numbers 102, 100, 101 via two separate
             waves built in non-sequential order. Verify ascending sort.
        Why: Dispatch output logs use issue-number order for readability;
             callers depend on deterministic ordering.
        """
        # Arrange
        mgr = DispatchStateManager(tmp_path / "test.db")
        items = [
            DispatchItemRecord(milestone=5, wave_num=1, issue=102, title="C"),
            DispatchItemRecord(milestone=5, wave_num=1, issue=100, title="A"),
            DispatchItemRecord(milestone=5, wave_num=1, issue=101, title="B"),
        ]
        mgr.create_wave(milestone=5, wave_num=1, items=items)

        # Act
        result = mgr.get_wave_items(milestone=5, wave_num=1)
        mgr.close()

        # Assert
        assert [r.issue for r in result] == [100, 101, 102]

    def test_get_wave_items_empty_wave_returns_empty_list(self, tmp_path: Path) -> None:
        """get_wave_items returns an empty list for a wave with no items.

        Tests: DispatchStateManager.get_wave_items — empty wave
        How: Create a wave with no items, then call get_wave_items.
        Why: Callers iterate the result; must not crash on empty list.
        """
        # Arrange
        mgr = DispatchStateManager(tmp_path / "test.db")
        mgr.create_wave(milestone=5, wave_num=1, items=[])

        # Act
        result = mgr.get_wave_items(milestone=5, wave_num=1)
        mgr.close()

        # Assert
        assert result == []


# ---------------------------------------------------------------------------
# check_stale_pids
# ---------------------------------------------------------------------------


class TestCheckStalePids:
    """Tests for DispatchStateManager.check_stale_pids."""

    def test_check_stale_pids_dead_pid_marks_item_failed(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """check_stale_pids marks in-progress items failed when their PID is dead.

        Tests: DispatchStateManager.check_stale_pids — ProcessLookupError path
        How: Create an in-progress item with pid=99999. Patch os.kill to raise
             ProcessLookupError for that PID. Call check_stale_pids and verify
             the item was moved to failed.
        Why: Dead PIDs indicate orphaned sessions; the dispatch loop must detect
             and requeue those items rather than waiting forever.
        """
        # Arrange
        mgr = DispatchStateManager(tmp_path / "test.db")
        mgr.create_wave(milestone=5, wave_num=1, items=_make_items(5, 1, count=1))
        mgr.set_item_in_progress(milestone=5, wave_num=1, issue=100, pid=99999)

        mocker.patch("backlog_core.dispatch_state.os.kill", side_effect=ProcessLookupError)

        # Act
        stale = mgr.check_stale_pids()

        # Assert
        assert len(stale) == 1
        assert stale[0].issue == 100
        assert stale[0].status == "failed"
        assert "99999" in stale[0].error

        record = mgr.get_item(milestone=5, wave_num=1, issue=100)
        mgr.close()
        assert record is not None
        assert record.status == "failed"

    def test_check_stale_pids_live_pid_leaves_item_in_progress(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """check_stale_pids does not touch items whose PID is still alive.

        Tests: DispatchStateManager.check_stale_pids — PermissionError (alive) path
        How: Create an in-progress item. Patch os.kill to raise PermissionError
             (process exists but not signallable). Verify item remains in-progress
             and check_stale_pids returns an empty list.
        Why: PermissionError means the process is alive; false-positives here
             would terminate running sessions.
        """
        # Arrange
        mgr = DispatchStateManager(tmp_path / "test.db")
        mgr.create_wave(milestone=5, wave_num=1, items=_make_items(5, 1, count=1))
        mgr.set_item_in_progress(milestone=5, wave_num=1, issue=100, pid=12345)

        mocker.patch("backlog_core.dispatch_state.os.kill", side_effect=PermissionError)

        # Act
        stale = mgr.check_stale_pids()

        # Assert
        assert stale == []
        record = mgr.get_item(milestone=5, wave_num=1, issue=100)
        mgr.close()
        assert record is not None
        assert record.status == "in-progress"

    def test_check_stale_pids_no_in_progress_items_returns_empty(self, tmp_path: Path) -> None:
        """check_stale_pids returns empty list when no items are in-progress.

        Tests: DispatchStateManager.check_stale_pids — empty result
        How: Create a wave with pending items (never started). Call
             check_stale_pids without patching os.kill — it should never be
             called because the SQL WHERE clause filters to in-progress only.
        Why: Avoids unnecessary os.kill calls and confirms the SQL filter
             is correct.
        """
        # Arrange
        mgr = DispatchStateManager(tmp_path / "test.db")
        mgr.create_wave(milestone=5, wave_num=1, items=_make_items(5, 1, count=2))

        # Act — no items are in-progress, so no PID checks should fire
        stale = mgr.check_stale_pids()
        mgr.close()

        # Assert
        assert stale == []

    def test_check_stale_pids_mixed_live_and_dead(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """check_stale_pids correctly identifies only dead PIDs in a mixed group.

        Tests: DispatchStateManager.check_stale_pids — mixed live/dead PIDs
        How: Two in-progress items: pid=1111 (dead) and pid=2222 (alive).
             Patch os.kill to raise ProcessLookupError only for 1111.
        Why: The method must apply per-PID checks, not fail all-or-nothing.
        """
        # Arrange
        mgr = DispatchStateManager(tmp_path / "test.db")
        items = [
            DispatchItemRecord(milestone=5, wave_num=1, issue=100, title="dead"),
            DispatchItemRecord(milestone=5, wave_num=1, issue=101, title="alive"),
        ]
        mgr.create_wave(milestone=5, wave_num=1, items=items)
        mgr.set_item_in_progress(milestone=5, wave_num=1, issue=100, pid=1111)
        mgr.set_item_in_progress(milestone=5, wave_num=1, issue=101, pid=2222)

        def _selective_kill(pid: int, sig: int) -> None:
            if pid == 1111:
                raise ProcessLookupError
            # pid 2222 — do nothing (process alive, signal ignored)

        mocker.patch("backlog_core.dispatch_state.os.kill", side_effect=_selective_kill)

        # Act
        stale = mgr.check_stale_pids()

        # Assert
        assert len(stale) == 1
        assert stale[0].issue == 100

        alive = mgr.get_item(milestone=5, wave_num=1, issue=101)
        mgr.close()
        assert alive is not None
        assert alive.status == "in-progress"

    def test_check_stale_pids_plain_oserror_marks_item_failed(self, tmp_path: Path, mocker: MockerFixture) -> None:
        """check_stale_pids marks items failed when os.kill raises a plain OSError.

        Tests: DispatchStateManager.check_stale_pids — bare OSError path
        How: Create an in-progress item with pid=99999. Patch os.kill to raise
             OSError(errno.EPERM, "Operation not permitted") — a plain OSError
             that is NOT a PermissionError subclass, as raised by some container
             runtimes. Call check_stale_pids and verify the item is failed.
        Why: Container runtimes may raise OSError subclasses other than
             ProcessLookupError or PermissionError. The old code only caught
             those two specific types; a bare OSError would propagate and crash
             the stale-check loop.
        """
        # Arrange
        mgr = DispatchStateManager(tmp_path / "test.db")
        mgr.create_wave(milestone=5, wave_num=1, items=_make_items(5, 1, count=1))
        mgr.set_item_in_progress(milestone=5, wave_num=1, issue=100, pid=99999)

        # Use errno.ENODEV ("No such device") — it is never auto-mapped to a
        # named OSError subclass, so the instance stays a plain OSError.
        plain_oserror = OSError(errno.ENODEV, "No such device")
        assert not isinstance(plain_oserror, PermissionError), (
            "Test precondition: OSError(errno.ENODEV) must not be a PermissionError instance"
        )
        mocker.patch("backlog_core.dispatch_state.os.kill", side_effect=plain_oserror)

        # Act
        stale = mgr.check_stale_pids()

        # Assert
        assert len(stale) == 1
        assert stale[0].issue == 100
        assert stale[0].status == "failed"
        assert "99999" in stale[0].error

        record = mgr.get_item(milestone=5, wave_num=1, issue=100)
        mgr.close()
        assert record is not None
        assert record.status == "failed"

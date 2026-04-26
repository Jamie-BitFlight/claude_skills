"""SQLite-backed state manager for dispatch orchestration.

This module is standalone — it has no MCP or FastMCP awareness. It provides
pure state management for dispatch waves and items, persisted to a SQLite
database at the path supplied by the caller.

All methods are synchronous. Callers in async contexts (server.py) wrap calls
in ``asyncio.to_thread()``.
"""

from __future__ import annotations

import os
import sqlite3
from typing import TYPE_CHECKING

from backlog_core.models import DispatchItemRecord, DispatchWaveRecord
from backlog_core.parsing import now_iso as _now_iso

if TYPE_CHECKING:
    from pathlib import Path


class DispatchStateManager:
    """SQLite state backend for dispatch orchestration.

    Creates the database and tables on first use. All methods are synchronous;
    callers wrap in ``asyncio.to_thread``. Thread-safe via
    ``check_same_thread=False``.

    Args:
        db_path: Filesystem path for the SQLite database file. Parent
            directories must already exist (caller's responsibility).

    Example:
        >>> mgr = DispatchStateManager(Path("/tmp/test.db"))
        >>> wave = mgr.create_wave(milestone=5, wave_num=1, items=[...])
    """

    def __init__(self, db_path: Path) -> None:
        """Initialise the state manager and ensure the database schema exists.

        Args:
            db_path: Filesystem path for the SQLite database file. The parent
                directory must already exist before calling this constructor.
        """
        self._db_path = db_path
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self.ensure_schema()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def ensure_schema(self) -> None:
        """Create ``waves`` and ``items`` tables if they do not exist.

        Idempotent — safe to call multiple times.
        """
        cursor = self._conn.cursor()
        cursor.executescript(
            """
            CREATE TABLE IF NOT EXISTS waves (
                milestone    INTEGER NOT NULL,
                wave_num     INTEGER NOT NULL,
                status       TEXT NOT NULL DEFAULT 'pending',
                started_at   TEXT,
                completed_at TEXT,
                PRIMARY KEY (milestone, wave_num)
            );

            CREATE TABLE IF NOT EXISTS items (
                milestone    INTEGER NOT NULL,
                wave_num     INTEGER NOT NULL,
                issue        INTEGER NOT NULL,
                title        TEXT NOT NULL DEFAULT '',
                status       TEXT NOT NULL DEFAULT 'pending',
                pid          INTEGER,
                session_id   TEXT,
                started_at   TEXT,
                completed_at TEXT,
                result       TEXT,
                error        TEXT,
                cost         REAL,
                result_file  TEXT,
                error_file   TEXT,
                PRIMARY KEY (milestone, wave_num, issue),
                FOREIGN KEY (milestone, wave_num) REFERENCES waves(milestone, wave_num)
            );

            CREATE INDEX IF NOT EXISTS idx_items_status
                ON items(status);

            CREATE INDEX IF NOT EXISTS idx_items_milestone
                ON items(milestone, wave_num);
            """
        )
        self._conn.commit()

    def close(self) -> None:
        """Close the underlying SQLite connection."""
        self._conn.close()

    # ------------------------------------------------------------------
    # Wave operations
    # ------------------------------------------------------------------

    def create_wave(self, milestone: int, wave_num: int, items: list[DispatchItemRecord]) -> DispatchWaveRecord:
        """Insert a wave row and all item rows.

        Args:
            milestone: GitHub milestone number.
            wave_num: Wave number from the dispatch plan (1-based).
            items: List of ``DispatchItemRecord`` instances to insert as
                children of this wave. Each record's ``milestone`` and
                ``wave_num`` fields are overwritten to match the wave.

        Returns:
            A ``DispatchWaveRecord`` with ``status='pending'`` and the
            supplied ``items`` attached.

        Raises:
            sqlite3.IntegrityError: If the (milestone, wave_num) pair already
                exists.
        """
        cursor = self._conn.cursor()
        cursor.execute(
            """
            INSERT INTO waves (milestone, wave_num, status)
            VALUES (?, ?, 'pending')
            """,
            (milestone, wave_num),
        )
        for item in items:
            cursor.execute(
                """
                INSERT INTO items
                    (milestone, wave_num, issue, title, status)
                VALUES (?, ?, ?, ?, 'pending')
                """,
                (milestone, wave_num, item.issue, item.title),
            )
        self._conn.commit()

        return DispatchWaveRecord(
            milestone=milestone,
            wave_num=wave_num,
            status="pending",
            started_at="",
            completed_at="",
            items=[
                DispatchItemRecord(
                    milestone=milestone, wave_num=wave_num, issue=i.issue, title=i.title, status="pending"
                )
                for i in items
            ],
        )

    def get_wave(self, milestone: int, wave_num: int) -> DispatchWaveRecord | None:
        """Retrieve a wave with all nested items.

        Args:
            milestone: GitHub milestone number.
            wave_num: Wave number (1-based).

        Returns:
            A ``DispatchWaveRecord`` with ``items`` populated, or ``None``
            if no wave matches.
        """
        cursor = self._conn.cursor()
        cursor.execute(
            """
            SELECT milestone, wave_num, status, started_at, completed_at
            FROM waves
            WHERE milestone = ? AND wave_num = ?
            """,
            (milestone, wave_num),
        )
        row = cursor.fetchone()
        if row is None:
            return None

        return DispatchWaveRecord(
            milestone=row["milestone"],
            wave_num=row["wave_num"],
            status=row["status"],
            started_at=row["started_at"] or "",
            completed_at=row["completed_at"] or "",
            items=self.get_wave_items(milestone, wave_num),
        )

    def get_all_waves(self, milestone: int) -> list[DispatchWaveRecord]:
        """Retrieve all waves for a milestone in insertion order.

        Args:
            milestone: GitHub milestone number.

        Returns:
            List of ``DispatchWaveRecord`` instances (each with nested items),
            ordered by ``wave_num`` ascending. Empty list if none found.
        """
        cursor = self._conn.cursor()
        cursor.execute(
            """
            SELECT milestone, wave_num, status, started_at, completed_at
            FROM waves
            WHERE milestone = ?
            ORDER BY wave_num ASC
            """,
            (milestone,),
        )
        rows = cursor.fetchall()
        return [
            DispatchWaveRecord(
                milestone=row["milestone"],
                wave_num=row["wave_num"],
                status=row["status"],
                started_at=row["started_at"] or "",
                completed_at=row["completed_at"] or "",
                items=self.get_wave_items(row["milestone"], row["wave_num"]),
            )
            for row in rows
        ]

    # ------------------------------------------------------------------
    # Item operations
    # ------------------------------------------------------------------

    def set_item_in_progress(self, milestone: int, wave_num: int, issue: int, pid: int) -> None:
        """Mark an item as in-progress and record the spawned PID.

        Args:
            milestone: GitHub milestone number.
            wave_num: Wave number (1-based).
            issue: GitHub issue number of the item.
            pid: OS process ID of the spawned claude session.
        """
        cursor = self._conn.cursor()
        cursor.execute(
            """
            UPDATE items
            SET status = 'in-progress',
                pid = ?,
                started_at = COALESCE(started_at, ?)
            WHERE milestone = ? AND wave_num = ? AND issue = ?
            """,
            (pid, _now_iso(), milestone, wave_num, issue),
        )
        # Also update wave status to in-progress when first item starts.
        cursor.execute(
            """
            UPDATE waves
            SET status = 'in-progress',
                started_at = COALESCE(started_at, ?)
            WHERE milestone = ? AND wave_num = ?
            """,
            (_now_iso(), milestone, wave_num),
        )
        self._conn.commit()

    def set_item_session_id(self, milestone: int, wave_num: int, issue: int, session_id: str | None) -> None:
        """Record the Claude Code session UUID for a spawned item.

        Args:
            milestone: GitHub milestone number.
            wave_num: Wave number (1-based).
            issue: GitHub issue number of the item.
            session_id: UUID extracted from JSONL type=system,subtype=init event, or None.
        """
        cursor = self._conn.cursor()
        cursor.execute(
            """
            UPDATE items
            SET session_id = ?
            WHERE milestone = ? AND wave_num = ? AND issue = ?
            """,
            (session_id, milestone, wave_num, issue),
        )
        self._conn.commit()

    def set_item_complete(
        self, milestone: int, wave_num: int, issue: int, result: str, cost: float | None = None
    ) -> None:
        """Mark an item as complete and record the result.

        Args:
            milestone: GitHub milestone number.
            wave_num: Wave number (1-based).
            issue: GitHub issue number of the item.
            result: Result summary or JSON string from the result file.
            cost: USD cost if available from the claude session output.
        """
        now = _now_iso()
        cursor = self._conn.cursor()
        cursor.execute(
            """
            UPDATE items
            SET status = 'complete',
                result = ?,
                cost = ?,
                completed_at = ?
            WHERE milestone = ? AND wave_num = ? AND issue = ?
            """,
            (result, cost, now, milestone, wave_num, issue),
        )
        self._conn.commit()
        self._maybe_complete_wave(milestone, wave_num)

    def set_item_failed(self, milestone: int, wave_num: int, issue: int, error: str) -> None:
        """Mark an item as failed and record the error message.

        Args:
            milestone: GitHub milestone number.
            wave_num: Wave number (1-based).
            issue: GitHub issue number of the item.
            error: Human-readable error details.
        """
        now = _now_iso()
        cursor = self._conn.cursor()
        cursor.execute(
            """
            UPDATE items
            SET status = 'failed',
                error = ?,
                completed_at = ?
            WHERE milestone = ? AND wave_num = ? AND issue = ?
            """,
            (error, now, milestone, wave_num, issue),
        )
        self._conn.commit()
        self._maybe_complete_wave(milestone, wave_num)

    def get_item(self, milestone: int, wave_num: int, issue: int) -> DispatchItemRecord | None:
        """Retrieve a single item by its primary key.

        Args:
            milestone: GitHub milestone number.
            wave_num: Wave number (1-based).
            issue: GitHub issue number.

        Returns:
            A ``DispatchItemRecord``, or ``None`` if not found.
        """
        cursor = self._conn.cursor()
        cursor.execute(
            """
            SELECT milestone, wave_num, issue, title, status, pid,
                   started_at, completed_at, result, error, cost,
                   result_file, error_file
            FROM items
            WHERE milestone = ? AND wave_num = ? AND issue = ?
            """,
            (milestone, wave_num, issue),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return _row_to_item(row)

    def get_wave_items(self, milestone: int, wave_num: int) -> list[DispatchItemRecord]:
        """Retrieve all items for a wave.

        Args:
            milestone: GitHub milestone number.
            wave_num: Wave number (1-based).

        Returns:
            List of ``DispatchItemRecord`` instances for the wave, ordered by
            ``issue`` ascending.
        """
        cursor = self._conn.cursor()
        cursor.execute(
            """
            SELECT milestone, wave_num, issue, title, status, pid,
                   started_at, completed_at, result, error, cost,
                   result_file, error_file
            FROM items
            WHERE milestone = ? AND wave_num = ?
            ORDER BY issue ASC
            """,
            (milestone, wave_num),
        )
        return [_row_to_item(row) for row in cursor.fetchall()]

    # ------------------------------------------------------------------
    # Stale PID detection
    # ------------------------------------------------------------------

    def check_stale_pids(self) -> list[DispatchItemRecord]:
        """Detect in-progress items whose spawned processes have died.

        Queries all items with ``status='in-progress'`` and a non-null PID.
        For each, sends signal 0 via ``os.kill`` to check process existence.
        Items whose PID is dead are marked failed with an explanatory message.

        Returns:
            List of ``DispatchItemRecord`` instances that were newly marked
            failed (empty if no stale items detected).
        """
        cursor = self._conn.cursor()
        cursor.execute(
            """
            SELECT milestone, wave_num, issue, title, status, pid,
                   started_at, completed_at, result, error, cost,
                   result_file, error_file
            FROM items
            WHERE status = 'in-progress' AND pid IS NOT NULL
            """
        )
        rows = cursor.fetchall()
        stale: list[DispatchItemRecord] = []
        for row in rows:
            pid: int = row["pid"]
            try:
                os.kill(pid, 0)
            except OSError as exc:
                if isinstance(exc, PermissionError):
                    # PID exists but we don't have permission to signal it.
                    # Process is alive; leave as-is.
                    pass
                else:
                    # ProcessLookupError (no such PID) or any other OSError
                    # subclass raised by container runtimes — treat as dead.
                    error_msg = f"Process died unexpectedly (PID {pid})"
                    self.set_item_failed(
                        milestone=row["milestone"], wave_num=row["wave_num"], issue=row["issue"], error=error_msg
                    )
                    stale.append(
                        DispatchItemRecord(
                            milestone=row["milestone"],
                            wave_num=row["wave_num"],
                            issue=row["issue"],
                            title=row["title"],
                            status="failed",
                            pid=pid,
                            started_at=row["started_at"] or "",
                            completed_at="",
                            result="",
                            error=error_msg,
                            cost=None,
                            result_file=row["result_file"] or "",
                            error_file=row["error_file"] or "",
                        )
                    )
        return stale

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _maybe_complete_wave(self, milestone: int, wave_num: int) -> None:
        """Mark the wave complete when all items reach a terminal status.

        Called after any item reaches ``complete`` or ``failed``. If any item
        is still ``pending`` or ``in-progress``, no update is made.

        Args:
            milestone: GitHub milestone number.
            wave_num: Wave number (1-based).
        """
        cursor = self._conn.cursor()
        cursor.execute(
            """
            SELECT COUNT(*) AS pending_count
            FROM items
            WHERE milestone = ? AND wave_num = ?
              AND status IN ('pending', 'in-progress')
            """,
            (milestone, wave_num),
        )
        row = cursor.fetchone()
        if row and row["pending_count"] == 0:
            cursor.execute(
                """
                UPDATE waves
                SET status = 'complete',
                    completed_at = ?
                WHERE milestone = ? AND wave_num = ?
                  AND status != 'complete'
                """,
                (_now_iso(), milestone, wave_num),
            )
            self._conn.commit()


def _row_to_item(row: sqlite3.Row) -> DispatchItemRecord:
    """Convert a sqlite3.Row from the items table to a DispatchItemRecord.

    Args:
        row: A sqlite3.Row with all columns from the ``items`` table.

    Returns:
        A populated ``DispatchItemRecord``.
    """
    return DispatchItemRecord(
        milestone=row["milestone"],
        wave_num=row["wave_num"],
        issue=row["issue"],
        title=row["title"] or "",
        status=row["status"],
        pid=row["pid"],
        started_at=row["started_at"] or "",
        completed_at=row["completed_at"] or "",
        result=row["result"] or "",
        error=row["error"] or "",
        cost=row["cost"],
        result_file=row["result_file"] or "",
        error_file=row["error_file"] or "",
    )

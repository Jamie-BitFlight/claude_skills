"""SQLite-backed state manager for dispatch orchestration.

This module is standalone — it has no MCP or FastMCP awareness. It provides
pure state management for dispatch waves and items, persisted to a SQLite
database at the path supplied by the caller.

All methods are synchronous. Callers in async contexts (server.py) wrap calls
in ``asyncio.to_thread()``.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from typing import TYPE_CHECKING

from backlog_core.backends.bd_runner import BdRunner
from backlog_core.backends.beads_models import parse_issue
from backlog_core.models import DispatchItemRecord, DispatchWaveRecord
from backlog_core.parsing import now_iso as _now_iso

if TYPE_CHECKING:
    from pathlib import Path

_WAVE_MAP_FILENAME: str = "dispatch-beads-wave-map.json"
_log = logging.getLogger(__name__)


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

    @property
    def db_path(self) -> Path:
        """Return the filesystem path to the SQLite database."""
        return self._db_path

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


class BeadsDispatchAdapter:
    """Thin adapter that records wave membership in beads molecule epics.

    SQLite remains the authority for all wave state (PIDs, completion status,
    timing). This adapter only binds/queries beads for the membership dimension.

    The wave→beads-molecule mapping is persisted in a JSON sidecar file
    (``dispatch-beads-wave-map.json``) alongside the SQLite database because
    the existing ``waves`` table has no column for a beads molecule ID and the
    task constrains us to no schema changes.

    Args:
        db_path: Filesystem path to the SQLite database. The sidecar file is
            written to the same parent directory.
    """

    def __init__(self, db_path: Path) -> None:
        """Initialise adapter and load the wave→molecule ID sidecar.

        Args:
            db_path: Path to the SQLite database; sidecar lives alongside it.
        """
        self._map_path = db_path.parent / _WAVE_MAP_FILENAME
        self._map: dict[str, str] = self._load_map()
        self._runner: BdRunner = BdRunner()

    # ------------------------------------------------------------------
    # Sidecar helpers
    # ------------------------------------------------------------------

    def _map_key(self, milestone: int, wave_num: int) -> str:
        """Return the sidecar dict key for a (milestone, wave_num) pair."""
        return f"{milestone}:{wave_num}"

    def _load_map(self) -> dict[str, str]:
        """Read the sidecar JSON file into a mapping.

        Returns:
            Mapping of ``"milestone:wave_num"`` keys to beads molecule IDs.
            Returns an empty dict when the sidecar file does not exist or
            contains non-object JSON.
        """
        if not self._map_path.exists():
            return {}
        text = self._map_path.read_text(encoding="utf-8")
        data = json.loads(text)
        if not isinstance(data, dict):
            _log.warning("beads wave map is not a JSON object; resetting: %s", self._map_path)
            return {}
        return {str(k): str(v) for k, v in data.items()}

    def _save_map(self) -> None:
        """Persist the in-memory wave→molecule map to the sidecar file."""
        self._map_path.write_text(json.dumps(self._map), encoding="utf-8")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_wave_id(self, milestone: int, wave_num: int) -> str | None:
        """Return the beads molecule ID for a wave, or ``None`` if not bonded.

        Args:
            milestone: GitHub milestone number.
            wave_num: Wave number (1-based).

        Returns:
            Beads nanoid string (e.g. ``"bd-a3f8"``), or ``None``.
        """
        return self._map.get(self._map_key(milestone, wave_num))

    def create_wave_molecule(self, milestone: int, wave_num: int, title: str) -> str:
        """Create a beads molecule epic for the wave and store its ID.

        Runs ``bd create --type molecule --title <title> --json`` via
        ``BdRunner``. The returned beads ID is written to the JSON sidecar.

        Args:
            milestone: GitHub milestone number.
            wave_num: Wave number (1-based).
            title: Human-readable title for the molecule epic.

        Returns:
            The beads nanoid string (e.g. ``"bd-a3f8"``) for the new molecule.

        Raises:
            BdNotInstalledError: If the ``bd`` binary is not on PATH.
            BdInvocationError: If ``bd create`` returns a non-zero exit code.
            BdJsonDecodeError: If the JSON response cannot be decoded.
            pydantic.ValidationError: If the response does not match the
                ``BeadsIssueRaw`` schema.
        """
        data = self._runner.run_json(["create", "--type", "molecule", "--title", title])
        issue = parse_issue(data)
        beads_id: str = issue.id
        self._map[self._map_key(milestone, wave_num)] = beads_id
        self._save_map()
        _log.info("Created beads molecule %s for wave %d:%d", beads_id, milestone, wave_num)
        return beads_id

    def bond_item(self, milestone: int, wave_num: int, beads_item_id: str) -> None:
        """Bond a beads issue into the wave's molecule epic.

        Runs ``bd mol bond <molecule_id> <item_id>``. No-op when no molecule
        ID is recorded for this wave (the wave was never bonded to beads).

        Args:
            milestone: GitHub milestone number.
            wave_num: Wave number (1-based).
            beads_item_id: Beads nanoid of the child issue to bond.

        Raises:
            BdNotInstalledError: If the ``bd`` binary is not on PATH.
            BdInvocationError: If ``bd mol bond`` returns a non-zero exit code.
        """
        wave_id = self.get_wave_id(milestone, wave_num)
        if wave_id is None:
            _log.debug("No molecule for wave %d:%d — skipping bond for %s", milestone, wave_num, beads_item_id)
            return
        self._runner.run_text(["mol", "bond", wave_id, beads_item_id])
        _log.debug("Bonded %s to molecule %s", beads_item_id, wave_id)

    def check_stale_members(
        self, milestone: int, wave_num: int, state_manager: DispatchStateManager
    ) -> list[DispatchItemRecord]:
        """Check in-progress SQLite items for a specific wave for PID liveness.

        Scopes PID liveness checks to the specific wave rather than scanning
        all in-progress items globally (contrast with
        ``DispatchStateManager.check_stale_pids()``). Dead PIDs are marked
        failed via the state manager.

        Note: Beads membership is not queried here — PID state is stored only
        in SQLite. The wave's molecule ID is checked solely to confirm this wave
        is beads-tracked; if no molecule is recorded the method returns early.

        Args:
            milestone: GitHub milestone number.
            wave_num: Wave number (1-based).
            state_manager: Live ``DispatchStateManager`` for state updates.

        Returns:
            List of ``DispatchItemRecord`` instances newly marked failed.
            Empty if no molecule is recorded for this wave or no stale PIDs.
        """
        wave_id = self.get_wave_id(milestone, wave_num)
        if wave_id is None:
            return []

        # PID liveness is checked via SQLite only; beads carries no PID data.
        wave_items = state_manager.get_wave_items(milestone, wave_num)
        stale: list[DispatchItemRecord] = []
        for item in wave_items:
            if item.status != "in-progress" or item.pid is None:
                continue
            try:
                os.kill(item.pid, 0)
            except OSError as exc:
                if isinstance(exc, PermissionError):
                    # Process alive but we lack permission to signal — skip.
                    pass
                else:
                    # ProcessLookupError or other OSError: PID is dead.
                    error_msg = f"Process died unexpectedly (PID {item.pid})"
                    state_manager.set_item_failed(
                        milestone=milestone, wave_num=wave_num, issue=item.issue, error=error_msg
                    )
                    stale.append(
                        DispatchItemRecord(
                            milestone=item.milestone,
                            wave_num=item.wave_num,
                            issue=item.issue,
                            title=item.title,
                            status="failed",
                            pid=item.pid,
                            started_at=item.started_at,
                            completed_at="",
                            result="",
                            error=error_msg,
                            cost=None,
                            result_file=item.result_file,
                            error_file=item.error_file,
                        )
                    )
        return stale


def dispatch_stale_check(
    state_manager: DispatchStateManager, milestone: int | None = None, wave_num: int | None = None
) -> list[DispatchItemRecord]:
    """Route stale-PID detection through beads or SQLite based on BACKLOG_BACKEND.

    When ``BACKLOG_BACKEND=beads`` and both *milestone* and *wave_num* are
    supplied, stale checking is scoped to a specific wave via
    ``BeadsDispatchAdapter.check_stale_members()``, which queries beads for
    wave members before checking PID liveness. For all other backends (or
    when milestone/wave_num are absent), falls back to
    ``DispatchStateManager.check_stale_pids()``, which scans all in-progress
    items globally.

    Note: this function operates on PID liveness and item completion state.
    It is distinct from the ``dispatch_stale_check`` MCP tool in
    ``server.py``, which checks plan freshness relative to a GitHub milestone.

    Args:
        state_manager: Live ``DispatchStateManager`` instance.
        milestone: Milestone number to scope the check (required for beads).
        wave_num: Wave number to scope the check (required for beads).

    Returns:
        List of ``DispatchItemRecord`` instances newly marked failed.
    """
    backend = os.environ.get("BACKLOG_BACKEND", "github")
    if backend == "beads" and milestone is not None and wave_num is not None:
        adapter = BeadsDispatchAdapter(state_manager.db_path)
        return adapter.check_stale_members(milestone, wave_num, state_manager)
    return state_manager.check_stale_pids()


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

from __future__ import annotations

import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from backlog_core.backends.sqlite_backend import SQLiteBackend
from backlog_core.errors import BacklogError
from backlog_core.models import BacklogItem, ContentKind, ContentRef, ContentWrite


def test_shared_connection_blocks_cross_operation_while_transaction_is_open(monkeypatch: pytest.MonkeyPatch) -> None:
    backend = SQLiteBackend(":memory:")
    transaction_started = threading.Event()
    release_transaction = threading.Event()
    work_item_started = threading.Event()
    work_item_completed = threading.Event()

    original_content_key = backend._content_key

    def pause_content_transaction(reference: ContentRef) -> tuple[str, str, str, str]:
        transaction_started.set()
        release_transaction.wait(timeout=1)
        return original_content_key(reference)

    def put_work_item() -> None:
        work_item_started.set()
        backend.put_work_item(BacklogItem(title="concurrent work item"))
        work_item_completed.set()

    monkeypatch.setattr(backend, "_content_key", pause_content_transaction)
    with ThreadPoolExecutor(max_workers=2) as executor:
        content_write = executor.submit(
            backend.put_content, ContentWrite(reference=ContentRef(kind=ContentKind.PLAN, name="P1"), content="content")
        )
        try:
            assert transaction_started.wait(timeout=1)
            work_item_write = executor.submit(put_work_item)
            assert work_item_started.wait(timeout=1)
            assert not work_item_completed.wait(timeout=0.1)
        finally:
            release_transaction.set()

        content_write.result()
        work_item_write.result()

    assert [item.title for item in backend.list_work_items()] == ["concurrent work item"]


def _build_legacy_db(path: Path, links: list[tuple[int, int]]) -> None:
    """Create a pre-``milestone_number`` database with an ``item_milestones`` join table."""
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE milestones (number INTEGER PRIMARY KEY, title TEXT NOT NULL, due_on TEXT,
            description TEXT, state TEXT NOT NULL DEFAULT 'open', created_at TEXT NOT NULL);
        CREATE TABLE items (issue_number INTEGER PRIMARY KEY, title TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open', body TEXT, created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL, closed_at TEXT);
        CREATE TABLE item_milestones (issue_number INTEGER NOT NULL, milestone_number INTEGER NOT NULL);
        INSERT INTO milestones (number, title, created_at) VALUES (1, 'm1', 't'), (2, 'm2', 't');
        INSERT INTO items (issue_number, title, created_at, updated_at) VALUES (7, 'seven', 't', 't');
        """
    )
    conn.executemany("INSERT INTO item_milestones VALUES (?, ?)", links)
    conn.commit()
    conn.close()


def test_migrate_schema_item_in_two_milestones_fails_closed_and_keeps_legacy_data(tmp_path: Path) -> None:
    db_path = tmp_path / "legacy.sqlite3"
    _build_legacy_db(db_path, [(7, 1), (7, 2)])

    with pytest.raises(BacklogError, match=r"#7"):
        SQLiteBackend(str(db_path))

    conn = sqlite3.connect(db_path)
    kept = conn.execute(
        "SELECT issue_number, milestone_number FROM item_milestones ORDER BY milestone_number"
    ).fetchall()
    columns = {row[1] for row in conn.execute("PRAGMA table_info(items)")}
    conn.close()
    assert kept == [(7, 1), (7, 2)]
    assert "milestone_number" not in columns


def test_migrate_schema_single_link_backfills_and_drops_legacy_table(tmp_path: Path) -> None:
    db_path = tmp_path / "legacy.sqlite3"
    _build_legacy_db(db_path, [(7, 2)])

    SQLiteBackend(str(db_path))

    conn = sqlite3.connect(db_path)
    milestone = conn.execute("SELECT milestone_number FROM items WHERE issue_number = 7").fetchone()
    legacy = conn.execute("SELECT name FROM sqlite_master WHERE name = 'item_milestones'").fetchone()
    conn.close()
    assert milestone == (2,)
    assert legacy is None

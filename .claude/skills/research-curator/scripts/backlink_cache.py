"""Store successful Marko extraction results by exact document content."""

from __future__ import annotations

import hashlib
import os
import sqlite3
import sys
from pathlib import Path

from pydantic import ValidationError

from backlink_models import CrossRefRow

_SCHEMA_VERSION = 1


def initialize_schema(connection: sqlite3.Connection) -> None:
    """Create the current disposable cache schema inside one transaction.

    Args:
        connection: Open SQLite connection configured for this cache.
    """
    connection.execute("BEGIN IMMEDIATE")
    try:
        current_version = connection.execute("PRAGMA user_version").fetchone()[0]
        if current_version != _SCHEMA_VERSION:
            connection.execute("DROP TABLE IF EXISTS extraction_rows")
            connection.execute("DROP TABLE IF EXISTS extractions")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS extractions (
                content_sha256 TEXT NOT NULL,
                parser_fingerprint TEXT NOT NULL,
                row_count INTEGER NOT NULL,
                PRIMARY KEY (content_sha256, parser_fingerprint)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS extraction_rows (
                content_sha256 TEXT NOT NULL,
                parser_fingerprint TEXT NOT NULL,
                ordinal INTEGER NOT NULL,
                entry_name TEXT NOT NULL,
                link_path TEXT NOT NULL,
                category TEXT NOT NULL,
                relationship TEXT NOT NULL,
                PRIMARY KEY (content_sha256, parser_fingerprint, ordinal),
                FOREIGN KEY (content_sha256, parser_fingerprint)
                    REFERENCES extractions (content_sha256, parser_fingerprint)
                    ON DELETE CASCADE
            )
            """
        )
        connection.execute(f"PRAGMA user_version = {_SCHEMA_VERSION}")
        connection.commit()
    except (OSError, sqlite3.Error):
        connection.rollback()
        raise


class CrossReferenceExtractionCache:
    """SQLite-backed cache keyed by exact content and parser fingerprints."""

    def __init__(self, path: Path) -> None:
        """Open or create the cache database at path."""
        path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(path, timeout=1.0)
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute("PRAGMA busy_timeout = 1000")
            initialize_schema(connection)
        except (OSError, sqlite3.Error):
            connection.close()
            raise
        self._connection = connection
        self._pending: dict[tuple[str, str], list[CrossRefRow]] = {}

    def get(self, content_sha256: str, parser_fingerprint: str) -> list[CrossRefRow] | None:
        """Return cached rows, including an empty extraction, or None on a miss."""
        key = (content_sha256, parser_fingerprint)
        pending = self._pending.get(key)
        if pending is not None:
            return list(pending)

        found = self._connection.execute(
            """
            SELECT row_count
            FROM extractions
            WHERE content_sha256 = ? AND parser_fingerprint = ?
            """,
            key,
        ).fetchone()
        if found is None:
            return None

        records = self._connection.execute(
            """
            SELECT entry_name, link_path, category, relationship
            FROM extraction_rows
            WHERE content_sha256 = ? AND parser_fingerprint = ?
            ORDER BY ordinal
            """,
            key,
        ).fetchall()
        try:
            rows = [
                CrossRefRow(
                    entry_name=cached_record[0],
                    link_path=cached_record[1],
                    category=cached_record[2],
                    relationship=cached_record[3],
                )
                for cached_record in records
            ]
        except ValidationError as exc:
            raise sqlite3.DatabaseError("cached extraction row failed validation") from exc
        if len(rows) != found[0]:
            raise sqlite3.DatabaseError("cached extraction row count does not match its manifest")
        return rows

    def put(self, content_sha256: str, parser_fingerprint: str, rows: list[CrossRefRow]) -> None:
        """Stage a successful extraction for one transaction at scan completion."""
        self._pending[content_sha256, parser_fingerprint] = list(rows)

    def commit(self) -> None:
        """Persist staged extractions without replacing entries written by another process."""
        with self._connection:
            for (content_sha256, parser_fingerprint), rows in self._pending.items():
                cursor = self._connection.execute(
                    """
                    INSERT OR IGNORE INTO extractions (content_sha256, parser_fingerprint, row_count)
                    VALUES (?, ?, ?)
                    """,
                    (content_sha256, parser_fingerprint, len(rows)),
                )
                if cursor.rowcount == 0:
                    continue
                self._connection.executemany(
                    """
                    INSERT INTO extraction_rows (
                        content_sha256,
                        parser_fingerprint,
                        ordinal,
                        entry_name,
                        link_path,
                        category,
                        relationship
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            content_sha256,
                            parser_fingerprint,
                            ordinal,
                            row.entry_name,
                            row.link_path,
                            row.category,
                            row.relationship,
                        )
                        for ordinal, row in enumerate(rows)
                    ],
                )
        self._pending.clear()

    def close(self) -> None:
        """Discard uncommitted staged rows and close the database connection."""
        self._pending.clear()
        self._connection.close()


def content_sha256(content: bytes) -> str:
    """Return the SHA-256 identity used for cache lookup."""
    return hashlib.sha256(content).hexdigest()


def default_cross_reference_cache_path(vault_root: Path) -> Path:
    """Return a stable user-cache path scoped to one resolved vault root."""
    configured = os.environ.get("RESEARCH_BACKLINK_CACHE_PATH")
    if configured:
        return Path(configured).expanduser()

    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))

    vault_identity = hashlib.sha256(os.fsencode(str(vault_root.resolve()))).hexdigest()[:20]
    return base / "claude-skills" / "research-backlinks" / f"{vault_identity}.sqlite3"

"""SQLite-backed implementation of the BacklogBackend Protocol.

Stores all backlog state in a local SQLite database file.  No PyGithub
dependency — uses only ``sqlite3`` from the standard library.

Schema (6 tables):
    items            — maps directly to BacklogItem fields
    item_tags        — replaces GitHub label system
    milestones       — maps to GitHub milestones
    item_milestones  — item-to-milestone association
    comments         — maps to GitHub issue comments
    projects         — maps to GitHub Projects V2

Branch operations are not supported; all five branch methods raise
``RuntimeError``.  The body column stores sections as JSON.

Usage::

    from backlog_core.backends.sqlite_backend import SQLiteBackend
    from backlog_core.backend_protocol import BacklogBackend, BacklogConfig, set_config

    backend = SQLiteBackend(":memory:")
    set_config(BacklogConfig(backend=backend))
    assert isinstance(backend, BacklogBackend)
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from github.Repository import Repository

    from backlog_core.models import Output, SamTask

from backlog_core import rendering as _rendering
from backlog_core.backend_protocol import IssueCommentNode, IssueNode, LabelNode, MilestoneFullNode
from backlog_core.models import (
    BackendAvailability,
    BackendStatus,
    BacklogItem,
    BacklogItemMetadata,
    BranchInfo,
    GroomedData,
    IssueLocalFields,
    IssueStatus,
    MergeResult,
    PullRequestRef,
    ViewItemResult,
)

__all__ = ["SQLiteBackend"]

# DDL executed once at startup — CREATE TABLE IF NOT EXISTS is idempotent.
_SCHEMA_SQL = """\
CREATE TABLE IF NOT EXISTS items (
    issue_number   INTEGER PRIMARY KEY,
    title          TEXT NOT NULL,
    status         TEXT NOT NULL DEFAULT 'open',
    body           TEXT,
    created_at     TEXT NOT NULL,
    updated_at     TEXT NOT NULL,
    closed_at      TEXT
);

CREATE TABLE IF NOT EXISTS item_tags (
    issue_number   INTEGER NOT NULL REFERENCES items(issue_number),
    tag            TEXT NOT NULL,
    UNIQUE(issue_number, tag)
);

CREATE TABLE IF NOT EXISTS milestones (
    number         INTEGER PRIMARY KEY,
    title          TEXT NOT NULL,
    due_on         TEXT,
    description    TEXT,
    state          TEXT NOT NULL DEFAULT 'open',
    created_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS item_milestones (
    issue_number      INTEGER NOT NULL REFERENCES items(issue_number),
    milestone_number  INTEGER NOT NULL REFERENCES milestones(number),
    PRIMARY KEY (issue_number, milestone_number)
);

CREATE TABLE IF NOT EXISTS comments (
    id             TEXT PRIMARY KEY,
    issue_number   INTEGER NOT NULL REFERENCES items(issue_number),
    body           TEXT NOT NULL,
    author         TEXT NOT NULL DEFAULT 'local',
    created_at     TEXT NOT NULL,
    updated_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS projects (
    id             TEXT PRIMARY KEY,
    number         INTEGER UNIQUE NOT NULL,
    title          TEXT NOT NULL,
    description    TEXT,
    created_at     TEXT NOT NULL
);

PRAGMA journal_mode=WAL;
"""


def _now() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(UTC).isoformat()


class SQLiteBackend:
    """SQLite-backed BacklogBackend for offline or local-only operation.

    All state lives in a single SQLite database file.  Every method is
    synchronous and has no network dependencies.  Branch operations are not
    supported and raise ``RuntimeError``.

    Args:
        db_path: Path to the SQLite database file, or ``:memory:`` for an
            ephemeral in-process database.  Defaults to ``:memory:``.
    """

    def __init__(self, db_path: str = ":memory:") -> None:
        """Initialise the SQLite database and create tables if absent.

        Args:
            db_path: Filesystem path to the database file, or ``:memory:``.
        """
        self._db_path = db_path
        self._conn = sqlite3.connect(db_path, check_same_thread=False, detect_types=sqlite3.PARSE_DECLTYPES)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA_SQL)
        self._conn.commit()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _next_issue_number(self) -> int:
        """Return the next auto-increment issue number."""
        row = self._conn.execute("SELECT COALESCE(MAX(issue_number), 0) + 1 FROM items").fetchone()
        return int(row[0])

    def _next_milestone_number(self) -> int:
        """Return the next auto-increment milestone number."""
        row = self._conn.execute("SELECT COALESCE(MAX(number), 0) + 1 FROM milestones").fetchone()
        return int(row[0])

    def _next_project_number(self) -> int:
        """Return the next auto-increment project number."""
        row = self._conn.execute("SELECT COALESCE(MAX(number), 0) + 1 FROM projects").fetchone()
        return int(row[0])

    def _row_to_issue_node(self, row: sqlite3.Row, tags: list[str] | None = None) -> IssueNode:
        """Convert a database row from ``items`` to an ``IssueNode``.

        Args:
            row: Row from the ``items`` table.
            tags: Pre-fetched tag list for this issue, or ``None`` to fetch now.

        Returns:
            ``IssueNode`` TypedDict populated from the row.
        """
        number = int(row["issue_number"])
        if tags is None:
            tag_rows = self._conn.execute("SELECT tag FROM item_tags WHERE issue_number = ?", (number,)).fetchall()
            tags = [r["tag"] for r in tag_rows]
        label_nodes: list[LabelNode] = [LabelNode(id=f"label-{t}", name=t) for t in tags]
        state = "OPEN" if str(row["status"]).lower() == "open" else "CLOSED"
        return IssueNode(
            id=f"sqlite-issue-{number}",
            number=number,
            title=row["title"],
            state=state,
            body=row["body"] or "",
            createdAt=row["created_at"],
            updatedAt=row["updated_at"],
            labels=label_nodes,
            milestone=None,
            assignees=[],
        )

    def _row_to_milestone_full(self, row: sqlite3.Row) -> MilestoneFullNode:
        """Convert a database row from ``milestones`` to a ``MilestoneFullNode``.

        Args:
            row: Row from the ``milestones`` table.

        Returns:
            ``MilestoneFullNode`` TypedDict populated from the row.
        """
        number = int(row["number"])
        open_count = int(
            self._conn.execute(
                "SELECT COUNT(*) FROM item_milestones im "
                "JOIN items i ON im.issue_number = i.issue_number "
                "WHERE im.milestone_number = ? AND i.status = 'open'",
                (number,),
            ).fetchone()[0]
        )
        closed_count = int(
            self._conn.execute(
                "SELECT COUNT(*) FROM item_milestones im "
                "JOIN items i ON im.issue_number = i.issue_number "
                "WHERE im.milestone_number = ? AND i.status != 'open'",
                (number,),
            ).fetchone()[0]
        )
        state = str(row["state"]).upper()
        return MilestoneFullNode(
            id=f"sqlite-milestone-{number}",
            number=number,
            title=row["title"],
            state=state,
            description=row["description"] or "",
            dueOn=row["due_on"],
            openIssueCount=open_count,
            closedIssueCount=closed_count,
        )

    # ------------------------------------------------------------------
    # Repository access
    # ------------------------------------------------------------------

    def get_github(self, repo: str = "", timeout: int = 15) -> Repository:  # type: ignore[return]
        """Raise RuntimeError — SQLiteBackend has no GitHub connection."""
        msg = "SQLiteBackend.get_github: no GitHub connection available"
        raise RuntimeError(msg)

    def try_get_github(self, repo: str = "") -> Repository | None:
        """Return None — SQLiteBackend has no GitHub connection."""
        return None

    def probe_backend_status(self, repo: str = "") -> BackendStatus:
        """Return REACHABLE status — SQLite backend is always available."""
        return BackendStatus(name="SQLite", availability=BackendAvailability.REACHABLE)

    # ------------------------------------------------------------------
    # GraphQL utilities (no-op — SQLite has no GraphQL layer)
    # ------------------------------------------------------------------

    def _graphql_request(
        self, repo: Repository, query: str, variables: dict[str, object] | None = None
    ) -> dict[str, Any]:
        """Return empty dict — SQLite backend has no GraphQL layer."""
        return {}

    def _resolve_labels_graphql(
        self, repo: Repository, repo_owner: str, repo_name: str, label_names: list[str]
    ) -> list[str]:
        """Return synthetic label node IDs — SQLite uses tag strings directly."""
        return [f"label-{name}" for name in label_names]

    # ------------------------------------------------------------------
    # Issue CRUD
    # ------------------------------------------------------------------

    def _fetch_issue_graphql(self, repo: Repository, owner: str, repo_name: str, issue_number: int) -> IssueNode:
        """Return the stored IssueNode for the given number.

        Args:
            repo: Ignored — SQLite has no GitHub connection.
            owner: Ignored.
            repo_name: Ignored.
            issue_number: Issue number to fetch.

        Returns:
            IssueNode for the given number.

        Raises:
            KeyError: When no item with ``issue_number`` exists.
        """
        row = self._conn.execute("SELECT * FROM items WHERE issue_number = ?", (issue_number,)).fetchone()
        if row is None:
            msg = f"SQLiteBackend: issue #{issue_number} not found"
            raise KeyError(msg)
        return self._row_to_issue_node(row)

    def _fetch_issues_graphql(
        self,
        repo: Repository,
        owner: str,
        repo_name: str,
        state: str = "OPEN",
        labels: list[str] | None = None,
        milestone_number: int | None = None,
        first: int = 100,
        since: str | None = None,
    ) -> list[IssueNode]:
        """Return issues filtered by state, labels, and milestone.

        Args:
            repo: Ignored.
            owner: Ignored.
            repo_name: Ignored.
            state: ``"OPEN"`` or ``"CLOSED"``.
            labels: Optional label names to filter by (all must match).
            milestone_number: Optional milestone number to filter by.
            first: Maximum results to return.
            since: Ignored (SQLite filtering by date not implemented).

        Returns:
            List of ``IssueNode`` TypedDicts.
        """
        db_status = "open" if state.upper() == "OPEN" else "closed"
        rows = self._conn.execute(
            "SELECT * FROM items WHERE status = ? ORDER BY issue_number LIMIT ?", (db_status, first)
        ).fetchall()

        nodes = [self._row_to_issue_node(r) for r in rows]

        if labels:
            label_set = set(labels)
            nodes = [n for n in nodes if any(lbl["name"] in label_set for lbl in n["labels"])]

        if milestone_number is not None:
            milestone_numbers = {
                int(r["issue_number"])
                for r in self._conn.execute(
                    "SELECT issue_number FROM item_milestones WHERE milestone_number = ?", (milestone_number,)
                ).fetchall()
            }
            nodes = [n for n in nodes if n["number"] in milestone_numbers]

        return nodes

    def _update_issue_graphql(
        self,
        repo: Repository,
        issue_node_id: str,
        *,
        state: str | None = None,
        body: str | None = None,
        title: str | None = None,
        label_ids: list[str] | None = None,
        milestone_id: str | None = None,
    ) -> None:
        """Update an issue's mutable fields in place.

        Args:
            repo: Ignored.
            issue_node_id: Node ID in the form ``"sqlite-issue-{number}"``.
            state: New state (``"OPEN"`` or ``"CLOSED"``), or ``None``.
            body: New body text, or ``None``.
            title: New title, or ``None``.
            label_ids: Replacement label IDs, or ``None``.
            milestone_id: Ignored in SQLite backend.
        """
        number = self._issue_number_for_node_id(issue_node_id)
        if state is not None:
            db_state = "open" if state.upper() == "OPEN" else "closed"
            self._conn.execute(
                "UPDATE items SET status = ?, updated_at = ? WHERE issue_number = ?", (db_state, _now(), number)
            )
        if body is not None:
            self._conn.execute(
                "UPDATE items SET body = ?, updated_at = ? WHERE issue_number = ?", (body, _now(), number)
            )
        if title is not None:
            self._conn.execute(
                "UPDATE items SET title = ?, updated_at = ? WHERE issue_number = ?", (title, _now(), number)
            )
        if label_ids is not None:
            # Convert synthetic IDs back to tag names: "label-{name}" -> "{name}"
            new_tags = [lid.removeprefix("label-") for lid in label_ids]
            self._conn.execute("DELETE FROM item_tags WHERE issue_number = ?", (number,))
            for tag in new_tags:
                self._conn.execute("INSERT OR IGNORE INTO item_tags (issue_number, tag) VALUES (?, ?)", (number, tag))
        self._conn.commit()

    def _issue_number_for_node_id(self, node_id: str) -> int:
        """Resolve a synthetic node ID to an issue number.

        Args:
            node_id: Node ID in the form ``"sqlite-issue-{number}"``.

        Returns:
            The integer issue number.

        Raises:
            KeyError: When the node ID does not match the expected pattern.
        """
        prefix = "sqlite-issue-"
        if not node_id.startswith(prefix):
            msg = f"SQLiteBackend: unrecognised node ID {node_id!r}"
            raise KeyError(msg)
        return int(node_id.removeprefix(prefix))

    def sync_issues_graphql(
        self,
        repo: Repository,
        owner: str,
        repo_name: str,
        *,
        state: str = "OPEN",
        labels: list[str] | None = None,
        milestone_number: int | None = None,
        since: datetime | None = None,
        callback: Callable[[IssueNode], None] | None = None,
        track_timestamp: bool = False,
    ) -> list[IssueNode]:
        """Return stored issues, calling callback for each.

        Args:
            repo: Ignored.
            owner: Ignored.
            repo_name: Ignored.
            state: Issue state filter.
            labels: Optional label names to filter by.
            milestone_number: Optional milestone number to filter by.
            since: Ignored.
            callback: Optional function called for each fetched IssueNode.
            track_timestamp: Ignored.

        Returns:
            List of ``IssueNode`` TypedDicts.
        """
        issues = self._fetch_issues_graphql(
            repo, owner, "", state=state, labels=labels, milestone_number=milestone_number
        )
        if callback is not None:
            for issue in issues:
                callback(issue)
        return issues

    def create_issue_for_item(
        self, repo: Repository, item: BacklogItem, dry_run: bool = False, output: Output | None = None
    ) -> int | None:
        """Create an issue from a BacklogItem and return its number.

        Args:
            repo: Ignored.
            item: BacklogItem to persist.
            dry_run: When ``True``, return ``None`` without writing.
            output: Ignored.

        Returns:
            Issue number on success, ``None`` on dry run.
        """
        if dry_run:
            return None
        number = self._next_issue_number()
        body = json.dumps(item.sections if hasattr(item, "sections") else {})
        ts = _now()
        self._conn.execute(
            "INSERT INTO items (issue_number, title, status, body, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (number, item.title, "open", body, ts, ts),
        )
        self._conn.commit()
        return number

    def close_github_issue(
        self,
        issue_ref: str,
        reason: str,
        *,
        reference: str = "",
        comment: str = "",
        repo: str = "",
        output: Output | None = None,
    ) -> None:
        """Close an issue by reference.

        Args:
            issue_ref: Issue number as string (with optional ``#`` prefix).
            reason: Ignored.
            reference: Ignored.
            comment: Ignored.
            repo: Ignored.
            output: Ignored.
        """
        number = int(issue_ref.lstrip("#"))
        self._conn.execute(
            "UPDATE items SET status = 'closed', updated_at = ?, closed_at = ? WHERE issue_number = ?",
            (_now(), _now(), number),
        )
        self._conn.commit()

    def resolve_github_issue(
        self,
        issue_ref: str,
        *,
        summary: str,
        method: str = "",
        notes: str = "",
        follow_ups: str = "",
        findings: str = "",
        repo: str = "",
        output: Output | None = None,
    ) -> None:
        """Resolve (close) an issue with a resolution comment.

        Args:
            issue_ref: Issue number as string (with optional ``#`` prefix).
            summary: Ignored (stored as comment if issue exists).
            method: Ignored.
            notes: Ignored.
            follow_ups: Ignored.
            findings: Ignored.
            repo: Ignored.
            output: Ignored.
        """
        number = int(issue_ref.lstrip("#"))
        self._conn.execute(
            "UPDATE items SET status = 'closed', updated_at = ?, closed_at = ? WHERE issue_number = ?",
            (_now(), _now(), number),
        )
        self._conn.commit()

    def fetch_open_issues_by_title(self, repo: Repository) -> dict[str, int]:
        """Return a mapping of open issue titles to issue numbers.

        Args:
            repo: Ignored.

        Returns:
            Dict mapping issue title to issue number.
        """
        rows = self._conn.execute("SELECT title, issue_number FROM items WHERE status = 'open'").fetchall()
        return {str(row["title"]): int(row["issue_number"]) for row in rows}

    def fetch_github_issue_body(self, repo_obj: Repository, issue_num: int, output: Output | None = None) -> str | None:
        """Return the body of the stored issue, or None if not found.

        Args:
            repo_obj: Ignored.
            issue_num: Issue number.
            output: Ignored.

        Returns:
            Body string, or ``None`` if the issue does not exist.
        """
        row = self._conn.execute("SELECT body FROM items WHERE issue_number = ?", (issue_num,)).fetchone()
        return str(row["body"]) if row is not None else None

    def check_open_prs_for_issue(self, issue_num: int, repo: str = "") -> list[PullRequestRef]:
        """Return empty list — SQLite backend has no pull requests.

        Args:
            issue_num: Ignored.
            repo: Ignored.

        Returns:
            Empty list.
        """
        return []

    def batch_fetch_statuses(self, items: list[BacklogItem], repo: str = "") -> dict[int, IssueStatus]:
        """Return statuses for items that have issue numbers.

        Args:
            items: BacklogItems to query (must have issue_number set).
            repo: Ignored.

        Returns:
            Dict mapping issue_number to IssueStatus.
        """
        result: dict[int, IssueStatus] = {}
        for item in items:
            raw_issue = getattr(item.metadata, "issue", "") or ""
            if not raw_issue:
                continue
            num = int(str(raw_issue).lstrip("#"))
            row = self._conn.execute("SELECT status FROM items WHERE issue_number = ?", (num,)).fetchone()
            if row is not None:
                result[num] = IssueStatus(status=str(row["status"]))
        return result

    def fetch_item_status(self, item: BacklogItem, repo: str = "", output: Output | None = None) -> str:
        """Return the status string for a single item.

        Args:
            item: BacklogItem to query.
            repo: Ignored.
            output: Ignored.

        Returns:
            Status string (e.g. ``"open"``, ``"closed"``).
        """
        raw_issue = getattr(item.metadata, "issue", "") or ""
        if not raw_issue:
            return "open"
        num = int(str(raw_issue).lstrip("#"))
        row = self._conn.execute("SELECT status FROM items WHERE issue_number = ?", (num,)).fetchone()
        return str(row["status"]) if row is not None else "open"

    def view_enrich_from_github(self, result: ViewItemResult, issue_num: str, repo: str = "") -> bool:
        """Enrich a ViewItemResult from stored issue data.

        Args:
            result: ViewItemResult to enrich in place.
            issue_num: Issue number string (with optional ``#`` prefix).
            repo: Ignored.

        Returns:
            ``True`` if enrichment succeeded, ``False`` if not found.
        """
        try:
            num = int(issue_num.lstrip("#"))
        except ValueError:
            return False
        row = self._conn.execute("SELECT * FROM items WHERE issue_number = ?", (num,)).fetchone()
        if row is None:
            return False
        state = str(row["status"])
        result.state = state
        result.body = str(row["body"] or "")
        result.number = num
        return True

    def issue_to_local_fields(self, issue: IssueNode) -> IssueLocalFields:
        """Convert an IssueNode to IssueLocalFields.

        Args:
            issue: IssueNode TypedDict.

        Returns:
            IssueLocalFields model populated from the issue.
        """
        return IssueLocalFields(title=issue["title"], body=issue["body"], status=issue["state"].lower())

    # ------------------------------------------------------------------
    # Issue comments
    # ------------------------------------------------------------------

    def _add_comment_graphql(self, repo: Repository, issue_node_id: str, body: str) -> str:
        """Add a comment to an issue and return its ID.

        Args:
            repo: Ignored.
            issue_node_id: Node ID in the form ``"sqlite-issue-{number}"``.
            body: Comment body text.

        Returns:
            UUID string for the new comment.
        """
        number = self._issue_number_for_node_id(issue_node_id)
        comment_id = str(uuid.uuid4())
        ts = _now()
        self._conn.execute(
            "INSERT INTO comments (id, issue_number, body, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (comment_id, number, body, ts, ts),
        )
        self._conn.commit()
        return comment_id

    def _fetch_issue_comments_graphql(
        self, repo: Repository, owner: str, repo_name: str, issue_number: int
    ) -> list[IssueCommentNode]:
        """Return all comments on the issue.

        Args:
            repo: Ignored.
            owner: Ignored.
            repo_name: Ignored.
            issue_number: Issue number.

        Returns:
            List of ``IssueCommentNode`` TypedDicts.
        """
        rows = self._conn.execute(
            "SELECT * FROM comments WHERE issue_number = ? ORDER BY created_at", (issue_number,)
        ).fetchall()
        return [
            IssueCommentNode(
                id=str(row["id"]),
                body=str(row["body"]),
                url=f"sqlite://{self._db_path}/comments/{row['id']}",
                author=str(row["author"]),
                created_at=str(row["created_at"]),
                updated_at=str(row["updated_at"]),
            )
            for row in rows
        ]

    def _fetch_comment_by_id_graphql(self, repo: Repository, comment_node_id: str) -> IssueCommentNode:
        """Return a comment by its ID.

        Args:
            repo: Ignored.
            comment_node_id: UUID string of the comment.

        Returns:
            ``IssueCommentNode`` TypedDict.

        Raises:
            KeyError: When no comment with ``comment_node_id`` exists.
        """
        row = self._conn.execute("SELECT * FROM comments WHERE id = ?", (comment_node_id,)).fetchone()
        if row is None:
            msg = f"SQLiteBackend: comment {comment_node_id!r} not found"
            raise KeyError(msg)
        return IssueCommentNode(
            id=str(row["id"]),
            body=str(row["body"]),
            url=f"sqlite://{self._db_path}/comments/{row['id']}",
            author=str(row["author"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    def _update_issue_comment_graphql(self, repo: Repository, comment_node_id: str, body: str) -> None:
        """Update a comment's body.

        Args:
            repo: Ignored.
            comment_node_id: UUID string of the comment.
            body: New body text.
        """
        self._conn.execute("UPDATE comments SET body = ?, updated_at = ? WHERE id = ?", (body, _now(), comment_node_id))
        self._conn.commit()

    # ------------------------------------------------------------------
    # Status mutations
    # ------------------------------------------------------------------

    def apply_status_in_progress(self, item: BacklogItem, repo: str = "", output: Output | None = None) -> None:
        """Store an in-progress tag on the item's issue row.

        Args:
            item: BacklogItem to update.
            repo: Ignored.
            output: Ignored.
        """
        raw_issue = getattr(item.metadata, "issue", "") or ""
        if not raw_issue:
            return
        num = int(str(raw_issue).lstrip("#"))
        self._conn.execute("INSERT OR IGNORE INTO item_tags (issue_number, tag) VALUES (?, 'in-progress')", (num,))
        self._conn.commit()

    def apply_status_verified(self, item: BacklogItem, repo: str = "", output: Output | None = None) -> None:
        """Store a verified tag on the item's issue row.

        Args:
            item: BacklogItem to update.
            repo: Ignored.
            output: Ignored.
        """
        raw_issue = getattr(item.metadata, "issue", "") or ""
        if not raw_issue:
            return
        num = int(str(raw_issue).lstrip("#"))
        self._conn.execute("INSERT OR IGNORE INTO item_tags (issue_number, tag) VALUES (?, 'verified')", (num,))
        self._conn.commit()

    def apply_status_groomed(self, item: BacklogItem, repo: str = "", output: Output | None = None) -> None:
        """Store a groomed tag on the item's issue row.

        Args:
            item: BacklogItem to update.
            repo: Ignored.
            output: Ignored.
        """
        raw_issue = getattr(item.metadata, "issue", "") or ""
        if not raw_issue:
            return
        num = int(str(raw_issue).lstrip("#"))
        self._conn.execute("INSERT OR IGNORE INTO item_tags (issue_number, tag) VALUES (?, 'groomed')", (num,))
        self._conn.commit()

    def sync_groomed_to_github_issue(
        self,
        repo_obj: Repository,
        issue_num: int,
        groomed_content: str,
        section_name: str | None = None,
        output: Output | None = None,
    ) -> bool:
        """Append groomed content to an issue body; return True if changed.

        Args:
            repo_obj: Ignored.
            issue_num: Issue number to update.
            groomed_content: Markdown content to append.
            section_name: Optional heading override.
            output: Ignored.

        Returns:
            ``True`` if the issue body was updated, ``False`` if not found.
        """
        row = self._conn.execute("SELECT body FROM items WHERE issue_number = ?", (issue_num,)).fetchone()
        if row is None:
            return False
        heading = section_name or "Groomed"
        current = str(row["body"] or "")
        new_body = f"{current}\n\n## {heading}\n\n{groomed_content}"
        self._conn.execute(
            "UPDATE items SET body = ?, updated_at = ? WHERE issue_number = ?", (new_body, _now(), issue_num)
        )
        self._conn.commit()
        return True

    # ------------------------------------------------------------------
    # Milestones and projects
    # ------------------------------------------------------------------

    def _fetch_milestones_graphql(
        self, repo: Repository, owner: str, repo_name: str, states: list[str] | None = None
    ) -> list[MilestoneFullNode]:
        """Return stored milestones, optionally filtered by state.

        Args:
            repo: Ignored.
            owner: Ignored.
            repo_name: Ignored.
            states: Optional list of state filters (e.g. ``["OPEN", "CLOSED"]``).

        Returns:
            List of ``MilestoneFullNode`` TypedDicts.
        """
        rows = self._conn.execute("SELECT * FROM milestones").fetchall()
        if states:
            state_set = {s.lower() for s in states}
            rows = [r for r in rows if str(r["state"]).lower() in state_set]
        return [self._row_to_milestone_full(r) for r in rows]

    def _projects_v2_list_query(self, owner: str, limit: int = 20) -> tuple[str, dict[str, object]]:
        """Return stub query/variables — SQLite has no GraphQL layer.

        Args:
            owner: Ignored.
            limit: Ignored.

        Returns:
            Empty query string and variables dict.
        """
        return ("", {"owner": owner, "limit": limit})

    def _projects_v2_create_mutation(self, owner_id: str, title: str) -> tuple[str, dict[str, object]]:
        """Return stub mutation/variables — SQLite has no GraphQL layer.

        Args:
            owner_id: Ignored.
            title: Ignored.

        Returns:
            Empty mutation string and variables dict.
        """
        return ("", {"ownerId": owner_id, "title": title})

    # ------------------------------------------------------------------
    # Task issues
    # ------------------------------------------------------------------

    def create_task_issue(
        self,
        repo: Repository,
        parent_issue_number: int,
        task: SamTask,
        description: str = "",
        acceptance_criteria: list[str] | None = None,
        labels: list[str] | None = None,
        output: Output | None = None,
    ) -> IssueNode | None:
        """Create a child task issue and return its IssueNode.

        Args:
            repo: Ignored.
            parent_issue_number: Ignored (SQLite has no parent tracking).
            task: SamTask model describing the task.
            description: Optional task description.
            acceptance_criteria: Ignored.
            labels: Optional label names to apply.
            output: Ignored.

        Returns:
            ``IssueNode`` of the created issue.
        """
        number = self._next_issue_number()
        task_type = getattr(task, "task_type", "") or ""
        task_desc = getattr(task, "description", "") or task.task_id
        title = (
            f"[{task.feature}/{task.task_id}] {task_type}: {task_desc}"
            if task_type
            else f"[{task.feature}/{task.task_id}] {task_desc}"
        )
        body = description or task_desc
        ts = _now()
        self._conn.execute(
            "INSERT INTO items (issue_number, title, status, body, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (number, title, "open", body, ts, ts),
        )
        if labels:
            for tag in labels:
                self._conn.execute("INSERT OR IGNORE INTO item_tags (issue_number, tag) VALUES (?, ?)", (number, tag))
        self._conn.commit()
        row = self._conn.execute("SELECT * FROM items WHERE issue_number = ?", (number,)).fetchone()
        return self._row_to_issue_node(row)

    def get_task_issues(
        self, repo: Repository, parent_issue_number: int, output: Output | None = None
    ) -> list[IssueNode]:
        """Return all stored issues (SQLite backend has no parent tracking).

        Args:
            repo: Ignored.
            parent_issue_number: Ignored.
            output: Ignored.

        Returns:
            All stored issue nodes.
        """
        rows = self._conn.execute("SELECT * FROM items ORDER BY issue_number").fetchall()
        return [self._row_to_issue_node(r) for r in rows]

    def update_task_status(
        self, repo: Repository, issue_number: int, new_status: str, output: Output | None = None
    ) -> bool:
        """Update issue state; return True if the state changed.

        Args:
            repo: Ignored.
            issue_number: Issue number to update.
            new_status: New status string.
            output: Ignored.

        Returns:
            ``True`` if the state changed, ``False`` otherwise.
        """
        row = self._conn.execute("SELECT status FROM items WHERE issue_number = ?", (issue_number,)).fetchone()
        if row is None:
            return False
        new_db_state = "closed" if new_status.lower() in {"closed", "done", "complete", "resolved"} else "open"
        if str(row["status"]) == new_db_state:
            return False
        self._conn.execute(
            "UPDATE items SET status = ?, updated_at = ? WHERE issue_number = ?", (new_db_state, _now(), issue_number)
        )
        self._conn.commit()
        return True

    # ------------------------------------------------------------------
    # Sync / serialisation
    # ------------------------------------------------------------------

    def render_issue_body(self, item: BacklogItem, original_body: str | None = None) -> str:
        """Render a BacklogItem to a JSON body string.

        SQLite stores sections as JSON rather than GitHub-flavoured Markdown.

        Args:
            item: BacklogItem to serialise.
            original_body: Ignored.

        Returns:
            JSON string of the sections dict.
        """
        sections = item.sections if hasattr(item, "sections") else {}
        return json.dumps(sections)

    def parse_issue_body(self, body: str, existing: BacklogItem | None = None) -> BacklogItem:
        """Deserialise a JSON body string into a BacklogItem.

        Args:
            body: Raw body string (JSON or plain text).
            existing: Optional existing BacklogItem to return unchanged.

        Returns:
            Populated BacklogItem model.
        """
        if existing is not None:
            return existing
        try:
            sections = json.loads(body)
            title = str(sections.get("title", "Untitled")) if isinstance(sections, dict) else "Untitled"
            description = str(sections.get("description", body)) if isinstance(sections, dict) else body
        except (json.JSONDecodeError, ValueError):
            lines = body.splitlines()
            title = lines[0].lstrip("# ").strip() if lines else "Untitled"
            description = "\n".join(lines[1:]).strip()
        return BacklogItem(
            title=title,
            description=description,
            metadata=BacklogItemMetadata(
                source="sqlite",
                added=datetime.now(UTC).date().isoformat(),
                priority="P1",
                item_type="Feature",
                status="open",
            ),
        )

    def merge_item(self, local: BacklogItem, remote: BacklogItem) -> BacklogItem:
        """Return remote as the merge winner (remote is source of truth).

        Args:
            local: Local BacklogItem state.
            remote: Remote BacklogItem state.

        Returns:
            The remote item unchanged.
        """
        return remote

    def unknown_key_to_heading(self, key: str) -> str:
        """Convert an unknown section key to a markdown heading string.

        Delegates to :func:`backlog_core.rendering.unknown_key_to_heading` to
        strip the ``"unknown__"`` prefix before title-casing.

        Returns:
            Heading text string (e.g. ``"Rt Ica"`` for ``"unknown__rt_ica"``).
        """
        return _rendering.unknown_key_to_heading(key)

    @property
    def section_heading(self) -> dict[str, str]:
        """Return the mapping of section key to display heading.

        Returns:
            Dict mapping section storage key to display heading string.
        """
        return _rendering.SECTION_HEADING

    def render_groomed_section(self, groomed: GroomedData) -> str:
        """Render a GroomedData as ``## Groomed ({date})`` with subsection children.

        Args:
            groomed: GroomedData to render.

        Returns:
            Rendered section string (no trailing newline).
        """
        return _rendering.render_groomed_section(groomed)

    def section_display_title(self, key: str, groomed_date: str = "") -> str:
        """Return the human-readable title for a section storage key.

        Args:
            key: Section storage key (e.g. ``"fact_check"``).
            groomed_date: Optional date string for the ``"groomed"`` key.

        Returns:
            Display title string (e.g. ``"Fact-Check"``).
        """
        return _rendering.section_display_title(key, groomed_date)

    # ------------------------------------------------------------------
    # Integration branches — not supported by SQLite backend
    # ------------------------------------------------------------------

    def create_integration_branch(
        self,
        milestone_number: int,
        slug: str,
        *,
        base_branch: str = "main",
        repo: str = "",
        output: Output | None = None,
    ) -> BranchInfo:
        """Raise RuntimeError — branch operations require GitHub backend.

        Args:
            milestone_number: Ignored.
            slug: Ignored.
            base_branch: Ignored.
            repo: Ignored.
            output: Ignored.

        Raises:
            RuntimeError: Always — branch operations not supported.
        """
        msg = "SQLiteBackend: branch operations not supported; use the GitHub backend"
        raise RuntimeError(msg)

    def get_integration_branch_status(
        self, branch_name: str, *, repo: str = "", output: Output | None = None
    ) -> BranchInfo | None:
        """Raise RuntimeError — branch operations require GitHub backend.

        Args:
            branch_name: Ignored.
            repo: Ignored.
            output: Ignored.

        Raises:
            RuntimeError: Always — branch operations not supported.
        """
        msg = "SQLiteBackend: branch operations not supported; use the GitHub backend"
        raise RuntimeError(msg)

    def merge_integration_branch(
        self, head_branch: str, base_branch: str, commit_message: str, *, repo: str = "", output: Output | None = None
    ) -> MergeResult:
        """Raise RuntimeError — branch operations require GitHub backend.

        Args:
            head_branch: Ignored.
            base_branch: Ignored.
            commit_message: Ignored.
            repo: Ignored.
            output: Ignored.

        Raises:
            RuntimeError: Always — branch operations not supported.
        """
        msg = "SQLiteBackend: branch operations not supported; use the GitHub backend"
        raise RuntimeError(msg)

    def delete_integration_branch(self, branch_name: str, *, repo: str = "", output: Output | None = None) -> bool:
        """Raise RuntimeError — branch operations require GitHub backend.

        Args:
            branch_name: Ignored.
            repo: Ignored.
            output: Ignored.

        Raises:
            RuntimeError: Always — branch operations not supported.
        """
        msg = "SQLiteBackend: branch operations not supported; use the GitHub backend"
        raise RuntimeError(msg)

    def list_integration_branches(self, *, repo: str = "", output: Output | None = None) -> list[BranchInfo]:
        """Raise RuntimeError — branch operations require GitHub backend.

        Args:
            repo: Ignored.
            output: Ignored.

        Raises:
            RuntimeError: Always — branch operations not supported.
        """
        msg = "SQLiteBackend: branch operations not supported; use the GitHub backend"
        raise RuntimeError(msg)

#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "duckdb>=1.0.0",
#     "typer>=0.21.0"
# ]
# ///
"""Session Historian — query and summarize Claude Code JSONL session transcripts.

Commands:
    list       — list recent sessions with metadata
    messages   — print verbatim user messages for a session
    search     — search raw JSONL files for text
    index      — build/rebuild the DuckDB session index
    show       — show session summary from cache (or generate structure)
"""

from __future__ import annotations

import hashlib
import json
import operator
import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import duckdb
import typer
from rich import box
from rich.console import Console
from rich.measure import Measurement
from rich.panel import Panel
from rich.table import Table

if TYPE_CHECKING:
    from collections.abc import Iterator

app = typer.Typer(
    name="session-historian",
    help="Query Claude Code JSONL session history with DuckDB indexing.",
    rich_markup_mode="rich",
    no_args_is_help=True,
)

stderr = Console(stderr=True)
stdout = Console()

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECTS_DIR = Path("~/.claude/projects").expanduser()
CACHE_DIR = Path("~/.claude/kaizen").expanduser()
DB_PATH = CACHE_DIR / "session-index.duckdb"
SUMMARIES_DIR = CACHE_DIR / "session-summaries"

# ---------------------------------------------------------------------------
# JSONL parsing
# ---------------------------------------------------------------------------

_NOISE_PREFIXES = (
    "<local-command-caveat>",
    "<bash-stdout>",
    "<tool_use_error>",
    "<task-notification>",
    "<command-message>",
    "<system-reminder>",
)

_CORRECTION_PHRASES = (
    "that's wrong",
    "no,",
    "stop",
    "undo",
    "revert",
    "don't",
    "not what i asked",
    "wrong",
    "incorrect",
    "that's not",
)

_STUCK_LOOP_THRESHOLD: int = 3


def _extract_text(content: str | list[str | dict] | None) -> str:
    """Extract plain text from a message content field.

    Args:
        content: Raw content value from a JSONL record. May be a plain string,
            a list of content blocks (dicts with ``type`` and ``text`` keys),
            or ``None``.

    Returns:
        Concatenated text from all ``text``-type blocks, joined by newlines.
        Returns an empty string when ``content`` is ``None`` or contains no
        text blocks.
    """
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    parts: list[str] = []
    for element in content:
        if isinstance(element, dict) and element.get("type") == "text":
            text = element.get("text")
            if isinstance(text, str):
                parts.append(text)
    return "\n".join(parts)


def _is_noise(text: str) -> bool:
    """Return True when a message starts with a known noise prefix.

    Args:
        text: The plain-text content of a user message.

    Returns:
        ``True`` if the stripped text begins with any prefix in
        ``_NOISE_PREFIXES``, ``False`` otherwise.
    """
    stripped = text.lstrip()
    return any(stripped.startswith(p) for p in _NOISE_PREFIXES)


def _iter_records(path: Path) -> Iterator[dict]:
    """Yield valid JSON records from a JSONL file.

    Args:
        path: Filesystem path to a ``.jsonl`` file.

    Yields:
        Parsed JSON objects. Lines that are empty or fail to parse
        are silently skipped. Non-dict objects are also skipped.
    """
    with path.open(encoding="utf-8", errors="replace") as fh:
        for raw_line in fh:
            stripped = raw_line.strip()
            if not stripped:
                continue
            try:
                rec = json.loads(stripped)
                if isinstance(rec, dict):
                    yield rec
            except json.JSONDecodeError:
                continue


def _slug_to_project_name(slug: str) -> str:
    """Convert a filesystem slug (directory name) to a human-readable project name.

    The slug format used by Claude Code encodes the full filesystem path of the
    project as a hyphen-separated string. This function strips leading path
    components (home directory, username, and optional location token) to
    return only the project portion.

    Args:
        slug: A hyphen-separated directory slug, e.g.
            ``"home-alice-repos-my-project"``.

    Returns:
        The project name portion of the slug, e.g. ``"my-project"``.  Falls
        back to the original ``slug`` when no identifiable prefix is found.
    """
    parts = [p for p in slug.split("-") if p]
    location_tokens = {"repos", "Desktop", "Documents", "Projects", "src", "code", "work"}
    idx = 0
    if idx < len(parts) and parts[idx] == "home":
        idx += 1
    if idx < len(parts):
        idx += 1  # username
    if idx < len(parts) and parts[idx] in location_tokens:
        idx += 1
    return "-".join(parts[idx:]) if idx < len(parts) else slug


# ---------------------------------------------------------------------------
# DuckDB index
# ---------------------------------------------------------------------------

_DDL = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id       TEXT NOT NULL,
    file_path        TEXT NOT NULL,
    project_slug     TEXT,
    project_name     TEXT,
    first_ts         TEXT,
    last_ts          TEXT,
    total_records    INTEGER,
    user_msg_count   INTEGER,
    assistant_turns  INTEGER,
    file_size_kb     DOUBLE,
    has_summary      BOOLEAN DEFAULT FALSE,
    indexed_at       TEXT,
    PRIMARY KEY (session_id, file_path)
);

CREATE TABLE IF NOT EXISTS user_messages (
    session_id   TEXT NOT NULL,
    file_path    TEXT NOT NULL,
    msg_index    INTEGER NOT NULL,
    timestamp    TEXT,
    content      TEXT,
    word_count   INTEGER,
    PRIMARY KEY (session_id, msg_index)
);
"""


def _open_db() -> duckdb.DuckDBPyConnection:
    """Open (or create) the DuckDB session index and ensure schema exists.

    Creates ``CACHE_DIR`` and its parents if they do not already exist, then
    connects to ``DB_PATH`` and runs the DDL to create any missing tables.

    Returns:
        An open ``DuckDBPyConnection`` with the session schema initialised.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB_PATH))
    con.execute(_DDL)
    return con


def _fetch_count(con: duckdb.DuckDBPyConnection, sql: str, params: list | None = None) -> int:
    """Execute a COUNT query and return the integer result.

    Args:
        con: An open DuckDB connection.
        sql: A SQL query whose first column in the first row is the count.
        params: Optional positional parameters for the query.

    Returns:
        The integer value of the first column of the first row, or ``0`` if
        no rows are returned.
    """
    row = con.execute(sql, params or []).fetchone()
    return int(row[0]) if row else 0


def _resolve_session(con: duckdb.DuckDBPyConnection, session_id: str) -> tuple[str, Path]:
    """Resolve session ID (including 'last' alias) to (resolved_id, jsonl_path).

    Handles the ``"last"`` alias by querying the most recently active session,
    and supports prefix matching via ``LIKE`` for short session IDs.

    Args:
        con: An open DuckDB connection with the session schema initialised.
        session_id: Full or prefix session ID, or the literal string ``"last"``
            to select the most recently active session.

    Returns:
        A tuple of ``(resolved_session_id, Path(file_path))`` on success.

    Raises:
        typer.Exit: With exit code 1 when no sessions are indexed, the
            session ID is not found, or the JSONL file is missing on disk.
    """
    if session_id == "last":
        row = con.execute("SELECT session_id FROM sessions ORDER BY last_ts DESC LIMIT 1").fetchone()
        if not row:
            stderr.print("[red]No sessions indexed. Run 'index' first.[/red]")
            raise typer.Exit(1)
        session_id = row[0]

    row = con.execute(
        "SELECT session_id, file_path FROM sessions WHERE session_id LIKE ? ORDER BY last_ts DESC LIMIT 1",
        [f"{session_id}%"],
    ).fetchone()

    if not row:
        stderr.print(f"[red]Session '{session_id}' not found in index. Run 'list' to see valid IDs.[/red]")
        raise typer.Exit(1)

    resolved_id, file_path_str = row
    path = Path(file_path_str)
    if not path.exists():
        stderr.print(f"[red]JSONL file not found on disk: {file_path_str}[/red]")
        raise typer.Exit(1)

    return resolved_id, path


@dataclass
class _FileStats:
    slug: str
    project_name: str
    first_ts: str
    last_ts: str
    total_records: int
    user_msgs: list[dict]
    assistant_turns: int
    file_kb: float
    now: str


def _scan_records(path: Path, records: list[dict]) -> _FileStats:
    """Extract statistics from parsed JSONL records.

    Args:
        path: Path to the source ``.jsonl`` file (used to derive the slug).
        records: Pre-parsed list of record dicts from the file.

    Returns:
        A ``_FileStats`` dataclass populated with aggregated metadata including
        timestamps, user message list, assistant turn count, and file size.
    """
    slug = path.parent.name
    timestamps: list[str] = []
    user_msgs: list[dict] = []
    assistant_turns = 0

    for rec in records:
        ts = rec.get("timestamp", "")
        if ts:
            timestamps.append(ts)
        msg_type = rec.get("type", "")
        if msg_type == "user" and "toolUseResult" not in rec:
            content = _extract_text(rec.get("message", {}).get("content"))
            if content and not _is_noise(content):
                user_msgs.append({"ts": ts, "content": content})
        elif msg_type == "assistant":
            assistant_turns += 1

    return _FileStats(
        slug=slug,
        project_name=_slug_to_project_name(slug),
        first_ts=min(timestamps) if timestamps else "",
        last_ts=max(timestamps) if timestamps else "",
        total_records=len(records),
        user_msgs=user_msgs,
        assistant_turns=assistant_turns,
        file_kb=path.stat().st_size / 1024,
        now=datetime.now(UTC).isoformat(),
    )


def _index_file(con: duckdb.DuckDBPyConnection, path: Path) -> tuple[int, int]:
    """Index one JSONL file into the DuckDB session index.

    Uses ``path.stem`` as the canonical session ID — stable, one-per-file,
    matches the filesystem UUID visible via ``ls ~/.claude/projects/*/``.

    Args:
        con: An open DuckDB connection with the session schema initialised.
        path: Path to the ``.jsonl`` file to index.

    Returns:
        A tuple of ``(user_msgs_indexed, assistant_turns)`` for the file.
    """
    stats = _scan_records(path, list(_iter_records(path)))
    sid = path.stem  # filename UUID — stable, never changes
    SUMMARIES_DIR.mkdir(parents=True, exist_ok=True)
    has_summary = (SUMMARIES_DIR / f"{sid}.md").exists()

    con.execute(
        """
        INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (session_id, file_path) DO UPDATE SET
            first_ts = excluded.first_ts,
            last_ts = excluded.last_ts,
            total_records = excluded.total_records,
            user_msg_count = excluded.user_msg_count,
            assistant_turns = excluded.assistant_turns,
            file_size_kb = excluded.file_size_kb,
            has_summary = excluded.has_summary,
            indexed_at = excluded.indexed_at
    """,
        [
            sid,
            str(path),
            stats.slug,
            stats.project_name,
            stats.first_ts,
            stats.last_ts,
            stats.total_records,
            len(stats.user_msgs),
            stats.assistant_turns,
            stats.file_kb,
            has_summary,
            stats.now,
        ],
    )

    for i, msg in enumerate(stats.user_msgs):
        words = len(msg["content"].split())
        con.execute(
            """
            INSERT INTO user_messages VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (session_id, msg_index) DO UPDATE SET
                content = excluded.content,
                word_count = excluded.word_count
        """,
            [sid, str(path), i, msg["ts"], msg["content"], words],
        )

    return len(stats.user_msgs), stats.assistant_turns


# ---------------------------------------------------------------------------
# Rich table helpers
# ---------------------------------------------------------------------------


def _get_table_width(table: Table) -> int:
    """Get the natural rendered width of a Rich table.

    Measures the table against a very wide temporary console so that Rich
    reports its unconstrained natural width rather than wrapping to the
    current terminal width.

    Args:
        table: The Rich ``Table`` instance to measure.

    Returns:
        The width in characters required to render the table without any
        column wrapping or truncation.
    """
    temp_console = Console(width=9999)
    measurement = Measurement.get(temp_console, temp_console.options, table)
    return int(measurement.maximum)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@app.command("index")
def cmd_index(
    rebuild: Annotated[bool, typer.Option("--rebuild", help="Drop and rebuild from scratch.")] = False,
    project: Annotated[str, typer.Option("--project", "-p", help="Filter by project name substring.")] = "",
) -> None:
    """Build or update the DuckDB session index from ~/.claude/projects/.

    Args:
        rebuild: When ``True``, all existing index data is deleted before
            re-indexing.
        project: Optional substring filter; only files whose parent directory
            name contains this value (case-insensitive) are indexed.
    """
    con = _open_db()

    if rebuild:
        con.execute("DELETE FROM user_messages")
        con.execute("DELETE FROM sessions")
        stderr.print("[yellow]Index cleared — rebuilding...[/yellow]")

    files = sorted(PROJECTS_DIR.glob("*/*.jsonl"), key=lambda f: f.stat().st_mtime, reverse=True)
    if project:
        files = [f for f in files if project.lower() in f.parent.name.lower()]

    stderr.print(f"[dim]Indexing {len(files)} JSONL file(s)...[/dim]")
    total_user = total_asst = 0
    for f in files:
        u, a = _index_file(con, f)
        total_user += u
        total_asst += a
        stderr.print(f"  [dim]{f.name}[/dim]  {u} user msgs, {a} assistant turns")

    count = _fetch_count(con, "SELECT COUNT(*) FROM sessions")
    stdout.print(
        f"\n[bold green]Index updated:[/bold green] {count} sessions, "
        f"{total_user} user messages, {total_asst} assistant turns"
    )
    stdout.print(f"[dim]DB: {DB_PATH}[/dim]")


def _ensure_indexed(con: duckdb.DuckDBPyConnection) -> None:
    """Build the index from scratch when it contains no sessions.

    Args:
        con: An open DuckDB connection with the session schema initialised.
    """
    if _fetch_count(con, "SELECT COUNT(*) FROM sessions") == 0:
        stderr.print("[yellow]Index is empty — building now...[/yellow]")
        for f in sorted(PROJECTS_DIR.glob("*/*.jsonl"), key=lambda f: f.stat().st_mtime, reverse=True):
            _index_file(con, f)


@app.command("list")
def cmd_list(
    limit: Annotated[int, typer.Option("--limit", "-n")] = 20,
    project: Annotated[str, typer.Option("--project", "-p", help="Filter by project name substring.")] = "",
    rebuild: Annotated[bool, typer.Option("--rebuild", help="Re-index before listing.")] = False,
) -> None:
    """List recent sessions with metadata. Runs index if DB is empty.

    Args:
        limit: Maximum number of sessions to display.
        project: Optional substring filter on project name.
        rebuild: When ``True``, clears and rebuilds the index before listing.
    """
    con = _open_db()

    if rebuild:
        con.execute("DELETE FROM user_messages")
        con.execute("DELETE FROM sessions")

    _ensure_indexed(con)

    if project:
        query = """
            SELECT session_id, project_name, last_ts, user_msg_count, assistant_turns,
                   file_size_kb, has_summary, file_path
            FROM sessions
            WHERE project_name LIKE ?
            ORDER BY last_ts DESC
            LIMIT ?
        """
        params: list = [f"%{project}%", limit]
    else:
        query = """
            SELECT session_id, project_name, last_ts, user_msg_count, assistant_turns,
                   file_size_kb, has_summary, file_path
            FROM sessions
            ORDER BY last_ts DESC
            LIMIT ?
        """
        params: list = [limit]
    rows = con.execute(query, params).fetchall()

    if not rows:
        stdout.print("[yellow]No sessions found. Run 'index' first.[/yellow]")
        return

    table = Table(title="Recent Sessions", show_lines=False, box=box.MINIMAL_DOUBLE_HEAD)
    table.add_column("Session ID", style="cyan", no_wrap=True)
    table.add_column("Project", style="green", no_wrap=True)
    table.add_column("Last Active", style="dim", no_wrap=True)
    table.add_column("User Msgs", justify="right")
    table.add_column("Asst Turns", justify="right")
    table.add_column("KB", justify="right", style="dim")
    table.add_column("Summary", justify="center")

    for sid, proj, last_ts, umsg, aturns, kb, _has_sum_db, _ in rows:
        date_str = last_ts[:16].replace("T", " ") if last_ts else "?"
        # Check filesystem directly — survives --rebuild without re-running mark-summarized
        summary_exists = (SUMMARIES_DIR / f"{sid}.md").exists()
        table.add_row(
            sid,
            proj or "unknown",
            date_str,
            str(umsg or 0),
            str(aturns or 0),
            f"{kb:.0f}" if kb else "?",
            ":white_check_mark:" if summary_exists else ":radio_button:",
        )

    table.width = _get_table_width(table)
    stdout.print(table, crop=False, overflow="ignore", no_wrap=True, soft_wrap=True)
    stdout.print(
        "\n[dim]Use 'messages <session-id>' for verbatim user messages, 'search <text>' to search raw files.[/dim]"
    )


@app.command("messages")
def cmd_messages(
    session_id: Annotated[str, typer.Argument(help="Session ID prefix or 'last' for most recent.")],
    raw: Annotated[bool, typer.Option("--raw", help="Output plain text, no formatting.")] = False,
) -> None:
    """Print verbatim user messages for a session.

    Args:
        session_id: Full or prefix session ID, or the literal string ``"last"``
            to select the most recently active session.
        raw: When ``True``, outputs plain text without Rich markup.

    Raises:
        typer.Exit: With exit code 1 when no sessions are indexed or the
            requested session ID has no messages in the index.
    """
    con = _open_db()
    session_id, _ = _resolve_session(con, session_id)

    rows = con.execute(
        """
        SELECT msg_index, timestamp, content
        FROM user_messages
        WHERE session_id LIKE ?
        ORDER BY msg_index
    """,
        [f"{session_id}%"],
    ).fetchall()

    if not rows:
        stderr.print(f"[yellow]No messages in index for '{session_id}' — check 'list' for valid IDs.[/yellow]")
        raise typer.Exit(1)

    if raw:
        for idx, ts, content in rows:
            date_str = ts[:19].replace("T", " ") if ts else "?"
            print(f"[{idx + 1}] {date_str}")
            print(content)
            print()
    else:
        stdout.print(f"\n[bold]User Messages — {session_id}[/bold] ({len(rows)} messages)\n")
        for idx, ts, content in rows:
            date_str = ts[:19].replace("T", " ") if ts else "?"
            stdout.print(f"[dim]── [{idx + 1}] {date_str} ──[/dim]")
            stdout.print(content)
            stdout.print()


def _highlight_excerpt(pattern: re.Pattern, content: str, context_chars: int) -> str:
    """Extract a context window around the first match and bold the matched text.

    Args:
        pattern: Compiled regular expression to search for.
        content: Full text of a user message.
        context_chars: Number of characters of context to include around the
            match (split equally before and after).

    Returns:
        A Rich-markup string with the matched text wrapped in
        ``[bold yellow]...[/bold yellow]``, with leading/trailing ellipsis
        characters when the excerpt does not start or end at the content
        boundaries. Returns a plain prefix of ``content`` when there is no
        match.
    """
    match = pattern.search(content)
    if not match:
        return content[:context_chars]
    start = max(0, match.start() - context_chars // 2)
    end = min(len(content), match.end() + context_chars // 2)
    excerpt = content[start:end]
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(content) else ""
    highlighted = pattern.sub(lambda m: f"[bold yellow]{m.group()}[/bold yellow]", excerpt)
    return f"{prefix}{highlighted}{suffix}"


def _search_file(path: Path, pattern: re.Pattern, limit: int, hits: list[tuple[str, str, str, str]]) -> None:
    """Search one JSONL file for pattern matches, appending results to ``hits``.

    Silently skips the file on ``OSError``. Stops appending once ``hits``
    reaches ``limit`` entries.

    Args:
        path: Path to a ``.jsonl`` file to search.
        pattern: Compiled regular expression to match against user message text.
        limit: Maximum total number of hits to collect across all files.
        hits: Mutable list to which matching tuples are appended. Each tuple
            contains ``(file_path_str, session_id, timestamp, content)``.
    """
    try:
        records = _iter_records(path)
    except OSError:
        return
    for rec in records:
        if len(hits) >= limit:
            return
        if rec.get("type") != "user" or "toolUseResult" in rec:
            continue
        content = _extract_text(rec.get("message", {}).get("content"))
        if not content or _is_noise(content):
            continue
        if pattern.search(content):
            hits.append((str(path), rec.get("sessionId", path.stem), rec.get("timestamp", ""), content))


@app.command("search")
def cmd_search(
    query: Annotated[str, typer.Argument(help="Text to search for (case-insensitive).")],
    limit: Annotated[int, typer.Option("--limit", "-n")] = 20,
    project: Annotated[str, typer.Option("--project", "-p")] = "",
    context_chars: Annotated[int, typer.Option("--context", "-c", help="Chars of context around match.")] = 200,
) -> None:
    """Search raw JSONL files for text. Returns verbatim matching user messages.

    IMPORTANT: Searches raw files, not the summary cache.

    Args:
        query: Case-insensitive text to search for.
        limit: Maximum number of matching messages to return.
        project: Optional substring filter on project directory name.
        context_chars: Number of characters of context to show around each
            match in the output.
    """
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    files = sorted(PROJECTS_DIR.glob("*/*.jsonl"), key=lambda f: f.stat().st_mtime, reverse=True)
    if project:
        files = [f for f in files if project.lower() in f.parent.name.lower()]

    hits: list[tuple[str, str, str, str]] = []
    for path in files:
        if len(hits) >= limit:
            break
        _search_file(path, pattern, limit, hits)

    if not hits:
        stdout.print(f"[yellow]No matches for '{query}'[/yellow]")
        return

    plural = "es" if len(hits) != 1 else ""
    stdout.print(f"\n[bold]Search results for '{query}'[/bold] ({len(hits)} match{plural})\n")
    for path_str, sid, ts, content in hits:
        date_str = ts[:16].replace("T", " ") if ts else "?"
        proj = _slug_to_project_name(Path(path_str).parent.name)
        stdout.print(f"[dim]── {proj} / {sid} @ {date_str} ──[/dim]")
        stdout.print(_highlight_excerpt(pattern, content, context_chars))
        stdout.print()


@app.command("show")
def cmd_show(session_id: Annotated[str, typer.Argument(help="Session ID prefix or 'last'.")]) -> None:
    """Show cached summary for a session, or print metadata for manual summarization.

    Args:
        session_id: Full or prefix session ID, or the literal string ``"last"``
            to select the most recently active session.

    Raises:
        typer.Exit: With exit code 1 when no sessions are indexed or the
            requested session ID is not found in the index.
    """
    con = _open_db()
    session_id, _ = _resolve_session(con, session_id)

    row = con.execute(
        """
        SELECT session_id, file_path, project_name, first_ts, last_ts,
               user_msg_count, assistant_turns, file_size_kb, has_summary
        FROM sessions WHERE session_id LIKE ?
        ORDER BY last_ts DESC LIMIT 1
    """,
        [f"{session_id}%"],
    ).fetchone()

    if not row:
        stderr.print(f"[red]Session '{session_id}' not found in index. Run 'list' first.[/red]")
        raise typer.Exit(1)

    sid, file_path, proj, first_ts, last_ts, umsg, aturns, kb, has_sum = row
    SUMMARIES_DIR.mkdir(parents=True, exist_ok=True)
    summary_path = SUMMARIES_DIR / f"{sid}.md"

    if has_sum and summary_path.exists():
        stdout.print(summary_path.read_text())
        return

    summary_status = f"Cached at {summary_path}" if has_sum else "Not yet generated"
    stdout.print(f"""
[bold]Session: {sid}[/bold]
Project:       {proj}
File:          {file_path}
Date range:    {first_ts[:19] if first_ts else "?"} → {last_ts[:19] if last_ts else "?"}
User messages: {umsg}
Asst turns:    {aturns}
File size:     {kb:.1f} KB
Summary:       {summary_status}

[dim]To generate summary: read the file, then write to {summary_path}[/dim]
[dim]To view user messages: session-historian messages {sid}[/dim]
""")


@app.command("mark-summarized")
def cmd_mark_summarized(
    session_id: Annotated[str, typer.Argument(help="Session ID to mark as having a cached summary.")],
) -> None:
    """Mark a session as having a cached summary in the index.

    Args:
        session_id: Full or prefix session ID to match against the index.
    """
    con = _open_db()
    con.execute("UPDATE sessions SET has_summary = TRUE WHERE session_id LIKE ?", [f"{session_id}%"])
    count = _fetch_count(
        con, "SELECT COUNT(*) FROM sessions WHERE session_id LIKE ? AND has_summary = TRUE", [f"{session_id}%"]
    )
    stdout.print(f"Marked {count} session(s) as summarized.")


def _build_tool_name_map(records: list[dict]) -> dict[str, str]:
    """Build a mapping from tool-use ID to tool name from assistant records.

    Args:
        records: Parsed JSONL records from a session file.

    Returns:
        Dict mapping each ``tool_use`` block ``id`` to its ``name`` field.
        Only assistant-role records with list-typed ``message.content`` are
        considered.
    """
    tool_name_map: dict[str, str] = {}
    for rec in records:
        if rec.get("type") != "assistant":
            continue
        content = rec.get("message", {}).get("content", [])
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use":
                block_id = block.get("id")
                if isinstance(block_id, str):
                    tool_name_map[block_id] = block.get("name", "unknown")
    return tool_name_map


def _collect_errors(records: list[dict], tool_name_map: dict[str, str]) -> list[tuple[str, str, str]]:
    """Collect tool errors from user records.

    Args:
        records: Parsed JSONL records from a session file.
        tool_name_map: Mapping from tool-use ID to tool name, as produced by
            ``_build_tool_name_map``.

    Returns:
        List of ``(timestamp, tool_name, error_content)`` tuples, one per
        ``tool_result`` block where ``is_error`` is ``True``.
    """
    errors: list[tuple[str, str, str]] = []
    for rec in records:
        if rec.get("type") != "user":
            continue
        content = rec.get("message", {}).get("content", [])
        if not isinstance(content, list):
            continue
        ts = rec.get("timestamp", "")
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_result" and block.get("is_error") is True:
                tool_use_id = block.get("tool_use_id", "")
                tool_name = tool_name_map.get(tool_use_id, "unknown")
                error_content = _extract_text(block.get("content"))
                errors.append((ts, tool_name, error_content))
    return errors


@app.command("errors")
def cmd_errors(
    session_id: Annotated[str, typer.Argument(help="Session ID prefix or 'last' for most recent.")] = "last",
    raw: Annotated[bool, typer.Option("--raw", help="Output plain text, no formatting.")] = False,
) -> None:
    r"""List tool errors from a session with timestamps and tool names.

    Performs a two-pass scan over the session JSONL: the first pass builds a
    mapping from tool-use IDs to tool names (from assistant records); the
    second pass extracts tool-result blocks where ``is_error`` is ``True``
    (from user records) and resolves each error's tool name via the map.

    Args:
        session_id: Full or prefix session ID, or the literal string ``"last"``
            to select the most recently active session.
        raw: When ``True``, outputs tab-separated lines with no Rich markup.
            Format: ``timestamp\\ttool_name\\terror_content_single_line``.

    Raises:
        typer.Exit: With exit code 1 when the session is not found.
        typer.Exit: With exit code 0 when no tool errors exist in the session.
    """
    con = _open_db()
    session_id, path = _resolve_session(con, session_id)
    records = list(_iter_records(path))

    tool_name_map = _build_tool_name_map(records)
    errors = _collect_errors(records, tool_name_map)

    if not errors:
        stderr.print(f"No tool errors in session {session_id}")
        raise typer.Exit(0)

    if raw:
        for ts, tool_name, content in errors:
            date_str = ts[:19].replace("T", " ") if ts else "?"
            single_line = content.replace("\n", " ")
            print(f"{date_str}\t{tool_name}\t{single_line}")
    else:
        stdout.print(f"\n[bold]Tool Errors — {session_id}[/bold] ({len(errors)} error(s))\n")
        for ts, tool_name, content in errors:
            date_str = ts[:19].replace("T", " ") if ts else "?"
            stdout.print(f"[dim]── {date_str}[/dim]  [red bold]{tool_name}[/red bold]")
            stdout.print(f"[red]{content}[/red]")
            stdout.print()


def _collect_tool_uses(records: list[dict]) -> list[tuple[str, str]]:
    """Collect tool-use entries from assistant records in encounter order.

    Args:
        records: Parsed JSONL records from a session file.

    Returns:
        List of ``(tool_use_id, tool_name)`` tuples, one per ``tool_use``
        block found in assistant-role records, preserving encounter order.
    """
    tool_uses: list[tuple[str, str]] = []
    for rec in records:
        if rec.get("type") != "assistant":
            continue
        content = rec.get("message", {}).get("content", [])
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use":
                block_id = block.get("id")
                if isinstance(block_id, str):
                    tool_uses.append((block_id, block.get("name", "unknown")))
    return tool_uses


def _collect_tool_results(records: list[dict]) -> dict[str, bool]:
    """Build a map from tool-use ID to success/failure from user records.

    Args:
        records: Parsed JSONL records from a session file.

    Returns:
        Dict mapping each ``tool_use_id`` to ``True`` (success) or ``False``
        (failure, i.e. ``is_error`` is ``True``).  Only user-role records
        with list-typed ``message.content`` containing ``tool_result`` blocks
        are considered.
    """
    matched: dict[str, bool] = {}
    for rec in records:
        if rec.get("type") != "user":
            continue
        content = rec.get("message", {}).get("content", [])
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_result":
                tool_use_id = block.get("tool_use_id")
                if isinstance(tool_use_id, str):
                    matched[tool_use_id] = block.get("is_error") is not True
    return matched


def _aggregate_tool_stats(
    tool_uses: list[tuple[str, str]], matched_ids: dict[str, bool]
) -> list[tuple[str, int, int, int, int]]:
    """Aggregate per-tool-name stats from tool uses and their results.

    Args:
        tool_uses: Ordered list of ``(tool_use_id, tool_name)`` tuples.
        matched_ids: Map from tool_use_id to success boolean, as produced by
            ``_collect_tool_results``.

    Returns:
        List of ``(tool_name, total, successes, failures, unmatched)`` tuples,
        sorted by total descending.
    """
    stats: dict[str, list[int]] = {}
    for tool_id, tool_name in tool_uses:
        if tool_name not in stats:
            stats[tool_name] = [0, 0, 0, 0]
        stats[tool_name][0] += 1
        if tool_id in matched_ids:
            if matched_ids[tool_id]:
                stats[tool_name][1] += 1
            else:
                stats[tool_name][2] += 1
        else:
            stats[tool_name][3] += 1
    rows: list[tuple[str, int, int, int, int]] = [
        (name, counts[0], counts[1], counts[2], counts[3]) for name, counts in stats.items()
    ]
    return sorted(rows, key=operator.itemgetter(1), reverse=True)


@app.command("tools")
def cmd_tools(
    session_id: Annotated[str, typer.Argument(help="Session ID prefix or 'last' for most recent.")] = "last",
    raw: Annotated[bool, typer.Option("--raw", help="Output plain text, no formatting.")] = False,
) -> None:
    r"""List tools used in a session with call counts and success/failure breakdown.

    Performs a two-pass scan over the session JSONL: the first pass collects
    all ``tool_use`` blocks from assistant records; the second pass correlates
    ``tool_result`` blocks from user records to classify each call as success
    or failure.  Calls with no matching ``tool_result`` are counted as
    unmatched (e.g. session interrupted before the tool returned).

    Args:
        session_id: Full or prefix session ID, or the literal string ``"last"``
            to select the most recently active session.
        raw: When ``True``, outputs a header line followed by tab-separated
            data rows with no Rich markup.
            Format: ``tool\\ttotal\\tsuccesses\\tfailures\\tunmatched``.

    Raises:
        typer.Exit: With exit code 1 when the session is not found.
        typer.Exit: With exit code 0 when no tool calls are recorded.
    """
    con = _open_db()
    session_id, path = _resolve_session(con, session_id)
    records = list(_iter_records(path))

    tool_uses = _collect_tool_uses(records)
    if not tool_uses:
        stderr.print(f"No tool calls recorded in session {session_id}")
        raise typer.Exit(0)

    sorted_tools = _aggregate_tool_stats(tool_uses, _collect_tool_results(records))

    if raw:
        print("tool\ttotal\tsuccesses\tfailures\tunmatched")
        for tool_name, total, successes, failures, unmatched in sorted_tools:
            print(f"{tool_name}\t{total}\t{successes}\t{failures}\t{unmatched}")
    else:
        table = Table(title=f"Tool Usage — {session_id}", show_lines=False, box=box.MINIMAL_DOUBLE_HEAD)
        table.add_column("Tool Name", style="cyan", no_wrap=True)
        table.add_column("Total Calls", justify="right")
        table.add_column("Successes", justify="right", style="green")
        table.add_column("Failures", justify="right", style="red")
        table.add_column("Unmatched", justify="right", style="dim")
        for tool_name, total, successes, failures, unmatched in sorted_tools:
            table.add_row(str(tool_name), str(total), str(successes), str(failures), str(unmatched))
        table.width = _get_table_width(table)
        stdout.print(table, crop=False, overflow="ignore", no_wrap=True, soft_wrap=True)


def _collect_correction_phrases(records: list[dict]) -> list[tuple[str, str, str]]:
    """Collect user messages that contain correction phrases.

    Scans user-role records (excluding ``toolUseResult`` records) for phrases
    from ``_CORRECTION_PHRASES``, case-insensitively.  Noise records are
    skipped via ``_is_noise``.

    Args:
        records: Parsed JSONL records from a session file.

    Returns:
        List of ``(timestamp, matched_phrase, excerpt)`` tuples, one per
        matching message (first 200 chars of the message text).
    """
    results: list[tuple[str, str, str]] = []
    for rec in records:
        if rec.get("type") != "user" or "toolUseResult" in rec:
            continue
        ts = rec.get("timestamp", "")
        content = _extract_text(rec.get("message", {}).get("content"))
        if not content or _is_noise(content):
            continue
        lower = content.lower()
        for phrase in _CORRECTION_PHRASES:
            if phrase in lower:
                results.append((ts, phrase, content[:200]))
                break  # one signal per message is enough
    return results


def _collect_stuck_loops(records: list[dict]) -> list[tuple[str, str, int, str]]:
    """Detect stuck tool loops in assistant records.

    A stuck loop is defined as ``_STUCK_LOOP_THRESHOLD`` or more consecutive
    ``tool_use`` blocks with the same identity key.  The identity key is
    ``"<name>:<md5_prefix>"`` where the MD5 is computed over the
    ``sort_keys=True`` JSON serialisation of the block's ``input`` field.

    Args:
        records: Parsed JSONL records from a session file.

    Returns:
        List of ``(first_timestamp, tool_name, count, input_hash)`` tuples,
        one entry emitted the moment a run reaches ``_STUCK_LOOP_THRESHOLD``
        (and again each additional occurrence beyond the threshold).
    """
    signals: list[tuple[str, str, int, str]] = []
    current_key: str = ""
    current_count: int = 0
    current_ts: str = ""
    current_tool: str = ""
    current_hash: str = ""

    for rec in records:
        if rec.get("type") != "assistant":
            continue
        ts = rec.get("timestamp", "")
        content = rec.get("message", {}).get("content", [])
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            name = block.get("name", "unknown")
            input_hash = hashlib.md5(
                json.dumps(block.get("input", {}), sort_keys=True).encode(), usedforsecurity=False
            ).hexdigest()[:8]
            identity = f"{name}:{input_hash}"
            if identity == current_key:
                current_count += 1
                if current_count >= _STUCK_LOOP_THRESHOLD:
                    signals.append((current_ts, current_tool, current_count, current_hash))
            else:
                current_key = identity
                current_count = 1
                current_ts = ts
                current_tool = name
                current_hash = input_hash

    return signals


@app.command("irritation")
def cmd_irritation(
    session_id: Annotated[str, typer.Argument(help="Session ID prefix or 'last' for most recent.")] = "last",
    raw: Annotated[bool, typer.Option("--raw", help="Output plain text, no formatting.")] = False,
) -> None:
    r"""Detect user irritation signals in a session.

    Reports two signal types:

    1. **Correction phrases** — user messages that contain phrases from the
       ``_CORRECTION_PHRASES`` list (e.g. "wrong", "stop", "undo"), detected
       case-insensitively.

    2. **Stuck tool loops** — sequences of ``_STUCK_LOOP_THRESHOLD`` or more
       consecutive identical tool calls (same tool name and input hash) in
       assistant records.

    Args:
        session_id: Full or prefix session ID, or the literal string ``"last"``
            to select the most recently active session.
        raw: When ``True``, outputs type-prefixed tab-separated lines with no
            Rich markup.  Format:
            ``phrase\\t<ts>\\t<phrase>\\t<excerpt>`` and
            ``loop\\t<ts>\\t<tool>\\t<count>\\t<hash>``.

    Raises:
        typer.Exit: With exit code 1 when the session is not found.
        typer.Exit: With exit code 0 when no irritation signals are detected.
    """
    con = _open_db()
    session_id, path = _resolve_session(con, session_id)
    records = list(_iter_records(path))

    phrases = _collect_correction_phrases(records)
    loops = _collect_stuck_loops(records)

    if not phrases and not loops:
        stderr.print(f"No irritation signals detected in session {session_id}")
        raise typer.Exit(0)

    if raw:
        for ts, phrase, excerpt in phrases:
            date_str = ts[:19].replace("T", " ") if ts else "?"
            single_line = excerpt.replace("\n", " ")
            print(f"phrase\t{date_str}\t{phrase}\t{single_line}")
        for ts, tool_name, count, input_hash in loops:
            date_str = ts[:19].replace("T", " ") if ts else "?"
            print(f"loop\t{date_str}\t{tool_name}\t{count}\t{input_hash}")
    else:
        stdout.print(f"\n[bold]Irritation Signals — {session_id}[/bold]\n")
        stdout.print(f"[bold]Correction Phrases ({len(phrases)} found)[/bold]")
        if phrases:
            for ts, phrase, excerpt in phrases:
                date_str = ts[:19].replace("T", " ") if ts else "?"
                stdout.print(f"[dim]── {date_str}[/dim]  [yellow bold]{phrase}[/yellow bold]")
                stdout.print(f"[dim]{excerpt}[/dim]")
                stdout.print()
        else:
            stdout.print("[dim]None[/dim]\n")

        stdout.print(f"[bold]Stuck Tool Loops ({len(loops)} detected)[/bold]")
        if loops:
            for ts, tool_name, count, input_hash in loops:
                date_str = ts[:19].replace("T", " ") if ts else "?"
                stdout.print(
                    f"[dim]── {date_str}[/dim]  [red bold]{tool_name}[/red bold]"
                    f"  [dim]x{count}[/dim]  [dim]{input_hash}[/dim]"
                )
                stdout.print()
        else:
            stdout.print("[dim]None[/dim]\n")


@app.command("current-path")
def cmd_current_path(
    rich: Annotated[bool, typer.Option("--rich", help="Display with Rich formatting.")] = False,
) -> None:
    """Print the JSONL file path for the current live session.

    Reads ``CLAUDE_SESSION_ID`` from the environment and computes the expected
    JSONL file path using the encoded current working directory.  Does not
    open DuckDB — pure filesystem check.

    Default output is a single raw line (machine-readable), suitable for
    agent pipelines.  Pass ``--rich`` for a human-readable panel display.

    Args:
        rich: When ``True``, renders the path inside a Rich Panel with a green
            border.  When ``False`` (default), prints only the absolute path
            with no markup.

    Raises:
        typer.Exit: With exit code 1 when ``CLAUDE_SESSION_ID`` is not set or
            the expected JSONL file does not exist.
    """
    session_id = os.environ.get("CLAUDE_SESSION_ID", "")
    if not session_id:
        stderr.print("[red]CLAUDE_SESSION_ID is not set[/red]")
        raise typer.Exit(1)

    encoded = str(Path.cwd()).replace("/", "-").lstrip("-")
    path = PROJECTS_DIR / encoded / f"{session_id}.jsonl"

    if path.exists():
        if rich:
            panel = Panel(str(path), title="Current Session Path", border_style="green")
            stdout.print(panel)
        else:
            print(str(path))
    else:
        stderr.print("[red]Session file not found[/red]")
        stderr.print(f"[dim]Session ID : {session_id}[/dim]")
        stderr.print(f"[dim]Expected   : {path}[/dim]")
        stderr.print(f"[dim]Projects   : {PROJECTS_DIR}[/dim]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()

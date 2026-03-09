#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = [
#     "fastmcp>=3.0.0rc1,<4",
#     "duckdb>=0.10.0",
#     "rich>=13.0",
#     "cairosvg>=2.7.0",
# ]
# ///
"""RTFP (Read The Fucking Prompt) MCP Server.

Finds the single strongest user reaction to an instruction-following failure
in a selected Claude Code session, reconstructs the triggering assistant
output, and renders the exchange as a terminal-style PNG.

Uses DuckDB as the query layer against existing JSONL session log files.
No persistent database file is created -- every query runs in-memory via
``read_ndjson_auto()``.

Tools:
    list_sessions         - Scan ~/.claude/projects/ for JSONL session files
    extract_user_messages - Write user-only batch JSONL for a single session
    get_context_window    - Return N messages before/after a target line_index
    scan_transcripts      - Extract raw user messages with context (Stage 1)
    get_scenario          - Get full message context for a specific file+line
    generate_social_post  - Generate social media content for a user message
    render_rage_receipt   - Render terminal-style SVG/PNG card and return image inline
"""

from __future__ import annotations

import asyncio
import json
import logging
import pathlib
from datetime import UTC, datetime
from typing import Any

import duckdb
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.utilities.types import Image
from mcp.types import TextContent
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_CONTEXT_WINDOW: int = 5

_READONLY_ANNOTATIONS: dict[str, bool] = {
    "readOnlyHint": True,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": False,
}

_WRITE_ANNOTATIONS: dict[str, bool] = {
    "readOnlyHint": False,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": False,
}

# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

mcp = FastMCP("frustration-analyzer", mask_error_details=False)

# ---------------------------------------------------------------------------
# SQL Templates
# ---------------------------------------------------------------------------

_SQL_COUNT_USER_MESSAGES: str = (
    "WITH numbered AS ("
    " SELECT filename AS file,"
    "        (row_number() OVER (PARTITION BY filename ORDER BY (SELECT NULL)) - 1) AS line_index,"
    '        message, uuid, "timestamp", sessionId AS session_id,'
    "        type, toolUseResult"
    " FROM read_ndjson_auto($1::VARCHAR[], union_by_name:=true, filename:=true)"
    ")"
    " SELECT count(*) FROM numbered WHERE type = 'user' AND toolUseResult IS NULL"
)

_SQL_QUERY_USER_MESSAGES: str = (
    "WITH numbered AS ("
    " SELECT filename AS file,"
    "        (row_number() OVER (PARTITION BY filename ORDER BY (SELECT NULL)) - 1) AS line_index,"
    '        message, uuid, "timestamp", sessionId AS session_id,'
    "        type, toolUseResult"
    " FROM read_ndjson_auto($1::VARCHAR[], union_by_name:=true, filename:=true)"
    ")"
    ' SELECT file, line_index, message, uuid, "timestamp", session_id'
    " FROM numbered"
    " WHERE type = 'user' AND toolUseResult IS NULL"
    " LIMIT $2 OFFSET $3"
)

_SQL_CONTEXT_MESSAGES: str = (
    "WITH indexed AS ("
    " SELECT (row_number() OVER (ORDER BY (SELECT NULL)) - 1) AS rn, *"
    " FROM read_ndjson_auto($1, union_by_name:=true)"
    ")"
    ' SELECT type AS role, "timestamp", uuid, message, toolUseResult'
    " FROM indexed WHERE rn >= $2 AND rn < $3"
)

_SQL_GET_SCENARIO: str = (
    "WITH indexed AS ("
    " SELECT (row_number() OVER (ORDER BY (SELECT NULL)) - 1) AS rn, *"
    " FROM read_ndjson_auto($1, union_by_name:=true)"
    ")"
    ' SELECT type, message, uuid, "timestamp", sessionId AS session_id'
    " FROM indexed WHERE rn = $2"
)

_SQL_GET_MESSAGE: str = (
    "WITH indexed AS ("
    " SELECT (row_number() OVER (ORDER BY (SELECT NULL)) - 1) AS rn, *"
    " FROM read_ndjson_auto($1, union_by_name:=true)"
    ")"
    ' SELECT message, uuid, "timestamp"'
    " FROM indexed WHERE rn = $2"
)

_SQL_ALL_MESSAGES_IN_FILE: str = (
    "WITH indexed AS ("
    " SELECT (row_number() OVER (ORDER BY (SELECT NULL)) - 1) AS rn, *"
    " FROM read_ndjson_auto($1, union_by_name:=true)"
    ")"
    ' SELECT rn AS line_index, type, "timestamp", message, toolUseResult'
    " FROM indexed ORDER BY rn"
)

_SQL_FIRST_USER_MESSAGES: str = (
    "WITH indexed AS ("
    " SELECT (row_number() OVER (ORDER BY (SELECT NULL)) - 1) AS rn, *"
    " FROM read_ndjson_auto($1, union_by_name:=true)"
    ")"
    ' SELECT rn AS line_index, type, "timestamp", message, toolUseResult'
    " FROM indexed"
    " WHERE type = 'user' AND toolUseResult IS NULL"
    " ORDER BY rn LIMIT 20"
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_glob(glob_path: str) -> list[str]:
    """Resolve a glob pattern to a sorted list of file paths.

    Args:
        glob_path: Glob pattern (e.g. ``~/.claude/projects/**/*.jsonl``).

    Returns:
        Sorted list of matching absolute file path strings.
    """
    expanded = str(pathlib.Path(glob_path).expanduser()) if "~" in glob_path else glob_path
    glob_chars = {"*", "?", "["}

    if not any(c in expanded for c in glob_chars):
        p = pathlib.Path(expanded)
        return [str(p)] if p.is_file() else []

    parts = pathlib.PurePosixPath(expanded).parts
    base_parts: list[str] = []
    for part in parts:
        if any(c in part for c in glob_chars):
            break
        base_parts.append(part)

    if base_parts:
        base = pathlib.Path(*base_parts)
        relative = str(pathlib.PurePosixPath(*parts[len(base_parts) :]))
    else:
        base = pathlib.Path()
        relative = expanded

    return sorted(str(p) for p in base.glob(relative))


def _resolve_path(file: str) -> str:
    """Expand ~ and return absolute path string.

    Returns:
        Absolute path string with home directory expanded.
    """
    return str(pathlib.Path(file).expanduser()) if "~" in file else file


def _extract_user_text_from_value(
    content: str | list[str | dict[str, str]] | dict[str, str | list[str | dict[str, str]]],
) -> str:
    """Extract plain text from a user message content field.

    Handles both string content and list-of-blocks content formats,
    as well as the ``{"content": ...}`` wrapper dict that DuckDB may
    return from JSON columns.

    Args:
        content: The content value -- may be a string, list, or dict
            with a ``content`` key.

    Returns:
        Extracted text, or empty string if no text found.
    """
    unwrapped = content.get("content", content) if isinstance(content, dict) else content

    if isinstance(unwrapped, str):
        return unwrapped
    if isinstance(unwrapped, list):
        parts: list[str] = []
        for block in unwrapped:
            if isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text", "")
                if isinstance(text, str):
                    parts.append(text)
            elif isinstance(block, str):
                parts.append(block)
        return " ".join(parts)
    return ""


def _is_human_plaintext(text: str) -> bool:
    """Check whether extracted text is genuine human-typed content.

    Filters out skill/command injection payloads, tool result blocks,
    and empty/whitespace-only strings that leak through the DuckDB
    ``type='user' AND toolUseResult IS NULL`` filter.

    The content field in Claude Code JSONL may wrap the actual text in
    surrounding double-quote characters, so those are stripped before
    pattern matching.

    Args:
        text: The extracted text string to validate.

    Returns:
        True if the text appears to be genuine human input.
    """
    stripped = text.strip()
    # Remove exactly one wrapping pair of double-quotes if present
    if stripped.startswith('"') and stripped.endswith('"') and len(stripped) > 1:
        stripped = stripped[1:-1].strip()
    if not stripped:
        return False
    # Skill/command injection payloads, system-injected XML tags, and
    # stop-hook feedback lines are not genuine human input.
    if stripped.startswith((
        "<command-message",
        "<command-name",
        "<command-args",
        "<task-notification",
        "<system-reminder",
        '<parameter name="orchestrator-read-warning',
        "[~/.claude/",
    )):
        return False
    # Tool result blocks are JSON arrays of dicts
    return not stripped.startswith("[{")


def _extract_assistant_text(message: str | dict[str, Any] | None) -> str:
    """Extract plain text from an assistant message content array.

    Args:
        message: The assistant message value from DuckDB.

    Returns:
        Joined text from all text-type content blocks, or empty string.
    """
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    if not isinstance(content, list):
        return ""
    parts: list[str] = []
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "text":
            t = block.get("text", "")
            if isinstance(t, str):
                parts.append(t)
    return " ".join(parts)


def _extract_assistant_context(message: str | dict[str, Any] | None, entry: dict[str, Any]) -> None:
    """Extract text and tool info from an assistant message into an entry dict.

    Args:
        message: The assistant message value from DuckDB (may be dict or None).
        entry: Mutable entry dict to populate with text and tool_name.
    """
    if not isinstance(message, dict):
        return
    content = message.get("content")
    if not isinstance(content, list):
        return
    text_parts: list[str] = []
    for block in content:
        if not isinstance(block, dict):
            continue
        match block.get("type"):
            case "text":
                t = block.get("text", "")
                if isinstance(t, str):
                    text_parts.append(t)
            case "tool_use":
                entry["tool_name"] = str(block.get("name", "unknown"))
    entry["text"] = " ".join(text_parts)


def _query_user_messages(glob_path: str, offset: int = 0, limit: int = 100) -> tuple[list[dict[str, Any]], int, int]:
    """Query user messages from JSONL files using DuckDB.

    Args:
        glob_path: Glob pattern pointing to JSONL transcript files.
        offset: Number of messages to skip (pagination).
        limit: Maximum number of messages to return.

    Returns:
        Tuple of (messages list, total count, files_scanned count).

    Raises:
        ToolError: If no files match the glob pattern.
    """
    files = _resolve_glob(glob_path)
    if not files:
        raise ToolError(f"No files matched glob pattern: {glob_path}")

    conn = duckdb.connect()

    total_row = conn.execute(_SQL_COUNT_USER_MESSAGES, [files]).fetchone()
    total = total_row[0] if total_row else 0

    rows = conn.execute(_SQL_QUERY_USER_MESSAGES, [files, limit, offset]).fetchall()
    columns = ["file", "line_index", "message", "uuid", "timestamp", "session_id"]
    conn.close()

    messages: list[dict[str, Any]] = []
    for row in rows:
        record = dict(zip(columns, row, strict=False))
        text = _extract_user_text_from_value(record.pop("message"))
        if text and _is_human_plaintext(text):
            record["text"] = text
            messages.append(record)

    return messages, total, len(files)


def _get_context_messages(file_path: str, line_index: int, context_window: int) -> list[dict[str, Any]]:
    """Get surrounding context messages for a specific position in a JSONL file.

    Args:
        file_path: Path to the JSONL file.
        line_index: Row index of the target message.
        context_window: Number of preceding messages to capture.

    Returns:
        List of context message dicts with role, timestamp, uuid, and text.
    """
    start = max(0, line_index - context_window)
    conn = duckdb.connect()

    rows = conn.execute(_SQL_CONTEXT_MESSAGES, [file_path, start, line_index]).fetchall()
    conn.close()

    context: list[dict[str, Any]] = []
    for row in rows:
        role, timestamp, uuid_val, message, tool_use_result = row
        if role == "user" and tool_use_result is None:
            text = _extract_user_text_from_value(message)
            if text:
                context.append({
                    "role": role,
                    "timestamp": str(timestamp or ""),
                    "uuid": str(uuid_val or ""),
                    "text": text,
                })
        elif role == "assistant":
            entry: dict[str, Any] = {"role": role, "timestamp": str(timestamp or ""), "uuid": str(uuid_val or "")}
            _extract_assistant_context(message, entry)
            context.append(entry)

    return context


def _derive_session_title(file_path: str, conn: duckdb.DuckDBPyConnection | None = None) -> str:
    """Derive a human-readable title from the first genuine user message in a session file.

    Scans through user messages, skipping skill/command injection payloads
    and tool result blocks, until a real human-typed message is found.

    Args:
        file_path: Absolute path to a JSONL session file.
        conn: Optional shared DuckDB connection. When provided the caller
            owns the connection lifecycle; when ``None`` a temporary
            connection is created and closed internally.

    Returns:
        First 80 characters of the first human-typed user message,
        or the filename stem as fallback.
    """
    own_conn = conn is None
    try:
        db: duckdb.DuckDBPyConnection = duckdb.connect() if own_conn else conn  # type: ignore[assignment]
        rows = db.execute(_SQL_FIRST_USER_MESSAGES, [file_path]).fetchall()
        if own_conn:
            db.close()
        for _line_index, msg_type, _timestamp, message, tool_use_result in rows:
            if msg_type != "user" or tool_use_result is not None:
                continue
            text = _extract_user_text_from_value(message)
            if text and _is_human_plaintext(text):
                return text[:80].replace("\n", " ").strip()
    except Exception as exc:  # noqa: BLE001
        logger.debug("Could not derive session title from %s: %s", file_path, exc)
    return pathlib.Path(file_path).stem


# ---------------------------------------------------------------------------
# Card rendering (Rich-based SVG/PNG)
# ---------------------------------------------------------------------------


def _build_card_content(task_summary: str, assistant_excerpt: str, user_reply: str) -> Text:
    """Build the Rich Text content for the RTFP card.

    Creates a styled text block with three labelled sections (task,
    assistant, user) separated by blank lines.

    Args:
        task_summary: Short description of the task context.
        assistant_excerpt: The offending assistant response excerpt.
        user_reply: The user's frustrated reply.

    Returns:
        Rich Text object with all sections styled.
    """
    content = Text()

    sections: list[tuple[str, str, str]] = [
        ("task:", task_summary, "#4ec9b0"),
        ("assistant:", assistant_excerpt, "#dcdcaa"),
        ("user:", user_reply, "#f44747"),
    ]

    for i, (label, body, color) in enumerate(sections):
        if i > 0:
            content.append("\n")
        content.append(label, style=f"bold {color}")
        content.append(f" {body}\n", style="dim white")

    return content


def _render_card(
    task_summary: str, assistant_excerpt: str, user_reply: str, output_path: str
) -> list[TextContent | Image]:
    """Render a terminal-style card as SVG or PNG.

    Uses Rich ``Console(record=True)`` to render a styled Panel, then
    exports as SVG.  If ``output_path`` ends with ``.png``, the SVG is
    converted to PNG via ``cairosvg.svg2png()``.

    The rendered asset is saved to *output_path* **and** returned inline
    so MCP clients receive the content directly:

    * SVG  -- returned as ``TextContent`` (the SVG XML string).
    * PNG  -- returned as a FastMCP ``Image`` (base64-encoded PNG bytes).

    A leading ``TextContent`` always carries JSON metadata (``output_path``,
    ``format``) for callers that also need the filesystem path.

    Args:
        task_summary: Short description of the task context.
        assistant_excerpt: The offending assistant response excerpt.
        user_reply: The user's frustrated reply.
        output_path: File path to write (``.svg`` or ``.png``).

    Returns:
        List of MCP content blocks: metadata ``TextContent`` followed by
        either an SVG ``TextContent`` or a PNG ``Image``.
    """
    content = _build_card_content(task_summary, assistant_excerpt, user_reply)
    panel = Panel(content, title="RTFP", title_align="left", border_style="bright_blue", padding=(1, 2))

    console = Console(record=True, width=100, force_terminal=True, color_system="truecolor")
    panel.width = console.width
    console.print(panel)

    svg_text = console.export_svg(title="RTFP")

    out = pathlib.Path(output_path).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)

    output_format: str
    result: list[TextContent | Image]

    if out.suffix.lower() == ".png":
        import cairosvg  # noqa: PLC0415

        png_bytes: bytes = cairosvg.svg2png(bytestring=svg_text.encode("utf-8"))
        out.write_bytes(png_bytes)
        output_format = "png"

        metadata = json.dumps({"output_path": str(out), "format": output_format})
        result = [TextContent(type="text", text=metadata), Image(data=png_bytes, format="png")]
    else:
        out.write_text(svg_text, encoding="utf-8")
        output_format = "svg"

        metadata = json.dumps({"output_path": str(out), "format": output_format})
        result = [TextContent(type="text", text=metadata), TextContent(type="text", text=svg_text)]

    return result


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------


@mcp.tool(annotations=_READONLY_ANNOTATIONS)
async def list_sessions(project_path: str = "~/.claude/projects/") -> dict[str, Any]:
    """Scan for JSONL session files and return them grouped by project.

    Scans ``~/.claude/projects/`` (or a provided path) for JSONL session
    files.  Sessions are sorted by modification time descending.  A title
    is derived from the first user message in each file (first 80 chars),
    with filename stem as fallback.

    Uses DuckDB ``read_ndjson_auto()`` for title extraction -- no persistent
    database is created.

    Args:
        project_path: Root directory to scan for JSONL files.
            Defaults to ``~/.claude/projects/``.

    Returns:
        Dict with ``sessions`` (list of session dicts) and ``count``.
        Each session: ``{file, project, modified, size_bytes, title}``.
    """

    def _scan() -> dict[str, Any]:
        root = pathlib.Path(project_path).expanduser()
        if not root.exists():
            raise ToolError(f"Project path does not exist: {root}")

        jsonl_files = sorted(root.rglob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)

        sessions: list[dict[str, Any]] = []
        conn = duckdb.connect()
        try:
            for f in jsonl_files:
                stat = f.stat()
                project = f.parent.name
                modified = datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat()
                title = _derive_session_title(str(f), conn=conn)
                sessions.append({
                    "file": str(f),
                    "project": project,
                    "modified": modified,
                    "size_bytes": stat.st_size,
                    "title": title,
                })
        finally:
            conn.close()

        return {"sessions": sessions, "count": len(sessions)}

    return await asyncio.to_thread(_scan)


@mcp.tool(annotations=_WRITE_ANNOTATIONS)
async def extract_user_messages(file: str, output_path: str) -> dict[str, Any]:
    """Extract user-only messages from a session file to a batch JSONL.

    Reads the given JSONL session file via DuckDB and filters to ONLY
    user-authored messages (type='user', toolUseResult IS NULL).  Writes
    a new JSONL file at output_path with entries:
    ``{"file": str, "line_index": int, "text": str}``.

    No assistant messages, tool outputs, or context is included.
    The output is suitable as input to a Stage 2 batch-detector subagent.

    Args:
        file: Path to the source JSONL session file.
        output_path: Path to write the output batch JSONL file.

    Returns:
        Dict with ``output_path``, ``message_count``, and ``source_file``.

    Raises:
        ToolError: If the source file cannot be read.
    """

    def _extract() -> dict[str, Any]:
        resolved = _resolve_path(file)
        if not pathlib.Path(resolved).is_file():
            raise ToolError(f"Source file not found: {resolved}")

        conn = duckdb.connect()
        rows = conn.execute(_SQL_ALL_MESSAGES_IN_FILE, [resolved]).fetchall()
        conn.close()

        out_path = pathlib.Path(output_path).expanduser()
        out_path.parent.mkdir(parents=True, exist_ok=True)

        count = 0
        with out_path.open("w", encoding="utf-8") as fh:
            for line_index, msg_type, _timestamp, message, tool_use_result in rows:
                if msg_type != "user" or tool_use_result is not None:
                    continue
                text = _extract_user_text_from_value(message)
                if not text or not _is_human_plaintext(text):
                    continue
                fh.write(json.dumps({"file": resolved, "line_index": int(line_index), "text": text}) + "\n")
                count += 1

        return {"output_path": str(out_path), "message_count": count, "source_file": resolved}

    return await asyncio.to_thread(_extract)


@mcp.tool(annotations=_READONLY_ANNOTATIONS)
async def get_context_window(file: str, line_index: int, before: int = 10, after: int = 3) -> dict[str, Any]:
    """Return full context around a target message for reconstruction.

    Reads the full JSONL session file via DuckDB and returns N messages
    before and M messages after the target line_index.  Includes ALL
    message types (user, assistant, tool results) -- this is full context
    reconstruction, not a user-only view.

    Each message in the result:
    ``{"role": str, "line_index": int, "text": str, "timestamp": str}``

    For assistant messages, text is extracted from the message.content array.

    Args:
        file: Path to the JSONL session file.
        line_index: 0-based row index of the target message.
        before: Number of messages to include before the target. Default 10.
        after: Number of messages to include after the target. Default 3.

    Returns:
        Dict with ``target``, ``before`` (list), and ``after`` (list).

    Raises:
        ToolError: If the file cannot be read or line_index is out of range.
    """

    def _query() -> dict[str, Any]:
        resolved = _resolve_path(file)
        if not pathlib.Path(resolved).is_file():
            raise ToolError(f"File not found: {resolved}")

        conn = duckdb.connect()
        rows = conn.execute(_SQL_ALL_MESSAGES_IN_FILE, [resolved]).fetchall()
        conn.close()

        if not rows:
            raise ToolError(f"No messages found in {resolved}")

        max_idx = rows[-1][0]
        if line_index < 0 or line_index > max_idx:
            raise ToolError(f"line_index {line_index} out of range 0-{max_idx} in {resolved}")

        def _to_entry(row: tuple) -> dict[str, Any]:
            idx, msg_type, timestamp, message, tool_use_result = row
            role = str(msg_type or "unknown")
            ts = str(timestamp or "")
            if role == "user" and tool_use_result is None:
                text = _extract_user_text_from_value(message)
            elif role == "assistant":
                text = _extract_assistant_text(message)
            else:
                # tool result or other
                text = str(message) if message is not None else ""
            return {"role": role, "line_index": int(idx), "text": text, "timestamp": ts}

        target_row = next((r for r in rows if r[0] == line_index), None)
        if target_row is None:
            raise ToolError(f"line_index {line_index} not found in {resolved}")

        before_rows = [r for r in rows if r[0] < line_index][-before:] if before > 0 else []
        after_rows = [r for r in rows if r[0] > line_index][:after] if after > 0 else []

        return {
            "target": _to_entry(target_row),
            "before": [_to_entry(r) for r in before_rows],
            "after": [_to_entry(r) for r in after_rows],
        }

    return await asyncio.to_thread(_query)


@mcp.tool(annotations=_WRITE_ANNOTATIONS)
async def render_rage_receipt(
    task_summary: str, assistant_excerpt: str, user_reply: str, output_path: str
) -> list[TextContent | Image]:
    """Render a terminal-style card from the 3-field RTFP artifact.

    Produces a styled Rich Panel rendered as SVG (default) or PNG.
    Sections are colour-coded:

    - ``task:`` label in cyan (#4ec9b0), body in dim white
    - ``assistant:`` label in yellow (#dcdcaa), body in dim white
    - ``user:`` label in red (#f44747), body in dim white

    Output format is determined by ``output_path`` extension:

    - ``.svg`` — direct SVG export (primary)
    - ``.png`` — SVG rendered then converted via ``cairosvg``

    The rendered asset is saved to ``output_path`` AND returned inline
    in the MCP response so agents can view the content directly:

    - SVG is returned as text content (the SVG XML string).
    - PNG is returned as an MCP ``ImageContent`` (base64-encoded bytes).

    A leading text content block always carries JSON metadata with
    ``output_path`` and ``format`` for callers with filesystem access.

    Args:
        task_summary: Short description of the task context.
        assistant_excerpt: The offending assistant response excerpt.
        user_reply: The user's frustrated reply.
        output_path: File path to write (``.svg`` or ``.png``).

    Returns:
        List of MCP content blocks: metadata text followed by either
        SVG text or PNG image content.

    Raises:
        ToolError: If the file cannot be written.
    """

    def _render() -> list[TextContent | Image]:
        try:
            return _render_card(task_summary, assistant_excerpt, user_reply, output_path)
        except OSError as exc:
            raise ToolError(f"Failed to write card to {output_path}: {exc}") from exc

    return await asyncio.to_thread(_render)


@mcp.tool(annotations=_READONLY_ANNOTATIONS)
async def scan_transcripts(
    glob_path: str, context_window: int = _DEFAULT_CONTEXT_WINDOW, offset: int = 0, limit: int = 100
) -> dict[str, Any]:
    """Extract raw user messages from JSONL transcript files for classification.

    Returns a paginated list of user messages with surrounding context.
    The caller (Claude) is responsible for classifying each message and
    deciding what to do with it.

    Uses DuckDB ``read_ndjson_auto()`` to query JSONL files directly --
    no persistent database is created.

    Args:
        glob_path: Glob pattern pointing to JSONL transcript files,
            e.g. ``~/.claude/projects/-my-project/*.jsonl``
        context_window: Number of preceding messages to include as
            context for each user message. Default 5.
        offset: Number of messages to skip for pagination. Default 0.
        limit: Maximum number of messages to return. Default 100.

    Returns:
        Dict with messages (list of {file, line_index, text, context}),
        total message count, offset, limit, and files_scanned.
    """

    def _scan() -> dict[str, Any]:
        messages, total, files_scanned = _query_user_messages(glob_path, offset, limit)

        for msg in messages:
            msg["context"] = _get_context_messages(msg["file"], msg["line_index"], context_window)

        return {"messages": messages, "total": total, "offset": offset, "limit": limit, "files_scanned": files_scanned}

    return await asyncio.to_thread(_scan)


@mcp.tool(annotations=_READONLY_ANNOTATIONS)
async def get_scenario(file: str, line_index: int, context_window: int = _DEFAULT_CONTEXT_WINDOW) -> dict[str, Any]:
    """Get the full message context for a specific file and line position.

    Reads the target JSONL file via DuckDB and returns the message at
    the given line index along with surrounding context messages.

    Args:
        file: Path to the JSONL transcript file.
        line_index: Row index (0-based) of the target message.
        context_window: Number of preceding messages to capture.

    Returns:
        Dict with the target message text, file, line_index, and
        preceding context messages.

    Raises:
        ToolError: If the file cannot be read or line_index is out of range.
    """

    def _query() -> dict[str, Any]:
        resolved = _resolve_path(file)
        conn = duckdb.connect()
        row = conn.execute(_SQL_GET_SCENARIO, [resolved, line_index]).fetchone()
        conn.close()

        if not row:
            raise ToolError(f"line_index {line_index} not found in {resolved}")

        msg_type, message, uuid_val, timestamp, session_id = row
        text = _extract_user_text_from_value(message) if msg_type == "user" else ""
        context = _get_context_messages(resolved, line_index, context_window)

        return {
            "file": resolved,
            "line_index": line_index,
            "type": msg_type,
            "text": text,
            "uuid": str(uuid_val or ""),
            "timestamp": str(timestamp or ""),
            "session_id": str(session_id or ""),
            "context": context,
        }

    return await asyncio.to_thread(_query)


@mcp.tool(annotations=_READONLY_ANNOTATIONS)
async def generate_social_post(
    file: str, line_index: int, context_window: int = _DEFAULT_CONTEXT_WINDOW
) -> dict[str, Any]:
    """Generate social media content for a user message from a JSONL file.

    Reads the message directly from the JSONL file via DuckDB and formats
    it as a social media post.  Content is always returned raw so the
    caller (agent) can present it to the user and ask whether any personal
    or business details should be replaced with placeholders before sharing.

    Args:
        file: Path to the JSONL transcript file.
        line_index: Row index (0-based) of the target message.
        context_window: Number of preceding messages for context summary.

    Returns:
        Dict with post, hashtags, and privacy_reminder.

    Raises:
        ToolError: If the message is not found.
    """

    def _generate() -> dict[str, Any]:
        resolved = _resolve_path(file)
        conn = duckdb.connect()

        row = conn.execute(_SQL_GET_MESSAGE, [resolved, line_index]).fetchone()
        conn.close()

        if not row:
            raise ToolError(f"line_index {line_index} not found in {resolved}")

        message_val, _uuid_val, _timestamp = row
        text = _extract_user_text_from_value(message_val)
        if not text:
            raise ToolError(f"No text content at line_index {line_index} in {resolved}")

        hashtags = ["#AIFrustration", "#RTFP", "#ClaudeCode"]
        post_text = f'\U0001f525 RTFP — Read The Fucking Prompt\n\nWhat the user said: "{text}"\n\n{" ".join(hashtags)}'

        return {
            "post": post_text,
            "hashtags": hashtags,
            "privacy_reminder": (
                "Review before sharing: this content may contain personal, business, or identifying details. "
                "Ask the user to confirm, or offer to replace specific details with mock placeholders like "
                "[Company], [Project], [Colleague], [Tool]."
            ),
        }

    return await asyncio.to_thread(_generate)


if __name__ == "__main__":
    mcp.run()

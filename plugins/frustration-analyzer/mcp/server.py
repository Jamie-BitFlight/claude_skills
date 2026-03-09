#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = [
#     "fastmcp>=3.0.0rc1,<4",
#     "duckdb>=0.10.0",
#     "pillow>=10.0.0",
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
    render_rage_receipt   - Render terminal-style PNG card from 3-field artifact
"""

from __future__ import annotations

import asyncio
import json
import logging
import pathlib
import textwrap
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import duckdb
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

if TYPE_CHECKING:
    from PIL.ImageDraw import ImageDraw as PILImageDraw
    from PIL.ImageFont import FreeTypeFont, ImageFont as PILImageFont

logger = logging.getLogger(__name__)

try:
    from PIL import Image, ImageDraw, ImageFont as _ImageFont

    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False

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

# Terminal card colors (dark terminal theme)
_COLOR_BG = (26, 26, 46)  # #1a1a2e
_COLOR_BORDER = (80, 80, 120)
_COLOR_TASK_LABEL = (80, 200, 200)  # dim cyan
_COLOR_ASSISTANT_LABEL = (220, 200, 80)  # yellow
_COLOR_USER_LABEL = (220, 80, 60)  # red/orange
_COLOR_BODY = (230, 230, 230)  # white
_COLOR_HEADER = (140, 140, 180)  # dim purple-white

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
    # Skill/command injection payloads start with XML tags
    if stripped.startswith(("<command-message", "<command-name", "<command-args")):
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
# PNG rendering helpers
# ---------------------------------------------------------------------------


_FONT_CACHE: dict[int, Any] = {}


def _get_font(size: int) -> FreeTypeFont | PILImageFont:
    """Load a monospace font at the given size, falling back to PIL default.

    Results are cached by size to avoid re-loading the font file on every call.

    Args:
        size: Font size in points.

    Returns:
        PIL ImageFont instance (FreeTypeFont if a path matched, else default).
    """
    if size in _FONT_CACHE:
        return _FONT_CACHE[size]

    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeMono.ttf",
        "/usr/share/fonts/TTF/DejaVuSansMono.ttf",
        "/System/Library/Fonts/Menlo.ttc",
        "/Library/Fonts/Courier New.ttf",
        "C:/Windows/Fonts/consola.ttf",
    ]
    for path in candidates:
        if pathlib.Path(path).exists():
            try:
                font = _ImageFont.truetype(path, size)
            except Exception as exc:  # noqa: BLE001
                logger.debug("Could not load font %s: %s", path, exc)
            else:
                _FONT_CACHE[size] = font
                return font
    font = _ImageFont.load_default()
    _FONT_CACHE[size] = font
    return font


_FONT_SIZE = 16
_PADDING = 24
_INNER_WIDTH = 700
_LINE_HEIGHT = _FONT_SIZE + 6
_WRAP_WIDTH = 72


def _wrap_text(text: str) -> list[str]:
    """Word-wrap text into lines of at most _WRAP_WIDTH characters.

    Args:
        text: Multi-line input text.

    Returns:
        List of wrapped lines.
    """
    lines: list[str] = []
    for paragraph in text.split("\n"):
        if paragraph.strip():
            lines.extend(textwrap.wrap(paragraph, _WRAP_WIDTH) or [paragraph])
        else:
            lines.append("")
    return lines


def _count_card_lines(sections: list[tuple[str, list[str], tuple[int, int, int]]]) -> int:
    """Count total text rows needed for the card layout.

    Args:
        sections: List of (label, wrapped_lines, color) tuples.

    Returns:
        Total line count including header and footer spacing.
    """
    total = 1  # header row
    for _, lines, _ in sections:
        total += 2 + len(lines)  # blank + label + content lines
    total += 1  # trailing blank before footer
    return total


def _char_width(font: FreeTypeFont | PILImageFont) -> int:
    """Get the pixel width of a single monospace character for the given font.

    Uses ``getbbox`` on FreeTypeFont; falls back to 8px for PIL's default
    bitmap font.

    Args:
        font: PIL font instance.

    Returns:
        Character width in pixels.
    """
    if hasattr(font, "getbbox"):
        bbox = font.getbbox("─")
        return int(bbox[2] - bbox[0])
    # PIL default bitmap font: fixed 6x11 or 8px wide depending on version
    return 8


def _draw_card(
    draw: PILImageDraw,
    font: FreeTypeFont | PILImageFont,
    sections: list[tuple[str, list[str], tuple[int, int, int]]],
    width: int,
    height: int,
) -> None:
    """Draw all card elements onto the ImageDraw canvas.

    Draws a complete text-art box using ``┌┐└┘│─`` characters so that
    all four sides are connected.  Each content row is bracketed by
    ``│`` on the left and right edges at the same x-positions as the
    corners of the header and footer lines.

    Args:
        draw: PIL ImageDraw instance.
        font: PIL font instance.
        sections: List of (label, wrapped_lines, label_color) tuples.
        width: Total image width.
        height: Total image height.
    """
    pad = _PADDING
    lh = _LINE_HEIGHT
    cw = _char_width(font)

    # The header/footer span _INNER_WIDTH characters total (including corners).
    # header_inner is the number of characters between ┌ and ┐ (exclusive).
    header_inner = _INNER_WIDTH - 2

    # --- Header row: ┌─ RTFP ─────...─┐ ---
    rtfp_label = " RTFP "
    dashes = "─" * (header_inner - len(rtfp_label) - 2)
    header_text = f"┌─{rtfp_label}{dashes}┐"
    draw.text((pad, pad), header_text, font=font, fill=_COLOR_HEADER)

    # x-position of the right-edge │ (same column as ┐ in header)
    right_x = pad + cw * (_INNER_WIDTH - 1)

    def _draw_bordered_line(y_pos: int, content: str, fill: tuple[int, int, int]) -> None:
        """Draw a single content row with │ borders on left and right.

        The content is padded with spaces to fill the full inner width so
        that the right ``│`` aligns with the header/footer corners.

        Args:
            y_pos: Vertical pixel position for the line.
            content: Text content (without border chars) to draw inside.
            fill: RGB color tuple for the content text.
        """
        # Pad content to fill inner width (between the two │ chars)
        # Inner chars = header_inner (space between ┌ and ┐)
        padded = content.ljust(header_inner)
        draw.text((pad, y_pos), "│", font=font, fill=_COLOR_HEADER)
        draw.text((pad + cw, y_pos), padded, font=font, fill=fill)
        draw.text((right_x, y_pos), "│", font=font, fill=_COLOR_HEADER)

    # --- Content rows ---
    y = pad + lh
    for label, lines, label_color in sections:
        _draw_bordered_line(y, "", _COLOR_BODY)  # blank separator line
        y += lh
        _draw_bordered_line(y, f" {label}", label_color)
        y += lh
        for line in lines:
            _draw_bordered_line(y, f"   {line}", _COLOR_BODY)
            y += lh

    _draw_bordered_line(y, "", _COLOR_BODY)  # trailing blank before footer
    y += lh

    # --- Footer row: └────────...─┘ ---
    draw.text((pad, y), f"└{'─' * header_inner}┘", font=font, fill=_COLOR_HEADER)


def _render_png(task_summary: str, assistant_excerpt: str, user_reply: str, output_path: str) -> dict[str, Any]:
    """Render a terminal-style PNG card.

    Args:
        task_summary: Short description of the task context.
        assistant_excerpt: The offending assistant response excerpt.
        user_reply: The user's frustrated reply.
        output_path: File path to write the PNG.

    Returns:
        Dict with output_path, width, height.
    """
    font: FreeTypeFont | PILImageFont = _get_font(_FONT_SIZE)
    sections: list[tuple[str, list[str], tuple[int, int, int]]] = [
        ("task:", _wrap_text(task_summary), _COLOR_TASK_LABEL),
        ("assistant:", _wrap_text(assistant_excerpt), _COLOR_ASSISTANT_LABEL),
        ("user:", _wrap_text(user_reply), _COLOR_USER_LABEL),
    ]
    total_lines = _count_card_lines(sections)
    height = _PADDING * 2 + total_lines * _LINE_HEIGHT + 4
    width = _INNER_WIDTH + _PADDING * 2

    img = Image.new("RGB", (width, height), color=_COLOR_BG)
    draw = ImageDraw.Draw(img)
    _draw_card(draw, font, sections, width, height)

    out = pathlib.Path(output_path).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(out), format="PNG")

    return {"output_path": str(out), "width": width, "height": height}


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
) -> dict[str, Any]:
    """Render a terminal-style PNG card from the 3-field RTFP artifact.

    Produces a dark-background terminal-style PNG with:
    - task label in dim cyan
    - "assistant:" label in yellow, body in white
    - "user:" label in red/orange, body in white

    Uses PIL with a bundled or system monospace font, falling back to
    PIL's built-in default font.  Works without network access.

    Layout::

        ┌─ RTFP ──────────────────────────────────────┐

          task: {task_summary}

          assistant:
            {assistant_excerpt (word-wrapped)}

          user:
            {user_reply (word-wrapped)}

        └──────────────────────────────────────────────┘

    Args:
        task_summary: Short description of the task context.
        assistant_excerpt: The offending assistant response excerpt.
        user_reply: The user's frustrated reply.
        output_path: File path to write the PNG (e.g. ``/tmp/rtfp.png``).

    Returns:
        Dict with ``output_path``, ``width``, and ``height``.

    Raises:
        ToolError: If PIL is unavailable or the file cannot be written.
    """

    def _render() -> dict[str, Any]:
        if not _PIL_AVAILABLE:
            raise ToolError("pillow is required for render_rage_receipt but is not installed")
        try:
            return _render_png(task_summary, assistant_excerpt, user_reply, output_path)
        except OSError as exc:
            raise ToolError(f"Failed to write PNG to {output_path}: {exc}") from exc

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

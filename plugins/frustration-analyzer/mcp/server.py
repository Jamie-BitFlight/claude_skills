#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = [
#     "fastmcp>=3.0.0rc1,<4",
#     "duckdb>=0.10.0",
#     "rich>=13.0",
#     "cairosvg>=2.7.0",
#     "tiktoken>=0.7.0",
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
import re
import xml.etree.ElementTree as ET  # noqa: S405
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element as _Element

import duckdb
import tiktoken
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

_DEFAULT_BATCH_TOKENS: int = 100_000
_TIKTOKEN_ENCODING: str = "p50k_base"


class _EncoderCache:
    """Lazily-initialised tiktoken encoder singleton."""

    _enc: tiktoken.Encoding | None = None

    @classmethod
    def get(cls) -> tiktoken.Encoding:
        """Return the shared p50k_base encoder, creating it on first call."""
        if cls._enc is None:
            cls._enc = tiktoken.get_encoding(_TIKTOKEN_ENCODING)
        return cls._enc


def _count_tokens(text: str) -> int:
    """Count tokens using tiktoken p50k_base encoding (Claude approximation).

    Args:
        text: The string to tokenise.

    Returns:
        Number of tokens in the text.
    """
    return len(_EncoderCache.get().encode(text))


def _split_into_batches(messages: list[dict[str, Any]], batch_tokens: int) -> list[list[dict[str, Any]]]:
    """Split messages into token-bounded batches.

    Args:
        messages: List of message dicts, each with a ``token_count`` key.
        batch_tokens: Maximum token budget per batch.

    Returns:
        List of batch lists. Each batch stays within the token budget.
    """
    batches: list[list[dict[str, Any]]] = []
    current_batch: list[dict[str, Any]] = []
    current_tokens = 0
    for msg in messages:
        tokens = msg["token_count"]
        if current_tokens + tokens > batch_tokens and current_batch:
            batches.append(current_batch)
            current_batch = []
            current_tokens = 0
        current_batch.append(msg)
        current_tokens += tokens
    if current_batch:
        batches.append(current_batch)
    return batches


def _write_batches(messages: list[dict[str, Any]], output_path: str, batch_tokens: int) -> list[str]:
    """Write messages to one or more batch JSONL files.

    When total tokens fit within ``batch_tokens``, writes a single file at
    ``output_path`` for backward compatibility.  Otherwise splits into
    multiple files in a directory derived from ``output_path``.

    Args:
        messages: User message dicts to write.
        output_path: Base output file path.
        batch_tokens: Token budget per batch.

    Returns:
        List of written file paths.
    """
    total_tokens = sum(m["token_count"] for m in messages)

    if total_tokens <= batch_tokens:
        out_path = pathlib.Path(output_path).expanduser()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as fh:
            for msg in messages:
                fh.write(json.dumps(msg) + "\n")
        return [str(out_path)]

    base = pathlib.Path(output_path).expanduser()
    batch_dir = base.parent / f"rtfp-batches-{base.stem}"
    batch_dir.mkdir(parents=True, exist_ok=True)

    batches = _split_into_batches(messages, batch_tokens)
    written_paths: list[str] = []
    for i, batch in enumerate(batches):
        batch_path = batch_dir / f"batch_{i + 1:03d}.jsonl"
        with batch_path.open("w", encoding="utf-8") as fh:
            for msg in batch:
                fh.write(json.dumps(msg) + "\n")
        written_paths.append(str(batch_path))
    return written_paths


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


_SVG_NS = "http://www.w3.org/2000/svg"
_SVG_NS_MAP = {"svg": _SVG_NS}
_BORDER_COLOR = "#1984e9"
_BOX_DRAWING_CHARS = frozenset("╭╮╰╯│─┐┘┌└├┤┬┴┼")
_G_TAG = f"{{{_SVG_NS}}}g"
_TEXT_TAG = f"{{{_SVG_NS}}}text"
_CLIP_LINE_MARKER = "-line-"
_CLIP_FIRST_LINE_MARKER = "-line-0"
_CONSOLE_WIDTH = 100

_RE_TRANSLATE = re.compile(r"translate\(")
_RE_TRANSLATE_COORDS = re.compile(r"translate\(\s*([\d.]+)\s*,\s*([\d.]+)\s*\)")


def _find_content_group(root: _Element) -> _Element | None:
    """Find the outermost ``<g transform="translate(...)">`` containing text.

    Args:
        root: Parsed SVG ``Element`` root.

    Returns:
        The ``<g>`` element, or ``None`` if the expected structure is absent.
    """
    for g in root.iter(_G_TAG):
        if _RE_TRANSLATE.search(g.get("transform", "")) and any(True for _ in g.iter(_TEXT_TAG)):
            return g
    return None


def _parse_translate(g: _Element) -> tuple[float, float]:
    """Extract ``(tx, ty)`` from a ``translate()`` transform attribute.

    Args:
        g: An SVG ``<g>`` element.

    Returns:
        Tuple of ``(tx, ty)`` floats, defaulting to ``(9.0, 41.0)``.
    """
    m = _RE_TRANSLATE_COORDS.search(g.get("transform", ""))
    return (float(m.group(1)), float(m.group(2))) if m else (9.0, 41.0)


def _extract_line_height(root: _Element) -> float:
    """Read ``line-height`` from the embedded ``<style>`` element.

    Args:
        root: Parsed SVG ``Element`` root.

    Returns:
        Line height in pixels (defaults to ``24.4``).
    """
    style_el = root.find(f"{{{_SVG_NS}}}style")
    if style_el is not None and style_el.text and (m := re.search(r"line-height:\s*([\d.]+)px", style_el.text)):
        return float(m.group(1))
    return 24.4


def _count_line_clips(root: _Element) -> tuple[int, float]:
    """Count content line clip-paths and find the first line's y-offset.

    Args:
        root: Parsed SVG ``Element`` root.

    Returns:
        Tuple of ``(num_lines, first_line_y)``.
    """
    clips = root.findall(".//svg:defs/svg:clipPath", _SVG_NS_MAP)
    num_lines = 0
    first_line_y = 1.5
    for cp in clips:
        cp_id = cp.get("id") or ""
        if _CLIP_LINE_MARKER not in cp_id:
            continue
        num_lines += 1
        if _CLIP_FIRST_LINE_MARKER in cp_id:
            rect_el = cp.find(f"{{{_SVG_NS}}}rect")
            if rect_el is not None:
                first_line_y = float(rect_el.get("y", "1.5"))
    return num_lines, first_line_y


def _find_matrix_group(outer_g: _Element) -> _Element:
    """Locate the ``<g class="...-matrix">`` inside the content group.

    Args:
        outer_g: The translated content ``<g>`` element.

    Returns:
        The matrix ``<g>``, or *outer_g* as fallback.
    """
    for g in outer_g.iter(_G_TAG):
        if "matrix" in g.get("class", ""):
            return g
    return outer_g


def _is_box_drawing_only(text: str) -> bool:
    """Return True if *text* contains only box-drawing and whitespace chars.

    Args:
        text: Normalised text content of an SVG ``<text>`` element.

    Returns:
        True when all visible characters are box-drawing glyphs.
    """
    non_ws = text.replace(" ", "").replace("\n", "").replace("\r", "")
    return bool(non_ws) and all(c in _BOX_DRAWING_CHARS for c in non_ws)


def _hide_box_drawing_glyphs(matrix_g: _Element) -> None:
    """Set ``fill-opacity="0"`` on text elements that contain only box-drawing chars.

    After hiding, any element whose non-box-drawing content equals the
    panel title ``"RTFP"`` is re-shown so the title remains visible.

    Args:
        matrix_g: The matrix ``<g>`` element containing rendered text.
    """
    # Single pass: hide box-drawing elements and find the title candidate
    title_candidate: _Element | None = None
    longest_non_box = 0
    for text_el in matrix_g.iter(_TEXT_TAG):
        raw = "".join(text_el.itertext()).strip().replace("\xa0", " ")
        if _is_box_drawing_only(raw):
            text_el.set("fill-opacity", "0")
            # Check if this hidden element contains the RTFP title
            cleaned = "".join(c for c in raw if c not in _BOX_DRAWING_CHARS).strip()
            if cleaned == "RTFP" and len(cleaned) > longest_non_box:
                longest_non_box = len(cleaned)
                title_candidate = text_el

    # Re-show the RTFP title element (it shares a row with ─ chars)
    if title_candidate is not None:
        title_candidate.attrib.pop("fill-opacity", None)


def _inject_border_rect(svg_text: str) -> str:
    """Replace Rich's box-drawing character border with a continuous SVG rect.

    Rich renders Panel borders using individual box-drawing glyphs
    (``╭╮╰╯│─``).  When cairosvg rasterises these, sub-pixel gaps appear
    between glyphs -- especially at the corners.  This function hides the
    glyph-based border and injects an SVG ``<rect>`` with a solid stroke
    that traces the same boundary as a single continuous path.

    Args:
        svg_text: The raw SVG string produced by ``console.export_svg()``.

    Returns:
        Modified SVG string with gapless border rect and hidden box glyphs.
    """
    ET.register_namespace("", _SVG_NS)
    root = ET.fromstring(svg_text)  # noqa: S314

    outer_g = _find_content_group(root)
    if outer_g is None:
        return svg_text

    tx, ty = _parse_translate(outer_g)
    line_height = _extract_line_height(root)
    char_width = line_height / 2.0
    num_lines, first_line_y = _count_line_clips(root)

    _hide_box_drawing_glyphs(_find_matrix_group(outer_g))

    # Rect aligns with where box-drawing chars were: left/right edges
    # centered on first/last character cells, top/bottom at clip boundaries.
    rect_attrs: dict[str, str] = {
        "x": f"{tx + char_width * 0.5:.1f}",
        "y": f"{ty + first_line_y:.1f}",
        "width": f"{char_width * (_CONSOLE_WIDTH - 1):.1f}",
        "height": f"{num_lines * line_height:.1f}",
        "rx": "4",
        "ry": "4",
        "fill": "none",
        "stroke": _BORDER_COLOR,
        "stroke-width": "2",
    }
    rect = ET.SubElement(root, f"{{{_SVG_NS}}}rect")
    for attr, val in rect_attrs.items():
        rect.set(attr, val)

    return ET.tostring(root, encoding="unicode", xml_declaration=False)


_DEFAULT_WIDTH: int = 900
_DEFAULT_FONT_SIZE: int = 15


def _apply_svg_dimensions(svg_text: str, *, width: int, font_size: int) -> str:
    """Apply configurable width and font-size to an SVG string.

    Rewrites the root ``<svg>`` element's ``width`` attribute and
    updates ``font-size`` declarations in the embedded ``<style>``
    element.  The aspect ratio is preserved by scaling ``height``
    proportionally.

    Args:
        svg_text: Raw SVG XML string.
        width: Desired image width in pixels.
        font_size: Desired font size in points.

    Returns:
        Modified SVG string with updated dimensions.
    """
    ET.register_namespace("", _SVG_NS)
    root = ET.fromstring(svg_text)  # noqa: S314

    # Scale width/height proportionally
    old_width_str = root.get("width", "")
    old_width = float(re.sub(r"[^0-9.]", "", old_width_str)) if old_width_str else float(width)
    scale = width / old_width if old_width else 1.0

    root.set("width", str(width))

    old_height_str = root.get("height", "")
    if old_height_str:
        old_height = float(re.sub(r"[^0-9.]", "", old_height_str))
        root.set("height", str(int(old_height * scale)))

    # Update font-size in embedded <style>
    style_el = root.find(f"{{{_SVG_NS}}}style")
    if style_el is not None and style_el.text:
        style_el.text = re.sub(r"font-size:\s*[\d.]+px", f"font-size: {font_size}px", style_el.text)

    return ET.tostring(root, encoding="unicode", xml_declaration=False)


def _render_card(
    task_summary: str,
    assistant_excerpt: str,
    user_reply: str,
    output_path: str,
    width: int = _DEFAULT_WIDTH,
    font_size: int = _DEFAULT_FONT_SIZE,
) -> list[TextContent | Image]:
    """Render a terminal-style card as SVG or PNG.

    Uses Rich ``Console(record=True)`` to render a styled Panel, then
    exports as SVG.  The Rich box-drawing character border is replaced
    with a continuous SVG ``<rect>`` stroke to eliminate sub-pixel gaps
    that appear when cairosvg rasterises individual glyphs.

    If ``output_path`` ends with ``.png``, the patched SVG is converted
    to PNG via ``cairosvg.svg2png()``.

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
        width: Image width in pixels for the output. Default 900.
        font_size: Font size in points for the SVG/PNG text. Default 15.

    Returns:
        List of MCP content blocks: metadata ``TextContent`` followed by
        either an SVG ``TextContent`` or a PNG ``Image``.
    """
    content = _build_card_content(task_summary, assistant_excerpt, user_reply)
    panel = Panel(content, title="RTFP", title_align="left", border_style="bright_blue", padding=(1, 2))

    console = Console(record=True, width=_CONSOLE_WIDTH, force_terminal=True, color_system="truecolor")
    panel.width = console.width
    console.print(panel)

    svg_text = console.export_svg(title="RTFP")

    # Replace box-drawing character border with a continuous SVG <rect>
    svg_text = _inject_border_rect(svg_text)

    # Apply configurable dimensions: scale SVG viewBox and font-size
    svg_text = _apply_svg_dimensions(svg_text, width=width, font_size=font_size)

    out = pathlib.Path(output_path).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)

    is_png = out.suffix.lower() == ".png"
    if is_png:
        import cairosvg  # noqa: PLC0415

        png_bytes: bytes = cairosvg.svg2png(bytestring=svg_text.encode("utf-8"), output_width=width)
        out.write_bytes(png_bytes)
        inline_content: TextContent | Image = Image(data=png_bytes, format="png")
    else:
        out.write_text(svg_text, encoding="utf-8")
        inline_content = TextContent(type="text", text=svg_text)

    metadata = json.dumps({"output_path": str(out), "format": "png" if is_png else "svg"})
    return [TextContent(type="text", text=metadata), inline_content]


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

        # Pre-compute stat() per file to avoid calling it twice (once for
        # sort key, once inside the loop).
        file_stats = [(f, f.stat()) for f in root.rglob("*.jsonl")]
        file_stats.sort(key=lambda pair: pair[1].st_mtime, reverse=True)

        sessions: list[dict[str, Any]] = []
        conn = duckdb.connect()
        try:
            for f, stat in file_stats:
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
async def extract_user_messages(
    file: str, output_path: str, batch_tokens: int = _DEFAULT_BATCH_TOKENS
) -> dict[str, Any]:
    """Extract user-only messages from a session file to batch JSONL file(s).

    Reads the given JSONL session file via DuckDB and filters to ONLY
    user-authored messages (type='user', toolUseResult IS NULL).

    **Token-aware batch splitting**: Uses tiktoken (p50k_base) to count
    tokens per message.  When the session's total token count exceeds
    ``batch_tokens``, the output is split into multiple batch files inside
    a directory derived from ``output_path`` (e.g. for ``/tmp/batch.jsonl``
    the directory ``/tmp/rtfp-batches-batch/batch_001.jsonl``, etc.).
    When the session fits in a single batch, a single file is written at
    ``output_path`` for backward compatibility.

    Each output JSONL entry:
    ``{"file": str, "line_index": int, "text": str, "token_count": int}``.

    No assistant messages, tool outputs, or context is included.
    The output is suitable as input to a Stage 2 batch-detector subagent.

    Args:
        file: Path to the source JSONL session file.
        output_path: Path to write the output batch JSONL file.
        batch_tokens: Target token budget per batch file.  When total
            tokens exceed this value the output is split into multiple
            files.  Default 100 000.

    Returns:
        Dict with ``output_paths`` (list of written file paths),
        ``batch_count``, ``message_count``, ``total_tokens``, and
        ``source_file``.  For single-batch output ``output_paths``
        contains one entry identical to the legacy ``output_path``.

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

        # -- Collect user messages with token counts -------------------------
        user_messages: list[dict[str, Any]] = []
        for line_index, msg_type, _timestamp, message, tool_use_result in rows:
            if msg_type != "user" or tool_use_result is not None:
                continue
            text = _extract_user_text_from_value(message)
            if not text or not _is_human_plaintext(text):
                continue
            token_count = _count_tokens(text)
            user_messages.append({
                "file": resolved,
                "line_index": int(line_index),
                "text": text,
                "token_count": token_count,
            })

        total_tokens = sum(m["token_count"] for m in user_messages)

        written_paths = _write_batches(user_messages, output_path, batch_tokens)

        return {
            "output_paths": written_paths,
            "batch_count": len(written_paths),
            "message_count": len(user_messages),
            "total_tokens": total_tokens,
            "source_file": resolved,
        }

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
    task_summary: str,
    assistant_excerpt: str,
    user_reply: str,
    output_path: str,
    width: int = _DEFAULT_WIDTH,
    font_size: int = _DEFAULT_FONT_SIZE,
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
        width: Image width in pixels. Default 900.
        font_size: Font size in points. Default 15.

    Returns:
        List of MCP content blocks: metadata text followed by either
        SVG text or PNG image content.

    Raises:
        ToolError: If the file cannot be written.
    """

    def _render() -> list[TextContent | Image]:
        try:
            return _render_card(
                task_summary, assistant_excerpt, user_reply, output_path, width=width, font_size=font_size
            )
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

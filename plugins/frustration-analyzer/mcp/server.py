#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = [
#     "fastmcp>=3.0.0rc1,<4",
#     "duckdb>=0.10.0",
# ]
# ///
"""Frustration Analyzer MCP Server.

Extracts user messages from Claude Code session transcripts using DuckDB as
a query engine against the existing JSONL session log files.  No persistent
database file is created -- every query runs in-memory against
``read_ndjson_auto()``.

Tools:
    scan_transcripts - Extract raw user messages from JSONL files for caller classification
    list_insults - Query user messages from JSONL files with optional filters
    top_insults - Return the longest/most notable user messages from JSONL files
    get_scenario - Get full message context for a specific file + line position
    generate_social_post - Generate social media content for a user message
    sanitize_text - Standalone PII sanitizer
"""

from __future__ import annotations

import asyncio
import logging
import pathlib
import re
from typing import Any

import duckdb
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_CONTEXT_WINDOW: int = 5
_MIN_TOKEN_LENGTH: int = 20

_READONLY_ANNOTATIONS: dict[str, bool] = {
    "readOnlyHint": True,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": False,
}

_CATEGORY_DISPLAY: dict[str, str] = {
    "profanity_at_ai": "Raw Rage",
    "model_comparison": "Model Shade",
    "competence_challenge": "Competence Check",
    "intelligence_insult": "Intelligence Insult",
    "repeat_failure": "Broken Record",
    "sarcasm": "Sarcasm",
    "dismissive_command": "Dismissal",
    "technical_putdown": "Technical Put-Down",
    "general_frustration": "General Frustration",
}

_CATEGORY_HASHTAGS: dict[str, str] = {
    "profanity_at_ai": "#RawRage",
    "model_comparison": "#ModelShade",
    "competence_challenge": "#CompetenceCheck",
    "intelligence_insult": "#IntelligenceInsult",
    "repeat_failure": "#BrokenRecord",
    "sarcasm": "#SarcasmDetected",
    "dismissive_command": "#Dismissed",
    "technical_putdown": "#TechnicalBurn",
    "general_frustration": "#GeneralFrustration",
}

# PII sanitization patterns (ordered most specific first)
_PII_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    ("EMAIL", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "[EMAIL]"),
    ("IP", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "[IP]"),
    ("TOKEN", re.compile(r"\b(?:sk-|ghp_|gho_|github_pat_|xoxb-|xoxp-|Bearer\s+)?[A-Za-z0-9_\-]{20,}\b"), "[TOKEN]"),
    (
        "PATH",
        re.compile(
            r"(?:/home/[A-Za-z0-9._-]+|/Users/[A-Za-z0-9._-]+|C:\\Users\\[A-Za-z0-9._-]+)"
            r"(?:[/\\][A-Za-z0-9._\-/\\]*)*"
        ),
        "[PATH]",
    ),
    ("URL", re.compile(r"https?://[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]+"), "[URL]"),
]

# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

mcp = FastMCP("frustration-analyzer", mask_error_details=False)

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

    # No glob characters — treat as a literal file path
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


def _query_user_messages(glob_path: str, offset: int = 0, limit: int = 100) -> tuple[list[dict[str, Any]], int, int]:
    """Query user messages from JSONL files using DuckDB.

    Uses ``read_ndjson_auto()`` to read JSONL files and SQL to filter
    for user messages (type = 'user', no toolUseResult).

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

    # Assign stable line_index (0-based row position in file) before filtering,
    # so line_index matches the actual line number for context lookups.
    total_row = conn.execute(_SQL_COUNT_USER_MESSAGES, [files]).fetchone()
    total = total_row[0] if total_row else 0

    rows = conn.execute(_SQL_QUERY_USER_MESSAGES, [files, limit, offset]).fetchall()
    columns = ["file", "line_index", "message", "uuid", "timestamp", "session_id"]
    conn.close()

    messages: list[dict[str, Any]] = []
    for row in rows:
        record = dict(zip(columns, row, strict=False))
        text = _extract_user_text_from_value(record.pop("message"))
        if text:
            record["text"] = text
            messages.append(record)

    return messages, total, len(files)


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
    # Unwrap {"content": ...} dict wrapper
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


def _get_context_messages(file_path: str, line_index: int, context_window: int) -> list[dict[str, Any]]:
    """Get surrounding context messages for a specific position in a JSONL file.

    Uses DuckDB to read the file and extract preceding messages.

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


def _sanitize_text_impl(text: str) -> dict[str, Any]:
    """Strip PII from text, returning sanitized version and redaction log.

    Args:
        text: The raw text to sanitize.

    Returns:
        Dict with original, sanitized, redactions list, and redaction_count.
    """
    sanitized = text
    redactions: list[dict[str, str]] = []

    for pii_type, pattern, replacement in _PII_PATTERNS:
        for match in pattern.finditer(sanitized):
            original_text = match.group()
            # Skip short matches for TOKEN pattern to avoid false positives
            if pii_type == "TOKEN" and len(original_text) < _MIN_TOKEN_LENGTH:
                continue
            redactions.append({"type": pii_type, "original": original_text, "replacement": replacement})

    # Apply redactions in reverse order to preserve positions
    for redaction in reversed(redactions):
        sanitized = sanitized.replace(redaction["original"], redaction["replacement"], 1)

    return {"original": text, "sanitized": sanitized, "redactions": redactions, "redaction_count": len(redactions)}


def _build_hashtags(category: str, model: str | None) -> list[str]:
    """Build hashtag list for a social post.

    Args:
        category: Insult category slug.
        model: Model name (str or None).

    Returns:
        List of hashtag strings.
    """
    hashtags: list[str] = ["#AIFrustration"]
    category_tag = _CATEGORY_HASHTAGS.get(category)
    if category_tag:
        hashtags.append(category_tag)
    if isinstance(model, str) and "claude" in model.lower():
        hashtags.append("#ClaudeCode")
    return hashtags


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------


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

        # Enrich each message with context from surrounding records
        for msg in messages:
            msg["context"] = _get_context_messages(msg["file"], msg["line_index"], context_window)

        return {"messages": messages, "total": total, "offset": offset, "limit": limit, "files_scanned": files_scanned}

    return await asyncio.to_thread(_scan)


@mcp.tool(annotations=_READONLY_ANNOTATIONS)
async def list_insults(
    glob_path: str, category: str = "", min_length: int = 0, limit: int = 20, offset: int = 0
) -> dict[str, Any]:
    """Query user messages from JSONL transcript files with optional filters.

    Searches JSONL session logs directly via DuckDB for user messages.
    Optionally filter by minimum text length. The ``category`` parameter
    is accepted for forward-compatibility but requires caller-side
    classification to be meaningful.

    Args:
        glob_path: Glob pattern pointing to JSONL transcript files.
        category: Reserved for caller-side filtering (currently unused
            -- all messages returned regardless of category value).
        min_length: Minimum character length of user message text.
        limit: Maximum number of results to return.
        offset: Number of results to skip for pagination.

    Returns:
        Dict with messages list, total count, offset, limit, and
        files_scanned.
    """

    def _query() -> dict[str, Any]:
        messages, total, files_scanned = _query_user_messages(glob_path, offset, limit)
        if min_length > 0:
            messages = [m for m in messages if len(m.get("text", "")) >= min_length]
        return {
            "messages": messages,
            "total": total,
            "offset": offset,
            "limit": limit,
            "files_scanned": files_scanned,
            "category_filter": category or None,
        }

    return await asyncio.to_thread(_query)


@mcp.tool(annotations=_READONLY_ANNOTATIONS)
async def top_insults(glob_path: str, n: int = 10, sort_by: str = "length") -> dict[str, Any]:
    """Return the top N user messages sorted by length from JSONL files.

    Queries JSONL session logs directly via DuckDB.  Without a
    persistent rating store, messages are ranked by text length as a
    proxy for expressiveness.

    Args:
        glob_path: Glob pattern pointing to JSONL transcript files.
        n: Number of top messages to return.
        sort_by: Sort dimension. Currently only ``length`` is supported.

    Returns:
        Dict with messages list, count, and sort_by value.

    Raises:
        ToolError: If sort_by is not a valid dimension.
    """
    valid_sorts = {"length"}
    if sort_by not in valid_sorts:
        raise ToolError(f"sort_by must be one of {valid_sorts}, got: {sort_by}")

    def _query() -> dict[str, Any]:
        messages, _total, _files_scanned = _query_user_messages(glob_path, offset=0, limit=n * 3)
        # Sort by text length descending and take top N
        messages.sort(key=lambda m: len(m.get("text", "")), reverse=True)
        top = messages[:n]
        return {"messages": top, "count": len(top), "sort_by": sort_by}

    return await asyncio.to_thread(_query)


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
        resolved = str(pathlib.Path(file).expanduser()) if "~" in file else file
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
    file: str,
    line_index: int,
    category: str = "general_frustration",
    mode: str = "sanitized",
    context_window: int = _DEFAULT_CONTEXT_WINDOW,
) -> dict[str, Any]:
    """Generate social media content for a user message from a JSONL file.

    Reads the message directly from the JSONL file via DuckDB, formats
    it as a social media post with the caller-provided category.

    Args:
        file: Path to the JSONL transcript file.
        line_index: Row index (0-based) of the target message.
        category: Insult category slug for display/hashtags.
        mode: Either ``raw`` (verbatim text) or ``sanitized`` (PII stripped).
        context_window: Number of preceding messages for context summary.

    Returns:
        Dict with post_text, raw_text, sanitized_text, char_count,
        and hashtags.

    Raises:
        ToolError: If the message is not found or mode is invalid.
    """
    if mode not in {"raw", "sanitized"}:
        raise ToolError(f"mode must be 'raw' or 'sanitized', got: {mode}")

    def _generate() -> dict[str, Any]:
        resolved = str(pathlib.Path(file).expanduser()) if "~" in file else file
        conn = duckdb.connect()

        row = conn.execute(_SQL_GET_MESSAGE, [resolved, line_index]).fetchone()
        conn.close()

        if not row:
            raise ToolError(f"line_index {line_index} not found in {resolved}")

        message_val, _uuid_val, _timestamp = row
        text = _extract_user_text_from_value(message_val)
        if not text:
            raise ToolError(f"No text content at line_index {line_index} in {resolved}")

        sanitized_result = _sanitize_text_impl(text)
        sanitized_text = sanitized_result["sanitized"]
        display_text = sanitized_text if mode == "sanitized" else text

        # Look for model name in preceding assistant messages
        context = _get_context_messages(resolved, line_index, context_window)
        model: str | None = None
        for ctx_msg in reversed(context):
            if ctx_msg.get("role") == "assistant" and ctx_msg.get("text"):
                # Model info isn't in context text; leave as None
                break

        hashtags = _build_hashtags(category, model)
        post_text = (
            f"\U0001f525 AI Frustration Report\n"
            f"\n"
            f'What the user said: "{display_text}"\n'
            f"\n"
            f"Category: {_CATEGORY_DISPLAY.get(category, category)}\n"
            f"\n"
            f"{' '.join(hashtags)}"
        )

        return {
            "file": resolved,
            "line_index": line_index,
            "mode": mode,
            "post_text": post_text,
            "raw_text": text,
            "sanitized_text": sanitized_text,
            "char_count": len(post_text),
            "hashtags": hashtags,
        }

    return await asyncio.to_thread(_generate)


@mcp.tool(annotations=_READONLY_ANNOTATIONS)
async def sanitize_text(text: str) -> dict[str, Any]:
    """Strip PII from arbitrary text.

    Detects and replaces email addresses, IP addresses, file paths,
    URLs, and API tokens/keys with type-specific placeholders.

    Args:
        text: The raw text to sanitize.

    Returns:
        Dict with original text, sanitized text, list of redactions
        (each with type, original, replacement), and redaction_count.
    """
    return await asyncio.to_thread(_sanitize_text_impl, text)


if __name__ == "__main__":
    mcp.run()

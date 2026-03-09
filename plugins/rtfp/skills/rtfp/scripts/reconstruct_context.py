#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "duckdb>=1.0.0",
# ]
# ///
"""Retrieve context windows around flagged user messages from a session transcript.

Stage 3 helper tool for the RTFP pipeline. This script is a RETRIEVAL TOOL,
not a decision-maker. It accepts a flagged JSON file path and uses DuckDB to
load both the flagged data and the session transcript, returning a window of
nearby transcript entries for each flagged index so the calling agent can
inspect the surrounding context and make its own judgments about winner/runner-up
selection and task summary.

Input (--flagged-file, required)::

    {"source_file": "/path/to/session.jsonl", "flagged_indexes": [12, 45, 78]}

Output (stdout, JSON)::

    {
        "session_file": "/path/to/session.jsonl",
        "contexts": [{"flagged_index": 12, "user_message": "...", "nearby_entries": [...]}],
    }

Usage::

    reconstruct_context.py --flagged-file flagged.json
    reconstruct_context.py --flagged-file flagged.json --session-file /path/to/session.jsonl
    reconstruct_context.py --flagged-file flagged.json --window 15
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import duckdb

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_WINDOW = 10  # entries before and after the flagged message


# ---------------------------------------------------------------------------
# DuckDB JSONL loading
# ---------------------------------------------------------------------------


def _load_transcript_duckdb(session_path: Path) -> list[dict]:
    """Load all records from a session JSONL file using DuckDB read_ndjson.

    Each returned dict preserves the original JSONL fields and gains an
    ``_line_index`` field indicating its zero-based position in the file.

    Args:
        session_path: Path to the session JSONL file.

    Returns:
        Ordered list of parsed message records.

    Raises:
        FileNotFoundError: If the session file does not exist.
        duckdb.IOException: If DuckDB cannot read the file.
    """
    if not session_path.exists():
        raise FileNotFoundError(f"Session file not found: {session_path}")

    # read_ndjson_auto reads newline-delimited JSON; maximum_object_size
    # handles large assistant messages.  Use parameterized query to avoid
    # S608 (SQL injection) lint warning.
    query = """
        SELECT *, row_number() OVER () - 1 AS _line_index
        FROM read_ndjson_auto($1, maximum_object_size=10485760)
    """
    with duckdb.connect(":memory:") as con:
        result = con.execute(query, [str(session_path)]).fetchall()
        columns = [desc[0] for desc in con.description]

    return [dict(zip(columns, row, strict=False)) for row in result]


def _load_flagged_duckdb(flagged_path: Path) -> dict[str, Any]:
    """Load flagged message data from a JSON file using DuckDB read_json_auto.

    Args:
        flagged_path: Path to the flagged JSON file produced by reaction-detector.

    Returns:
        Dict with 'source_file' (str) and 'flagged_indexes' (list[int]) keys.

    Raises:
        FileNotFoundError: If the flagged file does not exist.
        ValueError: If the file contains no data.
        duckdb.IOException: If DuckDB cannot read the file.
    """
    if not flagged_path.exists():
        raise FileNotFoundError(f"Flagged file not found: {flagged_path}")

    with duckdb.connect(":memory:") as con:
        row = con.execute("SELECT source_file, flagged_indexes FROM read_json_auto($1)", [str(flagged_path)]).fetchone()
        columns = [desc[0] for desc in con.description]

    if row is None:
        raise ValueError(f"No data found in flagged file: {flagged_path}")

    data = dict(zip(columns, row, strict=False))
    flagged = data.get("flagged_indexes") or []
    data["flagged_indexes"] = [int(i) for i in flagged]
    return data


# ---------------------------------------------------------------------------
# Content extraction helpers
# ---------------------------------------------------------------------------


def _extract_text(content: str | list | dict | None) -> str:
    """Extract readable text from a message content field.

    Handles plain strings, lists of content blocks (text and tool_use),
    and nested dicts.

    Args:
        content: Raw content from the message object.

    Returns:
        Plain text representation of the message content.
    """
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, dict):
        # Single content block
        if content.get("type") == "text":
            return content.get("text", "")
        return json.dumps(content, ensure_ascii=False)
    # list of content blocks
    parts: list[str] = []
    for element in content:
        if not isinstance(element, dict):
            parts.append(str(element))
            continue
        match element.get("type"):
            case "text":
                text = element.get("text")
                if isinstance(text, str):
                    parts.append(text)
            case "tool_use":
                name = element.get("name", "unknown_tool")
                parts.append(f"[tool_use: {name}]")
            case "tool_result":
                parts.append("[tool_result]")
            case other:
                if other:
                    parts.append(f"[{other}]")
    return "\n".join(parts)


def _extract_message_text(rec: dict) -> str:
    """Extract readable text from the 'message' field of a transcript record.

    Args:
        rec: Raw record dict from the transcript.

    Returns:
        Plain text of the message content, or empty string if absent.
    """
    message = rec.get("message")
    if isinstance(message, dict):
        return _extract_text(message.get("content"))
    if isinstance(message, str):
        return message
    return ""


def _record_to_entry(rec: dict) -> dict:
    """Convert a raw transcript record to a simplified entry for output.

    Preserves the essential fields an agent needs to read the context:
    type, role, text content, timestamp, and line index.

    Args:
        rec: Raw record dict from the transcript.

    Returns:
        Simplified entry dict.
    """
    entry: dict = {}

    # Position
    if "_line_index" in rec:
        entry["_line_index"] = rec["_line_index"]

    # Type / role
    rec_type = rec.get("type")
    if rec_type is not None:
        entry["type"] = rec_type

    # Timestamp
    timestamp = rec.get("timestamp")
    if timestamp is not None:
        entry["timestamp"] = timestamp

    # Message content — extract readable text
    message = rec.get("message")
    if isinstance(message, dict):
        role = message.get("role")
        if role is not None:
            entry["role"] = role
    entry["text"] = _extract_message_text(rec)

    # Tool use result indicator
    if "toolUseResult" in rec:
        entry["has_tool_result"] = True

    return entry


# ---------------------------------------------------------------------------
# Context window retrieval
# ---------------------------------------------------------------------------


def _build_index_map(records: list[dict]) -> dict[int, int]:
    """Build a lookup from _line_index to list position.

    Args:
        records: Full transcript records from ``_load_transcript_duckdb``.

    Returns:
        Dict mapping each record's ``_line_index`` to its position in ``records``.
    """
    return {int(rec["_line_index"]): pos for pos, rec in enumerate(records) if "_line_index" in rec}


def _get_context_window(
    records: list[dict], index_to_pos: dict[int, int], flagged_index: int, window: int = _DEFAULT_WINDOW
) -> dict | None:
    """Retrieve a window of nearby transcript entries around a flagged index.

    The flagged_index is the zero-based line index in the JSONL file
    (matching ``_line_index``).

    Args:
        records: Full transcript records loaded via DuckDB.
        index_to_pos: Pre-built lookup from ``_build_index_map``.
        flagged_index: The ``_line_index`` value of the flagged user message.
        window: Number of entries to retrieve before and after the flagged
            message.

    Returns:
        Dict with flagged_index, user_message text, and nearby_entries list.
        None if the flagged index is not found in the transcript.
    """
    pos = index_to_pos.get(flagged_index)
    if pos is None:
        print(f"  Warning: line index {flagged_index} not found in transcript", file=sys.stderr)
        return None

    # Compute window bounds
    start = max(0, pos - window)
    end = min(len(records), pos + window + 1)

    nearby: list[dict] = []
    for i in range(start, end):
        entry = _record_to_entry(records[i])
        entry["is_flagged"] = i == pos
        nearby.append(entry)

    return {
        "flagged_index": flagged_index,
        "user_message": _extract_message_text(records[pos]),
        "nearby_entries": nearby,
    }


# ---------------------------------------------------------------------------
# Main retrieval
# ---------------------------------------------------------------------------


def retrieve_contexts(input_data: dict, session_override: str | None = None, window: int = _DEFAULT_WINDOW) -> dict:
    """Retrieve context windows for all flagged indexes.

    Args:
        input_data: Parsed input JSON with "source_file" and
            "flagged_indexes" keys.
        session_override: Optional session file path override.
        window: Number of entries before and after each flagged message.

    Returns:
        Result dict with "session_file" and "contexts" keys.
    """
    source_file = session_override or input_data.get("source_file", "")
    flagged_indexes: list[int] = input_data.get("flagged_indexes", [])

    if not source_file:
        raise ValueError("no source_file specified in input or via --session-file")

    session_path = Path(source_file)
    if not session_path.exists():
        raise FileNotFoundError(f"session file not found: {session_path}")

    if not flagged_indexes:
        print("No flagged indexes in input.", file=sys.stderr)
        return {"session_file": source_file, "contexts": []}

    print(f"Loading transcript from {session_path.name} via DuckDB...", file=sys.stderr)
    records = _load_transcript_duckdb(session_path)
    print(f"  Loaded {len(records)} records.", file=sys.stderr)

    index_to_pos = _build_index_map(records)

    print(
        f"Retrieving context windows (window={window}) for {len(flagged_indexes)} flagged index(es)...", file=sys.stderr
    )
    contexts: list[dict] = []
    for idx in flagged_indexes:
        ctx = _get_context_window(records, index_to_pos, idx, window=window)
        if ctx is not None:
            contexts.append(ctx)
            print(f"  Index {idx}: retrieved {len(ctx['nearby_entries'])} nearby entries", file=sys.stderr)

    return {"session_file": source_file, "contexts": contexts}


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Retrieve context windows around flagged user messages from a session transcript."""
    parser = argparse.ArgumentParser(
        description=(
            "Retrieve nearby transcript context for flagged user messages. "
            "This is a helper tool for agent-driven candidate selection — "
            "it retrieves raw context, not scores or summaries."
        )
    )
    parser.add_argument(
        "--flagged-file", required=True, help="JSON file with flagged message data (produced by reaction-detector)"
    )
    parser.add_argument(
        "--session-file", default=None, help="Override session JSONL path (takes precedence over source_file in input)"
    )
    parser.add_argument(
        "--window",
        type=int,
        default=_DEFAULT_WINDOW,
        help=f"Number of entries before and after each flagged message (default: {_DEFAULT_WINDOW})",
    )
    args = parser.parse_args()

    try:
        input_data = _load_flagged_duckdb(Path(args.flagged_file))
        result = retrieve_contexts(input_data, session_override=args.session_file, window=args.window)
    except (ValueError, FileNotFoundError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    json.dump(result, sys.stdout, ensure_ascii=False, indent=2, default=str)
    print()  # trailing newline


if __name__ == "__main__":
    main()

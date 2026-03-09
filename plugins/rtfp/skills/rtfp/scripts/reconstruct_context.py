#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "duckdb>=1.0.0",
# ]
# ///
"""Retrieve context windows around flagged user messages from a session transcript.

Stage 3 helper tool for the RTFP pipeline. This script is a RETRIEVAL TOOL,
not a decision-maker. It accepts a session JSONL path and one or more message
indexes, uses DuckDB to load the session data, and returns a window of nearby
transcript entries for each flagged index so the calling agent can inspect the
surrounding context and make its own judgments about winner/runner-up selection
and task summary.

Input (stdin JSON or --flagged-file)::

    {"source_file": "/path/to/session.jsonl", "flagged_indexes": [12, 45, 78]}

Output (stdout, JSON)::

    {
        "session_file": "/path/to/session.jsonl",
        "contexts": [{"flagged_index": 12, "user_message": "...", "nearby_entries": [...]}],
    }

Usage::

    reconstruct_context.py --flagged-file /tmp/flagged.json
    reconstruct_context.py --flagged-file /tmp/flagged.json --session-file /path/to/session.jsonl
    reconstruct_context.py --flagged-file /tmp/flagged.json --window 15
    cat flagged.json | reconstruct_context.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

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

    con = duckdb.connect(":memory:")
    # read_ndjson_auto reads newline-delimited JSON; maximum_object_size
    # handles large assistant messages.  Use parameterized query to avoid
    # S608 (SQL injection) lint warning.
    query = """
        SELECT *, row_number() OVER () - 1 AS _line_index
        FROM read_ndjson_auto($1, maximum_object_size=10485760)
    """
    try:
        result = con.execute(query, [str(session_path)]).fetchall()
        columns = [desc[0] for desc in con.description]
    finally:
        con.close()

    records: list[dict] = []
    for row in result:
        rec = dict(zip(columns, row, strict=False))
        records.append(rec)
    return records


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
        content = message.get("content")
        entry["text"] = _extract_text(content)
    elif isinstance(message, str):
        entry["text"] = message

    # Tool use result indicator
    if "toolUseResult" in rec:
        entry["has_tool_result"] = True

    return entry


# ---------------------------------------------------------------------------
# Context window retrieval
# ---------------------------------------------------------------------------


def _get_context_window(records: list[dict], flagged_index: int, window: int = _DEFAULT_WINDOW) -> dict | None:
    """Retrieve a window of nearby transcript entries around a flagged index.

    The flagged_index is the zero-based line index in the JSONL file
    (matching ``_line_index``).

    Args:
        records: Full transcript records loaded via DuckDB.
        flagged_index: The ``_line_index`` value of the flagged user message.
        window: Number of entries to retrieve before and after the flagged
            message.

    Returns:
        Dict with flagged_index, user_message text, and nearby_entries list.
        None if the flagged index is not found in the transcript.
    """
    # Build a lookup from _line_index to position in the records list
    index_to_pos: dict[int, int] = {}
    for pos, rec in enumerate(records):
        line_idx = rec.get("_line_index")
        if line_idx is not None:
            index_to_pos[int(line_idx)] = pos

    pos = index_to_pos.get(flagged_index)
    if pos is None:
        print(f"  Warning: line index {flagged_index} not found in transcript", file=sys.stderr)
        return None

    # Extract user message text
    flagged_rec = records[pos]
    message = flagged_rec.get("message")
    user_text = ""
    if isinstance(message, dict):
        user_text = _extract_text(message.get("content"))
    elif isinstance(message, str):
        user_text = message

    # Compute window bounds
    start = max(0, pos - window)
    end = min(len(records), pos + window + 1)

    nearby: list[dict] = []
    for i in range(start, end):
        entry = _record_to_entry(records[i])
        entry["is_flagged"] = i == pos
        nearby.append(entry)

    return {"flagged_index": flagged_index, "user_message": user_text, "nearby_entries": nearby}


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
        print("Error: no source_file specified in input or via --session-file", file=sys.stderr)
        sys.exit(1)

    session_path = Path(source_file)
    if not session_path.exists():
        print(f"Error: session file not found: {session_path}", file=sys.stderr)
        sys.exit(1)

    if not flagged_indexes:
        print("No flagged indexes in input.", file=sys.stderr)
        return {"session_file": source_file, "contexts": []}

    print(f"Loading transcript from {session_path.name} via DuckDB...", file=sys.stderr)
    records = _load_transcript_duckdb(session_path)
    print(f"  Loaded {len(records)} records.", file=sys.stderr)

    print(
        f"Retrieving context windows (window={window}) for {len(flagged_indexes)} flagged index(es)...", file=sys.stderr
    )
    contexts: list[dict] = []
    for idx in flagged_indexes:
        ctx = _get_context_window(records, idx, window=window)
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
        "--flagged-file", default=None, help="JSON file with flagged message data (default: read from stdin)"
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

    if args.flagged_file is not None:
        flagged_path = Path(args.flagged_file)
        if not flagged_path.exists():
            print(f"Error: flagged file not found: {flagged_path}", file=sys.stderr)
            sys.exit(1)
        with flagged_path.open(encoding="utf-8") as fh:
            input_data = json.load(fh)
    else:
        input_data = json.load(sys.stdin)

    if not isinstance(input_data, dict):
        print("Error: input must be a JSON object with 'source_file' and 'flagged_indexes' keys", file=sys.stderr)
        sys.exit(1)

    result = retrieve_contexts(input_data, session_override=args.session_file, window=args.window)

    json.dump(result, sys.stdout, ensure_ascii=False, indent=2, default=str)
    print()  # trailing newline


if __name__ == "__main__":
    main()

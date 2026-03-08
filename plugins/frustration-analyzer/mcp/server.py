#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = [
#     "fastmcp>=3.0.0rc1,<4",
#     "duckdb>=0.10.0",
#     "pandas>=2.0.0",
# ]
# ///
"""Frustration Analyzer MCP Server.

Extracts user messages from Claude Code session transcripts for caller-side
classification, indexes caller-classified insults into DuckDB, and provides
query/reporting tools.

Tools:
    scan_transcripts - Extract raw user messages from JSONL files for caller classification
    index_insult - Store a caller-classified insult with ratings and scenario context
    list_insults - Query indexed insults with optional filters
    get_scenario - Get full scenario context for a specific insult
    top_insults - Return top N insults sorted by any rating dimension
    generate_social_post - Generate social media content for an insult
    sanitize_text - Standalone PII sanitizer
"""

from __future__ import annotations

import asyncio
import json
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
_DEFAULT_DB_DIR: str = "~/.local/share/frustration-analyzer"
_DEFAULT_DB_NAME: str = "insults.duckdb"
_MIN_TOKEN_LENGTH: int = 20
_MIN_RATING: int = 1
_MAX_RATING: int = 5

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

# Valid insult categories accepted by index_insult
_VALID_CATEGORIES: set[str] = {
    "profanity_at_ai",
    "model_comparison",
    "competence_challenge",
    "intelligence_insult",
    "repeat_failure",
    "sarcasm",
    "dismissive_command",
    "technical_putdown",
    "general_frustration",
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
# Schema SQL
# ---------------------------------------------------------------------------

_SCHEMA_SQL: str = """
CREATE TABLE IF NOT EXISTS insults (
    insult_id INTEGER PRIMARY KEY,
    session_id VARCHAR NOT NULL,
    timestamp VARCHAR NOT NULL,
    message_uuid VARCHAR,
    insult_text VARCHAR NOT NULL,
    category VARCHAR NOT NULL,
    matched_pattern VARCHAR,
    model VARCHAR,
    git_branch VARCHAR,
    session_slug VARCHAR,
    is_subagent BOOLEAN DEFAULT FALSE,
    agent_name VARCHAR
);

CREATE TABLE IF NOT EXISTS insult_ratings (
    rating_id INTEGER PRIMARY KEY,
    insult_id INTEGER NOT NULL REFERENCES insults(insult_id),
    creativity TINYINT NOT NULL CHECK (creativity BETWEEN 1 AND 5),
    accuracy TINYINT NOT NULL CHECK (accuracy BETWEEN 1 AND 5),
    severity TINYINT NOT NULL CHECK (severity BETWEEN 1 AND 5),
    humor TINYINT NOT NULL CHECK (humor BETWEEN 1 AND 5),
    composite DECIMAL(3,2),
    rated_by VARCHAR NOT NULL DEFAULT 'auto',
    rated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS insult_scenarios (
    scenario_id INTEGER PRIMARY KEY,
    insult_id INTEGER NOT NULL REFERENCES insults(insult_id),
    preceding_messages JSON NOT NULL,
    context_window_n TINYINT NOT NULL DEFAULT 5,
    summary VARCHAR,
    precipitating_failure VARCHAR,
    had_prior_correction BOOLEAN DEFAULT FALSE,
    compact_boundary_in_window BOOLEAN DEFAULT FALSE,
    tool_sequence JSON
);

CREATE VIEW IF NOT EXISTS insult_leaderboard AS
SELECT i.insult_id, i.insult_text, i.category, i.session_slug,
       r.creativity, r.accuracy, r.severity, r.humor, r.composite,
       s.precipitating_failure, s.summary
FROM insults i
JOIN insult_ratings r ON i.insult_id = r.insult_id
LEFT JOIN insult_scenarios s ON i.insult_id = s.insult_id
ORDER BY r.composite DESC;

CREATE VIEW IF NOT EXISTS category_distribution AS
SELECT i.category, COUNT(*) AS count,
       AVG(r.severity) AS avg_severity,
       AVG(r.composite) AS avg_composite
FROM insults i
JOIN insult_ratings r ON i.insult_id = r.insult_id
GROUP BY i.category
ORDER BY count DESC;

CREATE VIEW IF NOT EXISTS failure_triggers AS
SELECT s.precipitating_failure,
       COUNT(*) AS insult_count,
       AVG(r.severity) AS avg_severity,
       AVG(r.composite) AS avg_composite,
       MAX(r.composite) AS best_insult_score
FROM insult_scenarios s
JOIN insult_ratings r ON s.insult_id = r.insult_id
GROUP BY s.precipitating_failure
ORDER BY avg_severity DESC;

CREATE VIEW IF NOT EXISTS escalation_patterns AS
SELECT i.insult_id, i.insult_text, i.category, s.had_prior_correction,
       s.precipitating_failure, r.severity
FROM insults i
JOIN insult_ratings r ON i.insult_id = r.insult_id
JOIN insult_scenarios s ON i.insult_id = s.insult_id
WHERE s.had_prior_correction = TRUE
ORDER BY r.severity DESC;
"""

# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

mcp = FastMCP("frustration-analyzer", mask_error_details=False)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _default_db_path() -> str:
    """Return the default DuckDB file path, creating directories as needed.

    Returns:
        Absolute path to the default insults.duckdb file.
    """
    db_dir = pathlib.Path(_DEFAULT_DB_DIR).expanduser()
    db_dir.mkdir(parents=True, exist_ok=True)
    return str(db_dir / _DEFAULT_DB_NAME)


def _ensure_schema(conn: duckdb.DuckDBPyConnection) -> None:
    """Create tables and views if they do not exist.

    Args:
        conn: An open DuckDB connection.
    """
    conn.execute(_SCHEMA_SQL)


def _get_db(db_path: str) -> duckdb.DuckDBPyConnection:
    """Open a DuckDB connection and ensure schema exists.

    Args:
        db_path: Path to the .duckdb file. Empty string uses default.

    Returns:
        An open DuckDB connection with schema initialized.
    """
    resolved = db_path or _default_db_path()
    conn = duckdb.connect(resolved)
    _ensure_schema(conn)
    return conn


def _read_jsonl(file_path: str) -> list[dict[str, Any]]:
    """Read a JSONL file and return a list of parsed records.

    Args:
        file_path: Path to a single JSONL file.

    Returns:
        List of dicts, one per line.
    """
    records: list[dict[str, Any]] = []
    with pathlib.Path(file_path).open(encoding="utf-8") as fh:
        records.extend(json.loads(stripped) for line in fh if (stripped := line.strip()))
    return records


def _resolve_glob(glob_path: str) -> list[str]:
    """Resolve a glob pattern to a sorted list of file paths.

    Args:
        glob_path: Glob pattern (e.g. ``~/.claude/projects/**/*.jsonl``).

    Returns:
        Sorted list of matching absolute file path strings.
    """
    expanded = str(pathlib.Path(glob_path).expanduser()) if "~" in glob_path else glob_path
    parts = pathlib.PurePosixPath(expanded).parts
    base_parts: list[str] = []
    glob_chars = {"*", "?", "["}
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


def _extract_user_text(message: dict[str, Any]) -> str:
    """Extract plain text from a user message content field.

    Handles both string content and list-of-blocks content formats.

    Args:
        message: The ``message`` dict from a ``user`` record.

    Returns:
        Extracted text, or empty string if no text found.
    """
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    text = block.get("text", "")
                    if isinstance(text, str):
                        parts.append(text)
            elif isinstance(block, str):
                parts.append(block)
        return " ".join(parts)
    return ""


def _extract_model_from_records(records: list[dict[str, Any]], insult_index: int) -> str | None:
    """Find the model name from the most recent assistant message before the insult.

    Args:
        records: All JSONL records in the session.
        insult_index: Index of the insult record in the list.

    Returns:
        Model name string or None if not found.
    """
    for i in range(insult_index - 1, -1, -1):
        record = records[i]
        if record.get("type") == "assistant":
            message = record.get("message")
            if isinstance(message, dict):
                model = message.get("model")
                if isinstance(model, str):
                    return model
    return None


def _extract_tool_sequence(records: list[dict[str, Any]], start: int, end: int) -> list[str]:
    """Extract tool names from assistant messages in a record range.

    Args:
        records: All JSONL records.
        start: Start index (inclusive).
        end: End index (exclusive).

    Returns:
        Ordered list of tool names used.
    """
    tools: list[str] = []
    for i in range(start, min(end, len(records))):
        record = records[i]
        if record.get("type") != "assistant":
            continue
        message = record.get("message")
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                name = block.get("name")
                if isinstance(name, str):
                    tools.append(name)
    return tools


def _extract_assistant_entry(message: dict[str, Any], entry: dict[str, str]) -> None:
    """Extract text and tool info from an assistant message into entry dict.

    Args:
        message: The assistant message dict.
        entry: Mutable entry dict to populate with text and tool_name.
    """
    content = message.get("content")
    if not isinstance(content, list):
        return
    text_parts: list[str] = []
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "text":
            t = block.get("text", "")
            if isinstance(t, str):
                text_parts.append(t)
        elif block.get("type") == "tool_use":
            entry["tool_name"] = str(block.get("name", "unknown"))
    entry["text"] = " ".join(text_parts)


def _extract_scenario(records: list[dict[str, Any]], insult_index: int, context_window: int) -> dict[str, Any]:
    """Extract the scenario context around an insult.

    Args:
        records: All JSONL records in the session.
        insult_index: Index of the insult record.
        context_window: Number of preceding messages to capture.

    Returns:
        Dict with preceding_messages, compact_boundary_in_window,
        and tool_sequence.
    """
    start = max(0, insult_index - context_window)
    preceding: list[dict[str, Any]] = []
    compact_boundary_in_window = False

    for i in range(start, insult_index):
        record = records[i]
        record_type = record.get("type", "")

        if record_type == "system" and record.get("subtype") == "compact_boundary":
            compact_boundary_in_window = True
            continue

        entry: dict[str, str] = {
            "role": record_type,
            "timestamp": str(record.get("timestamp", "")),
            "uuid": str(record.get("uuid", "")),
        }

        if record_type == "user" and not record.get("toolUseResult"):
            message = record.get("message")
            if isinstance(message, dict):
                text = _extract_user_text(message)
                entry["text"] = text
        elif record_type == "assistant":
            message = record.get("message")
            if isinstance(message, dict):
                _extract_assistant_entry(message, entry)
        else:
            continue

        preceding.append(entry)

    tool_sequence = _extract_tool_sequence(records, start, insult_index)

    return {
        "preceding_messages": preceding,
        "compact_boundary_in_window": compact_boundary_in_window,
        "tool_sequence": tool_sequence,
    }


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


def _next_id(conn: duckdb.DuckDBPyConnection, table: str, id_column: str) -> int:
    """Get the next auto-increment ID for a table.

    Args:
        conn: Open DuckDB connection.
        table: Table name.
        id_column: Primary key column name.

    Returns:
        Next integer ID value.
    """
    row = conn.execute(f"SELECT COALESCE(MAX({id_column}), 0) FROM {table}").fetchone()  # noqa: S608
    return (row[0] if row else 0) + 1


def _index_insult(
    conn: duckdb.DuckDBPyConnection,
    record: dict[str, Any],
    records: list[dict[str, Any]],
    idx: int,
    text: str,
    assessment: dict[str, Any],
    context_window: int,
    session_id_from_file: str,
) -> bool:
    """Insert a single insult with its rating and scenario into the database.

    Uses LLM-provided classification and ratings from the assessment dict
    instead of regex-based heuristics.

    Args:
        conn: Open DuckDB connection.
        record: The JSONL record containing the insult.
        records: All JSONL records in the session.
        idx: Index of the insult record in records.
        text: The insult text.
        assessment: LLM classification dict with category, severity,
            creativity, humor, accuracy, matched_text, had_prior_correction.
        context_window: Number of preceding messages to capture.
        session_id_from_file: Fallback session ID from filename.

    Returns:
        True if a new insult was indexed, False if duplicate.
    """
    session_id = str(record.get("sessionId", session_id_from_file))
    message_uuid = str(record.get("uuid", ""))

    existing = conn.execute(
        "SELECT insult_id FROM insults WHERE session_id = ? AND message_uuid = ?", [session_id, message_uuid]
    ).fetchone()
    if existing:
        return False

    insult_id = _next_id(conn, "insults", "insult_id")
    category: str = assessment["category"]
    matched_text: str = assessment.get("matched_text", "")

    conn.execute(
        """INSERT INTO insults
        (insult_id, session_id, timestamp, message_uuid, insult_text,
         category, matched_pattern, model, git_branch, session_slug,
         is_subagent, agent_name)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            insult_id,
            session_id,
            str(record.get("timestamp", "")),
            message_uuid,
            text,
            category,
            matched_text,
            _extract_model_from_records(records, idx),
            record.get("gitBranch"),
            record.get("slug"),
            bool(record.get("isSidechain")),
            record.get("agentName"),
        ],
    )

    creativity = max(_MIN_RATING, min(_MAX_RATING, int(assessment.get("creativity", 2))))
    accuracy = max(_MIN_RATING, min(_MAX_RATING, int(assessment.get("accuracy", 2))))
    severity = max(_MIN_RATING, min(_MAX_RATING, int(assessment.get("severity", 2))))
    humor = max(_MIN_RATING, min(_MAX_RATING, int(assessment.get("humor", 2))))
    composite = round((creativity + accuracy + severity + humor) / 4, 2)

    conn.execute(
        """INSERT INTO insult_ratings
        (rating_id, insult_id, creativity, accuracy, severity, humor, composite, rated_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'llm')""",
        [_next_id(conn, "insult_ratings", "rating_id"), insult_id, creativity, accuracy, severity, humor, composite],
    )

    scenario = _extract_scenario(records, idx, context_window)
    had_prior_correction = bool(assessment.get("had_prior_correction"))
    conn.execute(
        """INSERT INTO insult_scenarios
        (scenario_id, insult_id, preceding_messages, context_window_n,
         had_prior_correction, compact_boundary_in_window, tool_sequence)
        VALUES (?, ?, ?, ?, ?, ?, ?)""",
        [
            _next_id(conn, "insult_scenarios", "scenario_id"),
            insult_id,
            json.dumps(scenario["preceding_messages"]),
            context_window,
            had_prior_correction,
            scenario["compact_boundary_in_window"],
            json.dumps(scenario["tool_sequence"]),
        ],
    )

    return True


def _scan_transcripts_impl(glob_path: str, context_window: int, offset: int, limit: int) -> dict[str, Any]:
    """Extract user messages from JSONL transcripts for caller-side classification.

    Walks matching JSONL files, extracts user messages with surrounding
    context, and returns them for the MCP caller to classify.

    Args:
        glob_path: Glob pattern pointing to JSONL transcript files.
        context_window: Number of preceding messages to capture per message.
        offset: Number of messages to skip (pagination).
        limit: Maximum number of messages to return.

    Returns:
        Dict with messages list, total count, offset, limit, and files_scanned.

    Raises:
        ToolError: If no files match the glob pattern.
    """
    files = _resolve_glob(glob_path)
    if not files:
        raise ToolError(f"No files matched glob pattern: {glob_path}")

    all_messages: list[dict[str, Any]] = []

    for file_path in files:
        records = _read_jsonl(file_path)
        for idx, record in enumerate(records):
            if record.get("type") != "user" or record.get("toolUseResult"):
                continue
            message = record.get("message")
            if not isinstance(message, dict):
                continue
            text = _extract_user_text(message)
            if not text:
                continue

            scenario = _extract_scenario(records, idx, context_window)
            all_messages.append({
                "file": file_path,
                "line_index": idx,
                "text": text,
                "context": scenario["preceding_messages"],
            })

    total = len(all_messages)
    page = all_messages[offset : offset + limit]

    return {"messages": page, "total": total, "offset": offset, "limit": limit, "files_scanned": len(files)}


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------


@mcp.tool(annotations=_READONLY_ANNOTATIONS)
async def scan_transcripts(
    glob_path: str, context_window: int = _DEFAULT_CONTEXT_WINDOW, db_path: str = "", offset: int = 0, limit: int = 100
) -> dict[str, Any]:
    """Extract raw user messages from JSONL transcript files for classification.

    Returns a paginated list of user messages with surrounding context.
    The caller (Claude) is responsible for classifying each message and
    calling ``index_insult`` for those it decides to index.

    No classification or external API calls are performed. No data is
    written to DuckDB.

    Args:
        glob_path: Glob pattern pointing to JSONL transcript files,
            e.g. ``~/.claude/projects/-my-project/*.jsonl``
        context_window: Number of preceding messages to include as
            context for each user message. Default 5.
        db_path: Unused, kept for call-site compatibility.
        offset: Number of messages to skip for pagination. Default 0.
        limit: Maximum number of messages to return. Default 100.

    Returns:
        Dict with messages (list of {file, line_index, text, context}),
        total message count, offset, limit, and files_scanned.
    """
    return await asyncio.to_thread(_scan_transcripts_impl, glob_path, context_window, offset, limit)


@mcp.tool(annotations=_WRITE_ANNOTATIONS)
async def index_insult(
    file: str,
    line_index: int,
    text: str,
    category: str,
    severity: int = 2,
    creativity: int = 2,
    humor: int = 2,
    accuracy: int = 2,
    had_prior_correction: bool = False,
    matched_text: str = "",
    reasoning: str = "",
    context_window: int = _DEFAULT_CONTEXT_WINDOW,
    db_path: str = "",
) -> dict[str, Any]:
    """Store a caller-classified insult with ratings and scenario context.

    The caller (Claude) decides which messages are insults and provides
    classification details. This tool writes the insult, its ratings,
    and the surrounding scenario context to DuckDB.

    Args:
        file: Source JSONL file path.
        line_index: Position of the insult record in the JSONL file.
        text: The insult text.
        category: One of: profanity_at_ai, model_comparison,
            competence_challenge, intelligence_insult, repeat_failure,
            sarcasm, dismissive_command, technical_putdown,
            general_frustration.
        severity: Severity rating 1-5.
        creativity: Creativity rating 1-5.
        humor: Humor rating 1-5.
        accuracy: Accuracy rating 1-5.
        had_prior_correction: Whether the AI was already corrected before.
        matched_text: The specific phrase that is the insult.
        reasoning: Free-text reasoning for the classification.
        context_window: Number of preceding messages to capture.
        db_path: Path to DuckDB file. Empty string uses default.

    Returns:
        Dict with indexed (bool), insult_id (int), and db_path (str).

    Raises:
        ToolError: If category is invalid, ratings are out of range,
            or the file/line_index cannot be read.
    """
    if category not in _VALID_CATEGORIES:
        raise ToolError(f"category must be one of {sorted(_VALID_CATEGORIES)}, got: {category!r}")
    for name, value in [("severity", severity), ("creativity", creativity), ("humor", humor), ("accuracy", accuracy)]:
        if not (_MIN_RATING <= value <= _MAX_RATING):
            raise ToolError(f"{name} must be between {_MIN_RATING} and {_MAX_RATING}, got: {value}")

    def _do_index() -> dict[str, Any]:
        records = _read_jsonl(file)
        if line_index < 0 or line_index >= len(records):
            raise ToolError(f"line_index {line_index} out of range for {file} (has {len(records)} records)")
        record = records[line_index]
        assessment: dict[str, Any] = {
            "category": category,
            "severity": severity,
            "creativity": creativity,
            "humor": humor,
            "accuracy": accuracy,
            "had_prior_correction": had_prior_correction,
            "matched_text": matched_text,
            "reasoning": reasoning,
        }
        conn = _get_db(db_path)
        resolved_db_path = db_path or _default_db_path()
        was_new = _index_insult(
            conn,
            record,
            records,
            line_index,
            text,
            assessment,
            context_window,
            file.rsplit("/", maxsplit=1)[-1].removesuffix(".jsonl"),
        )
        conn.close()
        insult_id: int | None = None
        if was_new:
            conn2 = _get_db(db_path)
            row = conn2.execute("SELECT MAX(insult_id) FROM insults").fetchone()
            conn2.close()
            insult_id = row[0] if row else None
        return {"indexed": was_new, "insult_id": insult_id, "db_path": resolved_db_path}

    return await asyncio.to_thread(_do_index)


@mcp.tool(annotations=_READONLY_ANNOTATIONS)
async def list_insults(
    db_path: str = "", category: str = "", min_composite: float = 0.0, limit: int = 20, offset: int = 0
) -> list[dict[str, Any]]:
    """Query indexed insults from the database with optional filters.

    Returns rows from the insult_leaderboard view, which joins
    insults, ratings, and scenarios.

    Args:
        db_path: Path to DuckDB file. Empty string uses default.
        category: Filter by insult category slug. Empty for all.
        min_composite: Minimum composite score threshold.
        limit: Maximum number of results to return.
        offset: Number of results to skip for pagination.

    Returns:
        List of dicts with insult details, ratings, and scenario info.
    """

    def _query() -> list[dict[str, Any]]:
        conn = _get_db(db_path)
        conditions: list[str] = []
        params: list[Any] = []

        if category:
            conditions.append("category = ?")
            params.append(category)
        if min_composite > 0:
            conditions.append("composite >= ?")
            params.append(min_composite)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"SELECT * FROM insult_leaderboard {where} LIMIT ? OFFSET ?"  # noqa: S608
        params.extend([limit, offset])

        result = conn.execute(sql, params).fetchdf()
        conn.close()
        return result.to_dict(orient="records")

    return await asyncio.to_thread(_query)


@mcp.tool(annotations=_READONLY_ANNOTATIONS)
async def get_scenario(insult_id: int, db_path: str = "") -> dict[str, Any]:
    """Get the full scenario context for a specific insult.

    Includes preceding messages, summary, precipitating failure,
    and tool sequence leading up to the insult.

    Args:
        insult_id: The ID of the insult to retrieve the scenario for.
        db_path: Path to DuckDB file. Empty string uses default.

    Returns:
        Dict with insult details and full scenario including
        preceding_messages JSON.

    Raises:
        ToolError: If the insult_id is not found.
    """

    def _query() -> dict[str, Any]:
        conn = _get_db(db_path)
        row = conn.execute(
            """SELECT i.insult_id, i.insult_text, i.category, i.session_id,
                      i.timestamp, i.model, i.session_slug,
                      s.preceding_messages, s.context_window_n,
                      s.summary, s.precipitating_failure,
                      s.had_prior_correction, s.compact_boundary_in_window,
                      s.tool_sequence,
                      r.creativity, r.accuracy, r.severity, r.humor, r.composite
               FROM insults i
               LEFT JOIN insult_scenarios s ON i.insult_id = s.insult_id
               LEFT JOIN insult_ratings r ON i.insult_id = r.insult_id
               WHERE i.insult_id = ?""",
            [insult_id],
        ).fetchone()
        conn.close()

        if not row:
            raise ToolError(f"Insult ID {insult_id} not found")

        columns = [
            "insult_id",
            "insult_text",
            "category",
            "session_id",
            "timestamp",
            "model",
            "session_slug",
            "preceding_messages",
            "context_window_n",
            "summary",
            "precipitating_failure",
            "had_prior_correction",
            "compact_boundary_in_window",
            "tool_sequence",
            "creativity",
            "accuracy",
            "severity",
            "humor",
            "composite",
        ]
        result = dict(zip(columns, row, strict=False))

        # Parse JSON fields
        for json_field in ("preceding_messages", "tool_sequence"):
            val = result.get(json_field)
            if isinstance(val, str):
                result[json_field] = json.loads(val)

        return result

    return await asyncio.to_thread(_query)


@mcp.tool(annotations=_READONLY_ANNOTATIONS)
async def top_insults(n: int = 10, sort_by: str = "composite", db_path: str = "") -> list[dict[str, Any]]:
    """Return the top N insults sorted by a rating dimension.

    Args:
        n: Number of top insults to return.
        sort_by: Rating dimension to sort by. One of: composite,
            humor, creativity, severity, accuracy.
        db_path: Path to DuckDB file. Empty string uses default.

    Returns:
        List of dicts with insult details and ratings, sorted by
        the specified dimension descending.

    Raises:
        ToolError: If sort_by is not a valid dimension.
    """
    valid_sorts = {"composite", "humor", "creativity", "severity", "accuracy"}
    if sort_by not in valid_sorts:
        raise ToolError(f"sort_by must be one of {valid_sorts}, got: {sort_by}")

    def _query() -> list[dict[str, Any]]:
        conn = _get_db(db_path)
        # sort_by is validated against valid_sorts whitelist above
        sql = (
            f"SELECT i.insult_id, i.insult_text, i.category, i.session_slug,"  # noqa: S608
            f" r.creativity, r.accuracy, r.severity, r.humor, r.composite,"
            f" s.summary, s.precipitating_failure"
            f" FROM insults i"
            f" JOIN insult_ratings r ON i.insult_id = r.insult_id"
            f" LEFT JOIN insult_scenarios s ON i.insult_id = s.insult_id"
            f" ORDER BY r.{sort_by} DESC"
            f" LIMIT ?"
        )
        result = conn.execute(sql, [n]).fetchdf()
        conn.close()
        return result.to_dict(orient="records")

    return await asyncio.to_thread(_query)


def _fetch_insult_for_post(insult_id: int, db_path: str) -> tuple[Any, ...]:
    """Fetch insult data needed for social post generation.

    Args:
        insult_id: The insult to fetch.
        db_path: Path to DuckDB file.

    Returns:
        Tuple of (id, text, category, model, creativity, accuracy,
        severity, humor, summary).

    Raises:
        ToolError: If insult_id not found.
    """
    conn = _get_db(db_path)
    row = conn.execute(
        """SELECT i.insult_id, i.insult_text, i.category, i.model,
                  r.creativity, r.accuracy, r.severity, r.humor,
                  s.summary
           FROM insults i
           JOIN insult_ratings r ON i.insult_id = r.insult_id
           LEFT JOIN insult_scenarios s ON i.insult_id = s.insult_id
           WHERE i.insult_id = ?""",
        [insult_id],
    ).fetchone()
    conn.close()
    if not row:
        raise ToolError(f"Insult ID {insult_id} not found")
    return row


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


@mcp.tool(annotations=_WRITE_ANNOTATIONS)
async def generate_social_post(insult_id: int, mode: str = "sanitized", db_path: str = "") -> dict[str, Any]:
    """Generate social media content for a specific insult.

    Creates a formatted post suitable for Twitter/X with the insult,
    its ratings, scenario context, and relevant hashtags.

    Args:
        insult_id: The ID of the insult to generate a post for.
        mode: Either ``raw`` (verbatim text) or ``sanitized`` (PII stripped).
        db_path: Path to DuckDB file. Empty string uses default.

    Returns:
        Dict with post_text, raw_insult, sanitized_insult, char_count,
        and hashtags.

    Raises:
        ToolError: If the insult is not found or mode is invalid.
    """
    if mode not in {"raw", "sanitized"}:
        raise ToolError(f"mode must be 'raw' or 'sanitized', got: {mode}")

    def _generate() -> dict[str, Any]:
        row = _fetch_insult_for_post(insult_id, db_path)
        (id_, insult_text, category, model, creativity, accuracy, severity, humor, summary) = row

        sanitized_result = _sanitize_text_impl(insult_text)
        sanitized_insult = sanitized_result["sanitized"]
        display_text = sanitized_insult if mode == "sanitized" else insult_text

        hashtags = _build_hashtags(category, model)
        post_text = (
            f"\U0001f525 AI Frustration Report\n"
            f"\n"
            f"The situation: {summary or 'Unknown context'}\n"
            f"\n"
            f'What the user said: "{display_text}"\n'
            f"\n"
            f"Category: {_CATEGORY_DISPLAY.get(category, category)}\n"
            f"Creativity: {creativity}/5 | Humor: {humor}/5\n"
            f"Accuracy: {accuracy}/5 | Severity: {severity}/5\n"
            f"\n"
            f"{' '.join(hashtags)}"
        )

        return {
            "insult_id": id_,
            "mode": mode,
            "post_text": post_text,
            "raw_insult": insult_text,
            "sanitized_insult": sanitized_insult,
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

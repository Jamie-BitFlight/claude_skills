#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = [
#     "fastmcp>=3.0.0rc1,<4",
#     "duckdb>=0.10.0",
# ]
# ///
"""Frustration Analyzer MCP Server.

Detects user insults in Claude Code session transcripts, rates them
across four dimensions (creativity, accuracy, severity, humor),
extracts precipitating scenarios, and generates social media content.

Tools:
    scan_transcripts - Scan JSONL files, detect insults, rate and store in DuckDB
    list_insults - Query indexed insults with optional filters
    get_scenario - Get full scenario context for a specific insult
    top_insults - Return top N insults sorted by any rating dimension
    generate_social_post - Generate social media content for an insult
    sanitize_text - Standalone PII sanitizer
"""

from __future__ import annotations

import asyncio
import json
import pathlib
import re
from typing import Any

import duckdb
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_CONTEXT_WINDOW: int = 5
_DEFAULT_DB_DIR: str = "~/.local/share/frustration-analyzer"
_DEFAULT_DB_NAME: str = "insults.duckdb"
_MIN_PUNCTUATION_ESCALATION: int = 3
_MIN_TOKEN_LENGTH: int = 20

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
}

# ---------------------------------------------------------------------------
# Insult detection patterns (8 categories)
# ---------------------------------------------------------------------------

_INSULT_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "profanity_at_ai",
        re.compile(
            r"\b(?:you\s+)?(?:fucking|damn|goddamn|bloody)\s+(?:idiot|moron|fool|useless|stupid|dumb|piece\s+of\s+shit)\b"
            r"|\b(?:wtf|what\s+the\s+fuck|what\s+the\s+hell)\s+(?:are\s+you\s+doing|is\s+this|is\s+wrong\s+with\s+you)\b"
            r"|\b(?:fuck\s+(?:you|this|off)|go\s+to\s+hell|screw\s+you)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "model_comparison",
        re.compile(
            r"\b(?:you'?re|this\s+is|acting\s+like|sounds?\s+like|worse\s+than|dumber\s+than)\s+"
            r"(?:gpt[-\s]?[23]|haiku|gemini\s*(?:nano|flash)?|copilot|chatgpt|a\s+chatbot"
            r"|clippy|eliza|a\s+markov\s+chain|an?\s+intern)\b"
            r"|\b(?:gpt[-\s]?[23]|haiku|chatgpt)\s+(?:level|quality|tier|grade)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "competence_challenge",
        re.compile(
            r"\b(?:are\s+you\s+(?:stupid|dumb|deaf|blind|broken|brain\s*dead|incapable)"
            r"|can'?t\s+you\s+(?:read|understand|follow|listen|think|do\s+anything)"
            r"|do\s+you\s+(?:even|not)\s+(?:understand|know|read|listen)"
            r"|how\s+(?:hard|difficult)\s+(?:is\s+it|can\s+it\s+be))\b",
            re.IGNORECASE,
        ),
    ),
    (
        "intelligence_insult",
        re.compile(
            r"\b(?:you'?re\s+(?:useless|worthless|hopeless|pathetic|terrible|awful|garbage|trash"
            r"|incompetent|clueless|brain\s*dead|an?\s+idiot|a\s+moron|the\s+worst)"
            r"|this\s+(?:is\s+)?(?:garbage|trash|useless|pathetic|terrible|awful|horseshit|bullshit)"
            r"|absolute(?:ly)?\s+(?:useless|worthless|pathetic|terrible|garbage))\b",
            re.IGNORECASE,
        ),
    ),
    (
        "repeat_failure",
        re.compile(
            r"\b(?:(?:you\s+)?(?:STILL|AGAIN|ONCE\s+AGAIN|YET\s+AGAIN)\s+(?:got\s+it\s+wrong|broke|failed|messed|fucked)"
            r"|(?:how\s+many\s+times|for\s+the\s+(?:\w+\s+)?time)\b"
            r"|(?:every\s+(?:single\s+)?time\s+you)"
            r"|(?:wrong\s+)?again[!?]{2,}"
            r"|(?:STILL\s+(?:broken|wrong|failing|bugged)))\b",
            re.IGNORECASE,
        ),
    ),
    (
        "sarcasm",
        re.compile(
            r"\b(?:(?:great|good|nice|wonderful|brilliant|excellent|amazing|fantastic)\s+(?:job|work|going)"
            r"|(?:wow|congrats|congratulations|bravo|well\s+done|genius)\s*[,.]?\s*(?:you|that|now|it)"
            r"|(?:oh?\s+)?(?:how\s+)?(?:helpful|useful|productive)\s*(?:\.{3,}|/s)"
            r"|(?:real(?:ly)?\s+)?(?:helpful|useful|smart|intelligent)\s+(?:aren'?t\s+you|one|there)"
            r"|thanks?\s+for\s+(?:nothing|wasting|breaking|making\s+it\s+worse))\b",
            re.IGNORECASE,
        ),
    ),
    (
        "dismissive_command",
        re.compile(
            r"^(?:just\s+(?:stop|shut\s+up|quit|give\s+up)"
            r"|(?:shut\s+(?:up|the\s+fuck\s+up))"
            r"|(?:I'?(?:ll|m\s+going\s+to)\s+(?:do\s+it\s+myself|just\s+do\s+it\s+manually|use\s+\w+\s+instead))"
            r"|(?:forget\s+(?:it|you)|I\s+give\s+up\s+on\s+you|done\s+with\s+you))\b",
            re.IGNORECASE,
        ),
    ),
    (
        "technical_putdown",
        re.compile(
            r"\b(?:(?:you|this)\s+(?:is\s+)?(?:a\s+)?(?:hallucinating|confabulating|regressing|overfitting|underfitting)"
            r"|(?:your\s+(?:context\s+window|attention|memory|weights|training\s+data)\s+(?:is|must\s+be)\s+(?:broken|garbage|corrupted|empty|fried))"
            r"|(?:off[\s-]?by[\s-]?one\s+(?:brain|intelligence|model))"
            r"|(?:you\s+(?:have|got)\s+(?:the\s+)?(?:memory|attention\s+span)\s+of\s+(?:a\s+)?(?:goldfish|gnat|rock))"
            r"|(?:temperature\s*=?\s*(?:99|100|infinity|NaN)))\b",
            re.IGNORECASE,
        ),
    ),
]

# Kaizen soft-signal patterns for had_prior_correction detection
_FRUSTRATION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("correction", re.compile(r"\b(?:no[,.]?\s|don'?t|wrong|incorrect|stop|undo|revert)\b", re.IGNORECASE)),
    ("denial", re.compile(r"\b(?:that'?s not|i didn'?t|never|absolutely not)\b", re.IGNORECASE)),
    ("interrupt", re.compile(r"\b(?:wait|hold on|cancel|abort|forget it|nevermind)\b", re.IGNORECASE)),
    ("frustration", re.compile(r"\b(?:why did you|you keep|again\?|still wrong|broken)\b", re.IGNORECASE)),
]

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

# Technical terms for creativity scoring
_TECHNICAL_TERMS: re.Pattern[str] = re.compile(
    r"\b(?:claude|opus|sonnet|haiku|gpt|gemini|llm|transformer|attention|context\s+window"
    r"|token|embedding|gradient|backprop|neural|perceptron|epoch|batch|inference"
    r"|hallucin|confabulat|overfit|underfit|regression|latent|vector|matrix"
    r"|algorithm|compiler|parser|runtime|stack|heap|buffer|pointer|mutex"
    r"|deadlock|race\s+condition|segfault|null\s+pointer|memory\s+leak)\b",
    re.IGNORECASE,
)

# Metaphor indicators for creativity scoring
_METAPHOR_INDICATORS: re.Pattern[str] = re.compile(
    r"\b(?:like\s+a|as\s+a|of\s+a|reminds\s+me\s+of|equivalent\s+of)\b", re.IGNORECASE
)

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


def _heuristic_rate(insult_text: str, category: str) -> dict[str, Any]:
    """Rate an insult heuristically across four dimensions.

    Args:
        insult_text: The raw insult text.
        category: The detected insult category slug.

    Returns:
        Dict with keys: creativity, accuracy, severity, humor, composite.
    """
    # --- Creativity ---
    creativity_bases: dict[str, int] = {
        "technical_putdown": 4,
        "model_comparison": 3,
        "sarcasm": 3,
        "repeat_failure": 2,
        "competence_challenge": 2,
        "profanity_at_ai": 1,
        "intelligence_insult": 1,
        "dismissive_command": 1,
    }
    creativity = creativity_bases.get(category, 2)
    if _TECHNICAL_TERMS.search(insult_text):
        creativity += 1
    if _METAPHOR_INDICATORS.search(insult_text):
        creativity += 1
    creativity = min(creativity, 5)

    # --- Severity ---
    severity_bases: dict[str, int] = {
        "profanity_at_ai": 4,
        "intelligence_insult": 3,
        "repeat_failure": 3,
        "competence_challenge": 2,
        "sarcasm": 2,
        "dismissive_command": 2,
        "model_comparison": 2,
        "technical_putdown": 2,
    }
    severity = severity_bases.get(category, 2)
    exclamation_count = insult_text.count("!") + insult_text.count("?")
    if exclamation_count >= _MIN_PUNCTUATION_ESCALATION:
        severity += 1
    # ALL CAPS word longer than 3 characters
    if re.search(r"\b[A-Z]{4,}\b", insult_text):
        severity += 1
    severity = min(severity, 5)

    # --- Humor ---
    humor = 2
    if category in {"sarcasm", "technical_putdown"}:
        humor += 1
    # Technical metaphor detection
    if _METAPHOR_INDICATORS.search(insult_text) and _TECHNICAL_TERMS.search(insult_text):
        humor += 1
    humor = min(humor, 5)

    # --- Accuracy ---
    accuracy = 3 if category == "technical_putdown" else 2
    accuracy = min(accuracy, 5)

    # --- Composite ---
    composite = round((creativity + accuracy + severity + humor) / 4, 2)

    return {
        "creativity": creativity,
        "accuracy": accuracy,
        "severity": severity,
        "humor": humor,
        "composite": composite,
    }


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


def _has_prior_correction(text: str) -> bool:
    """Check if text contains kaizen-level frustration signals.

    Args:
        text: User message text to check.

    Returns:
        True if any frustration pattern matches.
    """
    return any(pattern.search(text) for _, pattern in _FRUSTRATION_PATTERNS)


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
        Dict with preceding_messages, had_prior_correction,
        compact_boundary_in_window, and tool_sequence.
    """
    start = max(0, insult_index - context_window)
    preceding: list[dict[str, Any]] = []
    had_prior_correction = False
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
                if _has_prior_correction(text):
                    had_prior_correction = True
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
        "had_prior_correction": had_prior_correction,
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
    category: str,
    matched: str,
    context_window: int,
    session_id_from_file: str,
) -> bool:
    """Insert a single insult with its rating and scenario into the database.

    Args:
        conn: Open DuckDB connection.
        record: The JSONL record containing the insult.
        records: All JSONL records in the session.
        idx: Index of the insult record in records.
        text: The insult text.
        category: Matched insult category.
        matched: The matched pattern text.
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
            matched,
            _extract_model_from_records(records, idx),
            record.get("gitBranch"),
            record.get("slug"),
            bool(record.get("isSidechain")),
            record.get("agentName"),
        ],
    )

    rating = _heuristic_rate(text, category)
    conn.execute(
        """INSERT INTO insult_ratings
        (rating_id, insult_id, creativity, accuracy, severity, humor, composite, rated_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'auto')""",
        [
            _next_id(conn, "insult_ratings", "rating_id"),
            insult_id,
            rating["creativity"],
            rating["accuracy"],
            rating["severity"],
            rating["humor"],
            rating["composite"],
        ],
    )

    scenario = _extract_scenario(records, idx, context_window)
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
            scenario["had_prior_correction"],
            scenario["compact_boundary_in_window"],
            json.dumps(scenario["tool_sequence"]),
        ],
    )

    return True


def _scan_transcripts_impl(glob_path: str, context_window: int, db_path: str) -> dict[str, Any]:
    """Core implementation for scanning transcripts and indexing insults.

    Args:
        glob_path: Glob pattern pointing to JSONL transcript files.
        context_window: Number of preceding messages to capture per insult.
        db_path: Path to DuckDB file. Empty string uses default.

    Returns:
        Dict with scanned_files, insults_found, new_insults_indexed, db_path.
    """
    files = _resolve_glob(glob_path)
    if not files:
        raise ToolError(f"No files matched glob pattern: {glob_path}")

    conn = _get_db(db_path)
    resolved_db_path = db_path or _default_db_path()
    insults_found = 0
    new_insults_indexed = 0

    for file_path in files:
        session_id_from_file = file_path.rsplit("/", maxsplit=1)[-1].removesuffix(".jsonl")
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

            for category, pattern in _INSULT_PATTERNS:
                match = pattern.search(text)
                if not match:
                    continue
                insults_found += 1
                was_new = _index_insult(
                    conn, record, records, idx, text, category, match.group(), context_window, session_id_from_file
                )
                if was_new:
                    new_insults_indexed += 1
                break  # One category per message (first match wins)

    conn.close()

    return {
        "scanned_files": len(files),
        "insults_found": insults_found,
        "new_insults_indexed": new_insults_indexed,
        "db_path": resolved_db_path,
    }


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------


@mcp.tool(annotations=_WRITE_ANNOTATIONS)
async def scan_transcripts(
    glob_path: str, context_window: int = _DEFAULT_CONTEXT_WINDOW, db_path: str = ""
) -> dict[str, Any]:
    """Scan JSONL transcript files for insults, rate them, and store in DuckDB.

    Reads each JSONL file matching the glob pattern, scans user messages
    for insults across 8 categories, extracts the preceding scenario
    context, rates each insult heuristically, and stores everything in
    a persistent DuckDB database.

    Args:
        glob_path: Glob pattern pointing to JSONL transcript files,
            e.g. ``~/.claude/projects/-my-project/*.jsonl``
        context_window: Number of preceding messages to capture per
            insult for scenario extraction. Default 5.
        db_path: Path to DuckDB file. Empty string uses default
            (~/.local/share/frustration-analyzer/insults.duckdb).

    Returns:
        Dict with scanned_files, insults_found, new_insults_indexed,
        and db_path.
    """
    return await asyncio.to_thread(_scan_transcripts_impl, glob_path, context_window, db_path)


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

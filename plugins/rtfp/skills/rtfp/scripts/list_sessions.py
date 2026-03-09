#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "duckdb>=1.0.0",
# ]
# ///
"""List recent Claude Code sessions for the current project.

Discovers JSONL session files under ~/.claude/projects/ and outputs
session metadata as JSON to stdout. Progress/status goes to stderr.

Usage:
    list_sessions.py [--project-dir DIR] [--limit N] [--list-only]
"""

from __future__ import annotations

import argparse
import json
import operator
import sys
import urllib.parse
from datetime import UTC, datetime
from pathlib import Path

import duckdb

PROJECTS_DIR = Path("~/.claude/projects").expanduser()
_TITLE_MAX_LEN = 80

_NOISE_PREFIXES = (
    "<local-command-caveat>",
    "<bash-stdout>",
    "<tool_use_error>",
    "<task-notification>",
    "<command-message>",
    "<system-reminder>",
)


def _extract_text(content: str | list | None) -> str:
    """Extract plain text from a message content field.

    Args:
        content: Either a string, a list of content blocks, or None.

    Returns:
        The extracted text string.
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
    """Check whether a message starts with a known noise prefix.

    Args:
        text: The message text to check.

    Returns:
        True if the text starts with a noise prefix.
    """
    stripped = text.lstrip()
    return any(stripped.startswith(p) for p in _NOISE_PREFIXES)


def _derive_title(path: Path) -> tuple[str, int]:
    """Derive a session title from the first non-noise user message.

    Uses DuckDB ``read_ndjson()`` to read the JSONL session file.

    Args:
        path: Path to the JSONL session file.

    Returns:
        Tuple of (title string truncated to 80 chars, total message count).
    """
    message_count = 0
    title = ""
    conn = duckdb.connect()
    try:
        rows = conn.execute(
            "SELECT to_json(t) AS raw FROM read_ndjson(?, ignore_errors := true, maximum_object_size := 67108864) t",
            [str(path)],
        ).fetchall()
    except duckdb.Error:
        conn.close()
        return title, message_count
    finally:
        conn.close()

    for (raw_json,) in rows:
        try:
            rec = json.loads(raw_json)
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(rec, dict):
            continue
        message_count += 1
        if title:
            continue
        if rec.get("type") != "user":
            continue
        if rec.get("toolUseResult") is not None:
            continue
        msg = rec.get("message")
        if not isinstance(msg, dict):
            continue
        content = _extract_text(msg.get("content"))
        if not content or _is_noise(content):
            continue
        snippet = content.replace("\n", " ").strip()
        title = snippet[:_TITLE_MAX_LEN] if len(snippet) > _TITLE_MAX_LEN else snippet
    return title, message_count


def _find_project_dir(project_dir: str) -> Path | None:
    """Find the matching project session directory under ~/.claude/projects/.

    Args:
        project_dir: The project directory path to match.

    Returns:
        The matching project session directory, or None if not found.
    """
    if not PROJECTS_DIR.exists():
        return None

    project_path = Path(project_dir).resolve()

    # Try URL-encoded form (Claude Code newer versions)
    url_encoded = urllib.parse.quote(str(project_path), safe="")
    candidate = PROJECTS_DIR / url_encoded
    if candidate.exists():
        return candidate

    # Try hyphen-joined path form (older versions)
    # Claude Code replaces every `/` (including leading) with `-` and `_` with `-`
    hyphen_slug = str(project_path).replace("/", "-").replace("_", "-")
    candidate = PROJECTS_DIR / hyphen_slug
    if candidate.exists():
        return candidate

    # Try URL-decoded match on directory names
    for d in PROJECTS_DIR.iterdir():
        if not d.is_dir():
            continue
        try:
            decoded = urllib.parse.unquote(d.name)
        except ValueError:
            continue
        if Path(decoded) == project_path:
            return d

    return None


def _get_modified_at(path: Path) -> str:
    """Get the ISO-format modification timestamp for a file.

    Args:
        path: Path to the file.

    Returns:
        ISO-formatted timestamp string, or empty string on error.
    """
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return ""
    return datetime.fromtimestamp(mtime, tz=UTC).isoformat()


def _list_sessions(session_dir: Path, limit: int) -> list[dict[str, str | int]]:
    """Discover and list JSONL session files, most recently modified first.

    Args:
        session_dir: The project session directory containing JSONL files.
        limit: Maximum number of sessions to return.

    Returns:
        List of session metadata dicts.
    """
    jsonl_files: list[tuple[float, Path]] = []
    try:
        for entry in session_dir.iterdir():
            if entry.suffix == ".jsonl" and entry.is_file():
                try:
                    mtime = entry.stat().st_mtime
                except OSError:
                    continue
                jsonl_files.append((mtime, entry))
    except OSError:
        return []

    jsonl_files.sort(key=operator.itemgetter(0), reverse=True)
    jsonl_files = jsonl_files[:limit]

    sessions: list[dict[str, str | int]] = []
    total = len(jsonl_files)
    for i, (_mtime, path) in enumerate(jsonl_files, 1):
        print(f"  Scanning session {i}/{total}: {path.stem[:8]}...", file=sys.stderr, end="\r")
        title, message_count = _derive_title(path)
        modified_at = _get_modified_at(path)
        sessions.append({
            "session_id": path.stem,
            "file_path": str(path),
            "title": title,
            "modified_at": modified_at,
            "message_count": message_count,
        })

    if total > 0:
        # Clear the progress line
        print(" " * 60, file=sys.stderr, end="\r")

    return sessions


def main() -> None:
    """List recent Claude Code sessions for a project directory."""
    parser = argparse.ArgumentParser(description="List recent Claude Code sessions for the current project")
    parser.add_argument(
        "--project-dir",
        default=None,
        help="Project directory to find sessions for (default: current working directory)",
    )
    parser.add_argument("--limit", "-n", type=int, default=20, help="Max sessions to list (default: 20)")
    parser.add_argument("--list-only", action="store_true", help="Print JSON to stdout and exit")
    args = parser.parse_args()

    project_dir: str = args.project_dir if args.project_dir is not None else str(Path.cwd())
    session_dir = _find_project_dir(project_dir)

    if session_dir is None:
        print(f"No session directory found for project: {project_dir}", file=sys.stderr)
        result: dict[str, list | int] = {"sessions": [], "count": 0}
        print(json.dumps(result, indent=2))
        sys.exit(1)

    print(f"Scanning sessions in: {session_dir}", file=sys.stderr)
    sessions = _list_sessions(session_dir, args.limit)

    result = {"sessions": sessions, "count": len(sessions)}
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

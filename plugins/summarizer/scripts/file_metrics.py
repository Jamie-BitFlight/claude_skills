#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Cross-platform file metrics for summarization strategy selection.

Provides word count, line count, character count, file type detection,
and excerpt extraction using only Python standard library.

Usage:
    python file_metrics.py <file_path> [--excerpt-lines N] [--json]

Output (default): Human-readable metrics
Output (--json):  JSON object with all metrics
"""

from __future__ import annotations

import argparse
import codecs
import json
import mimetypes
import sys
from pathlib import Path
from typing import Any

# Strategy thresholds (word counts)
SMALL_THRESHOLD = 2000
MEDIUM_THRESHOLD = 10000

# File type categories for summarization strategy selection
FILE_CATEGORIES: dict[str, list[str]] = {
    "code": [
        ".py",
        ".js",
        ".ts",
        ".jsx",
        ".tsx",
        ".rs",
        ".go",
        ".java",
        ".c",
        ".cpp",
        ".h",
        ".hpp",
        ".cs",
        ".rb",
        ".php",
        ".swift",
        ".kt",
        ".scala",
        ".lua",
        ".pl",
        ".sh",
        ".bash",
        ".zsh",
        ".fish",
        ".ps1",
        ".r",
        ".m",
        ".mm",
        ".zig",
        ".nim",
        ".v",
        ".dart",
        ".ex",
        ".exs",
        ".clj",
        ".hs",
        ".ml",
        ".fs",
    ],
    "config": [".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf", ".env", ".properties", ".xml", ".plist"],
    "data": [".csv", ".tsv", ".parquet", ".arrow", ".ndjson", ".jsonl"],
    "documentation": [".md", ".rst", ".txt", ".adoc", ".org", ".tex", ".rtf"],
    "markup": [".html", ".htm", ".xhtml", ".svg"],
    "image": [".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".ico", ".tiff", ".tif"],
    "binary": [
        ".pdf",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".pptx",
        ".zip",
        ".tar",
        ".gz",
        ".bz2",
        ".7z",
        ".rar",
        ".exe",
        ".dll",
        ".so",
        ".dylib",
        ".wasm",
        ".bin",
        ".dat",
        ".db",
        ".sqlite",
    ],
}


def detect_category(file_path: Path) -> str:
    """Detect file category from extension.

    Returns:
        Category name: "code", "config", "data", "documentation",
        "markup", "image", "binary", or "unknown".
    """
    ext = file_path.suffix.lower()
    for category, extensions in FILE_CATEGORIES.items():
        if ext in extensions:
            return category
    return "unknown"


def probe_text(file_path: Path) -> bool:
    """Probe a UTF-8 prefix without mistaking a split code point for binary data.

    Returns:
        Whether the available UTF-8 prefix appears textual.
    """
    with file_path.open("rb") as stream:
        chunk = stream.read(8192)
    if b"\x00" in chunk:
        return False
    try:
        codecs.getincrementaldecoder("utf-8")().decode(chunk, final=len(chunk) < 8192)
    except UnicodeDecodeError:
        return False
    return True


def is_text_file(file_path: Path) -> bool:
    """Return whether the prefix appears textual; preserve the legacy boolean API.

    Returns:
        Whether the prefix appears textual, or false when inaccessible.
    """
    try:
        return probe_text(file_path)
    except OSError:
        return False


def count_metrics(file_path: Path) -> dict[str, Any]:
    """Count words, lines, and characters in a text file.

    Returns:
        Dict with word_count, line_count, char_count (int values),
        or with those keys as None plus an error key on failure.
    """
    try:
        content = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as e:
        return {"word_count": None, "line_count": None, "char_count": None, "error": str(e)}

    lines = content.splitlines()
    words = content.split()

    return {"word_count": len(words), "line_count": len(lines), "char_count": len(content)}


def extract_excerpt(file_path: Path, head_lines: int = 20, tail_lines: int = 10) -> dict[str, Any]:
    """Extract head and tail excerpts from a text file.

    Returns:
        Dict with head (str), tail (str or None), total_lines (int),
        or head=None, tail=None, error on failure.
    """
    try:
        content = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as e:
        return {"head": None, "tail": None, "error": str(e)}

    lines = content.splitlines()
    total = len(lines)

    head = "\n".join(lines[:head_lines]) if total > 0 else ""

    if tail_lines == 0:
        tail = None
    elif total > head_lines + tail_lines:
        tail = "\n".join(lines[-tail_lines:])
    elif total > head_lines:
        tail = "\n".join(lines[head_lines:])
    else:
        tail = None

    return {"head": head, "tail": tail, "total_lines": total}


def summarization_strategy(word_count: int | None) -> str:
    """Recommend summarization strategy based on word count.

    Returns:
        Strategy name: "small" (< 2000 words), "medium" (2000 to <10000),
        "large" (>= 10000), or "unknown" if word_count is None.
    """
    if word_count is None:
        return "unknown"
    if word_count < SMALL_THRESHOLD:
        return "small"
    if word_count < MEDIUM_THRESHOLD:
        return "medium"
    return "large"


def get_file_metrics(file_path: Path, excerpt_lines: int = 20, tail_lines: int = 10) -> dict[str, Any]:
    """Get comprehensive file metrics for summarization planning.

    Args:
        file_path: Path to the file to analyze.
        excerpt_lines: Number of head lines to include in excerpt (0 to skip).
        tail_lines: Number of tail lines to include in excerpt.

    Returns:
        Dict with path, name, extension, category, mime_type, is_text,
        file_size_bytes, and text metrics if applicable.
    """
    if not file_path.exists():
        return {"error": f"File not found: {file_path}"}

    if not file_path.is_file():
        return {"error": f"Not a file: {file_path}"}

    category = detect_category(file_path)
    mime_type, _ = mimetypes.guess_type(str(file_path))
    try:
        is_text = probe_text(file_path)
        file_size = file_path.stat().st_size
    except OSError as error:
        return {"error": str(error), "path": str(file_path)}

    result: dict[str, Any] = {
        "path": str(file_path.resolve()),
        "name": file_path.name,
        "extension": file_path.suffix.lower(),
        "category": category,
        "mime_type": mime_type,
        "is_text": is_text,
        "file_size_bytes": file_size,
    }

    if is_text:
        metrics = count_metrics(file_path)
        result.update(metrics)
        result["strategy"] = summarization_strategy(metrics.get("word_count"))

        if "error" in metrics:
            return result
        if excerpt_lines > 0:
            excerpt = extract_excerpt(file_path, head_lines=excerpt_lines, tail_lines=tail_lines)
            result["excerpt"] = excerpt
            if "error" in excerpt:
                result["error"] = excerpt["error"]
    else:
        result["word_count"] = None
        result["line_count"] = None
        result["char_count"] = None
        result["strategy"] = "binary"
        result["note"] = "Binary or non-UTF-8 prefix. Use an appropriate media/encoding-aware reader."

    return result


def format_human_readable(metrics: dict[str, Any]) -> str:
    """Format metrics as human-readable text.

    Returns:
        Multi-line string with formatted metrics.
    """
    if "error" in metrics:
        return f"Error: {metrics['error']}"

    lines = [
        f"File: {metrics['name']}",
        f"Path: {metrics['path']}",
        f"Category: {metrics['category']}",
        f"Size: {metrics['file_size_bytes']:,} bytes",
        f"Text: {metrics['is_text']}",
    ]

    if metrics["is_text"]:
        lines.extend([
            f"Words: {metrics.get('word_count', 'N/A'):,}",
            f"Lines: {metrics.get('line_count', 'N/A'):,}",
            f"Characters: {metrics.get('char_count', 'N/A'):,}",
            f"Strategy: {metrics.get('strategy', 'unknown')}",
        ])
    else:
        lines.append(f"Note: {metrics.get('note', 'Binary file')}")

    return "\n".join(lines)


def main() -> None:
    """Entry point."""
    parser = argparse.ArgumentParser(description="File metrics for summarization strategy selection")
    parser.add_argument("file_path", type=Path, help="Path to the file to analyze")
    parser.add_argument(
        "--excerpt-lines", type=int, default=20, help="Number of head lines to include in excerpt (default: 20)"
    )
    parser.add_argument(
        "--tail-lines", type=int, default=10, help="Number of tail lines to include in excerpt (default: 10)"
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON instead of human-readable text")
    parser.add_argument("--no-excerpt", action="store_true", help="Skip excerpt extraction")

    args = parser.parse_args()

    if args.excerpt_lines < 0:
        parser.error("--excerpt-lines must be >= 0")
    if args.tail_lines < 0:
        parser.error("--tail-lines must be >= 0")

    excerpt_lines = 0 if args.no_excerpt else args.excerpt_lines
    metrics = get_file_metrics(args.file_path, excerpt_lines=excerpt_lines, tail_lines=args.tail_lines)

    if args.json:
        print(json.dumps(metrics, indent=2, default=str))
    else:
        print(format_human_readable(metrics))

    # Exit with error code if file had issues
    if "error" in metrics:
        sys.exit(1)


if __name__ == "__main__":
    main()

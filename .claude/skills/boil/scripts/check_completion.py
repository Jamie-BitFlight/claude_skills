#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Completion Checker — scans files or agent response text for prohibited patterns.

Detects incomplete work, workarounds, invented limits, and prohibited exits.

Usage:
    # Scan files or directories
    .claude/skills/boil/scripts/check_completion.py [file_or_dir ...]

    # Check agent response text (pipe from command or heredoc)
    echo "response text" | .claude/skills/boil/scripts/check_completion.py --stdin
    pbpaste | .claude/skills/boil/scripts/check_completion.py --stdin

Exit codes:
    0 — no violations found
    1 — one or more violations found (review output before claiming complete)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Patterns checked in both file mode and stdin/response mode
PROHIBITED_PATTERNS = [
    # Invented limits — code patterns
    (r"\[:\d+\]", "INVENTED_LIMIT", "Slice truncation — e.g. content[:500]"),
    (r"\bMAX_LEN\s*=\s*\d+", "INVENTED_LIMIT", "Hard-coded MAX_LEN constant"),
    (r"\bmax_length\s*=\s*\d+", "INVENTED_LIMIT", "Hard-coded max_length parameter"),
    (r"truncate\s*=\s*True", "INVENTED_LIMIT", "Explicit truncation flag"),
    # Workaround markers — code and prose
    (r"\bworkaround\b", "WORKAROUND", "Workaround mentioned — verify root cause is fixed"),
    (r"\bquick[- ]?fix\b", "WORKAROUND", "Quick fix mentioned — verify root cause is fixed"),
    # Deferral phrases — primarily in prose/responses
    (r"\btable\s+this\b", "DEFERRAL", "Deferral phrase — verify permanent solve was applied"),
    (r"\blater\s+fix\b", "DEFERRAL", "Deferred fix — verify it was addressed"),
    (r"\bfor\s+now\b", "DEFERRAL", "Temporary language — verify permanent solve applied"),
    (r"\bcan\s+be\s+added\s+later\b", "DEFERRAL", "Deferral phrase — verify item was addressed"),
    (r"\baddress\s+later\b", "DEFERRAL", "Deferral phrase — verify permanent solve applied"),
    # Incompleteness markers
    (r"\bTODO\b(?!.*\btest\b)", "INCOMPLETE", "TODO marker (non-test) — verify resolved"),
    (r"\bFIXME\b", "INCOMPLETE", "FIXME marker — verify resolved"),
    (r"\bPENDING\b", "INCOMPLETE", "PENDING marker — verify resolved"),
    (r"partial\s+implementation", "INCOMPLETE", "Partial implementation stated — verify complete"),
    (r"not\s+implemented", "INCOMPLETE", "Not implemented — verify addressed"),
    (r"\bstub\b", "INCOMPLETE", "Stub mentioned — verify replaced with implementation"),
]

# Additional patterns checked only in stdin/response mode (agent text output)
RESPONSE_ONLY_PATTERNS = [
    (r"\bas\s+a\s+workaround\b", "WORKAROUND", "Workaround offered in response — apply root cause fix"),
    (r"\bwe\s+could\s+table\b", "DEFERRAL", "Table-for-later phrasing in response"),
    (r"\bi'?ll?\s+leave\b", "DEFERRAL", "Delegating remainder back to user"),
    (r"\bpartial\b.*\bimpl", "INCOMPLETE", "Partial implementation in response"),
    (r"\bin\s+a\s+future\b", "DEFERRAL", "Future-work deferral in response"),
    (r"\bnext\s+(step|time)\b", "DEFERRAL", "Deferred to next step/time"),
    (r"\bleft\s+as\s+an\s+exercise", "DEFERRAL", "Exercise-delegation to user"),
    (r"\bfor\s+simplicity\b", "WORKAROUND", "Simplicity-excuse — verify full solution applied"),
]

IGNORE_EXTENSIONS = {".pyc", ".lock", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".woff", ".ttf"}
IGNORE_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv"}


def scan_text(text: str, source_label: str, extra_patterns: list | None = None) -> list[tuple[int, str, str, str]]:
    """Return list of (line_no, pattern_kind, description, line_text) for each hit."""
    patterns = PROHIBITED_PATTERNS + (extra_patterns or [])
    hits = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        for pattern, kind, description in patterns:
            if re.search(pattern, line, re.IGNORECASE):
                hits.append((line_no, kind, description, line))
    return hits


def scan_file(path: Path) -> list[tuple[int, str, str, str]]:
    """Scan a single file for violations.

    Returns:
        List of (line_no, kind, description, line_text) tuples, one per violation.
    """
    if path.suffix in IGNORE_EXTENSIONS:
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    return scan_text(text, str(path))


def collect_paths(targets: list[str]) -> list[Path]:
    """Expand file and directory targets into a flat list of file paths.

    Returns:
        Flat list of Path objects for all matching files.
    """
    paths = []
    for t in targets:
        p = Path(t)
        if p.is_file():
            paths.append(p)
        elif p.is_dir():
            paths.extend(
                child
                for child in p.rglob("*")
                if child.is_file() and not any(part in IGNORE_DIRS for part in child.parts)
            )
    return paths


def print_hits(source_label: str, hits: list[tuple[int, str, str, str]]) -> None:
    """Print violation hits grouped under a source label."""
    print(f"\n{source_label}")
    for line_no, kind, description, line_text in hits:
        print(f"  line {line_no:4d}  [{kind}]  {description}")
        print(f"           {line_text}")


def main() -> int:
    """Entry point — dispatch to stdin or file scanning mode.

    Returns:
        0 if no violations found, 1 otherwise.
    """
    stdin_mode = "--stdin" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--stdin"]

    total_violations = 0

    if stdin_mode:
        text = sys.stdin.read()
        if not text.strip():
            print("OK — empty input, no violations found.")
            return 0
        hits = scan_text(text, "<stdin>", extra_patterns=RESPONSE_ONLY_PATTERNS)
        if hits:
            print_hits("<agent response / stdin>", hits)
            total_violations += len(hits)
        else:
            print("OK — no completion violations found in response text.")
    else:
        targets = args or ["."]
        paths = collect_paths(targets)
        for path in sorted(paths):
            hits = scan_file(path)
            if hits:
                print_hits(str(path), hits)
                total_violations += len(hits)
        if total_violations == 0:
            print("OK — no completion violations found.")

    if total_violations > 0:
        print(f"\n{total_violations} violation(s) found. Review before claiming task complete.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Check that Any/cast() usage is restricted to boundary modules."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

BOUNDARY_PATTERNS = {"boundary", "adapter", "parser", "validator", "external", "inbound"}


def is_boundary_module(filepath: Path) -> bool:
    """Check if a file is an approved boundary module.

    Returns:
        True if the file path or stem matches a known boundary pattern.
    """
    parts = set(filepath.parts)
    if parts & BOUNDARY_PATTERNS:
        return True
    stem = filepath.stem
    return any(stem.endswith(f"_{p}") for p in BOUNDARY_PATTERNS)


def find_any_usage(filepath: Path) -> list[tuple[int, str]]:
    """Find Any usage in a Python file.

    Returns:
        List of (line_number, description) tuples for each violation found.
    """
    violations = []
    try:
        tree = ast.parse(filepath.read_text(encoding="utf-8"), filename=str(filepath))
    except SyntaxError:
        return []

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.names:
                violations.extend((node.lineno, "imports Any") for alias in node.names if alias.name == "Any")
        elif isinstance(node, ast.Call):
            if (isinstance(node.func, ast.Name) and node.func.id == "cast") or (
                isinstance(node.func, ast.Attribute) and node.func.attr == "cast"
            ):
                violations.append((node.lineno, "calls cast()"))
        elif isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id == "Any":
            violations.append((node.lineno, "uses Any type"))

    return violations


def main() -> None:
    """Scan a directory for Any/cast() usage outside boundary modules and report violations."""
    search_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path()
    all_violations = []

    for py_file in search_dir.rglob("*.py"):
        if is_boundary_module(py_file):
            continue
        violations = find_any_usage(py_file)
        for line, msg in violations:
            all_violations.append(f"  {py_file}:{line} - {msg}")

    if all_violations:
        print("FAIL: Any/cast() found outside boundary modules:")
        for v in all_violations:
            print(v)
        sys.exit(1)
    else:
        print("PASS: Any usage restricted to boundary modules")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Check that Any/cast() usage is restricted to boundary modules."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

BOUNDARY_PATTERNS = {"boundary", "boundaries", "adapter", "adapters", "parser", "parsers", "validator", "validators", "external", "inbound", "coerce"}


def is_boundary_module(filepath: Path) -> bool:
    """Check if a file is an approved boundary module.

    Returns:
        True if the file path or stem matches a known boundary pattern.
    """
    parts = set(filepath.parts)
    if parts & BOUNDARY_PATTERNS:
        return True
    stem = filepath.stem
    singular = {"boundary", "adapter", "parser", "validator", "external", "inbound", "coerce"}
    return any(stem.endswith(f"_{p}") for p in singular)


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
        elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            if node.value.id == "typing" and node.attr == "Any":
                violations.append((node.lineno, "uses typing.Any"))

    return violations


def main() -> None:
    """Scan a directory for Any/cast() usage outside boundary modules and report violations."""
    targets = [Path(arg) for arg in sys.argv[1:]] or [Path()]
    missing = [path for path in targets if not path.exists()]
    if missing:
        for path in missing:
            print(f"ERROR: target does not exist: {path}", file=sys.stderr)
        sys.exit(2)

    files: list[Path] = []
    for target in targets:
        if target.is_file():
            if target.suffix == ".py":
                files.append(target)
        else:
            files.extend(target.rglob("*.py"))

    all_violations = []
    for py_file in files:
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

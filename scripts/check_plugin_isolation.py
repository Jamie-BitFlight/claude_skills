#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# ///
"""Check static plugin isolation invariants without repository Python imports."""

from __future__ import annotations

import argparse
from pathlib import Path

FORBIDDEN = ("../../scripts/", "../scripts/", ".claude/skills/")


def violations(plugin: Path) -> list[str]:
    """Return source-tree escape references found in executable/config files."""
    found: list[str] = []
    for path in plugin.rglob("*"):
        if not path.is_file() or path.is_symlink() or path.suffix not in {".py", ".json", ".yaml", ".yml"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for token in FORBIDDEN:
            if token in text:
                found.append(f"{path.relative_to(plugin)}: forbidden repository escape {token!r}")
    return found


def main() -> int:
    """Validate one plugin boundary."""
    parser = argparse.ArgumentParser()
    parser.add_argument("plugin", type=Path)
    args = parser.parse_args()
    failures = violations(args.plugin.resolve())
    if failures:
        print("\n".join(failures))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

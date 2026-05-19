#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "marko[gfm]",
# ]
# ///
"""Parse unchecked checkbox items from a markdown file and emit a task pool.

This script reads a markdown file containing GitHub Flavored Markdown checkbox
items (``- [ ] ...``), extracts all unchecked items via the marko GFM AST, and
emits either a JSON task pool or human-readable output showing the TaskCreate
sequence and worker count for use with swarm orchestration.

Usage::

    uv run scripts/markdown_to_task_pool.py <markdown_file> [--workers N] [--json]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import TypedDict

from marko import Markdown
from marko.block import List, ListItem, Paragraph
from marko.inline import RawText


class TaskItem(TypedDict):
    """A single task item in the pool."""

    index: int
    worker_id: str
    text: str


class TaskPool(TypedDict):
    """The complete task pool output structure."""

    team_name: str
    items: list[TaskItem]
    worker_count: int


def extract_unchecked_items(markdown_text: str) -> list[str]:
    """Extract text from unchecked checkbox items in a markdown document.

    Walks the marko GFM AST to find ``- [ ]`` list items (``checked=False``),
    skipping checked items (``- [x]`` and ``- [X]``, both ``checked=True``).
    Non-checkbox list items (``checked`` attribute absent or ``None``) are also
    skipped.

    Args:
        markdown_text: Full contents of a markdown file as a string.

    Returns:
        Ordered list of text strings from unchecked checkbox items. Each string
        is stripped of leading/trailing whitespace.
    """
    md = Markdown(extensions=["gfm"])
    doc = md.parse(markdown_text)

    results: list[str] = []
    for node in doc.children:
        if not isinstance(node, List):
            continue
        for item in node.children:
            if not isinstance(item, ListItem):
                continue
            for child in item.children:
                if not isinstance(child, Paragraph) or not hasattr(child, "checked"):
                    continue
                if child.checked is not False:
                    # Skips True (checked [x]/[X]) and None (non-checkbox items)
                    continue
                text_parts = [c.children.strip() for c in child.children if isinstance(c, RawText)]
                text = " ".join(text_parts).strip()
                if text:
                    results.append(text)

    return results


def build_task_pool(markdown_file: Path, worker_count_override: int | None = None) -> TaskPool:
    """Build a task pool dictionary from a markdown file.

    Reads the markdown file, extracts unchecked checkbox items, and constructs
    the task pool structure used for swarm orchestration.

    Args:
        markdown_file: Path to the markdown file containing checkbox items.
        worker_count_override: If provided, overrides the default worker count
            (which is the number of unchecked items). Does not affect the number
            of tasks emitted.

    Returns:
        TaskPool with keys ``team_name`` (str), ``items`` (list of TaskItem with
        ``index``, ``worker_id``, and ``text`` fields), and ``worker_count``
        (int).

    Raises:
        OSError: If the file cannot be read.
        ValueError: If the markdown text cannot be parsed.
    """
    markdown_text = markdown_file.read_text(encoding="utf-8")
    items = extract_unchecked_items(markdown_text)

    team_name = f"swarm-{markdown_file.stem}"
    worker_count = worker_count_override if worker_count_override is not None else len(items)

    return TaskPool(
        team_name=team_name,
        items=[TaskItem(index=i, worker_id=f"worker-{i}", text=text) for i, text in enumerate(items)],
        worker_count=worker_count,
    )


def format_human_readable(pool: TaskPool) -> str:
    """Format a task pool as human-readable text.

    Args:
        pool: Task pool as returned by :func:`build_task_pool`.

    Returns:
        Multi-line string with team name, task count, per-item details, and
        worker count summary.
    """
    items = pool["items"]
    lines: list[str] = [f"Team: {pool['team_name']}", f"Tasks: {len(items)}", ""]
    lines.extend(f"  [{item['index']}] {item['worker_id']}: {item['text']}" for item in items)
    lines.extend(("", f"Workers to spawn: {pool['worker_count']}"))
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Argument list to parse. Defaults to ``sys.argv[1:]``.

    Returns:
        Parsed argument namespace with ``markdown_file`` (Path), ``workers``
        (int or None), and ``json`` (bool) attributes.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Parse unchecked checkbox items from a markdown file and emit a task pool for swarm orchestration."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  %(prog)s tasks.md --json\n"
            "  %(prog)s tasks.md --workers 3\n"
            "  %(prog)s tasks.md --workers 3 --json"
        ),
    )
    parser.add_argument("markdown_file", type=Path, help="Path to the markdown file containing checkbox items.")

    def positive_int(value: str) -> int:
        try:
            n = int(value)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(f"must be an integer, got {value!r}") from exc
        if n < 1:
            raise argparse.ArgumentTypeError(f"must be >= 1, got {n}")
        return n

    parser.add_argument(
        "--workers",
        type=positive_int,
        default=None,
        metavar="N",
        help=(
            "Number of worker agents to spawn (default: number of unchecked items). "
            "Must be >= 1. Does not affect the number of tasks emitted."
        ),
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output instead of human-readable text.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the markdown task pool CLI.

    Parses arguments, reads the markdown file, extracts unchecked checkbox items,
    and prints either JSON or human-readable output to stdout.

    Args:
        argv: Argument list to parse. Defaults to ``sys.argv[1:]``.

    Returns:
        Exit code: 0 on success, 1 on error.
    """
    args = parse_args(argv)
    markdown_file: Path = args.markdown_file

    try:
        pool = build_task_pool(markdown_file, worker_count_override=args.workers)
    except OSError as exc:
        print(f"error: {markdown_file}: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"error: failed to parse {markdown_file}: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(pool, indent=2))
    else:
        print(format_human_readable(pool))

    return 0


if __name__ == "__main__":
    sys.exit(main())

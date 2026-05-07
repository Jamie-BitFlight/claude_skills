#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""Load design-context files for the designing-ui-for-cli skill.

Searches case-insensitively for PRODUCT.md, DESIGN.TUI.md, and DESIGN.md in the
following directories (first match per file wins):

    1. project root (cwd)
    2. context/
    3. docs/

Emits a JSON document to stdout matching this shape:

    {
      "contextDir": "<absolute path or null>",
      "product":    {"path": "<abs>", "content": "<text>", "isPlaceholder": <bool>} | null,
      "designTui":  {"path": "<abs>", "content": "<text>"} | null,
      "design":     {"path": "<abs>", "content": "<text>"} | null
    }

Resolution rule: when both ``designTui`` and ``design`` are populated, agents
use ``designTui`` for TUI/CLI work and treat ``design`` as auxiliary (for
example a web frontend living in the same repository).

``isPlaceholder`` is true when PRODUCT.md is empty, smaller than 200
characters, or contains a ``[TODO]`` marker.

Exit code is 0 even when no files are found; missing fields are returned as
``null`` so the caller can branch deterministically.

Mirrors the JSON output shape of impeccable's ``load-context.mjs`` with the
``designTui`` extension added for TUI projects.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PRODUCT_NAMES = ("PRODUCT.md",)
DESIGN_TUI_NAMES = ("DESIGN.TUI.md",)
DESIGN_NAMES = ("DESIGN.md",)
SEARCH_DIRS = ("", "context", "docs")
PLACEHOLDER_MIN_CHARS = 200
PLACEHOLDER_MARKER = "[TODO]"


def find_file_case_insensitive(directory: Path, target: str) -> Path | None:
    """Return the first entry in ``directory`` whose name matches ``target`` case-insensitively."""
    if not directory.is_dir():
        return None
    target_lower = target.lower()
    for entry in directory.iterdir():
        if entry.is_file() and entry.name.lower() == target_lower:
            return entry.resolve()
    return None


def find_first_match(cwd: Path, names: tuple[str, ...]) -> Path | None:
    """Search SEARCH_DIRS in priority order for any of ``names``; return first hit.

    Returns:
        Resolved absolute Path of the first matching file, or ``None`` if no
        match is found in any search directory.
    """
    for rel in SEARCH_DIRS:
        directory = (cwd / rel).resolve() if rel else cwd
        for name in names:
            hit = find_file_case_insensitive(directory, name)
            if hit is not None:
                return hit
    return None


def is_placeholder(content: str) -> bool:
    """Return True if PRODUCT.md content is empty, too short, or marked TODO."""
    if not content.strip():
        return True
    if len(content) < PLACEHOLDER_MIN_CHARS:
        return True
    return PLACEHOLDER_MARKER in content


def build_file_record(path: Path, *, with_placeholder: bool = False) -> dict[str, object]:
    """Read ``path`` and assemble the JSON record for it.

    Returns:
        Dict with ``path`` and ``content`` keys, plus ``isPlaceholder`` when
        ``with_placeholder`` is true.
    """
    content = path.read_text(encoding="utf-8")
    record: dict[str, object] = {"path": str(path), "content": content}
    if with_placeholder:
        record["isPlaceholder"] = is_placeholder(content)
    return record


def load_design_context(cwd: Path) -> dict[str, object]:
    """Locate context files relative to ``cwd`` and assemble the result dict.

    Returns:
        Dict with ``contextDir``, ``product``, ``designTui``, and ``design``
        keys. Each file field is either a record dict or ``None``.
    """
    product_path = find_first_match(cwd, PRODUCT_NAMES)
    design_tui_path = find_first_match(cwd, DESIGN_TUI_NAMES)
    design_path = find_first_match(cwd, DESIGN_NAMES)

    first_match = next((p for p in (product_path, design_tui_path, design_path) if p is not None), None)
    context_dir = str(first_match.parent) if first_match is not None else None

    return {
        "contextDir": context_dir,
        "product": (build_file_record(product_path, with_placeholder=True) if product_path is not None else None),
        "designTui": (build_file_record(design_tui_path) if design_tui_path is not None else None),
        "design": build_file_record(design_path) if design_path is not None else None,
    }


def main() -> int:
    """Print the design-context JSON to stdout.

    Returns:
        ``0`` on the normal success path; missing files do not raise.
    """
    cwd = Path.cwd().resolve()
    result = load_design_context(cwd)
    sys.stdout.write(json.dumps(result))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

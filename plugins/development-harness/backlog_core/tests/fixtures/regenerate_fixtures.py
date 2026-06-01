"""Regenerate full-content test fixtures for backlog issues.

Calls ``operations.view_item()`` directly (un-gated path) so that over-budget
items like #2515 return their full body and sections, not the compact
section-directory fallback the MCP ``backlog_view`` tool returns.

Usage (from repo root)::

    uv run python plugins/development-harness/backlog_core/tests/fixtures/regenerate_fixtures.py

All four fixture files are written to the same directory as this script.
JSON is written without indentation (repo Code Quality Standard: no json.dumps indent).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup — add the development-harness module root so backlog_core imports
# work whether this script is run from the repo root or from within the plugin.
# ---------------------------------------------------------------------------
_SCRIPT_DIR = Path(__file__).resolve().parent
_MODULE_ROOT = _SCRIPT_DIR.parent.parent.parent  # plugins/development-harness/
if str(_MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(_MODULE_ROOT))

from backlog_core.operations import view_item

__all__: list[str] = []

#: Issues to regenerate fixtures for.  These are the four items referenced in
#: the MCP progressive disclosure contract acceptance criteria (issue #2521).
ISSUE_NUMBERS: tuple[int, ...] = (2515, 2521, 996, 1857)

FIXTURES_DIR = _SCRIPT_DIR


def regenerate(issue_num: int) -> Path:
    """Fetch full content for *issue_num* and write the fixture JSON file.

    Calls ``view_item`` with default parameters (``include_content=True``),
    which returns the full ``ViewItemResult`` without any token-budget gate.

    Args:
        issue_num: GitHub issue number to fetch.

    Returns:
        Path to the written fixture file.

    Raises:
        Exception: Propagates any error from ``view_item`` so the caller can
            report and abort rather than silently write an empty fixture.
    """
    selector = f"#{issue_num}"
    t0 = time.monotonic()
    result = view_item(selector)
    elapsed = time.monotonic() - t0

    data = result.model_dump(mode="json")
    out_path = FIXTURES_DIR / f"issue-{issue_num}-full.json"
    out_path.write_text(json.dumps(data), encoding="utf-8")

    section_count = len(result.sections)
    body_len = len(result.body)
    file_size = out_path.stat().st_size
    print(
        f"  issue-{issue_num}: {section_count} sections, "
        f"{body_len:,} body chars → {file_size:,} bytes  ({elapsed:.1f}s)"
    )
    return out_path


def main() -> None:
    """Regenerate all fixtures, printing a summary line per issue."""
    print(f"Regenerating {len(ISSUE_NUMBERS)} fixtures into {FIXTURES_DIR}")
    for issue_num in ISSUE_NUMBERS:
        print(f"Fetching #{issue_num}...", end=" ", flush=True)
        regenerate(issue_num)
    print("Done.")


if __name__ == "__main__":
    main()

"""Assert frontend files contain no business logic.

Frontends are thin adapters: parse args, call operations, format output.
This test greps for patterns that indicate business logic has leaked into
frontend files.

As operations are extracted to dh_core.operations, forbidden patterns are
registered here. Each pattern is a regex string. If the pattern matches
in the target file, the test fails.

The patterns grow incrementally — each time an operation is extracted from
a frontend, the pattern that would re-introduce that logic is registered
here as a regression guard.

Current state: no patterns registered (Phase 0 scaffolding). Patterns will
be added starting in Phase 1.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# Ensure plugin root resolves relative paths.
_plugin_root = Path(__file__).resolve().parent.parent

#: Frontend files that must remain logic-free.
FRONTEND_FILES: list[str] = ["sam_schema/cli.py", "sam_schema/server.py", "backlog_core/server.py"]

#: Patterns forbidden in each frontend file.
#: Each entry is (filepath, regex_pattern, description).
#: Starts empty — patterns are added as logic is extracted.
FORBIDDEN_PATTERNS: list[tuple[str, str, str]] = [
    # Phase 1 will add entries like:
    # ("sam_schema/cli.py", r"from sam_schema\.core\.query import", "CLI must import from dh_core.operations, not legacy query.py"),
    # ("sam_schema/server.py", r"from sam_schema\.core\.gist_task_layer import", "MCP server must use dh_core.operations, not GistTaskLayer directly"),
]


class TestFrontendLogicFree:
    """Frontend files must not contain business logic."""

    @pytest.mark.parametrize(
        ("filepath", "pattern", "description"),
        FORBIDDEN_PATTERNS or [("__none__", "__never_match__", "no patterns registered yet")],
    )
    def test_no_forbidden_patterns(self, filepath: str, pattern: str, description: str) -> None:
        if filepath == "__none__":
            pytest.skip("No forbidden patterns registered yet")
        full_path = _plugin_root / filepath
        if not full_path.exists():
            pytest.skip(f"{filepath} does not exist yet")
        content = full_path.read_text()
        assert not re.search(pattern, content), (
            f"{filepath} matches forbidden pattern: {pattern}\n"
            f"Description: {description}\n"
            f"This indicates business logic has leaked back into the frontend."
        )

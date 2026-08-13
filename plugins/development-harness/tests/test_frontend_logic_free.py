"""Assert frontend files contain no business logic.

Frontends are thin adapters: parse args, call operations, format output.
This test uses AST-based import analysis to enforce that frontend files
only import from an allowlist of permitted modules.

The allowlist approach is stronger than a regex denylist because it catches
the general case (any import not on the list) rather than specific known
bad patterns. As logic is extracted to dh_core.operations, the allowlist
is tightened — eventually the only permitted import for business logic
will be dh_core.operations.

Additionally, a denylist of specific forbidden patterns (regexes) is
maintained as a regression guard for known-leaked logic.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

# Ensure plugin root resolves relative paths.
_plugin_root = Path(__file__).resolve().parent.parent

#: Frontend files that must remain logic-free.
FRONTEND_FILES: list[str] = ["sam_schema/cli.py", "sam_schema/server.py", "backlog_core/server.py"]

#: Allowed import roots for each frontend file.
#: During the transition, frontends still import from legacy modules.
#: As operations are extracted, entries are removed from the allowlist
#: and the forbidden_patterns list grows.
ALLOWED_IMPORTS: dict[str, set[str]] = {
    "sam_schema/cli.py": {
        "__future__",
        "io",
        "json",
        "os",
        "re",
        "shutil",
        "subprocess",
        "sys",
        "pathlib",
        "typing",
        "collections.abc",
        "datetime",
        "typer",
        "rich",
        "ruamel",
        "pydantic",
        "dh_core",
        "sam_schema",
        "dh_paths",
        "backlog_core",
    },
    "sam_schema/server.py": {
        "__future__",
        "json",
        "logging",
        "datetime",
        "pathlib",
        "typing",
        "collections.abc",
        "tiktoken",
        "fastmcp",
        "mcp",
        "pydantic",
        "backlog_core",
        "dh_core",
        "sam_schema",
    },
    "backlog_core/server.py": {
        "__future__",
        "argparse",
        "asyncio",
        "collections",
        "contextlib",
        "dataclasses",
        "difflib",
        "json",
        "logging",
        "os",
        "re",
        "sqlite3",
        "sys",
        "time",
        "datetime",
        "pathlib",
        "typing",
        "collections.abc",
        "dh_paths",
        "dispatch_schema",
        "tiktoken",
        "fastmcp",
        "mcp",
        "pydantic",
        "ruamel",
        "github",
        "dh_core",
        "backlog_core",
        "agent_profile",
    },
}

#: Specific forbidden regex patterns per file (regression guard).
#: Grows as logic is extracted. Each entry is (filepath, pattern, description).
FORBIDDEN_PATTERNS: list[tuple[str, str, str]] = [
    # Phase 1 will add entries like:
    # ("sam_schema/cli.py", r"from sam_schema\.core\.query import",
    #  "CLI must import from dh_core.operations, not legacy query.py"),
    # ("sam_schema/server.py", r"from sam_schema\.core\.gist_task_layer import",
    #  "MCP server must use dh_core.operations, not GistTaskLayer directly"),
]


def _extract_import_roots(filepath: Path) -> set[str]:
    """Parse a Python file and extract all import root module names.

    For ``from foo.bar import baz``, the root is ``foo``.
    For ``import foo.bar``, the root is ``foo``.
    Relative imports (``from . import foo``) are skipped — they are internal
    package references, not external dependencies.

    Args:
        filepath: Path to the Python file to analyze.

    Returns:
        Set of root module name strings.
    """
    content = filepath.read_text(encoding="utf-8")
    tree = ast.parse(content, filename=str(filepath))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                roots.add(root)
            continue
        if isinstance(node, ast.ImportFrom):
            if node.level > 0:
                # Relative import (from . import ... or from .foo import ...)
                # These are internal package references, not external deps.
                continue
            if node.module is None:
                continue
            root = node.module.split(".")[0]
            roots.add(root)
    return roots


class TestFrontendLogicFree:
    """Frontend files must not contain business logic."""

    @pytest.mark.parametrize("filepath", FRONTEND_FILES)
    def test_imports_are_allowlisted(self, filepath: str) -> None:
        """Every import in a frontend file must be on the allowlist."""
        full_path = _plugin_root / filepath
        if not full_path.exists():
            pytest.skip(f"{filepath} does not exist")

        actual_imports = _extract_import_roots(full_path)
        allowed = ALLOWED_IMPORTS.get(filepath, set())

        # dh_core is always allowed — it's the target import surface.
        allowed = allowed | {"dh_core"}

        violations = actual_imports - allowed
        # Filter out empty strings (relative imports)
        violations = {v for v in violations if v}
        assert not violations, (
            f"{filepath} imports non-allowlisted modules: {sorted(violations)}.\n"
            f"Allowed: {sorted(allowed)}.\n"
            f"Business logic imports must go through dh_core.operations."
        )

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

"""Assert frontend import roots stay within their declared allowlists.

This AST check guards the frontend dependency architecture: an unapproved
import root cannot enter a declared frontend. It does not establish that the
file has no inline business logic or that broad permitted roots contain none.

"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

# Ensure plugin root resolves relative paths.
_plugin_root = Path(__file__).resolve().parent.parent

#: Frontend files whose import roots are bounded by ``ALLOWED_IMPORTS``.
FRONTEND_FILES: list[str] = [
    "sam_schema/cli.py",
    "sam_schema/server.py",
    "sam_schema/server_ledger_routing.py",
    "sam_schema/server_backend.py",
    "sam_schema/server_plan_ops.py",
    "sam_schema/server_task_ops.py",
    "sam_schema/server_active_task.py",
    "backlog_core/server.py",
]

#: Allowed import roots for each frontend file.
#: During the transition, frontends still import from legacy modules.
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
    "sam_schema/server.py": {"__future__", "typing", "fastmcp", "mcp", "pydantic", "dh_core", "sam_schema"},
    "sam_schema/server_ledger_routing.py": {
        "__future__",
        "collections",
        "collections.abc",
        "typing",
        "fastmcp",
        "dh_core",
        "sam_schema",
    },
    "sam_schema/server_backend.py": {"__future__", "typing", "fastmcp", "backlog_core", "dh_core", "sam_schema"},
    "sam_schema/server_plan_ops.py": {
        "__future__",
        "json",
        "pathlib",
        "typing",
        "tiktoken",
        "fastmcp",
        "dh_core",
        "sam_schema",
    },
    "sam_schema/server_task_ops.py": {"__future__", "fastmcp", "dh_core", "sam_schema"},
    "sam_schema/server_active_task.py": {"__future__", "fastmcp", "dh_core", "sam_schema"},
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
        "fastmcp_tasks",
        "mcp",
        "pydantic",
        "ruamel",
        "github",
        "dh_core",
        "backlog_core",
        "agent_profile",
        "progressive_markdown",
    },
}


#: Specific forbidden regex patterns per file (regression guard).
#: Grows as logic is extracted. Each entry is (filepath, pattern, description).
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


class TestFrontendImportRoots:
    """Frontend import roots remain within the declared architecture boundary."""

    @pytest.mark.parametrize("filepath", FRONTEND_FILES)
    def test_import_roots_are_allowlisted(self, filepath: str) -> None:
        """Every absolute import root in a frontend file is declared."""
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
            "Frontend import roots must be declared in ALLOWED_IMPORTS."
        )

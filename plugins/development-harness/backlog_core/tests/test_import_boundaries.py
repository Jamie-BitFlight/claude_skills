"""Import-order regressions for development-harness module boundaries."""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path


def test_operations_imports_before_server_without_cycle() -> None:
    """The operations-first import order completes in a fresh interpreter."""
    plugin_dir = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "-c", "import dh_core.operations; import backlog_core.server"],
        cwd=plugin_dir,
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def test_github_context_backend_does_not_import_backlog_core() -> None:
    """The standalone context backend honors its declared dependency boundary."""
    plugin_dir = Path(__file__).resolve().parents[2]
    path = plugin_dir / "sam_schema/core/backends/github_context_backend.py"
    violations: list[str] = []

    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            violations.extend(
                alias.name
                for alias in node.names
                if alias.name == "backlog_core" or alias.name.startswith("backlog_core.")
            )
        elif (
            isinstance(node, ast.ImportFrom)
            and node.module
            and (node.module == "backlog_core" or node.module.startswith("backlog_core."))
        ):
            violations.append(node.module)

    assert violations == []


def test_github_context_backend_uses_shared_client_factory() -> None:
    """The context backend retains proxy, API-root, and timeout configuration."""
    plugin_dir = Path(__file__).resolve().parents[2]
    path = plugin_dir / "sam_schema/core/backends/github_context_backend.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    imports_factory = any(
        isinstance(node, ast.ImportFrom)
        and node.module == "github_client"
        and any(alias.name == "make_github_client" for alias in node.names)
        for node in ast.walk(tree)
    )
    direct_constructors = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "Github"
    ]

    assert imports_factory
    assert direct_constructors == []

#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "typer>=0.27.0",
#   "pytest>=9.1.1",
# ]
#
# [tool.ty.environment]
# extra-paths = ["."]
# ///
"""Tests for validate_pep723.py rule selection.

Covers the two conditions that decide between Rule 2 (package module) and
Rule 3 (standalone PEP 723 script).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from validate_pep723 import UV_SHEBANG, determine_applicable_rule, is_part_of_package

RULE_PACKAGE_EXECUTABLE = 2
RULE_UV_SCRIPT = 3

SCRIPT_BODY = f"""{UV_SHEBANG}
# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx>=0.28.1"]
# ///
import httpx
"""


@pytest.fixture
def distribution(tmp_path: Path) -> Path:
    """Create a project root that declares a distribution.

    Args:
        tmp_path: Per-test temporary directory.

    Returns:
        The project root path.
    """
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "demo"\n')
    return tmp_path


def write_script(path: Path) -> Path:
    """Write an executable PEP 723 script with an external dependency.

    Args:
        path: Destination file path.

    Returns:
        The path written.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(SCRIPT_BODY, encoding="utf-8")
    path.chmod(0o755)
    return path


def test_script_beside_pyproject_is_not_part_of_a_package(distribution: Path) -> None:
    """A loose script is not a package module just because an ancestor declares a distribution."""
    script = write_script(distribution / "scripts" / "tool.py")
    assert is_part_of_package(script) is False


def test_module_with_init_is_part_of_a_package(distribution: Path) -> None:
    """A module inside an __init__.py directory of a distribution is a package module."""
    package = distribution / "demo"
    package.mkdir()
    (package / "__init__.py").write_text("")
    module = write_script(package / "cli.py")
    assert is_part_of_package(module) is True


def test_src_layout_namespace_module_is_part_of_a_package(distribution: Path) -> None:
    """A namespace module below the conventional src root needs no __init__.py."""
    module = write_script(distribution / "src" / "acme" / "tools" / "cli.py")
    assert is_part_of_package(module) is True


def test_configured_flat_namespace_module_is_part_of_a_package(distribution: Path) -> None:
    """Explicit setuptools discovery identifies a flat namespace without __init__.py."""
    (distribution / "pyproject.toml").write_text(
        '[project]\nname = "demo"\n[tool.setuptools.packages.find]\ninclude = ["acme.*"]\n', encoding="utf-8"
    )
    module = write_script(distribution / "acme" / "tools" / "cli.py")
    assert is_part_of_package(module) is True


def test_empty_setuptools_find_does_not_swallow_loose_script(distribution: Path) -> None:
    """Default-root discovery alone is not enough to classify scripts as packages."""
    (distribution / "pyproject.toml").write_text(
        '[project]\nname = "demo"\n[tool.setuptools.packages.find]\n', encoding="utf-8"
    )
    script = write_script(distribution / "tool.py")
    assert is_part_of_package(script) is False


def test_setuptools_find_respects_where(distribution: Path) -> None:
    """A configured discovery root includes namespaces below it and excludes siblings."""
    (distribution / "pyproject.toml").write_text(
        '[project]\nname = "demo"\n[tool.setuptools.packages.find]\nwhere = ["lib"]\n', encoding="utf-8"
    )
    module = write_script(distribution / "lib" / "acme" / "tools" / "cli.py")
    sibling = write_script(distribution / "acme" / "tools" / "cli.py")
    assert is_part_of_package(module) is True
    assert is_part_of_package(sibling) is False


def test_setuptools_find_respects_exclude(distribution: Path) -> None:
    """An excluded namespace does not receive project-environment Rule 2."""
    (distribution / "pyproject.toml").write_text(
        '[project]\nname = "demo"\n[tool.setuptools.packages.find]\nwhere = ["src"]\nexclude = ["acme.tools.*"]\n',
        encoding="utf-8",
    )
    module = write_script(distribution / "src" / "acme" / "tools" / "internal" / "cli.py")
    assert is_part_of_package(module) is False


def test_src_namespace_module_without_pep723_selects_package_rule(distribution: Path) -> None:
    """A src-layout namespace module receives package dependencies through Rule 2."""
    module = distribution / "src" / "acme" / "tools" / "cli.py"
    module.parent.mkdir(parents=True)
    module.write_text("#!/usr/bin/env python3\nimport httpx\n", encoding="utf-8")
    module.chmod(0o755)
    rule, _reason, _evaluations = determine_applicable_rule(module, module.read_text())
    assert rule == RULE_PACKAGE_EXECUTABLE


def test_standalone_script_selects_the_uv_rule(distribution: Path) -> None:
    """A standalone PEP 723 script with external imports selects Rule 3, not Rule 2."""
    script = write_script(distribution / "scripts" / "tool.py")
    rule, _reason, _evaluations = determine_applicable_rule(script, script.read_text())
    assert rule == RULE_UV_SCRIPT


def test_pep723_metadata_outranks_package_membership(distribution: Path) -> None:
    """PEP 723 metadata wins over package membership, because uv resolves from the block."""
    package = distribution / "demo"
    package.mkdir()
    (package / "__init__.py").write_text("")
    script = write_script(package / "tool.py")
    rule, _reason, _evaluations = determine_applicable_rule(script, script.read_text())
    assert rule == RULE_UV_SCRIPT


def test_package_module_without_pep723_selects_the_package_rule(distribution: Path) -> None:
    """An executable package module carrying no PEP 723 block stays on Rule 2."""
    package = distribution / "demo"
    package.mkdir()
    (package / "__init__.py").write_text("")
    module = package / "cli.py"
    module.write_text("#!/usr/bin/env python3\nimport httpx\n")
    module.chmod(0o755)
    rule, _reason, _evaluations = determine_applicable_rule(module, module.read_text())
    assert rule == RULE_PACKAGE_EXECUTABLE

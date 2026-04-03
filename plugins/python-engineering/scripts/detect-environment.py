#!/usr/bin/env python3
"""Detect Python project environment and determine typing lane."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def detect_python_version(project_root: Path) -> str:
    """Extract requires-python from pyproject.toml.

    Returns:
        Version constraint string, or "unknown" if not found.
    """
    pyproject = project_root / "pyproject.toml"
    if not pyproject.exists():
        return "unknown"
    content = pyproject.read_text()
    for line in content.splitlines():
        if "requires-python" in line:
            # Simple extraction
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return "unknown"


def has_dependency(project_root: Path, name: str) -> bool:
    """Check if a dependency exists in pyproject.toml or uv.lock.

    Returns:
        True if the dependency name is found in pyproject.toml or uv.lock.
    """
    pyproject = project_root / "pyproject.toml"
    if pyproject.exists() and name.lower() in pyproject.read_text().lower():
        return True
    uv_lock = project_root / "uv.lock"
    return bool(uv_lock.exists() and name.lower() in uv_lock.read_text().lower())


def detect_type_checker(project_root: Path) -> str:
    """Detect the active type checker from pre-commit config.

    Returns:
        Name of the detected type checker: "ty", "mypy", or "pyright". Defaults to "ty".
    """
    # Check .pre-commit-config.yaml first
    pre_commit = project_root / ".pre-commit-config.yaml"
    if pre_commit.exists():
        content = pre_commit.read_text()
        if "id: ty" in content:
            return "ty"
        if "id: mypy" in content:
            return "mypy"
        if "id: pyright" in content or "id: basedpyright" in content:
            return "pyright"
    return "ty"  # default


def determine_lane(py_version: str, has_pydantic: bool, has_hypothesis: bool) -> str:
    """Determine the typing lane from environment.

    Returns:
        Lane identifier string such as "lane-b-311-stdlib" or "lane-c-311-pydantic".
    """
    if "3.10" in py_version and "3.11" not in py_version:
        return "lane-a-310-stdlib"
    if has_pydantic and has_hypothesis:
        return "lane-d-311-pydantic-hypothesis"
    if has_pydantic:
        return "lane-c-311-pydantic"
    return "lane-b-311-stdlib"


def main() -> None:
    """Detect environment and print JSON summary of Python version, dependencies, and typing lane."""
    project_root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path()
    py_version = detect_python_version(project_root)
    has_pydantic = has_dependency(project_root, "pydantic")
    has_hypothesis = has_dependency(project_root, "hypothesis")
    type_checker = detect_type_checker(project_root)
    lane = determine_lane(py_version, has_pydantic, has_hypothesis)

    result = {
        "project_root": str(project_root.resolve()),
        "requires_python": py_version,
        "has_pydantic": has_pydantic,
        "has_hypothesis": has_hypothesis,
        "type_checker": type_checker,
        "typing_lane": lane,
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

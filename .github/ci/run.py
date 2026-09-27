# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Execute planned CI work using argv, never interpolated shell fragments."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import PurePosixPath

# The plan schema version this runner reads; .github/ci/plan.py emits the same value.
PLAN_VERSION = 2
HOOKS = ("ruff", "ruff-format", "biome-check", "markdownlint-cli2", "shellcheck", "shell-fmt-go")


def paths_from(value: object) -> list[str]:
    """Reject empty/unsafe target lists instead of accidentally scanning everything.

    Returns:
        A validated, non-empty argument list.
    """
    if not isinstance(value, list) or not value or not all(isinstance(path, str) for path in value):
        raise ValueError("A non-empty list of target paths is required")
    for path in value:
        parsed = PurePosixPath(path)
        if (
            not path
            or parsed.is_absolute()
            or ".." in parsed.parts
            or path.startswith("-")
            or parsed == PurePosixPath()
        ):
            raise ValueError(f"Unsafe target path: {path!r}")
    return value


def pytest_command(shard: dict[str, object]) -> list[str]:
    """Build a pytest shard's command: its plugin runner, or root pytest for repository tests.

    Returns:
        The child executable and arguments, without shell quoting/interpolation.

    Raises:
        TypeError: If the runner or marker is not a string.
        ValueError: If the runner or paths are not safe relative paths, or a runner shard names paths.
    """
    runner = shard.get("runner", "")
    if not isinstance(runner, str):
        raise TypeError("The pytest runner must be a string")
    if runner:
        paths_from([runner])
    args = ["uv", "run", "--locked", "--script", runner] if runner else ["uv", "run", "--locked", "pytest"]
    marker = shard.get("marker", "")
    if not isinstance(marker, str):
        raise TypeError("The pytest marker must be a string")
    if marker:
        args.extend(["-m", marker, "-v"])
    paths = shard.get("paths", [])
    if runner:
        if paths != []:
            raise ValueError(f"The plugin runner owns its test paths: {runner}")
        return args
    return [*args, *paths_from(paths)]


def command(operation: str, plan: dict[str, object], shard: dict[str, object], hook: str | None = None) -> list[str]:
    """Build the exact child command, preserving pytest's configured defaults.

    Returns:
        The child executable and arguments, without shell quoting/interpolation.
    """
    if operation == "pytest":
        return pytest_command(shard)
    if operation == "skilllint":
        return ["uvx", "skilllint@latest", "check", *paths_from(plan.get("validation_paths"))]
    if operation != "prek" or (hook is not None and hook not in HOOKS):
        raise ValueError(f"Unsupported CI operation/hook: {operation!r}/{hook!r}")
    args = ["uv", "run", "--locked", "prek", "run"]
    if hook:
        args.append(hook)
    # Hygiene includes cross-file invariants: deleting a target can break an
    # unchanged symlink. Only explicitly named language hooks are file-local.
    if hook is None or plan.get("lint_all") is True:
        args.append("--all-files")
    elif plan.get("lint_all") is False:
        refs = [plan.get("base"), plan.get("head")]
        if not all(isinstance(ref, str) and re.fullmatch(r"[0-9a-fA-F]{40}", ref) for ref in refs):
            raise ValueError("Changed-file linting requires immutable comparison SHAs")
        args.extend(["--from-ref", str(refs[0]), "--to-ref", str(refs[1])])
    else:
        raise ValueError("The plan must explicitly select full or changed-file linting")
    return [*args, "--show-diff-on-failure"]


def main() -> None:
    """Replace this process so every child failure, including pytest exit 5, votes."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("pytest", "prek", "skilllint"))
    parser.add_argument("--hook", choices=HOOKS)
    args = parser.parse_args()
    plan = json.loads(os.environ["CI_PLAN"])
    version = plan.get("version") if isinstance(plan, dict) else None
    if version != PLAN_VERSION:
        raise ValueError(f"Expected CI plan version {PLAN_VERSION}, received {version}")
    shard = json.loads(os.environ.get("CI_SHARD", "{}"))
    if not isinstance(shard, dict):
        raise TypeError("Expected a matrix object")
    argv = command(args.operation, plan, shard, args.hook)
    print(json.dumps({"command": argv}, separators=(",", ":")), flush=True)
    os.execvp(argv[0], argv)


if __name__ == "__main__":
    main()

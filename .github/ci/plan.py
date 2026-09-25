# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Derive CI work from the event diff and plugin-owned pytest runners.

The bootstrap deliberately uses only the standard library: selecting work must
not install the repository's application and test dependencies.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import tomllib
from pathlib import Path, PurePosixPath
from typing import TypedDict


class Shard(TypedDict):
    """One pytest invocation, with an optional marker override."""

    name: str
    paths: list[str]
    marker: str
    runner: str


class Matrix(TypedDict):
    """GitHub Actions include-only matrix."""

    include: list[Shard]


class Plan(TypedDict):
    """Versioned, JSON-serializable selection shared by jobs and their runner."""

    version: int
    full_tests: bool
    lint_all: bool
    reasons: list[str]
    base: str
    head: str
    unit_matrix: Matrix
    integration_matrix: Matrix
    validation_paths: list[str]
    checks: dict[str, bool]
    allowed_skips: str


# A change to any of these can affect files beyond the changed directory.
LINT_CONFIG_NAMES = frozenset({
    ".pre-commit-config.yaml",
    "pyproject.toml",
    "uv.lock",
    ".python-version",
    "biome.json",
    "biome.jsonc",
    "ruff.toml",
    ".ruff.toml",
    "ty.toml",
    ".markdownlint.json",
    ".markdownlint.jsonc",
    ".markdownlint.yaml",
    ".markdownlint.yml",
    ".markdownlint-cli2.jsonc",
    ".markdownlint-cli2.yaml",
    ".markdownlint-cli2.yml",
    ".markdownlint-cli2.json",
    ".markdownlint-cli2.cjs",
    ".markdownlint-cli2.mjs",
    ".markdownlint.cjs",
    ".shellcheckrc",
    ".editorconfig",
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    ".gitignore",
    ".gitattributes",
})
LANGUAGE_SUFFIXES = {
    "lint-python": {".py", ".pyi"},
    "lint-js": {".js", ".jsx", ".cjs", ".mjs", ".ts", ".tsx", ".mts", ".cts", ".json", ".jsonc", ".css"},
    "lint-markdown": {".md", ".markdown", ".mdown", ".mkd"},
    "lint-shell": {".sh", ".bash", ".bats", ".dash", ".ksh", ".zsh"},
}


def plugin_owner(path: str) -> str | None:
    """Return the owning plugin directory, not its installation alias.

    Returns:
        Directory ownership, or None for repository-global paths.
    """
    parts = PurePosixPath(path).parts
    return parts[1] if len(parts) > 1 and parts[0] == "plugins" else None


def under(path: str, directory: str) -> bool:
    """Compare path components instead of matching coincidental prefixes.

    Returns:
        Whether the path is at or below the given directory.
    """
    return PurePosixPath(path).is_relative_to(PurePosixPath(directory))


def valid_path(value: str) -> str:
    """Validate a repository-relative path before using it as an argument.

    Returns:
        The normalized relative POSIX path.
    """
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts or value.startswith("-") or path == PurePosixPath():
        raise ValueError(f"Not a repository-relative path: {value!r}")
    return path.as_posix()


def read_pytest_config(root: Path) -> tuple[dict[str, list[str]], list[str]]:
    """Discover plugin runners and repository-owned test roots."""
    config = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    options = config["tool"]["pytest"]["ini_options"]
    testpaths = options["testpaths"]
    if not isinstance(testpaths, list) or not testpaths:
        raise ValueError("repository pytest testpaths must be a non-empty list")
    suites: dict[str, list[str]] = {"global": []}
    for value in testpaths:
        path = valid_path(value)
        if plugin_owner(path):
            raise ValueError(f"plugin test topology belongs in run_pytests.py, not root testpaths: {path}")
        if not (root / path).exists():
            raise ValueError(f"Configured testpath does not exist: {path}")
        suites["global"].append(path)
    for runner in sorted((root / "plugins").glob("*/run_pytests.py")):
        suites[runner.parent.name] = [runner.relative_to(root).as_posix()]
    imports = [valid_path(path) for path in options.get("pythonpath", []) if plugin_owner(path)]
    return suites, imports

def git(root: Path, *args: str) -> bytes:
    """Run a bounded, read-only Git command without a shell.

    Returns:
        The command's complete standard output as bytes.
    """
    executable = shutil.which("git")
    if executable is None:
        raise FileNotFoundError("Git executable is unavailable")
    return subprocess.run([executable, "-C", str(root), *args], check=True, capture_output=True, timeout=60).stdout


def changed_paths(root: Path, event: str, base: str, head: str) -> tuple[list[str] | None, str, str, str]:
    """Return PR-only changes, or an explicit full-run fallback reason.

    None means a full run, never an empty diff. Disabling rename detection
    deliberately includes both the old and new owners. NUL records preserve
    whitespace/newlines in filenames and avoid API path-filter limits.

    Returns:
        Changed paths or None for full validation, resolved refs, and a reason.
    """
    if event != "pull_request":
        return None, "", "", f"{event}: full regression run"
    if not all(re.fullmatch(r"[0-9a-fA-F]{40}", ref) for ref in (base, head)):
        return None, "", "", "Missing immutable PR comparison SHAs: full regression run"
    try:
        merge_base = git(root, "merge-base", base, head).decode("ascii").strip()
        data = git(root, "diff", "--name-only", "--no-renames", "-z", merge_base, head, "--")
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
        return None, "", "", f"PR comparison unavailable ({type(exc).__name__}): full regression run"
    return [os.fsdecode(path) for path in data.split(b"\0") if path], merge_base, head, "PR merge-base diff"


def local_input(path: str) -> bool:
    """Identify inputs with an explicit plugin or documentation boundary.

    Returns:
        Whether a path has a known local scope.
    """
    if plugin_owner(path):
        return True
    parsed = PurePosixPath(path)
    return parsed.suffix.lower() in {".md", ".rst", ".txt"} and (
        len(parsed.parts) == 1 or parsed.parts[0] in {"docs", "rules", "research"}
    )


def shared_source(path: str, imports: list[str]) -> bool:
    """Recognize Python providers visible to other suites via global pythonpath.

    Returns:
        Whether the change requires testing shared Python consumers.
    """
    name = PurePosixPath(path).name
    if name == "conftest.py":
        return True
    is_test = name.startswith("test_") or name.endswith("_test.py")
    return (
        not is_test
        and PurePosixPath(path).suffix in {".py", ".pyi"}
        and any(under(path, directory) for directory in imports)
    )


def marketplace_version_only(root: Path, base: str, head: str) -> bool:
    """Check that only marketplace metadata.version changed, not its registry.

    Returns:
        Whether the two immutable manifests differ only in their version field.
    """
    if not all(re.fullmatch(r"[0-9a-fA-F]{40}", ref) for ref in (base, head)):
        return False
    values = []
    try:
        for ref in (base, head):
            document = json.loads(git(root, "show", f"{ref}:.claude-plugin/marketplace.json"))
            if not isinstance(document, dict) or not isinstance(document.get("metadata"), dict):
                return False
            if not isinstance(document["metadata"].get("version"), str):
                return False
            del document["metadata"]["version"]
            values.append(document)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError, ValueError):
        return False
    return values[0] == values[1]


def build_plan(
    root: Path, paths: list[str] | None, base: str = "", head: str = "", reason: str = "Explicit selection"
) -> Plan:
    """Select work, preserving global guards and conservative shared fallbacks.

    Returns:
        The versioned selection, including exact matrix roots and permitted skips.
    """
    suites, imports = read_pytest_config(root)
    changed = paths or []
    owners = {owner for path in changed if (owner := plugin_owner(path))}
    version_only = ".claude-plugin/marketplace.json" in changed and marketplace_version_only(root, base, head)
    shared = [
        path
        for path in changed
        if (not local_input(path) or PurePosixPath(path).name in LINT_CONFIG_NAMES)
        and not (version_only and path == ".claude-plugin/marketplace.json")
    ]
    full_checks = paths is None or bool(shared)
    full_tests = full_checks or any(shared_source(path, imports) for path in changed)
    reasons = [reason]
    if version_only:
        reasons.append("Marketplace metadata.version-only change: retain targeted selection")
    reasons.extend(f"Shared/configuration input: {path}" for path in shared)
    reasons.extend(f"Shared Python import/fixture input: {path}" for path in changed if shared_source(path, imports))
    unit: list[Shard] = [
        {"name": owner, "paths": ([] if owner != "global" else targets), "marker": "", "runner": (targets[0] if owner != "global" else "")}
        for owner, targets in sorted(suites.items())
        if full_tests or owner == "global" or owner in owners
    ]
    integration: list[Shard] = []
    if full_tests or "development-harness" in owners:
        integration.append({
            "name": "development-harness", "paths": ["plugins/development-harness/tests"],
            "marker": "integration and not research_vault", "runner": "plugins/development-harness/run_pytests.py",
        })
    if full_tests or any(under(path, "research") for path in changed):
        integration.append({
            "name": "research-backlinks", "paths": ["tests/research_backlinks"],
            "marker": "integration and not research_vault",
        })
    if full_tests:
        integration.append({
            "name": "rebase-publication", "paths": ["tests/test_rebase_publication_identity.py"],
            "marker": "integration", "runner": "",
        })
    validation = ["plugins", ".claude"] if full_checks else [f"plugins/{owner}" for owner in sorted(owners)]
    validation = [path for path in validation if (root / path).is_dir()]
    # Extensionless files may be classified from shebangs by prek. Do not miss them
    # by trying to duplicate identify's complete file-type classifier here.
    extensionless = any(not PurePosixPath(path).suffix for path in changed)
    checks = {
        job: full_checks or extensionless or any(PurePosixPath(path).suffix.lower() in suffixes for path in changed)
        for job, suffixes in LANGUAGE_SUFFIXES.items()
    }
    checks.update({
        "typecheck-ty": full_checks
        or extensionless
        or any(PurePosixPath(path).suffix in {".py", ".pyi"} for path in changed),
        "audit-dependencies": True,
        "validate-plugins": bool(validation),
        "manifest-sync": full_checks or bool(owners) or ".claude-plugin/marketplace.json" in changed,
        "file-hygiene": True,
        "test-python": bool(unit),
        "test-cross-backend": full_tests or "development-harness" in owners,
        "test-integration": bool(integration),
    })
    allowed_skips = ",".join(sorted(job for job, selected_job in checks.items() if not selected_job))
    checks["research-validation"] = full_tests or any(under(path, "research") for path in changed)
    return {
        "version": 1,
        "full_tests": full_tests,
        "lint_all": full_checks,
        "reasons": reasons,
        "base": base,
        "head": head,
        "unit_matrix": {"include": unit},
        "integration_matrix": {"include": integration},
        "validation_paths": validation,
        "checks": checks,
        "allowed_skips": allowed_skips,
    }


def main() -> None:
    """Emit one compact plan to stdout and GitHub's job-output channel."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--event", default=os.environ.get("GITHUB_EVENT_NAME", "workflow_dispatch"))
    parser.add_argument("--base", default=os.environ.get("CI_BASE_SHA", ""))
    parser.add_argument("--head", default=os.environ.get("CI_HEAD_SHA", ""))
    args = parser.parse_args()
    paths, base, head, reason = changed_paths(args.root, args.event, args.base, args.head)
    plan = build_plan(args.root, paths, base, head, reason)
    encoded = json.dumps(plan, separators=(",", ":"))
    print(encoded)
    if output := os.environ.get("GITHUB_OUTPUT"):
        with Path(output).open("a", encoding="utf-8") as stream:
            stream.write(f"plan={encoded}\n")
    if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        with Path(summary).open("a", encoding="utf-8") as stream:
            stream.write("## CI selection\n\n")
            stream.write("\n".join(f"- {item}" for item in plan["reasons"]))
            stream.write("\n\nTest shards: " + ", ".join(shard["name"] for shard in plan["unit_matrix"]["include"]))
            stream.write("\n\nPlanned skips: " + (plan["allowed_skips"] or "none") + "\n")


if __name__ == "__main__":
    main()

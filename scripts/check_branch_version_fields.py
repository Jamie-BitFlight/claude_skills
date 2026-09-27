#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# ///
"""Fail when a branch changes a plugin or marketplace `version` field.

Versions are assigned only on main, by .github/workflows/bump-marketplace.yml.
Its `repair` step treats the latest commit that changed a manifest's version as
that plugin's last bump, so a version edited on a branch (including a downgrade
from a conflict resolution) would ship uncorrected.

A manifest's identity is its kind (harness directory and file name, e.g.
`.claude-plugin/plugin.json`) plus its `name`, not its path. For every manifest
at --head whose identity existed anywhere at the merge base of --base and
--head, each version field (`version`, `metadata.version`) must equal its merge
base value. Moves, renamed directories and rewrites therefore do not matter,
and bumps that reached main after the branch point are not attributed to the
branch. An identity absent at the merge base is a new plugin: any version is
allowed. A removed identity needs no check.

Known limit: a PR that changes a plugin's `name` and its version together is
treated as adding a new plugin, so the version change is not reported.

Exit codes: 0 when no version field changed, 1 when one did, 2 on a git error.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys

MANIFEST_SUFFIXES = ("/plugin.json", ".plugin.json", "/marketplace.json")
VERSION_PATHS = (("version",), ("metadata", "version"))
GIT = shutil.which("git") or "git"

Identity = tuple[str, object]
Versions = dict[str, object]


def git(*args: str) -> str:
    """Run one git command in the current repository.

    Returns:
        The command's stdout.
    """
    return subprocess.run([GIT, *args], check=True, capture_output=True, text=True).stdout


def manifests(revision: str, paths: list[str] | None = None) -> dict[str, tuple[Identity, Versions]]:
    """Read the identity and version fields of manifests at one revision.

    Args:
        revision: Revision to read.
        paths: Manifest paths to read; every manifest in the tree when None.

    Returns:
        Path to (identity, version fields) for each manifest that parses as a JSON object.
    """
    if paths is None:
        tree = git("ls-tree", "-r", "--name-only", "-z", revision).split("\0")
        paths = [path for path in tree if path.endswith(MANIFEST_SUFFIXES)]
    found: dict[str, tuple[Identity, Versions]] = {}
    for path in paths:
        try:
            data = json.loads(git("show", f"{revision}:{path}"))
        except json.JSONDecodeError:
            continue  # Not a manifest this check can identify; skilllint validates manifest syntax.
        if not isinstance(data, dict):
            continue
        fields: Versions = {}
        for keys in VERSION_PATHS:
            value: object = data
            for key in keys:
                value = value.get(key) if isinstance(value, dict) else None
            if value is not None:
                fields[".".join(keys)] = value
        found[path] = (("/".join(path.split("/")[-2:]), data.get("name")), fields)
    return found


def main() -> int:
    """Report every version field the branch changed on a plugin that existed at the fork point.

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", required=True, help="Target branch revision, e.g. the PR base SHA.")
    parser.add_argument("--head", required=True, help="Branch revision, e.g. the PR head SHA.")
    args = parser.parse_args()
    try:
        fork_point = git("merge-base", args.base, args.head).strip()
        base: dict[Identity, list[Versions]] = {}
        for identity, fields in manifests(fork_point).values():
            base.setdefault(identity, []).append(fields)
        # An unchanged file cannot have changed its versions, so only changed or added files are read at head.
        changed = git("diff", "--name-only", "--no-renames", "-z", "--diff-filter=AM", fork_point, args.head)
        head = manifests(args.head, [path for path in changed.split("\0") if path.endswith(MANIFEST_SUFFIXES)])
    except subprocess.CalledProcessError as error:
        sys.stderr.write(error.stderr)
        return 2
    offences = [
        f"{path}: {key} {base[identity][0].get(key)!r} -> {fields.get(key)!r}"
        for path, (identity, fields) in sorted(head.items())
        if identity in base and fields not in base[identity]
        for key in sorted(base[identity][0].keys() | fields.keys())
        if base[identity][0].get(key) != fields.get(key)
    ]
    if not offences:
        print("OK: no plugin or marketplace version field changed on this branch.")
        return 0
    sys.stderr.write(
        "Version fields are assigned on main by bump-marketplace.yml; restore these to the"
        f" values at {fork_point[:12]}:\n"
    )
    for offence in offences:
        sys.stderr.write(f"  - {offence}\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())

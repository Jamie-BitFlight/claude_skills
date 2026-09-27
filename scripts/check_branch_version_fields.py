#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# ///
"""Fail when a branch changes a plugin or marketplace `version` field.

Versions are assigned only on main, by .github/workflows/bump-marketplace.yml.
Its `repair` step treats the latest commit that changed a manifest's version as
that plugin's last bump, so a version edited on a branch (including a downgrade
from a conflict resolution) would ship uncorrected.

Compares each manifest at the merge base of --base and --head with --head, so
changes that reached main after the branch point are not attributed to the
branch. A manifest moved by the branch (e.g. a renamed plugin directory) is
compared with its old path, using git's rename detection; manifests added or
deleted by the branch are not checked.

Exit codes: 0 when no version field changed, 1 when one did, 2 on a git error.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from typing import Any

MANIFESTS = (":(glob)**/plugin.json", ":(glob)**/*.plugin.json", ":(glob)**/marketplace.json")
VERSION_PATHS = (("version",), ("metadata", "version"))
GIT = shutil.which("git") or "git"


def git(*args: str) -> str:
    """Run one git command in the current repository.

    Returns:
        The command's stdout.
    """
    return subprocess.run([GIT, *args], check=True, capture_output=True, text=True).stdout


def versions(revision: str, path: str) -> dict[str, Any]:
    """Read every version field of one manifest at one revision.

    Returns:
        Dotted key path to value, for each version field present.
    """
    data = json.loads(git("show", f"{revision}:{path}"))
    found: dict[str, Any] = {}
    for keys in VERSION_PATHS:
        value: Any = data
        for key in keys:
            value = value.get(key) if isinstance(value, dict) else None
        if value is not None:
            found[".".join(keys)] = value
    return found


def main() -> int:
    """Report every version field the branch changed.

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", required=True, help="Target branch revision, e.g. the PR base SHA.")
    parser.add_argument("--head", required=True, help="Branch revision, e.g. the PR head SHA.")
    args = parser.parse_args()
    try:
        fork_point = git("merge-base", args.base, args.head).strip()
        status = git("diff", "--name-status", "-M", "--diff-filter=MR", fork_point, args.head, "--", *MANIFESTS)
        # "M\tpath" or "R<score>\told\tnew": compare the old path at the fork point with the head path.
        pairs = [(fields[1], fields[-1]) for fields in (line.split("\t") for line in status.splitlines())]
        offences = [
            f"{path}: {key} {before.get(key)!r} -> {after.get(key)!r}"
            for old_path, path in pairs
            for before, after in [(versions(fork_point, old_path), versions(args.head, path))]
            for key in sorted(before.keys() | after.keys())
            if before.get(key) != after.get(key)
        ]
    except subprocess.CalledProcessError as error:
        sys.stderr.write(error.stderr)
        return 2
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

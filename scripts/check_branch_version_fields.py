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
compared with its old path. git's rename detection finds most moves; a move
rewritten past its similarity threshold shows as a delete plus an add, so an
added manifest is also paired with a deleted one of the same kind (e.g.
`.claude-plugin/plugin.json`) that has the same `name`, or with the only
deleted one of that kind when it is also the only added one. Other added or
deleted manifests are new or removed plugins and are not checked.

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


def manifest(revision: str, path: str) -> object:
    """Parse one manifest at one revision.

    Returns:
        The decoded JSON document.
    """
    return json.loads(git("show", f"{revision}:{path}"))


def kind(path: str) -> str:
    """Return a manifest's harness directory and file name, e.g. `.claude-plugin/plugin.json`.

    Returns:
        The last two path components.
    """
    return "/".join(path.split("/")[-2:])


def name(data: object) -> object:
    """Return a manifest's `name`, or None when it has none.

    Returns:
        The name value.
    """
    return data.get("name") if isinstance(data, dict) else None


def moved_pairs(fork_point: str, head: str, deleted: list[str], added: list[str]) -> list[tuple[str, str]]:
    """Pair manifests that a delete plus an add moved, by kind and name, else by a unique kind.

    Returns:
        (path at fork point, path at head) for each move found.
    """
    pairs: list[tuple[str, str]] = []
    gone = {path: name(manifest(fork_point, path)) for path in deleted}
    for path in added:
        same_kind = [old for old in gone if kind(old) == kind(path)]
        same_name = [old for old in same_kind if gone[old] == name(manifest(head, path))]
        unique = len(same_kind) == 1 and [new for new in added if kind(new) == kind(path)] == [path]
        match = same_name[:1] or (same_kind if unique else [])
        if match:
            pairs.append((match[0], path))
            del gone[match[0]]
    return pairs


def versions(revision: str, path: str) -> dict[str, Any]:
    """Read every version field of one manifest at one revision.

    Returns:
        Dotted key path to value, for each version field present.
    """
    data = manifest(revision, path)
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
        status = git("diff", "--name-status", "-M", "--diff-filter=MRAD", fork_point, args.head, "--", *MANIFESTS)
        # "M\tpath", "A\tpath", "D\tpath" or "R<score>\told\tnew".
        entries = [line.split("\t") for line in status.splitlines()]
        pairs = [(fields[1], fields[-1]) for fields in entries if fields[0][0] in "MR"]
        deleted = [fields[1] for fields in entries if fields[0] == "D"]
        added = [fields[1] for fields in entries if fields[0] == "A"]
        pairs += moved_pairs(fork_point, args.head, deleted, added)
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

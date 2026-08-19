#!/usr/bin/env python3
"""CI gate and retroactive audit for plugin.json version-bump drift.

Companion to ``auto_sync_manifests.py`` (the pre-commit hook). That hook only
inspects **staged** changes (``git diff --cached``), which is always empty in
a CI checkout -- nothing is ever staged there. A PR merged via GitHub's UI or
API never runs the local pre-commit hook either. Both gaps combined let PR
#3005 land a plugin content change with zero corresponding ``plugin.json``
version bump, and the marketplace cache -- keyed on that version -- kept
serving stale content indefinitely. See issue #3021.

Two modes:

``--check`` (CI gate, required check)
    Diffs *base-ref* against *head-ref* (a real base-vs-head tree comparison,
    not a staged-index comparison) and fails when any plugin with a changed
    file did not also raise its ``plugin.json`` version relative to
    *base-ref*. Newly added or fully deleted plugins are exempt -- there is
    no prior version to compare against. *head-ref* defaults to ``HEAD`` but
    should be passed explicitly (e.g. ``origin/$GITHUB_HEAD_REF``) on a
    GitHub Actions ``pull_request`` trigger, where the checked-out ``HEAD``
    is a synthetic merge commit rather than the PR's actual head commit.

``--audit`` (retroactive, report-only)
    Scans every plugin currently on disk, finds the most recent commit that
    changed its ``plugin.json`` version, and reports drift when any file
    under that plugin changed *after* that commit without a further bump.
    This is how a gap like #3021's -- already merged before this gate
    existed -- gets found without a manual ``git show`` investigation.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from auto_sync_manifests import (
    extract_version_from_json,
    parse_plugin_path,
    read_ref_json,
    resolve_base,
    run_git_command,
)


def plugins_with_diff(base_ref: str, head_ref: str = "HEAD") -> set[str]:
    """Return plugin directory names with any file changed between two refs.

    Args:
        base_ref: The git ref to diff against (e.g. a PR's merge-base with main).
        head_ref: The git ref representing the current state.

    Returns:
        Set of plugin directory names (the ``<name>`` in ``plugins/<name>/``)
        touched anywhere in the diff between the two refs.
    """
    output = run_git_command(["diff", "--name-only", f"{base_ref}...{head_ref}"])
    plugins: set[str] = set()
    for line in output.splitlines():
        parsed = parse_plugin_path(line.strip())
        if parsed:
            plugins.add(parsed["plugin"])
    return plugins


def check_version_bumps(base_ref: str, head_ref: str = "HEAD") -> list[str]:
    """Find plugins whose files changed between refs without a version bump.

    Args:
        base_ref: The git ref to diff against (e.g. the PR's merge-base with main).
        head_ref: The git ref representing the proposed merge state.

    Returns:
        Sorted list of plugin directory names that changed but whose
        ``plugin.json`` version at *head_ref* is not strictly greater than at
        *base_ref*. Plugins created or deleted within the diff are excluded --
        there is no prior version to compare against.
    """
    missing: list[str] = []
    for plugin_name in sorted(plugins_with_diff(base_ref, head_ref)):
        plugin_json_path = f"plugins/{plugin_name}/.claude-plugin/plugin.json"
        base_version = extract_version_from_json(read_ref_json(base_ref, plugin_json_path), ["version"])
        head_version = extract_version_from_json(read_ref_json(head_ref, plugin_json_path), ["version"])
        if base_version is None or head_version is None:
            continue  # plugin created or deleted in this diff -- no bump required
        if head_version <= base_version:
            missing.append(plugin_name)
    return missing


def find_last_version_bump_commit(plugin_json_relpath: str) -> str | None:
    """Find the most recent commit that changed plugin.json's version field.

    Args:
        plugin_json_relpath: Path to plugin.json, relative to the repo root.

    Returns:
        The commit SHA of the most recent version change. When the version was
        set once at file creation and never changed since, the creation
        (root) commit is returned -- it is still a valid drift baseline.
        Returns None only when plugin.json has no commit history at all.
    """
    commits = run_git_command(["log", "--format=%H", "--", plugin_json_relpath]).splitlines()
    for commit in commits:
        version = extract_version_from_json(read_ref_json(commit, plugin_json_relpath), ["version"])
        if version is None:
            continue

        # --verify --quiet: a root commit has no parent, so this exits non-zero --
        # --quiet suppresses git's "fatal: ... unknown revision" stderr for that
        # expected case (run_git_command forwards stderr on any non-zero exit).
        parent_sha = run_git_command(["rev-parse", "--verify", "--quiet", f"{commit}^"])
        if not parent_sha:
            return commit  # root commit -- version was set here, counts as the bump point

        parent_version = extract_version_from_json(read_ref_json(parent_sha, plugin_json_relpath), ["version"])
        if parent_version is None or version != parent_version:
            return commit

    return None


def audit_version_drift(plugins_root: Path) -> list[str]:
    """Find plugins whose content changed after their last recorded version bump.

    Assumes the current working directory is the repository root (true for
    every caller in this script -- git subcommands here rely on it). Plugin
    paths are always rebuilt as ``plugins/<name>/...`` strings rather than
    reused from *plugins_root* directly: ``git show ref:path`` -- unlike
    ``git log -- path`` or ``git diff -- path`` -- requires a repo-root-relative
    path and silently returns nothing for a filesystem-absolute one, so an
    absolute *plugins_root* (e.g. a pytest ``tmp_path`` fixture) would
    otherwise make every plugin look falsely un-bumped.

    Args:
        plugins_root: Path to the plugins/ directory (relative or absolute --
            only used to list plugin directory names, never passed to git).

    Returns:
        Sorted list of plugin directory names exhibiting drift -- i.e. a file
        under ``plugins/<name>/`` changed after the plugin's last version-bump
        commit, with no further bump since.
    """
    drifted: list[str] = []
    for plugin_dir in sorted(plugins_root.iterdir()):
        if not plugin_dir.is_dir():
            continue
        plugin_json_path = plugin_dir / ".claude-plugin" / "plugin.json"
        if not plugin_json_path.exists():
            continue

        plugin_name = plugin_dir.name
        rel_plugin_json = f"plugins/{plugin_name}/.claude-plugin/plugin.json"
        last_bump = find_last_version_bump_commit(rel_plugin_json)
        if last_bump is None:
            continue  # plugin.json has no commit history -- nothing to diff against

        changed = run_git_command(["diff", "--name-only", last_bump, "HEAD", "--", f"plugins/{plugin_name}"])
        if changed.strip():
            drifted.append(plugin_name)

    return drifted


def _run_check(base_ref_arg: str | None, head_ref_arg: str | None = None) -> int:
    """Run the CI version-bump gate and print the result.

    Args:
        base_ref_arg: Explicit base ref to diff against, or None to
            auto-resolve via ``resolve_base()`` (``origin/main`` -> ``main``).
        head_ref_arg: Explicit head ref to diff against, or None to use the
            checked-out working tree's ``HEAD``. On a GitHub Actions
            ``pull_request`` trigger, ``actions/checkout`` checks out a
            synthetic merge commit (base tip merged with the PR head) by
            default, not the PR's actual head commit -- diffing against that
            ``HEAD`` mixes in base-only changes that landed after the PR
            branch diverged. Callers on that trigger must pass the PR's real
            head ref explicitly (e.g. ``origin/${GITHUB_HEAD_REF}``, or
            ``github.event.pull_request.head.sha``).

    Returns:
        0 when every changed plugin bumped its version (or no base ref is
        needed because nothing changed); 1 when a bump is missing or no base
        ref is resolvable.
    """
    base_ref = base_ref_arg or resolve_base()
    if base_ref is None:
        sys.stderr.write("Error: no base ref resolvable (origin/main or main) -- pass --base-ref explicitly\n")
        return 1

    missing = check_version_bumps(base_ref, head_ref_arg or "HEAD")
    if not missing:
        print(f"OK: all changed plugins bumped plugin.json's version relative to {base_ref}")
        return 0

    sys.stderr.write("The following plugins changed but did not bump plugin.json's version:\n")
    for name in missing:
        sys.stderr.write(f"  - {name}\n")
    sys.stderr.write(
        "\nBump the version in plugins/<name>/.claude-plugin/plugin.json -- stage the plugin "
        "change and run `uv run --no-sync plugins/plugin-creator/scripts/auto_sync_manifests.py` "
        "locally (the pre-commit hook does this automatically), then push again.\n"
    )
    return 1


def _run_audit() -> int:
    """Run the retroactive drift audit and print results as compact JSON.

    This tool has no human operator -- every caller is an agent or CI script
    (see AGENTS.md "CLI and script output -- agent-only, never human-facing").
    JSON output lets a caller parse the result directly instead of scraping
    prose.

    Returns:
        0 always -- this is a report-only mode (issue #3021 acceptance
        criterion #2 scopes retroactive repair as report-only so it never
        blocks unrelated PRs); non-zero is reserved for genuine tool errors.
    """
    plugins_root = Path("plugins")
    if not plugins_root.is_dir():
        sys.stderr.write("Error: plugins/ directory not found\n")
        return 1

    drifted = audit_version_drift(plugins_root)
    print(json.dumps({"drifted_plugins": drifted}))
    return 0


def main() -> int:
    """Dispatch to the requested mode.

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else "")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="CI gate: fail if a changed plugin's version was not bumped")
    mode.add_argument(
        "--audit", action="store_true", help="Report plugins whose content changed after their last version bump"
    )
    parser.add_argument("--base-ref", default=None, help="Explicit base ref for --check (default: resolve_base())")
    parser.add_argument(
        "--head-ref",
        default=None,
        help=(
            "Explicit head ref for --check (default: HEAD). Required on a GitHub Actions "
            "pull_request trigger, since actions/checkout's default HEAD there is a synthetic "
            "merge commit, not the PR's real head -- pass origin/$GITHUB_HEAD_REF instead."
        ),
    )
    args = parser.parse_args()

    if args.check:
        return _run_check(args.base_ref, args.head_ref)
    return _run_audit()


if __name__ == "__main__":
    sys.exit(main())

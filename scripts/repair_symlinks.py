#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["gitpython>=3.1.45"]
# ///
"""Repair destroyed Git symlinks and normalize absolute symlink targets.

When core.symlinks is false, Git stores symlinks (mode 120000) as plain files
whose content is the target path. This script:
1. Sets core.symlinks true (repo-local)
2. Finds mode 120000 paths in HEAD that are plain files on disk (destroyed)
3. Removes each and creates real symlinks from HEAD blob content
4. Finds existing symlinks with absolute targets that resolve inside the repo
5. Replaces them with portable relative symlinks

Uses HEAD (not index) so we find destroyed symlinks even when they have been
staged — staging overwrites the index with 100644, so index-based detection
would miss them. destroyed-symlinks compares HEAD to index; we must fix before
that hook runs.

Uses GitPython — no subprocess / shell-out to git.

Requires Windows Developer Mode or Administrator for symlink creation.
Run from repository root.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from git import Repo
from git.exc import InvalidGitRepositoryError, NoSuchPathError
from git.objects import Blob

if TYPE_CHECKING:
    from collections.abc import Iterator

GIT_MODE_SYMLINK = 0o120000  # 40960 decimal; GitPython tree items use this


def _ensure_core_symlinks(repo: Repo) -> bool:
    """Set core.symlinks true.

    Returns:
        True if core.symlinks is now true, False on failure.
    """
    try:
        cfg = repo.config_reader()
        val = cfg.get_value("core", "symlinks", True)
        if val in {"true", True}:
            return True
    except (OSError, KeyError):
        pass
    try:
        with repo.config_writer() as writer:
            writer.set_value("core", "symlinks", "true")
        val = repo.config_reader().get_value("core", "symlinks")
    except (OSError, KeyError):
        print("repair_symlinks: failed to set core.symlinks true", file=sys.stderr)
        return False
    else:
        return val in {"true", True}


def _iter_symlink_blobs(repo: Repo, repo_root: Path) -> Iterator[tuple[Blob, Path]]:
    """Yield all mode 120000 (symlink) blobs in HEAD with their disk paths.

    Single tree traversal shared by all consumers (destroyed detection,
    absolute-target detection).

    Args:
        repo: The Git repository object.
        repo_root: Absolute path to the repository root.

    Yields:
        Tuples of (blob, disk_path) for every symlink entry in HEAD.
    """
    head_tree = repo.head.commit.tree
    for item in head_tree.traverse():
        if isinstance(item, Blob) and item.mode == GIT_MODE_SYMLINK:
            yield item, repo_root / item.path


def _get_symlink_target_from_blob(repo: Repo, blob: Blob) -> str:
    """Read symlink target from blob content.

    Returns:
        The symlink target path as stored in the blob.
    """
    stream = repo.odb.stream(blob.binsha)
    return stream.read().decode("utf-8", errors="replace").strip()


def _normalize_symlink_target(target: str, symlink_path: Path, repo_root_resolved: Path) -> str:
    r"""Normalize an absolute symlink target to a relative path when inside the repo.

    Relative targets are returned unchanged. Absolute targets that resolve to a
    path inside the repo root are converted to a relative path from the symlink's
    parent directory. Absolute targets outside the repo are returned unchanged so
    that external symlinks are preserved as-is.

    The computation uses ``os.path.relpath`` rather than ``Path.relative_to``
    because relpath handles ``..`` traversal correctly for paths that are not
    strict descendants of the symlink's parent.

    Args:
        target: Raw symlink target string read from the Git blob or readlink
            (may use ``\\`` separators on Windows).
        symlink_path: Absolute path of the symlink file on disk (or where it
            will be created). Used as the base for the relative path
            calculation.
        repo_root_resolved: Resolved (canonicalized) repo root path. Callers
            should compute this once via ``repo_root.resolve()`` and pass it
            in to avoid repeated filesystem calls.

    Returns:
        The (possibly rewritten) symlink target string. Always uses ``/``
        separators. Returns the original *target* unchanged when it is
        already relative or when the resolved target falls outside the repo.
    """
    # Normalise Windows-style separators in the incoming target
    abs_target = Path(target.replace("\\", "/"))

    if not abs_target.is_absolute():
        return str(abs_target)

    try:
        abs_target.relative_to(repo_root_resolved)
    except ValueError:
        # Target prefix doesn't match the current repo root.  This happens
        # when a symlink was created on a different machine (different home
        # directory, different checkout path).  Recover by finding the repo
        # directory name in the absolute path and treating everything after
        # it as a repo-relative path.
        #
        # Example: target = /home/otheruser/repos/claude_skills/plugins/foo
        #          repo   = /home/user/claude_skills  (name = "claude_skills")
        #          After repo name: plugins/foo
        #          Verify: repo_root / plugins/foo exists → rewrite
        repo_name = repo_root_resolved.name
        parts = abs_target.parts
        found_suffix: Path | None = None
        for i, part in enumerate(parts):
            if part == repo_name and i + 1 < len(parts):
                candidate = Path(*parts[i + 1 :])
                if (repo_root_resolved / candidate).exists():
                    found_suffix = candidate
                break  # Only match the first occurrence of the repo name.
        if found_suffix is None:
            # Repo name not found in path, or suffix doesn't exist — external.
            return str(abs_target)
        # Rewrite: the real target is repo_root / found_suffix.
        abs_target = repo_root_resolved / found_suffix

    # Target is inside the repo: compute relative path from symlink's parent.
    rel = os.path.relpath(str(abs_target), str(symlink_path.parent))
    return rel.replace("\\", "/")


def _replace_symlink(path: Path, target: str, rel: Path) -> bool:
    """Remove a symlink and recreate it with a new target.

    Args:
        path: Absolute path of the symlink on disk.
        target: New symlink target string.
        rel: Repo-relative path of the symlink (for error messages).

    Returns:
        True on success, False on failure.
    """
    path.unlink()
    try:
        path.symlink_to(target)
    except OSError:
        print(
            f"repair_symlinks: could not create symlink for {rel} "
            "(enable Windows Developer Mode or run as Administrator)",
            file=sys.stderr,
        )
        return False
    return path.is_symlink()


def _repair_one(repo: Repo, blob: Blob, path: Path, repo_root: Path, repo_root_resolved: Path) -> bool:
    """Repair a single destroyed symlink.

    Returns:
        True on success, False on failure.
    """
    rel = path.relative_to(repo_root)
    raw_target = _get_symlink_target_from_blob(repo, blob)
    target = _normalize_symlink_target(raw_target, path, repo_root_resolved)
    if target != raw_target:
        print(f"repair_symlinks: normalized absolute symlink to relative: {rel} -> {target}", file=sys.stderr)
    if path.is_dir():
        # Path was a symlink in HEAD but is now a directory on disk —
        # intentionally replaced, not a destroyed symlink.
        return True
    if not _replace_symlink(path, target, rel):
        return False
    # Stage the repaired symlink so index gets mode 120000; otherwise
    # destroyed-symlinks still fails (HEAD 120000 vs index 100644).
    repo.index.add([str(rel).replace("\\", "/")])
    repo.index.write()
    return True


def _normalize_one(path: Path, repo_root: Path, repo_root_resolved: Path) -> bool:
    """Normalize a single existing symlink from absolute to relative.

    Reads the current symlink target, normalizes it via
    ``_normalize_symlink_target``, and recreates the symlink if the target
    changed.

    Args:
        path: Absolute path of the symlink on disk.
        repo_root: Absolute path to the repository root.
        repo_root_resolved: Pre-resolved repo root path.

    Returns:
        True if the symlink was normalized (or was already fine), False on
        failure.
    """
    raw_target = str(path.readlink())
    target = _normalize_symlink_target(raw_target, path, repo_root_resolved)
    if target == raw_target:
        # Still absolute after normalization — genuinely external, skip.
        return True
    rel = path.relative_to(repo_root)
    print(f"repair_symlinks: normalized absolute symlink to relative: {rel} -> {target}", file=sys.stderr)
    return _replace_symlink(path, target, rel)


def _content_matches_blob_target(path: Path, expected_target: str) -> bool:
    """Return True only if the file content is exactly the symlink target path.

    On Windows with core.symlinks=false, a destroyed symlink is stored as a
    plain file containing only the target path — no newline, no carriage
    return.  A real file intentionally replacing a symlink always contains
    embedded newlines (code, comments, etc.) and will not match.

    Args:
        path: Path to the regular file to inspect.
        expected_target: Symlink target string read from the Git blob.

    Returns:
        True if the file contains only ``expected_target`` with no newlines,
        False otherwise or on read error.
    """
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return "\n" not in content and "\r" not in content and content == expected_target


def main() -> int:
    """Repair destroyed Git symlinks and normalize absolute targets.

    Returns:
        0 on success, 1 on failure.
    """
    repo_root = Path.cwd()
    if not (repo_root / ".git").exists():
        print("repair_symlinks: not a git repository", file=sys.stderr)
        return 1

    try:
        repo = Repo(repo_root)
    except (InvalidGitRepositoryError, NoSuchPathError):
        print("repair_symlinks: not a git repository", file=sys.stderr)
        return 1

    if not _ensure_core_symlinks(repo):
        return 1

    repo_root_resolved = repo_root.resolve()

    # Single tree traversal — partition into destroyed and absolute-target lists.
    # These sets are mutually exclusive: destroyed entries are plain files (not
    # symlinks), while absolute-target entries are real symlinks on disk.
    destroyed: list[tuple[Blob, Path]] = []
    absolute: list[Path] = []
    for blob, path in _iter_symlink_blobs(repo, repo_root):
        if path.exists() and not path.is_symlink():
            if _content_matches_blob_target(path, _get_symlink_target_from_blob(repo, blob)):
                destroyed.append((blob, path))
        elif path.is_symlink() and path.readlink().is_absolute():
            absolute.append(path)

    # Phase 1: Repair destroyed symlinks (plain files that should be symlinks).
    for blob, path in destroyed:
        if not _repair_one(repo, blob, path, repo_root, repo_root_resolved):
            return 1

    # Phase 2: Normalize existing symlinks with absolute targets.
    for path in absolute:
        if not _normalize_one(path, repo_root, repo_root_resolved):
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Regression checks for the standalone, distributable uv plugin bundle."""

from __future__ import annotations

import filecmp
from pathlib import Path


REPO_ROOT = Path(__file__).parents[1]
SOURCE_SKILL = REPO_ROOT / "plugins" / "python3-development" / "skills" / "uv"
STANDALONE_SKILL = REPO_ROOT / "plugins" / "uv" / "skills" / "uv"


def test_uv_plugin_contains_regular_copy_of_shared_skill() -> None:
    """Keep the standalone bundle portable and aligned with its source skill."""
    assert STANDALONE_SKILL.is_dir()
    assert not STANDALONE_SKILL.is_symlink()

    source_files = sorted(path.relative_to(SOURCE_SKILL) for path in SOURCE_SKILL.rglob("*") if path.is_file())
    standalone_files = sorted(
        path.relative_to(STANDALONE_SKILL) for path in STANDALONE_SKILL.rglob("*") if path.is_file()
    )

    assert standalone_files == source_files
    for relative_path in source_files:
        assert filecmp.cmp(
            SOURCE_SKILL / relative_path,
            STANDALONE_SKILL / relative_path,
            shallow=False,
        )

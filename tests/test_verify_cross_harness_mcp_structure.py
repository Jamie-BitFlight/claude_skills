"""Tests for the classification logic in ``scripts/verify_cross_harness_mcp_structure.py``.

Fixture repository trees are built as real files under ``tmp_path`` and then walked to produce
the ``path``/``type`` entries a GitHub "get tree recursively" API response would contain, so the
classification functions under test exercise the same tree-walking shape they see in production —
only the network call (``run_gh_json``) is replaced.
"""

from __future__ import annotations

import importlib.util
import operator
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

_SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "verify_cross_harness_mcp_structure.py"
_SPEC = importlib.util.spec_from_file_location("verify_cross_harness_mcp_structure", _SCRIPT_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"Could not load module from {_SCRIPT_PATH}")
verify = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = verify
_SPEC.loader.exec_module(verify)


def _write(root: Path, *relative_paths: str) -> None:
    """Create empty files at each relative path under ``root``, creating parents as needed."""
    for relative_path in relative_paths:
        file_path = root / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text("", encoding="utf-8")


def _blob_paths(root: Path) -> list[dict[str, str]]:
    """Walk a real fixture tree and return GitHub-tree-shaped blob entries.

    Returns:
        One ``{"path": ..., "type": "blob"}`` entry per file under ``root``, using
        forward-slash-separated paths relative to ``root``.
    """
    return sorted(
        (
            {"path": file_path.relative_to(root).as_posix(), "type": "blob"}
            for file_path in root.rglob("*")
            if file_path.is_file()
        ),
        key=operator.itemgetter("path"),
    )


def _fake_tree_response(root: Path, *, truncated: bool = False) -> dict[str, Any]:
    """Build a fake ``git/trees`` API payload from a real on-disk fixture tree."""
    return {"tree": _blob_paths(root), "truncated": truncated}


def _base_candidate(repository: str = "octo-org/octo-repo", *, rank: int = 1) -> dict[str, Any]:
    return {"repository": repository, "default_branch": "main", "rank": rank, "stars": 5000, "forks": 200}


class TestPluginRoot:
    """Direct unit coverage of ``plugin_root``."""

    def test_returns_dot_for_repository_root_manifest(self) -> None:
        assert verify.plugin_root(".claude-plugin/plugin.json", ".claude-plugin") == "."

    def test_returns_parent_directory_for_nested_manifest(self) -> None:
        assert verify.plugin_root("plugins/foo/.claude-plugin/plugin.json", ".claude-plugin") == "plugins/foo"

    def test_raises_on_unexpected_manifest_path(self) -> None:
        with pytest.raises(ValueError, match=r"Unexpected \.claude-plugin manifest path"):
            verify.plugin_root("plugins/foo/.claude-plugin/other.json", ".claude-plugin")


class TestMcpConfigPaths:
    """Direct unit coverage of ``mcp_config_paths``."""

    def test_finds_dot_mcp_json_at_root(self) -> None:
        paths = [".mcp.json", "README.md"]
        assert verify.mcp_config_paths(paths, ".") == [".mcp.json"]

    def test_finds_dot_mcp_variant_and_mcp_configs_directory(self) -> None:
        paths = [
            "plugins/foo/.mcp.dev.json",
            "plugins/foo/mcp-configs/server.json",
            "plugins/foo/mcp-configs/notes.md",
            "plugins/foo/README.md",
        ]
        assert verify.mcp_config_paths(paths, "plugins/foo") == [
            "plugins/foo/.mcp.dev.json",
            "plugins/foo/mcp-configs/server.json",
        ]

    def test_excludes_paths_outside_the_given_root(self) -> None:
        paths = ["plugins/foo/.mcp.json", "plugins/bar/.mcp.json"]
        assert verify.mcp_config_paths(paths, "plugins/foo") == ["plugins/foo/.mcp.json"]

    def test_returns_empty_list_when_no_config_present(self) -> None:
        paths = ["plugins/foo/README.md", "plugins/foo/skills/index.md"]
        assert verify.mcp_config_paths(paths, "plugins/foo") == []


class TestInspectTree:
    """Status-outcome coverage of ``inspect_tree`` against real fixture trees."""

    def test_tree_unavailable_when_no_default_branch(self) -> None:
        candidate = _base_candidate()
        candidate["default_branch"] = None

        record = verify.inspect_tree(candidate)

        assert record["status"] == "tree_unavailable"
        assert record["reason"] == "repository has no default branch"

    def test_accepted_for_semantic_inspection_when_aligned_plugin_has_bundled_mcp(
        self, tmp_path: Path, mocker: MockerFixture
    ) -> None:
        root = tmp_path / "octo-repo"
        _write(
            root,
            "plugins/foo/.claude-plugin/plugin.json",
            "plugins/foo/.codex-plugin/plugin.json",
            "plugins/foo/.mcp.json",
            "plugins/foo/README.md",
        )
        mocker.patch.object(verify, "run_gh_json", return_value=_fake_tree_response(root))

        record = verify.inspect_tree(_base_candidate())

        assert record["status"] == "accepted_for_semantic_inspection"
        assert record["tree_truncated"] is False
        assert [plugin["root"] for plugin in record["aligned_plugins"]] == ["plugins/foo"]
        assert record["aligned_plugins"][0]["mcp_config_paths"] == ["plugins/foo/.mcp.json"]

    def test_rejected_when_aligned_plugin_has_no_bundled_mcp(self, tmp_path: Path, mocker: MockerFixture) -> None:
        root = tmp_path / "octo-repo"
        _write(
            root,
            "plugins/foo/.claude-plugin/plugin.json",
            "plugins/foo/.codex-plugin/plugin.json",
            "plugins/foo/README.md",
        )
        mocker.patch.object(verify, "run_gh_json", return_value=_fake_tree_response(root))

        record = verify.inspect_tree(_base_candidate())

        assert record["status"] == "rejected_no_aligned_bundled_mcp"
        assert record["aligned_plugins"][0]["mcp_config_paths"] == []

    def test_rejected_when_manifests_are_not_aligned_to_the_same_root(
        self, tmp_path: Path, mocker: MockerFixture
    ) -> None:
        root = tmp_path / "octo-repo"
        _write(
            root,
            "plugins/foo/.claude-plugin/plugin.json",
            "plugins/bar/.codex-plugin/plugin.json",
            "plugins/bar/.mcp.json",
        )
        mocker.patch.object(verify, "run_gh_json", return_value=_fake_tree_response(root))

        record = verify.inspect_tree(_base_candidate())

        assert record["status"] == "rejected_no_aligned_bundled_mcp"
        assert record["aligned_plugins"] == []

    def test_inconclusive_when_tree_truncated_even_with_bundled_mcp(
        self, tmp_path: Path, mocker: MockerFixture
    ) -> None:
        root = tmp_path / "octo-repo"
        _write(
            root,
            "plugins/foo/.claude-plugin/plugin.json",
            "plugins/foo/.codex-plugin/plugin.json",
            "plugins/foo/.mcp.json",
        )
        mocker.patch.object(verify, "run_gh_json", return_value=_fake_tree_response(root, truncated=True))

        record = verify.inspect_tree(_base_candidate())

        assert record["status"] == "inconclusive_tree_truncated"
        assert record["tree_truncated"] is True

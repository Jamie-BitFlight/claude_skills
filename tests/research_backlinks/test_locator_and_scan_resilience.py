"""Regression tests for validator locators and vault-scan resilience.

Covers the three behaviour changes PR #3529 makes to how issues are *located*
and how a scan survives a damaged vault:

1. ``_yaml_body_lines`` blanks the YAML frontmatter in place rather than
   truncating it, so a reported ``line`` is the real file line rather than one
   offset by that entry's frontmatter length.
2. ``_infer_research_root`` walks up to the enclosing git repository root for an
   all-files argument list, so the pre-commit hook's ``pass_filenames: true``
   shape keeps directory context for any number of staged entries.
3. ``build_cross_reference_graph`` reports each scan-skipped file once per call
   and never aborts the whole scan on one unreadable, unparseable, or
   vault-escaping ``.md``.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import backlink_lib
import validate_research

from .conftest import validator_command


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    """Run validate_research.py via uv run --script."""
    return subprocess.run(validator_command(args), capture_output=True, text=True, check=False)


_YAML_ENTRY_BODY = """\
# Alpha

## Overview

## Problem Addressed

Text.
"""


def _write_yaml_entry(path: Path, *, frontmatter_padding: int = 0) -> str:
    """Write an entry with YAML frontmatter and one deliberately empty section.

    Args:
        path: Destination file.
        frontmatter_padding: Extra frontmatter lines, used to vary the offset
            between the top of the file and the start of the body.

    Returns:
        The exact text written, so a test can locate a line by content.
    """
    padding = "".join(f"pad_{i}: value\n" for i in range(frontmatter_padding))
    content = f"---\nname: alpha\n{padding}---\n\n{_YAML_ENTRY_BODY}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return content


class TestFrontmatterAwareLineNumbers:
    """A reported line number indexes the real file, frontmatter included."""

    @pytest.mark.parametrize("frontmatter_padding", [0, 5, 17])
    def test_empty_section_line_points_at_the_real_heading(self, tmp_path: Path, frontmatter_padding: int) -> None:
        """The Overview issue's line is the file line actually holding '## Overview'."""
        entry = tmp_path / "alpha.md"
        content = _write_yaml_entry(entry, frontmatter_padding=frontmatter_padding)
        expected_line = content.splitlines().index("## Overview") + 1

        result = validate_research.validate_file(entry, tmp_path)

        overview_issues = [i for i in result["issues"] if i["message"] == "Empty section: Overview"]
        assert overview_issues, f"Expected an empty-section issue for Overview:\n{result['issues']}"
        assert overview_issues[0]["line"] == expected_line


class TestInferResearchRoot:
    """Root inference keeps locators resolvable for every hook argument shape."""

    @staticmethod
    def _repo_with_entries(tmp_path: Path, *names: str) -> tuple[Path, list[Path]]:
        """Build a git repo containing research/coding-agents/<name> for each name."""
        repo = tmp_path / "repo"
        (repo / ".git").mkdir(parents=True)
        category = repo / "research" / "coding-agents"
        category.mkdir(parents=True)
        entries = []
        for name in names:
            entry = category / name
            entry.write_text("# Entry\n", encoding="utf-8")
            entries.append(entry)
        return repo, entries

    def test_single_staged_file_resolves_to_repo_root(self, tmp_path: Path) -> None:
        """One staged file still walks up to the git root."""
        repo, entries = self._repo_with_entries(tmp_path, "alpha.md")
        assert validate_research._infer_research_root(entries) == repo

    def test_multiple_staged_files_in_one_category_resolve_to_repo_root(self, tmp_path: Path) -> None:
        """Three entries from one category keep directory context, not bare basenames."""
        repo, entries = self._repo_with_entries(tmp_path, "alpha.md", "beta.md", "gamma.md")

        root = validate_research._infer_research_root(entries)

        assert root == repo
        assert entries[0].relative_to(root) == Path("research/coding-agents/alpha.md")

    def test_lone_directory_argument_stays_vault_relative(self, tmp_path: Path) -> None:
        """A directory argument reports relative to that vault, not the repo root."""
        repo, _ = self._repo_with_entries(tmp_path, "alpha.md")
        vault = repo / "research"
        assert validate_research._infer_research_root([vault]) == vault

    def test_files_outside_any_repo_fall_back_to_common_ancestor(self, tmp_path: Path) -> None:
        """With no enclosing .git, the common ancestor is the root."""
        category = tmp_path / "vault" / "tools"
        category.mkdir(parents=True)
        entries = []
        for name in ("alpha.md", "beta.md"):
            entry = category / name
            entry.write_text("# Entry\n", encoding="utf-8")
            entries.append(entry)
        assert validate_research._infer_research_root(entries) == category


_UNPARSEABLE_ENTRY = """\
# Broken

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| beta.md | tools | no markdown link in the Entry cell |
"""


class TestScanResilience:
    """One damaged .md skips itself; it never aborts the scan."""

    def test_symlink_escaping_the_vault_does_not_abort_the_scan(self, tmp_path: Path) -> None:
        """An .md symlinked outside the vault is skipped, not fatal."""
        outside = tmp_path / "outside"
        outside.mkdir()
        (outside / "target.md").write_text("# Outside\n", encoding="utf-8")

        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / "entry.md").write_text("# Entry\n", encoding="utf-8")
        (vault / "escape.md").symlink_to(outside / "target.md")

        graph = backlink_lib.build_cross_reference_graph(vault, quiet=True).graph

        assert (vault / "entry.md").resolve() in graph

    def test_scan_skip_warning_prints_a_vault_relative_path(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        """The warning names the file the way the edge lines below it are named."""
        vault = tmp_path / "vault"
        (vault / "tools").mkdir(parents=True)
        (vault / "tools" / "broken.md").write_text(_UNPARSEABLE_ENTRY, encoding="utf-8")

        backlink_lib.build_cross_reference_graph(vault)

        stderr = capsys.readouterr().err
        assert "warning: scan-skipped" in stderr
        assert "tools/broken.md" in stderr
        assert str(vault) not in stderr

    def test_quiet_suppresses_the_scan_skip_warning(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        """quiet=True is what keeps --fix's second graph build from reprinting."""
        vault = tmp_path / "vault"
        (vault / "tools").mkdir(parents=True)
        (vault / "tools" / "broken.md").write_text(_UNPARSEABLE_ENTRY, encoding="utf-8")

        backlink_lib.build_cross_reference_graph(vault, quiet=True)

        assert "scan-skipped" not in capsys.readouterr().err

    @pytest.mark.integration
    def test_fix_run_reports_each_scan_skip_exactly_once(self, tmp_path: Path) -> None:
        """check-backlinks --fix builds the graph twice but warns once."""
        vault = tmp_path / "vault"
        (vault / "tools").mkdir(parents=True)
        (vault / "tools" / "broken.md").write_text(_UNPARSEABLE_ENTRY, encoding="utf-8")

        result = _run(["check-backlinks", str(vault), "--fix"])

        skips = result.stderr.count("warning: scan-skipped")
        assert skips == 1, f"Expected exactly one scan-skipped warning, got {skips}:\n{result.stderr}"

"""Tests for check-backlinks scan coverage reporting and write exclusion.

Covers the two gaps issue #3516 records against the shared Post-Actions gate:

1. ``check-backlinks`` used to exit 0 whenever no asymmetric edge remained in the
   graph it managed to build, even when the scan had dropped files. Exit 0 then
   claimed coverage the scan did not have. ``build_cross_reference_graph`` now
   returns its skips alongside the graph, the CLI reports them on stdout, and a
   skipped file fails the run unless ``--allow-partial-scan`` is passed.
2. ``check-backlinks --fix`` had no way to keep it from writing to a named file.
   ``--exclude`` now gates the write only -- the excluded file is still scanned
   and its asymmetric pairs are still reported.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

import backlink_lib

_SCRIPTS_DIR = Path(__file__).parents[2] / ".claude" / "skills" / "research-curator" / "scripts"
_VALIDATE_SCRIPT = _SCRIPTS_DIR / "validate_research.py"

# A Cross-References table whose Entry cell holds no markdown link. parse_cross_references_table
# raises ValueError on it, so the whole file is dropped during the scan's parse phase.
_UNPARSEABLE_ENTRY = """\
# Broken

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| beta.md | tools | no markdown link in the Entry cell |
"""


def _uv_path() -> str:
    """Locate the uv binary, raising RuntimeError if not found."""
    found = shutil.which("uv")
    if found is None:
        raise RuntimeError("uv binary not found on PATH — cannot run CLI tests")
    return found


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    """Run validate_research.py via uv run --script."""
    cmd = [_uv_path(), "run", "--script", str(_VALIDATE_SCRIPT), *args]
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def _write_entry(path: Path, cross_refs: list[tuple[str, str, str]] | None = None) -> None:
    """Write a research entry carrying only the sections the backlink scan reads."""
    path.parent.mkdir(parents=True, exist_ok=True)
    slug = path.stem
    # ## References must be present: append_backlink_row anchors a new Cross-References
    # section to it (or to ## Freshness Tracking) and raises ValueError without either.
    lines = [
        f"# {slug.title()}",
        "",
        "## Overview",
        "",
        f"{slug.title()} test entry.",
        "",
        "## References",
        "",
        "- [Example](https://example.com) (accessed 2026-01-01)",
        "",
    ]
    if cross_refs:
        lines += [
            "---",
            "",
            "## Cross-References",
            "",
            "| Entry | Category | Relationship |",
            "|-------|----------|--------------|",
        ]
        lines += [
            f"| [{Path(link).stem.title()}]({link}) | {category} | {relationship} |"
            for link, category, relationship in cross_refs
        ]
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


@pytest.fixture
def clean_vault(tmp_path: Path) -> Path:
    """Vault with zero asymmetric edges and nothing for the scan to skip."""
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "README.md").write_text("# Research\n", encoding="utf-8")
    _write_entry(vault / "agent-frameworks" / "alpha.md", [("../tools/beta.md", "tools", "provides X to")])
    _write_entry(vault / "tools" / "beta.md", [("../agent-frameworks/alpha.md", "agent-frameworks", "consumes X from")])
    return vault


@pytest.fixture
def asymmetric_vault(tmp_path: Path) -> Path:
    """Vault with exactly one asymmetric edge: alpha cites beta, beta cites nobody."""
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "README.md").write_text("# Research\n", encoding="utf-8")
    _write_entry(vault / "agent-frameworks" / "alpha.md", [("../tools/beta.md", "tools", "provides X to")])
    _write_entry(vault / "tools" / "beta.md")
    return vault


class TestScanReportsItsOwnSkips:
    """build_cross_reference_graph hands every dropped file back to its caller."""

    def test_clean_scan_reports_no_skips(self, clean_vault: Path) -> None:
        """A vault with nothing to skip returns an empty skip list."""
        scan = backlink_lib.build_cross_reference_graph(clean_vault, quiet=True)

        assert scan.skips == []

    def test_unparseable_entry_is_returned_as_a_skip(self, clean_vault: Path) -> None:
        """The file the scan dropped is named in skips, not only on stderr."""
        (clean_vault / "tools" / "broken.md").write_text(_UNPARSEABLE_ENTRY, encoding="utf-8")

        scan = backlink_lib.build_cross_reference_graph(clean_vault, quiet=True)

        assert [skip.path for skip in scan.skips] == ["tools/broken.md"]
        assert scan.skips[0].reason == "parse"

    def test_skip_path_is_vault_relative(self, clean_vault: Path) -> None:
        """A skip path is reported the same way the edge lines are."""
        (clean_vault / "tools" / "broken.md").write_text(_UNPARSEABLE_ENTRY, encoding="utf-8")

        scan = backlink_lib.build_cross_reference_graph(clean_vault, quiet=True)

        assert str(clean_vault) not in scan.skips[0].path

    def test_quiet_still_records_the_skip(self, clean_vault: Path, capsys: pytest.CaptureFixture) -> None:
        """quiet suppresses the stderr warning only — it never drops the record."""
        (clean_vault / "tools" / "broken.md").write_text(_UNPARSEABLE_ENTRY, encoding="utf-8")

        scan = backlink_lib.build_cross_reference_graph(clean_vault, quiet=True)

        assert "scan-skipped" not in capsys.readouterr().err
        assert len(scan.skips) == 1


class TestScanCoverageDecidesExitCode:
    """A hole in the scan's coverage fails the run on its own."""

    def test_clean_vault_reports_zero_skips(self, clean_vault: Path) -> None:
        """The count is machine-readable on stdout even when it is zero."""
        result = _run(["check-backlinks", str(clean_vault)])

        assert "scan_skipped_files: 0" in result.stdout
        assert result.returncode == 0, f"Expected exit 0, got {result.returncode}:\n{result.stdout}"

    def test_skipped_file_is_counted_on_stdout(self, clean_vault: Path) -> None:
        """The skip count and the skipped path both reach stdout."""
        (clean_vault / "tools" / "broken.md").write_text(_UNPARSEABLE_ENTRY, encoding="utf-8")

        result = _run(["check-backlinks", str(clean_vault)])

        assert "scan_skipped_files: 1" in result.stdout
        assert "tools/broken.md (parse)" in result.stdout

    def test_skipped_file_fails_an_otherwise_clean_vault(self, clean_vault: Path) -> None:
        """This is the defect: exit 0 used to claim coverage the scan did not have."""
        (clean_vault / "tools" / "broken.md").write_text(_UNPARSEABLE_ENTRY, encoding="utf-8")

        result = _run(["check-backlinks", str(clean_vault)])

        assert result.returncode == 1, f"Expected exit 1 for a partial scan, got {result.returncode}:\n{result.stdout}"

    def test_allow_partial_scan_restores_exit_zero(self, clean_vault: Path) -> None:
        """A caller that accepts a partial scan opts in explicitly."""
        (clean_vault / "tools" / "broken.md").write_text(_UNPARSEABLE_ENTRY, encoding="utf-8")

        result = _run(["check-backlinks", str(clean_vault), "--allow-partial-scan"])

        assert result.returncode == 0, f"Expected exit 0 with --allow-partial-scan:\n{result.stdout}\n{result.stderr}"
        assert "scan_skipped_files: 1" in result.stdout

    def test_allow_partial_scan_does_not_excuse_an_asymmetric_edge(self, asymmetric_vault: Path) -> None:
        """The flag waives scan coverage only, never a real finding."""
        result = _run(["check-backlinks", str(asymmetric_vault), "--allow-partial-scan"])

        assert result.returncode == 1
        assert "asymmetric_cross_references: 1" in result.stdout

    def test_fix_run_fails_when_the_scan_was_partial(self, asymmetric_vault: Path) -> None:
        """--fix cannot repair a scan-skip, so it must not report success over one."""
        (asymmetric_vault / "tools" / "broken.md").write_text(_UNPARSEABLE_ENTRY, encoding="utf-8")

        result = _run(["check-backlinks", str(asymmetric_vault), "--fix"])

        assert "backlinks_repaired: 1" in result.stdout
        assert result.returncode == 1, f"Expected exit 1 for a partial scan, got {result.returncode}:\n{result.stdout}"


class TestExcludeGatesTheWriteOnly:
    """--exclude keeps --fix out of a named file without hiding it from the scan."""

    def test_fix_writes_to_the_target_without_exclude(self, asymmetric_vault: Path) -> None:
        """Baseline: the repair lands in the target that was missing the backlink."""
        target = asymmetric_vault / "tools" / "beta.md"
        before = target.read_text(encoding="utf-8")

        result = _run(["check-backlinks", str(asymmetric_vault), "--fix"])

        assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"
        assert target.read_text(encoding="utf-8") != before

    def test_excluded_target_is_not_written(self, asymmetric_vault: Path) -> None:
        """The excluded file is byte-identical after a --fix run."""
        target = asymmetric_vault / "tools" / "beta.md"
        before = target.read_text(encoding="utf-8")

        _run(["check-backlinks", str(asymmetric_vault), "--fix", "--exclude", str(target)])

        assert target.read_text(encoding="utf-8") == before

    def test_excluded_target_is_still_scanned_and_reported(self, asymmetric_vault: Path) -> None:
        """Exclusion gates the write, not the finding — the pair still shows up."""
        target = asymmetric_vault / "tools" / "beta.md"

        result = _run(["check-backlinks", str(asymmetric_vault), "--fix", "--exclude", str(target)])

        assert "asymmetric_cross_references: 1" in result.stdout
        assert "agent-frameworks/alpha.md -> tools/beta.md" in result.stdout

    def test_excluded_write_is_counted(self, asymmetric_vault: Path) -> None:
        """The run says how many repairs it withheld."""
        target = asymmetric_vault / "tools" / "beta.md"

        result = _run(["check-backlinks", str(asymmetric_vault), "--fix", "--exclude", str(target)])

        assert "backlinks_excluded: 1" in result.stdout
        assert "backlinks_repaired: 0" in result.stdout

    def test_unrepaired_exclusion_leaves_the_run_failing(self, asymmetric_vault: Path) -> None:
        """A withheld repair is still an open asymmetric pair, so the gate stays red."""
        target = asymmetric_vault / "tools" / "beta.md"

        result = _run(["check-backlinks", str(asymmetric_vault), "--fix", "--exclude", str(target)])

        assert result.returncode == 1, f"Expected exit 1, got {result.returncode}:\n{result.stdout}"

    def test_exclude_is_repeatable(self, tmp_path: Path) -> None:
        """Two --exclude options withhold two writes in one run."""
        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / "README.md").write_text("# Research\n", encoding="utf-8")
        _write_entry(
            vault / "agent-frameworks" / "alpha.md",
            [("../tools/beta.md", "tools", "provides X to"), ("../tools/gamma.md", "tools", "provides Y to")],
        )
        _write_entry(vault / "tools" / "beta.md")
        _write_entry(vault / "tools" / "gamma.md")
        beta_before = (vault / "tools" / "beta.md").read_text(encoding="utf-8")
        gamma_before = (vault / "tools" / "gamma.md").read_text(encoding="utf-8")

        result = _run([
            "check-backlinks",
            str(vault),
            "--fix",
            "--exclude",
            str(vault / "tools" / "beta.md"),
            "--exclude",
            str(vault / "tools" / "gamma.md"),
        ])

        assert "backlinks_excluded: 2" in result.stdout
        assert (vault / "tools" / "beta.md").read_text(encoding="utf-8") == beta_before
        assert (vault / "tools" / "gamma.md").read_text(encoding="utf-8") == gamma_before

    def test_excluding_one_target_still_repairs_the_other(self, tmp_path: Path) -> None:
        """Exclusion is per-path, not a global switch that stops every repair."""
        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / "README.md").write_text("# Research\n", encoding="utf-8")
        _write_entry(
            vault / "agent-frameworks" / "alpha.md",
            [("../tools/beta.md", "tools", "provides X to"), ("../tools/gamma.md", "tools", "provides Y to")],
        )
        _write_entry(vault / "tools" / "beta.md")
        _write_entry(vault / "tools" / "gamma.md")
        gamma_before = (vault / "tools" / "gamma.md").read_text(encoding="utf-8")

        result = _run(["check-backlinks", str(vault), "--fix", "--exclude", str(vault / "tools" / "gamma.md")])

        assert "backlinks_repaired: 1" in result.stdout
        assert "backlinks_excluded: 1" in result.stdout
        assert (vault / "tools" / "gamma.md").read_text(encoding="utf-8") == gamma_before

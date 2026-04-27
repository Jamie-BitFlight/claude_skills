"""Tests for the validate_research.py check-backlinks CLI subcommand."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).parents[2] / ".claude" / "skills" / "research-curator" / "scripts"
_VALIDATE_SCRIPT = _SCRIPTS_DIR / "validate_research.py"


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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _write_minimal_entry(path: Path, cross_refs: list[tuple[str, str, str]] | None = None) -> None:
    """Write a minimal well-formed research entry."""
    path.parent.mkdir(parents=True, exist_ok=True)
    slug = path.stem
    content = f"""\
# {slug.title()}

**Research Date**: 2026-01-01
**Source URL**: https://example.com/{slug}
**Version at Research**: 1.0.0
**License**: MIT

---

## Overview

{slug.title()} test entry.

## Problem Addressed

Test.

## Key Features

- Feature A

## Technical Architecture

Simple.

## Installation & Usage

```bash
pip install {slug}
```

## Key Statistics

- Stars: 5 (as of 2026-01-01)

## Relevance to Claude Code Development

Test.

## References

- [Example](https://example.com) (accessed 2026-01-01)

## Freshness Tracking

- **Last Verified**: 2026-01-01
- **Version at Verification**: 1.0.0
- **Next Review Recommended**: 2026-07-01
"""
    if cross_refs:
        table_lines = [
            "",
            "---",
            "",
            "## Cross-References",
            "",
            "| Entry | Category | Relationship |",
            "|-------|----------|--------------|",
        ]
        for link, category, relationship in cross_refs:
            link_name = Path(link).stem.title()
            table_lines.append(f"| [{link_name}]({link}) | {category} | {relationship} |")
        content = content.rstrip("\n") + "\n" + "\n".join(table_lines) + "\n"

    path.write_text(content, encoding="utf-8")


@pytest.fixture
def asymmetric_vault(tmp_path: Path) -> Path:
    """Vault with exactly one asymmetric edge: alpha→beta, beta has no backlink."""
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "README.md").write_text("# Research\n", encoding="utf-8")

    _write_minimal_entry(
        vault / "agent-frameworks" / "alpha.md", cross_refs=[("../tools/beta.md", "tools", "provides embedding layer")]
    )
    _write_minimal_entry(vault / "tools" / "beta.md")

    return vault


@pytest.fixture
def symmetric_vault(tmp_path: Path) -> Path:
    """Vault with zero asymmetric edges: alpha↔beta mutual references."""
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "README.md").write_text("# Research\n", encoding="utf-8")

    _write_minimal_entry(
        vault / "agent-frameworks" / "alpha.md", cross_refs=[("../tools/beta.md", "tools", "provides embedding layer")]
    )
    _write_minimal_entry(
        vault / "tools" / "beta.md",
        cross_refs=[("../agent-frameworks/alpha.md", "agent-frameworks", "consumes embedding layer provided by")],
    )
    return vault


# ---------------------------------------------------------------------------
# --help test
# ---------------------------------------------------------------------------


class TestHelpOutput:
    """Validate --help lists the check-backlinks subcommand."""

    def test_help_lists_check_backlinks(self) -> None:
        """--help output mentions check-backlinks subcommand."""
        result = _run(["--help"])
        assert result.returncode == 0, f"--help exited {result.returncode}:\n{result.stderr}"
        assert "check-backlinks" in result.stdout, f"'check-backlinks' not found in --help output:\n{result.stdout}"

    def test_check_backlinks_help(self) -> None:
        """check-backlinks --help shows vault_path argument."""
        result = _run(["check-backlinks", "--help"])
        assert result.returncode == 0
        assert "vault" in result.stdout.lower() or "path" in result.stdout.lower()


# ---------------------------------------------------------------------------
# Default mode (no --fix)
# ---------------------------------------------------------------------------


class TestDefaultMode:
    """Default check-backlinks mode: report asymmetries, exit 1 if any."""

    def test_asymmetric_vault_exits_one(self, asymmetric_vault: Path) -> None:
        """Asymmetric vault exits 1."""
        result = _run(["check-backlinks", str(asymmetric_vault)])
        assert result.returncode == 1, (
            f"Expected exit 1 for asymmetric vault, got {result.returncode}:\n{result.stdout}"
        )

    def test_asymmetric_vault_prints_count(self, asymmetric_vault: Path) -> None:
        """Asymmetric vault prints asymmetric_cross_references: 1."""
        result = _run(["check-backlinks", str(asymmetric_vault)])
        assert "asymmetric_cross_references: 1" in result.stdout, f"Expected count line in output:\n{result.stdout}"

    def test_symmetric_vault_exits_zero(self, symmetric_vault: Path) -> None:
        """Fully symmetric vault exits 0."""
        result = _run(["check-backlinks", str(symmetric_vault)])
        assert result.returncode == 0, f"Expected exit 0 for symmetric vault, got {result.returncode}:\n{result.stdout}"

    def test_symmetric_vault_prints_zero_count(self, symmetric_vault: Path) -> None:
        """Symmetric vault prints asymmetric_cross_references: 0."""
        result = _run(["check-backlinks", str(symmetric_vault)])
        assert "asymmetric_cross_references: 0" in result.stdout

    def test_asymmetric_vault_prints_edge_details(self, asymmetric_vault: Path) -> None:
        """Output includes the specific asymmetric pair paths."""
        result = _run(["check-backlinks", str(asymmetric_vault)])
        # Should mention alpha.md -> beta.md or beta.md in the detailed lines
        output = result.stdout
        assert "alpha.md" in output or "beta.md" in output, f"Expected entry paths in output:\n{output}"


# ---------------------------------------------------------------------------
# --fix mode
# ---------------------------------------------------------------------------


class TestFixMode:
    """--fix mode repairs asymmetries and exits 0."""

    def test_fix_mode_exits_zero(self, asymmetric_vault: Path) -> None:
        """--fix on asymmetric vault exits 0."""
        result = _run(["check-backlinks", str(asymmetric_vault), "--fix"])
        assert result.returncode == 0, (
            f"Expected exit 0 after fix, got {result.returncode}:\n{result.stdout}\n{result.stderr}"
        )

    def test_fix_mode_reports_repaired_count(self, asymmetric_vault: Path) -> None:
        """--fix output contains backlinks_repaired: N."""
        result = _run(["check-backlinks", str(asymmetric_vault), "--fix"])
        assert "backlinks_repaired:" in result.stdout, f"Expected backlinks_repaired in output:\n{result.stdout}"

    def test_fix_mode_repairs_one(self, asymmetric_vault: Path) -> None:
        """--fix repairs the single asymmetric edge."""
        result = _run(["check-backlinks", str(asymmetric_vault), "--fix"])
        assert "backlinks_repaired: 1" in result.stdout

    def test_rerun_after_fix_exits_zero(self, asymmetric_vault: Path) -> None:
        """After --fix, plain check-backlinks exits 0."""
        _run(["check-backlinks", str(asymmetric_vault), "--fix"])
        result = _run(["check-backlinks", str(asymmetric_vault)])
        assert result.returncode == 0, f"Expected exit 0 after fix+rerun, got {result.returncode}:\n{result.stdout}"

    def test_rerun_after_fix_reports_zero_asymmetries(self, asymmetric_vault: Path) -> None:
        """After --fix, re-check reports asymmetric_cross_references: 0."""
        _run(["check-backlinks", str(asymmetric_vault), "--fix"])
        result = _run(["check-backlinks", str(asymmetric_vault)])
        assert "asymmetric_cross_references: 0" in result.stdout


# ---------------------------------------------------------------------------
# Real vault informational baseline
# ---------------------------------------------------------------------------


class TestRealVaultBaseline:
    """Informational: scan real vault and emit asymmetry count."""

    def test_check_backlinks_against_real_vault(self) -> None:
        """Run check-backlinks against real vault — captures informational baseline.

        This test does NOT assert a specific count. It only verifies the command
        runs to completion and emits the expected output line format.
        """
        real_vault = Path(__file__).parents[2] / "research"
        if not real_vault.exists():
            pytest.skip("Real research vault not present")

        result = _run(["check-backlinks", str(real_vault)])

        # Must emit the count line regardless of exit code
        assert "asymmetric_cross_references:" in result.stdout, (
            f"Expected count line in output:\n{result.stdout}\nstderr:\n{result.stderr}"
        )

        # Extract and print the count for informational purposes
        for line in result.stdout.splitlines():
            if line.startswith("asymmetric_cross_references:"):
                count_str = line.split(":")[1].strip()
                print(f"\nReal vault asymmetric_cross_references: {count_str}")
                break

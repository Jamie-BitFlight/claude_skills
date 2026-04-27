"""Tests for idempotency: append_backlink_row, backlink_exists, and validator --fix."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import backlink_lib as bl

_SCRIPTS_DIR = Path(__file__).parents[2] / ".claude" / "skills" / "research-curator" / "scripts"
_VALIDATE_SCRIPT = _SCRIPTS_DIR / "validate_research.py"


def _uv_path() -> str:
    """Locate the uv binary, raising RuntimeError if not found."""
    found = shutil.which("uv")
    if found is None:
        raise RuntimeError("uv binary not found on PATH — cannot run CLI tests")
    return found


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_ENTRY_WITH_CROSS_REF = """\
# Target Entry

**Research Date**: 2026-01-01
**Source URL**: https://example.com/target
**Version at Research**: 1.0.0
**License**: MIT

---

## Overview

A test entry with a Cross-References table.

## Problem Addressed

Test entry.

## Key Features

- Feature A

## Technical Architecture

Simple.

## Installation & Usage

```bash
pip install target
```

## Key Statistics

- Stars: 10 (as of 2026-01-01)

## Relevance to Claude Code Development

Test.

## References

- [Example](https://example.com) (accessed 2026-01-01)

## Freshness Tracking

- **Last Verified**: 2026-01-01
- **Version at Verification**: 1.0.0
- **Next Review Recommended**: 2026-07-01

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [AlphaEntry](../agent-frameworks/alpha.md) | agent-frameworks | provides embedding layer |
"""


# ---------------------------------------------------------------------------
# append_backlink_row idempotency tests
# ---------------------------------------------------------------------------


class TestAppendBacklinkRowIdempotency:
    """append_backlink_row must be idempotent when row already present."""

    def test_existing_row_returns_false_modified(self) -> None:
        """Calling append_backlink_row on existing link returns (unchanged_md, False)."""
        row = bl.CrossRefRow(
            entry_name="AlphaEntry",
            link_path="../agent-frameworks/alpha.md",
            category="agent-frameworks",
            relationship="provides embedding layer",
        )
        new_md, modified = bl.append_backlink_row(_ENTRY_WITH_CROSS_REF, row)
        assert not modified, "modified should be False when row already present"
        assert new_md == _ENTRY_WITH_CROSS_REF, "markdown must be unchanged when row already present"

    def test_existing_row_path_normalised(self) -> None:
        """Link path normalisation: './alpha.md' matches 'alpha.md'."""
        md = (
            "# Entry\n\n## Freshness Tracking\n\n- done\n\n---\n\n## Cross-References\n\n"
            "| Entry | Category | Relationship |\n"
            "|-------|----------|---|\n"
            "| [Alpha](alpha.md) | tools | provides X |\n"
        )
        row = bl.CrossRefRow(entry_name="Alpha", link_path="./alpha.md", category="tools", relationship="provides X")
        _, modified = bl.append_backlink_row(md, row)
        assert not modified, "Normalised path match must report not modified"

    def test_new_row_returns_true_modified(self) -> None:
        """append_backlink_row on a NEW row returns (updated_md, True)."""
        row = bl.CrossRefRow(
            entry_name="BetaEntry", link_path="../tools/beta.md", category="tools", relationship="consumes X"
        )
        new_md, modified = bl.append_backlink_row(_ENTRY_WITH_CROSS_REF, row)
        assert modified, "modified should be True for a genuinely new row"
        assert "BetaEntry" in new_md

    def test_double_append_same_as_single(self) -> None:
        """Running append_backlink_row twice produces the same result as running once."""
        row = bl.CrossRefRow(
            entry_name="GammaEntry", link_path="../tools/gamma.md", category="tools", relationship="orchestrates agents"
        )
        once_md, _ = bl.append_backlink_row(_ENTRY_WITH_CROSS_REF, row)
        twice_md, twice_modified = bl.append_backlink_row(once_md, row)
        assert not twice_modified, "Second call must be a no-op"
        assert once_md == twice_md, "Second call output must equal first call output"

    def test_backlink_exists_true_for_present_link(self) -> None:
        """backlink_exists returns True when the normalised path is in the table."""
        assert bl.backlink_exists(_ENTRY_WITH_CROSS_REF, "../agent-frameworks/alpha.md")

    def test_backlink_exists_false_for_absent_link(self) -> None:
        """backlink_exists returns False when link not present in table."""
        assert not bl.backlink_exists(_ENTRY_WITH_CROSS_REF, "../agent-frameworks/missing.md")


# ---------------------------------------------------------------------------
# Validator --fix idempotency
# ---------------------------------------------------------------------------


class TestValidatorFixIdempotent:
    """Running --fix twice must leave vault in zero-asymmetry state after first run."""

    def _make_asymmetric_vault(self, tmp_path: Path) -> Path:
        """Create a minimal two-entry vault with one asymmetric edge."""
        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / "README.md").write_text("# Research\n", encoding="utf-8")

        alpha_dir = vault / "agent-frameworks"
        alpha_dir.mkdir()
        beta_dir = vault / "tools"
        beta_dir.mkdir()

        # Alpha references Beta (forward edge exists)
        alpha_md = """\
# Alpha

**Research Date**: 2026-01-01
**Source URL**: https://example.com/alpha
**Version at Research**: 1.0.0
**License**: MIT

---

## Overview

Alpha entry.

## Problem Addressed

Test.

## Key Features

- Feature A

## Technical Architecture

Simple.

## Installation & Usage

```bash
pip install alpha
```

## Key Statistics

- Stars: 10 (as of 2026-01-01)

## Relevance to Claude Code Development

Test.

## References

- [Example](https://example.com) (accessed 2026-01-01)

## Freshness Tracking

- **Last Verified**: 2026-01-01
- **Version at Verification**: 1.0.0
- **Next Review Recommended**: 2026-07-01

---

## Cross-References

| Entry | Category | Relationship |
|-------|----------|--------------|
| [Beta](../tools/beta.md) | tools | provides data pipeline |
"""
        (alpha_dir / "alpha.md").write_text(alpha_md, encoding="utf-8")

        # Beta has no cross-references (asymmetric: no backlink to Alpha)
        beta_md = """\
# Beta

**Research Date**: 2026-01-01
**Source URL**: https://example.com/beta
**Version at Research**: 1.0.0
**License**: MIT

---

## Overview

Beta entry.

## Problem Addressed

Test.

## Key Features

- Feature B

## Technical Architecture

Simple.

## Installation & Usage

```bash
pip install beta
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
        (beta_dir / "beta.md").write_text(beta_md, encoding="utf-8")
        return vault

    def _run_check_backlinks(self, vault: Path, fix: bool = False) -> subprocess.CompletedProcess[str]:
        """Run the check-backlinks command via uv run --script."""
        cmd = [_uv_path(), "run", "--script", str(_VALIDATE_SCRIPT), "check-backlinks", str(vault)]
        if fix:
            cmd.append("--fix")
        return subprocess.run(cmd, capture_output=True, text=True, check=False)

    def test_validator_fix_idempotent(self, tmp_path: Path) -> None:
        """Running --fix twice yields zero asymmetries both times after first fix."""
        vault = self._make_asymmetric_vault(tmp_path)

        # First check: expect asymmetry
        result1 = self._run_check_backlinks(vault)
        assert "asymmetric_cross_references: 1" in result1.stdout, (
            f"Expected 1 asymmetry before fix, got:\n{result1.stdout}"
        )

        # First fix: repair the asymmetry
        result_fix1 = self._run_check_backlinks(vault, fix=True)
        assert result_fix1.returncode == 0, (
            f"First fix should exit 0, got {result_fix1.returncode}:\n{result_fix1.stdout}\n{result_fix1.stderr}"
        )
        assert "backlinks_repaired: 1" in result_fix1.stdout

        # Re-check after fix: must report 0 asymmetries
        result2 = self._run_check_backlinks(vault)
        assert "asymmetric_cross_references: 0" in result2.stdout, (
            f"Expected 0 asymmetries after fix, got:\n{result2.stdout}"
        )
        assert result2.returncode == 0

        # Second fix: idempotent — no changes, still 0
        result_fix2 = self._run_check_backlinks(vault, fix=True)
        assert result_fix2.returncode == 0, (
            f"Second fix should exit 0, got {result_fix2.returncode}:\n{result_fix2.stdout}"
        )
        assert "asymmetric_cross_references: 0" in result_fix2.stdout

    def test_fix_then_check_exits_zero(self, tmp_path: Path) -> None:
        """After --fix, plain check-backlinks exits 0."""
        vault = self._make_asymmetric_vault(tmp_path)
        self._run_check_backlinks(vault, fix=True)
        result = self._run_check_backlinks(vault)
        assert result.returncode == 0

    def test_fix_writes_backlink_row_to_target(self, tmp_path: Path) -> None:
        """After --fix, the target entry (beta.md) contains a Cross-References row for alpha."""
        vault = self._make_asymmetric_vault(tmp_path)
        self._run_check_backlinks(vault, fix=True)
        beta_text = (vault / "tools" / "beta.md").read_text(encoding="utf-8")
        assert "## Cross-References" in beta_text
        assert "alpha.md" in beta_text

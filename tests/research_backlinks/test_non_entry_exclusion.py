"""Tests that validate_research.py excludes directory-level non-entry files.

Covers the ``_is_research_entry``/``collect_files`` exclusion class: README.md, CLAUDE.md,
and AGENTS.md are AI-facing instruction/navigation files for a directory, not research
entries subject to the entry-template schema, and must never be scanned or format-detected.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, Final

import pytest

pytestmark = pytest.mark.integration

_REPO_ROOT = Path(__file__).parents[2]
_SCRIPTS_DIR = _REPO_ROOT / ".claude" / "skills" / "research-curator" / "scripts"
_VALIDATE_SCRIPT = _SCRIPTS_DIR / "validate_research.py"

# Per AGENTS.md's "Bounded subprocess execution" gotcha: wrap external commands that could hang
# (uv resolving PEP 723 deps, or a spawned child left running) so a timeout kills the whole
# process group instead of stalling the pytest worker indefinitely. Matches the pattern already
# established in the neighboring test_cross_references_check.py for this same validator script.
_RUN_BOUNDED: Final = (
    "uv",
    "run",
    "--script",
    str(_REPO_ROOT / "scripts" / "run_bounded.py"),
    "--timeout-seconds",
    "60",
    "--",
)


def _uv_path() -> str:
    """Locate the uv binary, raising RuntimeError if not found."""
    found = shutil.which("uv")
    if found is None:
        msg = "uv binary not found on PATH — cannot run CLI tests"
        raise RuntimeError(msg)
    return found


def _run_json(args: list[str]) -> dict[str, Any]:
    """Run validate_research.py main with --json (bounded) and parse the result.

    ``Any`` is this test module's JSON-parsing boundary (subprocess stdout from an
    external script whose shape each caller asserts directly), per this repo's typing
    policy of confining ``Any`` to boundary code that ingests unknown-shape external data.
    """
    cmd = [*_RUN_BOUNDED, _uv_path(), "run", "--script", str(_VALIDATE_SCRIPT), "main", *args, "--json"]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert result.stderr == "" or result.returncode in (0, 1), (
        f"Unexpected failure running validator:\n{result.stdout}\n{result.stderr}"
    )
    return json.loads(result.stdout)


@pytest.fixture
def vault_with_non_entry_files(tmp_path: Path) -> Path:
    """Vault containing README.md, CLAUDE.md, AGENTS.md and one well-formed entry."""
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "README.md").write_text("# Research Vault\n", encoding="utf-8")
    (vault / "CLAUDE.md").write_text("# AI-facing instructions\n\nSome project instructions.\n", encoding="utf-8")
    (vault / "AGENTS.md").write_text("# Agent working guide\n\nSome project instructions.\n", encoding="utf-8")

    category_dir = vault / "tools"
    category_dir.mkdir()
    (category_dir / "widget.md").write_text(
        "---\nname: widget\nresearch_date: 2026-01-01\nsource_url: https://example.com/widget\nversion_at_research: 1.0.0\nlicense: MIT\nfreshness_tracking:\n  last_verified: 2026-01-01\n  version_at_verification: 1.0.0\n  next_review: 2026-07-01\n---\n\n# Widget\n\n## Overview\n\nWidget test entry.\n\n## Problem Addressed\n\nTest.\n\n## Key Features\n\n- Feature A\n\n## Technical Architecture\n\nSimple.\n\n## Installation & Usage\n\n```bash\npip install widget\n```\n\n## Relevance to Claude Code Development\n\nTest.\n\n## References\n\n- [Example](https://example.com) (accessed 2026-01-01)\n",
        encoding="utf-8",
    )
    return vault


class TestNonEntryFileExclusion:
    """README.md, CLAUDE.md, and AGENTS.md must never be scanned as research entries."""

    def test_directory_scan_excludes_all_non_entry_files(self, vault_with_non_entry_files: Path) -> None:
        """Scanning the vault directory only reports the one real entry."""
        result = _run_json([str(vault_with_non_entry_files)])
        files = {entry["file"] for entry in result["entries"]}
        assert files == {"tools/widget.md"}, f"Expected only the real entry, got: {files}"

    def test_direct_claude_md_path_yields_no_entries(self, vault_with_non_entry_files: Path) -> None:
        """Passing CLAUDE.md directly still yields zero scanned entries."""
        result = _run_json([str(vault_with_non_entry_files / "CLAUDE.md")])
        assert result["entries"] == []
        assert result["summary"]["total"] == 0

    def test_direct_agents_md_path_yields_no_entries(self, vault_with_non_entry_files: Path) -> None:
        """Passing AGENTS.md directly still yields zero scanned entries."""
        result = _run_json([str(vault_with_non_entry_files / "AGENTS.md")])
        assert result["entries"] == []
        assert result["summary"]["total"] == 0

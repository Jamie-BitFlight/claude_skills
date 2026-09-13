"""Tests for the relevance_unanchored validator check.

The Phase 1c Repo Anchor Pass (references/extraction-methodology.md) requires every item in an
entry's Relevance section to carry an anchor: a repo-relative path with a quoted line read from
it, or the search command that returned nothing. Nothing enforced that mechanically -- the
pre-commit hook ran validate_research.py on every changed research entry and checked only that the
Relevance heading existed, so an entry whose author skipped Phase 1c entirely was still
committable and the only skip-detector was the agent's own self-report.

These tests pin the detector: an entry whose Relevance section cites neither a path nor a search
gets the warning; one citing either form does not. Severity is warning, matching
cross_references_absent -- the check flags a skipped pass for review, it does not fail the commit.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Final

_REPO_ROOT = Path(__file__).parents[2]
_VALIDATE_SCRIPT = _REPO_ROOT / ".claude" / "skills" / "research-curator" / "scripts" / "validate_research.py"

# Per AGENTS.md's "Bounded subprocess execution" gotcha: wrap external commands that could hang
# (uv resolving PEP 723 deps) so a timeout kills the whole process group.
_RUN_BOUNDED: Final = (
    "uv",
    "run",
    "--script",
    str(_REPO_ROOT / "scripts" / "run_bounded.py"),
    "--timeout-seconds",
    "60",
    "--",
)

# An unanchored Relevance body: true of any repository, checkable against none.
UNANCHORED = "Useful for agent workflows and fits well with this project's architecture."

# A present anchor: repo-relative path in backticks plus a line read from it.
PRESENT_ANCHOR = """\
- **Parallel fan-out** -> `plugins/agent-orchestration/skills/parallel-work/SKILL.md`
  - Today: "teams are not the default"
  - Change: none -- that skill already covers it
"""

# An absence anchor: the search command and its result, no path at all.
ABSENCE_ANCHOR = """\
- **msgspec encoder** -> nothing in the searched scope
  - Today: `git grep -il "msgspec" -- plugins/ rules/ docs/ AGENTS.md` -> 0 matches
  - Change: none -- out of scope
"""


def _uv_path() -> str:
    """Locate the uv binary, raising RuntimeError if not found."""
    found = shutil.which("uv")
    if found is None:
        raise RuntimeError("uv binary not found on PATH -- cannot run CLI tests")
    return found


def _run_json(path: Path) -> dict:
    """Run validate_research.py main --json on a single file and parse the result."""
    cmd = [*_RUN_BOUNDED, _uv_path(), "run", "--script", str(_VALIDATE_SCRIPT), "main", "--json", str(path)]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return json.loads(result.stdout)


def _write_entry(path: Path, relevance_body: str) -> None:
    """Write a minimal well-formed text-header entry with a given Relevance section body."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""\
# Example

**Research Date**: 2026-06-01
**Source URL**: https://example.com/example
**Version at Research**: 1.0.0
**License**: MIT

---

## Overview

Example test entry.

## Problem Addressed

Test.

## Key Features

- Feature A

## Technical Architecture

Simple.

## Installation & Usage

```bash
pip install example
```

## Relevance to Claude Code Development

{relevance_body}

## References

- [Example](https://example.com) (accessed 2026-06-01)

## Freshness Tracking

- **Last Verified**: 2026-06-01
- **Version at Verification**: 1.0.0
- **Next Review Recommended**: 2027-01-01
""",
        encoding="utf-8",
    )


def _issues_for(entry_json: dict, check: str) -> list[dict]:
    return [i for i in entry_json["entries"][0]["issues"] if i["check"] == check]


class TestRelevanceUnanchored:
    """relevance_unanchored: warns when the Relevance section cites no path and no search."""

    def test_unanchored_prose_warns(self, tmp_path: Path) -> None:
        """Generic prose naming no path and running no search gets the warning."""
        entry = tmp_path / "example.md"
        _write_entry(entry, UNANCHORED)
        issues = _issues_for(_run_json(entry), "relevance_unanchored")
        assert len(issues) == 1
        assert issues[0]["severity"] == "warning"

    def test_present_anchor_is_clean(self, tmp_path: Path) -> None:
        """A backticked repo-relative path satisfies the check."""
        entry = tmp_path / "example.md"
        _write_entry(entry, PRESENT_ANCHOR)
        assert _issues_for(_run_json(entry), "relevance_unanchored") == []

    def test_absence_anchor_is_clean(self, tmp_path: Path) -> None:
        """A git grep command string satisfies the check even with no path cited."""
        entry = tmp_path / "example.md"
        _write_entry(entry, ABSENCE_ANCHOR)
        assert _issues_for(_run_json(entry), "relevance_unanchored") == []

    def test_warning_alone_does_not_fail_the_entry(self, tmp_path: Path) -> None:
        """Warning severity: the check surfaces a skipped pass, it does not block the commit."""
        entry = tmp_path / "example.md"
        _write_entry(entry, UNANCHORED)
        assert _run_json(entry)["entries"][0]["status"] == "pass"

    def test_backticked_non_repo_path_does_not_satisfy(self, tmp_path: Path) -> None:
        """A backticked path outside the anchor scope is not evidence about this repo."""
        entry = tmp_path / "example.md"
        _write_entry(entry, "- Install into `/usr/local/bin/example` and run it.")
        issues = _issues_for(_run_json(entry), "relevance_unanchored")
        assert len(issues) == 1

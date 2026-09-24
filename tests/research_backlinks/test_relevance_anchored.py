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
from tempfile import TemporaryDirectory
from typing import Final

import pytest

pytestmark = pytest.mark.integration

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

# Dates straddling RELEVANCE_ANCHOR_EXEMPT_BEFORE in validate_research.py. The relevance checks
# are must-fix only for an entry a run just created or refreshed (validation-rules.md); the entry
# date is the observable proxy for that, so a current date is gated and an older one is not.
GATED_DATE = "2026-09-20"
EXEMPT_DATE = "2026-06-01"

# A present anchor naming a path that is not in the repository -- shape-valid, existence-invalid.
FABRICATED_ANCHOR = """\
- **Terminal workarounds** -> `.claude/rules/interactive-terminal-workarounds.md`
  - Today: "run the command non-interactively"
  - Change: none -- that rule already covers it
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


def _write_entry(path: Path, relevance_body: str, entry_date: str = GATED_DATE) -> None:
    """Write a minimal well-formed text-header entry with a given Relevance section body.

    Args:
        path: Where to write the entry.
        relevance_body: Body of the Relevance to Claude Code Development section.
        entry_date: Research Date and Last Verified value. Defaults to a date on or after
            RELEVANCE_ANCHOR_EXEMPT_BEFORE so the relevance checks apply; pass EXEMPT_DATE to
            exercise the pre-existing-corpus side of that cutoff.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""\
# Example

**Research Date**: {entry_date}
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

- **Last Verified**: {entry_date}
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

    def test_entry_predating_the_cutoff_is_exempt(self, tmp_path: Path) -> None:
        """The pre-existing corpus stays quiet: the anchor pass applies from its cutoff forward."""
        entry = tmp_path / "example.md"
        _write_entry(entry, UNANCHORED, entry_date=EXEMPT_DATE)
        assert _issues_for(_run_json(entry), "relevance_unanchored") == []


def _init_checkout(root: Path) -> None:
    """Make ``root`` a git checkout so repo_root_for resolves anchor paths against it."""
    subprocess.run([*_RUN_BOUNDED, "git", "init", "--quiet", str(root)], check=True, capture_output=True)


class TestRelevanceAnchorPaths:
    """relevance_anchor_path_missing: an anchor path that shape-matches but does not resolve.

    Shape alone is satisfied by a plausible-looking path nobody opened, which makes naming an
    invented file the cheapest way to clear the anchor gate. Every path in a real anchor record
    came from a git grep hit, so it exists.
    """

    def test_fabricated_path_warns(self, tmp_path: Path) -> None:
        """A path absent from the checkout is reported, however well-formed it looks."""
        _init_checkout(tmp_path)
        entry = tmp_path / "research" / "example.md"
        _write_entry(entry, FABRICATED_ANCHOR)
        issues = _issues_for(_run_json(entry), "relevance_anchor_path_missing")
        assert len(issues) == 1
        assert issues[0]["severity"] == "warning"
        assert ".claude/rules/interactive-terminal-workarounds.md" in issues[0]["message"]

    def test_resolving_path_is_clean(self, tmp_path: Path) -> None:
        """A path that exists in the checkout raises nothing."""
        _init_checkout(tmp_path)
        anchored = tmp_path / "plugins" / "agent-orchestration" / "skills" / "parallel-work" / "SKILL.md"
        anchored.parent.mkdir(parents=True)
        anchored.write_text("teams are not the default\n", encoding="utf-8")
        entry = tmp_path / "research" / "example.md"
        _write_entry(entry, PRESENT_ANCHOR)
        assert _issues_for(_run_json(entry), "relevance_anchor_path_missing") == []

    def test_absence_anchor_has_no_path_to_resolve(self, tmp_path: Path) -> None:
        """An absence anchor cites a command, not a path, so nothing is checked and nothing warns."""
        _init_checkout(tmp_path)
        entry = tmp_path / "research" / "example.md"
        _write_entry(entry, ABSENCE_ANCHOR)
        assert _issues_for(_run_json(entry), "relevance_anchor_path_missing") == []
        assert _issues_for(_run_json(entry), "relevance_anchor_paths_unchecked") == []

    def test_no_date_exemption(self, tmp_path: Path) -> None:
        """Unlike relevance_unanchored, this check has no cutoff.

        Predating Phase 1c excuses an entry from having anchors. It does not excuse an entry from
        citing a path that is not in the repository -- that claim is false at any age.
        """
        _init_checkout(tmp_path)
        entry = tmp_path / "research" / "example.md"
        _write_entry(entry, FABRICATED_ANCHOR, entry_date=EXEMPT_DATE)
        assert len(_issues_for(_run_json(entry), "relevance_anchor_path_missing")) == 1

    def test_outside_a_checkout_reports_unchecked_rather_than_clean(self) -> None:
        """No checkout root means the paths were not checked -- say so instead of passing silently."""
        with TemporaryDirectory(dir=Path.home()) as directory:
            entry = Path(directory) / "example.md"
            assert all(not (parent / ".git").exists() for parent in entry.resolve().parents)
            _write_entry(entry, FABRICATED_ANCHOR)
            issues = _issues_for(_run_json(entry), "relevance_anchor_paths_unchecked")
            assert len(issues) == 1
            assert _issues_for(_run_json(entry), "relevance_anchor_path_missing") == []

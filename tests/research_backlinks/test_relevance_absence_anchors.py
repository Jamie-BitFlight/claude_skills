"""Tests for the relevance_absence_anchor_* validator checks.

Phase 1c of extraction-methodology.md writes two anchor shapes into an entry's Relevance section:
an A1 presence anchor (a repo path plus a quoted line) and an A2 absence anchor (a ``git grep``
command plus the match count it returned). ``check_relevance_anchor_paths`` re-verifies A1 records
by confirming the cited path exists -- but nothing re-verified A2 records, because an A2 cites no
path and its ``-> 0 matches`` is a literal integer typed into the entry, indistinguishable in the
file from one that was never actually run.

These tests pin ``check_relevance_absence_anchors``, which closes that hole by re-executing every
recorded absence-anchor ``git grep`` command and comparing its count against the entry's own
record.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
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

# The exact scope every canonical absence-anchor command searches -- must match
# _ANCHOR_SCOPE_PATHSPECS in validate_research.py and extraction-methodology.md's Phase 1c step 2.
_SCOPE = ":/plugins/ :/.claude/skills/ :/.claude/agents/ :/rules/ :/docs/ :/AGENTS.md"

GATED_DATE = "2026-09-20"


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


def _issues_for(entry_json: dict, check: str) -> list[dict]:
    return [i for i in entry_json["entries"][0]["issues"] if i["check"] == check]


def _write_entry(path: Path, relevance_body: str, entry_date: str = GATED_DATE) -> None:
    """Write a minimal well-formed text-header entry with a given Relevance section body."""
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


def _init_checkout(root: Path) -> None:
    """Make ``root`` a git checkout so repo_root_for resolves it, and git grep can search it."""
    subprocess.run([*_RUN_BOUNDED, "git", "init", "--quiet", str(root)], check=True, capture_output=True)
    # git grep only searches tracked/staged content, not bare untracked files -- an empty initial
    # commit-less stage is fine, later tests add and stage their own marker files as needed.
    subprocess.run(
        [*_RUN_BOUNDED, "git", "-C", str(root), "config", "user.email", "test@example.com"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        [*_RUN_BOUNDED, "git", "-C", str(root), "config", "user.name", "Test"], check=True, capture_output=True
    )


def _stage(root: Path, relative_path: str, content: str) -> None:
    """Write a file under ``root`` and stage it, so git grep can find it."""
    target = root / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    subprocess.run([*_RUN_BOUNDED, "git", "-C", str(root), "add", "-A"], check=True, capture_output=True)


class TestAbsenceAnchorRefuted:
    """relevance_absence_anchor_refuted: re-run count differs from the recorded count."""

    def test_matching_count_passes(self, tmp_path: Path) -> None:
        """A recorded count that matches what git grep actually returns raises nothing."""
        _init_checkout(tmp_path)
        entry = tmp_path / "research" / "example.md"
        body = (
            "- **Some capability** -> nothing in scope searched\n"
            f'  - Today: `git grep --full-name -il "zzz-nonexistent-term-zzz" -- {_SCOPE}` → 0 matches\n'
        )
        _write_entry(entry, body)
        result = _run_json(entry)
        assert _issues_for(result, "relevance_absence_anchor_refuted") == []
        assert _issues_for(result, "relevance_absence_anchor_unparsed") == []
        assert _issues_for(result, "relevance_absence_anchors_unchecked") == []

    def test_refuted_count_fails(self, tmp_path: Path) -> None:
        """A recorded zero that git grep now contradicts is reported as an error."""
        _init_checkout(tmp_path)
        _stage(tmp_path, "plugins/marker.md", "This file mentions findme_term_xyz right here.\n")
        entry = tmp_path / "research" / "example.md"
        body = (
            "- **Some capability** -> nothing in scope searched\n"
            f'  - Today: `git grep --full-name -il "findme_term_xyz" -- {_SCOPE}` → 0 matches\n'
        )
        _write_entry(entry, body)
        issues = _issues_for(_run_json(entry), "relevance_absence_anchor_refuted")
        assert len(issues) == 1
        assert issues[0]["severity"] == "error"
        assert "findme_term_xyz" in issues[0]["message"]
        assert "recorded 0 matches" in issues[0]["message"]
        assert "returns 1 matches" in issues[0]["message"]

    def test_no_date_exemption(self, tmp_path: Path) -> None:
        """Unlike relevance_unanchored, a refuted count is reported at any entry date."""
        _init_checkout(tmp_path)
        _stage(tmp_path, "plugins/marker.md", "This file mentions findme_term_old right here.\n")
        entry = tmp_path / "research" / "example.md"
        body = (
            "- **Some capability** -> nothing in scope searched\n"
            f'  - Today: `git grep --full-name -il "findme_term_old" -- {_SCOPE}` → 0 matches\n'
        )
        _write_entry(entry, body, entry_date="2026-01-01")
        issues = _issues_for(_run_json(entry), "relevance_absence_anchor_refuted")
        assert len(issues) == 1

    def test_no_shell_interpretation_of_recorded_term(self, tmp_path: Path) -> None:
        """A term carrying shell metacharacters is passed as a literal argv element, never a shell string.

        If the term were interpolated into a shell command, ``$(touch ...)`` would create the
        marker file below as a side effect of running the check. It must not.
        """
        _init_checkout(tmp_path)
        entry = tmp_path / "research" / "example.md"
        marker = tmp_path / "should_not_exist_from_shell_injection.txt"
        term = f"$(touch {marker.name}; echo pwned)"
        body = (
            "- **Some capability** -> nothing in scope searched\n"
            f'  - Today: `git grep --full-name -il "{term}" -- {_SCOPE}` → 0 matches\n'
        )
        _write_entry(entry, body)
        result = _run_json(entry)
        # The literal string is not a real hit in the scope, so the recorded 0 should hold --
        # proving the check ran the term as a literal git grep pattern, not a shell command.
        assert _issues_for(result, "relevance_absence_anchor_refuted") == []
        assert _issues_for(result, "relevance_absence_anchor_unparsed") == []
        assert not marker.exists(), "shell metacharacters in the recorded term were executed by a shell"


class TestAbsenceAnchorUnparsed:
    """relevance_absence_anchor_unparsed: a git-grep-shaped line that is not the canonical form."""

    def test_malformed_command_is_unparsed(self, tmp_path: Path) -> None:
        """A command missing --full-name does not reproduce the canonical shape."""
        _init_checkout(tmp_path)
        entry = tmp_path / "research" / "example.md"
        body = (
            "- **Some capability** -> nothing in scope searched\n"
            f'  - Today: `git grep -il "some-term" -- {_SCOPE}` → 0 matches\n'
        )
        _write_entry(entry, body)
        result = _run_json(entry)
        issues = _issues_for(result, "relevance_absence_anchor_unparsed")
        assert len(issues) == 1
        assert issues[0]["severity"] == "error"
        assert "some-term" in issues[0]["message"]
        # A command that cannot be parsed also cannot be re-run, so it must not silently pass.
        assert _issues_for(result, "relevance_absence_anchor_refuted") == []

    def test_wrong_pathspec_scope_is_unparsed(self, tmp_path: Path) -> None:
        """A command missing one of the six fixed pathspecs does not reproduce the canonical shape."""
        _init_checkout(tmp_path)
        entry = tmp_path / "research" / "example.md"
        body = (
            "- **Some capability** -> nothing in scope searched\n"
            '  - Today: `git grep --full-name -il "some-term" -- :/plugins/ :/rules/` → 0 matches\n'
        )
        _write_entry(entry, body)
        issues = _issues_for(_run_json(entry), "relevance_absence_anchor_unparsed")
        assert len(issues) == 1

    def test_well_formed_units_alongside_a_malformed_one_still_flag_only_the_malformed_one(
        self, tmp_path: Path
    ) -> None:
        """A malformed unit does not suppress checking of a correctly formed unit in the same entry."""
        _init_checkout(tmp_path)
        entry = tmp_path / "research" / "example.md"
        body = (
            "- **Capability A** -> nothing in scope searched\n"
            f'  - Today: `git grep --full-name -il "well-formed-term" -- {_SCOPE}` → 0 matches\n'
            "- **Capability B** -> nothing in scope searched\n"
            f'  - Today: `git grep -il "malformed-term" -- {_SCOPE}` → 0 matches\n'
        )
        _write_entry(entry, body)
        result = _run_json(entry)
        assert _issues_for(result, "relevance_absence_anchor_refuted") == []
        unparsed = _issues_for(result, "relevance_absence_anchor_unparsed")
        assert len(unparsed) == 1
        assert "malformed-term" in unparsed[0]["message"]


class TestAbsenceAnchorsUnchecked:
    """relevance_absence_anchors_unchecked: absence anchors present but no .git was found."""

    def test_outside_a_checkout_reports_unchecked_rather_than_silently_passing(self, tmp_path: Path) -> None:
        """No checkout root means re-execution could not run -- say so instead of passing silently."""
        entry = tmp_path / "example.md"
        body = (
            "- **Some capability** -> nothing in scope searched\n"
            f'  - Today: `git grep --full-name -il "some-term" -- {_SCOPE}` → 0 matches\n'
        )
        _write_entry(entry, body)
        result = _run_json(entry)
        issues = _issues_for(result, "relevance_absence_anchors_unchecked")
        assert len(issues) == 1
        assert issues[0]["severity"] == "warning"
        assert _issues_for(result, "relevance_absence_anchor_refuted") == []

    def test_no_absence_anchors_raises_nothing(self, tmp_path: Path) -> None:
        """An entry with only a presence anchor (no git grep at all) triggers none of these checks."""
        entry = tmp_path / "example.md"
        body = (
            "- **Parallel fan-out** -> `plugins/agent-orchestration/skills/parallel-work/SKILL.md`\n"
            '  - Today: "teams are not the default"\n'
        )
        _write_entry(entry, body)
        result = _run_json(entry)
        assert _issues_for(result, "relevance_absence_anchor_refuted") == []
        assert _issues_for(result, "relevance_absence_anchor_unparsed") == []
        assert _issues_for(result, "relevance_absence_anchors_unchecked") == []

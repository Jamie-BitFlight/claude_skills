"""Exit-code tests for the validate-delegation PreToolUse hook against its stdin fixtures."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK = REPO_ROOT / ".claude" / "hooks" / "validate-delegation.cjs"
FIXTURES = REPO_ROOT / "tests" / "fixtures"


def run_hook(fixture_name: str) -> subprocess.CompletedProcess[str]:
    """Run the hook with one fixture file as its stdin.

    Args:
        fixture_name: Basename of a JSON file under tests/fixtures.

    Returns:
        The completed process, with captured stdout and stderr.
    """
    return subprocess.run(
        ["node", str(HOOK)],
        input=(FIXTURES / fixture_name).read_text(encoding="utf-8"),
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize(
    ("fixture_name", "expected_exit", "expected_violation"),
    [
        ("dispatch-specialist.json", 0, None),
        ("dispatch-generic.json", 0, None),
        ("dispatch-no-phase.json", 2, "Rule 3: Missing PHASE: line"),
        ("dispatch-no-observations-or-files.json", 2, "Rule 4: Missing OBSERVATIONS + CONTEXT"),
    ],
)
def test_hook_exit_code_matches_fixture(fixture_name: str, expected_exit: int, expected_violation: str | None) -> None:
    """Each fixture yields the documented exit code and, on rejection, names the violated rule."""
    result = run_hook(fixture_name)
    assert result.returncode == expected_exit, result.stderr
    if expected_violation is None:
        assert result.stderr == ""
    else:
        assert expected_violation in result.stderr
        assert "Required template (plugins/agent-orchestration/skills/delegate/SKILL.md" in result.stderr

"""Tests for the runtime-escape audit gate (`skills/lint/scripts/audit_runtime_escapes.py`).

Tests: The repo-path detector's decision on a line, and the process exit code a caller acts on.
How: Load the script by path (its directory is not on `pythonpath`), drive `_scan_line` for
     per-shape assertions, and run the script as a subprocess over a temporary plugin tree for
     the exit-code assertions.
Why: The script is a publishing gate whose exit code certifies runtime text as portable. It had
     no tests, and a de-duplication guard keyed on a whole-line substring search made it exit 0
     on content it should have flagged — a green result that reads as evidence of cleanliness.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from types import ModuleType

_SCRIPT = Path(__file__).resolve().parents[1] / "skills" / "lint" / "scripts" / "audit_runtime_escapes.py"

# A sibling plugin name and the scanned plugin's own name, as `_scan_line` expects them.
_SIBLINGS = frozenset({"other-plugin"})
_OWN = "probe"


def _load() -> ModuleType:
    """Import the audit script by path.

    Returns:
        The imported module.
    """
    spec = importlib.util.spec_from_file_location("audit_runtime_escapes", _SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Registered before execution because `@dataclass` resolves its own module from `sys.modules`.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_audit = _load()


def _repo_path_tokens(line: str) -> list[str]:
    """Return the repo-path tokens reported for one line of runtime text.

    Args:
        line: The raw source line.

    Returns:
        Every reported `repo-path` token, in detection order.
    """
    found = _audit._scan_line("skills/demo/SKILL.md", 1, line, _SIBLINGS, _OWN)
    return [e.token for e in found if e.kind == "repo-path"]


def _make_plugin(tmp_path: Path, body: str) -> Path:
    """Write a one-file probe plugin under a `plugins/` root and return its directory.

    Args:
        tmp_path: Test-scoped temporary directory.
        body: The SKILL.md body to scan.

    Returns:
        The probe plugin directory, suitable for `--plugin-dir`.
    """
    plugin_dir = tmp_path / "plugins" / _OWN
    skill_dir = plugin_dir / "skills" / "demo"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(body, encoding="utf-8")
    return plugin_dir


def _run_gate(plugin_dir: Path) -> subprocess.CompletedProcess[str]:
    """Run the audit script as a caller would and capture its exit code.

    Args:
        plugin_dir: The plugin directory to scan.

    Returns:
        The completed process, with `returncode` carrying the gate verdict.
    """
    return subprocess.run(
        [sys.executable, str(_SCRIPT), "--plugin-dir", str(plugin_dir)], capture_output=True, text=True, check=False
    )


# ===========================================================================
# The reported defect: a leading slash silenced the gate
# ===========================================================================


class TestLeadingSlashReproduction:
    """The two cases that differ only by a leading slash must reach the same verdict."""

    def test_bare_repo_path_is_reported(self) -> None:
        """A bare repo-root path is a finding."""
        assert _repo_path_tokens("See rules/style.md for the convention.") == ["rules/style.md"]

    def test_absolute_repo_path_is_reported(self) -> None:
        """The same path written absolutely is also a finding, reported with its leading slash."""
        assert _repo_path_tokens("See /rules/style.md for the convention.") == ["/rules/style.md"]

    def test_both_forms_exit_nonzero(self, tmp_path: Path) -> None:
        """The exit code — what a caller acts on — is 1 for both forms.

        The gate previously exited 0 on the leading-slash form, certifying it as clean.
        """
        with_slash = _run_gate(_make_plugin(tmp_path / "a", "See /rules/style.md for the convention.\n"))
        without_slash = _run_gate(_make_plugin(tmp_path / "b", "See rules/style.md for the convention.\n"))
        assert with_slash.returncode == 1, with_slash.stdout
        assert without_slash.returncode == 1, without_slash.stdout

    def test_clean_content_exits_zero(self, tmp_path: Path) -> None:
        """A plugin with no escapes still exits 0, so exit 1 stays meaningful."""
        result = _run_gate(_make_plugin(tmp_path, "Read the bundled reference beside this file.\n"))
        assert result.returncode == 0, result.stdout


# ===========================================================================
# Every repo-root directory, not just `rules/`
# ===========================================================================


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("Run /tests/test_x.py to check.", "/tests/test_x.py"),
        ("Open /examples/demo.md for a sample.", "/examples/demo.md"),
        ("Open /research/entry.md.", "/research/entry.md"),
        ("Open /tests_backlog/test_y.py.", "/tests_backlog/test_y.py"),
    ],
)
def test_absolute_paths_into_every_repo_root_are_reported(line: str, expected: str) -> None:
    """The leading-slash blindness covered every entry in `_REPO_ROOT_DIRS`, not only `rules/`."""
    assert _repo_path_tokens(line) == [expected]


# ===========================================================================
# Shapes the whole-line guard also swallowed
# ===========================================================================


class TestWholeLineContamination:
    """A match must be judged by what precedes it, not by a search of the whole line."""

    def test_bare_path_survives_a_longer_path_later_on_the_line(self) -> None:
        """An unrelated longer path elsewhere on the line must not silence a bare one."""
        line = "Read rules/style.md; it lives at plugins/other-plugin/rules/style.md."
        assert _repo_path_tokens(line) == ["rules/style.md"]

    def test_bare_path_survives_a_longer_path_earlier_on_the_line(self) -> None:
        """The same, with the longer path first."""
        assert _repo_path_tokens("Read docs/rules/style.md and rules/style.md.") == ["rules/style.md"]

    def test_each_occurrence_is_reported_independently(self) -> None:
        """Two bare occurrences on one line are two findings."""
        assert _repo_path_tokens("Read rules/style.md and rules/style.md.") == ["rules/style.md", "rules/style.md"]

    def test_absolute_markdown_link_target_is_reported(self) -> None:
        """An absolute path inside a markdown link is a finding like any other."""
        assert _repo_path_tokens("See [style](/rules/style.md).") == ["/rules/style.md"]

    def test_anchor_fragment_does_not_hide_the_path(self) -> None:
        """A trailing `#fragment` leaves the path itself reportable."""
        assert _repo_path_tokens("See rules/style.md#heading for the rule.") == ["rules/style.md"]


# ===========================================================================
# Relative climbs: one depth rule, applied to prose as well as to links
# ===========================================================================


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("See ./rules/style.md for the rule.", []),
        ("See ../rules/style.md for the rule.", []),
        ("See ../../rules/style.md for the rule.", []),
        ("See ../../../rules/style.md for the rule.", ["../../../rules/style.md"]),
    ],
)
def test_relative_climbs_use_the_plugin_escape_depth(line: str, expected: list[str]) -> None:
    """Shallow climbs stay inside the plugin; a climb past the plugin root is a finding.

    The depth is `_escapes_plugin`'s, reused rather than restated, so prose and markdown links
    cannot drift apart.
    """
    assert _repo_path_tokens(line) == expected


# ===========================================================================
# Exemptions the fix must not break
# ===========================================================================


@pytest.mark.parametrize(
    "line",
    [
        "Read ${CLAUDE_PLUGIN_ROOT}/rules/style.md now.",
        "Read $CLAUDE_PLUGIN_ROOT/rules/style.md now.",
        "Read ${CLAUDE_SKILL_DIR}/rules/style.md now.",
        "Read <plugin>/rules/style.md now.",
        "See https://example.com/rules/style.md online.",
        "See docs/rules/style.md there.",
        "See plugins/other-plugin/rules/style.md there.",
        "See my-tests/helper.py beside this file.",
        "See ./test-examples/mock_test.t beside this file.",
    ],
)
def test_exempt_and_internal_shapes_are_not_repo_paths(line: str) -> None:
    """Portable prefixes, placeholders, URLs, and paths under another directory stay silent."""
    assert _repo_path_tokens(line) == []


def test_fenced_blocks_are_never_findings(tmp_path: Path) -> None:
    """A fence is an illustration, so a document may quote the anti-pattern verbatim."""
    body = "Example of what not to write:\n\n```\nSee /rules/style.md for the rule.\n```\n"
    assert _run_gate(_make_plugin(tmp_path, body)).returncode == 0


def test_cross_plugin_path_is_still_its_own_class(tmp_path: Path) -> None:
    """Suppressing the repo-path sub-match must not suppress the cross-plugin finding itself."""
    found = _audit._scan_line("skills/demo/SKILL.md", 1, "See plugins/other-plugin/rules/x.md.", _SIBLINGS, _OWN)
    assert [e.kind for e in found] == ["cross-plugin-path"]


# ===========================================================================
# Measured limits of the detector, recorded so closing one is visible
# ===========================================================================


@pytest.mark.parametrize(
    "line",
    ["See rules\\style.md for the rule.", "See RULES/style.md for the rule.", "See rules%2Fstyle.md for the rule."],
)
@pytest.mark.xfail(
    strict=True,
    reason=(
        "`_REPO_PATH_RE` matches lowercase, forward-slash-separated segments only, so a backslash "
        "separator, an uppercase directory, or a URL-encoded separator never reaches the detector. "
        "A separate mechanism from the de-duplication guard; widening the pattern changes what the "
        "gate flags across every plugin and needs its own triage."
    ),
)
def test_known_pattern_level_gaps(line: str) -> None:
    """Record the shapes the pattern itself cannot see; this fails loudly if one is closed."""
    assert _repo_path_tokens(line) != []

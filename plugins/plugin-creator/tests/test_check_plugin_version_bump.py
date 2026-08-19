"""Tests for check_plugin_version_bump.py — the CI version-bump gate and audit.

Background (issue #3021): auto_sync_manifests.py's pre-commit-hook mode only
inspects *staged* changes (``git diff --cached``), which is always empty on a
plain CI checkout. A PR merged via GitHub's UI/API never runs the local
pre-commit hook either. Both gaps combined let PR #3005 land a plugin content
change with zero corresponding ``plugin.json`` version bump, so the
marketplace cache -- keyed on that version -- kept serving stale content.

This module's ``--check`` mode closes the gap with a real base-ref-vs-head-ref
git diff (not a staged-index diff), so it works identically on a fresh CI
checkout of a squash-merged PR. Its ``--audit`` mode finds plugins where that
gap already bit before the gate existed.

Test isolation strategy:
- Pure-logic tests (diff parsing, version comparison, CLI dispatch) monkeypatch
  ``run_git_command`` / ``read_ref_json`` to avoid real subprocess calls.
- Integration tests build real temp git repos (mirroring
  ``test_auto_sync_manifests.py``'s ``TestReadRefJson`` pattern) so the actual
  git-diff-between-refs mechanism -- the core fix -- is exercised end to end,
  including the exact "GitHub squash-merge, no staged changes" failure mode.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Module import -- both scripts live in the same directory so the module
# under test's own `from auto_sync_manifests import ...` resolves once that
# directory is on sys.path (mirroring how `uv run <script>` adds the script's
# own directory to sys.path[0]).
# ---------------------------------------------------------------------------
_SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

_SCRIPT_PATH = _SCRIPTS_DIR / "check_plugin_version_bump.py"
_spec = importlib.util.spec_from_file_location("check_plugin_version_bump", _SCRIPT_PATH)
if _spec and _spec.loader:
    gate = importlib.util.module_from_spec(_spec)
    sys.modules["check_plugin_version_bump"] = gate
    _spec.loader.exec_module(gate)
else:
    msg = f"Could not load module from {_SCRIPT_PATH}"
    raise ImportError(msg)


# ============================================================================
# Area 1: plugins_with_diff -- parsing a base..head diff into plugin names
# ============================================================================


class TestPluginsWithDiff:
    """Tests for plugins_with_diff -- extracts plugin names from a ref diff."""

    def test_extracts_plugin_names_from_changed_paths(self, monkeypatch: Any) -> None:
        """Every plugins/<name>/... path in the diff contributes its plugin name.

        Tests: plugins_with_diff
        How: Monkeypatch run_git_command to return a mixed diff (two plugins,
             one non-plugin path); call plugins_with_diff("main", "HEAD").
        Why: This is the replacement for the staged-index scan -- it must
             correctly reduce a real base..head diff to the set of plugins
             whose content actually changed in the PR.
        """
        # Arrange
        diff_output = "plugins/foo/skills/x/SKILL.md\nplugins/bar/README.md\nAGENTS.md\n"
        monkeypatch.setattr(gate, "run_git_command", lambda _args: diff_output)

        # Act
        result = gate.plugins_with_diff("main", "HEAD")

        # Assert
        assert result == {"foo", "bar"}

    def test_no_plugin_paths_returns_empty_set(self, monkeypatch: Any) -> None:
        """A diff touching no plugins/ path returns an empty set.

        Tests: plugins_with_diff
        How: Monkeypatch run_git_command to return only non-plugin paths.
        Why: The gate must not false-positive on repo-root or .claude/ changes.
        """
        # Arrange
        monkeypatch.setattr(gate, "run_git_command", lambda _args: "AGENTS.md\n.claude/settings.json\n")

        # Act
        result = gate.plugins_with_diff("main", "HEAD")

        # Assert
        assert result == set()


# ============================================================================
# Area 2: check_version_bumps -- the CI gate's core decision
# ============================================================================


class TestCheckVersionBumps:
    """Tests for check_version_bumps -- flags plugins that changed without a bump."""

    def test_flags_plugin_whose_version_did_not_increase(self, monkeypatch: Any) -> None:
        """A changed plugin with an unchanged version is reported as missing a bump.

        Tests: check_version_bumps
        How: One plugin ("dh") changed; base and head both report version 9.0.15.
        Why: This is exactly the #3021 failure mode -- PR #3005 changed
             development-harness content but plugin.json stayed at 9.0.15.
        """
        # Arrange
        monkeypatch.setattr(gate, "plugins_with_diff", lambda _base, _head: {"dh"})

        def _fake_read_ref_json(_ref: str, _path: str) -> dict[str, str]:
            return {"version": "9.0.15"}

        monkeypatch.setattr(gate, "read_ref_json", _fake_read_ref_json)

        # Act
        result = gate.check_version_bumps("main", "HEAD")

        # Assert
        assert result == ["dh"]

    def test_passes_when_version_strictly_increased(self, monkeypatch: Any) -> None:
        """A changed plugin whose version increased at head is not flagged.

        Tests: check_version_bumps
        How: base version "9.0.15", head version "9.0.16".
        Why: This is the correct, bumped state -- the gate must not false-positive.
        """
        # Arrange
        monkeypatch.setattr(gate, "plugins_with_diff", lambda _base, _head: {"dh"})

        def _fake_read_ref_json(ref: str, _path: str) -> dict[str, str]:
            return {"version": "9.0.16" if ref == "HEAD" else "9.0.15"}

        monkeypatch.setattr(gate, "read_ref_json", _fake_read_ref_json)

        # Act
        result = gate.check_version_bumps("main", "HEAD")

        # Assert
        assert result == []

    def test_exempts_newly_added_plugin(self, monkeypatch: Any) -> None:
        """A plugin absent at base_ref (brand new) is exempt -- no prior version to compare.

        Tests: check_version_bumps
        How: base has no plugin.json (read_ref_json returns None for base ref).
        Why: A newly created plugin has no "bump" concept; flagging it would be a
             false positive that blocks legitimate new-plugin PRs.
        """
        # Arrange
        monkeypatch.setattr(gate, "plugins_with_diff", lambda _base, _head: {"brand-new"})

        def _fake_read_ref_json(ref: str, _path: str) -> dict[str, str] | None:
            return None if ref == "main" else {"version": "0.1.0"}

        monkeypatch.setattr(gate, "read_ref_json", _fake_read_ref_json)

        # Act
        result = gate.check_version_bumps("main", "HEAD")

        # Assert
        assert result == []

    def test_exempts_deleted_plugin(self, monkeypatch: Any) -> None:
        """A plugin absent at head_ref (fully deleted) is exempt.

        Tests: check_version_bumps
        How: head has no plugin.json (read_ref_json returns None for HEAD).
        Why: A deleted plugin has nothing left to bump.
        """
        # Arrange
        monkeypatch.setattr(gate, "plugins_with_diff", lambda _base, _head: {"removed"})

        def _fake_read_ref_json(ref: str, _path: str) -> dict[str, str] | None:
            return None if ref == "HEAD" else {"version": "1.0.0"}

        monkeypatch.setattr(gate, "read_ref_json", _fake_read_ref_json)

        # Act
        result = gate.check_version_bumps("main", "HEAD")

        # Assert
        assert result == []

    def test_multiple_plugins_returns_sorted_missing_list(self, monkeypatch: Any) -> None:
        """Multiple unbumped plugins are all reported, sorted by name.

        Tests: check_version_bumps
        How: Two plugins changed, neither bumped.
        Why: A PR touching several plugins must surface every gap, not just
             the first one found.
        """
        # Arrange
        monkeypatch.setattr(gate, "plugins_with_diff", lambda _base, _head: {"zzz", "aaa"})
        monkeypatch.setattr(gate, "read_ref_json", lambda _ref, _path: {"version": "1.0.0"})

        # Act
        result = gate.check_version_bumps("main", "HEAD")

        # Assert
        assert result == ["aaa", "zzz"]


# ============================================================================
# Area 3: find_last_version_bump_commit -- retroactive audit's git-log walk
# ============================================================================


class TestFindLastVersionBumpCommit:
    """Tests for find_last_version_bump_commit."""

    def test_returns_commit_where_version_actually_changed(self, monkeypatch: Any) -> None:
        """Walks commit history and returns the first commit whose parent had a different version.

        Tests: find_last_version_bump_commit
        How: Three commits in log order [c3, c2, c1]; only c2 -> c1 changed the
             version (c3 and c2 both "1.0.1"; c1 "1.0.0").
        Why: The most recent commit touching plugin.json is not necessarily a
             bump commit (e.g. a docs edit inside the same file) -- the audit
             must find the actual version-changing commit, not just the latest.
        """
        # Arrange
        versions = {"c3": "1.0.1", "c2": "1.0.1", "c1": "1.0.0", "c1^": None}
        parents = {"c3": "c2", "c2": "c1", "c1": ""}

        monkeypatch.setattr(gate, "run_git_command", lambda args: self._fake_log_or_parent(args, parents))

        def _fake_read_ref_json(ref: str, _path: str) -> dict[str, str] | None:
            version = versions.get(ref)
            return {"version": version} if version else None

        monkeypatch.setattr(gate, "read_ref_json", _fake_read_ref_json)

        # Act
        result = gate.find_last_version_bump_commit(".claude-plugin/plugin.json")

        # Assert -- c2 is where the version last changed (c1 -> c2 is 1.0.0 -> 1.0.1)
        assert result == "c2"

    @staticmethod
    def _fake_log_or_parent(args: list[str], parents: dict[str, str]) -> str:
        """Route a monkeypatched run_git_command call to log-history or rev-parse-parent output."""
        if args[0] == "log":
            return "c3\nc2\nc1"
        # args like ["rev-parse", "--verify", "--quiet", "c3^"]
        commit = args[-1].removesuffix("^")
        return parents.get(commit, "")

    def test_returns_none_when_plugin_json_has_no_history(self, monkeypatch: Any) -> None:
        """No commit at all touches plugin.json -- returns None (no baseline exists).

        Tests: find_last_version_bump_commit
        How: `git log -- <path>` returns empty output (file was never committed).
        Why: audit_version_drift must skip a plugin with zero manifest history
             entirely rather than crash or false-positive.
        """
        # Arrange
        monkeypatch.setattr(gate, "run_git_command", lambda _args: "")
        monkeypatch.setattr(gate, "read_ref_json", lambda _ref, _path: {"version": "1.0.0"})

        # Act
        result = gate.find_last_version_bump_commit(".claude-plugin/plugin.json")

        # Assert
        assert result is None

    def test_root_commit_returned_when_version_set_once_and_never_bumped_since(self, monkeypatch: Any) -> None:
        """Version set at creation and never bumped since -- the root commit is the baseline.

        Tests: find_last_version_bump_commit
        How: Two commits, c2 -> c1, both report version "1.0.0" (c1 is the root,
             its own parent lookup returns empty).
        Why: The root commit still counts as a valid drift baseline -- a plugin
             that has NEVER bumped is exactly the case the audit must catch
             when later content changes without any bump at all.
        """
        # Arrange
        parents = {"c2": "c1", "c1": ""}

        def _fake_run(args: list[str]) -> str:
            if args[0] == "log":
                return "c2\nc1"
            commit = args[-1].removesuffix("^")
            return parents.get(commit, "")

        monkeypatch.setattr(gate, "run_git_command", _fake_run)
        monkeypatch.setattr(gate, "read_ref_json", lambda _ref, _path: {"version": "1.0.0"})

        # Act
        result = gate.find_last_version_bump_commit(".claude-plugin/plugin.json")

        # Assert -- c1 is the root; its version was never subsequently bumped
        assert result == "c1"

    def test_root_commit_counts_as_the_bump_point(self, monkeypatch: Any) -> None:
        """A file's creation commit (no parent) counts as its version-bump point.

        Tests: find_last_version_bump_commit
        How: Single commit "c1" with no parent (rev-parse c1^ fails -> "").
        Why: The very first commit that set plugin.json's version is a valid
             baseline -- there's nothing before it to compare against.
        """
        # Arrange
        monkeypatch.setattr(gate, "run_git_command", lambda args: "c1" if args[0] == "log" else "")
        monkeypatch.setattr(gate, "read_ref_json", lambda _ref, _path: {"version": "1.0.0"})

        # Act
        result = gate.find_last_version_bump_commit(".claude-plugin/plugin.json")

        # Assert
        assert result == "c1"


# ============================================================================
# Area 4: CLI dispatch -- _run_check / _run_audit
# ============================================================================


class TestRunCheck:
    """Tests for _run_check -- the --check CLI mode."""

    def test_returns_1_and_lists_missing_plugins(self, monkeypatch: Any, capsys: Any) -> None:
        """Missing bumps produce a non-zero exit and a readable stderr report.

        Tests: _run_check
        How: check_version_bumps returns ["dh"].
        Why: A required CI check must fail (non-zero) and explain what to fix
             so the PR author isn't left guessing.
        """
        # Arrange
        monkeypatch.setattr(gate, "check_version_bumps", lambda _base, _head="HEAD": ["dh"])

        # Act
        exit_code = gate._run_check("main")

        # Assert
        assert exit_code == 1
        captured = capsys.readouterr()
        assert "dh" in captured.err

    def test_returns_0_when_nothing_missing(self, monkeypatch: Any) -> None:
        """No missing bumps -- gate passes.

        Tests: _run_check
        How: check_version_bumps returns [].
        Why: The gate must not block PRs that correctly bumped every changed plugin.
        """
        # Arrange
        monkeypatch.setattr(gate, "check_version_bumps", lambda _base, _head="HEAD": [])

        # Act
        exit_code = gate._run_check("main")

        # Assert
        assert exit_code == 0

    def test_returns_1_when_no_base_ref_resolvable(self, monkeypatch: Any) -> None:
        """No explicit base ref and resolve_base() returns None -- gate fails loudly.

        Tests: _run_check
        How: base_ref_arg=None, resolve_base() monkeypatched to return None.
        Why: Silently skipping the check when no base is resolvable would defeat
             its purpose -- fail loud instead so a misconfigured CI job is caught.
        """
        # Arrange
        monkeypatch.setattr(gate, "resolve_base", lambda: None)

        # Act
        exit_code = gate._run_check(None)

        # Assert
        assert exit_code == 1

    def test_passes_explicit_head_ref_through_to_check_version_bumps(self, monkeypatch: Any) -> None:
        """An explicit --head-ref is forwarded verbatim, not silently replaced with HEAD.

        Tests: _run_check
        How: Capture the (base, head) pair check_version_bumps is called with.
        Why: Greptile P1 / Copilot finding (PR #3022): on a GitHub Actions
             pull_request trigger, actions/checkout's default HEAD is a
             synthetic base+PR merge commit -- callers must be able to point
             the diff at the PR's real head ref instead of the implicit HEAD.
        """
        # Arrange
        seen: list[tuple[str, str]] = []
        monkeypatch.setattr(gate, "check_version_bumps", lambda base, head: seen.append((base, head)) or [])

        # Act
        exit_code = gate._run_check("main", "origin/feature-branch")

        # Assert
        assert exit_code == 0
        assert seen == [("main", "origin/feature-branch")]

    def test_defaults_head_ref_to_head_when_not_given(self, monkeypatch: Any) -> None:
        """Omitting --head-ref preserves the original HEAD-implicit behaviour.

        Tests: _run_check
        How: Call with head_ref_arg=None (the CLI default) and capture the
             head ref check_version_bumps receives.
        Why: Falsification check for the previous test -- proves the new
             parameter is additive and does not break local/non-PR usage
             (e.g. a developer running --check with just --base-ref).
        """
        # Arrange
        seen: list[tuple[str, str]] = []
        monkeypatch.setattr(gate, "check_version_bumps", lambda base, head: seen.append((base, head)) or [])

        # Act
        exit_code = gate._run_check("main", None)

        # Assert
        assert exit_code == 0
        assert seen == [("main", "HEAD")]


class TestRunAudit:
    """Tests for _run_audit -- the --audit CLI mode."""

    def test_reports_no_drift(self, tmp_path: Path, monkeypatch: Any, capsys: Any) -> None:
        """No drifted plugins -- reports a clean JSON result and exits 0.

        Tests: _run_audit
        How: audit_version_drift monkeypatched to return [].
        Why: The audit is report-only (issue #3021 AC #2); a clean repo state
             must be machine-parseable, not silence. Per AGENTS.md's "CLI and
             script output" convention, every caller of this repo's scripts
             is an agent/CI process, never a human at a terminal, so the
             result is compact JSON rather than prose (Greptile P2 finding).
        """
        # Arrange
        monkeypatch.chdir(tmp_path)
        (tmp_path / "plugins").mkdir()
        monkeypatch.setattr(gate, "audit_version_drift", lambda _root: [])

        # Act
        exit_code = gate._run_audit()

        # Assert
        assert exit_code == 0
        assert json.loads(capsys.readouterr().out) == {"drifted_plugins": []}

    def test_reports_drifted_plugins(self, tmp_path: Path, monkeypatch: Any, capsys: Any) -> None:
        """Drifted plugins are reported as a JSON list; still exits 0 (report-only).

        Tests: _run_audit
        How: audit_version_drift monkeypatched to return ["dh"].
        Why: Report-only means CI never blocks on this mode -- it exists purely
             to surface a gap like #3021's for manual/scripted follow-up, and
             that follow-up tooling must be able to parse the result directly.
        """
        # Arrange
        monkeypatch.chdir(tmp_path)
        (tmp_path / "plugins").mkdir()
        monkeypatch.setattr(gate, "audit_version_drift", lambda _root: ["dh"])

        # Act
        exit_code = gate._run_audit()

        # Assert
        assert exit_code == 0
        assert json.loads(capsys.readouterr().out) == {"drifted_plugins": ["dh"]}


class TestRunRepair:
    """Tests for _run_repair -- the --repair CLI mode."""

    def test_reports_no_repairs_when_no_drift(self, tmp_path: Path, monkeypatch: Any, capsys: Any) -> None:
        """No drifted plugins -- reports an empty JSON result and exits 0.

        Tests: _run_repair
        How: audit_version_drift monkeypatched to return [].
        Why: --repair must be a safe no-op on a healthy repo -- the post-merge
             CI job runs this unconditionally on every push (T3), so a clean
             tree must never be mistaken for an error.
        """
        # Arrange
        monkeypatch.chdir(tmp_path)
        (tmp_path / "plugins").mkdir()
        monkeypatch.setattr(gate, "audit_version_drift", lambda _root: [])

        # Act
        exit_code = gate._run_repair()

        # Assert
        assert exit_code == 0
        assert json.loads(capsys.readouterr().out) == {"repaired": [], "failed": []}

    def test_reports_repaired_plugins(self, tmp_path: Path, monkeypatch: Any, capsys: Any) -> None:
        """Drifted plugins are repaired and reported with their old/new versions.

        Tests: _run_repair
        How: audit_version_drift monkeypatched to return ["dh"];
             repair_plugin_version monkeypatched to simulate a successful bump.
        Why: The repair job's commit message and evidence trail depend on this
             JSON naming each plugin and its version delta (T1 spec).
        """
        # Arrange
        monkeypatch.chdir(tmp_path)
        (tmp_path / "plugins").mkdir()
        monkeypatch.setattr(gate, "audit_version_drift", lambda _root: ["dh"])
        monkeypatch.setattr(gate, "repair_plugin_version", lambda _plugin_dir: ("9.0.17", "9.0.18"))

        # Act
        exit_code = gate._run_repair()

        # Assert
        assert exit_code == 0
        assert json.loads(capsys.readouterr().out) == {
            "repaired": [{"plugin": "dh", "old_version": "9.0.17", "new_version": "9.0.18"}],
            "failed": [],
        }

    def test_failed_repair_is_reported_and_exits_nonzero(self, tmp_path: Path, monkeypatch: Any, capsys: Any) -> None:
        """A drifted plugin that cannot be repaired is surfaced, not silently dropped.

        Tests: _run_repair
        How: audit_version_drift monkeypatched to return a drifted plugin;
             repair_plugin_version monkeypatched to return None (its documented
             failure contract -- see repair_plugin_version's docstring).
        Why: Copilot review on PR #3032 flagged that a drifted plugin whose
             current plugin.json has a missing/non-string version made
             _run_repair silently drop it from the output while still exiting
             0 -- CI would report success while the repair never landed.
             Per .claude/rules/silent-failure-prevention.md, a write operation
             must report what changed (or, here, what could not be changed).
        """
        # Arrange
        monkeypatch.chdir(tmp_path)
        (tmp_path / "plugins").mkdir()
        monkeypatch.setattr(gate, "audit_version_drift", lambda _root: ["broken"])
        monkeypatch.setattr(gate, "repair_plugin_version", lambda _plugin_dir: None)

        # Act
        exit_code = gate._run_repair()

        # Assert
        assert exit_code == 1
        assert json.loads(capsys.readouterr().out) == {"repaired": [], "failed": ["broken"]}


class TestRepairPluginVersion:
    """Tests for repair_plugin_version's documented None-on-malformed-input contract."""

    def test_returns_none_on_missing_plugin_json(self, tmp_path: Path) -> None:
        """A plugin.json that does not exist on disk returns None instead of crashing.

        Tests: repair_plugin_version
        Why: Copilot review on PR #3032 (check_plugin_version_bump.py:190) flagged
             that repair_plugin_version's docstring claims it returns None for a
             malformed/missing plugin.json, but it called read_text()+json.loads()
             with no FileNotFoundError handling -- --repair would crash instead.
        """
        plugin_dir = tmp_path / "plugins" / "missing"
        (plugin_dir / ".claude-plugin").mkdir(parents=True)

        assert gate.repair_plugin_version(plugin_dir) is None

    def test_returns_none_on_malformed_json(self, tmp_path: Path) -> None:
        """A plugin.json containing invalid JSON returns None instead of crashing.

        Tests: repair_plugin_version
        Why: Same Copilot finding as test_returns_none_on_missing_plugin_json --
             json.loads() previously propagated JSONDecodeError uncaught.
        """
        plugin_dir = tmp_path / "plugins" / "malformed"
        (plugin_dir / ".claude-plugin").mkdir(parents=True)
        (plugin_dir / ".claude-plugin" / "plugin.json").write_text("{not valid json", encoding="utf-8")

        assert gate.repair_plugin_version(plugin_dir) is None

    def test_returns_none_on_malformed_version_string(self, tmp_path: Path) -> None:
        """A syntactically valid plugin.json with a non-semver version string returns None.

        Tests: repair_plugin_version
        Why: Greptile review on PR #3032 (check_plugin_version_bump.py:193-197) flagged
             that the pre-fix type check only verified `version` was a `str`, not that
             it was a well-formed `major.minor.patch` value. A drifted manifest with
             `"version": "abc"` passed that check, and `bump_version` silently coerced
             it to "0.1.0" -- reporting a successful repair while actually downgrading
             the plugin instead of surfacing the invalid version as a failed repair.
        """
        plugin_dir = tmp_path / "plugins" / "malformed-version"
        (plugin_dir / ".claude-plugin").mkdir(parents=True)
        (plugin_dir / ".claude-plugin" / "plugin.json").write_text(
            json.dumps({"name": "malformed-version", "version": "abc"}), encoding="utf-8"
        )

        assert gate.repair_plugin_version(plugin_dir) is None


# ============================================================================
# Area 5: Integration tests -- real git repos, no mocking
# ============================================================================

# integration: exercises real git subprocesses end to end

_GIT_ENV: dict[str, str] = {
    "GIT_AUTHOR_NAME": "Test",
    "GIT_AUTHOR_EMAIL": "t@t",
    "GIT_COMMITTER_NAME": "Test",
    "GIT_COMMITTER_EMAIL": "t@t",
    "PATH": os.environ["PATH"],
}


def _git(repo: Path, *args: str) -> str:
    """Run a git command in *repo* with a hermetic identity and return stdout."""
    result = subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, env=_GIT_ENV, text=True)
    return result.stdout.strip()


def _write_plugin_json(repo: Path, plugin_name: str, version: str) -> Path:
    """Write plugins/<plugin_name>/.claude-plugin/plugin.json with *version*."""
    path = repo / "plugins" / plugin_name / ".claude-plugin" / "plugin.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"name": plugin_name, "version": version}) + "\n", encoding="utf-8")
    return path


@pytest.mark.integration
class TestFindLastVersionBumpCommitIntegration:
    """End-to-end test for the root-commit stderr-noise fix (PR #3022 review)."""

    def test_root_commit_produces_no_stderr_noise(self, tmp_path: Path, monkeypatch: Any, capsys: Any) -> None:
        """A true git root commit's parent lookup must not leak "fatal: ..." to stderr.

        Tests: find_last_version_bump_commit (real git subprocess, no mocking)
        How: A one-commit repo -- the root commit's `<sha>^` does not exist.
             Bare `git rev-parse <sha>^` exits non-zero with a "fatal: ..."
             message for that case, and run_git_command() forwards any
             non-zero-exit stderr straight to this process's stderr
             (auto_sync_manifests.py run_git_command) -- so a plain --audit
             run over a repo with a fresh plugin would print that noise even
             though a root commit is an expected, non-error case.
        Why: Falsification first -- confirm real git actually fails loudly for
             this case (proves the reproduction is real), then confirm
             find_last_version_bump_commit's own stderr is empty (proves the
             ``rev-parse --verify --quiet`` fix suppresses it).
        """
        # Arrange
        monkeypatch.chdir(tmp_path)
        _git(tmp_path, "init")
        _git(tmp_path, "config", "commit.gpgsign", "false")
        _write_plugin_json(tmp_path, "dh", "1.0.0")
        _git(tmp_path, "add", ".")
        _git(tmp_path, "commit", "-m", "root: dh at 1.0.0")
        root_sha = _git(tmp_path, "rev-parse", "HEAD")

        # Falsification: confirm bare `git rev-parse <sha>^` really does fail
        # loudly for a true root commit -- otherwise this test would not be
        # exercising the bug the review comment described.
        bare_attempt = subprocess.run(
            ["git", "rev-parse", f"{root_sha}^"],
            cwd=tmp_path,
            capture_output=True,
            env=_GIT_ENV,
            text=True,
            check=False,
        )
        assert bare_attempt.returncode != 0
        assert bare_attempt.stderr.strip() != ""

        # Act
        result = gate.find_last_version_bump_commit("plugins/dh/.claude-plugin/plugin.json")

        # Assert -- root commit is still returned as the bump point ...
        assert result == root_sha
        # ... and no "fatal: ..." noise reached this process's stderr getting there.
        assert capsys.readouterr().err == ""


@pytest.mark.integration
class TestCheckVersionBumpsIntegration:
    """End-to-end tests against real git repos -- the actual #3021 reproduction.

    These simulate a GitHub squash-merge: every commit is a plain `git commit`
    (nothing is ever staged-and-left-uncommitted the way a pre-commit hook
    would see it), matching exactly how a PR lands on a CI checkout.
    """

    def test_detects_the_pr_3005_failure_mode(self, tmp_path: Path, monkeypatch: Any) -> None:
        """A plugin file changed on top of base without a version bump is flagged.

        Tests: check_version_bumps (real git diff between two commits)
        How: Commit 1 (base): plugin.json at 9.0.15 plus a skill file.
             Commit 2 (head): the skill file is edited, plugin.json untouched.
             This is exactly PR #3005 / commit ba58d56d's shape.
        Why: This is the direct reproduction of issue #3021 -- proves the gate
             would have failed that PR's CI run had it existed then.
        """
        # Arrange
        monkeypatch.chdir(tmp_path)
        _git(tmp_path, "init")
        _git(tmp_path, "config", "commit.gpgsign", "false")
        skill_path = tmp_path / "plugins" / "dh" / "skills" / "work-backlog-item" / "SKILL.md"
        skill_path.parent.mkdir(parents=True, exist_ok=True)
        skill_path.write_text("original content\n", encoding="utf-8")
        _write_plugin_json(tmp_path, "dh", "9.0.15")
        _git(tmp_path, "add", ".")
        _git(tmp_path, "commit", "-m", "base: dh at 9.0.15")
        base_sha = _git(tmp_path, "rev-parse", "HEAD")

        # PR commit: content changes, version does not (the bug)
        skill_path.write_text("fixed content\n", encoding="utf-8")
        _git(tmp_path, "add", ".")
        _git(tmp_path, "commit", "-m", "fix: gate-token bang-exec permission denied")

        # Act
        missing = gate.check_version_bumps(base_sha, "HEAD")

        # Assert -- the exact gap that let PR #3005 land silently
        assert missing == ["dh"]

    def test_passes_once_the_bump_is_included(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Falsification check: the same diff, but with plugin.json also bumped, passes clean.

        Tests: check_version_bumps (real git diff between two commits)
        How: Same as the failure-mode test, except the PR commit also bumps
             plugin.json to 9.0.16.
        Why: Proves the gate distinguishes bumped from unbumped -- it isn't
             failing every diff unconditionally.
        """
        # Arrange
        monkeypatch.chdir(tmp_path)
        _git(tmp_path, "init")
        _git(tmp_path, "config", "commit.gpgsign", "false")
        skill_path = tmp_path / "plugins" / "dh" / "skills" / "work-backlog-item" / "SKILL.md"
        skill_path.parent.mkdir(parents=True, exist_ok=True)
        skill_path.write_text("original content\n", encoding="utf-8")
        _write_plugin_json(tmp_path, "dh", "9.0.15")
        _git(tmp_path, "add", ".")
        _git(tmp_path, "commit", "-m", "base: dh at 9.0.15")
        base_sha = _git(tmp_path, "rev-parse", "HEAD")

        # PR commit: content changes AND version bumps
        skill_path.write_text("fixed content\n", encoding="utf-8")
        _write_plugin_json(tmp_path, "dh", "9.0.16")
        _git(tmp_path, "add", ".")
        _git(tmp_path, "commit", "-m", "fix: gate-token bang-exec permission denied")

        # Act
        missing = gate.check_version_bumps(base_sha, "HEAD")

        # Assert
        assert missing == []

    def test_unrelated_plugin_change_is_not_flagged(self, tmp_path: Path, monkeypatch: Any) -> None:
        """A PR touching a different plugin does not flag an untouched one.

        Tests: check_version_bumps (real git diff between two commits)
        How: Two plugins exist at base; only one changes in the PR commit.
        Why: Guards against a scan that walks every plugin.json instead of only
             ones with an actual diff -- would be a correctness bug at scale.
        """
        # Arrange
        monkeypatch.chdir(tmp_path)
        _git(tmp_path, "init")
        _git(tmp_path, "config", "commit.gpgsign", "false")
        touched = tmp_path / "plugins" / "dh" / "README.md"
        touched.parent.mkdir(parents=True, exist_ok=True)
        touched.write_text("v1\n", encoding="utf-8")
        _write_plugin_json(tmp_path, "dh", "1.0.0")
        _write_plugin_json(tmp_path, "other-plugin", "2.0.0")
        _git(tmp_path, "add", ".")
        _git(tmp_path, "commit", "-m", "base")
        base_sha = _git(tmp_path, "rev-parse", "HEAD")

        touched.write_text("v2\n", encoding="utf-8")
        _write_plugin_json(tmp_path, "dh", "1.0.1")
        _git(tmp_path, "add", ".")
        _git(tmp_path, "commit", "-m", "bump dh only")

        # Act
        missing = gate.check_version_bumps(base_sha, "HEAD")

        # Assert -- other-plugin never appears; it wasn't touched
        assert missing == []

    def test_synthetic_merge_commit_head_false_flags_base_only_change(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Reproduction (Greptile P1 / Copilot, PR #3022): a base-only change after
        divergence, diffed via the default HEAD, wrongly blocks a valid PR.

        Tests: check_version_bumps (real git diff between two refs, mirroring the
             workflow's actual base/head comparison)
        How: 1) divergence commit -- pluginA and pluginB both at 1.0.0.
             2) PR branch: bumps pluginB only (a real, correctly-bumped PR change).
             3) base tip: after divergence, base's own history edits pluginA's
                content with *no* version bump (unrelated to the PR).
             4) a synthetic merge commit combining both, exactly as
                actions/checkout produces by default for a pull_request
                trigger (base tip as first parent, PR head merged in).
        Why: Diffing base_sha...HEAD against that merge commit makes pluginA
             look like it changed in "the PR" (it did not -- only the base
             branch changed it), so the gate would fail a PR that never
             touched pluginA. Falsification: the same check against the PR's
             real head commit (the fix) must not flag it.
        """
        # Arrange
        monkeypatch.chdir(tmp_path)
        _git(tmp_path, "init")
        _git(tmp_path, "config", "commit.gpgsign", "false")
        plugin_a_file = tmp_path / "plugins" / "plugin-a" / "README.md"
        plugin_a_file.parent.mkdir(parents=True, exist_ok=True)
        plugin_a_file.write_text("v1\n", encoding="utf-8")
        _write_plugin_json(tmp_path, "plugin-a", "1.0.0")
        _write_plugin_json(tmp_path, "plugin-b", "1.0.0")
        _git(tmp_path, "add", ".")
        _git(tmp_path, "commit", "-m", "divergence point")
        divergence_sha = _git(tmp_path, "rev-parse", "HEAD")
        base_branch = _git(tmp_path, "branch", "--show-current")

        # PR branch: correctly bumps pluginB only.
        _git(tmp_path, "checkout", "-b", "pr-branch")
        _write_plugin_json(tmp_path, "plugin-b", "1.0.1")
        _git(tmp_path, "add", ".")
        _git(tmp_path, "commit", "-m", "PR: bump plugin-b")
        pr_head_sha = _git(tmp_path, "rev-parse", "HEAD")

        # Base tip: unrelated post-divergence change to pluginA, no bump.
        _git(tmp_path, "checkout", base_branch)
        plugin_a_file.write_text("v2 -- unrelated base drift\n", encoding="utf-8")
        _git(tmp_path, "add", ".")
        _git(tmp_path, "commit", "-m", "base: unbumped plugin-a drift")
        base_tip_sha = _git(tmp_path, "rev-parse", "HEAD")

        # Synthetic PR merge commit, as actions/checkout produces by default.
        _git(tmp_path, "checkout", "-b", "synthetic-merge", base_tip_sha)
        _git(tmp_path, "merge", "--no-ff", "--no-edit", pr_head_sha)
        merge_sha = _git(tmp_path, "rev-parse", "HEAD")
        _git(tmp_path, "checkout", merge_sha)  # detached HEAD == HEAD is the merge commit

        # Act -- bug: default head_ref (implicit HEAD == the merge commit)
        buggy_missing = gate.check_version_bumps(divergence_sha, "HEAD")
        # Act -- fix: explicit head_ref pointing at the PR's real head
        fixed_missing = gate.check_version_bumps(divergence_sha, pr_head_sha)

        # Assert -- reproduction: plugin-a is wrongly flagged via the merge commit ...
        assert buggy_missing == ["plugin-a"]
        # ... but never flagged when diffed against the PR's actual head.
        assert fixed_missing == []

    def test_synthetic_merge_commit_head_masks_a_real_missing_bump(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Reproduction (Greptile P1 / Copilot, PR #3022): a base-side version bump
        merged into HEAD can mask a genuinely unbumped PR change.

        Tests: check_version_bumps (real git diff between two refs, mirroring the
             workflow's actual base/head comparison)
        How: 1) divergence commit -- pluginA at 1.0.0.
             2) PR branch: edits pluginA's content but never bumps its version
                (the actual bug the gate exists to catch).
             3) base tip: after divergence, base independently bumps pluginA
                to 2.0.0 for an unrelated reason.
             4) synthetic merge commit combining both.
        Why: Diffing base_sha...HEAD against that merge commit shows
             plugin-a's version at "head" as 2.0.0 (inherited from base) even
             though the PR's own commit never bumped it -- head > base passes
             the gate, silently letting an unbumped PR change through.
             Falsification: diffing against the PR's real head must catch it.
        """
        # Arrange
        monkeypatch.chdir(tmp_path)
        _git(tmp_path, "init")
        _git(tmp_path, "config", "commit.gpgsign", "false")
        plugin_a_file = tmp_path / "plugins" / "plugin-a" / "README.md"
        plugin_a_file.parent.mkdir(parents=True, exist_ok=True)
        plugin_a_file.write_text("v1\n", encoding="utf-8")
        _write_plugin_json(tmp_path, "plugin-a", "1.0.0")
        _git(tmp_path, "add", ".")
        _git(tmp_path, "commit", "-m", "divergence point")
        divergence_sha = _git(tmp_path, "rev-parse", "HEAD")
        base_branch = _git(tmp_path, "branch", "--show-current")

        # PR branch: content change, no bump (the bug the gate must catch).
        _git(tmp_path, "checkout", "-b", "pr-branch")
        plugin_a_file.write_text("v2 -- PR change, unbumped\n", encoding="utf-8")
        _git(tmp_path, "add", ".")
        _git(tmp_path, "commit", "-m", "PR: edits plugin-a, forgets the bump")
        pr_head_sha = _git(tmp_path, "rev-parse", "HEAD")

        # Base tip: unrelated bump, landed on base after the PR diverged.
        _git(tmp_path, "checkout", base_branch)
        _write_plugin_json(tmp_path, "plugin-a", "2.0.0")
        _git(tmp_path, "add", ".")
        _git(tmp_path, "commit", "-m", "base: unrelated plugin-a bump to 2.0.0")
        base_tip_sha = _git(tmp_path, "rev-parse", "HEAD")

        # Synthetic PR merge commit, as actions/checkout produces by default.
        _git(tmp_path, "checkout", "-b", "synthetic-merge", base_tip_sha)
        _git(tmp_path, "merge", "--no-ff", "--no-edit", pr_head_sha)
        merge_sha = _git(tmp_path, "rev-parse", "HEAD")
        _git(tmp_path, "checkout", merge_sha)  # detached HEAD == HEAD is the merge commit

        # Act -- bug: default head_ref (implicit HEAD == the merge commit)
        buggy_missing = gate.check_version_bumps(divergence_sha, "HEAD")
        # Act -- fix: explicit head_ref pointing at the PR's real head
        fixed_missing = gate.check_version_bumps(divergence_sha, pr_head_sha)

        # Assert -- reproduction: the merge commit's inherited base bump hides the gap ...
        assert buggy_missing == []
        # ... but diffing against the PR's real head catches the missing bump.
        assert fixed_missing == ["plugin-a"]


@pytest.mark.integration
class TestAuditVersionDriftIntegration:
    """End-to-end tests for audit_version_drift against a real git history."""

    def test_finds_drift_after_the_last_bump_commit(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Content changed after the last version-bump commit is reported as drift.

        Tests: audit_version_drift
        How: Commit 1: plugin.json at 1.0.0 + README. Commit 2: bump to 1.0.1
             (the "last bump"). Commit 3: README changes again with no further
             bump -- the live #3021 pattern found in this repo's own history
             (13+ unbumped development-harness commits after its last bump).
        Why: Directly validates the retroactive audit mode required by issue
             #3021 acceptance criterion #2.
        """
        # Arrange
        monkeypatch.chdir(tmp_path)
        _git(tmp_path, "init")
        _git(tmp_path, "config", "commit.gpgsign", "false")
        readme = tmp_path / "plugins" / "dh" / "README.md"
        readme.parent.mkdir(parents=True, exist_ok=True)
        readme.write_text("v1\n", encoding="utf-8")
        _write_plugin_json(tmp_path, "dh", "1.0.0")
        _git(tmp_path, "add", ".")
        _git(tmp_path, "commit", "-m", "base")

        _write_plugin_json(tmp_path, "dh", "1.0.1")
        _git(tmp_path, "add", ".")
        _git(tmp_path, "commit", "-m", "bump to 1.0.1")

        readme.write_text("v2 -- no bump\n", encoding="utf-8")
        _git(tmp_path, "add", ".")
        _git(tmp_path, "commit", "-m", "content change with no bump")

        # Act
        drifted = gate.audit_version_drift(tmp_path / "plugins")

        # Assert
        assert drifted == ["dh"]

    def test_no_drift_when_every_change_is_covered_by_its_bump(self, tmp_path: Path, monkeypatch: Any) -> None:
        """A plugin whose every content change is followed by a bump shows no drift.

        Tests: audit_version_drift
        How: Every content-changing commit also bumps the version.
        Why: Falsification check -- the audit must not flag a healthy plugin.
        """
        # Arrange
        monkeypatch.chdir(tmp_path)
        _git(tmp_path, "init")
        _git(tmp_path, "config", "commit.gpgsign", "false")
        readme = tmp_path / "plugins" / "dh" / "README.md"
        readme.parent.mkdir(parents=True, exist_ok=True)
        readme.write_text("v1\n", encoding="utf-8")
        _write_plugin_json(tmp_path, "dh", "1.0.0")
        _git(tmp_path, "add", ".")
        _git(tmp_path, "commit", "-m", "base")

        readme.write_text("v2\n", encoding="utf-8")
        _write_plugin_json(tmp_path, "dh", "1.0.1")
        _git(tmp_path, "add", ".")
        _git(tmp_path, "commit", "-m", "content change with bump")

        # Act
        drifted = gate.audit_version_drift(tmp_path / "plugins")

        # Assert
        assert drifted == []


@pytest.mark.integration
class TestRepairPluginVersionIntegration:
    """End-to-end tests for --repair against a real git history.

    These are the regression tests for #3027 -- two branches deriving the
    same next version from an identical origin/main snapshot land on the
    same number after both merge. `repair_plugin_version` runs against
    `check.py --repair`'s own module (`gate`), not `auto_sync_manifests`,
    so it must fail on the pre-T1 `check_plugin_version_bump.py` (no
    `--repair` mode existed at all) and pass once T1 lands.
    """

    def test_repairs_the_pr_3027_collision(self, tmp_path: Path, monkeypatch: Any) -> None:
        """A version collision (two merges landing on the same number) is un-collided.

        Tests: repair_plugin_version, audit_version_drift (via _run_repair)
        How: Commit A (PR A's merge): bumps dh's plugin.json from 9.0.16 to
             9.0.17. Commit B (PR B's merge): changes dh content but leaves
             the version at 9.0.17 -- both PRs independently computed
             base_version + 1 from the same origin/main snapshot, so B's
             merge does not raise the version further. This is the exact
             #3027 collision shape from plan/architect-plugin-version-bump-race.md.
        Why: This is the regression test for #3027. It must fail against
             pre-T1 code (repair_plugin_version / --repair did not exist) and
             pass once the fix lands -- the actual evidence for the fix, not
             just "tests added."
        """
        # Arrange
        monkeypatch.chdir(tmp_path)
        _git(tmp_path, "init")
        _git(tmp_path, "config", "commit.gpgsign", "false")
        skill_path = tmp_path / "plugins" / "dh" / "skills" / "foo" / "SKILL.md"
        skill_path.parent.mkdir(parents=True, exist_ok=True)
        skill_path.write_text("original content\n", encoding="utf-8")
        _write_plugin_json(tmp_path, "dh", "9.0.16")
        _git(tmp_path, "add", ".")
        _git(tmp_path, "commit", "-m", "base: dh at 9.0.16")

        # Commit A -- PR A's merge: bumps to 9.0.17
        _write_plugin_json(tmp_path, "dh", "9.0.17")
        _git(tmp_path, "add", ".")
        _git(tmp_path, "commit", "-m", "PR A merge: bump dh to 9.0.17")

        # Commit B -- PR B's merge: content change, version left at 9.0.17 (collision)
        skill_path.write_text("PR B content change\n", encoding="utf-8")
        _git(tmp_path, "add", ".")
        _git(tmp_path, "commit", "-m", "PR B merge: content change, version still 9.0.17")

        # Act
        exit_code = gate._run_repair()

        # Assert -- repaired to 9.0.18, un-colliding the two merges
        plugin_json_path = tmp_path / "plugins" / "dh" / ".claude-plugin" / "plugin.json"
        assert exit_code == 0
        assert json.loads(plugin_json_path.read_text(encoding="utf-8"))["version"] == "9.0.18"

    def test_repairs_the_pr_3021_no_bump_case(self, tmp_path: Path, monkeypatch: Any) -> None:
        """A GitHub-UI merge that skipped the pre-commit hook entirely still gets bumped.

        Tests: repair_plugin_version, audit_version_drift (via _run_repair)
        How: Single commit -- plugin.json at 1.0.0, never bumped since
             creation, with a content change. This is the #3021 shape: a
             squash-merge that never ran the local pre-commit hook.
        Why: T1's repair predicate must close both #3027 and #3021 with one
             rule (per the plan's Recommendation section) -- this proves the
             no-bump-at-all case independently of the collision case above.
        """
        # Arrange
        monkeypatch.chdir(tmp_path)
        _git(tmp_path, "init")
        _git(tmp_path, "config", "commit.gpgsign", "false")
        readme = tmp_path / "plugins" / "dh" / "README.md"
        readme.parent.mkdir(parents=True, exist_ok=True)
        readme.write_text("v1\n", encoding="utf-8")
        _write_plugin_json(tmp_path, "dh", "1.0.0")
        _git(tmp_path, "add", ".")
        _git(tmp_path, "commit", "-m", "root: dh at 1.0.0")

        readme.write_text("v2 -- squash-merged, no bump\n", encoding="utf-8")
        _git(tmp_path, "add", ".")
        _git(tmp_path, "commit", "-m", "GitHub-UI squash-merge, hook never ran")

        # Act
        exit_code = gate._run_repair()

        # Assert
        plugin_json_path = tmp_path / "plugins" / "dh" / ".claude-plugin" / "plugin.json"
        assert exit_code == 0
        assert json.loads(plugin_json_path.read_text(encoding="utf-8"))["version"] == "1.0.1"

    def test_idempotent_on_clean_tree(self, tmp_path: Path, monkeypatch: Any) -> None:
        """Running --repair twice in a row only bumps once.

        Tests: repair_plugin_version, audit_version_drift (via _run_repair)
        How: Repair a real collision (as above), commit the repair, then run
             --repair again against the now-clean tree.
        Why: The post-merge CI job (T3) runs on every push -- if repair were
             not idempotent, every subsequent unrelated push would keep
             bumping every previously-repaired plugin forever.
        """
        # Arrange
        monkeypatch.chdir(tmp_path)
        _git(tmp_path, "init")
        _git(tmp_path, "config", "commit.gpgsign", "false")
        skill_path = tmp_path / "plugins" / "dh" / "skills" / "foo" / "SKILL.md"
        skill_path.parent.mkdir(parents=True, exist_ok=True)
        skill_path.write_text("original content\n", encoding="utf-8")
        _write_plugin_json(tmp_path, "dh", "9.0.16")
        _git(tmp_path, "add", ".")
        _git(tmp_path, "commit", "-m", "base: dh at 9.0.16")

        _write_plugin_json(tmp_path, "dh", "9.0.17")
        _git(tmp_path, "add", ".")
        _git(tmp_path, "commit", "-m", "PR A merge: bump dh to 9.0.17")

        skill_path.write_text("PR B content change\n", encoding="utf-8")
        _git(tmp_path, "add", ".")
        _git(tmp_path, "commit", "-m", "PR B merge: content change, version still 9.0.17")

        first_exit_code = gate._run_repair()
        assert first_exit_code == 0
        plugin_json_path = tmp_path / "plugins" / "dh" / ".claude-plugin" / "plugin.json"
        assert json.loads(plugin_json_path.read_text(encoding="utf-8"))["version"] == "9.0.18"

        _git(tmp_path, "add", ".")
        _git(tmp_path, "commit", "-m", "repair commit: bump dh to 9.0.18")

        # Act -- second run against the now-clean tree
        second_exit_code = gate._run_repair()

        # Assert -- no further bump
        assert second_exit_code == 0
        assert json.loads(plugin_json_path.read_text(encoding="utf-8"))["version"] == "9.0.18"

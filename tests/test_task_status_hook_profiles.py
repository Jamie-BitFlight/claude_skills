"""Tests for hook profile controls added to task_status_hook.py.

Tests: Profile resolution (CLAUDE_SKILLS_HOOK_PROFILE), disabled-hook parsing
(CLAUDE_SKILLS_DISABLED_HOOKS), skip decision logic, strict pre-completion
checks, and main() integration paths.

Strategy:
- Unit tests for resolve_profile, parse_disabled_hooks, should_skip_hook,
  and run_strict_pre_completion_checks use monkeypatch for env var control
  and mocker for sam_schema isolation.
- Integration tests for main() patch parse_hook_input (avoids stdin) and
  the two handlers (avoids disk I/O). main() always calls sys.exit(0) which
  raises SystemExit; tests assert on the exit code and whether handlers were
  called.
- No test touches real task plan files on disk.

Test file: tests/test_task_status_hook_profiles.py
Implementation: plugins/development-harness/skills/implementation-manager/scripts/task_status_hook.py
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pytest

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

# task_status_hook is on pythonpath via pyproject.toml:
#   ./plugins/development-harness/skills/implementation-manager/scripts
# No sys.path manipulation required here.
import task_status_hook as hook
from task_status_hook import (
    HOOK_ID_POST_TOOL_USE,
    HOOK_ID_SUBAGENT_STOP,
    HookProfile,
    parse_disabled_hooks,
    resolve_profile,
    run_strict_pre_completion_checks,
    should_skip_hook,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def hook_input_subagent_stop() -> dict[str, Any]:
    """Minimal valid stdin JSON for a SubagentStop event.

    Returns:
        Dict matching the shape parse_hook_input() would return for SubagentStop.
    """
    return {
        "hook_event_name": "SubagentStop",
        "session_id": "test-session-abc123",
        "cwd": "/tmp/test-cwd",
        "prompt": "",
    }


@pytest.fixture
def hook_input_post_tool_use() -> dict[str, Any]:
    """Minimal valid stdin JSON for a PostToolUse (Write) event.

    Returns:
        Dict matching the shape parse_hook_input() would return for PostToolUse.
    """
    return {
        "hook_event_name": "PostToolUse",
        "tool_name": "Write",
        "session_id": "test-session-abc123",
        "cwd": "/tmp/test-cwd",
    }


# ---------------------------------------------------------------------------
# Unit: resolve_profile()
# ---------------------------------------------------------------------------


class TestResolveProfile:
    """Unit tests for resolve_profile().

    Tests: CLAUDE_SKILLS_HOOK_PROFILE env var parsing — valid values, invalid
    values, unset, empty string, and case sensitivity.
    """

    def test_unset_returns_standard(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Unset env var returns HookProfile.STANDARD.

        Tests: resolve_profile() default.
        How: Remove env var entirely, call resolve_profile().
        Why: Default behavior must match current codebase (standard = no change).
        """
        monkeypatch.delenv("CLAUDE_SKILLS_HOOK_PROFILE", raising=False)
        result = resolve_profile()
        assert result == HookProfile.STANDARD

    def test_empty_string_returns_standard(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Empty string env var returns HookProfile.STANDARD.

        Tests: resolve_profile() with empty string.
        How: Set env var to empty string, call resolve_profile().
        Why: Empty string is treated as unset — same default behavior.
        """
        monkeypatch.setenv("CLAUDE_SKILLS_HOOK_PROFILE", "")
        result = resolve_profile()
        assert result == HookProfile.STANDARD

    def test_whitespace_only_returns_standard(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Whitespace-only env var returns HookProfile.STANDARD.

        Tests: resolve_profile() whitespace handling.
        How: Set env var to spaces only, call resolve_profile().
        Why: Whitespace is stripped; empty string after strip triggers default.
        """
        monkeypatch.setenv("CLAUDE_SKILLS_HOOK_PROFILE", "   ")
        result = resolve_profile()
        assert result == HookProfile.STANDARD

    def test_minimal_returns_minimal(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """'minimal' returns HookProfile.MINIMAL.

        Tests: resolve_profile() with valid minimal value.
        How: Set env var to 'minimal', call resolve_profile().
        Why: Minimal profile skips PostToolUse handler.
        """
        monkeypatch.setenv("CLAUDE_SKILLS_HOOK_PROFILE", "minimal")
        result = resolve_profile()
        assert result == HookProfile.MINIMAL

    def test_standard_returns_standard(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """'standard' returns HookProfile.STANDARD.

        Tests: resolve_profile() with explicit standard value.
        How: Set env var to 'standard', call resolve_profile().
        Why: Standard profile is the current behavior — explicit setting should work.
        """
        monkeypatch.setenv("CLAUDE_SKILLS_HOOK_PROFILE", "standard")
        result = resolve_profile()
        assert result == HookProfile.STANDARD

    def test_strict_returns_strict(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """'strict' returns HookProfile.STRICT.

        Tests: resolve_profile() with valid strict value.
        How: Set env var to 'strict', call resolve_profile().
        Why: Strict profile adds pre-completion validation warnings.
        """
        monkeypatch.setenv("CLAUDE_SKILLS_HOOK_PROFILE", "strict")
        result = resolve_profile()
        assert result == HookProfile.STRICT

    def test_invalid_value_returns_standard(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Invalid profile value returns STANDARD and emits warning to stderr.

        Tests: resolve_profile() invalid value fallback.
        How: Set env var to 'ultra', call resolve_profile(), check stderr.
        Why: Fail-safe default prevents misconfiguration from breaking hooks.
        """
        monkeypatch.setenv("CLAUDE_SKILLS_HOOK_PROFILE", "ultra")
        result = resolve_profile()
        assert result == HookProfile.STANDARD
        captured = capsys.readouterr()
        assert "ultra" in captured.err
        assert "standard" in captured.err

    def test_case_sensitive_uppercase_invalid(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """'MINIMAL' (uppercase) is invalid — values are case-sensitive lowercase.

        Tests: resolve_profile() case sensitivity.
        How: Set env var to 'MINIMAL', call resolve_profile().
        Why: ADR-004 mandates case-sensitive lowercase values; uppercase triggers warning.
        """
        monkeypatch.setenv("CLAUDE_SKILLS_HOOK_PROFILE", "MINIMAL")
        result = resolve_profile()
        assert result == HookProfile.STANDARD
        captured = capsys.readouterr()
        assert "MINIMAL" in captured.err

    def test_case_sensitive_mixed_invalid(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """'Standard' (title case) is invalid — values are case-sensitive lowercase.

        Tests: resolve_profile() case sensitivity with title case.
        How: Set env var to 'Standard', call resolve_profile().
        Why: Consistent with ADR-004 case-sensitivity requirement.
        """
        monkeypatch.setenv("CLAUDE_SKILLS_HOOK_PROFILE", "Standard")
        result = resolve_profile()
        assert result == HookProfile.STANDARD
        captured = capsys.readouterr()
        assert "Standard" in captured.err


# ---------------------------------------------------------------------------
# Unit: parse_disabled_hooks()
# ---------------------------------------------------------------------------


class TestParseDisabledHooks:
    """Unit tests for parse_disabled_hooks().

    Tests: CLAUDE_SKILLS_DISABLED_HOOKS env var parsing — comma splitting,
    whitespace stripping, empty segments, unknown IDs, unset/empty.
    """

    def test_unset_returns_empty_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Unset env var returns empty set.

        Tests: parse_disabled_hooks() default.
        How: Remove env var, call parse_disabled_hooks().
        Why: No hooks disabled by default — current behavior preserved.
        """
        monkeypatch.delenv("CLAUDE_SKILLS_DISABLED_HOOKS", raising=False)
        result = parse_disabled_hooks()
        assert result == set()

    def test_empty_string_returns_empty_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Empty string env var returns empty set.

        Tests: parse_disabled_hooks() with empty string.
        How: Set env var to '', call parse_disabled_hooks().
        Why: Empty string is treated as no disabled hooks.
        """
        monkeypatch.setenv("CLAUDE_SKILLS_DISABLED_HOOKS", "")
        result = parse_disabled_hooks()
        assert result == set()

    def test_whitespace_only_returns_empty_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Whitespace-only env var returns empty set.

        Tests: parse_disabled_hooks() whitespace handling.
        How: Set env var to spaces, call parse_disabled_hooks().
        Why: Whitespace segments after strip become empty and are excluded.
        """
        monkeypatch.setenv("CLAUDE_SKILLS_DISABLED_HOOKS", "   ")
        result = parse_disabled_hooks()
        assert result == set()

    def test_single_hook_id(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Single hook ID returns a one-element set.

        Tests: parse_disabled_hooks() with one ID.
        How: Set env var to 'task-status:post-tool-use'.
        Why: Single-hook disable is the most common use case.
        """
        monkeypatch.setenv("CLAUDE_SKILLS_DISABLED_HOOKS", HOOK_ID_POST_TOOL_USE)
        result = parse_disabled_hooks()
        assert result == {HOOK_ID_POST_TOOL_USE}

    def test_multiple_comma_separated_ids(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Multiple comma-separated IDs return the full set.

        Tests: parse_disabled_hooks() multi-ID parsing.
        How: Set env var to both hook IDs comma-separated.
        Why: Both hooks disabled simultaneously is a valid configuration.
        """
        monkeypatch.setenv("CLAUDE_SKILLS_DISABLED_HOOKS", f"{HOOK_ID_POST_TOOL_USE},{HOOK_ID_SUBAGENT_STOP}")
        result = parse_disabled_hooks()
        assert result == {HOOK_ID_POST_TOOL_USE, HOOK_ID_SUBAGENT_STOP}

    def test_whitespace_stripped_from_each_id(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Whitespace around each ID is stripped.

        Tests: parse_disabled_hooks() whitespace stripping.
        How: Include spaces around IDs in env var value.
        Why: Users may include spaces for readability; must be tolerated.
        """
        monkeypatch.setenv("CLAUDE_SKILLS_DISABLED_HOOKS", f"  {HOOK_ID_POST_TOOL_USE}  ,  {HOOK_ID_SUBAGENT_STOP}  ")
        result = parse_disabled_hooks()
        assert result == {HOOK_ID_POST_TOOL_USE, HOOK_ID_SUBAGENT_STOP}

    def test_trailing_comma_excluded(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Trailing comma produces no empty-string entry in the result set.

        Tests: parse_disabled_hooks() trailing comma handling.
        How: Set env var with trailing comma.
        Why: Empty segments from consecutive or trailing commas must not appear.
        """
        monkeypatch.setenv("CLAUDE_SKILLS_DISABLED_HOOKS", f"{HOOK_ID_POST_TOOL_USE},")
        result = parse_disabled_hooks()
        assert result == {HOOK_ID_POST_TOOL_USE}
        assert "" not in result

    def test_consecutive_commas_no_empty_segments(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Consecutive commas produce no empty-string entries.

        Tests: parse_disabled_hooks() consecutive comma handling.
        How: Set env var with double comma between IDs.
        Why: Defensive parsing must exclude empty segments entirely.
        """
        monkeypatch.setenv("CLAUDE_SKILLS_DISABLED_HOOKS", f"{HOOK_ID_POST_TOOL_USE},,{HOOK_ID_SUBAGENT_STOP}")
        result = parse_disabled_hooks()
        assert result == {HOOK_ID_POST_TOOL_USE, HOOK_ID_SUBAGENT_STOP}
        assert "" not in result

    def test_unknown_hook_ids_included(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Unknown hook IDs are included in the result set without warning.

        Tests: parse_disabled_hooks() unknown ID forward compatibility.
        How: Set env var to an unrecognized hook ID.
        Why: ADR-003 mandates no validation — unknown IDs silently never match.
        """
        monkeypatch.setenv("CLAUDE_SKILLS_DISABLED_HOOKS", "future-hook:some-handler")
        result = parse_disabled_hooks()
        assert "future-hook:some-handler" in result


# ---------------------------------------------------------------------------
# Unit: should_skip_hook()
# ---------------------------------------------------------------------------


class TestShouldSkipHook:
    """Unit tests for should_skip_hook().

    Tests: All combinations of event x profile x disabled set covering the
    behavior matrix and ADR-002 (disabled takes precedence over profile).
    """

    def test_post_tool_use_minimal_skipped(self) -> None:
        """PostToolUse + minimal profile -> True (skip).

        Tests: should_skip_hook() minimal profile skips PostToolUse.
        How: Call with PostToolUse event and minimal profile, empty disabled set.
        Why: Minimal profile eliminates the 30-50x/task PostToolUse cost.
        """
        result = should_skip_hook("PostToolUse", HookProfile.MINIMAL, set())
        assert result is True

    def test_post_tool_use_standard_runs(self) -> None:
        """PostToolUse + standard profile -> False (run).

        Tests: should_skip_hook() standard profile runs PostToolUse.
        How: Call with PostToolUse event and standard profile.
        Why: Standard profile must preserve current behavior exactly.
        """
        result = should_skip_hook("PostToolUse", HookProfile.STANDARD, set())
        assert result is False

    def test_post_tool_use_strict_runs(self) -> None:
        """PostToolUse + strict profile -> False (run).

        Tests: should_skip_hook() strict profile runs PostToolUse.
        How: Call with PostToolUse event and strict profile.
        Why: Strict adds checks on SubagentStop only; PostToolUse runs normally.
        """
        result = should_skip_hook("PostToolUse", HookProfile.STRICT, set())
        assert result is False

    def test_subagent_stop_minimal_runs(self) -> None:
        """SubagentStop + minimal profile -> False (run).

        Tests: should_skip_hook() minimal profile runs SubagentStop.
        How: Call with SubagentStop event and minimal profile.
        Why: Minimal skips PostToolUse only; SubagentStop is essential for completion marking.
        """
        result = should_skip_hook("SubagentStop", HookProfile.MINIMAL, set())
        assert result is False

    def test_subagent_stop_standard_runs(self) -> None:
        """SubagentStop + standard profile -> False (run).

        Tests: should_skip_hook() standard profile runs SubagentStop.
        How: Call with SubagentStop event and standard profile.
        Why: SubagentStop runs in all profiles.
        """
        result = should_skip_hook("SubagentStop", HookProfile.STANDARD, set())
        assert result is False

    def test_subagent_stop_strict_runs(self) -> None:
        """SubagentStop + strict profile -> False (run).

        Tests: should_skip_hook() strict profile runs SubagentStop.
        How: Call with SubagentStop event and strict profile.
        Why: SubagentStop runs in all profiles (strict adds checks inside the handler).
        """
        result = should_skip_hook("SubagentStop", HookProfile.STRICT, set())
        assert result is False

    def test_post_tool_use_disabled_skipped(self) -> None:
        """PostToolUse disabled by ID -> True regardless of profile.

        Tests: should_skip_hook() disabled set takes precedence.
        How: Pass PostToolUse with standard profile but disable its hook ID.
        Why: Explicit disable is a stronger signal than profile (ADR-002).
        """
        disabled = {HOOK_ID_POST_TOOL_USE}
        result = should_skip_hook("PostToolUse", HookProfile.STANDARD, disabled)
        assert result is True

    def test_subagent_stop_disabled_skipped(self) -> None:
        """SubagentStop disabled by ID -> True regardless of profile.

        Tests: should_skip_hook() disabled set for SubagentStop.
        How: Pass SubagentStop with strict profile but disable its hook ID.
        Why: Disabled hook must exit 0 even when strict mode is active.
        """
        disabled = {HOOK_ID_SUBAGENT_STOP}
        result = should_skip_hook("SubagentStop", HookProfile.STRICT, disabled)
        assert result is True

    def test_disabled_takes_precedence_over_minimal_profile(self) -> None:
        """Disabled set wins over minimal profile for SubagentStop.

        Tests: should_skip_hook() disabled + minimal profile interaction.
        How: Pass SubagentStop with minimal profile and SubagentStop in disabled set.
        Why: Disabled is checked first regardless of profile.
        """
        disabled = {HOOK_ID_SUBAGENT_STOP}
        result = should_skip_hook("SubagentStop", HookProfile.MINIMAL, disabled)
        assert result is True

    def test_unknown_event_name_not_skipped(self) -> None:
        """Unknown event name -> False (let dispatch handle it).

        Tests: should_skip_hook() unknown event fallthrough.
        How: Pass an unrecognized event name with minimal profile.
        Why: Unknown events have no hook_id in _EVENT_TO_HOOK_ID; they fall through
        to existing dispatch which handles unknowns silently.
        """
        result = should_skip_hook("UnknownEvent", HookProfile.MINIMAL, set())
        assert result is False

    def test_both_hooks_disabled(self) -> None:
        """Both hook IDs disabled -> both return True.

        Tests: should_skip_hook() with fully populated disabled set.
        How: Disable both hook IDs, check both events.
        Why: Users may disable all hook handlers during debugging.
        """
        disabled = {HOOK_ID_POST_TOOL_USE, HOOK_ID_SUBAGENT_STOP}
        assert should_skip_hook("PostToolUse", HookProfile.STANDARD, disabled) is True
        assert should_skip_hook("SubagentStop", HookProfile.STANDARD, disabled) is True


# ---------------------------------------------------------------------------
# Unit: run_strict_pre_completion_checks()
# ---------------------------------------------------------------------------


class TestRunStrictPreCompletionChecks:
    """Unit tests for run_strict_pre_completion_checks().

    Tests: Status checks, acceptance criteria checks, error handling.
    All sam_get_task calls are mocked to avoid real file I/O.
    """

    def _make_task_mock(
        self, *, status: str = "in-progress", acceptance_criteria: str = "- [ ] Must work"
    ) -> MagicMock:
        """Build a minimal Task-like mock for sam_get_task return value.

        Args:
            status: SamTaskStatus value string.
            acceptance_criteria: Acceptance criteria string (empty = unconfigured).

        Returns:
            MagicMock with status and acceptance_criteria attributes set.
        """
        from sam_schema.core.models import TaskStatus as SamTaskStatus

        task = MagicMock()
        task.status = SamTaskStatus(status)
        task.acceptance_criteria = acceptance_criteria
        return task

    def test_in_progress_with_criteria_returns_empty(self) -> None:
        """IN_PROGRESS + non-empty criteria -> empty warnings list (all checks pass).

        Tests: run_strict_pre_completion_checks() happy path.
        How: Pass IN_PROGRESS task with criteria directly (no I/O mocking needed).
        Why: No warnings means strict mode adds no output when everything is correct.
        """
        task = self._make_task_mock(status="in-progress", acceptance_criteria="- [ ] Must pass")
        result = run_strict_pre_completion_checks(task, "T01")
        assert result == []

    def test_not_started_status_returns_warning(self) -> None:
        """NOT_STARTED status -> warning about unclaimed task.

        Tests: run_strict_pre_completion_checks() check #1 (status).
        How: Pass NOT_STARTED task directly.
        Why: Task should be claimed before completion; strict mode flags this.
        """
        task = self._make_task_mock(status="not-started", acceptance_criteria="- [ ] Must pass")
        warnings = run_strict_pre_completion_checks(task, "T01")
        assert len(warnings) >= 1
        assert any("not-started" in w or "claimed" in w for w in warnings)

    def test_empty_acceptance_criteria_returns_warning(self) -> None:
        """Empty acceptance criteria -> warning about missing criteria.

        Tests: run_strict_pre_completion_checks() check #2 (acceptance criteria).
        How: Pass IN_PROGRESS task with empty criteria directly.
        Why: Tasks without acceptance criteria cannot be verified; strict mode flags this.
        """
        task = self._make_task_mock(status="in-progress", acceptance_criteria="")
        warnings = run_strict_pre_completion_checks(task, "T01")
        assert len(warnings) >= 1
        assert any("acceptance" in w.lower() or "criteria" in w.lower() for w in warnings)

    def test_whitespace_only_criteria_returns_warning(self) -> None:
        """Whitespace-only acceptance criteria -> warning (treated as empty).

        Tests: run_strict_pre_completion_checks() whitespace-only criteria.
        How: Pass task with whitespace-only criteria directly.
        Why: Whitespace is semantically empty; should trigger the same warning.
        """
        task = self._make_task_mock(status="in-progress", acceptance_criteria="   ")
        warnings = run_strict_pre_completion_checks(task, "T01")
        assert len(warnings) >= 1

    def test_both_checks_fail_returns_two_warnings(self) -> None:
        """NOT_STARTED + empty criteria -> two warnings (both checks fail).

        Tests: run_strict_pre_completion_checks() dual failure.
        How: Pass NOT_STARTED task with empty criteria directly.
        Why: Both checks are independent; both failures must be reported.
        """
        task = self._make_task_mock(status="not-started", acceptance_criteria="")
        warnings = run_strict_pre_completion_checks(task, "T01")
        assert len(warnings) == 2

    def test_none_acceptance_criteria_treated_as_empty_returns_warning(self) -> None:
        """acceptance_criteria=None (falsy) is treated as empty — triggers criteria warning.

        Tests: run_strict_pre_completion_checks() None criteria handling.
        How: Set acceptance_criteria to None on mock task after construction.
        Why: `or ""` fallback must treat None the same as empty string.
        """
        task = self._make_task_mock(status="in-progress", acceptance_criteria="")
        task.acceptance_criteria = None
        result = run_strict_pre_completion_checks(task, "T01")
        assert len(result) >= 1
        assert any("criteria" in w.lower() or "acceptance" in w.lower() for w in result)

    def test_task_id_included_in_status_warning(self) -> None:
        """Status warning message includes the task_id for traceability.

        Tests: run_strict_pre_completion_checks() status warning content.
        How: Pass NOT_STARTED task with task_id='T42', check warning contains 'T42'.
        Why: Warnings must be actionable — task_id identifies which task to investigate.
        """
        task = self._make_task_mock(status="not-started", acceptance_criteria="- [ ] Must pass")
        result = run_strict_pre_completion_checks(task, "T42")
        assert len(result) == 1
        assert "T42" in result[0]

    def test_task_id_included_in_criteria_warning(self) -> None:
        """Criteria warning message includes the task_id for traceability.

        Tests: run_strict_pre_completion_checks() criteria warning content.
        How: Pass in-progress task with empty criteria, task_id='T99'.
        Why: Warnings must be actionable — task_id identifies which task to investigate.
        """
        task = self._make_task_mock(status="in-progress", acceptance_criteria="")
        result = run_strict_pre_completion_checks(task, "T99")
        assert len(result) == 1
        assert "T99" in result[0]

    def test_return_type_is_always_list_of_str(self) -> None:
        """Function always returns list[str] regardless of status/criteria combination.

        Tests: run_strict_pre_completion_checks() return type invariant.
        How: Call with multiple status/criteria combinations, verify type each time.
        Why: Callers iterate warnings as strings; type must be stable across all inputs.
        """
        cases = [
            ("in-progress", "- [x] Works"),
            ("not-started", ""),
            ("in-progress", "   "),
            ("not-started", "- [ ] Pending"),
        ]
        for status, criteria in cases:
            task = self._make_task_mock(status=status, acceptance_criteria=criteria)
            result = run_strict_pre_completion_checks(task, "T01")
            assert isinstance(result, list)
            assert all(isinstance(w, str) for w in result)


# ---------------------------------------------------------------------------
# Integration: main() end-to-end paths
# ---------------------------------------------------------------------------


class TestMainIntegration:
    """Integration tests for main() covering profile/disable routing.

    Tests: main() dispatches correctly based on env vars and event type.
    Strategy: patch parse_hook_input to avoid stdin, patch handlers to avoid
    disk I/O, assert on SystemExit code and handler call counts.
    """

    def test_no_env_vars_post_tool_use_calls_handler(
        self, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture, hook_input_post_tool_use: dict[str, Any]
    ) -> None:
        """No env vars + PostToolUse -> handle_activity_update called (current behavior).

        Tests: main() backward compatibility for PostToolUse.
        How: Clear env vars, patch parse_hook_input and handle_activity_update, run main().
        Why: Without env vars, behavior must be identical to the pre-feature codebase.
        """
        monkeypatch.delenv("CLAUDE_SKILLS_HOOK_PROFILE", raising=False)
        monkeypatch.delenv("CLAUDE_SKILLS_DISABLED_HOOKS", raising=False)

        mocker.patch("task_status_hook.parse_hook_input", return_value=hook_input_post_tool_use)
        mock_activity = mocker.patch("task_status_hook.handle_activity_update")
        mock_stop = mocker.patch("task_status_hook.handle_subagent_stop")

        with pytest.raises(SystemExit) as exc_info:
            hook.main()

        assert exc_info.value.code == 0
        mock_activity.assert_called_once_with(hook_input_post_tool_use)
        mock_stop.assert_not_called()

    def test_no_env_vars_subagent_stop_calls_handler(
        self, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture, hook_input_subagent_stop: dict[str, Any]
    ) -> None:
        """No env vars + SubagentStop -> handle_subagent_stop called (current behavior).

        Tests: main() backward compatibility for SubagentStop.
        How: Clear env vars, patch parse_hook_input and handle_subagent_stop, run main().
        Why: Without env vars, SubagentStop must run exactly as before.
        """
        monkeypatch.delenv("CLAUDE_SKILLS_HOOK_PROFILE", raising=False)
        monkeypatch.delenv("CLAUDE_SKILLS_DISABLED_HOOKS", raising=False)

        mocker.patch("task_status_hook.parse_hook_input", return_value=hook_input_subagent_stop)
        mock_stop = mocker.patch("task_status_hook.handle_subagent_stop")
        mock_activity = mocker.patch("task_status_hook.handle_activity_update")

        with pytest.raises(SystemExit) as exc_info:
            hook.main()

        assert exc_info.value.code == 0
        mock_stop.assert_called_once_with(hook_input_subagent_stop, profile=HookProfile.STANDARD)
        mock_activity.assert_not_called()

    def test_minimal_profile_post_tool_use_skipped(
        self, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture, hook_input_post_tool_use: dict[str, Any]
    ) -> None:
        """profile=minimal + PostToolUse -> exits 0 without calling handler.

        Tests: main() minimal profile skips PostToolUse.
        How: Set HOOK_PROFILE=minimal, provide PostToolUse input, assert handler not called.
        Why: Minimal profile eliminates LastActivity timestamp I/O overhead.
        """
        monkeypatch.setenv("CLAUDE_SKILLS_HOOK_PROFILE", "minimal")
        monkeypatch.delenv("CLAUDE_SKILLS_DISABLED_HOOKS", raising=False)

        mocker.patch("task_status_hook.parse_hook_input", return_value=hook_input_post_tool_use)
        mock_activity = mocker.patch("task_status_hook.handle_activity_update")
        mock_stop = mocker.patch("task_status_hook.handle_subagent_stop")

        with pytest.raises(SystemExit) as exc_info:
            hook.main()

        assert exc_info.value.code == 0
        mock_activity.assert_not_called()
        mock_stop.assert_not_called()

    def test_minimal_profile_subagent_stop_runs(
        self, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture, hook_input_subagent_stop: dict[str, Any]
    ) -> None:
        """profile=minimal + SubagentStop -> handle_subagent_stop called normally.

        Tests: main() minimal profile does NOT skip SubagentStop.
        How: Set HOOK_PROFILE=minimal, provide SubagentStop input.
        Why: Completion marking must run even in minimal mode.
        """
        monkeypatch.setenv("CLAUDE_SKILLS_HOOK_PROFILE", "minimal")
        monkeypatch.delenv("CLAUDE_SKILLS_DISABLED_HOOKS", raising=False)

        mocker.patch("task_status_hook.parse_hook_input", return_value=hook_input_subagent_stop)
        mock_stop = mocker.patch("task_status_hook.handle_subagent_stop")
        mock_activity = mocker.patch("task_status_hook.handle_activity_update")

        with pytest.raises(SystemExit) as exc_info:
            hook.main()

        assert exc_info.value.code == 0
        mock_stop.assert_called_once_with(hook_input_subagent_stop, profile=HookProfile.MINIMAL)
        mock_activity.assert_not_called()

    def test_strict_profile_subagent_stop_passes_profile(
        self, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture, hook_input_subagent_stop: dict[str, Any]
    ) -> None:
        """profile=strict + SubagentStop -> handle_subagent_stop called with STRICT profile.

        Tests: main() strict profile threads profile into handler.
        How: Set HOOK_PROFILE=strict, assert handler called with profile=STRICT.
        Why: handle_subagent_stop runs strict checks only when profile=STRICT.
        """
        monkeypatch.setenv("CLAUDE_SKILLS_HOOK_PROFILE", "strict")
        monkeypatch.delenv("CLAUDE_SKILLS_DISABLED_HOOKS", raising=False)

        mocker.patch("task_status_hook.parse_hook_input", return_value=hook_input_subagent_stop)
        mock_stop = mocker.patch("task_status_hook.handle_subagent_stop")

        with pytest.raises(SystemExit) as exc_info:
            hook.main()

        assert exc_info.value.code == 0
        mock_stop.assert_called_once_with(hook_input_subagent_stop, profile=HookProfile.STRICT)

    def test_disabled_subagent_stop_exits_without_handler(
        self, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture, hook_input_subagent_stop: dict[str, Any]
    ) -> None:
        """DISABLED_HOOKS=subagent-stop + SubagentStop -> exits 0, handler not called.

        Tests: main() disabled hook early exit.
        How: Disable subagent-stop hook ID, provide SubagentStop event.
        Why: Explicit disable must prevent handler from running (ADR-002).
        """
        monkeypatch.delenv("CLAUDE_SKILLS_HOOK_PROFILE", raising=False)
        monkeypatch.setenv("CLAUDE_SKILLS_DISABLED_HOOKS", HOOK_ID_SUBAGENT_STOP)

        mocker.patch("task_status_hook.parse_hook_input", return_value=hook_input_subagent_stop)
        mock_stop = mocker.patch("task_status_hook.handle_subagent_stop")
        mock_activity = mocker.patch("task_status_hook.handle_activity_update")

        with pytest.raises(SystemExit) as exc_info:
            hook.main()

        assert exc_info.value.code == 0
        mock_stop.assert_not_called()
        mock_activity.assert_not_called()

    def test_disabled_post_tool_use_exits_without_handler(
        self, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture, hook_input_post_tool_use: dict[str, Any]
    ) -> None:
        """DISABLED_HOOKS=post-tool-use + PostToolUse -> exits 0, handler not called.

        Tests: main() disabled PostToolUse hook.
        How: Disable post-tool-use hook ID, provide PostToolUse event.
        Why: Disabled hook must exit 0 cleanly regardless of profile.
        """
        monkeypatch.delenv("CLAUDE_SKILLS_HOOK_PROFILE", raising=False)
        monkeypatch.setenv("CLAUDE_SKILLS_DISABLED_HOOKS", HOOK_ID_POST_TOOL_USE)

        mocker.patch("task_status_hook.parse_hook_input", return_value=hook_input_post_tool_use)
        mock_activity = mocker.patch("task_status_hook.handle_activity_update")
        mock_stop = mocker.patch("task_status_hook.handle_subagent_stop")

        with pytest.raises(SystemExit) as exc_info:
            hook.main()

        assert exc_info.value.code == 0
        mock_activity.assert_not_called()
        mock_stop.assert_not_called()

    def test_strict_profile_with_disabled_subagent_stop_skips_handler(
        self,
        monkeypatch: pytest.MonkeyPatch,
        mocker: MockerFixture,
        hook_input_subagent_stop: dict[str, Any],
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """profile=strict + DISABLED_HOOKS=subagent-stop -> disabled wins, handler skipped.

        Tests: main() disabled takes precedence over strict profile (ADR-002).
        How: Set HOOK_PROFILE=strict and disable subagent-stop. Handler must not run.
        Why: Explicit disable overrides profile semantics in all cases.
        """
        monkeypatch.setenv("CLAUDE_SKILLS_HOOK_PROFILE", "strict")
        monkeypatch.setenv("CLAUDE_SKILLS_DISABLED_HOOKS", HOOK_ID_SUBAGENT_STOP)

        mocker.patch("task_status_hook.parse_hook_input", return_value=hook_input_subagent_stop)
        mock_stop = mocker.patch("task_status_hook.handle_subagent_stop")

        with pytest.raises(SystemExit) as exc_info:
            hook.main()

        assert exc_info.value.code == 0
        mock_stop.assert_not_called()

    def test_skip_log_emitted_to_stderr_profile(
        self,
        monkeypatch: pytest.MonkeyPatch,
        mocker: MockerFixture,
        hook_input_post_tool_use: dict[str, Any],
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Skipped hook via profile emits '[hook] Skipped:' log to stderr.

        Tests: main() skip log format for profile-based skip.
        How: Set minimal profile, trigger PostToolUse skip, capture stderr.
        Why: Skip logs are observable signals that hooks are being controlled.
        """
        monkeypatch.setenv("CLAUDE_SKILLS_HOOK_PROFILE", "minimal")
        monkeypatch.delenv("CLAUDE_SKILLS_DISABLED_HOOKS", raising=False)

        mocker.patch("task_status_hook.parse_hook_input", return_value=hook_input_post_tool_use)
        mocker.patch("task_status_hook.handle_activity_update")

        with pytest.raises(SystemExit):
            hook.main()

        captured = capsys.readouterr()
        assert "[hook] Skipped:" in captured.err
        assert "profile=" in captured.err or "minimal" in captured.err

    def test_skip_log_emitted_to_stderr_disabled(
        self,
        monkeypatch: pytest.MonkeyPatch,
        mocker: MockerFixture,
        hook_input_subagent_stop: dict[str, Any],
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Skipped hook via disabled set emits '[hook] Skipped:' log with 'disabled'.

        Tests: main() skip log format for disabled-set skip.
        How: Disable subagent-stop, trigger SubagentStop skip, capture stderr.
        Why: 'disabled' in log distinguishes from profile-based skip.
        """
        monkeypatch.delenv("CLAUDE_SKILLS_HOOK_PROFILE", raising=False)
        monkeypatch.setenv("CLAUDE_SKILLS_DISABLED_HOOKS", HOOK_ID_SUBAGENT_STOP)

        mocker.patch("task_status_hook.parse_hook_input", return_value=hook_input_subagent_stop)
        mocker.patch("task_status_hook.handle_subagent_stop")

        with pytest.raises(SystemExit):
            hook.main()

        captured = capsys.readouterr()
        assert "[hook] Skipped:" in captured.err
        assert "disabled" in captured.err

    def test_parse_hook_input_consumed_before_skip(
        self, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture, hook_input_post_tool_use: dict[str, Any]
    ) -> None:
        """parse_hook_input is called even when hook will be skipped.

        Tests: main() stdin consumption before skip check.
        How: Set minimal profile (would skip), spy on parse_hook_input.
        Why: stdin must always be consumed to avoid pipe errors (design constraint).
        """
        monkeypatch.setenv("CLAUDE_SKILLS_HOOK_PROFILE", "minimal")
        monkeypatch.delenv("CLAUDE_SKILLS_DISABLED_HOOKS", raising=False)

        mock_parse = mocker.patch("task_status_hook.parse_hook_input", return_value=hook_input_post_tool_use)
        mocker.patch("task_status_hook.handle_activity_update")

        with pytest.raises(SystemExit):
            hook.main()

        mock_parse.assert_called_once()

    def test_unknown_event_exits_zero_silently(self, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture) -> None:
        """Unknown event name exits 0 silently (existing behavior unchanged).

        Tests: main() unknown event passthrough.
        How: Provide hook input with unrecognized hook_event_name.
        Why: Unknown events must not crash the hook; exit 0 silently.
        """
        monkeypatch.delenv("CLAUDE_SKILLS_HOOK_PROFILE", raising=False)
        monkeypatch.delenv("CLAUDE_SKILLS_DISABLED_HOOKS", raising=False)

        unknown_input: dict[str, Any] = {"hook_event_name": "PreToolUse", "session_id": "s1"}
        mocker.patch("task_status_hook.parse_hook_input", return_value=unknown_input)
        mock_stop = mocker.patch("task_status_hook.handle_subagent_stop")
        mock_activity = mocker.patch("task_status_hook.handle_activity_update")

        with pytest.raises(SystemExit) as exc_info:
            hook.main()

        assert exc_info.value.code == 0
        mock_stop.assert_not_called()
        mock_activity.assert_not_called()

    def test_invalid_stdin_json_exits_two(self, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture) -> None:
        """parse_hook_input raising JSONDecodeError causes main() to exit with code 2.

        Tests: main() stdin parse error path.
        How: Patch parse_hook_input to raise json.JSONDecodeError, assert exit code 2.
        Why: Malformed stdin must produce exit code 2 (error signal) not 0 (success).
        """
        import json

        monkeypatch.delenv("CLAUDE_SKILLS_HOOK_PROFILE", raising=False)
        monkeypatch.delenv("CLAUDE_SKILLS_DISABLED_HOOKS", raising=False)

        mocker.patch("task_status_hook.parse_hook_input", side_effect=json.JSONDecodeError("bad json", "", 0))

        with pytest.raises(SystemExit) as exc_info:
            hook.main()

        assert exc_info.value.code == 2

    def test_post_tool_use_non_matching_tool_no_handler(
        self, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
    ) -> None:
        """PostToolUse with tool_name='Read' does not call handle_activity_update.

        Tests: main() PostToolUse tool_name filter (Write/Edit/Bash only).
        How: Set tool_name to 'Read', confirm handler not called.
        Why: Only Write/Edit/Bash trigger LastActivity updates; Read must not.
        """
        monkeypatch.delenv("CLAUDE_SKILLS_HOOK_PROFILE", raising=False)
        monkeypatch.delenv("CLAUDE_SKILLS_DISABLED_HOOKS", raising=False)

        read_input: dict[str, Any] = {
            "hook_event_name": "PostToolUse",
            "tool_name": "Read",
            "session_id": "s1",
            "cwd": "/tmp",
        }
        mocker.patch("task_status_hook.parse_hook_input", return_value=read_input)
        mock_activity = mocker.patch("task_status_hook.handle_activity_update")

        with pytest.raises(SystemExit) as exc_info:
            hook.main()

        assert exc_info.value.code == 0
        mock_activity.assert_not_called()


# ---------------------------------------------------------------------------
# Backward compatibility: fixture validates against parse_hook_input
# ---------------------------------------------------------------------------


class TestFixtureValidity:
    """Verify test fixtures produce dicts that parse_hook_input would accept.

    Tests: Fixture correctness — ensures integration test inputs are realistic.
    """

    def test_subagent_stop_fixture_parseable(self, hook_input_subagent_stop: dict[str, Any]) -> None:
        """hook_input_subagent_stop fixture has required hook_event_name field.

        Tests: SubagentStop fixture shape.
        How: Check fixture has hook_event_name=SubagentStop.
        Why: Fixtures that don't match real hook input shape produce misleading test results.
        """
        assert hook_input_subagent_stop["hook_event_name"] == "SubagentStop"
        assert "session_id" in hook_input_subagent_stop

    def test_post_tool_use_fixture_parseable(self, hook_input_post_tool_use: dict[str, Any]) -> None:
        """hook_input_post_tool_use fixture has required hook_event_name and tool_name fields.

        Tests: PostToolUse fixture shape.
        How: Check fixture has hook_event_name=PostToolUse and tool_name=Write.
        Why: tool_name=Write is required to trigger handle_activity_update in main().
        """
        assert hook_input_post_tool_use["hook_event_name"] == "PostToolUse"
        assert hook_input_post_tool_use["tool_name"] == "Write"
        assert "session_id" in hook_input_post_tool_use

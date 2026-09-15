"""Tests for the disabled-hook control in task_status_hook.py.

Tests: disabled-hook parsing (CLAUDE_SKILLS_DISABLED_HOOKS), skip decision logic, and
main() integration paths.

Step 1a (see plan-posttooluse-activetask.md) deleted the PostToolUse handler and the
CLAUDE_SKILLS_HOOK_PROFILE runtime profile that gated it — SubagentStop settle is now the
only handler, and CLAUDE_SKILLS_DISABLED_HOOKS is the only remaining runtime control.

Strategy:
- Unit tests for parse_disabled_hooks and should_skip_hook use monkeypatch for env var
  control.
- Integration tests for main() patch parse_hook_input (avoids stdin) and handle_subagent_stop
  (avoids disk I/O). main() always calls sys.exit(0) which raises SystemExit; tests assert
  on the exit code and whether the handler was called.
- No test touches real task plan files on disk.

Test file: plugins/development-harness/tests/test_task_status_hook_profiles.py
Implementation: plugins/development-harness/skills/implementation-manager/scripts/task_status_hook.py
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

# task_status_hook is on pythonpath via pyproject.toml:
#   ./plugins/development-harness/skills/implementation-manager/scripts
# No sys.path manipulation required here.
import task_status_hook as hook
from task_status_hook import HOOK_ID_SUBAGENT_STOP, parse_disabled_hooks, should_skip_hook

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
        How: Set env var to 'task-status:subagent-stop'.
        Why: Single-hook disable is the most common use case.
        """
        monkeypatch.setenv("CLAUDE_SKILLS_DISABLED_HOOKS", HOOK_ID_SUBAGENT_STOP)
        result = parse_disabled_hooks()
        assert result == {HOOK_ID_SUBAGENT_STOP}

    def test_multiple_comma_separated_ids(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Multiple comma-separated IDs return the full set.

        Tests: parse_disabled_hooks() multi-ID parsing.
        How: Set env var to two IDs comma-separated.
        Why: The parser is generic — it must not assume only one real hook ID exists.
        """
        monkeypatch.setenv("CLAUDE_SKILLS_DISABLED_HOOKS", f"{HOOK_ID_SUBAGENT_STOP},other:hook")
        result = parse_disabled_hooks()
        assert result == {HOOK_ID_SUBAGENT_STOP, "other:hook"}

    def test_whitespace_stripped_from_each_id(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Whitespace around each ID is stripped.

        Tests: parse_disabled_hooks() whitespace stripping.
        How: Include spaces around IDs in env var value.
        Why: Users may include spaces for readability; must be tolerated.
        """
        monkeypatch.setenv("CLAUDE_SKILLS_DISABLED_HOOKS", f"  {HOOK_ID_SUBAGENT_STOP}  ,  other:hook  ")
        result = parse_disabled_hooks()
        assert result == {HOOK_ID_SUBAGENT_STOP, "other:hook"}

    def test_trailing_comma_excluded(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Trailing comma produces no empty-string entry in the result set.

        Tests: parse_disabled_hooks() trailing comma handling.
        How: Set env var with trailing comma.
        Why: Empty segments from consecutive or trailing commas must not appear.
        """
        monkeypatch.setenv("CLAUDE_SKILLS_DISABLED_HOOKS", f"{HOOK_ID_SUBAGENT_STOP},")
        result = parse_disabled_hooks()
        assert result == {HOOK_ID_SUBAGENT_STOP}
        assert "" not in result

    def test_consecutive_commas_no_empty_segments(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Consecutive commas produce no empty-string entries.

        Tests: parse_disabled_hooks() consecutive comma handling.
        How: Set env var with double comma between IDs.
        Why: Defensive parsing must exclude empty segments entirely.
        """
        monkeypatch.setenv("CLAUDE_SKILLS_DISABLED_HOOKS", f"{HOOK_ID_SUBAGENT_STOP},,other:hook")
        result = parse_disabled_hooks()
        assert result == {HOOK_ID_SUBAGENT_STOP, "other:hook"}
        assert "" not in result

    def test_unknown_hook_ids_included(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Unknown hook IDs are included in the result set without warning.

        Tests: parse_disabled_hooks() unknown ID forward compatibility.
        How: Set env var to an unrecognized hook ID.
        Why: No validation is performed — unknown IDs silently never match.
        """
        monkeypatch.setenv("CLAUDE_SKILLS_DISABLED_HOOKS", "future-hook:some-handler")
        result = parse_disabled_hooks()
        assert "future-hook:some-handler" in result


# ---------------------------------------------------------------------------
# Unit: should_skip_hook()
# ---------------------------------------------------------------------------


class TestShouldSkipHook:
    """Unit tests for should_skip_hook().

    Tests: SubagentStop runs by default, is skipped when disabled by ID, and an
    unrecognised event name is never skipped (it has no hook ID to match).
    """

    def test_subagent_stop_runs_by_default(self) -> None:
        """SubagentStop with an empty disabled set -> False (run).

        Tests: should_skip_hook() default behaviour.
        How: Call with SubagentStop event and an empty disabled set.
        Why: SubagentStop settle must run unless explicitly disabled.
        """
        result = should_skip_hook("SubagentStop", set())
        assert result is False

    def test_subagent_stop_disabled_skipped(self) -> None:
        """SubagentStop disabled by ID -> True.

        Tests: should_skip_hook() disabled set for SubagentStop.
        How: Pass SubagentStop with its hook ID in the disabled set.
        Why: Explicit disable must prevent the handler from running.
        """
        result = should_skip_hook("SubagentStop", {HOOK_ID_SUBAGENT_STOP})
        assert result is True

    def test_unrelated_disabled_id_does_not_skip(self) -> None:
        """A disabled set naming an unrelated hook ID does not skip SubagentStop.

        Tests: should_skip_hook() only matches the event's own hook ID.
        How: Disable an unrelated hook ID, call with SubagentStop.
        Why: Disabling one hook must not silently disable another.
        """
        result = should_skip_hook("SubagentStop", {"other:hook"})
        assert result is False

    def test_unknown_event_name_not_skipped(self) -> None:
        """Unknown event name -> False (let dispatch handle it).

        Tests: should_skip_hook() unknown event fallthrough.
        How: Pass an unrecognized event name.
        Why: Unknown events have no hook_id in _EVENT_TO_HOOK_ID; they fall through
        to existing dispatch which handles unknowns silently.
        """
        result = should_skip_hook("UnknownEvent", set())
        assert result is False


# ---------------------------------------------------------------------------
# Integration: main() end-to-end paths
# ---------------------------------------------------------------------------


class TestMainIntegration:
    """Integration tests for main() covering SubagentStop dispatch and disable routing.

    Tests: main() dispatches correctly based on env vars and event type.
    Strategy: patch parse_hook_input to avoid stdin, patch handle_subagent_stop to avoid
    disk I/O, assert on SystemExit code and handler call counts.
    """

    def test_no_env_vars_subagent_stop_calls_handler(
        self, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture, hook_input_subagent_stop: dict[str, Any]
    ) -> None:
        """No env vars + SubagentStop -> handle_subagent_stop called.

        Tests: main() default behavior for SubagentStop.
        How: Clear env vars, patch parse_hook_input and handle_subagent_stop, run main().
        Why: Without env vars, SubagentStop must run.
        """
        monkeypatch.delenv("CLAUDE_SKILLS_DISABLED_HOOKS", raising=False)

        mocker.patch("task_status_hook.parse_hook_input", return_value=hook_input_subagent_stop)
        mock_stop = mocker.patch("task_status_hook.handle_subagent_stop")

        with pytest.raises(SystemExit) as exc_info:
            hook.main()

        assert exc_info.value.code == 0
        mock_stop.assert_called_once_with(hook_input_subagent_stop)

    def test_disabled_subagent_stop_exits_without_handler(
        self, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture, hook_input_subagent_stop: dict[str, Any]
    ) -> None:
        """DISABLED_HOOKS=subagent-stop + SubagentStop -> exits 0, handler not called.

        Tests: main() disabled hook early exit.
        How: Disable subagent-stop hook ID, provide SubagentStop event.
        Why: Explicit disable must prevent handler from running.
        """
        monkeypatch.setenv("CLAUDE_SKILLS_DISABLED_HOOKS", HOOK_ID_SUBAGENT_STOP)

        mocker.patch("task_status_hook.parse_hook_input", return_value=hook_input_subagent_stop)
        mock_stop = mocker.patch("task_status_hook.handle_subagent_stop")

        with pytest.raises(SystemExit) as exc_info:
            hook.main()

        assert exc_info.value.code == 0
        mock_stop.assert_not_called()

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
        Why: The skip log is an observable signal that a hook is being controlled.
        """
        monkeypatch.setenv("CLAUDE_SKILLS_DISABLED_HOOKS", HOOK_ID_SUBAGENT_STOP)

        mocker.patch("task_status_hook.parse_hook_input", return_value=hook_input_subagent_stop)
        mocker.patch("task_status_hook.handle_subagent_stop")

        with pytest.raises(SystemExit):
            hook.main()

        captured = capsys.readouterr()
        assert "[hook] Skipped:" in captured.err
        assert "disabled" in captured.err

    def test_parse_hook_input_consumed_before_skip(
        self, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture, hook_input_subagent_stop: dict[str, Any]
    ) -> None:
        """parse_hook_input is called even when the hook will be skipped.

        Tests: main() stdin consumption before skip check.
        How: Disable subagent-stop (would skip), spy on parse_hook_input.
        Why: stdin must always be consumed to avoid pipe errors (design constraint).
        """
        monkeypatch.setenv("CLAUDE_SKILLS_DISABLED_HOOKS", HOOK_ID_SUBAGENT_STOP)

        mock_parse = mocker.patch("task_status_hook.parse_hook_input", return_value=hook_input_subagent_stop)
        mocker.patch("task_status_hook.handle_subagent_stop")

        with pytest.raises(SystemExit):
            hook.main()

        mock_parse.assert_called_once()

    def test_unknown_event_exits_zero_silently(self, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture) -> None:
        """Unknown event name exits 0 silently (existing behavior unchanged).

        Tests: main() unknown event passthrough.
        How: Provide hook input with unrecognized hook_event_name.
        Why: Unknown events must not crash the hook; exit 0 silently.
        """
        monkeypatch.delenv("CLAUDE_SKILLS_DISABLED_HOOKS", raising=False)

        unknown_input: dict[str, Any] = {"hook_event_name": "PreToolUse", "session_id": "s1"}
        mocker.patch("task_status_hook.parse_hook_input", return_value=unknown_input)
        mock_stop = mocker.patch("task_status_hook.handle_subagent_stop")

        with pytest.raises(SystemExit) as exc_info:
            hook.main()

        assert exc_info.value.code == 0
        mock_stop.assert_not_called()

    def test_invalid_stdin_json_exits_two(self, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture) -> None:
        """parse_hook_input raising JSONDecodeError causes main() to exit with code 2.

        Tests: main() stdin parse error path.
        How: Patch parse_hook_input to raise json.JSONDecodeError, assert exit code 2.
        Why: Malformed stdin must produce exit code 2 (error signal) not 0 (success).
        """
        import json

        monkeypatch.delenv("CLAUDE_SKILLS_DISABLED_HOOKS", raising=False)

        mocker.patch("task_status_hook.parse_hook_input", side_effect=json.JSONDecodeError("bad json", "", 0))

        with pytest.raises(SystemExit) as exc_info:
            hook.main()

        assert exc_info.value.code == 2


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

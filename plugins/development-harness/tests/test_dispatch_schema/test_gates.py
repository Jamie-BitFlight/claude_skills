"""Tests for dispatch_schema.gates.run_quality_gates.

Covers: empty command list, single passing command, single failing command,
fail-fast mode halts on first failure, run-all mode collects all results,
command-not-found produces exit_code=127 without raising, stdout/stderr
capture, custom cwd forwarded to subprocess, GateResult.passed semantics,
and CommandResult field population.

Test naming: test_{scenario}_{expected_result}
Structure: AAA (Arrange / Act / Assert)
Mocking: pytest-mock (MockerFixture) only — no unittest.mock imports.
"""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import dispatch_schema.gates as _gates_module
import pytest
from dispatch_schema.core.models import GateResult, GateRunMode
from dispatch_schema.gates import run_quality_gates

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_resolve_executable_cache() -> None:
    """Clear the _resolve_executable lru_cache before each test.

    Prevents a cached real shutil.which result from a previous test from
    bypassing a mocker.patch("dispatch_schema.gates.shutil.which", ...) mock
    installed by the current test.
    """
    _gates_module._resolve_executable.cache_clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_completed_process(
    returncode: int = 0, stdout: str = "", stderr: str = ""
) -> subprocess.CompletedProcess[str]:
    """Build a CompletedProcess stub for use in mocker.patch returns."""
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


# ---------------------------------------------------------------------------
# Empty command list
# ---------------------------------------------------------------------------


class TestEmptyCommandList:
    """run_quality_gates with an empty commands list."""

    def test_empty_commands_returns_passed_true(self) -> None:
        """Empty command list returns GateResult with passed=True.

        Tests: run_quality_gates with no commands.
        How: Call with empty list; assert passed=True and no results.
        Why: No failures among zero commands — vacuously passes.
        """
        # Arrange / Act
        result = run_quality_gates([])

        # Assert
        assert result.passed is True
        assert result.results == []

    def test_empty_commands_returns_empty_results_list(self) -> None:
        """Empty command list returns GateResult with empty results list.

        Tests: results field when commands is empty.
        How: Call with empty list; assert results is [].
        Why: Callers must be able to iterate results safely with no commands.
        """
        # Arrange / Act
        result = run_quality_gates([])

        # Assert
        assert result.results == []

    def test_empty_commands_preserves_mode_in_result(self) -> None:
        """Empty command list records the requested mode in GateResult.

        Tests: GateResult.mode field with empty commands.
        How: Call with RUN_ALL mode and empty list; assert mode matches.
        Why: Callers may inspect mode to understand how results were collected.
        """
        # Arrange / Act
        result = run_quality_gates([], mode=GateRunMode.RUN_ALL)

        # Assert
        assert result.mode == GateRunMode.RUN_ALL


# ---------------------------------------------------------------------------
# Single passing command
# ---------------------------------------------------------------------------


class TestSinglePassingCommand:
    """run_quality_gates with one command that exits 0."""

    def test_single_passing_command_returns_passed_true(self, mocker: MockerFixture) -> None:
        """Single command with exit_code=0 produces GateResult.passed=True.

        Tests: Happy path — one passing command.
        How: Patch shutil.which to return a resolved path; patch subprocess.run
             to return CompletedProcess(returncode=0). Assert GateResult.passed.
        Why: Confirms the basic success path works end-to-end.
        """
        # Arrange
        mocker.patch("dispatch_schema.gates.shutil.which", return_value="/usr/bin/true")
        mocker.patch(
            "dispatch_schema.gates.subprocess.run", return_value=_make_completed_process(returncode=0, stdout="ok\n")
        )

        # Act
        result = run_quality_gates(["true"])

        # Assert
        assert result.passed is True

    def test_single_passing_command_produces_one_result(self, mocker: MockerFixture) -> None:
        """Single command produces exactly one CommandResult in results.

        Tests: results list length for one command.
        How: Patch subprocess.run; assert len(result.results) == 1.
        Why: Ensures each command yields exactly one entry.
        """
        # Arrange
        mocker.patch("dispatch_schema.gates.shutil.which", return_value="/usr/bin/true")
        mocker.patch("dispatch_schema.gates.subprocess.run", return_value=_make_completed_process(returncode=0))

        # Act
        result = run_quality_gates(["true"])

        # Assert
        assert len(result.results) == 1

    def test_single_passing_command_captures_stdout(self, mocker: MockerFixture) -> None:
        """CommandResult.stdout contains the subprocess stdout text.

        Tests: stdout capture in CommandResult.
        How: Patch subprocess.run to return stdout="hello\n"; assert captured.
        Why: Callers rely on stdout to display gate output to users.
        """
        # Arrange
        mocker.patch("dispatch_schema.gates.shutil.which", return_value="/usr/bin/echo")
        mocker.patch(
            "dispatch_schema.gates.subprocess.run", return_value=_make_completed_process(returncode=0, stdout="hello\n")
        )

        # Act
        result = run_quality_gates(["echo hello"])

        # Assert
        assert result.results[0].stdout == "hello\n"

    def test_single_passing_command_captures_stderr(self, mocker: MockerFixture) -> None:
        """CommandResult.stderr contains the subprocess stderr text.

        Tests: stderr capture in CommandResult.
        How: Patch subprocess.run to return stderr="warn\n"; assert captured.
        Why: Stderr may contain warnings that callers need to surface.
        """
        # Arrange
        mocker.patch("dispatch_schema.gates.shutil.which", return_value="/usr/bin/mybin")
        mocker.patch(
            "dispatch_schema.gates.subprocess.run", return_value=_make_completed_process(returncode=0, stderr="warn\n")
        )

        # Act
        result = run_quality_gates(["mybin --check"])

        # Assert
        assert result.results[0].stderr == "warn\n"

    def test_single_passing_command_preserves_original_command_string(self, mocker: MockerFixture) -> None:
        """CommandResult.command stores the original command string, not the resolved path.

        Tests: CommandResult.command field fidelity.
        How: Patch which to return a different path; assert .command == original string.
        Why: Callers display the command string for diagnostics — it must match input.
        """
        # Arrange
        mocker.patch("dispatch_schema.gates.shutil.which", return_value="/usr/local/bin/uv")
        mocker.patch("dispatch_schema.gates.subprocess.run", return_value=_make_completed_process(returncode=0))

        # Act
        result = run_quality_gates(["uv run pytest"])

        # Assert
        assert result.results[0].command == "uv run pytest"


# ---------------------------------------------------------------------------
# Single failing command
# ---------------------------------------------------------------------------


class TestSingleFailingCommand:
    """run_quality_gates with one command that exits non-zero."""

    def test_single_failing_command_returns_passed_false(self, mocker: MockerFixture) -> None:
        """Single command with non-zero exit_code produces GateResult.passed=False.

        Tests: Failure detection for one command.
        How: Patch subprocess.run to return returncode=1; assert passed=False.
        Why: A failing gate must propagate failure to the aggregate result.
        """
        # Arrange
        mocker.patch("dispatch_schema.gates.shutil.which", return_value="/usr/bin/false")
        mocker.patch("dispatch_schema.gates.subprocess.run", return_value=_make_completed_process(returncode=1))

        # Act
        result = run_quality_gates(["false"])

        # Assert
        assert result.passed is False

    def test_single_failing_command_result_passed_is_false(self, mocker: MockerFixture) -> None:
        """CommandResult.passed is False when exit_code != 0.

        Tests: CommandResult.passed field derivation.
        How: Patch subprocess.run with returncode=2; assert CommandResult.passed.
        Why: Each result must independently reflect its own exit code.
        """
        # Arrange
        mocker.patch("dispatch_schema.gates.shutil.which", return_value="/usr/bin/false")
        mocker.patch("dispatch_schema.gates.subprocess.run", return_value=_make_completed_process(returncode=2))

        # Act
        result = run_quality_gates(["false"])

        # Assert
        assert result.results[0].passed is False
        assert result.results[0].exit_code == 2


# ---------------------------------------------------------------------------
# Fail-fast mode
# ---------------------------------------------------------------------------


class TestFailFastMode:
    """run_quality_gates with mode=GateRunMode.FAIL_FAST (default)."""

    def test_fail_fast_stops_after_first_failure(self, mocker: MockerFixture) -> None:
        """Fail-fast mode stops executing after the first failing command.

        Tests: Fail-fast execution halt.
        How: Provide three commands; first fails; assert only one result collected.
        Why: Fail-fast prevents wasted execution and surfaces the earliest failure.
        """
        # Arrange
        mocker.patch("dispatch_schema.gates.shutil.which", return_value="/usr/bin/cmd")
        mock_run = mocker.patch(
            "dispatch_schema.gates.subprocess.run", return_value=_make_completed_process(returncode=1)
        )

        # Act
        result = run_quality_gates(["cmd a", "cmd b", "cmd c"], mode=GateRunMode.FAIL_FAST)

        # Assert
        assert len(result.results) == 1
        mock_run.assert_called_once()

    def test_fail_fast_is_the_default_mode(self, mocker: MockerFixture) -> None:
        """Calling run_quality_gates without mode= defaults to FAIL_FAST.

        Tests: Default mode parameter.
        How: Call without mode; patch two commands (first fails); assert one result.
        Why: The default must be safe (fail-fast), not permissive (run-all).
        """
        # Arrange
        mocker.patch("dispatch_schema.gates.shutil.which", return_value="/usr/bin/cmd")
        mocker.patch("dispatch_schema.gates.subprocess.run", return_value=_make_completed_process(returncode=1))

        # Act
        result = run_quality_gates(["cmd a", "cmd b"])

        # Assert
        assert result.mode == GateRunMode.FAIL_FAST
        assert len(result.results) == 1

    def test_fail_fast_records_mode_in_result(self, mocker: MockerFixture) -> None:
        """GateResult.mode is FAIL_FAST when that mode was used.

        Tests: GateResult.mode field in fail-fast scenario.
        How: Call with FAIL_FAST; assert result.mode.
        Why: Callers may need to log or display execution mode.
        """
        # Arrange
        mocker.patch("dispatch_schema.gates.shutil.which", return_value="/usr/bin/true")
        mocker.patch("dispatch_schema.gates.subprocess.run", return_value=_make_completed_process(returncode=0))

        # Act
        result = run_quality_gates(["true"], mode=GateRunMode.FAIL_FAST)

        # Assert
        assert result.mode == GateRunMode.FAIL_FAST

    def test_fail_fast_continues_through_all_passing_commands(self, mocker: MockerFixture) -> None:
        """Fail-fast mode collects all results when every command passes.

        Tests: Fail-fast does not short-circuit on success.
        How: Provide three passing commands; assert all three results collected.
        Why: Fail-fast must only halt on failure, not on every result.
        """
        # Arrange
        mocker.patch("dispatch_schema.gates.shutil.which", return_value="/usr/bin/true")
        mocker.patch("dispatch_schema.gates.subprocess.run", return_value=_make_completed_process(returncode=0))

        # Act
        result = run_quality_gates(["true", "true", "true"], mode=GateRunMode.FAIL_FAST)

        # Assert
        assert len(result.results) == 3
        assert result.passed is True


# ---------------------------------------------------------------------------
# Run-all mode
# ---------------------------------------------------------------------------


class TestRunAllMode:
    """run_quality_gates with mode=GateRunMode.RUN_ALL."""

    def test_run_all_executes_every_command_despite_failure(self, mocker: MockerFixture) -> None:
        """Run-all mode executes every command regardless of failures.

        Tests: RUN_ALL does not halt on failure.
        How: Provide three commands; first fails; assert all three results collected.
        Why: Run-all is used when callers need a full diagnostic picture.
        """
        # Arrange
        mocker.patch("dispatch_schema.gates.shutil.which", return_value="/usr/bin/cmd")
        mocker.patch(
            "dispatch_schema.gates.subprocess.run",
            side_effect=[
                _make_completed_process(returncode=1),
                _make_completed_process(returncode=0),
                _make_completed_process(returncode=0),
            ],
        )

        # Act
        result = run_quality_gates(["cmd a", "cmd b", "cmd c"], mode=GateRunMode.RUN_ALL)

        # Assert
        assert len(result.results) == 3

    def test_run_all_passed_is_false_when_any_command_fails(self, mocker: MockerFixture) -> None:
        """GateResult.passed is False if any command failed in run-all mode.

        Tests: Aggregate passed field with mixed results.
        How: First fails, rest pass; assert GateResult.passed=False.
        Why: A partial success is still a failure for gate purposes.
        """
        # Arrange
        mocker.patch("dispatch_schema.gates.shutil.which", return_value="/usr/bin/cmd")
        mocker.patch(
            "dispatch_schema.gates.subprocess.run",
            side_effect=[
                _make_completed_process(returncode=1),
                _make_completed_process(returncode=0),
                _make_completed_process(returncode=0),
            ],
        )

        # Act
        result = run_quality_gates(["cmd a", "cmd b", "cmd c"], mode=GateRunMode.RUN_ALL)

        # Assert
        assert result.passed is False

    def test_run_all_records_mode_in_result(self, mocker: MockerFixture) -> None:
        """GateResult.mode is RUN_ALL when that mode was used.

        Tests: GateResult.mode field in run-all scenario.
        How: Call with RUN_ALL; assert result.mode.
        Why: Callers may need to distinguish how results were collected.
        """
        # Arrange
        mocker.patch("dispatch_schema.gates.shutil.which", return_value="/usr/bin/true")
        mocker.patch("dispatch_schema.gates.subprocess.run", return_value=_make_completed_process(returncode=0))

        # Act
        result = run_quality_gates(["true"], mode=GateRunMode.RUN_ALL)

        # Assert
        assert result.mode == GateRunMode.RUN_ALL


# ---------------------------------------------------------------------------
# Command-not-found (exit_code=127)
# ---------------------------------------------------------------------------


class TestCommandNotFound:
    """run_quality_gates when shutil.which cannot resolve the executable."""

    def test_command_not_found_returns_exit_code_127(self, mocker: MockerFixture) -> None:
        """Unresolvable command produces CommandResult.exit_code=127.

        Tests: command-not-found path in run_quality_gates.
        How: Patch shutil.which to return None; assert CommandResult.exit_code.
        Why: 127 is the POSIX convention for command-not-found; callers check it.
        """
        # Arrange
        mocker.patch("dispatch_schema.gates.shutil.which", return_value=None)

        # Act
        result = run_quality_gates(["nonexistent-command --flag"])

        # Assert
        assert result.results[0].exit_code == 127

    def test_command_not_found_does_not_raise_exception(self, mocker: MockerFixture) -> None:
        """Unresolvable command does not raise any exception.

        Tests: No exception propagation for command-not-found.
        How: Patch shutil.which to return None; call run_quality_gates; no raises.
        Why: Gate runner must be resilient — a missing tool is a gate failure,
             not a crash.
        """
        # Arrange
        mocker.patch("dispatch_schema.gates.shutil.which", return_value=None)

        # Act / Assert (no exception expected)
        result = run_quality_gates(["nonexistent-command"])
        assert isinstance(result, GateResult)

    def test_command_not_found_sets_passed_false(self, mocker: MockerFixture) -> None:
        """Unresolvable command sets CommandResult.passed=False.

        Tests: passed field for command-not-found.
        How: Patch shutil.which to return None; assert CommandResult.passed.
        Why: Missing executable is a definitive failure — passed must be False.
        """
        # Arrange
        mocker.patch("dispatch_schema.gates.shutil.which", return_value=None)

        # Act
        result = run_quality_gates(["ghost-tool"])

        # Assert
        assert result.results[0].passed is False

    def test_command_not_found_stderr_contains_command_name(self, mocker: MockerFixture) -> None:
        """CommandResult.stderr names the unresolvable command.

        Tests: stderr content for command-not-found path.
        How: Patch shutil.which to return None; assert stderr mentions the command.
        Why: Callers display stderr to diagnose why a gate failed.
        """
        # Arrange
        mocker.patch("dispatch_schema.gates.shutil.which", return_value=None)

        # Act
        result = run_quality_gates(["ghost-tool --run"])

        # Assert
        assert "ghost-tool" in result.results[0].stderr

    def test_command_not_found_subprocess_run_not_called(self, mocker: MockerFixture) -> None:
        """subprocess.run is never called when shutil.which returns None.

        Tests: subprocess.run invocation is skipped for command-not-found.
        How: Patch both which and subprocess.run; assert subprocess.run not called.
        Why: No subprocess should be spawned for an unresolvable command.
        """
        # Arrange
        mocker.patch("dispatch_schema.gates.shutil.which", return_value=None)
        mock_run = mocker.patch("dispatch_schema.gates.subprocess.run")

        # Act
        run_quality_gates(["ghost-tool"])

        # Assert
        mock_run.assert_not_called()

    def test_command_not_found_fail_fast_stops_after_missing_command(self, mocker: MockerFixture) -> None:
        """Fail-fast stops after a command-not-found result, skipping remaining commands.

        Tests: Fail-fast interaction with command-not-found.
        How: First command unresolvable; second resolvable; assert only one result.
        Why: command-not-found is passed=False, so fail-fast must honour it.
        """
        # Arrange
        mocker.patch("dispatch_schema.gates.shutil.which", side_effect=[None, "/usr/bin/true"])
        mock_run = mocker.patch("dispatch_schema.gates.subprocess.run")

        # Act
        result = run_quality_gates(["ghost-tool", "true"], mode=GateRunMode.FAIL_FAST)

        # Assert
        assert len(result.results) == 1
        mock_run.assert_not_called()


# ---------------------------------------------------------------------------
# cwd forwarding
# ---------------------------------------------------------------------------


class TestCwdForwarding:
    """run_quality_gates forwards cwd to subprocess.run."""

    def test_cwd_is_forwarded_to_subprocess_run(self, mocker: MockerFixture, tmp_path: Path) -> None:
        """cwd parameter is passed through to subprocess.run.

        Tests: cwd forwarding to subprocess.
        How: Patch subprocess.run; capture call kwargs; assert cwd matches.
        Why: Gate commands must execute in the correct working directory.
        """
        # Arrange
        mocker.patch("dispatch_schema.gates.shutil.which", return_value="/usr/bin/true")
        mock_run = mocker.patch(
            "dispatch_schema.gates.subprocess.run", return_value=_make_completed_process(returncode=0)
        )

        # Act
        run_quality_gates(["true"], cwd=tmp_path)

        # Assert
        _, kwargs = mock_run.call_args
        assert kwargs["cwd"] == tmp_path

    def test_cwd_none_passes_none_to_subprocess(self, mocker: MockerFixture) -> None:
        """cwd=None (default) passes None to subprocess.run.

        Tests: Default cwd value forwarding.
        How: Patch subprocess.run; call without cwd; assert cwd kwarg is None.
        Why: None instructs subprocess to inherit the current process directory.
        """
        # Arrange
        mocker.patch("dispatch_schema.gates.shutil.which", return_value="/usr/bin/true")
        mock_run = mocker.patch(
            "dispatch_schema.gates.subprocess.run", return_value=_make_completed_process(returncode=0)
        )

        # Act
        run_quality_gates(["true"])

        # Assert
        _, kwargs = mock_run.call_args
        assert kwargs["cwd"] is None


# ---------------------------------------------------------------------------
# subprocess.run invocation contract
# ---------------------------------------------------------------------------


class TestSubprocessInvocationContract:
    """run_quality_gates calls subprocess.run with the correct arguments."""

    def test_subprocess_run_called_with_capture_output_true(self, mocker: MockerFixture) -> None:
        """subprocess.run is called with capture_output=True.

        Tests: stdout/stderr capture configuration.
        How: Patch subprocess.run; assert capture_output kwarg.
        Why: Without capture_output=True, stdout and stderr are not available.
        """
        # Arrange
        mocker.patch("dispatch_schema.gates.shutil.which", return_value="/usr/bin/true")
        mock_run = mocker.patch(
            "dispatch_schema.gates.subprocess.run", return_value=_make_completed_process(returncode=0)
        )

        # Act
        run_quality_gates(["true"])

        # Assert
        _, kwargs = mock_run.call_args
        assert kwargs["capture_output"] is True

    def test_subprocess_run_called_with_text_true(self, mocker: MockerFixture) -> None:
        """subprocess.run is called with text=True for string stdout/stderr.

        Tests: Text mode configuration for subprocess.
        How: Patch subprocess.run; assert text kwarg.
        Why: text=True ensures stdout/stderr are str, not bytes.
        """
        # Arrange
        mocker.patch("dispatch_schema.gates.shutil.which", return_value="/usr/bin/true")
        mock_run = mocker.patch(
            "dispatch_schema.gates.subprocess.run", return_value=_make_completed_process(returncode=0)
        )

        # Act
        run_quality_gates(["true"])

        # Assert
        _, kwargs = mock_run.call_args
        assert kwargs["text"] is True

    def test_subprocess_run_receives_resolved_executable_path(self, mocker: MockerFixture) -> None:
        """subprocess.run receives the resolved executable path as first token.

        Tests: shutil.which resolution applied to command tokens.
        How: Patch which to return '/resolved/mybin'; assert first positional arg.
        Why: Ensures PATH resolution happens before process spawn.
        """
        # Arrange
        mocker.patch("dispatch_schema.gates.shutil.which", return_value="/resolved/mybin")
        mock_run = mocker.patch(
            "dispatch_schema.gates.subprocess.run", return_value=_make_completed_process(returncode=0)
        )

        # Act
        run_quality_gates(["mybin --flag value"])

        # Assert
        args, _ = mock_run.call_args
        tokens = args[0]
        assert tokens[0] == "/resolved/mybin"

    def test_subprocess_run_receives_tokenised_arguments(self, mocker: MockerFixture) -> None:
        """Command arguments are tokenised with shlex.split and passed to subprocess.run.

        Tests: shlex.split applied to command string.
        How: Patch subprocess.run; assert tokens include the flag and value args.
        Why: Prevents shell injection — no shell=True is used.
        """
        # Arrange
        mocker.patch("dispatch_schema.gates.shutil.which", return_value="/resolved/mybin")
        mock_run = mocker.patch(
            "dispatch_schema.gates.subprocess.run", return_value=_make_completed_process(returncode=0)
        )

        # Act
        run_quality_gates(["mybin --flag value"])

        # Assert
        args, _ = mock_run.call_args
        tokens = args[0]
        assert tokens == ["/resolved/mybin", "--flag", "value"]


# ---------------------------------------------------------------------------
# Integration tests — real subprocess (marked integration)
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_run_quality_gates_integration_real_echo_passes(tmp_path: Path) -> None:
    """run_quality_gates returns passed=True when a real command succeeds.

    Tests: integration path with a real subprocess call.
    How: Run 'echo hello' in a tmp directory; assert result fields.
    Why: Ensures the unit-tested mock path matches real subprocess behaviour.
    """
    # Arrange / Act
    result = run_quality_gates(["echo hello"], cwd=tmp_path)

    # Assert
    assert result.passed is True
    assert result.results[0].exit_code == 0
    assert "hello" in result.results[0].stdout


@pytest.mark.integration
def test_run_quality_gates_integration_false_fails(tmp_path: Path) -> None:
    """run_quality_gates returns passed=False when a real command exits non-zero.

    Tests: integration path with a failing real command.
    How: Run 'false' in a tmp directory; assert passed is False and exit code non-zero.
    Why: Confirms gate failure propagates correctly end-to-end.
    """
    # Arrange / Act
    result = run_quality_gates(["false"], cwd=tmp_path)

    # Assert
    assert result.passed is False
    assert result.results[0].exit_code != 0


@pytest.mark.integration
def test_run_quality_gates_integration_command_not_found(tmp_path: Path) -> None:
    """run_quality_gates returns exit_code=127 for a non-existent real command.

    Tests: command-not-found path with a real subprocess call.
    How: Run a gibberish command; assert passed is False and exit_code is 127.
    Why: Verifies the shutil.which-based 127 path matches real shell semantics.
    """
    # Arrange / Act
    result = run_quality_gates(["zzz-definitely-not-a-real-command-xyz"], cwd=tmp_path)

    # Assert
    assert result.passed is False
    assert result.results[0].exit_code == 127


# ---------------------------------------------------------------------------
# subprocess.TimeoutExpired contract (exit_code=124)
# ---------------------------------------------------------------------------


class TestSubprocessTimeoutContract:
    """run_quality_gates behaviour when subprocess.run raises TimeoutExpired.

    The implementation catches subprocess.TimeoutExpired and converts it to a
    CommandResult(exit_code=124) without re-raising, following the Unix
    timeout(1) convention and mirroring the existing exit_code=127
    command-not-found pattern.
    """

    def test_timeout_produces_exit_code_124(self, mocker: MockerFixture) -> None:
        """TimeoutExpired exception is converted to CommandResult.exit_code=124.

        Tests: Timeout exception path in run_quality_gates.
        How: Patch shutil.which to return a valid path; patch subprocess.run
             with side_effect=TimeoutExpired; assert exit_code is 124.
        Why: 124 is the Unix timeout(1) convention; callers check this code to
             distinguish hung commands from other failures.
        """
        # Arrange
        mocker.patch("dispatch_schema.gates.shutil.which", return_value="/usr/bin/cmd")
        mocker.patch(
            "dispatch_schema.gates.subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=["cmd"], timeout=300.0)
        )

        # Act
        result = run_quality_gates(["cmd"], timeout=300.0)

        # Assert
        assert result.results[0].exit_code == 124

    def test_timeout_stderr_contains_timeout_duration(self, mocker: MockerFixture) -> None:
        """CommandResult.stderr includes the configured timeout duration.

        Tests: stderr content for the TimeoutExpired path.
        How: Patch subprocess.run to raise TimeoutExpired with timeout=300.0;
             assert the string "300.0s" appears in CommandResult.stderr.
        Why: Callers display stderr in logs; the duration lets operators
             diagnose whether the timeout was appropriate.
        """
        # Arrange
        mocker.patch("dispatch_schema.gates.shutil.which", return_value="/usr/bin/cmd")
        mocker.patch(
            "dispatch_schema.gates.subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=["cmd"], timeout=300.0)
        )

        # Act
        result = run_quality_gates(["cmd"], timeout=300.0)

        # Assert
        assert "300s" in result.results[0].stderr

    def test_timeout_result_has_passed_false(self, mocker: MockerFixture) -> None:
        """CommandResult.passed is False when TimeoutExpired is raised.

        Tests: passed field derivation for the timeout exception path.
        How: Patch subprocess.run to raise TimeoutExpired; assert passed.
        Why: A timed-out command is a definitive failure — it never completed.
        """
        # Arrange
        mocker.patch("dispatch_schema.gates.shutil.which", return_value="/usr/bin/cmd")
        mocker.patch(
            "dispatch_schema.gates.subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=["cmd"], timeout=300.0)
        )

        # Act
        result = run_quality_gates(["cmd"], timeout=300.0)

        # Assert
        assert result.results[0].passed is False

    def test_timeout_failfast_stops_after_first_timeout(self, mocker: MockerFixture) -> None:
        """Fail-fast mode halts after a TimeoutExpired result.

        Tests: FAIL_FAST interaction with the timeout exception path.
        How: Provide two commands; first raises TimeoutExpired; assert only
             one result is collected and subprocess.run called once.
        Why: TimeoutExpired produces passed=False, so fail-fast must honour it
             and skip subsequent commands.
        """
        # Arrange
        mocker.patch("dispatch_schema.gates.shutil.which", return_value="/usr/bin/cmd")
        mock_run = mocker.patch(
            "dispatch_schema.gates.subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=["cmd"], timeout=300.0)
        )

        # Act
        result = run_quality_gates(["cmd a", "cmd b"], mode=GateRunMode.FAIL_FAST, timeout=300.0)

        # Assert
        assert len(result.results) == 1
        mock_run.assert_called_once()

    def test_timeout_runall_continues_after_timeout(self, mocker: MockerFixture) -> None:
        """Run-all mode continues executing after a TimeoutExpired result.

        Tests: RUN_ALL interaction with the timeout exception path.
        How: First command raises TimeoutExpired; second returns exit_code=0;
             assert two results are collected.
        Why: Run-all must collect a full diagnostic picture — even when a
             command times out, subsequent commands should still run.
        """
        # Arrange
        mocker.patch("dispatch_schema.gates.shutil.which", return_value="/usr/bin/cmd")
        mocker.patch(
            "dispatch_schema.gates.subprocess.run",
            side_effect=[subprocess.TimeoutExpired(cmd=["cmd"], timeout=300.0), _make_completed_process(returncode=0)],
        )

        # Act
        result = run_quality_gates(["cmd a", "cmd b"], mode=GateRunMode.RUN_ALL, timeout=300.0)

        # Assert
        assert len(result.results) == 2
        assert result.results[0].exit_code == 124
        assert result.results[1].exit_code == 0

    def test_custom_timeout_value_forwarded_to_subprocess(self, mocker: MockerFixture) -> None:
        """Custom timeout value is passed through to subprocess.run.

        Tests: timeout parameter forwarding in run_quality_gates.
        How: Call with timeout=5.0; assert subprocess.run received timeout=5.0
             as a keyword argument.
        Why: Without forwarding, the subprocess would use no timeout regardless
             of what the caller requested — the fix must wire the parameter.
        """
        # Arrange
        mocker.patch("dispatch_schema.gates.shutil.which", return_value="/usr/bin/cmd")
        mock_run = mocker.patch(
            "dispatch_schema.gates.subprocess.run", return_value=_make_completed_process(returncode=0)
        )

        # Act
        run_quality_gates(["cmd"], timeout=5.0)

        # Assert
        _, kwargs = mock_run.call_args
        assert kwargs["timeout"] == pytest.approx(5.0)


# ---------------------------------------------------------------------------
# {files} template variable pass-through
# ---------------------------------------------------------------------------


class TestFilesTemplateVariable:
    """{files} placeholder in commands is NOT substituted by run_quality_gates.

    The function is a pass-through executor: callers must expand {files}
    before invoking run_quality_gates. This class documents and enforces
    that contract.
    """

    def test_files_template_passed_verbatim_to_subprocess(self, mocker: MockerFixture) -> None:
        """{files} appears literally in the subprocess.run call args.

        Tests: that run_quality_gates does not substitute {files} before
               passing the tokenised command to subprocess.run.
        How: Patch shutil.which; patch subprocess.run; call with a command
             containing {files}; inspect the positional args received by
             subprocess.run.
        Why: Callers pre-expand {files} with the actual file list. If
             run_quality_gates substituted it too, a double-expansion bug
             would silently corrupt commands.
        """
        # Arrange
        mocker.patch("dispatch_schema.gates.shutil.which", return_value="/usr/bin/ruff")
        mock_run = mocker.patch(
            "dispatch_schema.gates.subprocess.run", return_value=_make_completed_process(returncode=0)
        )

        # Act
        run_quality_gates(["ruff check {files}"])

        # Assert: {files} was forwarded as a literal token
        call_args, _ = mock_run.call_args
        assert "{files}" in call_args[0]

    def test_files_template_result_recorded_in_command_field(self, mocker: MockerFixture) -> None:
        """CommandResult.command preserves the original {files} command string.

        Tests: CommandResult.command field when input contains {files}.
        How: Call with 'ruff check {files}'; assert result.results[0].command
             equals the original string unchanged.
        Why: The command field is the caller-visible record of what was run.
             If it were modified, callers could not correlate results back to
             their original pre-expanded command template.
        """
        # Arrange
        mocker.patch("dispatch_schema.gates.shutil.which", return_value="/usr/bin/ruff")
        mocker.patch("dispatch_schema.gates.subprocess.run", return_value=_make_completed_process(returncode=0))

        # Act
        result = run_quality_gates(["ruff check {files}"])

        # Assert
        assert result.results[0].command == "ruff check {files}"

"""Tests for the ``cli_output`` JSON-on-error contract.

Tests: ``exit_with_json_error`` and ``emit_result`` keep failure payloads on
stdout as parseable JSON instead of routing them through the stderr-only
``err()`` helper.
How: Call the helpers directly (no Typer command context needed) and
capture stdout/stderr via ``capsys``.
Why: Every ``sam`` CLI invocation is consumed by an agent parsing compact
JSON from stdout (see plugins/development-harness/AGENTS.md "CLI and script
output"). A caught operation-layer error that only reaches stderr hands the
agent's JSON parser an empty stdout stream instead of the structured
``{"error": ...}`` payload the operations layer returned.
"""

from __future__ import annotations

import json

import pytest
import typer

from sam_schema.cli_output import emit_result, exit_with_json_error


class TestExitWithJsonError:
    """``exit_with_json_error`` writes JSON to stdout before exiting."""

    def test_writes_payload_as_json_to_stdout(self, capsys: pytest.CaptureFixture[str]) -> None:
        """The payload reaches stdout as compact JSON, not stderr text.

        Tests: stdout content.
        How: Call with a mapping payload, capture stdout after the raised Exit.
        Why: A caller reading only stdout must still receive the full error mapping.
        """
        with pytest.raises(typer.Exit):
            exit_with_json_error({"error": "bad", "context": 1})

        captured = capsys.readouterr()
        assert json.loads(captured.out) == {"error": "bad", "context": 1}
        assert captured.err == ""

    def test_defaults_to_exit_code_one(self) -> None:
        """The default exit code is 1 (operation/user error).

        Tests: default ``exit_code`` value.
        How: Call without an explicit ``exit_code`` and inspect the raised Exit.
        Why: Shell-level failure detection (``$?``) depends on a nonzero default.
        """
        with pytest.raises(typer.Exit) as exc_info:
            exit_with_json_error({"error": "bad"})

        assert exc_info.value.exit_code == 1

    def test_forwards_explicit_exit_code(self) -> None:
        """A caller-supplied ``exit_code`` is used instead of the default.

        Tests: explicit ``exit_code`` forwarding.
        How: Call with ``exit_code=2`` and inspect the raised Exit.
        Why: Some callers distinguish user errors (1) from internal errors (2).
        """
        with pytest.raises(typer.Exit) as exc_info:
            exit_with_json_error({"error": "bad"}, exit_code=2)

        assert exc_info.value.exit_code == 2


class TestEmitResultErrorContract:
    """``emit_result`` keeps error mappings JSON-parseable on stdout."""

    def test_error_mapping_reaches_stdout_as_json_and_exits_nonzero(self, capsys: pytest.CaptureFixture[str]) -> None:
        """A result mapping with an ``error`` key is JSON-emitted, not swallowed.

        Tests: The literal PR review regression -- ``dispatch read``/``artifact
        read`` on a missing entity previously exited via ``err()`` before any
        JSON reached stdout.
        How: Pass a mapping with ``error`` plus diagnostic context fields.
        Why: Callers parsing compact JSON must see the full error mapping,
        including any extra context fields (e.g. ``milestone_number``).
        """
        result = {"error": "Dispatch plan not found: x.yaml", "milestone_number": 999}

        with pytest.raises(typer.Exit) as exc_info:
            emit_result(result)

        assert exc_info.value.exit_code == 1
        captured = capsys.readouterr()
        assert json.loads(captured.out) == result

    def test_diagnostics_are_echoed_to_stderr_before_the_json_error(self, capsys: pytest.CaptureFixture[str]) -> None:
        """``messages``/``warnings``/``errors`` lists still go to stderr.

        Tests: Diagnostic-stream separation is preserved by the fix.
        How: Pass a mapping with both diagnostics and an ``error`` key.
        Why: stdout must remain exclusively the structured JSON payload; any
        prose diagnostics belong on stderr so a JSON parser on stdout never
        has to skip non-JSON lines.
        """
        result = {"error": "boom", "warnings": ["heads up"]}

        with pytest.raises(typer.Exit):
            emit_result(result)

        captured = capsys.readouterr()
        assert captured.err.strip() == "heads up"
        assert json.loads(captured.out) == result

    def test_success_mapping_without_error_key_is_unaffected(self, capsys: pytest.CaptureFixture[str]) -> None:
        """A mapping without an ``error`` key still returns normally.

        Tests: Regression guard -- the new error branch must not affect the
        pre-existing success path.
        How: Pass a mapping with no ``error`` key, assert no exception raised.
        Why: ``emit_result`` is the shared success/failure emitter for every
        ``sam`` grouped command; a success-path regression would break every
        caller, not just the error path this fix targets.
        """
        result = {"claimed": True, "task_id": "T1"}

        emit_result(result)

        captured = capsys.readouterr()
        assert json.loads(captured.out) == result

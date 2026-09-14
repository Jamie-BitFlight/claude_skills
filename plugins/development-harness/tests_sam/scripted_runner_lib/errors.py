"""Failing loudly: every reason a run stops, named rather than left to a traceback."""

from __future__ import annotations


class ScriptedRunnerError(RuntimeError):
    """The run cannot go on."""


class ToolchainMissingError(ScriptedRunnerError):
    """A program the run needs is not resolvable on PATH."""


class FixtureMissingError(ScriptedRunnerError):
    """A loop-plan fixture file the loop reads is absent."""


class CommandTimeoutError(ScriptedRunnerError):
    """A command did not finish inside the time the run allows it."""

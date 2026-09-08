"""One ``sam plan`` command: how the loop issues it, and what it printed, parsed rather than scraped.

This is the whole of the runner's contact with the ledger. Every command runs as a subprocess with
its arguments as a list, never through a shell, and every result is read as the JSON object or array
it is; ``dispatch``'s bare attempt number and the ``unchanged`` no-op line are handled as their own
documented shapes.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import BaseModel

from tests_sam.scripted_runner_lib.errors import CommandTimeoutError, ScriptedRunnerError
from tests_sam.scripted_runner_lib.workspace import Toolchain

ADDRESS_FLAGS: frozenset[str] = frozenset({"--address", "--plan-address"})
"""The flags that carry the plan or task a command acts on."""

NO_OP_CODE = re.compile(r"^[a-z][a-z-]*$")
"""A bare reason code, such as ``unchanged``, printed instead of a JSON result."""


class Argument(BaseModel):
    """One long flag of a ``sam plan`` command, with the value it carries."""

    name: str
    value: str | None = None


class CommandCall(BaseModel):
    """One ``sam plan`` invocation, as the surface tests read it."""

    command: str
    flags: tuple[str, ...] = ()
    address: str | None = None


class CommandResult(BaseModel):
    """One invocation's outcome, parsed rather than scraped.

    Every view below answers with a real default when the command's shape does not carry that
    field, so a caller reads an empty result instead of handling an exception.
    """

    call: CommandCall
    exit_code: int
    stdout: str
    stderr: str
    payload: dict[str, Any] | list[Any] | None = None

    @property
    def fields(self) -> dict[str, Any]:
        """Return the payload's own fields, or an empty mapping when it is not an object."""
        return self.payload if isinstance(self.payload, dict) else {}

    @property
    def findings(self) -> list[Any]:
        """Return the payload's entries, or an empty list when it is not an array."""
        return self.payload if isinstance(self.payload, list) else []

    @property
    def events(self) -> tuple[str, ...]:
        """Return the event kinds the command appended to the log."""
        recorded = self.fields.get("events")
        return tuple(str(item) for item in recorded) if isinstance(recorded, list) else ()

    @property
    def status(self) -> str | None:
        """Return the task status the command reports, when it reports one."""
        reported = self.fields.get("status")
        return str(reported) if isinstance(reported, str) else None

    @property
    def attempt(self) -> int | None:
        """Return the attempt number, from the payload or from ``dispatch``'s bare line."""
        reported = self.fields.get("attempt")
        if isinstance(reported, int):
            return reported
        printed = self.stdout.strip()
        return int(printed) if printed.isdigit() else None

    @property
    def task(self) -> str | None:
        """Return the task the command acted on, when it names one."""
        named = self.fields.get("task")
        return str(named) if isinstance(named, str) else None

    @property
    def renew_by(self) -> str | None:
        """Return the new lease deadline, when the command renewed one."""
        deadline = self.fields.get("renew_by")
        return str(deadline) if isinstance(deadline, str) else None

    @property
    def changed(self) -> dict[str, Any]:
        """Return the columns the command wrote."""
        written = self.fields.get("changed")
        return written if isinstance(written, dict) else {}

    @property
    def row(self) -> dict[str, Any]:
        """Return the task row the command rendered, when it rendered one."""
        rendered = self.fields.get("row")
        return rendered if isinstance(rendered, dict) else {}

    @property
    def items(self) -> tuple[dict[str, Any], ...]:
        """Return the task rows a listing command rendered."""
        listed = self.fields.get("items")
        return tuple(item for item in listed if isinstance(item, dict)) if isinstance(listed, list) else ()

    @property
    def count(self) -> int | None:
        """Return how many rows a listing command counted."""
        counted = self.fields.get("count")
        return counted if isinstance(counted, int) else None

    @property
    def sections(self) -> tuple[dict[str, Any], ...]:
        """Return the report sections the command rendered."""
        rendered = self.fields.get("sections")
        return tuple(item for item in rendered if isinstance(item, dict)) if isinstance(rendered, list) else ()

    @property
    def noop(self) -> str | None:
        """Return the bare no-op code the command printed instead of a result, when it did."""
        printed = self.stdout.strip()
        return printed if self.payload is None and NO_OP_CODE.match(printed) else None


class LedgerCommandError(ScriptedRunnerError):
    """A ``sam plan`` command exited non-zero, which stops the run."""

    def __init__(self, result: CommandResult) -> None:
        """Carry the command, its status and both of its streams into the message.

        Args:
            result: The outcome of the command that exited non-zero.
        """
        self.call = result.call
        self.exit_code = result.exit_code
        self.stdout = result.stdout
        self.stderr = result.stderr
        super().__init__(
            f"sam plan {result.call.command} {' '.join(result.call.flags)} exited {result.exit_code}\n"
            f"stdout: {result.stdout}\n"
            f"stderr: {result.stderr}"
        )


def parse_payload(stdout: str) -> dict[str, Any] | list[Any] | None:
    """Return one command's stdout as the JSON object or array it is, or None when it is neither.

    Args:
        stdout: What the command printed.

    Returns:
        The parsed object or array, or None for a bare no-op code, a bare attempt number or silence.
    """
    text = stdout.strip()
    if not text:
        return None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict | list) else None


def address_of(arguments: Sequence[Argument]) -> str | None:
    """Return the plan or task one command acts on.

    Args:
        arguments: The command's flags and their values.

    Returns:
        The ``--address`` or ``--plan-address`` value, or None when the command names neither.
    """
    for item in arguments:
        if item.name in ADDRESS_FLAGS:
            return item.value
    return None


class LedgerCli:
    """Runs one ``sam plan`` command per call, as a subprocess and never through a shell."""

    def __init__(self, toolchain: Toolchain, environment: Mapping[str, str], timeout_seconds: int) -> None:
        """Bind the driver to one CLI, one environment and one per-command timeout.

        Args:
            toolchain: The resolved ``uv`` and the CLI it runs.
            environment: The variables this run adds to the inherited environment.
            timeout_seconds: How long one command may take.
        """
        self.toolchain = toolchain
        self.environment = {**os.environ, **environment, "PYTHONIOENCODING": "utf-8"}
        self.timeout_seconds = timeout_seconds

    def run(self, command: str, arguments: Sequence[Argument]) -> CommandResult:
        """Run one ``sam plan`` command and return what it printed, parsed.

        Args:
            command: The ``sam plan`` command name.
            arguments: Its flags and their values.

        Returns:
            The command's outcome.

        Raises:
            LedgerCommandError: When the command exits non-zero, which is unexpected on this path.
            CommandTimeoutError: When the command does not finish inside the run's per-command limit.
        """
        argv = [str(self.toolchain.uv), "run", str(self.toolchain.cli_path), "plan", command]
        for item in arguments:
            argv.append(item.name)
            if item.value is not None:
                argv.append(item.value)
        try:
            completed = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=self.environment,
                timeout=self.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as expired:
            flags = " ".join(item.name for item in arguments)
            raise CommandTimeoutError(
                f"sam plan {command} {flags} did not finish within {self.timeout_seconds} seconds"
            ) from expired
        result = CommandResult(
            call=CommandCall(
                command=command, flags=tuple(item.name for item in arguments), address=address_of(arguments)
            ),
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            payload=parse_payload(completed.stdout),
        )
        if result.exit_code != 0:
            raise LedgerCommandError(result)
        return result
